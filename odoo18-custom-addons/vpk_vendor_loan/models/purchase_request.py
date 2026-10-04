# -*- coding: utf-8 -*-
from odoo import _, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    vpk_vendor_loan_ids = fields.One2many(
        "vpk.vendor.loan",
        "purchase_request_id",
        string="ใบยืมจากผู้ขาย",
    )
    vpk_vendor_loan_count = fields.Integer(compute="_compute_vpk_vendor_loan_count")

    def _compute_vpk_vendor_loan_count(self):
        for request in self:
            request.vpk_vendor_loan_count = len(request.vpk_vendor_loan_ids)

    def action_view_vpk_vendor_loan(self):
        self.ensure_one()
        loans = self.vpk_vendor_loan_ids
        action = {
            "type": "ir.actions.act_window",
            "name": _("ยืมของจากผู้ขาย"),
            "res_model": "vpk.vendor.loan",
            "view_mode": "form" if len(loans) == 1 else "list,form",
            "target": "current",
        }
        if len(loans) == 1:
            action["res_id"] = loans.id
        else:
            action["domain"] = [("id", "in", loans.ids)]
        return action
