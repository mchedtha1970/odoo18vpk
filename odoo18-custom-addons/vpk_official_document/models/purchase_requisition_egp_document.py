# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionEgpDocument(models.Model):
    _inherit = "purchase.requisition.egp.document"

    official_document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        string="หนังสือลงนาม",
        copy=False,
        ondelete="set null",
        index=True,
    )
    signature_state = fields.Selection(
        related="official_document_id.signature_state",
        string="สถานะการลงนาม",
        store=True,
    )

    def action_generate_winner_document(self):
        self.ensure_one()
        if self.signature_state in ("waiting", "signed"):
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว ไม่สามารถสร้างใหม่ได้"))
        res = super().action_generate_winner_document()
        self._ensure_winner_official_document()
        return res

    def action_send_for_signature(self):
        self.ensure_one()
        if self.document_type_id.code != "winner_announcement":
            raise UserError(_("ปุ่มนี้ใช้ส่งประกาศผู้ชนะลงนามเท่านั้น"))
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if not self.document_file:
            self.action_generate_winner_document()
        official = self._ensure_winner_official_document()
        official.action_send_for_signature()
        return True

    def _ensure_winner_official_document(self):
        self.ensure_one()
        Official = self.env["vpk.official.document"]
        values = self._winner_announcement_values()
        requisition = self.requisition_id
        basename = "ประกาศผู้ชนะ-%s" % (
            self.egp_reference or requisition.name or self.id
        )
        vals = {
            "document_type": "winner_announcement",
            "requisition_id": requisition.id,
            "subject": values.get("subject") or _("ประกาศผู้ชนะการเสนอราคา"),
            "body": values.get("body") or "",
            "date": self.document_date or fields.Date.context_today(self),
            "company_id": requisition.company_id.id,
            "signer_name": values.get("signer_full") or values.get("signer_name") or "",
            "signer_position": values.get("signer_title") or "",
            "approver_acting": values.get("signer_acting") or "",
        }
        document = self.official_document_id
        if not document:
            document = Official.search(
                [
                    ("document_type", "=", "winner_announcement"),
                    ("requisition_id", "=", requisition.id),
                    ("state", "!=", "cancelled"),
                ],
                limit=1,
            )
        if document and document.signature_state in ("waiting", "signed"):
            if not self.official_document_id:
                self.official_document_id = document.id
            return document
        if not document or not document.officer_id:
            vals["officer_id"] = self.env.user.id
        if document:
            document.with_context(skip_validation_check=True).write(vals)
        else:
            document = Official.create(vals)
        if not self.official_document_id:
            self.official_document_id = document.id
        officer_vals = {}
        if document.officer_id == self.env.user:
            if values.get("cert_full"):
                officer_vals["officer_name"] = values["cert_full"]
            if values.get("cert_title"):
                officer_vals["officer_position"] = values["cert_title"]
        if officer_vals:
            document.with_context(skip_validation_check=True).write(officer_vals)
        if not self.document_file:
            return document
        raw_file = base64.b64decode(self.document_file)
        filename = self.document_filename or ("%s.pdf" % basename)
        if filename.lower().endswith(".pdf"):
            mimetype = "application/pdf"
            kind = "pdf"
        else:
            mimetype = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            kind = "docx"
        document.with_context(skip_validation_check=True)._store_generated_file(
            raw_file,
            filename,
            mimetype,
            kind,
        )
        return document
