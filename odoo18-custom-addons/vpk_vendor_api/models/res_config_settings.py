# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    vpk_vendor_api_key = fields.Char(
        string="Vendor API Key",
        config_parameter="vpk_vendor_api.api_key",
        help="ส่งใน Header: X-Api-Key หรือ Authorization: Bearer <key>",
    )
    vpk_vendor_api_enabled = fields.Boolean(
        string="Enable Vendor Registration API",
        config_parameter="vpk_vendor_api.enabled",
        default=True,
    )
    vpk_vendor_api_max_upload_mb = fields.Float(
        string="Max Upload Size (MB)",
        config_parameter="vpk_vendor_api.max_upload_mb",
        default=10.0,
        help="ขนาดไฟล์เอกสารทางการค้าสูงสุดต่อไฟล์ (MB)",
    )
