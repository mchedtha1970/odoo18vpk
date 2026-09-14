from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    minimum_receipt_shelf_life_days = fields.Integer(
        string="อายุคงเหลือขั้นต่ำเมื่อรับยา (วัน)",
        default=0,
        help=(
            "หากมากกว่า 0 ระบบจะตรวจวันหมดอายุของทุก LOT ตอนรับสินค้า "
            "และบังคับแนบใบรับรองการเปลี่ยนยาเมื่ออายุคงเหลือต่ำกว่าเกณฑ์"
        ),
    )
