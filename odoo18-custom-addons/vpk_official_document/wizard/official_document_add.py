from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VpkOfficialDocumentAddWizard(models.TransientModel):
    _name = "vpk.official.document.add.wizard"
    _description = "เพิ่มเอกสารราชการในใบขอซื้อ"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="request_id.company_id")
    document_type_id = fields.Many2one(
        comodel_name="vpk.official.document.type",
        string="ประเภทเอกสาร",
        required=True,
        domain="[('create_from_purchase_request', '=', True)]",
    )
    add_mode = fields.Selection(
        selection=[
            ("studio", "ดึงจาก Document Studio"),
            ("attach", "แนบไฟล์ต้นทาง"),
        ],
        string="วิธีเพิ่มเอกสาร",
        required=True,
        default="studio",
    )
    studio_template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม Document Studio",
        domain="[('active', '=', True), ('company_id', 'in', [False, company_id])]",
    )
    file = fields.Binary(string="ไฟล์ต้นทาง")
    filename = fields.Char(string="ชื่อไฟล์")
    notes = fields.Text(string="หมายเหตุ")

    @api.onchange("add_mode")
    def _onchange_add_mode(self):
        if self.add_mode != "studio":
            self.studio_template_id = False
        if self.add_mode != "attach":
            self.file = False
            self.filename = False

    def action_confirm(self):
        self.ensure_one()
        request = self.request_id
        document_type = self.document_type_id
        if not document_type:
            raise UserError(_("กรุณาเลือกประเภทเอกสาร"))
        if self.add_mode == "attach":
            return self._action_attach(request, document_type)
        return self._action_from_studio(request, document_type)

    def _action_from_studio(self, request, document_type):
        if not self.studio_template_id:
            raise UserError(_("กรุณาเลือกแบบฟอร์มจาก Document Studio"))
        Document = self.env["vpk.official.document"]
        Studio = self.env["vpk.document.studio.document"]
        existing = Document._find_existing_document(
            document_type.code, request=request
        )
        if existing and existing.state not in ("draft", "generated"):
            raise UserError(
                _("มี %s ในใบขอซื้อนี้อยู่แล้ว และไม่สามารถแทนที่ได้")
                % document_type.display_name
            )
        values = Studio._values_from_purchase_request(
            self.studio_template_id, request
        )
        studio = Studio.create(
            {
                "template_id": self.studio_template_id.id,
                "request_id": request.id,
                "source_ref": "purchase.request,%d" % request.id,
                "company_id": request.company_id.id,
                "value_json": values,
                "note": self.notes,
            }
        )
        if existing:
            official = existing
            official.write(
                {
                    "source_mode": "studio",
                    "studio_template_id": self.studio_template_id.id,
                    "studio_document_id": studio.id,
                    "subject": official.subject or document_type.name,
                }
            )
        else:
            official = Document.create(
                {
                    "document_type": document_type.code,
                    "request_id": request.id,
                    "department_id": request.department_id.id,
                    "company_id": request.company_id.id,
                    "source_mode": "studio",
                    "studio_template_id": self.studio_template_id.id,
                    "studio_document_id": studio.id,
                    "subject": document_type.name,
                }
            )
        studio.official_document_id = official.id
        official._apply_integrity_people_from_request(request)
        if not official.signer_line_ids:
            official._seed_default_approvers()
        if self.notes:
            official.message_post(body=self.notes)
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร Document Studio"),
            "res_model": "vpk.document.studio.document",
            "res_id": studio.id,
            "view_mode": "form",
            "target": "current",
        }

    def _action_attach(self, request, document_type):
        if not self.file:
            raise UserError(_("กรุณาแนบไฟล์ต้นทางที่หน่วยงานจัดทำมาเอง"))
        Document = self.env["vpk.official.document"]
        document = Document._find_existing_document(
            document_type.code, request=request
        )
        if document and document.state not in ("draft", "generated"):
            raise UserError(
                _("มี %s ในใบขอซื้อนี้อยู่แล้ว และไม่สามารถแทนที่ไฟล์ได้")
                % document_type.display_name
            )
        if not document:
            document = Document.create(
                {
                    "document_type": document_type.code,
                    "request_id": request.id,
                    "department_id": request.department_id.id,
                    "company_id": request.company_id.id,
                    "source_mode": "uploaded",
                    "subject": document_type.name,
                }
            )
        else:
            document.write({"source_mode": "uploaded"})
        document._attach_uploaded_file(self.file, self.filename)
        if self.notes:
            document.message_post(body=self.notes)
        return document._action_open_form()
