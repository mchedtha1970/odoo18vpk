# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    disbursement_form_ids = fields.One2many(
        "vpk.disbursement.form",
        "invoice_id",
        string="ใบขอเบิกเงิน",
        copy=False,
    )
    disbursement_form_count = fields.Integer(
        compute="_compute_disbursement_form_count",
    )
    vpk_sent_to_finance = fields.Boolean(
        string="ส่งการเงินแล้ว",
        compute="_compute_vpk_sent_to_finance",
    )

    @api.depends("disbursement_form_ids", "disbursement_form_ids.state")
    def _compute_disbursement_form_count(self):
        for move in self:
            forms = move.sudo().disbursement_form_ids.filtered(
                lambda form: form.state != "cancel"
            )
            move.disbursement_form_count = len(forms)

    @api.depends(
        "payment_request_id",
        "payment_request_id.payment_finance_sent_on",
    )
    def _compute_vpk_sent_to_finance(self):
        for move in self:
            request = move.sudo().payment_request_id
            move.vpk_sent_to_finance = bool(
                request and request.payment_finance_sent_on
            )

    def action_open_disbursement_forms(self):
        self.ensure_one()
        forms = self.disbursement_form_ids.filtered(lambda form: form.state != "cancel")
        action = {
            "type": "ir.actions.act_window",
            "name": _("ใบขอเบิกเงิน"),
            "res_model": "vpk.disbursement.form",
            "view_mode": "list,form",
            "domain": [("invoice_id", "=", self.id), ("state", "!=", "cancel")],
            "context": {
                "default_invoice_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }
        if len(forms) == 1:
            action["view_mode"] = "form"
            action["res_id"] = forms.id
        return action

    def action_create_disbursement_form(self):
        self.ensure_one()
        form = self.env["vpk.disbursement.form"].action_create_from_invoice(self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "vpk.disbursement.form",
            "res_id": form.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_gfmis_document(self):
        """บิลที่ส่งการเงินแล้ว → สร้างใบขอเบิกเงิน (ขบ.01) แทนเอกสาร GFMIS เดิม."""
        self.ensure_one()
        if self.vpk_sent_to_finance:
            return self.action_create_disbursement_form()
        return super().action_create_gfmis_document()
