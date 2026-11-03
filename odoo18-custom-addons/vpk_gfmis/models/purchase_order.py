# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    gfmis_document_ids = fields.One2many(
        "gfmis.document",
        "purchase_id",
        string="ใบเบิกเงิน",
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
            "name": _("ใบเบิกเงิน"),
            "res_model": "gfmis.document",
            "view_mode": "list,form",
            "domain": [("purchase_id", "=", self.id)],
            "context": {
                "default_purchase_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_request_gfmis_payment(self):
        """เปิดหรือสร้างเอกสารขอเบิกเงินจากใบสั่งซื้อนี้."""
        self.ensure_one()
        if self.state not in ("purchase", "done"):
            raise UserError(_("ขอเบิกเงินได้เมื่อยืนยันใบสั่งซื้อแล้ว"))
        Gfmis = self.env["gfmis.document"]
        draft = Gfmis.search(
            [
                ("purchase_id", "=", self.id),
                ("doc_class", "=", "request"),
                ("state", "=", "draft"),
            ],
            limit=1,
        )
        doc = draft or Gfmis.action_create_from_purchase(self)
        doc._vpk_ensure_default_wht()
        return {
            "type": "ir.actions.act_window",
            "name": _("ขอเบิกเงิน"),
            "res_model": "gfmis.document",
            "res_id": doc.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
