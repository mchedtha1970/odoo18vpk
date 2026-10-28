from odoo import fields, models


class DocumentStudioBlock(models.Model):
    _inherit = "vpk.document.studio.block"

    code_number = fields.Char(default="saraban_no_th")
