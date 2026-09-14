# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


PR_APPROVAL_PACKET_TYPES = (
    "wa_committee_order",
    "specific_method_approval",
)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    official_document_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
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
    issued_spec_price_committee_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="บันทึกขออนุมัติแต่งตั้งคณะกรรมการกำหนดคุณลักษณะที่ออกแล้ว",
    )
    issued_specific_method_approval_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="รายงานขออนุมัติจัดซื้อจัดจ้างที่ออกแล้ว",
    )
    specific_method_approval_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="รายงานขออนุมัติจัดซื้อจัดจ้าง",
        domain=[("document_type", "=", "specific_method_approval")],
    )
    wa_committee_order_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="เอกสารแต่งตั้งคณะกรรมการ",
        domain=[
            (
                "document_type",
                "in",
                ("wa_committee_order", "spec_price_committee"),
            )
        ],
    )
    integrity_over_100k_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="เอกสารแสดงความบริสุทธิ์ใจ",
        domain=[("document_type", "=", "integrity_over_100k")],
    )
    approval_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        compute="_compute_approval_attachment_ids",
        string="เอกสารอนุมัติ",
    )
    has_approval_attachments = fields.Boolean(
        compute="_compute_approval_attachment_ids",
    )

    @api.depends("official_document_ids", "official_document_ids.state")
    def _compute_official_document_count(self):
        Document = self.env["vpk.official.document"].sudo()
        counts = {
            row["request_id"][0]: row["request_id_count"]
            for row in Document.read_group(
                [("request_id", "in", self.ids)],
                ["request_id"],
                ["request_id"],
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
            rec.issued_spec_price_committee_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "spec_price_committee"
                    and doc.state != "cancelled"
                )
            )[:1]
            rec.issued_specific_method_approval_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "specific_method_approval"
                    and doc.state != "cancelled"
                )
            )[:1]

    @api.depends(
        "official_document_ids",
        "official_document_ids.state",
        "official_document_ids.pdf_attachment_id",
        "official_document_ids.pdf_file",
    )
    def _compute_approval_attachment_ids(self):
        for rec in self:
            if not isinstance(rec.id, int):
                rec.approval_attachment_ids = False
                rec.has_approval_attachments = False
                continue
            attachments = rec.env["ir.attachment"]
            for doc in rec._vpk_approval_packet_documents():
                attachments |= doc._get_pdf_attachment()
            rec.approval_attachment_ids = attachments
            rec.has_approval_attachments = bool(attachments)

    def _vpk_approval_packet_documents(self):
        self.ensure_one()
        documents = self.env["vpk.official.document"]
        for document_type in PR_APPROVAL_PACKET_TYPES:
            documents |= self.official_document_ids.filtered(
                lambda doc, dtype=document_type: (
                    doc.document_type == dtype and doc.state != "cancelled"
                )
            )[:1]
        return documents

    def _vpk_ensure_pr_approval_packet(self):
        """Create committee order + approval report PDFs before sending to the director."""
        Document = self.env["vpk.official.document"]
        packet = Document.browse()
        for rec in self:
            order = Document.create_from_purchase_request(rec)
            approval = Document.create_specific_method_approval_from_purchase_request(
                rec
            )
            for doc in order | approval:
                if not doc._get_pdf_attachment():
                    doc.with_context(skip_validation_check=True).action_generate_pdf()
                if not doc._get_pdf_attachment():
                    raise UserError(
                        _("ไม่สามารถสร้างไฟล์ PDF ของ %s ได้ กรุณากดพิมพ์ PDF ก่อนขออนุมัติ")
                        % doc.display_name
                    )
                if doc.state in ("draft", "generated"):
                    doc.with_context(skip_validation_check=True).write(
                        {"state": "to_approve"}
                    )
            packet |= order | approval
        return packet

    def _vpk_document_is_fully_approved(self, document):
        if document.state == "cancelled":
            return False
        if document.state == "approved":
            return True
        if document.review_ids:
            document.invalidate_recordset(["validation_status", "validated"])
            return document.validation_status == "validated"
        return False

    def _vpk_related_official_documents(self):
        self.ensure_one()
        return self.official_document_ids.filtered(
            lambda doc: doc.state != "cancelled"
        )

    @api.depends(
        "official_document_ids",
        "official_document_ids.state",
        "official_document_ids.validation_status",
        "official_document_ids.review_ids.status",
    )
    def _compute_can_send_to_egp(self):
        if hasattr(super(), "_compute_can_send_to_egp"):
            return super()._compute_can_send_to_egp()
        for request in self:
            if "can_send_to_egp" in request._fields:
                request.can_send_to_egp = request._vpk_related_documents_all_approved()

    def _vpk_related_documents_all_approved(self):
        """True when every issued official document on this PR is fully signed."""
        self.ensure_one()
        documents = self._vpk_related_official_documents()
        if not documents:
            return False
        issued_types = set(documents.mapped("document_type"))
        if not set(PR_APPROVAL_PACKET_TYPES).issubset(issued_types):
            return False
        return all(self._vpk_document_is_fully_approved(doc) for doc in documents)

    def _vpk_packet_is_complete(self):
        self.ensure_one()
        packet = self._vpk_approval_packet_documents()
        if set(packet.mapped("document_type")) != set(PR_APPROVAL_PACKET_TYPES):
            return False
        return all(self._vpk_document_is_fully_approved(doc) for doc in packet)

    def _vpk_approve_if_packet_complete(self):
        """When both packet documents are approved, approve and confirm the PR."""
        now = fields.Datetime.now()
        for rec in self:
            if rec.state not in ("draft", "to_approve", "sent_to_procurement"):
                continue
            if not rec._vpk_packet_is_complete():
                continue
            pending = rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if pending:
                pending.write(
                    {
                        "status": "approved",
                        "done_by": self.env.user.id,
                        "reviewed_date": now,
                    }
                )
                pending._compute_can_review()
            rec.invalidate_recordset(["validation_status", "validated"])
            if hasattr(rec, "_vpk_auto_confirm_if_validated"):
                rec._vpk_auto_confirm_if_validated()
            if rec.state in ("draft", "to_approve", "sent_to_procurement"):
                rec.sudo().with_user(self.env.user).with_context(
                    skip_validation_check=True
                ).button_approved()

    def _vpk_reset_approval_packet_reviews(self, status="rejected"):
        now = fields.Datetime.now()
        for rec in self:
            docs = rec._vpk_approval_packet_documents()
            pending = docs.mapped("review_ids").filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if status == "unlink":
                pending.unlink()
            elif pending:
                pending.write(
                    {
                        "status": status,
                        "done_by": self.env.user.id,
                        "reviewed_date": now,
                    }
                )
                pending._compute_can_review()
            docs.filtered(lambda doc: doc.state == "to_approve").with_context(
                skip_validation_check=True
            ).write({"state": "generated"})

    def request_validation(self):
        packet = self._vpk_ensure_pr_approval_packet()
        created = super().request_validation()
        packet._vpk_create_reviews_from_purchase_request(created)
        return created

    def restart_validation(self):
        self._vpk_reset_approval_packet_reviews(status="unlink")
        return super().restart_validation()

    def reject_tier(self):
        res = super().reject_tier()
        self._vpk_reset_approval_packet_reviews(status="rejected")
        return res

    def validate_tier(self):
        for rec in self:
            if rec._vpk_approval_packet_documents() and not rec._vpk_packet_is_complete():
                raise UserError(
                    _(
                        "กรุณาอนุมัติคำสั่งแต่งตั้งกรรมการ และรายงานขออนุมัติจัดซื้อจัดจ้างให้ครบก่อน "
                        "ระบบจะอนุมัติใบขอซื้อให้อัตโนมัติ"
                    )
                )
        return super().validate_tier()

    def _vpk_auto_confirm_if_validated(self):
        self.ensure_one()
        if self._vpk_approval_packet_documents() and not self._vpk_packet_is_complete():
            return
        return super()._vpk_auto_confirm_if_validated()

    def _sync_saraban_from_document(self, document):
        super()._sync_saraban_from_document(document)
        purpose = (
            document.purpose
            if "purpose" in document._fields
            else "pr_approval"
        )
        if purpose == "official_document":
            return
        number = document.book_no_display or document.book_no
        approvals = self.official_document_ids.filtered(
            lambda doc: (
                doc.document_type == "specific_method_approval"
                and doc.state != "cancelled"
            )
        )
        for approval in approvals:
            vals = {}
            if number:
                vals["saraban_book_no"] = number
            if document:
                vals["saraban_document_id"] = document.id
            if vals:
                approval.write(vals)

    def action_view_official_documents(self):
        self.ensure_one()
        documents = self.official_document_ids
        if len(documents) == 1:
            return documents._action_open_form()
        return {
            "type": "ir.actions.act_window",
            "name": "หนังสือราชการ",
            "res_model": "vpk.official.document",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": {
                "default_request_id": self.id,
                "default_department_id": self.department_id.id,
                "default_document_type": "wa_committee_order",
            },
        }

    def action_create_wa_committee_order(self):
        self.ensure_one()
        document = self.env["vpk.official.document"].create_from_purchase_request(self)
        return document._action_open_form()

    def action_create_integrity_over_100k(self):
        self.ensure_one()
        document = self.env["vpk.official.document"].create_integrity_from_purchase_request(
            self
        )
        return document._action_open_form()

    def action_create_spec_price_committee(self):
        self.ensure_one()
        document = self.env[
            "vpk.official.document"
        ].create_spec_price_committee_from_purchase_request(self)
        return document._action_open_form()

    def action_create_specific_method_approval(self):
        self.ensure_one()
        document = self.env[
            "vpk.official.document"
        ].create_specific_method_approval_from_purchase_request(self)
        return document._action_open_form()
