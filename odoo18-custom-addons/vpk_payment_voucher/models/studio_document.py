# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    from odoo.addons.vpk_document_studio_procurement.models.studio_document import (
        LINK_FIELDS,
    )
except ImportError:  # pragma: no cover
    LINK_FIELDS = {}

PAYMENT_VOUCHER_TYPE_CODES = ("payment_voucher", "ใบสำคัญจ่าย")

# Register link so create() from procurement sets payment_voucher_id from source_ref
LINK_FIELDS["vpk.payment.voucher"] = "payment_voucher_id"


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    payment_voucher_id = fields.Many2one(
        comodel_name="vpk.payment.voucher",
        string="ใบสำคัญจ่าย",
        index=True,
        ondelete="set null",
        copy=False,
    )

    @api.model
    def _extra_source_models(self):
        return super()._extra_source_models() + ["vpk.payment.voucher"]

    def _vpk_fill_links_from_sources(self):
        res = super()._vpk_fill_links_from_sources()
        for rec in self:
            if rec.payment_voucher_id or not rec.source_ref:
                continue
            source = rec._record_from_ref(rec.source_ref)
            if source and source._name == "vpk.payment.voucher":
                rec.sudo().write({"payment_voucher_id": source.id})
        return res

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._vpk_sync_payment_voucher_from_document_state()
        return res

    def _vpk_sync_payment_voucher_from_document_state(self):
        """ส่งลงนาม → ใบสำคัญจ่ายรออนุมัติ; ลงนามครบ → อนุมัติแล้วอัตโนมัติ."""
        for rec in self:
            voucher = rec.payment_voucher_id
            if not voucher or voucher.state == "cancel":
                continue
            target = False
            if rec.state == "to_approve" and voucher.state in ("draft", "to_approve"):
                target = "to_approve"
            elif rec.state == "approved" and voucher.state != "approved":
                target = "approved"
            elif (
                rec.state in ("draft", "generated")
                and voucher.state == "to_approve"
            ):
                # ตีกลับ / กลับเป็นร่าง เอกสาร → คืนใบสำคัญจ่ายเป็นร่าง
                target = "draft"
            if not target or voucher.state == target:
                continue
            voucher.sudo().write({"state": target})
            if target == "to_approve":
                voucher.message_post(
                    body=_("สถานะใบสำคัญจ่ายเปลี่ยนเป็นรออนุมัติ ตามการส่งลงนามเอกสาร %s")
                    % rec.display_name
                )
            elif target == "approved":
                voucher.message_post(
                    body=_("สถานะใบสำคัญจ่ายอนุมัติอัตโนมัติ เนื่องจากลงนามเอกสาร %s ครบแล้ว")
                    % rec.display_name
                )

    # ------------------------------------------------------------------
    # Finance dashboard (รายการตั้งเจ้าหนี้รอทำจ่าย)
    # ------------------------------------------------------------------
    @api.model
    def get_payment_finance_dashboard(self):
        """เติมสถานะใบสำคัญจ่าย (บันทึกข้อความ) ลง Dashboard รอทำจ่าย."""
        data = super().get_payment_finance_dashboard()
        rows = data.get("rows") or []
        if not rows:
            return data

        Voucher = self.env["vpk.payment.voucher"].sudo()
        bill_ids = [row["bill_id"] for row in rows if row.get("bill_id")]
        vouchers = Voucher.search(
            [
                ("state", "!=", "cancel"),
                ("bill_ids", "in", bill_ids or [0]),
            ],
            order="id desc",
        )
        by_bill = {}
        for voucher in vouchers:
            for bill in voucher.bill_ids:
                by_bill.setdefault(bill.id, voucher)

        state_labels = dict(Voucher._fields["state"].selection)
        for row in rows:
            voucher = by_bill.get(row.get("bill_id") or 0)
            if voucher:
                row["memo_voucher_id"] = voucher.id
                row["memo_voucher_name"] = voucher.name or ""
                row["memo_voucher_state"] = voucher.state
                row["memo_voucher_state_label"] = state_labels.get(voucher.state, voucher.state)
                if (
                    voucher.state == "approved"
                    and row.get("state") == "to_finance"
                    and not row.get("draft_payment_id")
                ):
                    row["can_register_payment"] = True
            else:
                row["memo_voucher_id"] = False
                row["memo_voucher_name"] = ""
                row["memo_voucher_state"] = ""
                row["memo_voucher_state_label"] = ""
            row["can_create_memo_voucher"] = bool(
                row.get("bill_id") and row.get("state") == "to_finance" and not voucher
            )
        return data

    def action_create_or_open_payment_voucher(self):
        """สร้างหรือเปิดใบสำคัญจ่ายจากใบเรียกเก็บบน Dashboard."""
        self.ensure_one()
        self._vpk_check_ap_access()
        rec = self.sudo()
        bill = rec.payment_bill_id
        if not rec.payment_finance_sent_on or not bill:
            raise UserError(_("เจ้าหนี้ยังไม่ได้ส่งรายการนี้ให้การเงิน"))
        if bill.state != "posted":
            raise UserError(_("ใบเรียกเก็บยังไม่ได้อนุมัติ/POST"))

        existing = self.env["vpk.payment.voucher"].sudo().search(
            [
                ("bill_ids", "in", [bill.id]),
                ("state", "!=", "cancel"),
            ],
            limit=1,
        )
        if existing:
            voucher = existing
        else:
            voucher = self.env["vpk.payment.voucher"].sudo().create_from_bills(bill)

        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสำคัญจ่าย"),
            "res_model": "vpk.payment.voucher",
            "res_id": voucher.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
