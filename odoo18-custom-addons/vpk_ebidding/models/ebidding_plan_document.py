# -*- coding: utf-8 -*-
import base64
import mimetypes

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.vpk_document_studio_sign.models.pdf_stamp import (
    SignatureStampError,
    stamp_text_on_pdf,
)

THAI_MONTHS = (
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)
THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


class EbiddingPlanDocumentType(models.Model):
    _name = "ebidding.plan.document.type"
    _description = "ประเภทเอกสาร e-GP ของแผนจัดซื้อจัดจ้าง"
    _order = "sequence, id"

    name = fields.Char(string="ประเภทเอกสาร", required=True, translate=True)
    code = fields.Char(string="รหัส", required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "รหัสประเภทเอกสารซ้ำ"),
    ]


class EbiddingPlanDocumentSigner(models.Model):
    _name = "ebidding.plan.document.signer"
    _description = "ผู้อนุมัติเอกสาร e-GP ของแผน"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="ebidding.plan.document",
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
        related="document_id.company_id",
        store=True,
    )

    def _is_director_secretary(self, user):
        secretary = self.env.ref(
            "vpk_tier_validation.user_director_secretary",
            raise_if_not_found=False,
        )
        return bool(secretary and user == secretary)

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
            if vals.get("user_id") and not vals.get("position"):
                user = self.env["res.users"].browse(vals["user_id"])
                position = self._position_for(user)
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
            if not vals.get("sequence") and vals.get("document_id"):
                siblings = self.search([("document_id", "=", vals["document_id"])])
                vals["sequence"] = max(siblings.mapped("sequence") or [0]) + 1
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("user_id") and "position" not in vals:
            position = self._position_for(self.env["res.users"].browse(vals["user_id"]))
            if position:
                vals = dict(vals, position=position)
        return super().write(vals)


class EbiddingPlanDocument(models.Model):
    _name = "ebidding.plan.document"
    _description = "เอกสาร e-GP ของแผนจัดซื้อจัดจ้าง"
    _order = "sequence, id"

    plan_id = fields.Many2one(
        comodel_name="ebidding.plan",
        string="ชุดแผน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    plan_line_id = fields.Many2one(
        comodel_name="ebidding.plan.line",
        string="รายการแผน",
        ondelete="set null",
        domain="[('plan_id', '=', plan_id)]",
        help="ระบุถ้าเอกสารนี้เป็นของแผนรายการใดรายการหนึ่ง",
    )
    sequence = fields.Integer(default=10)
    document_type_id = fields.Many2one(
        comodel_name="ebidding.plan.document.type",
        string="ประเภทเอกสาร",
        required=True,
        ondelete="restrict",
        index=True,
    )
    egp_reference = fields.Char(string="เลขอ้างอิง e-GP")
    document_number = fields.Char(
        string="เลขที่เอกสาร",
        help="เลขที่ที่ประทับลงบนไฟล์ PDF ที่แนบ",
    )
    document_date = fields.Date(string="วันที่เอกสาร")
    notes = fields.Text(string="หมายเหตุ")
    document_file = fields.Binary(string="ไฟล์แนบ (PDF)", attachment=True)
    document_filename = fields.Char(string="ชื่อไฟล์")
    stamp_source_file = fields.Binary(
        string="ไฟล์ต้นฉบับก่อนประทับ",
        attachment=True,
        copy=False,
    )
    stamp_source_filename = fields.Char(copy=False)
    number_stamp_box = fields.Json(copy=False)
    date_stamp_box = fields.Json(copy=False)
    number_stamped = fields.Boolean(copy=False)
    date_stamped = fields.Boolean(copy=False)
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="ไฟล์แนบ",
        readonly=True,
        copy=False,
    )
    studio_document_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="เอกสารลงนาม",
        copy=False,
        ondelete="set null",
        index=True,
    )
    signature_state = fields.Selection(
        related="studio_document_id.signature_state",
        string="สถานะการลงนาม",
        store=True,
    )
    signer_line_ids = fields.One2many(
        comodel_name="ebidding.plan.document.signer",
        inverse_name="document_id",
        string="รายชื่อผู้อนุมัติ",
        copy=True,
    )
    signer_summary = fields.Char(
        string="ลงนาม/อนุมัติ",
        compute="_compute_signer_summary",
    )
    company_id = fields.Many2one(
        related="plan_id.company_id",
        store=True,
    )

    @api.depends("signer_line_ids.user_id", "signer_line_ids.sequence")
    def _compute_signer_summary(self):
        for rec in self:
            lines = rec.signer_line_ids.filtered("user_id").sorted(
                key=lambda line: (line.sequence, line.id)
            )
            rec.signer_summary = (
                " → ".join(lines.mapped("user_id.name")) if lines else False
            )

    def unlink(self):
        studio_documents = self.mapped("studio_document_id")
        res = super().unlink()
        still_used = self.search([("studio_document_id", "in", studio_documents.ids)])
        (studio_documents - still_used.mapped("studio_document_id")).sudo().unlink()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence") and vals.get("plan_id"):
                max_sequence = max(
                    self.search(
                        [("plan_id", "=", vals["plan_id"])],
                        order="sequence desc",
                        limit=1,
                    ).mapped("sequence")
                    or [0]
                )
                vals["sequence"] = max_sequence + 10
        records = super().create(vals_list)
        records._sync_attachment()
        return records

    def write(self, vals):
        if "document_file" in vals and not self.env.context.get("vpk_stamping_pdf"):
            vals = dict(
                vals,
                stamp_source_file=False,
                stamp_source_filename=False,
                number_stamp_box=False,
                date_stamp_box=False,
                number_stamped=False,
                date_stamped=False,
            )
        res = super().write(vals)
        if {"document_file", "document_filename", "document_type_id"}.intersection(
            vals
        ):
            self._sync_attachment()
        return res

    def _mimetype_for_filename(self, filename):
        guessed, _encoding = mimetypes.guess_type(filename or "")
        return guessed or "application/pdf"

    def _sync_attachment(self):
        attachment_obj = self.env["ir.attachment"]
        for record in self:
            if not record.document_file:
                if record.attachment_id:
                    record.attachment_id.unlink()
                    record.attachment_id = False
                continue
            filename = (
                record.document_filename
                or record.document_type_id.name
                or "เอกสาร e-GP.pdf"
            )
            attachment_vals = {
                "name": filename,
                "type": "binary",
                "datas": record.document_file,
                "res_model": record._name,
                "res_id": record.id,
                "mimetype": self._mimetype_for_filename(filename),
            }
            if record.attachment_id:
                record.attachment_id.write(attachment_vals)
            else:
                record.attachment_id = attachment_obj.create(attachment_vals)

    def _format_thai_document_date(self, value):
        if not value:
            return ""
        text = "%d %s %d" % (
            value.day,
            THAI_MONTHS[value.month],
            value.year + 543,
        )
        return text.translate(THAI_DIGITS)

    def _stamp_payload_box(self, box):
        if not box or not isinstance(box, dict):
            return False
        return {
            "page_index": box.get("page_index", 0),
            "x_ratio": box.get("x_ratio"),
            "y_ratio": box.get("y_ratio"),
            "w_ratio": box.get("w_ratio"),
            "h_ratio": box.get("h_ratio"),
        }

    def action_open_stamp_number_viewer(self):
        self.ensure_one()
        if self.signature_state == "signed":
            raise UserError(_("เอกสารลงนามแล้ว ไม่สามารถแก้ไขเลขที่หรือวันที่บนไฟล์ได้"))
        if not self.attachment_id and not self.document_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนบันทึกเลขที่/วันที่เอกสาร"))
        if not self.attachment_id:
            self._sync_attachment()
        if not self.attachment_id:
            raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนบันทึกเลขที่/วันที่เอกสาร"))
        return {
            "type": "ir.actions.client",
            "tag": "vpk_ebidding_stamp_number_pdf_viewer",
            "name": _("บันทึกเลขที่/วันที่เอกสาร"),
            "params": {
                "attachment_id": self.attachment_id.id,
                "res_model": self._name,
                "res_id": self.id,
                "title": self.document_filename
                or self.document_type_id.name
                or _("เอกสาร e-GP"),
                "document_number": self.document_number or self.egp_reference or "",
                "document_date": self.document_date.isoformat()
                if self.document_date
                else "",
                "number_box": self.number_stamp_box or {},
                "date_box": self.date_stamp_box or {},
                "has_number_stamp": bool(self.number_stamped),
                "has_date_stamp": bool(self.date_stamped),
                "apply_method": "action_apply_document_stamps",
            },
        }

    def _ensure_stamp_source(self):
        self.ensure_one()
        if self.stamp_source_file or not self.document_file:
            return
        self.with_context(vpk_stamping_pdf=True).write(
            {
                "stamp_source_file": self.document_file,
                "stamp_source_filename": self.document_filename,
            }
        )

    def _push_stamped_file(self, pdf_bytes):
        self.ensure_one()
        filename = self.document_filename or self.stamp_source_filename or "เอกสาร e-GP.pdf"
        self.with_context(vpk_stamping_pdf=True).write(
            {
                "document_file": base64.b64encode(pdf_bytes),
                "document_filename": filename,
            }
        )
        self._sync_attachment()
        document = self.studio_document_id
        if document and document.signature_state == "not_sent":
            document.attach_uploaded_file(base64.b64encode(pdf_bytes), filename)

    def _rebuild_stamped_pdf(self):
        self.ensure_one()
        source = self.stamp_source_file or self.document_file
        if not source:
            raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนบันทึกเลขที่/วันที่เอกสาร"))
        pdf = base64.b64decode(source)
        try:
            if self.number_stamped and self.document_number and self.number_stamp_box:
                pdf = stamp_text_on_pdf(
                    pdf, self.document_number, self.number_stamp_box
                )
            if self.date_stamped and self.document_date and self.date_stamp_box:
                pdf = stamp_text_on_pdf(
                    pdf,
                    self._format_thai_document_date(self.document_date),
                    self.date_stamp_box,
                )
        except SignatureStampError as error:
            raise UserError(str(error)) from error
        self._push_stamped_file(pdf)
        return True

    def _stamp_dialog_result(self):
        self.ensure_one()
        return {
            "attachment_id": self.attachment_id.id if self.attachment_id else False,
            "document_number": self.document_number or "",
            "document_date": self.document_date.isoformat() if self.document_date else "",
            "number_box": self.number_stamp_box or {},
            "date_box": self.date_stamp_box or {},
            "has_number_stamp": bool(self.number_stamped),
            "has_date_stamp": bool(self.date_stamped),
        }

    def action_apply_document_stamps(self, payload=None):
        self.ensure_one()
        payload = payload or {}
        if self.signature_state == "signed":
            raise UserError(_("เอกสารลงนามแล้ว ไม่สามารถแก้ไขเลขที่หรือวันที่บนไฟล์ได้"))
        if not self.document_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนบันทึกเลขที่/วันที่เอกสาร"))

        number = " ".join((payload.get("document_number") or "").split())
        number_box = self._stamp_payload_box(payload.get("number_box"))
        document_date = payload.get("document_date")
        date_value = fields.Date.to_date(document_date) if document_date else False
        date_box = self._stamp_payload_box(payload.get("date_box"))

        if number and not number_box:
            raise UserError(_("กรุณากำหนดกรอบตำแหน่งเลขที่เอกสารบนหน้าเอกสาร"))
        if date_value and not date_box:
            raise UserError(_("กรุณากำหนดกรอบตำแหน่งวันที่เอกสารบนหน้าเอกสาร"))
        if not number and not date_value and not self.number_stamped and not self.date_stamped:
            raise UserError(_("กรุณาระบุเลขที่เอกสารหรือวันที่เอกสารอย่างน้อย 1 รายการ"))
        if (number_box and not number) or (date_box and not date_value):
            raise UserError(_("กรุณาใส่ค่าในช่องที่มีการกำหนดกรอบแล้ว"))

        self._ensure_stamp_source()
        vals = {}
        if number and number_box:
            vals.update(
                {
                    "document_number": number,
                    "number_stamp_box": number_box,
                    "number_stamped": True,
                }
            )
        if date_value and date_box:
            vals.update(
                {
                    "document_date": date_value,
                    "date_stamp_box": date_box,
                    "date_stamped": True,
                }
            )
        if vals:
            self.with_context(vpk_stamping_pdf=True).write(vals)
        self._rebuild_stamped_pdf()
        return True

    def action_remove_number_stamp(self, from_dialog=False):
        self.ensure_one()
        if self.signature_state == "signed":
            raise UserError(_("เอกสารลงนามแล้ว ไม่สามารถแก้ไขเลขที่บนไฟล์ได้"))
        if not self.stamp_source_file:
            raise UserError(
                _("ไม่พบไฟล์ต้นฉบับ จึงลบเลขที่ออกจากไฟล์ไม่ได้ กรุณาแนบไฟล์ใหม่แล้วประทับอีกครั้ง")
            )
        if not self.number_stamped:
            raise UserError(_("ยังไม่มีเลขที่เอกสารที่ประทับบนไฟล์"))
        self.with_context(vpk_stamping_pdf=True).write(
            {
                "number_stamped": False,
                "number_stamp_box": False,
            }
        )
        self._rebuild_stamped_pdf()
        if from_dialog:
            return self._stamp_dialog_result()
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def action_remove_date_stamp(self, from_dialog=False):
        self.ensure_one()
        if self.signature_state == "signed":
            raise UserError(_("เอกสารลงนามแล้ว ไม่สามารถแก้ไขวันที่บนไฟล์ได้"))
        if not self.stamp_source_file:
            raise UserError(
                _("ไม่พบไฟล์ต้นฉบับ จึงลบวันที่ออกจากไฟล์ไม่ได้ กรุณาแนบไฟล์ใหม่แล้วประทับอีกครั้ง")
            )
        if not self.date_stamped:
            raise UserError(_("ยังไม่มีวันที่เอกสารที่ประทับบนไฟล์"))
        self.with_context(vpk_stamping_pdf=True).write(
            {
                "date_stamped": False,
                "date_stamp_box": False,
            }
        )
        self._rebuild_stamped_pdf()
        if from_dialog:
            return self._stamp_dialog_result()
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    def action_apply_document_number(self, document_number, custom_box):
        """Backward-compatible wrapper used by older client actions."""
        return self.action_apply_document_stamps(
            {
                "document_number": document_number,
                "number_box": custom_box,
            }
        )

    def action_preview_document(self):
        self.ensure_one()
        if not self.attachment_id and not self.document_file:
            raise UserError(_("กรุณาแนบไฟล์ก่อนเปิดดู"))
        if not self.attachment_id:
            self._sync_attachment()
        if not self.attachment_id:
            raise UserError(_("กรุณาแนบไฟล์ก่อนเปิดดู"))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.attachment_id.id,
            "target": "new",
        }

    def action_open_approver_modal(self):
        self.ensure_one()
        if not self.signer_line_ids:
            self._seed_default_signers()
        view = self.env.ref("vpk_ebidding.view_ebidding_plan_document_approver_form")
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

    def _seed_default_signers(self):
        self.ensure_one()
        if self.signer_line_ids:
            return
        company = self.company_id or self.env.company
        Values = self.env["vpk.procurement.document.values"]
        officer = Values.company_person(company, "officer")[0]
        head = Values.company_person(company, "head_officer")[0]
        secretary = Values.director_secretary()
        director = Values.company_person(company, "signer")[0]
        candidates = [
            (officer, "เจ้าหน้าที่", False),
            (head, "หัวหน้าเจ้าหน้าที่", False),
            (secretary, "เลขาผู้อำนวยการ", True),
            (director, "ผู้อำนวยการ", False),
        ]
        Signer = self.env["ebidding.plan.document.signer"]
        rows = []
        seen = set()
        seq = 1
        for user, fallback_pos, is_check in candidates:
            if not user or user.id in seen:
                continue
            seen.add(user.id)
            pos = Values.person_from_user(user)[1]
            rows.append(
                {
                    "document_id": self.id,
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
        if self.studio_document_id and self.signature_state == "not_sent":
            self._push_signers_to_studio_document(self.studio_document_id)
        return {"type": "ir.actions.act_window_close"}

    def action_save_and_send_to_approver_inbox(self):
        self.ensure_one()
        if not self.document_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ในรายการเอกสารก่อนส่งให้ผู้อนุมัติ"))
        if not self.signer_line_ids.filtered("user_id"):
            raise UserError(_("กรุณาเพิ่มผู้อนุมัติอย่างน้อย 1 คนก่อนส่งอนุมัติ"))
        return self.action_send_for_signature_inbox()

    def _studio_document_type(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        return self.env["vpk.document.studio.document.type"].search(
            [("code", "=", "egp_plan_approval"), ("company_id", "in", [False, company.id])],
            limit=1,
        )

    def _ensure_studio_document(self):
        self.ensure_one()
        document = self.studio_document_id
        if document and document.signature_state != "not_sent":
            return document
        plan = self.plan_id
        if not document:
            document_type = self._studio_document_type()
            if not document_type:
                raise UserError(_("ยังไม่ได้ตั้งค่าประเภทเอกสาร egp_plan_approval ใน Document Studio"))
            document = self.env["vpk.document.studio.document"].create(
                {
                    "source_mode": "uploaded",
                    "document_type_id": document_type.id,
                    "source_ref": "%s,%d" % (self._name, self.id),
                    "date": self.document_date or fields.Date.context_today(self),
                    "company_id": plan.company_id.id,
                }
            )
            self.studio_document_id = document.id
        if self.document_file:
            basename = "%s-%s" % (
                self.document_type_id.name or "eGP",
                self.egp_reference or plan.code or self.id,
            )
            document.attach_uploaded_file(
                self.document_file, self.document_filename or ("%s.pdf" % basename)
            )
        self._push_signers_to_studio_document(document)
        return document

    def _push_signers_to_studio_document(self, document):
        self.ensure_one()
        if not document or document.signature_state != "not_sent":
            return document
        lines = self.signer_line_ids.filtered("user_id").sorted(
            key=lambda line: (line.sequence, line.id)
        )
        if not lines:
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

    def action_send_for_signature_inbox(self):
        self.ensure_one()
        if self.signature_state == "signed":
            raise UserError(_("เอกสารนี้ลงนามแล้ว"))
        if self.signature_state == "waiting":
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว กำลังรอลงนาม"))
        if not self.signer_line_ids.filtered("user_id"):
            if not self.document_file:
                raise UserError(
                    _("กรุณาแนบไฟล์ PDF และกดปุ่ม 'เพิ่มผู้อนุมัติ' ก่อนส่งเพื่อลงนาม")
                )
            return self.action_open_approver_modal()
        if not self.document_file and not self.studio_document_id.pdf_file:
            raise UserError(_("กรุณาแนบไฟล์ PDF ก่อนส่งเข้ากล่องผู้อนุมัติ"))
        self._ensure_studio_document().action_send_for_signature()
        return {"type": "ir.actions.act_window_close"}
