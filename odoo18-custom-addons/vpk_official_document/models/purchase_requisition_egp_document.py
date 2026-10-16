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
        """สร้างหนังสือราชการจากเทมเพลต แล้วเปิดฟอร์มเอกสาร เหมือนรายงานผลการพิจารณา."""
        self.ensure_one()
        if self.document_type_id.code != "winner_announcement":
            return super().action_generate_winner_document()
        if self.signature_state in ("waiting", "signed"):
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว ไม่สามารถสร้างใหม่ได้"))
        document = self._build_winner_official_document()
        return document._action_open_form()

    def action_send_for_signature_inbox(self):
        """เปิดตัวเลือกส่งลงนาม หรือข้ามการอนุมัติเพื่อทดสอบ."""
        self.ensure_one()
        code = self.document_type_id.code
        if code == "winner_announcement":
            if self.signature_state == "signed":
                raise UserError(_("เอกสารนี้ลงนามแล้ว"))
            if self.signature_state == "waiting":
                raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
            if not self.official_document_id or not self.official_document_id.pdf_file:
                self._build_winner_official_document()
            official = self._ensure_winner_official_document()
        elif code == "award_approval":
            if self.signature_state == "signed":
                raise UserError(_("เอกสารนี้ลงนามแล้ว"))
            if self.signature_state == "waiting":
                raise UserError(_("เอกสารถูกส่งขออนุมัติแล้ว"))
            if not self.document_file:
                raise UserError(_("ยังไม่มีไฟล์รายงาน กรุณาพิมพ์รายงานก่อนขออนุมัติ"))
            official = self._ensure_award_official_document()
        else:
            raise UserError(_("เอกสารนี้ยังไม่มีขั้นตอนส่งเพื่อลงนาม"))
        return official.action_open_send_wizard()

    def action_request_award_approval(self):
        self.ensure_one()
        if self.document_type_id.code != "award_approval":
            raise UserError(_("ปุ่มนี้ใช้ขออนุมัติรายงานผลการพิจารณาเท่านั้น"))
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งขออนุมัติแล้ว"))
        if not self.document_file:
            raise UserError(_("ยังไม่มีไฟล์รายงาน กรุณาพิมพ์รายงานก่อนขออนุมัติ"))
        report = self.award_report_id
        if report and report.state == "draft":
            report.action_submit()
        official = self._ensure_award_official_document()
        official.action_send_for_signature()
        return True

    def _ensure_award_official_document(self):
        self.ensure_one()
        Official = self.env["vpk.official.document"]
        if self.document_type_id.code != "award_approval":
            return Official
        report = self.award_report_id
        requisition = self.requisition_id
        vals = {
            "document_type": "award_approval",
            "requisition_id": requisition.id,
            "subject": (report.subject if report else "")
            or _("รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง"),
            "date": self.document_date or fields.Date.context_today(self),
            "company_id": requisition.company_id.id,
        }
        if report and report.purchase_request_id:
            vals["request_id"] = report.purchase_request_id.id
        document = self.official_document_id
        if not document and requisition:
            document = Official.search(
                [
                    ("document_type", "=", "award_approval"),
                    ("requisition_id", "=", requisition.id),
                    ("state", "!=", "cancelled"),
                ],
                limit=1,
            )
        if document and document.signature_state in ("waiting", "signed"):
            if not self.official_document_id:
                self.official_document_id = document.id
            return document
        if document:
            document.with_context(skip_validation_check=True).write(vals)
        else:
            document = Official.with_context(skip_validation_check=True).create(vals)
        if self.official_document_id != document:
            self.official_document_id = document.id
        if report:
            report._push_signers_to_official_document(document)
        if not self.document_file:
            return document
        basename = "รายงานผลการพิจารณา-%s" % (
            self.egp_reference or requisition.name or self.id
        )
        document.with_context(skip_validation_check=True)._store_generated_file(
            base64.b64decode(self.document_file),
            self.document_filename or ("%s.pdf" % basename),
            "application/pdf",
            "pdf",
        )
        return document

    def action_send_for_signature(self):
        self.ensure_one()
        if self.document_type_id.code != "winner_announcement":
            raise UserError(_("ปุ่มนี้ใช้ส่งประกาศผู้ชนะลงนามเท่านั้น"))
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
        if not self.official_document_id or not self.official_document_id.pdf_file:
            self._build_winner_official_document()
        official = self._ensure_winner_official_document()
        official.action_send_for_signature()
        return True

    def _build_winner_official_document(self):
        """Fill the winner-announcement template into an official document."""
        self.ensure_one()
        document = self._ensure_winner_official_document(copy_file=False)
        if document.signature_state in ("waiting", "signed"):
            return document
        try:
            document.with_context(skip_validation_check=True).action_generate_pdf()
        except UserError:
            if not document.docx_file:
                raise
            if not document.pdf_file:
                document.with_context(skip_validation_check=True).action_generate_docx()
        return document

    def _ensure_winner_official_document(self, copy_file=True):
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
            "body": values.get("body")
            or "\n\n".join(
                part
                for part in (
                    values.get("body_intro") or "",
                    values.get("body_winner") or "",
                )
                if part
            ),
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
        if not copy_file or not self.document_file:
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


class PurchaseRequisitionAwardReport(models.Model):
    _inherit = "purchase.requisition.award.report"

    def _push_signers_to_official_document(self, document):
        """Copy the approver table onto the official document before it is sent."""
        self.ensure_one()
        if not document or document.signature_state in ("waiting", "signed"):
            return document
        lines = self.signer_line_ids.filtered("user_id").sorted(
            key=lambda line: (line.sequence, line.id)
        )
        if not lines:
            return document
        Signer = self.env["vpk.official.document.signer"]
        document.signer_line_ids.with_context(vpk_skip_signer_sync=True).unlink()
        Signer.with_context(vpk_skip_signer_sync=True).create(
            [
                {
                    "document_id": document.id,
                    "sequence": line.sequence,
                    "user_id": line.user_id.id,
                    "position": line.position,
                    "is_check": line.is_check,
                    "is_sign": line.is_sign,
                }
                for line in lines
            ]
        )
        document._sync_signers_from_lines()
        return document
