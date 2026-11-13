# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, models
from odoo.exceptions import UserError


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    def _vpk_find_disbursement_form(self):
        """หาใบขอเบิกเงินที่ผูกกับใบขออนุมัติเบิกจ่าย / ใบเรียกเก็บ."""
        self.ensure_one()
        Form = self.env["vpk.disbursement.form"].sudo()
        form = Form.search(
            [
                ("payment_request_id", "=", self.id),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )
        if form:
            return form
        bill = self.payment_bill_id
        if bill:
            return Form.search(
                [("invoice_id", "=", bill.id), ("state", "!=", "cancel")],
                limit=1,
            )
        return Form.browse()

    @api.model
    def get_payment_finance_dashboard(self):
        """เติมคอลัมน์ใบขอเบิกเงิน + สถานะลง Dashboard รอทำจ่าย."""
        data = super().get_payment_finance_dashboard()
        rows = data.get("rows") or []
        if not rows:
            return data

        Form = self.env["vpk.disbursement.form"].sudo()
        state_labels = dict(Form._fields["state"].selection)
        doc_ids = [row["id"] for row in rows]
        bill_ids = [row["bill_id"] for row in rows if row.get("bill_id")]

        forms = Form.search(
            [
                ("state", "!=", "cancel"),
                "|",
                ("payment_request_id", "in", doc_ids),
                ("invoice_id", "in", bill_ids or [0]),
            ]
        )
        by_request = {}
        by_bill = {}
        for form in forms:
            if form.payment_request_id:
                by_request.setdefault(form.payment_request_id.id, form)
            if form.invoice_id:
                by_bill.setdefault(form.invoice_id.id, form)

        for row in rows:
            form = by_request.get(row["id"]) or by_bill.get(row.get("bill_id") or 0)
            has_draft_pay = bool(row.get("draft_payment_id"))
            voucher_approved = row.get("memo_voucher_state") == "approved"
            is_non_gfmis = row.get("po_disbursement_type") == "non_gfmis"
            if form:
                row["kb_id"] = form.id
                row["kb_name"] = form.name or ""
                row["kb_state"] = form.state
                row["kb_state_label"] = state_labels.get(form.state, form.state)
                row["can_register_payment"] = (
                    form.state == "uploaded" or voucher_approved or is_non_gfmis
                ) and not has_draft_pay
            else:
                row["kb_id"] = False
                row["kb_name"] = ""
                row["kb_state"] = ""
                row["kb_state_label"] = "ยังไม่มีใบขอเบิกเงิน"
                row["can_register_payment"] = (
                    voucher_approved or is_non_gfmis
                ) and not has_draft_pay
        return data

    def action_open_register_payment(self):
        """ยืนยันรายการจ่ายได้เมื่อใบขอเบิกเงินอัปโหลดกรมบัญชีกลางแล้ว หรือใบสำคัญจ่ายอนุมัติแล้ว / ไม่ผ่าน GFMIS."""
        self.ensure_one()
        form = self._vpk_find_disbursement_form()
        po = self.purchase_id
        is_non_gfmis = bool(
            po
            and "egp_disbursement_type" in po._fields
            and po.egp_disbursement_type == "non_gfmis"
        )
        has_approved_voucher = False
        if "vpk.payment.voucher" in self.env and self.payment_bill_id:
            has_approved_voucher = bool(
                self.env["vpk.payment.voucher"]
                .sudo()
                .search_count(
                    [
                        ("bill_ids", "in", [self.payment_bill_id.id]),
                        ("state", "=", "approved"),
                    ]
                )
            )
        if not (
            (form and form.state == "uploaded")
            or is_non_gfmis
            or has_approved_voucher
        ):
            raise UserError(
                _(
                    "ยืนยันรายการจ่ายได้เมื่อใบขอเบิกเงินอัปโหลดเข้ากรมบัญชีกลางแล้ว หรือใบสำคัญจ่ายอนุมัติแล้วเท่านั้น"
                )
            )
        return super().action_open_register_payment()
