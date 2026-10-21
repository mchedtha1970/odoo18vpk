# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequestReturnWizard(models.TransientModel):
    _name = "purchase.request.return.wizard"
    _description = "ส่งกลับใบขอซื้อให้หน่วยงานแก้ไข"

    request_id = fields.Many2one(
        "purchase.request",
        string="ใบขอซื้อ",
        required=True,
        readonly=True,
    )
    reason = fields.Text(
        string="เหตุผลในการส่งกลับให้แก้ไข",
        required=True,
    )

    def action_confirm_return(self):
        self.ensure_one()
        reason = (self.reason or "").strip()
        if not reason:
            raise UserError(_("กรุณาระบุเหตุผลในการส่งกลับให้แก้ไข"))
        self.request_id._vpk_do_return_for_revision(reason)
        return {"type": "ir.actions.act_window_close"}
