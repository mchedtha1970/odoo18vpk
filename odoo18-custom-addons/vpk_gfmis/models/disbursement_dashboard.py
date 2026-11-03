# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo import api, fields, models

STAGES = [
    ("draft", "ร่างใบเบิก"),
    ("wait_approve_request", "รออนุมัติขอเบิก"),
    ("wait_approve_pay", "รออนุมัติสั่งจ่าย"),
    ("sent_treasury", "ส่งกรมบัญชีกลาง"),
    ("paid", "จ่ายแล้ว"),
]
STAGE_INDEX = {key: index for index, (key, _label) in enumerate(STAGES)}
PAID_STATES = ("paid", "agency_paid")
APPROVE_STATES = ("wait_approve_request", "wait_approve_pay")
PROGRESS_STATES = (
    "wait_approve_request",
    "wait_approve_pay",
    "sent_treasury",
    "wait_agency_pay",
)
THAI_MONTHS = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]
THAI_MONTHS_LONG = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


class GfmisDisbursementDashboard(models.Model):
    _inherit = "gfmis.document"

    @api.model
    def get_disbursement_dashboard_data(self, fiscal_year=None):
        today = fields.Date.context_today(self)
        current_year = self._pay_fiscal_year(today)
        years = self._pay_year_options(current_year)
        fiscal_year = fiscal_year or current_year
        if fiscal_year not in years:
            years.insert(0, fiscal_year)
        period_start, period_end = self._pay_period(fiscal_year)

        documents = self.search(
            [
                ("doc_class", "=", "request"),
                ("document_date", ">=", period_start),
                ("document_date", "<=", period_end),
            ],
            order="document_date desc, id desc",
        )
        active = documents.filtered(lambda rec: rec.state != "cancelled")
        waiting_orders = self._pay_waiting_orders(period_start, period_end)

        stage_counts = {key: 0 for key, _label in STAGES}
        stage_amounts = {key: 0.0 for key, _label in STAGES}
        for rec in active:
            key = self._pay_stage_key(rec.state)
            stage_counts[key] += 1
            stage_amounts[key] += rec.amount_untaxed or 0.0

        max_stage = max(stage_counts.values() or [1]) or 1
        quarters = [
            {"label": "ไตรมาส %s" % (index + 1), "request": 0.0, "paid": 0.0}
            for index in range(4)
        ]
        for rec in active:
            index = self._pay_quarter(rec.document_date, period_start)
            if index is None:
                continue
            quarters[index]["request"] += rec.amount_untaxed or 0.0
            if rec.state in PAID_STATES:
                quarters[index]["paid"] += rec.amount_net or 0.0
        quarter_max = max(
            [item["request"] for item in quarters] + [item["paid"] for item in quarters] + [1]
        )

        methods = {
            "direct": {"key": "direct", "label": "จ่ายตรงผู้ขาย", "count": 0, "amount": 0.0},
            "through": {"key": "through", "label": "จ่ายผ่านส่วนราชการ", "count": 0, "amount": 0.0},
        }
        for rec in active:
            method = rec.payment_method if rec.payment_method in methods else "direct"
            methods[method]["count"] += 1
            methods[method]["amount"] += rec.amount_untaxed or 0.0
        method_max = max([item["amount"] for item in methods.values()] + [1])
        method_rows = [
            dict(item, width=round((item["amount"] / method_max) * 100, 1))
            for item in methods.values()
        ]

        amount_total = sum(active.mapped("amount_untaxed"))
        amount_net = sum(active.mapped("amount_net"))
        amount_wht = sum(active.mapped("amount_wht"))
        amount_paid = sum(
            rec.amount_net for rec in active if rec.state in PAID_STATES
        )
        in_progress = active.filtered(lambda rec: rec.state in PROGRESS_STATES)
        waiting_approve = active.filtered(lambda rec: rec.state in APPROVE_STATES)
        paid_docs = active.filtered(lambda rec: rec.state in PAID_STATES)
        paid_pct = (amount_paid / amount_net * 100.0) if amount_net else 0.0

        alerts = []
        if waiting_orders:
            alerts.append(
                {
                    "tone": "progress",
                    "text": "รอสร้างใบเบิกเงิน %s ใบสั่งซื้อที่ยืนยันแล้ว" % len(waiting_orders),
                }
            )
        wait_am01 = len(active.filtered(lambda rec: rec.state == "wait_approve_request"))
        wait_am02 = len(active.filtered(lambda rec: rec.state == "wait_approve_pay"))
        sent = len(active.filtered(lambda rec: rec.state in ("sent_treasury", "wait_agency_pay")))
        if wait_am01:
            alerts.append({"tone": "approve", "text": "รออนุมัติขอเบิก (อม.01) %s รายการ" % wait_am01})
        if wait_am02:
            alerts.append({"tone": "approve", "text": "รออนุมัติสั่งจ่าย (อม.02) %s รายการ" % wait_am02})
        if sent:
            alerts.append({"tone": "late", "text": "ส่งกรมบัญชีกลางแล้วยังไม่จ่าย %s รายการ" % sent})
        if not alerts:
            alerts.append({"tone": "progress", "text": "ไม่มีรายการค้างดำเนินการในขณะนี้"})

        return {
            "fiscal_year": fiscal_year,
            "year_options": years,
            "as_of_label": "ข้อมูล ณ วันที่ %s %s %s" % (
                today.day,
                THAI_MONTHS_LONG[today.month - 1],
                today.year + 543,
            ),
            "kpis": {
                "total": len(active),
                "amount": amount_total,
                "net": amount_net,
                "wht": amount_wht,
                "in_progress": len(in_progress),
                "waiting_approve": len(waiting_approve),
                "waiting_create": len(waiting_orders),
                "paid_count": len(paid_docs),
                "paid_amount": amount_paid,
                "paid_pct": paid_pct,
            },
            "stages": [
                {
                    "key": key,
                    "label": label,
                    "count": stage_counts[key],
                    "amount": stage_amounts[key],
                    "width": round((stage_counts[key] / max_stage) * 100, 1),
                }
                for key, label in STAGES
            ],
            "quarters": quarters,
            "quarter_max": quarter_max,
            "methods": method_rows,
            "alerts": alerts,
            "documents": [self._pay_document_row(rec) for rec in documents],
            "waiting": [self._pay_waiting_row(order) for order in waiting_orders[:50]],
            "open_stage_count": len(active.filtered(lambda rec: rec.state not in PAID_STATES)),
        }

    @api.model
    def _pay_stage_key(self, state):
        if state in PAID_STATES:
            return "paid"
        if state == "wait_agency_pay":
            return "sent_treasury"
        if state == "recorded":
            return "wait_approve_request"
        if state in STAGE_INDEX:
            return state
        return "draft"

    @api.model
    def _pay_status(self, state):
        labels = dict(self._fields["state"].selection)
        if state in PAID_STATES:
            return "done", labels.get(state) or "จ่ายแล้ว"
        if state in APPROVE_STATES:
            return "approve", labels.get(state)
        if state == "cancelled":
            return "cancel", "ยกเลิก"
        if state == "returned":
            return "return", "เบิกเกินส่งคืน"
        if state == "draft":
            return "draft", "ร่าง"
        return "progress", labels.get(state) or state

    def _pay_document_row(self, rec):
        status_key, status_label = self._pay_status(rec.state)
        stage_key = self._pay_stage_key(rec.state)
        return {
            "id": rec.id,
            "name": rec.name,
            "po_id": rec.purchase_id.id or False,
            "po_name": rec.purchase_id.name or "—",
            "vendor": rec.partner_id.name or "—",
            "form": rec.form_code or "—",
            "reference": rec.reference or rec.dika_number or "—",
            "amount": rec.amount_untaxed or 0.0,
            "wht": rec.amount_wht or 0.0,
            "net": rec.amount_net or 0.0,
            "state": rec.state,
            "stage_index": STAGE_INDEX.get(stage_key, 0),
            "status_key": status_key,
            "status_label": status_label,
            "date": self._pay_thai_date(rec.document_date),
            "method": dict(rec._fields["payment_method"].selection).get(rec.payment_method) or "—",
        }

    @api.model
    def _pay_waiting_row(self, order):
        wa_name = "—"
        if "wa_ids" in order._fields:
            wa = order.wa_ids.filtered(lambda rec: rec.state != "cancel")[:1]
            wa_name = wa.name or "—"
        return {
            "id": order.id,
            "name": order.name,
            "vendor": order.partner_id.name or "—",
            "amount": order.amount_untaxed or 0.0,
            "wa_name": wa_name,
            "date": self._pay_thai_date(order.date_approve or order.date_order),
        }

    @api.model
    def _pay_waiting_orders(self, period_start, period_end):
        period_until = period_end + timedelta(days=1)
        orders = self.env["purchase.order"].search(
            [
                ("state", "in", ("purchase", "done")),
                "|",
                "&",
                ("date_approve", ">=", period_start),
                ("date_approve", "<", period_until),
                "&",
                "&",
                ("date_approve", "=", False),
                ("date_order", ">=", period_start),
                ("date_order", "<", period_until),
            ],
            order="date_approve desc, id desc",
        )
        linked = self.search(
            [
                ("purchase_id", "in", orders.ids),
                ("doc_class", "=", "request"),
                ("state", "!=", "cancelled"),
            ]
        ).mapped("purchase_id")
        return orders - linked

    @api.model
    def _pay_thai_date(self, value):
        if not value:
            return "—"
        day = value.date() if hasattr(value, "date") else value
        return "%s %s %s" % (day.day, THAI_MONTHS[day.month - 1], str(day.year + 543)[-2:])

    @api.model
    def _pay_fiscal_year(self, day):
        end_year = day.year + 1 if day.month >= 10 else day.year
        return str(end_year + 543)

    @api.model
    def _pay_period(self, fiscal_year):
        ce = int(fiscal_year) - 543
        return date(ce - 1, 10, 1), date(ce, 9, 30)

    @api.model
    def _pay_quarter(self, day, period_start):
        if not day:
            return None
        index = (day.year - period_start.year) * 12 + day.month - period_start.month
        if 0 <= index <= 11:
            return index // 3
        return None

    @api.model
    def _pay_year_options(self, current_year):
        years = {current_year}
        for day in self.search([("doc_class", "=", "request")]).mapped("document_date"):
            if day:
                years.add(self._pay_fiscal_year(day))
        return sorted(years, reverse=True)
