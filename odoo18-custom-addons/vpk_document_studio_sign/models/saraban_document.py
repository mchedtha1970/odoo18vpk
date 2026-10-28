from odoo import fields, models


class SarabanDocument(models.Model):
    _inherit = "saraban.document"

    studio_document_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="เอกสาร Document Studio",
        ondelete="set null",
        index=True,
        tracking=True,
    )

    def action_register(self):
        res = super().action_register()
        for rec in self:
            if rec.studio_document_id and rec.book_no:
                rec.studio_document_id.write(
                    {
                        "saraban_book_no": rec.book_no_display or rec.book_no,
                        "saraban_document_id": rec.id,
                    }
                )
        return res

    def action_open_studio_document(self):
        self.ensure_one()
        if not self.studio_document_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "vpk.document.studio.document",
            "res_id": self.studio_document_id.id,
            "view_mode": "form",
            "target": "current",
        }
