# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    gfmis_document_ids = fields.One2many(
        "gfmis.document",
        "invoice_id",
        string="เอกสาร GFMIS",
    )
    gfmis_document_count = fields.Integer(compute="_compute_gfmis_document_count")

    @api.depends("gfmis_document_ids")
    def _compute_gfmis_document_count(self):
        for move in self:
            move.gfmis_document_count = len(move.gfmis_document_ids)

    def action_open_gfmis_documents(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร GFMIS"),
            "res_model": "gfmis.document",
            "view_mode": "list,form",
            "domain": [("invoice_id", "=", self.id)],
            "context": {"default_invoice_id": self.id, "default_partner_id": self.partner_id.id},
        }
        if len(self.gfmis_document_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.gfmis_document_ids.id
        return action

    def action_create_gfmis_document(self):
        self.ensure_one()
        doc = self.env["gfmis.document"].action_create_from_invoice(self)
        return {
            "type": "ir.actions.act_window",
            "res_model": "gfmis.document",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }
