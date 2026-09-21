# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    gfmis_document_ids = fields.One2many(
        "gfmis.document",
        "purchase_id",
        string="เอกสาร GFMIS",
    )
    gfmis_document_count = fields.Integer(compute="_compute_gfmis_document_count")

    @api.depends("gfmis_document_ids")
    def _compute_gfmis_document_count(self):
        for order in self:
            order.gfmis_document_count = len(order.gfmis_document_ids)

    def action_open_gfmis_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร GFMIS"),
            "res_model": "gfmis.document",
            "view_mode": "list,form",
            "domain": [("purchase_id", "=", self.id)],
            "context": {
                "default_purchase_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }
