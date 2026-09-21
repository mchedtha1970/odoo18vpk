# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    gfmis_document_ids = fields.One2many(
        "gfmis.document",
        "payment_id",
        string="เอกสาร GFMIS",
    )
    gfmis_document_count = fields.Integer(compute="_compute_gfmis_document_count")

    @api.depends("gfmis_document_ids")
    def _compute_gfmis_document_count(self):
        for pay in self:
            pay.gfmis_document_count = len(pay.gfmis_document_ids)

    def action_open_gfmis_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร GFMIS"),
            "res_model": "gfmis.document",
            "view_mode": "list,form",
            "domain": [("payment_id", "=", self.id)],
            "context": {"default_payment_id": self.id, "default_partner_id": self.partner_id.id},
        }
