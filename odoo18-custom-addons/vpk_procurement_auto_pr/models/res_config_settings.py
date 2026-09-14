from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    procurement_auto_gen_enabled = fields.Boolean(
        string="เปิดใช้ Gen Auto ใบขอซื้อ/จ้าง/เช่า",
        config_parameter="vpk_procurement_auto_pr.auto_gen_enabled",
        default=True,
        help="เปิด/ปิดการสร้างใบขอซื้ออัตโนมัติจากจุดสั่งซื้อและสัญญาใกล้หมดอายุทั่วทั้งระบบ",
    )
    procurement_contract_expiry_days = fields.Integer(
        string="แจ้งเตือนสัญญาใกล้หมดอายุ (วัน)",
        config_parameter="vpk_procurement_auto_pr.contract_expiry_days",
        default=60,
        help="สร้าง PR อัตโนมัติเมื่อสัญญาจ้าง/เช่าจะหมดอายุภายในจำนวนวันนี้",
    )
    pr_name_assignment = fields.Selection(
        selection=[
            ("auto", "อัตโนมัติเท่านั้น"),
        ],
        string="รูปแบบเลขที่ใบขอซื้อ/จ้าง",
        config_parameter="vpk_procurement_auto_pr.pr_name_assignment",
        default="auto",
        help="เลขที่ใบขอซื้อ/จ้างออกจาก Sequence อัตโนมัติเมื่อบันทึก",
    )
