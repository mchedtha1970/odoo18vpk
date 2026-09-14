from odoo import fields, models


class PurchaseContract(models.Model):
    _inherit = "purchase.contract"

    contract_kind = fields.Selection(
        selection=[
            ("buy", "ซื้อ"),
            ("hire", "จ้าง"),
            ("lease", "เช่า"),
        ],
        string="ประเภทสัญญา",
        default="buy",
        tracking=True,
        help="ใช้แยกสัญญาซื้อ / จ้าง / เช่า สำหรับ Gen Auto เมื่อใกล้หมดอายุ",
    )
