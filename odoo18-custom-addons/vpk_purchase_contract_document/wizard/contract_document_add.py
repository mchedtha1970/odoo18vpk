# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

SOURCE_MODELS = (False, "purchase.contract")


class StudioDocumentWizardApprover(models.TransientModel):
    _inherit = "vpk.studio.document.wizard.approver"

    contract_wizard_id = fields.Many2one(
        comodel_name="vpk.contract.document.add.wizard",
        ondelete="cascade",
    )


class VpkContractDocumentAddWizard(models.TransientModel):
    _name = "vpk.contract.document.add.wizard"
    _description = "เพิ่มเอกสารสัญญา"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญา",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="contract_id.company_id")
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
        " ('template_ids.source_model_name', '=', 'purchase.contract')]"
        " if add_mode == 'studio' else [])",
    )
    studio_template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม Document Studio",
        domain="[('active', '=', True), ('company_id', 'in', [False, company_id]),"
        " '|', ('source_model_name', '=', False),"
        " ('source_model_name', '=', 'purchase.contract'),"
        " ('document_type_id', '=', studio_document_type_id)]",
    )
    egp_reference = fields.Char(string="เลขอ้างอิง e-GP")
    document_date = fields.Date(string="วันที่เอกสาร", default=fields.Date.context_today)
    file = fields.Binary(string="ไฟล์ต้นทาง (PDF)")
    filename = fields.Char(string="ชื่อไฟล์")
    notes = fields.Text(string="หมายเหตุ")
    approver_ids = fields.One2many(
        comodel_name="vpk.studio.document.wizard.approver",
        inverse_name="contract_wizard_id",
        string="ลำดับผู้อนุมัติ",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        contract = self.env["purchase.contract"].browse(values.get("contract_id"))
        if contract and not values.get("egp_reference"):
            values["egp_reference"] = (
                contract.egp_contract_control_no or contract.egp_reference or False
            )
        return values

    def _load_approvers_from_template(self):
        template = self.studio_template_id
        self.approver_ids = (
            template._vpk_approver_wizard_commands() if template else [(5, 0, 0)]
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
            company = self.contract_id.company_id or self.env.company
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

    def _contract_document_vals(self):
        return {
            "contract_id": self.contract_id.id,
            "document_type_id": self.studio_document_type_id.id,
            "egp_reference": self.egp_reference or False,
            "document_date": self.document_date,
            "notes": self.notes,
        }

    def action_confirm(self):
        self.ensure_one()
        if not self.studio_document_type_id:
            raise UserError(_("กรุณาเลือกประเภทเอกสาร"))
        if self.add_mode == "attach":
            return self._action_attach()
        return self._action_from_studio()

    def _action_attach(self):
        if not self.file:
            raise UserError(_("กรุณาแนบไฟล์ต้นทาง"))
        vals = self._contract_document_vals()
        vals.update({"document_file": self.file, "document_filename": self.filename})
        self.env["purchase.contract.document"].create(vals)
        return {"type": "ir.actions.act_window_close"}

    def _action_from_studio(self):
        template = self.studio_template_id
        if not template:
            raise UserError(_("กรุณาเลือกแบบฟอร์มจาก Document Studio"))
        contract = self.contract_id
        document = self.env["purchase.contract.document"].create(
            self._contract_document_vals()
        )
        studio = self.env["vpk.document.studio.document"]._vpk_create_for_record(
            contract,
            self.studio_document_type_id,
            template=template,
            extra={
                "requisition_id": contract.requisition_id.id or False,
                "company_id": contract.company_id.id,
                "date": self.document_date or fields.Date.context_today(self),
                "note": self.notes,
            },
            approver_rows=self.approver_ids._vpk_seed_rows() or None,
        )
        document.studio_document_id = studio.id
        self.env["purchase.contract.document.signer"].create(
            [
                {
                    "document_id": document.id,
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
