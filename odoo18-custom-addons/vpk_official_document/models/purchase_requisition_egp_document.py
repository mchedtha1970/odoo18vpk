# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    company_id = fields.Many2one(
        related="egp_document_id.company_id",
        store=True,
    )

    def _is_director_secretary(self, user):
        secretary = self.env.ref(
            "vpk_tier_validation.user_director_secretary",
            raise_if_not_found=False,
        )
        return bool(secretary and user == secretary)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if not self.user_id:
            return
        _name, position = self.env["vpk.official.document"]._person_from_user(
            self.user_id
        )
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
        Document = self.env["vpk.official.document"]
        for vals in vals_list:
            if vals.get("user_id") and not vals.get("position"):
                user = self.env["res.users"].browse(vals["user_id"])
                _name, position = Document._person_from_user(user)
                if position:
                    vals["position"] = position
            if vals.get("is_check") and vals.get("is_sign"):
                vals["is_sign"] = False
            elif "is_check" not in vals and "is_sign" not in vals:
                user = self.env["res.users"].browse(vals.get("user_id"))
                if user and self._is_director_secretary(user):
                    vals["is_check"] = True
                    vals["is_sign"] = False
                else:
                    vals["is_sign"] = True
            if not vals.get("sequence") and vals.get("egp_document_id"):
                siblings = self.search(
                    [("egp_document_id", "=", vals["egp_document_id"])]
                )
                vals["sequence"] = max(siblings.mapped("sequence") or [0]) + 1
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("user_id") and "position" not in vals:
            user = self.env["res.users"].browse(vals["user_id"])
            _name, position = self.env["vpk.official.document"]._person_from_user(
                user
            )
            if position:
                vals = dict(vals, position=position)
        return super().write(vals)


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
    signer_line_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.document.signer",
        inverse_name="egp_document_id",
        string="รายชื่อผู้อนุมัติ",
        copy=True,
    )
    signer_summary = fields.Char(
        string="ลงนาม/อนุมัติ",
        compute="_compute_signer_summary",
    )

    @api.depends("signer_line_ids.user_id", "signer_line_ids.sequence")
    def _compute_signer_summary(self):
        for rec in self:
            lines = rec.signer_line_ids.filtered("user_id").sorted(
                key=lambda line: (line.sequence, line.id)
            )
            if lines:
                rec.signer_summary = " → ".join(lines.mapped("user_id.name"))
            else:
                rec.signer_summary = False

    def action_open_approver_modal(self):
        """เปิดหน้าต่างกำหนดรายชื่อผู้อนุมัติของเอกสารที่แนบจาก e-GP และกดส่งเข้ากล่องงานรออนุมัติ."""
        self.ensure_one()
        if not self.signer_line_ids:
            self._seed_default_egp_signers()
        view = self.env.ref(
            "vpk_official_document.view_purchase_requisition_egp_document_approver_form"
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
        company = self.company_id or self.env.company
        Official = self.env["vpk.official.document"]
        officer = Official._person_user_from_company(
            company, "official_doc_officer_id", "official_doc_officer_name"
        )
        head = Official._person_user_from_company(
            company, "official_doc_head_officer_id", "official_doc_head_officer_name"
        )
        secretary = Official._vpk_director_secretary_user()
        director = Official._person_user_from_company(
            company, "official_doc_signer_id", "official_doc_signer_name"
        )
        code = self.document_type_id.code
        candidates = []
        if code in ("wa_committee_order", "spec_price_committee", "winner_announcement"):
            candidates = [
                (secretary, "เลขาผู้อำนวยการ", True),
                (director, "ผู้อำนวยการ", False),
            ]
        elif code in (
            "specific_method_approval",
            "award_approval",
            "consider_procurement",
        ):
            candidates = [
                (officer, "เจ้าหน้าที่", False),
                (head, "หัวหน้าเจ้าหน้าที่", False),
                (secretary, "เลขาผู้อำนวยการ", True),
                (director, "ผู้อำนวยการ", False),
            ]
        elif code == "integrity_over_100k":
            candidates = [
                (officer, "เจ้าหน้าที่", False),
                (head, "หัวหน้าเจ้าหน้าที่", False),
            ]
        else:
            candidates = [
                (director, "ผู้อำนวยการ", False),
            ]
        Signer = self.env["purchase.requisition.egp.document.signer"]
        rows = []
        seen = set()
        seq = 1
        for user, fallback_pos, is_check in candidates:
            if not user or user.id in seen:
                continue
            seen.add(user.id)
            _name, pos = Official._person_from_user(user)
            rows.append(
                {
                    "egp_document_id": self.id,
                    "sequence": seq,
                    "user_id": user.id,
                    "position": pos or fallback_pos,
                    "is_check": is_check,
                    "is_sign": not is_check,
                }
            )
            seq += 1
        if rows:
            Signer.create(rows)

    def action_save_approvers_only(self):
        self.ensure_one()
        if self.official_document_id and self.signature_state not in ("waiting", "signed"):
            self._push_egp_signers_to_official_document(self.official_document_id)
        return {"type": "ir.actions.act_window_close"}

    def action_save_and_send_to_approver_inbox(self):
        """บันทึกผู้อนุมัติที่กำหนดไว้ และเปิดหน้าต่างส่งเอกสารเข้ากล่องงานรออนุมัติ."""
        self.ensure_one()
        if not self.document_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ในรายการเอกสารก่อนส่งให้ผู้อนุมัติ"))
        if not self.signer_line_ids.filtered("user_id"):
            raise UserError(_("กรุณาเพิ่มผู้อนุมัติอย่างน้อย 1 คนก่อนส่งอนุมัติ"))
        return self.action_send_for_signature_inbox()

    def _map_official_document_type_code(self):
        self.ensure_one()
        code = self.document_type_id.code or ""
        if code == "consider_procurement":
            return "award_approval"
        valid_codes = {
            key for key, _label in self.env["vpk.official.document"]._selection_document_type()
        }
        if code in valid_codes:
            return code
        return "specific_method_approval"

    def _ensure_attached_egp_official_document(self):
        """สร้างหรืออัปเดต vpk.official.document จากไฟล์ที่แนบในรายการเอกสาร e-GP พร้อมผู้อนุมัติที่เลือก."""
        self.ensure_one()
        Official = self.env["vpk.official.document"]
        requisition = self.requisition_id
        request = requisition.purchase_request_id
        doc_type = self._map_official_document_type_code()
        subject = "%s (%s)" % (
            self.document_type_id.name or _("เอกสาร e-GP"),
            self.egp_reference or requisition.egp_project_name or requisition.name or "",
        )
        vals = {
            "document_type": doc_type,
            "requisition_id": requisition.id,
            "request_id": request.id if request else False,
            "department_id": request.department_id.id if request and request.department_id else False,
            "department_name": request.department_id.name if request and request.department_id else False,
            "subject": subject.strip(),
            "date": self.document_date or fields.Date.context_today(self),
            "company_id": requisition.company_id.id,
        }
        document = self.official_document_id
        if document and document.signature_state in ("waiting", "signed"):
            return document
        if document:
            document.with_context(skip_validation_check=True).write(vals)
        else:
            document = Official.with_context(skip_validation_check=True).create(vals)
            self.official_document_id = document.id
        self._push_egp_signers_to_official_document(document)
        if self.document_file:
            basename = "%s-%s" % (
                self.document_type_id.name or "eGP",
                self.egp_reference or requisition.name or self.id,
            )
            filename = self.document_filename or ("%s.pdf" % basename)
            document.with_context(skip_validation_check=True)._store_generated_file(
                base64.b64decode(self.document_file),
                filename,
                "application/pdf",
                "pdf",
            )
        return document

    def _push_egp_signers_to_official_document(self, document):
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
        """เปิดตัวเลือกส่งลงนาม หรือข้ามการอนุมัติเพื่อทดสอบ สำหรับเอกสารทุกประเภทที่แนบไฟล์แล้ว."""
        self.ensure_one()
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
        code = self.document_type_id.code
        if self.signer_line_ids.filtered("user_id"):
            if not self.document_file and (
                not self.official_document_id or not self.official_document_id.pdf_file
            ):
                raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนส่งเข้ากล่องผู้อนุมัติ"))
            official = self._ensure_attached_egp_official_document()
        else:
            if not self.document_file:
                raise UserError(_("กรุณาแนบไฟล์ PDF และกดปุ่ม 'เพิ่มผู้อนุมัติ' ก่อนส่งเพื่อลงนาม"))
            return self.action_open_approver_modal()
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
        if self.signer_line_ids.filtered("user_id"):
            self._push_egp_signers_to_official_document(document)
        elif report:
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
        if self.signer_line_ids.filtered("user_id"):
            self._push_egp_signers_to_official_document(document)
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


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

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

    @api.depends(
        "award_report_ids.state",
        "egp_document_ids.document_type_code",
        "egp_document_ids.document_filename",
        "egp_document_ids.attachment_id",
        "egp_document_ids.signature_state",
        "egp_document_ids.official_document_id.state",
    )
    def _compute_egp_award_approved(self):
        return super()._compute_egp_award_approved()


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
