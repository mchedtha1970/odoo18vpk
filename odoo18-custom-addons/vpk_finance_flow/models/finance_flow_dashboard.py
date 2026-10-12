# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.misc import formatLang

TZ = ZoneInfo("Asia/Bangkok")
MONTHS = (
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
OPEN_BILL_STATES = ("not_paid", "partial", "in_payment")
BILL_STATUS = {
    "not_paid": "รอจ่าย",
    "partial": "จ่ายบางส่วน",
    "in_payment": "กำลังจ่าย",
    "paid": "จ่ายแล้ว",
    "reversed": "กลับรายการ",
}
PAYMENT_STATUS = {
    "draft": "ร่าง",
    "in_process": "กำลังจ่าย",
    "paid": "จ่ายแล้ว",
    "canceled": "ยกเลิก",
    "rejected": "ถูกปฏิเสธ",
}
APPROVAL_STATES = ("wait_approve_request", "wait_approve_pay")
TREASURY_STATES = ("sent_treasury", "wait_agency_pay")
CLOSED_GFMIS = ("paid", "agency_paid", "returned", "cancelled")


class AccountMoveFinanceFlow(models.Model):
    _inherit = "account.move"

    @api.model
    def get_finance_flow_dashboard(self, period="7d"):
        """งานค้างและความเคลื่อนไหวของเจ้าหนี้ การเงิน และบัญชี"""
        period = period if period in ("today", "7d", "30d") else "7d"
        now_local, start_utc = self._flow_bounds(period)
        company = self.env.company
        company_domain = [("company_id", "=", company.id)]
        bills = self.env["account.move"]
        payments = self.env["account.payment"]
        leaves = self.env["vpk.bank.cheque.leaf"]
        gfmis = self._flow_gfmis()

        bill_base = company_domain + [
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("state", "!=", "cancel"),
        ]
        open_bills = bill_base + [("payment_state", "in", list(OPEN_BILL_STATES))]
        draft_bills = bill_base + [("state", "=", "draft")]
        waiting_bills = bill_base + [
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
        ]
        paying_bills = bill_base + [
            ("state", "=", "posted"),
            ("payment_state", "=", "in_payment"),
        ]
        overdue_bills = bill_base + [
            ("state", "=", "posted"),
            ("payment_state", "in", list(OPEN_BILL_STATES)),
            ("invoice_date_due", "!=", False),
            ("invoice_date_due", "<", fields.Date.context_today(self)),
        ]
        no_gfmis_bills = bill_base + [
            ("state", "=", "posted"),
            ("payment_state", "in", list(OPEN_BILL_STATES)),
            ("gfmis_document_ids", "=", False),
        ]

        pay_base = company_domain + [("payment_type", "=", "outbound")]
        draft_payments = pay_base + [("state", "=", "draft")]
        process_payments = pay_base + [("state", "=", "in_process")]
        paid_payments = pay_base + [("state", "=", "paid"), ("write_date", ">=", start_utc)]

        printed_leaves = leaves.search([("state", "=", "printed")])
        open_leaves = printed_leaves.filtered(
            lambda leaf: not leaf.payment_id or leaf.payment_id.state != "paid"
        )

        gfmis_base = company_domain
        draft_gfmis = gfmis_base + [("state", "=", "draft")]
        approval_gfmis = gfmis_base + [("state", "in", list(APPROVAL_STATES))]
        treasury_gfmis = gfmis_base + [("state", "in", list(TREASURY_STATES))]
        missing_transfer = gfmis_base + [
            ("state", "not in", ("draft", "cancelled")),
            ("transfer_date", "=", False),
        ]
        account_attention = [
            ("company_id", "=", company.id),
            ("state", "not in", ("cancelled", "returned")),
            "|",
            ("state", "not in", ("paid", "agency_paid")),
            ("transfer_date", "=", False),
        ]
        draft_entries = company_domain + [("move_type", "=", "entry"), ("state", "=", "draft")]

        ap_rows = bills.search(open_bills, order="write_date desc, id desc", limit=8)
        pay_rows = payments.search(
            pay_base + [("state", "in", ("draft", "in_process"))],
            order="write_date desc, id desc",
            limit=8,
        )
        gfmis_rows = self.env["gfmis.document"].browse()
        if gfmis is not False:
            try:
                gfmis_rows = gfmis.search([
                    ("company_id", "=", company.id),
                    "|",
                    ("state", "not in", list(CLOSED_GFMIS)),
                    "&", "&",
                    ("state", "not in", ("draft", "cancelled")),
                    ("transfer_date", "=", False),
                    ("state", "!=", "returned"),
                ], order="write_date desc, id desc", limit=8)
            except AccessError:
                gfmis_rows = gfmis.browse()

        columns = [
            self._flow_column(
                "ap",
                "เจ้าหนี้",
                "ใบแจ้งหนี้ผู้ขายที่ยังไม่ปิด",
                "คู่ค้า",
                [
                    self._flow_stage("draft", "ร่าง", bills.search_count(draft_bills), "blue", "ใบแจ้งหนี้ร่าง", bills, draft_bills),
                    self._flow_stage("waiting", "รอจ่าย", bills.search_count(waiting_bills), "orange", "ตั้งหนี้แล้ว รอจ่าย", bills, waiting_bills),
                    self._flow_stage("paying", "กำลังจ่าย", bills.search_count(paying_bills), "blue", "จ่ายแล้ว รอบัญชีตัด", bills, paying_bills),
                    self._flow_stage("overdue", "เกินกำหนด", bills.search_count(overdue_bills), "red", "ใบแจ้งหนี้เกินกำหนด", bills, overdue_bills),
                    self._flow_stage("no_gfmis", "ยังไม่ขอเบิก", bills.search_count(no_gfmis_bills), "orange", "ตั้งหนี้แล้ว ยังไม่มีเอกสาร GFMIS", bills, no_gfmis_bills),
                ],
                [self._flow_bill_row(bill, now_local) for bill in ap_rows],
                self._flow_action("ใบแจ้งหนี้ที่ยังไม่ปิด", "account.move", open_bills),
            ),
            self._flow_column(
                "finance",
                "การเงิน",
                "ใบจ่ายและเช็คที่ยังไม่ขึ้นเงิน",
                "ผู้รับเงิน",
                [
                    self._flow_stage("draft", "ใบจ่ายร่าง", payments.search_count(draft_payments), "blue", "ใบจ่ายที่ยังไม่ยืนยัน", payments, draft_payments),
                    self._flow_stage("process", "กำลังจ่าย", payments.search_count(process_payments), "orange", "จ่ายแล้ว ยังไม่ตัดบัญชี", payments, process_payments),
                    self._flow_stage("cheque", "เช็คพิมพ์แล้ว", len(open_leaves), "orange", "เช็คที่พิมพ์แล้วยังไม่ขึ้นเงิน", leaves, [("id", "in", open_leaves.ids)]),
                    self._flow_stage("paid", "จ่ายแล้ว", payments.search_count(paid_payments), "green", "จ่ายครบในช่วงนี้", payments, paid_payments),
                ],
                self._flow_finance_rows(pay_rows, open_leaves, now_local),
                self._flow_action("ใบจ่ายที่ยังไม่ปิด", "account.payment", pay_base + [("state", "in", ("draft", "in_process"))]),
            ),
            self._flow_column(
                "account",
                "บัญชี",
                "ขอเบิก GFMIS และรายการที่ยังไม่ผ่าน",
                "ผู้รับเงิน",
                [
                    self._flow_stage("draft", "ขอเบิกร่าง", self._flow_count(gfmis, draft_gfmis), "blue", "เอกสาร GFMIS ร่าง", gfmis, draft_gfmis),
                    self._flow_stage("approval", "รออนุมัติ", self._flow_count(gfmis, approval_gfmis), "orange", "รออนุมัติขอเบิกหรือสั่งจ่าย", gfmis, approval_gfmis),
                    self._flow_stage("treasury", "ส่งคลัง", self._flow_count(gfmis, treasury_gfmis), "blue", "ส่งคลังหรือรอจ่ายผู้มีสิทธิ", gfmis, treasury_gfmis),
                    self._flow_stage("transfer", "ยังไม่ลงวันที่โอน", self._flow_count(gfmis, missing_transfer), "orange", "ยังไม่ได้ลงวันที่โอน", gfmis, missing_transfer),
                    self._flow_stage("entry", "บัญชียังไม่ผ่าน", bills.search_count(draft_entries), "red", "รายการบัญชียังไม่ผ่านรายการ", bills, draft_entries),
                ],
                [self._flow_gfmis_row(doc, now_local) for doc in gfmis_rows],
                self._flow_action("เอกสาร GFMIS ที่ยังต้องติดตาม", "gfmis.document", account_attention) if gfmis is not False else False,
            ),
        ]

        open_ap_bills = bills.search(open_bills)
        open_ap = len(open_ap_bills)
        open_finance = payments.search_count(pay_base + [("state", "in", ("draft", "in_process"))]) + len(open_leaves)
        open_account = self._flow_count(gfmis, account_attention) + bills.search_count(draft_entries)
        residual = sum(open_ap_bills.mapped("amount_total"))
        process_amount = sum(payments.search(process_payments).mapped("amount"))
        movement = self._flow_movement(bills, payments, gfmis, start_utc, now_local)
        alerts = self._flow_alerts(
            bills, payments, open_leaves, gfmis,
            overdue_bills, process_payments, no_gfmis_bills, approval_gfmis, missing_transfer,
            now_local,
        )
        period_label = {"today": "วันนี้", "7d": "7 วัน", "30d": "30 วัน"}[period]
        return {
            "period": period,
            "date_label": self._flow_thai_date(now_local),
            "updated_at": now_local.strftime("%H:%M"),
            "kpis": [
                self._flow_kpi("ap", "เจ้าหนี้ค้าง", open_ap, "ใบ", "ยอดใบแจ้งหนี้ %s" % self._flow_money(residual), "alert" if open_ap else "green"),
                self._flow_kpi("finance", "การเงินค้าง", open_finance, "รายการ", "กำลังจ่าย %s" % self._flow_money(process_amount), "alert" if open_finance else "green"),
                self._flow_kpi("account", "บัญชีค้าง", open_account, "เรื่อง", "ขอเบิกและรายการที่ยังไม่ปิด", "alert" if open_account else "green"),
                self._flow_kpi("moved", "ขยับในช่วงนี้", len(movement), "รายการ", period_label, "blue"),
            ],
            "flow": [
                self._flow_step("รับวางบิล", bills.search_count(draft_bills), self._flow_action("ใบแจ้งหนี้ร่าง", "account.move", draft_bills)),
                self._flow_step("ตั้งหนี้รอจ่าย", bills.search_count(waiting_bills) + bills.search_count(paying_bills), self._flow_action("ตั้งหนี้แล้วยังไม่ปิด", "account.move", open_bills + [("state", "=", "posted")])),
                self._flow_step("ขอเบิก", self._flow_count(gfmis, draft_gfmis) + self._flow_count(gfmis, gfmis_base + [("state", "=", "recorded")]), self._flow_action("ขอเบิกที่ยังไม่อนุมัติ", "gfmis.document", gfmis_base + [("state", "in", ("draft", "recorded"))])),
                self._flow_step("รออนุมัติ", self._flow_count(gfmis, approval_gfmis) + self._flow_count(gfmis, treasury_gfmis), self._flow_action("รออนุมัติหรือส่งคลัง", "gfmis.document", gfmis_base + [("state", "in", list(APPROVAL_STATES + TREASURY_STATES))])),
                self._flow_step("การเงินจ่าย", payments.search_count(pay_base + [("state", "in", ("draft", "in_process"))]), self._flow_action("ใบจ่ายที่ยังไม่ปิด", "account.payment", pay_base + [("state", "in", ("draft", "in_process"))])),
                self._flow_step("เช็คยังไม่ขึ้นเงิน", len(open_leaves), self._flow_action("เช็คที่พิมพ์แล้ว", "vpk.bank.cheque.leaf", [("id", "in", open_leaves.ids or [0])])),
            ],
            "columns": columns,
            "movement": movement,
            "alerts": alerts,
            "alert_count": len(alerts),
        }

    def _flow_gfmis(self):
        if "gfmis.document" not in self.env:
            return False
        return self.env["gfmis.document"]

    def _flow_count(self, model, domain):
        if model is False or model is None:
            return 0
        try:
            return model.search_count(domain)
        except AccessError:
            return 0

    def _flow_bounds(self, period):
        now_local = datetime.now(TZ)
        days = {"today": 0, "7d": 6, "30d": 29}[period]
        start_local = (now_local - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        return now_local, start_utc

    def _flow_thai_date(self, value):
        return "%s %s %s" % (value.day, MONTHS[value.month], value.year + 543)

    def _flow_when(self, value, now_local):
        if not value:
            return ""
        local = value.replace(tzinfo=timezone.utc).astimezone(TZ)
        if local.date() == now_local.date():
            return "วันนี้ %s" % local.strftime("%H:%M")
        return "%s %s %s" % (local.day, MONTHS[local.month], str(local.year + 543)[-2:])

    def _flow_money(self, amount):
        return formatLang(self.env, amount or 0.0, currency_obj=self.env.company.currency_id)

    def _flow_selection(self, record, field_name):
        field = record._fields[field_name]
        return dict(field._description_selection(self.env)).get(record[field_name], "")

    def _flow_action(self, name, model_name, domain):
        if not model_name:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model_name,
            "view_mode": "list,form",
            "views": [[False, "list"], [False, "form"]],
            "domain": domain,
            "target": "current",
        }

    def _flow_stage(self, key, label, count, tone, title, model, domain):
        model_name = False if model is False or model is None else model._name
        return {
            "key": key,
            "label": label,
            "count": count,
            "tone": tone if count else "gray",
            "action": self._flow_action(title, model_name, domain) if model_name else False,
        }

    def _flow_step(self, label, count, action):
        return {"label": label, "count": count, "action": action}

    def _flow_kpi(self, key, label, value, hint, foot, tone):
        return {
            "key": key,
            "label": label,
            "value": value,
            "hint": hint,
            "foot": foot,
            "tone": tone,
        }

    def _flow_column(self, key, title, subtitle, meta_header, stages, rows, action):
        return {
            "key": key,
            "title": title,
            "subtitle": subtitle,
            "meta_header": meta_header,
            "stages": stages,
            "rows": rows,
            "action": action,
        }

    def _flow_bill_row(self, bill, now_local):
        tone = "red" if bill.invoice_date_due and bill.invoice_date_due < fields.Date.context_today(self) and bill.payment_state in OPEN_BILL_STATES else "orange"
        if bill.state == "draft":
            tone = "blue"
        name = bill.name if bill.name and bill.name != "/" else "ร่าง"
        return {
            "id": bill.id,
            "model": "account.move",
            "name": name,
            "meta": bill.partner_id.name or "",
            "status": BILL_STATUS.get(bill.payment_state, "ร่าง") if bill.state == "posted" else "ร่าง",
            "tone": tone,
            "time": self._flow_money(bill.amount_residual or bill.amount_total),
            "when": self._flow_when(bill.write_date, now_local),
        }

    def _flow_payment_row(self, payment, now_local):
        return {
            "id": payment.id,
            "model": "account.payment",
            "name": payment.name or "ร่าง",
            "meta": payment.partner_id.name or "",
            "status": PAYMENT_STATUS.get(payment.state, self._flow_selection(payment, "state")),
            "tone": "orange" if payment.state == "in_process" else "blue",
            "time": self._flow_money(payment.amount),
            "when": self._flow_when(payment.write_date, now_local),
        }

    def _flow_cheque_row(self, leaf, now_local):
        return {
            "id": leaf.id,
            "model": "vpk.bank.cheque.leaf",
            "name": str(leaf.cheque_number),
            "meta": leaf.paid_to or leaf.partner_id.name or "",
            "status": "เช็คพิมพ์แล้ว",
            "tone": "orange",
            "time": self._flow_money(leaf.amount),
            "when": self._flow_when(leaf.write_date, now_local),
        }

    def _flow_gfmis_row(self, doc, now_local):
        tone = "orange" if doc.state in APPROVAL_STATES or not doc.transfer_date else "blue"
        if doc.state in ("paid", "agency_paid"):
            tone = "green" if doc.transfer_date else "orange"
        return {
            "id": doc.id,
            "model": "gfmis.document",
            "name": doc.name or "ร่าง",
            "meta": doc.partner_id.name or "",
            "status": self._flow_selection(doc, "state"),
            "tone": tone,
            "time": self._flow_money(doc.amount_net),
            "when": self._flow_when(doc.write_date, now_local),
        }

    def _flow_finance_rows(self, payments, leaves, now_local):
        stamped = [(payment.write_date, self._flow_payment_row(payment, now_local)) for payment in payments]
        stamped.extend((leaf.write_date, self._flow_cheque_row(leaf, now_local)) for leaf in leaves)
        stamped.sort(key=lambda item: item[0] or datetime.min, reverse=True)
        return [row for _stamp, row in stamped[:8]]

    def _flow_movement(self, bills, payments, gfmis, start_utc, now_local):
        company = [("company_id", "=", self.env.company.id), ("write_date", ">=", start_utc)]
        items = []
        for bill in bills.search(company + [("move_type", "in", ("in_invoice", "in_refund"))], order="write_date desc", limit=12):
            row = self._flow_bill_row(bill, now_local)
            row["desk"] = "เจ้าหนี้"
            items.append((bill.write_date, row))
        for payment in payments.search(company + [("payment_type", "=", "outbound")], order="write_date desc", limit=12):
            row = self._flow_payment_row(payment, now_local)
            row["desk"] = "การเงิน"
            items.append((payment.write_date, row))
        if gfmis is not False:
            try:
                docs = gfmis.search(company, order="write_date desc", limit=12)
            except AccessError:
                docs = gfmis.browse()
            for doc in docs:
                row = self._flow_gfmis_row(doc, now_local)
                row["desk"] = "บัญชี"
                items.append((doc.write_date, row))
        items.sort(key=lambda item: item[0] or datetime.min, reverse=True)
        rows = []
        seen = set()
        for _stamp, row in items:
            key = (row["model"], row["id"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
            if len(rows) == 8:
                break
        return rows

    def _flow_alerts(self, bills, payments, leaves, gfmis, overdue_domain, process_domain, no_gfmis_domain, approval_domain, transfer_domain, now_local):
        alerts = []
        for bill in bills.search(overdue_domain, order="invoice_date_due, id", limit=4):
            alerts.append(self._flow_alert(bill, "account.move", bill.name, "เกินกำหนดชำระ", bill.partner_id.name or "", "เปิดใบแจ้งหนี้"))
        for payment in payments.search(process_domain, order="date, id", limit=3):
            alerts.append(self._flow_alert(payment, "account.payment", payment.name, "จ่ายแล้วยังไม่ตัดบัญชี", payment.partner_id.name or "", "เปิดใบจ่าย"))
        for leaf in leaves[:3]:
            alerts.append(self._flow_alert(leaf, "vpk.bank.cheque.leaf", str(leaf.cheque_number), "เช็คพิมพ์แล้วยังไม่ขึ้นเงิน", leaf.paid_to or "", "เปิดใบเช็ค"))
        if gfmis is not False:
            try:
                pending = gfmis.search(approval_domain, order="write_date desc", limit=3)
                missing = gfmis.search(transfer_domain, order="write_date desc", limit=3)
            except AccessError:
                pending = missing = gfmis.browse()
            for doc in pending:
                alerts.append(self._flow_alert(doc, "gfmis.document", doc.name, self._flow_selection(doc, "state"), doc.partner_id.name or "", "เปิดขอเบิก"))
            for doc in missing:
                alerts.append(self._flow_alert(doc, "gfmis.document", doc.name, "ยังไม่ได้ลงวันที่โอน", doc.partner_id.name or "", "เปิดขอเบิก"))
        for bill in bills.search(no_gfmis_domain, order="invoice_date desc, id desc", limit=3):
            name = bill.name if bill.name and bill.name != "/" else "ร่าง"
            alerts.append(self._flow_alert(bill, "account.move", name, "ตั้งหนี้แล้ว ยังไม่ทำเรื่องเบิก", bill.partner_id.name or "", "เปิดใบแจ้งหนี้"))
        unique = []
        seen = set()
        for alert in alerts:
            key = (alert["model"], alert["id"], alert["message"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(alert)
            if len(unique) == 8:
                break
        return unique

    def _flow_alert(self, record, model_name, name, message, detail, action_label):
        return {
            "id": record.id,
            "model": model_name,
            "name": name or "",
            "message": message,
            "detail": detail or "",
            "action_label": action_label,
        }
