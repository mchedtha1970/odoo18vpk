from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .studio_document import PR_APPROVAL_PACKET_TYPES


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    studio_document_ids = fields.One2many(
        comodel_name="vpk.document.studio.document",
        inverse_name="request_id",
        string="เอกสารที่เกี่ยวข้อง",
    )
    studio_document_count = fields.Integer(
        string="จำนวนเอกสาร",
        compute="_compute_studio_document_count",
    )
    vpk_studio_signed_complete = fields.Boolean(
        string="ลงนามครบแล้ว",
        compute="_compute_vpk_studio_signed_complete",
    )

    @api.depends("studio_document_ids")
    def _compute_studio_document_count(self):
        Document = self.env["vpk.document.studio.document"].sudo()
        counts = {
            row["request_id"][0]: row["request_id_count"]
            for row in Document.read_group(
                [("request_id", "in", self.ids)], ["request_id"], ["request_id"]
            )
        }
        for rec in self:
            rec.studio_document_count = counts.get(rec.id, 0)

    @api.depends("studio_document_ids.state", "studio_document_ids.document_type_code")
    def _compute_vpk_studio_signed_complete(self):
        for rec in self:
            rec.vpk_studio_signed_complete = rec._vpk_studio_packet_is_complete()

    # ------------------------------------------------------------------
    # Approval packet
    # ------------------------------------------------------------------
    def _vpk_studio_packet_documents(self):
        self.ensure_one()
        documents = self.env["vpk.document.studio.document"]
        active = self.sudo().studio_document_ids.filtered(lambda doc: doc.state != "cancelled")
        for code in PR_APPROVAL_PACKET_TYPES:
            documents |= active.filtered(
                lambda doc, code=code: doc.document_type_code == code
            ).sorted("id", reverse=True)[:1]
        return documents

    def _vpk_studio_packet_is_complete(self):
        self.ensure_one()
        packet = self._vpk_studio_packet_documents()
        if set(packet.mapped("document_type_code")) != set(PR_APPROVAL_PACKET_TYPES):
            return False
        return all(doc.state == "approved" for doc in packet)

    def _vpk_ensure_studio_packet(self):
        """Create the committee order and approval report, then send them to sign."""
        Document = self.env["vpk.document.studio.document"]
        Type = self.env["vpk.document.studio.document.type"]
        packet = Document.browse()
        for rec in self:
            existing = rec._vpk_studio_packet_documents()
            for code in PR_APPROVAL_PACKET_TYPES:
                document = existing.filtered(lambda doc, code=code: doc.document_type_code == code)
                if not document:
                    if code == "wa_committee_order" and not rec.work_acceptance_committee_ids:
                        raise UserError(
                            _("กรุณาบันทึกคณะกรรมการตรวจรับในแท็บคณะกรรมการก่อนขออนุมัติ")
                        )
                    document_type = Type.search(
                        [("code", "=", code), ("company_id", "in", [False, rec.company_id.id])],
                        limit=1,
                    )
                    if not document_type:
                        raise UserError(
                            _("ยังไม่ได้ตั้งค่าประเภทเอกสาร %s ใน Document Studio") % code
                        )
                    document = Document._vpk_create_for_record(rec, document_type)
                if not document.pdf_file and document.source_mode == "studio":
                    document.action_generate_pdf()
                if not document.pdf_file:
                    raise UserError(
                        _("ไม่สามารถสร้างไฟล์ PDF ของ %s ได้ กรุณาพิมพ์ PDF ก่อนขออนุมัติ")
                        % document.display_name
                    )
                packet |= document
        return packet

    def request_validation(self):
        check_budget = getattr(self, "_check_budget_available_before_submit", None)
        if check_budget:
            action = check_budget()
            if isinstance(action, dict):
                return action
        packet = self._vpk_ensure_studio_packet()
        created = super().request_validation()
        if isinstance(created, dict):
            return created
        packet.filtered(lambda doc: doc.state in ("draft", "generated")).action_send_for_signature()
        return created

    def _vpk_reset_studio_packet(self, unlink_reviews=False):
        for rec in self:
            docs = rec._vpk_studio_packet_documents().filtered(
                lambda doc: doc.state == "to_approve"
            )
            open_reviews = docs.mapped("review_ids").filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if unlink_reviews:
                docs.mapped("review_ids").sudo().unlink()
            elif open_reviews:
                open_reviews.sudo().write(
                    {
                        "status": "rejected",
                        "done_by": self.env.user.id,
                        "reviewed_date": fields.Datetime.now(),
                    }
                )
            docs.sudo().with_context(skip_validation_check=True).write({"state": "generated"})

    def restart_validation(self):
        self._vpk_reset_studio_packet(unlink_reviews=True)
        return super().restart_validation()

    def reject_tier(self):
        res = super().reject_tier()
        if not self.env.context.get("vpk_skip_pr_reject_from_packet"):
            self._vpk_reset_studio_packet()
        return res

    def _vpk_reject_from_packet(self):
        """A packet document was rejected: reject the request and reopen the other one."""
        for rec in self:
            pending = rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            pending.write(
                {
                    "status": "rejected",
                    "done_by": self.env.user.id,
                    "reviewed_date": fields.Datetime.now(),
                }
            )
            rec._vpk_reset_studio_packet()
            if hasattr(rec, "_notify_requesting_unit_rejected"):
                rec._notify_requesting_unit_rejected()
            rec.message_post(body=_("เอกสารประกอบการขออนุมัติถูกตีกลับ กรุณาแก้ไขแล้วขออนุมัติใหม่"))

    def validate_tier(self):
        for rec in self:
            if rec._vpk_studio_packet_documents() and not rec._vpk_studio_packet_is_complete():
                raise UserError(
                    _(
                        "กรุณาลงนามคำสั่งแต่งตั้งกรรมการ และรายงานขออนุมัติจัดซื้อจัดจ้างให้ครบก่อน "
                        "ระบบจะอนุมัติใบขอซื้อให้อัตโนมัติ"
                    )
                )
        return super().validate_tier()

    def _vpk_auto_confirm_if_validated(self):
        self.ensure_one()
        if self._vpk_studio_packet_documents() and not self._vpk_studio_packet_is_complete():
            return
        return super()._vpk_auto_confirm_if_validated()

    def _vpk_approve_if_packet_complete(self):
        """When every packet document is signed, approve and confirm the request."""
        now = fields.Datetime.now()
        for rec in self:
            if rec.state not in ("draft", "to_approve", "sent_to_procurement"):
                continue
            if not rec._vpk_studio_packet_is_complete():
                continue
            pending = rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if pending:
                pending.sudo().write(
                    {"status": "approved", "done_by": self.env.user.id, "reviewed_date": now}
                )
                pending._compute_can_review()
            rec.invalidate_recordset(["validation_status", "validated"])
            if hasattr(rec, "_vpk_auto_confirm_if_validated"):
                rec._vpk_auto_confirm_if_validated()
            if rec.state in ("draft", "to_approve", "sent_to_procurement"):
                rec.with_user(self.env.user).sudo().with_context(
                    skip_validation_check=True,
                    skip_check_state_condition=True,
                    vpk_in_auto_confirm=True,
                ).button_approved()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_view_studio_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารที่เกี่ยวข้อง"),
            "res_model": "vpk.document.studio.document",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": {
                "default_request_id": self.id,
                "default_source_ref": "purchase.request,%d" % self.id,
                "search_default_my_documents": 0,
            },
        }

    def action_open_add_studio_document_wizard(self):
        self.ensure_one()
        return self.env["vpk.studio.document.add.wizard"]._open_for(self)
