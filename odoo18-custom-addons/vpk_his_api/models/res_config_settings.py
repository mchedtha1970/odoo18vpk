# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    vpk_his_api_key = fields.Char(
        string="HIS API Key",
        config_parameter="vpk_his_api.api_key",
        help="ส่งใน Header: X-Api-Key หรือ Authorization: Bearer <key>",
    )
    vpk_his_api_enabled = fields.Boolean(
        string="Enable HIS API",
        config_parameter="vpk_his_api.enabled",
        default=True,
    )
