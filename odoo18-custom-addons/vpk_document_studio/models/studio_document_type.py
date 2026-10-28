# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


class DocumentStudioDocumentType(models.Model):
    _name = "vpk.document.studio.document.type"
    _description = "ประเภทเอกสาร Document Studio"
    _order = "sequence, name, id"

    name = fields.Char(string="ชื่อประเภทเอกสาร", required=True)
    code = fields.Char(string="รหัส", required=True, index=True, copy=False)
    sequence = fields.Integer(string="ลำดับ", default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string="คำอธิบาย")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        default=lambda self: self.env.company,
        index=True,
    )
    template_ids = fields.One2many(
        comodel_name="vpk.document.studio.template",
        inverse_name="document_type_id",
        string="แบบฟอร์ม",
    )
    template_count = fields.Integer(
        string="จำนวนแบบฟอร์ม",
        compute="_compute_template_count",
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "รหัสประเภทเอกสารซ้ำ",
        ),
    ]

    @api.depends("template_ids")
    def _compute_template_count(self):
        for rec in self:
            rec.template_count = len(rec.template_ids)

    def action_view_templates(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("แบบฟอร์ม — %s") % self.name,
            "res_model": "vpk.document.studio.template",
            "view_mode": "list,form",
            "domain": [("document_type_id", "=", self.id)],
            "context": {"default_document_type_id": self.id},
        }
