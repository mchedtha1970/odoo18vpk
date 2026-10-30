# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression


class ApprovalApiService(models.AbstractModel):
    _name = "vpk.approval.api.service"
    _description = "Mobile approval API"

    def _review_model(self):
        return self.env["tier.review"]

    def _pending_domain(self):
        return self._review_model()._my_pending_domain()

    def _list_domain(self, status="pending"):
        Review = self._review_model()
        status = (status or "pending").strip().lower()
        if status in ("approved", "done"):
            return Review._my_approved_domain(), "approved"
        if status in ("rejected", "reject"):
            return Review._my_rejected_domain(), "rejected"
        if status == "all":
            return (
                expression.OR(
                    [
                        Review._my_pending_domain(),
                        Review._my_approved_domain(),
                        Review._my_rejected_domain(),
                    ]
                ),
                "all",
            )
        return Review._my_pending_domain(), "pending"

    def search_pending(self, limit=50, offset=0, status="pending"):
        return self.search_reviews(limit=limit, offset=offset, status=status)

    def search_reviews(self, limit=50, offset=0, status="pending"):
        Review = self._review_model()
        domain, status = self._list_domain(status)
        limit = min(max(int(limit or 50), 1), 200)
        offset = max(int(offset or 0), 0)
        order = "reviewed_date desc, id desc" if status != "pending" else "id desc"
        count = Review.search_count(domain)
        reviews = Review.search(domain, limit=limit, offset=offset, order=order)
        return {
            "count": count,
            "limit": limit,
            "offset": offset,
            "status": status,
            "items": [self.serialize_review(review) for review in reviews],
        }

    def get_review(self, review_id):
        review = self._require_review(review_id, action="read")
        return self.serialize_review(review, detail=True)

    def serialize_review(self, review, detail=False):
        record = self._browse_record(review, sudo=True)
        display = review.sudo()
        document_type = False
        document_type_label = display.model_display_name or ""
        document_name = ""
        subject = ""
        request_id = False
        request_name = ""
        has_pdf = False
        pdf_filename = ""
        if record and record.exists():
            document_name = record.display_name
            info = (
                record._vpk_review_card_info()
                if hasattr(record, "_vpk_review_card_info")
                else {}
            )
            if info:
                document_type = record.document_type_id.code or False
                document_type_label = info.get("type_label") or document_type_label
                subject = info.get("subject") or ""
            elif "document_type" in record._fields:
                document_type = record.document_type
                labels = dict(
                    record._fields["document_type"]._description_selection(record.env)
                )
                document_type_label = labels.get(document_type, document_type_label)
            if not subject and "subject" in record._fields:
                subject = record.subject or ""
            if "request_id" in record._fields and record.request_id:
                request_id = record.request_id.id
                request_name = record.request_id.display_name
            elif review.model == "purchase.request":
                request_id = record.id
                request_name = record.display_name
            has_pdf = self._review_has_pdf(review, record)
            if "pdf_filename" in record._fields:
                pdf_filename = record.pdf_filename or ""
        payload = {
            "id": review.id,
            "sequence": review.sequence,
            "status": review.status,
            "status_label": review.display_status or review.status,
            "can_review": bool(review.can_review),
            "can_sign": bool(
                review.can_review and self._is_signable(record) and has_pdf
            ),
            "has_comment": bool(review.has_comment),
            "name": display.name or "",
            "title": display.res_display_name or document_name or display.name or "",
            "model": review.model,
            "model_label": display.model_display_name or "",
            "document_id": review.res_id,
            "document_name": document_name,
            "document_type": document_type,
            "document_type_label": document_type_label,
            "subject": subject,
            "request_id": request_id,
            "request_name": request_name,
            "requested_by": self._user_payload(review.requested_by),
            "done_by": self._user_payload(review.done_by),
            "reviewed_date": fields.Datetime.to_string(review.reviewed_date)
            if review.reviewed_date
            else False,
            "document_state": record.state
            if record and record.exists() and "state" in record._fields
            else False,
            "has_pdf": has_pdf,
            "pdf_filename": pdf_filename,
            "pdf_url": "/vpk/api/v1/mobile/approvals/%s/pdf" % review.id if has_pdf else False,
        }
        if detail and record and record.exists() and self._is_signable(record):
            signers = record.vpk_approver_line_ids.filtered("is_sign").sorted("sequence")
            payload["signer_name"] = signers[-1:].user_id.name or ""
            payload["date"] = fields.Date.to_string(record.date) if record.date else False
            payload["saraban_book_no"] = (
                record.saraban_book_no if "saraban_book_no" in record._fields else ""
            )
        return payload

    def get_pdf(self, review_id):
        review = self._require_review(review_id, action="read")
        record = self._browse_record(review, sudo=True)
        attachment = self._pdf_attachment(review, record)
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        data = attachment.sudo().datas
        if not data:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        filename = (
            ("pdf_filename" in record._fields and record.pdf_filename)
            or attachment.name
            or "document.pdf"
        )
        return {
            "filename": filename,
            "content": base64.b64decode(data),
            "content_disposition": "inline; filename*=UTF-8''%s" % quote(filename),
        }

    def approve(self, review_id, signature=None, comment=None):
        review = self._require_review(review_id, action="approve")
        record = self._browse_record(review)
        if not record:
            raise UserError(_("ไม่พบเอกสาร"))
        reviews = self._user_reviews(record, review)
        if comment:
            reviews.write({"comment": comment})
        if self._is_signable(record):
            if not signature:
                raise UserError(_("กรุณาลงลายเซ็นบนเอกสาร"))
            record.action_apply_signature(signature)
        else:
            record._validate_tier(reviews)
        if hasattr(record, "_update_counter"):
            record._update_counter({"review_deleted": True})
        review.invalidate_recordset()
        return {
            "id": review.id,
            "status": review.status,
            "document_state": record.state if "state" in record._fields else False,
        }

    def reject(self, review_id, comment=None):
        review = self._require_review(review_id, action="reject")
        record = self._browse_record(review)
        if not record:
            raise UserError(_("ไม่พบเอกสาร"))
        reviews = self._user_reviews(record, review)
        if review.has_comment and not comment:
            raise UserError(_("กรุณาระบุเหตุผลที่ไม่อนุมัติ"))
        if comment:
            reviews.write({"comment": comment})
        record._rejected_tier(reviews)
        if hasattr(record, "_update_counter"):
            record._update_counter({"review_deleted": True})
        review.invalidate_recordset()
        return {
            "id": review.id,
            "status": review.status,
            "document_state": record.state if "state" in record._fields else False,
        }

    def user_payload(self, user=None):
        return self._user_payload(user or self.env.user)

    def _user_payload(self, user):
        if not user:
            return False
        return {
            "id": user.id,
            "login": user.login,
            "name": user.name,
            "job_title": user.partner_id.function or "",
        }

    def _require_pending_review(self, review_id):
        return self._require_review(review_id, action="approve")

    def _require_review(self, review_id, action="read"):
        review = self._review_model().browse(int(review_id)).exists()
        if not review:
            raise UserError(_("ไม่พบรายการ"))
        user = self.env.user
        is_reviewer = user in review.reviewer_ids
        is_done_by_me = bool(review.done_by) and review.done_by == user
        if action in ("approve", "reject"):
            if review.status != "pending" or not review.can_review or not is_reviewer:
                raise AccessError(_("รายการนี้ไม่อยู่ในงานรออนุมัติของคุณ"))
            if "vpk_inbox_visible" in review._fields and not review.vpk_inbox_visible:
                raise AccessError(_("รายการนี้ไม่อยู่ในงานรออนุมัติของคุณ"))
            return review
        if review.status == "pending" and review.can_review and is_reviewer:
            return review
        if review.status in ("approved", "rejected") and is_done_by_me:
            return review
        raise AccessError(_("คุณไม่มีสิทธิ์เปิดรายการนี้"))

    def _browse_record(self, review, sudo=False):
        if not review.model or not review.res_id or review.model not in self.env:
            return self._review_model().browse()
        Model = self.env[review.model]
        if sudo:
            Model = Model.sudo()
        return Model.browse(review.res_id)

    def _user_reviews(self, record, review):
        if hasattr(record, "_get_sequences_to_approve"):
            sequences = record._get_sequences_to_approve(self.env.user)
            reviews = record.review_ids.filtered(
                lambda item: item.sequence in sequences or item.approve_sequence_bypass
            )
            if review in reviews:
                return reviews
        return review

    def _review_has_pdf(self, review, record):
        if not record or not record.exists():
            return False
        if not self._is_signable(record):
            return False
        return bool(self._pdf_attachment(review, record))

    def _pdf_attachment(self, review, record):
        if not record or not record.exists() or not self._is_signable(record):
            return self.env["ir.attachment"]
        return record.sudo()._get_pdf_attachment()

    def _is_signable(self, record):
        """Documents signed by stamping a signature on their PDF."""
        return bool(record) and hasattr(record, "action_apply_signature") and hasattr(
            record, "_get_pdf_attachment"
        )

    @api.model
    def issue_session(self, login, password, db_name=None):
        database = db_name or request.db
        if not database:
            raise UserError(_("ไม่ระบุฐานข้อมูล"))
        credential = {"login": login, "password": password, "type": "password"}
        auth_info = request.session.authenticate(database, credential)
        uid = auth_info.get("uid")
        if not uid or uid != request.session.uid:
            raise AccessError(_("เข้าสู่ระบบไม่สำเร็จ"))
        return auth_info
