# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    emergency_budget_bypass = fields.Boolean(
        string="อนุญาตเส้นทางงบเร่งด่วนสำหรับ PR ฉุกเฉิน",
        config_parameter="vpk_purchase_request_urgent.emergency_budget_bypass",
        help="เมื่อเปิด: PR ที่เลือกเป็น 'ฉุกเฉิน' สามารถเช็คงบแบบเร่งด่วนได้ "
             "(ผ่านการตรวจเพื่อส่งอนุมัติ โดยไม่จองงบแผ่นดินทันที — ต้องติดตามตัดงบภายหลัง)\n"
             "เมื่อปิด: PR ฉุกเฉินยังต้องเช็คและจองงบตามปกติเหมือน PR ทั่วไป",
    )
