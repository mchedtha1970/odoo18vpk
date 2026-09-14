# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    vpk_vendor_external_id = fields.Char(
        string="External Vendor ID",
        index=True,
        copy=False,
        help="รหัสอ้างอิงผู้จำหน่ายจากระบบภายนอก (ใช้ upsert ผ่าน Vendor API)",
    )
