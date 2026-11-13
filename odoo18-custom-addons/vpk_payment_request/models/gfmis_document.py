# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import api, fields, models


class GfmisDocument(models.Model):
    _inherit = "gfmis.document"

    payment_request_doc_ids = fields.Many2many(
        comodel_name="vpk.document.studio.document",
        string="เอกสารอนุมัติเบิกจ่าย",
        compute="_compute_payment_request_doc_ids",
    )

    @api.depends("invoice_id", "purchase_id")
    def _compute_payment_request_doc_ids(self):
        Doc = self.env["vpk.document.studio.document"].sudo()
        for rec in self:
            domain = [
                ("document_type_code", "=", "payment_request"),
                ("state", "!=", "cancelled"),
            ]
            docs = Doc.browse()
            if rec.invoice_id:
                docs = Doc.search(domain + [("payment_bill_id", "=", rec.invoice_id.id)])
            if not docs and rec.purchase_id:
                docs = Doc.search(domain + [("purchase_id", "=", rec.purchase_id.id)])
            rec.payment_request_doc_ids = docs
