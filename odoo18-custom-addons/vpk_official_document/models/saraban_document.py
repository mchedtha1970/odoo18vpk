# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class SarabanDocument(models.Model):
    _inherit = "saraban.document"

    official_document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        string="หนังสือราชการ",
        ondelete="set null",
        index=True,
        tracking=True,
    )

    def action_register(self):
        res = super().action_register()
        for rec in self:
            if rec.official_document_id and rec.book_no:
                rec.official_document_id.write(
                    {
                        "saraban_book_no": rec.book_no_display or rec.book_no,
                        "saraban_document_id": rec.id,
                    }
                )
        return res

    def action_open_official_document(self):
        self.ensure_one()
        if not self.official_document_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "vpk.official.document",
            "res_id": self.official_document_id.id,
            "view_mode": "form",
            "target": "current",
        }
