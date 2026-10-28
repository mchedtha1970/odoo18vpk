from odoo import _, api, fields, models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    studio_document_ids = fields.One2many(
        comodel_name="vpk.document.studio.document",
        inverse_name="wa_id",
        string="เอกสารที่เกี่ยวข้อง",
    )
    studio_document_count = fields.Integer(
        string="จำนวนเอกสาร",
        compute="_compute_studio_document_count",
    )
    issued_inspection_document_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="ใบตรวจรับที่ออกแล้ว",
        compute="_compute_studio_document_count",
    )

    @api.depends("studio_document_ids.state", "studio_document_ids.document_type_code")
    def _compute_studio_document_count(self):
        for rec in self:
            documents = rec.sudo().studio_document_ids
            rec.studio_document_count = len(documents)
            rec.issued_inspection_document_id = documents.filtered(
                lambda doc: doc.document_type_code == "inspection_report"
                and doc.state != "cancelled"
            )[:1]

    def action_view_studio_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสารที่เกี่ยวข้อง"),
            "res_model": "vpk.document.studio.document",
            "view_mode": "list,form",
            "domain": [("wa_id", "=", self.id)],
            "context": {
                "default_wa_id": self.id,
                "default_source_ref": "work.acceptance,%d" % self.id,
            },
        }

    def action_create_inspection_report(self):
        """ออกใบตรวจรับจากแบบฟอร์ม Document Studio (ถ้าออกแล้วเปิดฉบับเดิม)."""
        self.ensure_one()
        Document = self.env["vpk.document.studio.document"]
        document = Document._vpk_find_for_record(self, "inspection_report")
        if not document:
            document_type = self.env["vpk.document.studio.document.type"].search(
                [("code", "=", "inspection_report")], limit=1
            )
            if not document_type:
                return self.action_open_add_studio_document_wizard()
            document = Document._vpk_create_for_record(self, document_type)
        return document._action_open_form()

    def action_open_add_studio_document_wizard(self):
        self.ensure_one()
        return self.env["vpk.studio.document.add.wizard"]._open_for(self)
