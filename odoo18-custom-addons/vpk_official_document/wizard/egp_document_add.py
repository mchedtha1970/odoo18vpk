from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VpkEgpDocumentAddWizard(models.TransientModel):
    _name = "vpk.egp.document.add.wizard"
    _description = "เพิ่มเอกสารในกระบวนการ e-GP"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ e-GP",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="requisition_id.company_id")
    document_type_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.document.type",
        string="ประเภทเอกสาร",
        required=True,
    )
    add_mode = fields.Selection(
        selection=[
            ("studio", "ดึงจาก Document Studio"),
            ("attach", "แนบไฟล์ต้นทาง"),
        ],
        string="วิธีเพิ่มเอกสาร",
        required=True,
        default="attach",
    )
    studio_template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม Document Studio",
        domain="[('active', '=', True), ('company_id', 'in', [False, company_id]),"
        " '|', ('source_model_name', '=', False),"
        " ('source_model_name', 'in', ['purchase.request', 'purchase.requisition']),"
        " '|', '|', ('document_type_id', '=', False),"
        " ('document_type_id.egp_document_type_ids', '=', False),"
        " ('document_type_id.egp_document_type_ids', 'in', [document_type_id])]",
    )
    egp_reference = fields.Char(string="เลขอ้างอิง e-GP")
    document_date = fields.Date(
        string="วันที่เอกสาร",
        default=fields.Date.context_today,
    )
    file = fields.Binary(string="ไฟล์ต้นทาง (PDF)")
    filename = fields.Char(string="ชื่อไฟล์")
    notes = fields.Text(string="หมายเหตุ")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        requisition = self.env["purchase.requisition"].browse(
            values.get("requisition_id")
        )
        if requisition and not values.get("egp_reference"):
            values["egp_reference"] = requisition.egp_reference
        return values

    @api.onchange("document_type_id", "add_mode")
    def _onchange_document_type_studio_template(self):
        if self.add_mode != "studio" or not self.document_type_id:
            return
        templates = self.env["vpk.document.studio.template"]._templates_for_linked_type(
            "egp_document_type_ids",
            self.document_type_id,
            self.requisition_id.company_id or self.env.company,
        )
        if len(templates) == 1:
            self.studio_template_id = templates
        elif self.studio_template_id and templates and self.studio_template_id not in templates:
            self.studio_template_id = False

    @api.onchange("add_mode")
    def _onchange_add_mode(self):
        if self.add_mode != "studio":
            self.studio_template_id = False
        if self.add_mode != "attach":
            self.file = False
            self.filename = False

    def action_confirm(self):
        self.ensure_one()
        if self.add_mode == "attach":
            return self._action_attach()
        return self._action_from_studio()

    def _egp_document_vals(self):
        return {
            "requisition_id": self.requisition_id.id,
            "document_type_id": self.document_type_id.id,
            "egp_reference": self.egp_reference or False,
            "document_date": self.document_date,
            "notes": self.notes,
        }

    def _action_attach(self):
        if not self.file:
            raise UserError(_("กรุณาแนบไฟล์ต้นทาง"))
        vals = self._egp_document_vals()
        vals.update({"document_file": self.file, "document_filename": self.filename})
        self.env["purchase.requisition.egp.document"].create(vals)
        return {"type": "ir.actions.act_window_close"}

    def _action_from_studio(self):
        if not self.studio_template_id:
            raise UserError(_("กรุณาเลือกแบบฟอร์มจาก Document Studio"))
        requisition = self.requisition_id
        request = requisition.purchase_request_id
        template = self.studio_template_id
        if template.source_model_name == "purchase.requisition" or not request:
            source = requisition
        else:
            source = request
        egp_document = self.env["purchase.requisition.egp.document"].create(
            self._egp_document_vals()
        )
        studio = self.env["vpk.document.studio.document"].create(
            {
                "template_id": template.id,
                "source_ref": "%s,%d" % (source._name, source.id),
                "request_id": request.id if request else False,
                "company_id": requisition.company_id.id,
                "note": self.notes,
            }
        )
        official = (
            self.env["vpk.official.document"]
            .with_context(skip_validation_check=True)
            .create(
                {
                    "document_type": egp_document._map_official_document_type_code(),
                    "requisition_id": requisition.id,
                    "request_id": request.id if request else False,
                    "department_id": request.department_id.id if request else False,
                    "company_id": requisition.company_id.id,
                    "source_mode": "studio",
                    "studio_template_id": template.id,
                    "studio_document_id": studio.id,
                    "subject": self.document_type_id.name,
                    "date": self.document_date or fields.Date.context_today(self),
                }
            )
        )
        studio.official_document_id = official.id
        egp_document.official_document_id = official.id
        if not official.signer_line_ids:
            official._seed_default_approvers()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร Document Studio"),
            "res_model": "vpk.document.studio.document",
            "res_id": studio.id,
            "view_mode": "form",
            "target": "current",
        }
