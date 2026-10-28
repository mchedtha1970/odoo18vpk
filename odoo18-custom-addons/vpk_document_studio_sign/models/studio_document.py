import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .pdf_stamp import SignatureStampError, stamp_signature_on_pdf

THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
SIGN_LOCKED_STATES = ("to_approve", "approved")

_logger = logging.getLogger(__name__)


class DocumentStudioDocument(models.Model):
    _name = "vpk.document.studio.document"
    _inherit = ["vpk.document.studio.document", "tier.validation"]
    _state_from = ["draft", "generated", "to_approve"]
    _state_to = ["approved"]
    _cancel_state = "cancelled"
    _tier_validation_manual_config = True

    state = fields.Selection(
        selection_add=[
            ("to_approve", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        ondelete={
            "to_approve": "set default",
            "approved": "set default",
            "cancelled": "set default",
        },
    )
    signature_state = fields.Selection(
        selection=[
            ("not_sent", "ยังไม่ส่งลงนาม"),
            ("waiting", "รอลงนาม"),
            ("signed", "ลงนามแล้ว"),
        ],
        string="สถานะการลงนาม",
        compute="_compute_signature_state",
        store=True,
    )
    signed_on = fields.Datetime(string="ลงนามครบเมื่อ", copy=False, readonly=True)
    vpk_secretary_screen_state = fields.Selection(
        selection=[("checked", "ตรวจสอบแล้ว")],
        string="สถานะการตรวจสอบ",
        copy=False,
    )
    saraban_book_no = fields.Char(
        string="เลขที่จากสารบรรณ",
        copy=False,
        tracking=True,
        help="ใช้ในแบบฟอร์มด้วย {{saraban_no}} (เลขอารบิก) หรือ {{saraban_no_th}} (เลขไทย)",
    )
    saraban_document_id = fields.Many2one(
        comodel_name="saraban.document",
        string="งานสารบรรณ",
        copy=False,
        ondelete="set null",
        index=True,
    )

    vpk_signing_enabled = fields.Boolean(compute="_compute_vpk_signing_enabled")

    def _compute_vpk_signing_enabled(self):
        for rec in self:
            rec.vpk_signing_enabled = rec._vpk_signing_enabled()

    @api.depends("state")
    def _compute_signature_state(self):
        for rec in self:
            if rec.state == "approved":
                rec.signature_state = "signed"
            elif rec.state == "to_approve":
                rec.signature_state = "waiting"
            else:
                rec.signature_state = "not_sent"

    # ------------------------------------------------------------------
    # Generation guards and merge values
    # ------------------------------------------------------------------
    def _check_not_locked_for_signing(self):
        for rec in self:
            if rec.state in SIGN_LOCKED_STATES:
                raise UserError(
                    _("เอกสาร %s ส่งลงนามแล้ว ไม่สามารถสร้างไฟล์ใหม่ได้") % rec.display_name
                )
            if rec.state == "cancelled":
                raise UserError(_("เอกสาร %s ถูกยกเลิกแล้ว") % rec.display_name)

    def action_generate_docx(self):
        self._check_not_locked_for_signing()
        return super().action_generate_docx()

    def action_generate_pdf(self):
        self._check_not_locked_for_signing()
        return super().action_generate_pdf()

    def _live_body_codes(self):
        return super()._live_body_codes() | {"saraban_no", "saraban_no_th"}

    def write(self, vals):
        if "body" in vals and self and all(rec.state in SIGN_LOCKED_STATES for rec in self):
            # The editor is read-only here; a body sent by the form is only its re-serialisation.
            vals = {key: value for key, value in vals.items() if key != "body"}
            if not vals:
                return True
        res = super().write(vals)
        if "saraban_book_no" in vals and not self.env.context.get("vpk_live_field_refresh"):
            self._apply_saraban_number_to_body()
        return res

    def _apply_saraban_number_to_body(self):
        for rec in self.filtered(
            lambda doc: doc.state not in SIGN_LOCKED_STATES + ("cancelled",)
        ):
            had_pdf = bool(rec.pdf_file)
            before = rec.body
            rec._refresh_live_body_fields()
            if not had_pdf or rec.body == before:
                continue
            try:
                with self.env.cr.savepoint():
                    rec.action_generate_pdf()
            except Exception:
                _logger.info(
                    "Could not regenerate PDF of %s after saraban number change",
                    rec.display_name,
                    exc_info=True,
                )

    def _merge_mapping(self):
        result = super()._merge_mapping()
        number = (self.saraban_book_no or "").strip()
        if number or not result.get("saraban_no"):
            result["saraban_no"] = number
        if number or not result.get("saraban_no_th"):
            result["saraban_no_th"] = number.translate(THAI_DIGITS)
        return result

    def _get_under_validation_exceptions(self):
        return list(
            set(
                super()._get_under_validation_exceptions()
                + [
                    "state",
                    "pdf_file",
                    "pdf_filename",
                    "docx_file",
                    "docx_filename",
                    "message_main_attachment_id",
                    "signed_on",
                    "signature_state",
                    "saraban_book_no",
                    "saraban_document_id",
                    "vpk_secretary_screen_state",
                ]
            )
        )

    def _get_after_validation_exceptions(self):
        return list(
            set(
                super()._get_after_validation_exceptions()
                + [
                    "state",
                    "pdf_file",
                    "pdf_filename",
                    "signed_on",
                    "signature_state",
                    "vpk_secretary_screen_state",
                ]
            )
        )

    # ------------------------------------------------------------------
    # Sending for signature
    # ------------------------------------------------------------------
    def _vpk_signing_enabled(self):
        """Hook: documents signed through another flow return False."""
        self.ensure_one()
        return True

    def _get_pdf_attachment(self):
        self.ensure_one()
        return self.env["ir.attachment"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", "pdf_file"),
            ],
            limit=1,
        )

    def action_send_for_signature(self):
        for rec in self:
            if not rec._vpk_signing_enabled():
                raise UserError(_("เอกสารนี้ส่งลงนามผ่านหนังสือราชการ"))
            if rec.state == "cancelled":
                raise UserError(_("ไม่สามารถส่งเอกสารที่ยกเลิกแล้ว"))
            if rec.state == "approved":
                raise UserError(_("เอกสารนี้ลงนามแล้ว"))
            if rec.state == "to_approve":
                continue
            rec._vpk_check_approver_table()
            if not rec.pdf_file:
                rec.action_generate_pdf()
            rec.review_ids.filtered(
                lambda review: review.status not in ("pending", "waiting")
            ).sudo().unlink()
            rec.with_context(skip_validation_check=True).write(
                {"state": "to_approve", "vpk_secretary_screen_state": False}
            )
            rec.request_validation()
            rec.message_post(body=_("ส่งเอกสารเพื่อลงนามตามลำดับผู้อนุมัติ"))
        return True

    def action_draft(self):
        for rec in self:
            if rec.state == "approved":
                raise UserError(_("เอกสารลงนามครบแล้ว ไม่สามารถกลับเป็นร่างได้"))
        self.mapped("review_ids").sudo().unlink()
        self.with_context(skip_validation_check=True).write(
            {"state": "draft", "vpk_secretary_screen_state": False}
        )
        return True

    def action_cancel(self):
        self.mapped("review_ids").filtered(
            lambda review: review.status in ("pending", "waiting")
        ).sudo().unlink()
        self.with_context(skip_validation_check=True).write({"state": "cancelled"})
        return True

    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers)
        for rec in self:
            rec.invalidate_recordset(["validation_status"])
            if rec.validation_status == "validated" and rec.state != "approved":
                rec.sudo().with_context(
                    skip_validation_check=True,
                    skip_check_state_condition=True,
                ).write({"state": "approved", "signed_on": fields.Datetime.now()})
                rec.sudo().message_post(body=_("ลงนามครบทุกลำดับแล้ว"))
        return res

    def _rejected_tier(self, tiers=False):
        res = super()._rejected_tier(tiers)
        for rec in self.filtered(lambda doc: doc.state == "to_approve"):
            partners = rec.review_ids.mapped("requested_by.partner_id")
            rec.sudo().with_context(skip_validation_check=True).write(
                {"state": "generated", "vpk_secretary_screen_state": False}
            )
            rec.sudo().message_post(
                body=_("เอกสารถูกตีกลับ กรุณาแก้ไขแล้วส่งลงนามใหม่"),
                partner_ids=partners.ids,
            )
        return res

    def action_open_pdf_viewer(self):
        self.ensure_one()
        return self._sign_viewer_action(can_sign=False)

    def _vpk_review_card_context(self):
        """Source record label shown before the document type in the inbox."""
        self.ensure_one()
        return ""

    def _vpk_review_card_info(self):
        """Inbox card and approval board texts for vpk_tier_validation."""
        self.ensure_one()
        values = self.value_json or {}
        signer = self.vpk_approver_line_ids.filtered("is_sign").sorted("sequence")[-1:].user_id
        return {
            "subject": values.get("subject") or self.template_id.name or "",
            "number": self.saraban_book_no or (self.name if self.name != "New" else ""),
            "department": values.get("department_name") or "",
            "type_label": self.document_type_id.name or self.template_id.name or self._description,
            "type_key": "%s:%s" % (self._name, self.document_type_id.code or ""),
            "context": self._vpk_review_card_context(),
            "signer_id": signer.id,
            "hide_on_board": self.state not in ("to_approve", "approved"),
        }

    # ------------------------------------------------------------------
    # Sign viewer and stamping
    # ------------------------------------------------------------------
    def _person_from_user(self, user):
        if not user:
            return "", ""
        employee = user.employee_id
        if not employee and "employee_ids" in user._fields:
            employee = user.employee_ids[:1]
        name = (employee.name if employee else "") or user.name or ""
        position = ""
        if employee:
            position = employee.job_title or (employee.job_id.name if employee.job_id else "")
        return name, position

    def _sign_viewer_action(self, can_sign=None):
        self.ensure_one()
        attachment = self._get_pdf_attachment()
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        if can_sign is None:
            can_sign = self.state == "to_approve" and bool(self.can_review)
        secretary_screen = bool(self.vpk_secretary_can_screen)
        return {
            "type": "ir.actions.client",
            "tag": "vpk_document_sign_pdf_viewer",
            "name": self.display_name,
            "params": {
                "attachment_id": attachment.id,
                "res_model": self._name,
                "res_id": self.id,
                "title": self.pdf_filename or self.display_name,
                "can_sign": bool(can_sign) and not secretary_screen,
                "secretary_screen": secretary_screen,
            },
        }

    def action_open_sign_viewer(self):
        self.ensure_one()
        return self._sign_viewer_action()

    def _signature_search_needles(self, user):
        name, _position = self._person_from_user(user)
        name = " ".join((name or "").split())
        return ["(%s)" % name, name] if name else []

    def action_apply_signature(self, signature, signature_box=None):
        self.ensure_one()
        if self.state != "to_approve":
            raise UserError(_("เอกสารต้องอยู่ในสถานะรออนุมัติจึงจะลงนามได้"))
        self.invalidate_recordset(["can_review"])
        if not self.can_review:
            raise UserError(_("คุณไม่มีสิทธิ์ลงนามเอกสารนี้"))
        raw = signature or ""
        if isinstance(raw, bytes):
            raw = raw.decode("ascii", errors="ignore")
        if raw.startswith("data:") and "," in raw:
            raw = raw.split(",", 1)[1]
        raw = raw.strip()
        if not raw:
            raise UserError(_("กรุณาลงลายเซ็น"))
        doc = self.sudo()
        if not doc.pdf_file:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        try:
            stamped = stamp_signature_on_pdf(
                base64.b64decode(doc.pdf_file),
                base64.b64decode(raw),
                self._signature_search_needles(self.env.user),
                custom_box=signature_box,
            )
        except SignatureStampError as error:
            raise UserError(str(error)) from error
        filename = doc.pdf_filename or "document.pdf"
        if "-signed" not in filename.lower():
            stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
            filename = "%s-signed.pdf" % stem
        doc.with_context(skip_validation_check=True).write(
            {"pdf_file": base64.b64encode(stamped), "pdf_filename": filename}
        )
        return self.sudo().validate_tier()

    def reject_tier(self):
        if self.env.su:
            return super().reject_tier()
        self.invalidate_recordset(["can_review"])
        if not self.can_review:
            raise UserError(_("คุณไม่มีสิทธิ์ตีกลับเอกสารนี้"))
        return super(DocumentStudioDocument, self.sudo()).reject_tier()

    def action_secretary_mark_checked(self):
        for rec in self:
            if not rec.vpk_secretary_can_screen:
                raise UserError(_("เฉพาะผู้ตรวจสอบที่ถึงคิวของเอกสารนี้"))
            rec.sudo().with_context(skip_validation_check=True).write(
                {"vpk_secretary_screen_state": "checked"}
            )
            rec.sudo().message_post(
                body=_("%s ตรวจสอบเอกสารแล้ว") % self.env.user.display_name
            )
        return True

    def action_secretary_send_director(self):
        for rec in self:
            if not rec.vpk_secretary_can_screen:
                raise UserError(_("เฉพาะผู้ตรวจสอบที่ถึงคิวของเอกสารนี้"))
            if rec.vpk_secretary_screen_state != "checked":
                raise UserError(_("กรุณากดตรวจสอบแล้วก่อนส่งต่อ"))
        res = self.sudo().validate_tier()
        self.sudo().with_context(skip_validation_check=True).write(
            {"vpk_secretary_screen_state": False}
        )
        return res

    # ------------------------------------------------------------------
    # Saraban numbering
    # ------------------------------------------------------------------
    def _saraban_org_code(self):
        self.ensure_one()
        return "ภก ๐๐๓๓.๒๐๑"

    def action_request_saraban_number(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("ไม่สามารถขอเลขสารบรรณจากเอกสารที่ยกเลิกแล้ว"))
        existing = self.saraban_document_id
        if existing and existing.state == "registered":
            raise UserError(
                _("เอกสารนี้มีเลขสารบรรณแล้ว (%s)")
                % (existing.book_no_display or existing.book_no)
            )
        vals = {
            "name": self.template_id.name or self.name,
            "purpose": "official_document",
            "source_ref": "%s/%s" % (self._name, self.id),
            "studio_document_id": self.id,
        }
        if existing and existing.state == "draft":
            saraban = existing
            saraban.write(vals)
        else:
            vals.update(
                {
                    "doc_type": "memo",
                    "org_code": self._saraban_org_code(),
                    "company_id": self.company_id.id,
                    "note": _("สร้างจากเอกสาร Document Studio %s") % self.name,
                }
            )
            saraban = self.env["saraban.document"].create(vals)
        saraban.action_register()
        number = saraban.book_no_display or saraban.book_no
        self.write({"saraban_book_no": number, "saraban_document_id": saraban.id})
        self.message_post(
            body=_("ขอเลขจากระบบสารบรรณสำเร็จ<br/>เลขที่สารบรรณ: <b>%s</b>") % number
        )
        return True

    def action_open_saraban_document(self):
        self.ensure_one()
        if not self.saraban_document_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "saraban.document",
            "res_id": self.saraban_document_id.id,
            "view_mode": "form",
            "target": "current",
        }
