from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    official_doc_agency = fields.Char(related="company_id.official_doc_agency", readonly=False)
