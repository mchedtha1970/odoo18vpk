# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    official_document_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="wa_id",
        string="หนังสือราชการ",
    )
    official_document_count = fields.Integer(
        compute="_compute_official_document_count",
    )
    issued_wa_committee_order_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="คำสั่งแต่งตั้งที่ออกแล้ว",
    )
    issued_integrity_document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="แบบแสดงความบริสุทธิ์ใจที่ออกแล้ว",
    )

    @api.depends("official_document_ids", "official_document_ids.state")
    def _compute_official_document_count(self):
        Document = self.env["vpk.official.document"].sudo()
        counts = {
            row["wa_id"][0]: row["wa_id_count"]
            for row in Document.read_group(
                [("wa_id", "in", self.ids)],
                ["wa_id"],
                ["wa_id"],
            )
        }
        for rec in self:
            rec.official_document_count = counts.get(rec.id, 0)
            rec.issued_wa_committee_order_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "wa_committee_order"
                    and doc.state != "cancelled"
                )
            )[:1]
            rec.issued_integrity_document_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "integrity_over_100k"
                    and doc.state != "cancelled"
                )
            )[:1]
            if not rec.issued_wa_committee_order_id or not rec.issued_integrity_document_id:
                request = self.env["vpk.official.document"]._request_from_work_acceptance(
                    rec
                )
                if request:
                    if not rec.issued_wa_committee_order_id:
                        rec.issued_wa_committee_order_id = (
                            self.env["vpk.official.document"]._find_existing_document(
                                "wa_committee_order", request=request
                            )
                        )
                    if not rec.issued_integrity_document_id:
                        rec.issued_integrity_document_id = (
                            self.env["vpk.official.document"]._find_existing_document(
                                "integrity_over_100k", request=request
                            )
                        )

    def action_view_official_documents(self):
        self.ensure_one()
        documents = self.official_document_ids
        if len(documents) == 1:
            return documents._action_open_form()
        domain = [("wa_id", "=", self.id)]
        request = self.env["vpk.official.document"]._request_from_work_acceptance(self)
        if request:
            domain = ["|", ("wa_id", "=", self.id), ("request_id", "=", request.id)]
        return {
            "type": "ir.actions.act_window",
            "name": "หนังสือราชการ",
            "res_model": "vpk.official.document",
            "view_mode": "list,form",
            "domain": domain,
            "context": {
                "default_wa_id": self.id,
                "default_purchase_id": self.purchase_id.id,
                "default_document_type": "wa_committee_order",
            },
        }

    def action_create_wa_committee_order(self):
        self.ensure_one()
        document = self.env["vpk.official.document"].create_from_work_acceptance(self)
        return document._action_open_form()

    def action_create_integrity_over_100k(self):
        self.ensure_one()
        document = self.env["vpk.official.document"].create_integrity_from_work_acceptance(
            self
        )
        return document._action_open_form()
