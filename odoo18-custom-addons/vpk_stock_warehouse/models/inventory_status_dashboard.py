# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models

FAST_MIN_ISSUES = 12
WINDOW_FAST_DAYS = 90
WINDOW_HOLD_DAYS = 180
THAI_MONTHS = (
    "",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
)


class StockWarehouseInventoryStatus(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def get_inventory_status_dashboard(self, warehouse_id=False, category_id=False):
        """สถานะสินค้าคงคลัง: คงเหลือ เคลื่อนไหวเร็ว ช้า และไม่เคลื่อนไหว"""
        lines, meta = self._inventory_status_lines(warehouse_id, category_id)
        return self._inventory_status_payload(lines, meta)

    @api.model
    def export_inventory_status_rows(self, warehouse_id=False, category_id=False):
        lines, _meta = self._inventory_status_lines(warehouse_id, category_id)
        rows = []
        for line in lines:
            rows.append(
                {
                    "code": line["code"],
                    "name": line["name"],
                    "category": line["category"],
                    "klass": line["klass_label"],
                    "qty": line["qty"],
                    "uom": line["uom"],
                    "value": round(line["value"], 2),
                    "out_90": line["out_count"],
                    "qty_out_90": line["qty_out"],
                    "cover_days": line["cover"],
                    "last_move": line["last_label"],
                }
            )
        return rows

    def _inventory_status_lines(self, warehouse_id, category_id):
        company = self.env.company
        warehouse = self.browse(warehouse_id).exists() if warehouse_id else self.browse()
        if warehouse and warehouse.company_id != company:
            warehouse = self.browse()
        category = self.env["product.category"].browse(category_id).exists() if category_id else self.env["product.category"]
        categ_ids = []
        if category:
            categ_ids = self.env["product.category"].search([("id", "child_of", category.id)]).ids

        now = fields.Datetime.now()
        fast_from = now - timedelta(days=WINDOW_FAST_DAYS)
        hold_from = now - timedelta(days=WINDOW_HOLD_DAYS)
        params = {"company_id": company.id, "fast_from": fast_from, "hold_from": hold_from}
        quant_loc, move_src, params = self._inventory_status_scope(warehouse, params)
        categ_sql = ""
        if categ_ids:
            params["categ_ids"] = categ_ids
            categ_sql = "AND pt.categ_id = ANY(%(categ_ids)s)"

        self.env.cr.execute(
            f"""
            SELECT q.product_id, SUM(q.quantity) AS qty, MIN(q.in_date) AS in_date
            FROM stock_quant q
            JOIN stock_location l ON l.id = q.location_id
            JOIN product_product pp ON pp.id = q.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE q.quantity > 0
              AND l.usage = 'internal'
              AND (l.company_id IS NULL OR l.company_id = %(company_id)s)
              AND {quant_loc}
              {categ_sql}
            GROUP BY q.product_id
            """,
            params,
        )
        quant_rows = self.env.cr.dictfetchall()
        product_ids = [row["product_id"] for row in quant_rows]
        move_map = {}
        if product_ids:
            params["product_ids"] = product_ids
            self.env.cr.execute(
                f"""
                SELECT sm.product_id,
                       COUNT(*) FILTER (
                           WHERE sm.date >= %(fast_from)s
                             AND src.usage = 'internal'
                             AND dest.usage <> 'internal'
                       ) AS out_90,
                       COUNT(*) FILTER (
                           WHERE src.usage = 'internal'
                             AND dest.usage <> 'internal'
                       ) AS out_180,
                       COALESCE(SUM(sm.product_qty) FILTER (
                           WHERE sm.date >= %(fast_from)s
                             AND src.usage = 'internal'
                             AND dest.usage <> 'internal'
                       ), 0) AS qty_out_90,
                       MAX(sm.date) FILTER (
                           WHERE src.usage = 'internal'
                             AND dest.usage <> 'internal'
                       ) AS last_out,
                       COUNT(*) FILTER (
                           WHERE src.usage = 'internal'
                             AND dest.usage = 'internal'
                             AND sm.location_id <> sm.location_dest_id
                       ) AS internal_180
                FROM stock_move sm
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dest ON dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND sm.date >= %(hold_from)s
                  AND sm.company_id = %(company_id)s
                  AND sm.product_id = ANY(%(product_ids)s)
                  AND {move_src}
                GROUP BY sm.product_id
                """,
                params,
            )
            move_map = {row["product_id"]: row for row in self.env.cr.dictfetchall()}

        order_map = self._inventory_status_mins(warehouse, product_ids, company)
        products = self.env["product.product"].browse(product_ids).with_company(company)
        prices = {product.id: product.sudo().standard_price or 0.0 for product in products}
        lines = []
        for row in quant_rows:
            product = products.browse(row["product_id"])
            move = move_map.get(product.id, {})
            out_90 = int(move.get("out_90") or 0)
            out_180 = int(move.get("out_180") or 0)
            internal_180 = int(move.get("internal_180") or 0)
            qty_out = float(move.get("qty_out_90") or 0.0)
            in_date = row["in_date"]
            last_out = move.get("last_out")
            anchor = last_out or in_date or now
            age_days = max((now - anchor).days, 0)
            if out_90 >= FAST_MIN_ISSUES:
                klass = "fast"
            elif out_90 >= 1 or out_180 >= 1 or internal_180 >= 1 or age_days < WINDOW_HOLD_DAYS:
                klass = "slow"
            else:
                klass = "dead"
            qty = float(row["qty"] or 0.0)
            price = float(prices.get(product.id) or 0.0)
            cover = int(round(qty / (qty_out / WINDOW_FAST_DAYS))) if qty_out > 0 else None
            min_qty = order_map.get(product.id)
            uom = product.uom_id.name or ""
            lines.append(
                {
                    "id": product.id,
                    "code": product.default_code or "",
                    "name": product.name or product.display_name,
                    "category_id": product.categ_id.id,
                    "category": product.categ_id.name or "ไม่ระบุหมวด",
                    "qty": qty,
                    "uom": uom,
                    "qty_text": self._inventory_status_qty(qty, uom),
                    "value": qty * price,
                    "out_count": out_90,
                    "qty_out": qty_out,
                    "out_text": self._inventory_status_qty(qty_out, uom),
                    "cover": cover,
                    "below_min": bool(min_qty is not None and qty < min_qty),
                    "age_days": age_days,
                    "last_label": self._inventory_status_date(last_out or in_date),
                    "klass": klass,
                    "klass_label": {"fast": "เคลื่อนไหวเร็ว", "slow": "เคลื่อนไหวช้า", "dead": "ไม่เคลื่อนไหว"}[klass],
                }
            )
        warehouses = self.search([("company_id", "=", company.id)], order="sequence, name, id")
        meta = {
            "now": now,
            "warehouse": warehouse,
            "category": category,
            "warehouses": warehouses,
            "categories": self._inventory_status_categories(warehouse, company),
        }
        return lines, meta

    def _inventory_status_scope(self, warehouse, params):
        if warehouse and warehouse.lot_stock_id and warehouse.lot_stock_id.parent_path:
            params = dict(params, path=warehouse.lot_stock_id.parent_path + "%")
            return (
                "l.parent_path LIKE %(path)s",
                "(src.parent_path LIKE %(path)s OR dest.parent_path LIKE %(path)s)",
                params,
            )
        return ("TRUE", "src.usage = 'internal'", params)

    def _inventory_status_mins(self, warehouse, product_ids, company):
        if not product_ids:
            return {}
        domain = [
            ("company_id", "=", company.id),
            ("product_id", "in", product_ids),
            ("active", "=", True),
        ]
        if warehouse:
            domain.append(("warehouse_id", "=", warehouse.id))
        grouped = self.env["stock.warehouse.orderpoint"]._read_group(
            domain, ["product_id"], ["product_min_qty:max"]
        )
        result = {}
        for product, min_qty in grouped:
            if product:
                result[product.id] = min_qty or 0.0
        return result

    def _inventory_status_categories(self, warehouse, company):
        params = {"company_id": company.id}
        quant_loc, _move_src, params = self._inventory_status_scope(warehouse, params)
        self.env.cr.execute(
            f"""
            SELECT DISTINCT pt.categ_id
            FROM stock_quant q
            JOIN stock_location l ON l.id = q.location_id
            JOIN product_product pp ON pp.id = q.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE q.quantity > 0
              AND l.usage = 'internal'
              AND (l.company_id IS NULL OR l.company_id = %(company_id)s)
              AND {quant_loc}
              AND pt.categ_id IS NOT NULL
            """,
            params,
        )
        categ_ids = [row[0] for row in self.env.cr.fetchall()]
        categories = self.env["product.category"].browse(categ_ids).sorted(key=lambda categ: categ.complete_name or "")
        return [{"id": categ.id, "name": categ.complete_name or categ.name} for categ in categories]

    def _inventory_status_payload(self, lines, meta):
        def subset(klass):
            return [line for line in lines if line["klass"] == klass]

        fast = subset("fast")
        slow = subset("slow")
        dead = subset("dead")
        total_sku = len(lines)
        total_qty = sum(line["qty"] for line in lines)
        total_value = sum(line["value"] for line in lines)

        def pct(count):
            return round((count * 100.0 / total_sku), 1) if total_sku else 0

        def value_pct(group):
            if not total_value:
                return 0
            return round((sum(line["value"] for line in group) * 100.0 / total_value), 1)

        slow_out = sum(line["qty_out"] for line in slow)
        slow_qty = sum(line["qty"] for line in slow)
        slow_cover = int(round(slow_qty / (slow_out / WINDOW_FAST_DAYS))) if slow_out else None
        dead_year = [line for line in dead if line["age_days"] > 365]
        fast_low = [line for line in fast if line["below_min"] or (line["cover"] is not None and line["cover"] < 30)]

        def part(key, label, group):
            return {
                "key": key,
                "label": label,
                "sku": len(group),
                "sku_pct": pct(len(group)),
                "value": sum(line["value"] for line in group),
                "value_pct": value_pct(group),
            }

        parts = [
            part("fast", "เคลื่อนไหวเร็ว", fast),
            part("slow", "เคลื่อนไหวช้า", slow),
            part("dead", "ไม่เคลื่อนไหว", dead),
        ]
        categories = {}
        for line in lines:
            bucket = categories.setdefault(
                line["category_id"],
                {"id": line["category_id"], "name": line["category"], "sku": 0, "qty": 0.0, "value": 0.0, "fast": 0, "slow": 0, "dead": 0},
            )
            bucket["sku"] += 1
            bucket["qty"] += line["qty"]
            bucket["value"] += line["value"]
            bucket[line["klass"]] += 1
        category_rows = []
        for bucket in sorted(categories.values(), key=lambda item: (-item["value"], -item["sku"], item["name"])):
            sku = bucket["sku"] or 1
            category_rows.append(
                {
                    "id": bucket["id"],
                    "name": bucket["name"],
                    "sku": bucket["sku"],
                    "qty": bucket["qty"],
                    "qty_text": self._inventory_status_qty(bucket["qty"], ""),
                    "value": bucket["value"],
                    "fast_pct": round(bucket["fast"] * 100 / sku),
                    "slow_pct": round(bucket["slow"] * 100 / sku),
                    "dead_pct": round(bucket["dead"] * 100 / sku),
                }
            )

        age_buckets = [
            {"key": "d180", "label": "180–270 วัน", "min": 180, "max": 270},
            {"key": "d271", "label": "271–365 วัน", "min": 271, "max": 365},
            {"key": "y1", "label": "เกิน 1 ปี", "min": 366, "max": None},
        ]
        ages = []
        for spec in age_buckets:
            matched = [
                line
                for line in dead
                if line["age_days"] >= spec["min"] and (spec["max"] is None or line["age_days"] <= spec["max"])
            ]
            ages.append(
                {
                    "key": spec["key"],
                    "label": spec["label"],
                    "sku": len(matched),
                    "value": sum(line["value"] for line in matched),
                    "ids": [line["id"] for line in matched],
                }
            )
        max_age_value = max([item["value"] for item in ages] or [0]) or 1
        for item in ages:
            item["width"] = int(round(item["value"] * 100 / max_age_value)) if item["value"] else (8 if item["sku"] else 0)

        fast_rows = sorted(fast, key=lambda line: (-line["out_count"], line["cover"] if line["cover"] is not None else 10**9))[:6]
        slow_rows = sorted(slow, key=lambda line: (-(line["cover"] or 0), -line["qty"]))[:6]
        dead_rows = sorted(dead, key=lambda line: (-line["value"], -line["age_days"]))[:6]
        warehouse = meta["warehouse"]
        category = meta["category"]
        return {
            "date_label": self._inventory_status_today(meta["now"]),
            "warehouse_id": warehouse.id if warehouse else 0,
            "category_id": category.id if category else 0,
            "warehouses": [{"id": wh.id, "label": "%s (%s)" % (wh.name, wh.code or "-")} for wh in meta["warehouses"]],
            "categories": meta["categories"],
            "total_sku": total_sku,
            "total_qty": total_qty,
            "total_value": total_value,
            "parts": parts,
            "slow_cover": slow_cover,
            "fast_low": len(fast_low),
            "dead_year": len(dead_year),
            "categories_table": category_rows,
            "ages": ages,
            "fast_rows": [self._inventory_status_row(line) for line in fast_rows],
            "slow_rows": [self._inventory_status_row(line) for line in slow_rows],
            "dead_rows": [self._inventory_status_row(line) for line in dead_rows],
            "ids": {
                "all": [line["id"] for line in lines],
                "fast": [line["id"] for line in fast],
                "slow": [line["id"] for line in slow],
                "dead": [line["id"] for line in dead],
                "dead_year": [line["id"] for line in dead_year],
            },
        }

    def _inventory_status_row(self, line):
        return {
            "id": line["id"],
            "code": line["code"] or line["name"],
            "name": line["name"],
            "qty_text": line["qty_text"],
            "out_text": line["out_text"],
            "cover": line["cover"],
            "value": line["value"],
            "last_label": line["last_label"],
            "low": line["below_min"] or (line["cover"] is not None and line["cover"] < 30),
        }

    def _inventory_status_qty(self, qty, uom):
        if abs(qty - round(qty)) < 0.001:
            text = "{:,.0f}".format(round(qty))
        else:
            text = "{:,.2f}".format(qty)
        return ("%s %s" % (text, uom)).strip()

    def _inventory_status_date(self, moment):
        if not moment:
            return "-"
        local = fields.Datetime.context_timestamp(self, moment)
        return "%s %s %s" % (local.day, THAI_MONTHS[local.month], local.year + 543)

    def _inventory_status_today(self, moment):
        local = fields.Datetime.context_timestamp(self, moment)
        weekdays = ("จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์")
        return "%s %s %s %s" % (weekdays[local.weekday()], local.day, THAI_MONTHS[local.month], local.year + 543)
