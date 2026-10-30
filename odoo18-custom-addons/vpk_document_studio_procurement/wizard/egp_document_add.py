from odoo import _, api, fields, models
from odoo.exceptions import UserError

SOURCE_MODELS = (False, "purchase.request", "purchase.requisition")


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
    add_mode = fields.Selection(
        selection=[
            ("studio", "ดึงจาก Document Studio"),
            ("attach", "แนบไฟล์ต้นทาง"),
        ],
        string="วิธีเพิ่มเอกสาร",
        required=True,
        default="studio",
    )
    studio_document_type_id = fields.Many2one(
        comodel_name="vpk.document.studio.document.type",
        string="ประเภทเอกสาร",
        domain="[('company_id', 'in', [False, company_id])]"
        " + ([('template_ids.active', '=', True),"
        " '|', ('template_ids.source_model_name', '=', False),"
        " ('template_ids.source_model_name', 'in', ['purchase.request', 'purchase.requisition'])]"
        " if add_mode == 'studio' else [])",
    )
    studio_template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม Document Studio",
        domain="[('active', '=', True), ('company_id', 'in', [False, company_id]),"
        " '|', ('source_model_name', '=', False),"
        " ('source_model_name', 'in', ['purchase.request', 'purchase.requisition']),"
        " ('document_type_id', '=', studio_document_type_id)]",
    )
    egp_reference = fields.Char(string="เลขอ้างอิง e-GP")
    document_date = fields.Date(string="วันที่เอกสาร", default=fields.Date.context_today)
    file = fields.Binary(string="ไฟล์ต้นทาง (PDF)")
    filename = fields.Char(string="ชื่อไฟล์")
    notes = fields.Text(string="หมายเหตุ")
    approver_ids = fields.One2many(
        comodel_name="vpk.studio.document.wizard.approver",
        inverse_name="egp_wizard_id",
        string="ลำดับผู้อนุมัติ",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        requisition = self.env["purchase.requisition"].browse(values.get("requisition_id"))
        if requisition and not values.get("egp_reference"):
            values["egp_reference"] = requisition.egp_reference
        return values

    def _load_approvers_from_template(self):
        template = self.studio_template_id
        self.approver_ids = (
            template._vpk_approver_wizard_commands()
            if template
            else [(5, 0, 0)]
        )

    @api.onchange("studio_document_type_id", "add_mode", "studio_template_id")
    def _onchange_studio_document_type(self):
        if self.add_mode != "studio":
            self.studio_template_id = False
            self._load_approvers_from_template()
            return
        studio_type = self.studio_document_type_id
        if self.studio_template_id.document_type_id != studio_type:
            self.studio_template_id = False
        if studio_type and not self.studio_template_id:
            company = self.requisition_id.company_id or self.env.company
            templates = studio_type.template_ids.filtered(
                lambda tmpl: tmpl.active
                and tmpl.company_id in (company, self.env["res.company"])
                and tmpl.source_model_name in SOURCE_MODELS
            )
            if len(templates) == 1:
                self.studio_template_id = templates
        self._load_approvers_from_template()

    @api.onchange("add_mode")
    def _onchange_add_mode(self):
        if self.add_mode != "attach":
            self.file = False
            self.filename = False

    def action_confirm(self):
        self.ensure_one()
        if not self.studio_document_type_id:
            raise UserError(_("กรุณาเลือกประเภทเอกสาร"))
        if self.add_mode == "attach":
            return self._action_attach()
        return self._action_from_studio()

    def _egp_type_for_studio_type(self, studio_type):
        """e-GP documents need an e-GP type; reuse the linked one or one with the same code."""
        if studio_type.egp_document_type_ids:
            return studio_type.egp_document_type_ids[:1]
        EgpType = self.env["purchase.requisition.egp.document.type"].sudo()
        egp_type = EgpType.with_context(active_test=False).search(
            [("code", "=", studio_type.code)], limit=1
        )
        if not egp_type:
            egp_type = EgpType.create({"name": studio_type.name, "code": studio_type.code})
        return egp_type

    def _egp_document_vals(self):
        return {
            "requisition_id": self.requisition_id.id,
            "document_type_id": self._egp_type_for_studio_type(self.studio_document_type_id).id,
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
        template = self.studio_template_id
        if not template:
            raise UserError(_("กรุณาเลือกแบบฟอร์มจาก Document Studio"))
        requisition = self.requisition_id
        request = requisition.purchase_request_id
        if template.source_model_name == "purchase.requisition" or not request:
            source = requisition
        else:
            source = request
        egp_document = self.env["purchase.requisition.egp.document"].create(
            self._egp_document_vals()
        )
        studio = self.env["vpk.document.studio.document"]._vpk_create_for_record(
            source,
            self.studio_document_type_id,
            template=template,
            extra={
                "requisition_id": requisition.id,
                "request_id": request.id if request else False,
                "company_id": requisition.company_id.id,
                "note": self.notes,
            },
            approver_rows=self.approver_ids._vpk_seed_rows() or None,
        )
        egp_document.studio_document_id = studio.id
        Signer = self.env["purchase.requisition.egp.document.signer"]
        Signer.create(
            [
                {
                    "egp_document_id": egp_document.id,
                    "sequence": index,
                    "user_id": line.user_id.id,
                    "position": line.position or "",
                    "is_check": line.is_check,
                    "is_sign": line.is_sign,
                }
                for index, line in enumerate(
                    studio.vpk_approver_line_ids.filtered("user_id").sorted(
                        key=lambda rec: (rec.sequence, rec.id)
                    ),
                    start=1,
                )
            ]
        )
        return studio._action_open_form()
