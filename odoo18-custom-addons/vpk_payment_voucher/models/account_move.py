# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_create_payment_voucher(self):
        """สร้างใบสำคัญจ่ายจากใบเรียกเก็บที่เลือก (ต้อง POST แล้ว)."""
        bills = self.filtered(
            lambda move: move.move_type == "in_invoice" and move.state == "posted"
        )
        if not bills:
            raise UserError(_("เลือกใบเรียกเก็บที่ POST แล้วเท่านั้น"))
        voucher = self.env["vpk.payment.voucher"].create_from_bills(bills)
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสำคัญจ่าย"),
            "res_model": "vpk.payment.voucher",
            "res_id": voucher.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
