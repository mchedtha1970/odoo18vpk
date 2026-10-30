from odoo import _, api, fields, models
from odoo.exceptions import UserError

SOURCE_MODELS = [
    ("purchase.request", "ใบขอซื้อ"),
    ("work.acceptance", "ใบตรวจรับ"),
    ("purchase.order", "ใบสั่งซื้อ"),
]


class StudioDocumentWizardApprover(models.TransientModel):
    _name = "vpk.studio.document.wizard.approver"
    _description = "ผู้อนุมัติตอนสร้างเอกสาร"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="vpk.studio.document.add.wizard",
        ondelete="cascade",
    )
    egp_wizard_id = fields.Many2one(
        comodel_name="vpk.egp.document.add.wizard",
        ondelete="cascade",
    )
    sequence = fields.Integer(string="ลำดับอนุมัติ", default=10)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        domain=[("share", "=", False)],
    )
    position = fields.Char(string="ตำแหน่ง")
    is_check = fields.Boolean(string="ตรวจสอบ")
    is_sign = fields.Boolean(string="ลงนาม", default=True)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        Approval = self.env["vpk.approval.line"]
        if self.user_id:
            position = Approval._position_from_user(self.user_id)
            if position:
                self.position = position
            if Approval._is_director_secretary(self.user_id):
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

    def _vpk_seed_rows(self):
        rows = []
        for line in self.sorted(key=lambda rec: (rec.sequence, rec.id)):
            if not line.user_id:
                continue
            is_check = bool(line.is_check)
            is_sign = bool(line.is_sign) and not is_check
            if not is_check and not is_sign:
                is_sign = True
            rows.append(
                {
                    "sequence": line.sequence or len(rows) + 1,
                    "user_id": line.user_id.id,
                    "position": line.position or "",
                    "is_check": is_check,
                    "is_sign": is_sign,
                }
            )
        return rows


class StudioDocumentAddWizard(models.TransientModel):
    _name = "vpk.studio.document.add.wizard"
    _description = "เพิ่มเอกสารจากใบขอซื้อ / ใบตรวจรับ"

    res_model = fields.Selection(selection=SOURCE_MODELS, required=True, readonly=True)
    res_id = fields.Integer(required=True, readonly=True)
    company_id = fields.Many2one(comodel_name="res.company", readonly=True)
    source_model_id = fields.Many2one(comodel_name="ir.model", compute="_compute_source_model_id")
    document_type_id = fields.Many2one(
        comodel_name="vpk.document.studio.document.type",
        string="ประเภทเอกสาร",
        domain="[('company_id', 'in', [False, company_id])]",
    )
    add_mode = fields.Selection(
        selection=[
            ("studio", "สร้างจากแบบฟอร์ม Document Studio"),
            ("attach", "แนบไฟล์ต้นทาง"),
        ],
        string="วิธีเพิ่มเอกสาร",
        required=True,
        default="studio",
    )
    studio_template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม",
        domain="[('active', '=', True), ('company_id', 'in', [False, company_id]),"
        " ('document_type_id', '=', document_type_id),"
        " '|', ('source_model_id', '=', False), ('source_model_id', '=', source_model_id)]",
    )
    file = fields.Binary(string="ไฟล์ต้นทาง")
    filename = fields.Char(string="ชื่อไฟล์")
    notes = fields.Text(string="หมายเหตุ")
    approver_ids = fields.One2many(
        comodel_name="vpk.studio.document.wizard.approver",
        inverse_name="wizard_id",
        string="ลำดับผู้อนุมัติ",
    )

    @api.depends("res_model")
    def _compute_source_model_id(self):
        for rec in self:
            rec.source_model_id = (
                self.env["ir.model"]._get(rec.res_model) if rec.res_model else False
            )

    @api.model
    def _open_for(self, record):
        wizard = self.create(
            {
                "res_model": record._name,
                "res_id": record.id,
                "company_id": record.company_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("เพิ่มเอกสาร"),
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _search_studio_template(self):
        self.ensure_one()
        if not self.document_type_id:
            return self.env["vpk.document.studio.template"]
        return self.env["vpk.document.studio.template"].search(
            [
                ("document_type_id", "=", self.document_type_id.id),
                ("active", "=", True),
                ("company_id", "in", [False, self.company_id.id]),
                "|",
                ("source_model_id", "=", False),
                ("source_model_id", "=", self.source_model_id.id),
            ],
            order="source_model_id, id desc",
            limit=1,
        )

    def _load_approvers_from_template(self, template=False):
        template = template or self.studio_template_id or self._search_studio_template()
        self.approver_ids = (
            template._vpk_approver_wizard_commands()
            if template
            else [(5, 0, 0)]
        )

    @api.onchange("document_type_id", "add_mode", "studio_template_id")
    def _onchange_document_type_id(self):
        if self.add_mode != "studio":
            if self.studio_template_id:
                self.studio_template_id = False
            self._load_approvers_from_template()
            return
        if self.document_type_id and self.studio_template_id.document_type_id != self.document_type_id:
            self.studio_template_id = self._search_studio_template()
        self._load_approvers_from_template()

    def _record(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_("ไม่พบเอกสารต้นทาง"))
        return record

    def action_confirm(self):
        self.ensure_one()
        record = self._record()
        Document = self.env["vpk.document.studio.document"]
        existing = Document._vpk_find_for_record(record, self.document_type_id.code)
        if existing and existing.state not in ("draft", "generated"):
            raise UserError(
                _("มี %s อยู่แล้ว และส่งลงนามแล้ว ไม่สามารถแทนที่ได้")
                % self.document_type_id.display_name
            )
        if self.add_mode == "attach":
            if not self.file:
                raise UserError(_("กรุณาแนบไฟล์ต้นทาง"))
            document = Document.create(
                {
                    "source_mode": "uploaded",
                    "document_type_id": self.document_type_id.id,
                    "source_ref": "%s,%d" % (record._name, record.id),
                    "company_id": record.company_id.id,
                    "note": self.notes,
                }
            )
            document.attach_uploaded_file(self.file, self.filename)
            rows = self.approver_ids._vpk_seed_rows()
            if rows:
                document._vpk_seed_default_approvers(replace=True, rows=rows)
            else:
                document._vpk_seed_default_approvers()
        else:
            if not self.studio_template_id:
                raise UserError(_("กรุณาเลือกแบบฟอร์ม Document Studio"))
            rows = self.approver_ids._vpk_seed_rows()
            document = Document._vpk_create_for_record(
                record,
                self.document_type_id,
                template=self.studio_template_id,
                extra={"note": self.notes},
                approver_rows=rows or None,
            )
        if existing:
            existing.action_cancel()
        if self.notes:
            document.message_post(body=self.notes)
        return document._action_open_form()
