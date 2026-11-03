# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    gfmis_agency_code = fields.Char(
        related="company_id.gfmis_agency_code",
        readonly=False,
    )
    gfmis_area_code = fields.Char(
        related="company_id.gfmis_area_code",
        readonly=False,
    )
    gfmis_disbursing_unit_code = fields.Char(
        related="company_id.gfmis_disbursing_unit_code",
        readonly=False,
    )
    gfmis_wht_signer_name = fields.Char(
        related="company_id.gfmis_wht_signer_name",
        readonly=False,
    )
    gfmis_wht_signer_position = fields.Char(
        related="company_id.gfmis_wht_signer_position",
        readonly=False,
    )
