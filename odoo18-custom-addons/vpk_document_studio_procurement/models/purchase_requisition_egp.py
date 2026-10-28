import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DIRECTOR_ONLY_EGP_CODES = ("wa_committee_order", "spec_price_committee", "winner_announcement")
FULL_CHAIN_EGP_CODES = ("specific_method_approval", "award_approval", "consider_procurement")
STUDIO_TYPE_FOR_EGP_CODE = {"consider_procurement": "award_approval"}


class DocumentStudioDocumentType(models.Model):
    _inherit = "vpk.document.studio.document.type"

    egp_document_type_ids = fields.Many2many(
        comodel_name="purchase.requisition.egp.document.type",
        relation="vpk_studio_doc_type_egp_type_rel",
        column1="studio_type_id",
        column2="egp_type_id",
        string="ประเภทเอกสาร e-GP",
        help="เมื่อเพิ่มเอกสารในกระบวนการ e-GP ด้วยประเภทเหล่านี้ จะแสดงแบบฟอร์มของประเภทนี้ให้เลือก",
    )


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    @api.model
    def _templates_for_linked_type(self, field_name, linked_type, company):
        if not linked_type:
            return self.browse()
        return self.search(
            [
                ("active", "=", True),
                ("company_id", "in", [False, company.id]),
                ("document_type_id.%s" % field_name, "in", linked_type.ids),
            ]
        )


class PurchaseRequisitionEgpDocumentSigner(models.Model):
    _name = "purchase.requisition.egp.document.signer"
    _description = "ผู้อนุมัติเอกสารจากระบบ e-GP"
    _order = "sequence, id"

    egp_document_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.document",
        string="เอกสาร e-GP",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับอนุมัติ", default=1)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        required=True,
        ondelete="restrict",
        domain=[("share", "=", False)],
    )
    position = fields.Char(string="ตำแหน่ง")
    is_check = fields.Boolean(string="ตรวจสอบ")
    is_sign = fields.Boolean(string="ลงนาม", default=True)
    company_id = fields.Many2one(related="egp_document_id.company_id", store=True)

    def _is_director_secretary(self, user):
        return bool(user) and user == self.env["vpk.procurement.document.values"].director_secretary()

    def _position_for(self, user):
        return self.env["vpk.procurement.document.values"].person_from_user(user)[1]

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if not self.user_id:
            return
        position = self._position_for(self.user_id)
        if position:
            self.position = position
        if self._is_director_secretary(self.user_id):
            self.is_check = True
            self.is_sign = False
        elif not self.is_check:
            self.is_sign = True

    @api.onchange("is_check")
    def _onchange_is_check(self):
        if self.is_check:
            self.is_sign = False

    @api.onchange("is_sign")
    def _onchange_is_sign(self):
        if self.is_sign:
            self.is_check = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            user = self.env["res.users"].browse(vals.get("user_id"))
            if user and not vals.get("position"):
                position = self._position_for(user)
                if position:
                    vals["position"] = position
            if vals.get("is_check") and vals.get("is_sign"):
                vals["is_sign"] = False
            elif "is_check" not in vals and "is_sign" not in vals:
                secretary = self._is_director_secretary(user)
                vals["is_check"] = secretary
                vals["is_sign"] = not secretary
            if not vals.get("sequence") and vals.get("egp_document_id"):
                siblings = self.search([("egp_document_id", "=", vals["egp_document_id"])])
                vals["sequence"] = max(siblings.mapped("sequence") or [0]) + 1
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("user_id") and "position" not in vals:
            position = self._position_for(self.env["res.users"].browse(vals["user_id"]))
            if position:
                vals = dict(vals, position=position)
        return super().write(vals)


class PurchaseRequisitionEgpDocument(models.Model):
    _inherit = "purchase.requisition.egp.document"

    studio_document_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="เอกสารลงนาม",
        copy=False,
        ondelete="set null",
        index=True,
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
    signer_line_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.document.signer",
        inverse_name="egp_document_id",
        string="รายชื่อผู้อนุมัติ",
        copy=True,
    )
    signer_summary = fields.Char(string="ลงนาม/อนุมัติ", compute="_compute_signer_summary")

    @api.depends("studio_document_id.signature_state")
    def _compute_signature_state(self):
        for rec in self:
            rec.signature_state = rec.studio_document_id.signature_state or "not_sent"

    def unlink(self):
        studio_documents = self.mapped("studio_document_id")
        res = super().unlink()
        still_used = self.search([("studio_document_id", "in", studio_documents.ids)])
        (studio_documents - still_used.mapped("studio_document_id")).sudo().unlink()
        return res

    @api.depends("signer_line_ids.user_id", "signer_line_ids.sequence")
    def _compute_signer_summary(self):
        for rec in self:
            lines = rec.signer_line_ids.filtered("user_id").sorted(
                key=lambda line: (line.sequence, line.id)
            )
            rec.signer_summary = " → ".join(lines.mapped("user_id.name")) if lines else False

    # ------------------------------------------------------------------
    # Approver table
    # ------------------------------------------------------------------
    def action_open_approver_modal(self):
        self.ensure_one()
        if not self.signer_line_ids:
            self._seed_default_egp_signers()
        view = self.env.ref(
            "vpk_document_studio_procurement.view_purchase_requisition_egp_document_approver_form"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("กำหนดผู้อนุมัติเอกสาร — %s")
            % (self.document_type_id.name or self.display_name),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "new",
        }

    def _seed_default_egp_signers(self):
        self.ensure_one()
        if self.signer_line_ids:
            return
        Values = self.env["vpk.procurement.document.values"]
        company = self.company_id or self.env.company
        officer = Values.company_person(company, "officer")[0]
        head = Values.company_person(company, "head_officer")[0]
        director = Values.company_person(company, "signer")[0]
        secretary = Values.director_secretary()
        code = self.document_type_id.code
        if code in DIRECTOR_ONLY_EGP_CODES:
            candidates = [(secretary, "เลขาผู้อำนวยการ", True), (director, "ผู้อำนวยการ", False)]
        elif code in FULL_CHAIN_EGP_CODES:
            candidates = [
                (officer, "เจ้าหน้าที่", False),
                (head, "หัวหน้าเจ้าหน้าที่", False),
                (secretary, "เลขาผู้อำนวยการ", True),
                (director, "ผู้อำนวยการ", False),
            ]
        elif code == "integrity_over_100k":
            candidates = [(officer, "เจ้าหน้าที่", False), (head, "หัวหน้าเจ้าหน้าที่", False)]
        else:
            candidates = [(director, "ผู้อำนวยการ", False)]
        rows = []
        seen = set()
        for user, fallback_position, is_check in candidates:
            if not user or user.id in seen:
                continue
            seen.add(user.id)
            rows.append(
                {
                    "egp_document_id": self.id,
                    "sequence": len(rows) + 1,
                    "user_id": user.id,
                    "position": Values.person_from_user(user)[1] or fallback_position,
                    "is_check": is_check,
                    "is_sign": not is_check,
                }
            )
        if rows:
            self.env["purchase.requisition.egp.document.signer"].create(rows)

    def action_save_approvers_only(self):
        self.ensure_one()
        if self.studio_document_id and self.signature_state == "not_sent":
            self._push_egp_signers_to_studio_document(self.studio_document_id)
        return {"type": "ir.actions.act_window_close"}

    def action_save_and_send_to_approver_inbox(self):
        self.ensure_one()
        if not self.document_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ในรายการเอกสารก่อนส่งให้ผู้อนุมัติ"))
        if not self.signer_line_ids.filtered("user_id"):
            raise UserError(_("กรุณาเพิ่มผู้อนุมัติอย่างน้อย 1 คนก่อนส่งอนุมัติ"))
        return self.action_send_for_signature_inbox()

    @api.model
    def _push_signer_lines(self, lines, document):
        lines = lines.filtered("user_id").sorted(key=lambda line: (line.sequence, line.id))
        if not document or document.signature_state != "not_sent" or not lines:
            return document
        document.vpk_approver_line_ids.sudo().unlink()
        self.env["vpk.approval.line"].sudo().create(
            [
                {
                    "res_model": document._name,
                    "res_id": document.id,
                    "sequence": index,
                    "user_id": line.user_id.id,
                    "position": line.position or "",
                    "is_check": line.is_check,
                    "is_sign": line.is_sign,
                }
                for index, line in enumerate(lines, start=1)
            ]
        )
        return document

    def _push_egp_signers_to_studio_document(self, document):
        self.ensure_one()
        return self._push_signer_lines(self.signer_line_ids, document)

    # ------------------------------------------------------------------
    # Studio document for an attached e-GP file
    # ------------------------------------------------------------------
    def _studio_document_type(self):
        self.ensure_one()
        code = self.document_type_id.code or ""
        code = STUDIO_TYPE_FOR_EGP_CODE.get(code, code)
        Type = self.env["vpk.document.studio.document.type"]
        company = self.company_id or self.env.company
        domain = [("company_id", "in", [False, company.id])]
        return (
            Type.search(domain + [("code", "=", code)], limit=1)
            or Type.search(domain + [("egp_document_type_ids", "in", self.document_type_id.ids)], limit=1)
            or Type.search(domain + [("code", "=", "egp_document")], limit=1)
        )

    def _studio_document_vals(self, document_type):
        requisition = self.requisition_id
        request = requisition.purchase_request_id
        return {
            "source_mode": "uploaded",
            "document_type_id": document_type.id,
            "source_ref": "purchase.requisition,%d" % requisition.id,
            "requisition_id": requisition.id,
            "request_id": request.id if request else False,
            "date": self.document_date or fields.Date.context_today(self),
            "company_id": requisition.company_id.id,
        }

    def _ensure_attached_egp_studio_document(self):
        """Wrap the attached e-GP file in an uploaded studio document with the approvers."""
        self.ensure_one()
        document = self.studio_document_id
        if document and document.signature_state != "not_sent":
            return document
        document_type = self._studio_document_type()
        if not document_type:
            raise UserError(_("ยังไม่ได้ตั้งค่าประเภทเอกสารสำหรับเอกสาร e-GP ใน Document Studio"))
        if not document:
            document = self.env["vpk.document.studio.document"].create(
                self._studio_document_vals(document_type)
            )
            self.studio_document_id = document.id
        if self.document_file and document.source_mode == "uploaded":
            filename = self.document_filename or "%s-%s.pdf" % (
                self.document_type_id.name or "eGP",
                self.egp_reference or self.requisition_id.name or self.id,
            )
            document.with_context(vpk_egp_file_sync=True).attach_uploaded_file(
                self.document_file, filename
            )
        self._push_egp_signers_to_studio_document(document)
        return document

    def action_send_for_signature_inbox(self):
        self.ensure_one()
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
        if not self.signer_line_ids.filtered("user_id"):
            if not self.document_file:
                raise UserError(_("กรุณาแนบไฟล์ PDF และกดปุ่ม 'เพิ่มผู้อนุมัติ' ก่อนส่งเพื่อลงนาม"))
            return self.action_open_approver_modal()
        if not self.document_file and not self.studio_document_id.pdf_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนส่งเข้ากล่องผู้อนุมัติ"))
        document = self._ensure_attached_egp_studio_document()
        document.action_send_for_signature()
        return {"type": "ir.actions.act_window_close"}

    # ------------------------------------------------------------------
    # Award approval report
    # ------------------------------------------------------------------
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
        self._ensure_award_studio_document().action_send_for_signature()
        return True

    def _ensure_award_studio_document(self):
        self.ensure_one()
        if self.document_type_id.code != "award_approval":
            return self.env["vpk.document.studio.document"]
        document = self._ensure_attached_egp_studio_document()
        report = self.award_report_id
        if not self.signer_line_ids.filtered("user_id") and report:
            self._push_signer_lines(report.signer_line_ids, document)
        return document

    # ------------------------------------------------------------------
    # Winner announcement (Studio form)
    # ------------------------------------------------------------------
    def _winner_studio_values(self):
        values = self._winner_announcement_values()
        return {
            "agency": self._company_person_name(
                self.company_id, "official_doc_agency", self.company_id.name or ""
            ),
            "subject": values.get("subject") or "",
            "body_intro": values.get("body_intro") or "",
            "body_winner": values.get("body_winner") or "",
            "announce_date_th": values.get("announce_date") or "",
            "signer_name": values.get("signer_full") or values.get("signer_name") or "",
            "signer_position": values.get("signer_title") or "",
            "approver_acting": values.get("signer_acting") or "",
        }

    def _ensure_winner_studio_document(self):
        self.ensure_one()
        document = self.studio_document_id
        if document and document.signature_state != "not_sent":
            return document
        Document = self.env["vpk.document.studio.document"]
        requisition = self.requisition_id
        values = self._winner_studio_values()
        if document and document.template_id:
            document.value_json = dict(document.value_json or {}, **values)
            document.body = document._filled_body_html(convert_word=True)
        else:
            document_type = self._studio_document_type()
            if not document_type:
                raise UserError(_("ยังไม่ได้ตั้งค่าประเภทเอกสารประกาศผู้ชนะใน Document Studio"))
            document = Document._vpk_create_for_record(
                requisition,
                document_type,
                extra={"value_json": values, "date": self.document_date or fields.Date.context_today(self)},
            )
            self.studio_document_id = document.id
        if self.signer_line_ids.filtered("user_id"):
            self._push_egp_signers_to_studio_document(document)
        return document

    def _build_winner_studio_document(self):
        self.ensure_one()
        document = self._ensure_winner_studio_document()
        if document.signature_state != "not_sent":
            return document
        try:
            document.action_generate_pdf()
        except UserError:
            document.action_generate_docx()
        content = document.pdf_file or document.docx_file
        filename = document.pdf_filename if document.pdf_file else document.docx_filename
        if content:
            self.write(
                {
                    "document_file": content,
                    "document_filename": filename,
                    "document_date": self.document_date or fields.Date.context_today(self),
                }
            )
        return document

    def action_generate_winner_document(self):
        self.ensure_one()
        if self.document_type_id.code != "winner_announcement":
            return super().action_generate_winner_document()
        if self.signature_state != "not_sent":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว ไม่สามารถสร้างใหม่ได้"))
        return self._build_winner_studio_document()._action_open_form()

    def action_send_for_signature(self):
        self.ensure_one()
        if self.document_type_id.code != "winner_announcement":
            raise UserError(_("ปุ่มนี้ใช้ส่งประกาศผู้ชนะลงนามเท่านั้น"))
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
        document = self.studio_document_id
        if not document or not document.pdf_file:
            document = self._build_winner_studio_document()
        if not document.pdf_file:
            raise UserError(_("ไม่สามารถสร้างไฟล์ PDF ของประกาศผู้ชนะได้"))
        document.action_send_for_signature()
        return True


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    studio_document_ids = fields.One2many(
        comodel_name="vpk.document.studio.document",
        inverse_name="requisition_id",
        string="เอกสาร Document Studio",
    )

    def action_open_add_egp_document_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เพิ่มเอกสาร"),
            "res_model": "vpk.egp.document.add.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_requisition_id": self.id},
        }

    def _egp_document_is_signed(self, document):
        if getattr(document, "signature_state", False) == "signed":
            return True
        studio = getattr(document, "studio_document_id", False)
        return bool(studio) and studio.state == "approved"

    @api.depends(
        "award_report_ids.state",
        "egp_document_ids.document_type_code",
        "egp_document_ids.document_filename",
        "egp_document_ids.attachment_id",
        "egp_document_ids.signature_state",
        "egp_document_ids.studio_document_id.state",
    )
    def _compute_egp_award_approved(self):
        return super()._compute_egp_award_approved()
