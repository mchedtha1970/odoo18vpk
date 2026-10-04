# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from odoo import api, models
from odoo.osv.expression import AND, OR

OPEN_STATES = ("draft", "waiting", "confirmed", "assigned")
THAI_WEEKDAYS = ("จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์")
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


class StockWarehouseOperationsDashboard(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def get_operations_dashboard(self, period="today", warehouse_id=False):
        """สถานะงานคลัง: รับสินค้า โอนระหว่างคลัง และเบิกจ่ายออก"""
        tz = self._ops_tz()
        now_local = datetime.now(tz)
        start_local, end_local = self._ops_period_bounds(period, now_local)
        start_utc = self._ops_naive_utc(start_local)
        end_utc = self._ops_naive_utc(end_local)
        now_utc = self._ops_naive_utc(now_local)

        warehouses = self.search(
            [("company_id", "=", self.env.company.id)],
            order="sequence, name, id",
        )
        warehouse = self.browse(warehouse_id).exists() if warehouse_id else self.browse()
        if not warehouse or warehouse not in warehouses:
            warehouse = self._vpk_central_warehouse() or warehouses[:1]

        empty = self._ops_empty_payload(period, now_local, warehouses, warehouse)
        if not warehouse or not warehouse.lot_stock_id:
            return empty

        stock = warehouse.lot_stock_id
        has_qc = "qc_state" in self.env["stock.picking"]._fields
        scope = OR([
            [("state", "in", list(OPEN_STATES))],
            [("state", "=", "done"), ("date_done", ">=", start_utc), ("date_done", "<=", end_utc)],
        ])
        company_domain = [("company_id", "=", self.env.company.id), ("state", "!=", "cancel")]
        receipts = self._ops_collect(
            "receipt",
            AND([
                company_domain,
                [
                    ("picking_type_id.warehouse_id", "=", warehouse.id),
                    ("picking_type_code", "=", "incoming"),
                ],
                scope,
            ]),
            warehouse,
            stock,
            has_qc,
            now_utc,
            end_utc,
            tz,
        )
        transfers = self._ops_collect(
            "transfer",
            AND([
                company_domain,
                [("picking_type_code", "=", "internal")],
                OR([
                    [("location_id", "child_of", stock.id)],
                    [("location_dest_id", "child_of", stock.id)],
                ]),
                scope,
            ]),
            warehouse,
            stock,
            has_qc,
            now_utc,
            end_utc,
            tz,
        )
        issues = self._ops_collect(
            "issue",
            AND([
                company_domain,
                [
                    ("picking_type_code", "=", "outgoing"),
                    ("location_id", "child_of", stock.id),
                ],
                scope,
            ]),
            warehouse,
            stock,
            has_qc,
            now_utc,
            end_utc,
            tz,
        )
        columns = [receipts, transfers, issues]
        alerts = []
        for column in columns:
            alerts.extend(column.pop("alerts"))
        alerts.sort(key=lambda item: item["late_minutes"], reverse=True)
        alerts = alerts[:8]
        for alert in alerts:
            alert.pop("late_minutes", None)

        period_hint = {"today": "วันนี้", "7d": "7 วัน", "30d": "30 วัน"}.get(period, "วันนี้")
        hint_gap = "" if period == "today" else " "
        kpis = [
            self._ops_kpi(
                "receipt",
                "รับสินค้า",
                "ใบรับ%s%s" % (hint_gap, period_hint),
                receipts,
                "จัดเก็บเสร็จ %s ใบ · %s%%" % (receipts["done_count"], receipts["done_percent"]),
                "blue",
            ),
            self._ops_kpi(
                "transfer",
                "โอนสินค้า",
                "ใบโอน%s%s" % (hint_gap, period_hint),
                transfers,
                "ระหว่างทาง %s · รับแล้ว %s"
                % (transfers["stage_counts"].get("shipping", 0) + transfers["stage_counts"].get("waiting_receive", 0), transfers["done_count"]),
                "amber",
            ),
            self._ops_kpi(
                "issue",
                "เบิกใช้ภายใน",
                "ใบเบิก%s%s" % (hint_gap, period_hint),
                issues,
                "จ่ายแล้ว %s · รอจัด %s"
                % (
                    issues["done_count"],
                    issues["stage_counts"].get("approve", 0) + issues["stage_counts"].get("wait_pick", 0),
                ),
                "purple",
            ),
            {
                "key": "sla",
                "label": "งานเกิน SLA",
                "hint": "ต้องติดตาม",
                "value": len(alerts),
                "progress": 0,
                "foot": "รับ %s · โอน %s · เบิก %s"
                % (
                    sum(1 for alert in alerts if alert["stream"] == "receipt"),
                    sum(1 for alert in alerts if alert["stream"] == "transfer"),
                    sum(1 for alert in alerts if alert["stream"] == "issue"),
                ),
                "tone": "alert",
            },
        ]
        return {
            "period": period if period in ("today", "7d", "30d") else "today",
            "date_label": self._ops_thai_date(now_local),
            "updated_at": now_local.strftime("%H:%M"),
            "warehouse_id": warehouse.id,
            "warehouse_label": "%s (%s)" % (warehouse.name, warehouse.code or "-"),
            "warehouses": [
                {"id": wh.id, "name": wh.name, "code": wh.code or "", "label": "%s (%s)" % (wh.name, wh.code or "-")}
                for wh in warehouses
            ],
            "kpis": kpis,
            "columns": columns,
            "chart": self._ops_chart(period, start_local, now_local, columns, tz),
            "alerts": alerts,
            "alert_count": len(alerts),
        }

    def _ops_collect(self, stream, domain, warehouse, stock, has_qc, now_utc, day_end_utc, tz):
        pickings = self.env["stock.picking"].search(domain, order="scheduled_date asc, id desc")
        spec = self._ops_stream_spec(stream)
        stage_counts = {stage["key"]: 0 for stage in spec["stages"]}
        classified = []
        alerts = []
        for picking in pickings:
            stage_key, badge, tone = self._ops_classify(
                stream, picking, stock, has_qc, day_end_utc
            )
            stage_counts[stage_key] = stage_counts.get(stage_key, 0) + 1
            late_minutes = self._ops_late_minutes(picking, now_utc)
            row = {
                "id": picking.id,
                "model": "stock.picking",
                "name": picking.name,
                "meta": self._ops_meta(stream, picking),
                "route": self._ops_route(stream, picking),
                "status": badge,
                "tone": tone,
                "time": self._ops_row_time(stream, picking, tz, now_utc),
                "open": picking.state in OPEN_STATES,
                "scheduled": self._ops_local(picking.scheduled_date, tz),
            }
            classified.append(row)
            if late_minutes > 0 or (has_qc and stream == "receipt" and picking.qc_state == "failed" and picking.state in OPEN_STATES):
                alerts.append(
                    self._ops_alert(stream, picking, stock, late_minutes, now_utc, has_qc)
                )
        classified.sort(key=lambda row: (not row["open"], row["scheduled"] or datetime.max.replace(tzinfo=tz)))
        rows = []
        for row in classified[:6]:
            row.pop("open", None)
            row.pop("scheduled", None)
            rows.append(row)
        done_count = stage_counts.get(spec["done_key"], 0)
        total = sum(stage_counts.values())
        return {
            "key": stream,
            "title": spec["title"],
            "subtitle": spec["subtitle"],
            "time_header": spec["time_header"],
            "meta_header": spec["meta_header"],
            "stages": [
                {
                    "key": stage["key"],
                    "label": stage["label"],
                    "count": stage_counts.get(stage["key"], 0),
                    "tone": stage["tone"],
                }
                for stage in spec["stages"]
            ],
            "rows": rows,
            "done_count": done_count,
            "done_percent": int(round((done_count * 100.0 / total), 0)) if total else 0,
            "total": total,
            "stage_counts": stage_counts,
            "alerts": alerts,
            "action": self._ops_action(spec["action_name"], spec["list_domain"](warehouse, stock)),
            "buckets": self._ops_done_buckets(pickings, tz),
        }

    def _ops_stream_spec(self, stream):
        if stream == "receipt":
            return {
                "title": "1. การรับสินค้า",
                "subtitle": "จากผู้ขายเข้าคลัง ตามใบสั่งซื้อ",
                "time_header": "เวลา",
                "meta_header": "ผู้ขาย / PO",
                "done_key": "done",
                "action_name": "ใบรับสินค้า",
                "stages": [
                    {"key": "waiting_truck", "label": "รอรถมา", "tone": "gray"},
                    {"key": "receiving", "label": "ตรวจรับ", "tone": "orange"},
                    {"key": "qc", "label": "QC", "tone": "blue"},
                    {"key": "putaway", "label": "จัดเก็บ", "tone": "green"},
                    {"key": "done", "label": "เสร็จสิ้น", "tone": "outline"},
                ],
                "list_domain": lambda warehouse, stock: [
                    ("picking_type_id.warehouse_id", "=", warehouse.id),
                    ("picking_type_code", "=", "incoming"),
                    ("state", "!=", "cancel"),
                ],
            }
        if stream == "transfer":
            return {
                "title": "2. การโอนสินค้า",
                "subtitle": "ระหว่างคลัง ต้นทางหรือปลายทางเป็นคลังนี้",
                "time_header": "กำหนดถึง",
                "meta_header": "ต้นทาง → ปลายทาง",
                "done_key": "done",
                "action_name": "โอนสินค้า",
                "stages": [
                    {"key": "draft", "label": "สร้างใบโอน", "tone": "gray"},
                    {"key": "picking", "label": "จัดสินค้า", "tone": "orange"},
                    {"key": "shipping", "label": "ขนส่ง", "tone": "blue"},
                    {"key": "waiting_receive", "label": "รอรับ", "tone": "green"},
                    {"key": "done", "label": "รับแล้ว", "tone": "outline"},
                ],
                "list_domain": lambda warehouse, stock: [
                    ("picking_type_code", "=", "internal"),
                    ("state", "!=", "cancel"),
                    "|",
                    ("location_id", "child_of", stock.id),
                    ("location_dest_id", "child_of", stock.id),
                ],
            }
        return {
            "title": "3. การเบิกใช้ภายใน",
            "subtitle": "จ่ายออกจากคลังนี้ ให้หน่วยงานหรือตัดใช้",
            "time_header": "รอนานแล้ว",
            "meta_header": "หน่วยงาน",
            "done_key": "done",
            "action_name": "เบิกใช้ภายใน",
            "stages": [
                {"key": "approve", "label": "รออนุมัติ", "tone": "orange"},
                {"key": "wait_pick", "label": "รอจัด", "tone": "gray"},
                {"key": "picking", "label": "กำลังจัด", "tone": "blue"},
                {"key": "ready", "label": "พร้อมรับ", "tone": "green"},
                {"key": "done", "label": "จ่ายแล้ว", "tone": "outline"},
            ],
            "list_domain": lambda warehouse, stock: [
                ("picking_type_code", "=", "outgoing"),
                ("location_id", "child_of", stock.id),
                ("state", "!=", "cancel"),
            ],
        }

    def _ops_classify(self, stream, picking, stock, has_qc, day_end_utc):
        if stream == "receipt":
            qc_state = picking.qc_state if has_qc else False
            if picking.state == "done":
                return "done", "จัดเก็บแล้ว", "green"
            if qc_state == "failed":
                return "qc", "QC ไม่ผ่าน", "red"
            if qc_state == "draft":
                return "qc", "กำลังตรวจ QC", "blue"
            if qc_state == "passed":
                return "putaway", "รอจัดเก็บ", "green"
            if picking.state in ("draft", "waiting", "confirmed"):
                return "waiting_truck", "รอรถมา", "gray"
            scheduled = picking.scheduled_date
            if scheduled and scheduled > day_end_utc:
                return "waiting_truck", "รอรถมา", "gray"
            return "receiving", "กำลังตรวจรับ", "orange"
        if stream == "transfer":
            if picking.state == "done":
                return "done", "รับครบแล้ว", "green"
            if picking.state == "draft":
                return "draft", "สร้างใบโอน", "gray"
            if picking.state in ("waiting", "confirmed"):
                return "picking", "กำลังจัดสินค้า", "orange"
            dest_here = self._ops_under(picking.location_dest_id, stock)
            source_here = self._ops_under(picking.location_id, stock)
            if dest_here and not source_here:
                return "waiting_receive", "รอรับปลายทาง", "green"
            return "shipping", "ระหว่างขนส่ง", "blue"
        if picking.state == "done":
            return "done", "จ่ายแล้ว", "green"
        if picking.state == "draft":
            return "approve", "รออนุมัติ", "orange"
        if picking.state == "waiting":
            return "wait_pick", "รอจัด", "gray"
        if picking.state == "confirmed":
            return "picking", "กำลังจัด", "blue"
        return "ready", "พร้อมรับ", "green"

    def _ops_meta(self, stream, picking):
        if stream == "receipt":
            partner = picking.partner_id.name or "ไม่ระบุผู้ขาย"
            origin = picking.origin or ""
            return "%s · %s" % (partner, origin) if origin else partner
        if stream == "transfer":
            return "%s → %s" % (
                self._ops_point_label(picking.location_id),
                self._ops_point_label(picking.location_dest_id),
            )
        partner = picking.partner_id.name
        if partner:
            return partner
        origin = picking.origin or ""
        dest = picking.location_dest_id.name or ""
        if origin and dest:
            return "%s · %s" % (dest, origin)
        return origin or dest or "-"

    def _ops_route(self, stream, picking):
        if stream == "transfer":
            return self._ops_meta(stream, picking)
        return picking.origin or picking.partner_id.name or ""

    def _ops_point_label(self, location):
        warehouse = location.warehouse_id
        if warehouse and warehouse.code:
            return warehouse.code
        if warehouse:
            return warehouse.name
        return location.name or "-"

    def _ops_under(self, location, stock):
        if not location or not stock:
            return False
        return location.id == stock.id or location.parent_path.startswith(stock.parent_path)

    def _ops_row_time(self, stream, picking, tz, now_utc):
        if stream == "issue" and picking.state in OPEN_STATES:
            anchor = picking.scheduled_date or picking.create_date
            return self._ops_age_label(anchor, now_utc)
        moment = picking.date_done if picking.state == "done" else picking.scheduled_date
        local = self._ops_local(moment, tz)
        if not local:
            return "-"
        return local.strftime("%H:%M")

    def _ops_late_minutes(self, picking, now_utc):
        if picking.state not in OPEN_STATES or not picking.scheduled_date:
            return 0
        delta = now_utc - picking.scheduled_date
        minutes = int(delta.total_seconds() // 60)
        return minutes if minutes > 0 else 0

    def _ops_alert(self, stream, picking, stock, late_minutes, now_utc, has_qc):
        age = self._ops_age_label(picking.scheduled_date or picking.create_date, now_utc)
        qc_failed = has_qc and stream == "receipt" and picking.qc_state == "failed"
        dest_here = self._ops_under(picking.location_dest_id, stock)
        source_here = self._ops_under(picking.location_id, stock)
        if qc_failed:
            message = "QC ไม่ผ่าน ยังบันทึกรับไม่ได้"
        elif stream == "receipt":
            message = "ถึงกำหนดรับแล้ว %s" % age
        elif stream == "transfer" and dest_here and not source_here:
            message = "รอรับปลายทางเกินกำหนด %s" % age
        elif stream == "transfer":
            message = "ยังโอนไม่เสร็จ เกินกำหนด %s" % age
        else:
            message = "รอจ่ายเกินกำหนด %s" % age
        labels = {"receipt": "รับ", "transfer": "โอน", "issue": "เบิก"}
        return {
            "id": picking.id,
            "model": "stock.picking",
            "stream": stream,
            "name": picking.name,
            "message": message,
            "detail": self._ops_meta(stream, picking),
            "action_label": labels[stream],
            "late_minutes": late_minutes or 1,
        }

    def _ops_done_buckets(self, pickings, tz):
        buckets = {}
        for picking in pickings.filtered(lambda item: item.state == "done" and item.date_done):
            local = self._ops_local(picking.date_done, tz)
            hour_key = local.strftime("%Y-%m-%d %H")
            day_key = "day:" + local.strftime("%Y-%m-%d")
            buckets[hour_key] = buckets.get(hour_key, 0) + 1
            buckets[day_key] = buckets.get(day_key, 0) + 1
        return buckets

    def _ops_chart(self, period, start_local, now_local, columns, tz):
        groups = []
        if period == "today":
            last_hour = min(max(now_local.hour, 8), 18)
            cursor = start_local.replace(hour=8, minute=0, second=0, microsecond=0)
            while cursor.hour <= last_hour:
                groups.append((cursor.strftime("%H:00"), cursor.strftime("%Y-%m-%d %H"), False))
                cursor += timedelta(hours=1)
                if cursor.hour == 0:
                    break
            title = "ใบงานที่เสร็จ ต่อชั่วโมง"
        else:
            cursor = start_local
            while cursor.date() <= now_local.date():
                groups.append(
                    (
                        "%s %s" % (cursor.day, THAI_MONTHS[cursor.month]),
                        "day:" + cursor.strftime("%Y-%m-%d"),
                        True,
                    )
                )
                cursor += timedelta(days=1)
            title = "ใบงานที่เสร็จ ต่อวัน"
        payload_groups = []
        max_value = 1
        for label, key, _is_day in groups:
            bars = []
            for column in columns:
                value = column["buckets"].get(key, 0)
                bars.append({"key": column["key"], "value": value})
                max_value = max(max_value, value)
            payload_groups.append({"label": label, "bars": bars})
        for group in payload_groups:
            for bar in group["bars"]:
                bar["height"] = int(round(bar["value"] * 100 / max_value)) if bar["value"] else 0
        for column in columns:
            column.pop("buckets", None)
            column.pop("stage_counts", None)
        return {
            "title": title,
            "max": max_value,
            "groups": payload_groups,
            "series": [
                {"key": "receipt", "label": "รับสินค้า", "color": "#3E67C5"},
                {"key": "transfer", "label": "โอนสินค้า", "color": "#1E2A44"},
                {"key": "issue", "label": "เบิกใช้ภายใน", "color": "#E59A3A"},
            ],
        }

    def _ops_kpi(self, key, label, hint, column, foot, tone):
        return {
            "key": key,
            "label": label,
            "hint": hint,
            "value": column["total"],
            "progress": column["done_percent"],
            "foot": foot,
            "tone": tone,
        }

    def _ops_action(self, name, domain):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "stock.picking",
            "view_mode": "list,kanban,form",
            "views": [[False, "list"], [False, "kanban"], [False, "form"]],
            "domain": domain,
            "target": "current",
        }

    def _ops_empty_payload(self, period, now_local, warehouses, warehouse):
        return {
            "period": period if period in ("today", "7d", "30d") else "today",
            "date_label": self._ops_thai_date(now_local),
            "updated_at": now_local.strftime("%H:%M"),
            "warehouse_id": warehouse.id if warehouse else False,
            "warehouse_label": "",
            "warehouses": [
                {"id": wh.id, "name": wh.name, "code": wh.code or "", "label": "%s (%s)" % (wh.name, wh.code or "-")}
                for wh in warehouses
            ],
            "kpis": [],
            "columns": [],
            "chart": {"title": "", "max": 1, "groups": [], "series": []},
            "alerts": [],
            "alert_count": 0,
        }

    def _ops_tz(self):
        name = self.env.user.tz or "Asia/Bangkok"
        try:
            return ZoneInfo(name)
        except Exception:
            return ZoneInfo("Asia/Bangkok")

    def _ops_period_bounds(self, period, now_local):
        end_local = now_local.replace(hour=23, minute=59, second=59, microsecond=0)
        if period == "7d":
            start_local = (now_local - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "30d":
            start_local = (now_local - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_local, end_local

    def _ops_naive_utc(self, moment):
        return moment.astimezone(timezone.utc).replace(tzinfo=None)

    def _ops_local(self, moment, tz):
        if not moment:
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(tz)

    def _ops_thai_date(self, moment):
        weekday = THAI_WEEKDAYS[moment.weekday()]
        return "%s %s %s %s" % (weekday, moment.day, THAI_MONTHS[moment.month], moment.year + 543)

    def _ops_age_label(self, anchor, now_utc):
        if not anchor:
            return ""
        minutes = int((now_utc - anchor).total_seconds() // 60)
        if minutes < 1:
            return "เมื่อสักครู่"
        if minutes < 60:
            return "%s นาที" % minutes
        hours = minutes // 60
        mins = minutes % 60
        if hours < 24:
            if mins:
                return "%s ชม. %s น." % (hours, mins)
            return "%s ชม." % hours
        days = hours // 24
        hours_left = hours % 24
        if hours_left:
            return "%s วัน %s ชม." % (days, hours_left)
        return "%s วัน" % days
