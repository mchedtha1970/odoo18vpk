# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DocumentStudioCreateWizard(models.TransientModel):
    """Create a Document Studio document from any record (Action menu)."""

    _name = "vpk.document.studio.create.wizard"
    _description = "สร้างเอกสารจาก Document Studio"

    source_model = fields.Char(string="โมเดลต้นทาง", readonly=True)
    source_res_id = fields.Integer(string="ID เรคคอร์ดต้นทาง", readonly=True)
    source_name = fields.Char(string="เรคคอร์ดต้นทาง", compute="_compute_source_name")
    template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม",
        required=True,
        domain="[('source_model_id.model', '=', source_model)]",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        model = self.env.context.get("active_model")
        res_id = self.env.context.get("active_id")
        if model and res_id:
            values.update({"source_model": model, "source_res_id": res_id})
            templates = self.env["vpk.document.studio.template"].search(
                [("source_model_id.model", "=", model)]
            )
            if len(templates) == 1:
                values["template_id"] = templates.id
        return values

    @api.depends("source_model", "source_res_id")
    def _compute_source_name(self):
        for rec in self:
            record = (
                self.env[rec.source_model].browse(rec.source_res_id).exists()
                if rec.source_model in self.env
                else None
            )
            rec.source_name = record.display_name if record else ""

    def action_create(self):
        self.ensure_one()
        if self.source_model not in self.env or not self.source_res_id:
            raise UserError(_("ไม่พบเรคคอร์ดต้นทาง กรุณาเปิดจากหน้าของเอกสารต้นทาง"))
        record = self.env[self.source_model].browse(self.source_res_id).exists()
        if not record:
            raise UserError(_("เรคคอร์ดต้นทางถูกลบแล้ว"))
        document = self.env["vpk.document.studio.document"].create(
            {
                "template_id": self.template_id.id,
                "source_ref": "%s,%s" % (record._name, record.id),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร"),
            "res_model": "vpk.document.studio.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }
