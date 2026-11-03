# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_round


class VpkStockCardReport(models.TransientModel):
    _name = "vpk.stock.card.report"
    _description = "รายงานบัญชีคุมวัสดุ"

    date_from = fields.Date(
        string="ตั้งแต่วันที่",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="ถึงวันที่",
        required=True,
        default=fields.Date.context_today,
    )
    categ_id = fields.Many2one(
        "product.category",
        string="กลุ่มวัสดุ",
        help="เลือกหมวดสินค้า เช่น วัสดุสำนักงาน จะรวมหมวดย่อยด้วย",
    )
    product_ids = fields.Many2many(
        "product.product",
        string="สินค้า",
        domain="[('is_storable', '=', True)]",
    )
    warehouse_id = fields.Many2one("stock.warehouse", string="คลังสินค้า")
    company_id = fields.Many2one(
        "res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
    )
    hide_zero = fields.Boolean(
        string="ซ่อนสินค้าที่ยอดเป็นศูนย์ตลอดช่วง",
        default=True,
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด"))

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_stock_card.action_report_stock_card"
        ).report_action(self)

    def _thai_date(self, value):
        if not value:
            return ""
        return "%s/%s/%s" % (value.day, value.month, value.year + 543)

    def _thai_datetime(self, value=None):
        value = value or fields.Datetime.context_timestamp(
            self, datetime.utcnow()
        )
        return "%s/%s/%s %02d:%02d:%02d" % (
            value.day,
            value.month,
            value.year + 543,
            value.hour,
            value.minute,
            value.second,
        )

    def _format_qty(self, qty, digits=2):
        return float_round(qty or 0.0, precision_digits=digits)

    def _format_amount(self, amount):
        return float_round(amount or 0.0, precision_digits=2)

    def _category_label(self):
        self.ensure_one()
        if self.categ_id:
            name = self.categ_id.display_name or self.categ_id.name or ""
            # ตัด root "กลุ่มวัสดุ / " ถ้ามี เพื่อให้หัวรายงานสั้น
            if " / " in name:
                name = name.split(" / ", 1)[-1]
            return name
        if self.product_ids:
            return _("สินค้าที่เลือก")
        return _("ทั้งหมด")

    def _warehouse_location_ids(self):
        self.ensure_one()
        Location = self.env["stock.location"]
        if self.warehouse_id:
            return Location.search(
                [
                    ("id", "child_of", self.warehouse_id.view_location_id.id),
                    ("usage", "=", "internal"),
                ]
            )
        return Location.search(
            [
                ("company_id", "in", [False, self.company_id.id]),
                ("usage", "=", "internal"),
            ]
        )

    def _product_domain(self):
        self.ensure_one()
        domain = [
            ("is_storable", "=", True),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]
        if self.product_ids:
            domain.append(("id", "in", self.product_ids.ids))
        elif self.categ_id:
            domain.append(("categ_id", "child_of", self.categ_id.id))
        return domain

    def _move_unit_cost(self, move, product):
        layers = move.stock_valuation_layer_ids
        if layers:
            qty = sum(layers.mapped("quantity"))
            value = sum(layers.mapped("value"))
            if not float_is_zero(qty, precision_digits=6):
                return abs(value / qty)
        if move.price_unit:
            return abs(move.price_unit)
        return product.standard_price or 0.0

    def _party_label(self, move, direction):
        picking = move.picking_id
        if direction == "in":
            if picking.partner_id:
                return picking.partner_id.display_name
            if move.partner_id:
                return move.partner_id.display_name
            return _("รายการรับพัสดุ")
        # issue: prefer destination location / warehouse name
        dest = move.location_dest_id
        if dest.usage == "internal" and dest.warehouse_id:
            return dest.warehouse_id.name
        name = dest.display_name or ""
        # ตัด prefix ตำแหน่งยาว ๆ ให้สั้นลง
        if "/" in name:
            name = name.rsplit("/", 1)[-1].strip()
        if name:
            return name
        if picking.partner_id:
            return picking.partner_id.display_name
        if picking.origin:
            return picking.origin
        return _("รายการเบิกพัสดุ")

    def _doc_number(self, move):
        if move.picking_id:
            return move.picking_id.name
        return move.reference or move.name or ""

    def _collect_product_moves(self, products, location_ids):
        Move = self.env["stock.move"]
        domain = [
            ("state", "=", "done"),
            ("product_id", "in", products.ids),
            ("company_id", "=", self.company_id.id),
            ("date", "<=", fields.Datetime.to_datetime(self.date_to).replace(
                hour=23, minute=59, second=59
            )),
            "|",
            ("location_id", "in", location_ids.ids),
            ("location_dest_id", "in", location_ids.ids),
        ]
        moves = Move.search(domain, order="date asc, id asc")
        return moves

    def _signed_effect(self, move, location_ids):
        """คืนค่า (direction, qty) ทิศทางเทียบคลังที่เลือก"""
        loc_set = set(location_ids.ids)
        src_in = move.location_id.id in loc_set
        dest_in = move.location_dest_id.id in loc_set
        qty = move.quantity or 0.0
        if float_is_zero(qty, precision_digits=6):
            return False, 0.0
        if dest_in and not src_in:
            return "in", qty
        if src_in and not dest_in:
            return "out", qty
        return False, 0.0

    def _build_card(self, product, moves, location_ids):
        opening_qty = 0.0
        opening_amount = 0.0
        period_rows = []
        date_from = self.date_from

        for move in moves:
            direction, qty = self._signed_effect(move, location_ids)
            if not direction:
                continue
            unit = self._move_unit_cost(move, product)
            amount = qty * unit
            move_date = fields.Datetime.context_timestamp(self, move.date).date()
            if move_date < date_from:
                if direction == "in":
                    opening_qty += qty
                    opening_amount += amount
                else:
                    opening_qty -= qty
                    opening_amount -= amount
                continue
            period_rows.append(
                {
                    "date": move_date,
                    "party": self._party_label(move, direction),
                    "doc": self._doc_number(move),
                    "unit_price": unit,
                    "in_qty": qty if direction == "in" else 0.0,
                    "in_amount": amount if direction == "in" else 0.0,
                    "out_qty": qty if direction == "out" else 0.0,
                    "out_amount": amount if direction == "out" else 0.0,
                }
            )

        if self.hide_zero and not period_rows and float_is_zero(
            opening_qty, precision_digits=4
        ):
            return False

        bal_qty = opening_qty
        bal_amount = opening_amount
        days = []
        by_date = defaultdict(list)
        for row in period_rows:
            by_date[row["date"]].append(row)

        # แถวยอดยกมาต้นงวด
        opening_day = {
            "date": None,
            "date_label": "",
            "lines": [
                {
                    "date_label": "",
                    "party": _("ยอดยกมา"),
                    "doc": "",
                    "unit_price": 0.0,
                    "in_qty": 0.0,
                    "in_amount": 0.0,
                    "out_qty": 0.0,
                    "out_amount": 0.0,
                    "bal_qty": self._format_qty(bal_qty),
                    "bal_amount": self._format_amount(bal_amount),
                    "is_subtotal": False,
                    "is_opening": True,
                }
            ],
            "has_subtotal": False,
        }

        for day in sorted(by_date):
            day_in_qty = day_in_amt = day_out_qty = day_out_amt = 0.0
            lines = []
            first = True
            for row in by_date[day]:
                bal_qty += row["in_qty"] - row["out_qty"]
                bal_amount += row["in_amount"] - row["out_amount"]
                day_in_qty += row["in_qty"]
                day_in_amt += row["in_amount"]
                day_out_qty += row["out_qty"]
                day_out_amt += row["out_amount"]
                lines.append(
                    {
                        "date_label": self._thai_date(day) if first else "",
                        "party": row["party"],
                        "doc": row["doc"],
                        "unit_price": self._format_amount(row["unit_price"]),
                        "in_qty": self._format_qty(row["in_qty"])
                        if row["in_qty"]
                        else 0.0,
                        "in_amount": self._format_amount(row["in_amount"])
                        if row["in_amount"]
                        else 0.0,
                        "out_qty": self._format_qty(row["out_qty"])
                        if row["out_qty"]
                        else 0.0,
                        "out_amount": self._format_amount(row["out_amount"])
                        if row["out_amount"]
                        else 0.0,
                        "bal_qty": self._format_qty(bal_qty),
                        "bal_amount": self._format_amount(bal_amount),
                        "is_subtotal": False,
                        "is_opening": False,
                    }
                )
                first = False
            # ยอดยกไปท้ายวัน
            lines.append(
                {
                    "date_label": "",
                    "party": _("ยอดยกไป"),
                    "doc": "",
                    "unit_price": 0.0,
                    "in_qty": self._format_qty(day_in_qty),
                    "in_amount": self._format_amount(day_in_amt),
                    "out_qty": self._format_qty(day_out_qty),
                    "out_amount": self._format_amount(day_out_amt),
                    "bal_qty": self._format_qty(bal_qty),
                    "bal_amount": self._format_amount(bal_amount),
                    "is_subtotal": True,
                    "is_opening": False,
                }
            )
            days.append(
                {
                    "date": day,
                    "date_label": self._thai_date(day),
                    "lines": lines,
                }
            )

        product_name = product.display_name
        if product.default_code and product.default_code in product_name:
            # display_name มักเป็น [CODE] Name — ใช้ชื่ออย่างเดียวในช่องรายการ
            product_name = product.name

        return {
            "product_id": product.id,
            "product_code": product.default_code or str(product.id),
            "product_name": product_name,
            "uom_name": product.uom_id.display_name,
            "opening": opening_day,
            "days": days,
            "has_movement": bool(period_rows),
        }

    def get_report_cards(self):
        self.ensure_one()
        products = self.env["product.product"].search(
            self._product_domain(), order="default_code, id"
        )
        if not products:
            raise UserError(_("ไม่พบสินค้าตามเงื่อนไขที่เลือก"))
        location_ids = self._warehouse_location_ids()
        if not location_ids:
            raise UserError(_("ไม่พบตำแหน่งคลังสำหรับเงื่อนไขที่เลือก"))
        moves = self._collect_product_moves(products, location_ids)
        moves_by_product = defaultdict(
            lambda: self.env["stock.move"]
        )
        for move in moves:
            moves_by_product[move.product_id.id] |= move

        cards = []
        for product in products:
            card = self._build_card(
                product, moves_by_product[product.id], location_ids
            )
            if card:
                cards.append(card)
        if not cards:
            raise UserError(
                _("ไม่มีรายการเคลื่อนไหวหรือยอดคงเหลือในช่วงวันที่ที่เลือก")
            )
        return cards

    def get_report_meta(self):
        self.ensure_one()
        return {
            "category_label": self._category_label(),
            "date_from_label": self._thai_date(self.date_from),
            "date_to_label": self._thai_date(self.date_to),
            "print_label": self._thai_datetime(),
            "warehouse_label": self.warehouse_id.name if self.warehouse_id else "",
            "company_name": self.company_id.name,
        }
