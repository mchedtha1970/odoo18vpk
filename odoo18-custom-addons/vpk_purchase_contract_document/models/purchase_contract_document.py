# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import mimetypes

from odoo import _, api, fields, models
from odoo.exceptions import UserError

FALLBACK_STUDIO_TYPE_CODE = "contract_document"


class PurchaseContractDocumentSigner(models.Model):
    _name = "purchase.contract.document.signer"
    _description = "ผู้อนุมัติเอกสารสัญญา"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="purchase.contract.document",
        string="เอกสารสัญญา",
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
    company_id = fields.Many2one(related="document_id.company_id", store=True)

    def _is_director_secretary(self, user):
        return bool(user) and user == self.env[
            "vpk.procurement.document.values"
        ].director_secretary()

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


class PurchaseContractDocument(models.Model):
    _name = "purchase.contract.document"
    _description = "เอกสารสัญญา"
    _order = "sequence, id"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญา",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    document_type_id = fields.Many2one(
        comodel_name="vpk.document.studio.document.type",
        string="ประเภทเอกสาร",
        required=True,
        ondelete="restrict",
        index=True,
    )
    egp_reference = fields.Char(string="เลขอ้างอิง e-GP")
    document_date = fields.Date(string="วันที่เอกสาร")
    notes = fields.Text(string="หมายเหตุ")
    document_file = fields.Binary(string="ไฟล์แนบ (PDF)", attachment=True)
    document_filename = fields.Char(string="ชื่อไฟล์")
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
        comodel_name="purchase.contract.document.signer",
        inverse_name="document_id",
        string="รายชื่อผู้อนุมัติ",
        copy=True,
    )
    signer_summary = fields.Char(
        string="ลงนาม/อนุมัติ",
        compute="_compute_signer_summary",
    )
    company_id = fields.Many2one(related="contract_id.company_id", store=True)

    @api.depends("studio_document_id.signature_state")
    def _compute_signature_state(self):
        for rec in self:
            rec.signature_state = rec.studio_document_id.signature_state or "not_sent"

    @api.depends("signer_line_ids.user_id", "signer_line_ids.sequence")
    def _compute_signer_summary(self):
        for rec in self:
            lines = rec.signer_line_ids.filtered("user_id").sorted(
                key=lambda line: (line.sequence, line.id)
            )
            rec.signer_summary = (
                " → ".join(lines.mapped("user_id.name")) if lines else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            contract = self.env["purchase.contract"].browse(vals.get("contract_id"))
            if not vals.get("sequence") and contract:
                vals["sequence"] = max(contract.contract_document_ids.mapped("sequence") or [0]) + 10
            if not vals.get("egp_reference") and contract:
                vals["egp_reference"] = (
                    contract.egp_contract_control_no or contract.egp_reference or False
                )
        records = super().create(vals_list)
        records._sync_attachment()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"document_file", "document_filename", "document_type_id"}.intersection(vals):
            self._sync_attachment()
        return res

    def unlink(self):
        studio_documents = self.mapped("studio_document_id")
        res = super().unlink()
        still_used = self.search([("studio_document_id", "in", studio_documents.ids)])
        (studio_documents - still_used.mapped("studio_document_id")).sudo().unlink()
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
                or "เอกสารสัญญา.pdf"
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

    def action_preview_document(self):
        self.ensure_one()
        if not self.attachment_id and self.document_file:
            self._sync_attachment()
        if not self.attachment_id:
            raise UserError(_("กรุณาแนบไฟล์ก่อนเปิดดู"))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.attachment_id.id,
            "target": "new",
        }

    def action_open_studio_document(self):
        self.ensure_one()
        if not self.studio_document_id:
            raise UserError(_("เอกสารนี้ไม่ได้สร้างจาก Document Studio"))
        return self.studio_document_id._action_open_form()

    # ------------------------------------------------------------------
    # Approvers
    # ------------------------------------------------------------------
    def action_open_approver_modal(self):
        self.ensure_one()
        if not self.signer_line_ids:
            self._seed_default_signers()
        view = self.env.ref(
            "vpk_purchase_contract_document.view_purchase_contract_document_approver_form"
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

    def _studio_template(self):
        self.ensure_one()
        if self.studio_document_id.template_id:
            return self.studio_document_id.template_id
        company = self.company_id or self.env.company
        return self.document_type_id.template_ids.filtered(
            lambda tmpl: tmpl.active
            and tmpl.company_id in (company, self.env["res.company"])
        )[:1]

    def _seed_default_signers(self):
        self.ensure_one()
        if self.signer_line_ids:
            return
        Signer = self.env["purchase.contract.document.signer"]
        studio_lines = self.studio_document_id.vpk_approver_line_ids.filtered("user_id")
        if studio_lines:
            Signer.create(
                [
                    {
                        "document_id": self.id,
                        "sequence": index,
                        "user_id": line.user_id.id,
                        "position": line.position or "",
                        "is_check": line.is_check,
                        "is_sign": line.is_sign,
                    }
                    for index, line in enumerate(
                        studio_lines.sorted(key=lambda rec: (rec.sequence, rec.id)),
                        start=1,
                    )
                ]
            )
            return
        template = self._studio_template()
        rows = template._vpk_approver_row_vals() if template else []
        if rows:
            Signer.create(
                [
                    {"document_id": self.id, **vals, "sequence": index}
                    for index, vals in enumerate(rows, start=1)
                ]
            )

    def _push_signers_to_studio_document(self, document):
        self.ensure_one()
        lines = self.signer_line_ids.filtered("user_id").sorted(
            key=lambda line: (line.sequence, line.id)
        )
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

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------
    def _studio_document_type_for_upload(self):
        self.ensure_one()
        if self.document_type_id:
            return self.document_type_id
        company = self.company_id or self.env.company
        return self.env["vpk.document.studio.document.type"].search(
            [
                ("code", "=", FALLBACK_STUDIO_TYPE_CODE),
                ("company_id", "in", [False, company.id]),
            ],
            limit=1,
        )

    def _ensure_studio_document(self):
        self.ensure_one()
        document = self.studio_document_id
        if document and document.signature_state != "not_sent":
            return document
        contract = self.contract_id
        if not document:
            document_type = self._studio_document_type_for_upload()
            if not document_type:
                raise UserError(_("ยังไม่ได้ตั้งค่าประเภทเอกสารสัญญาใน Document Studio"))
            document = self.env["vpk.document.studio.document"].create(
                {
                    "source_mode": "uploaded",
                    "document_type_id": document_type.id,
                    "source_ref": "%s,%d" % (contract._name, contract.id),
                    "date": self.document_date or fields.Date.context_today(self),
                    "company_id": contract.company_id.id,
                }
            )
            self.studio_document_id = document.id
        if self.document_file and document.source_mode == "uploaded":
            filename = self.document_filename or "%s-%s.pdf" % (
                self.document_type_id.name or _("เอกสารสัญญา"),
                contract.name or self.id,
            )
            document.with_context(vpk_contract_file_sync=True).attach_uploaded_file(
                self.document_file, filename
            )
        self._push_signers_to_studio_document(document)
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
