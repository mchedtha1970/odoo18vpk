# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    fy_period_label = fields.Char(
        related="product_variant_id.fy_period_label",
        string="ปีงบประมาณ",
    )
    fy_purchased_qty = fields.Float(
        related="product_variant_id.fy_purchased_qty",
        string="ปริมาณเคยซื้อ (ปีงบฯ)",
    )
    fy_last_price_unit = fields.Float(
        related="product_variant_id.fy_last_price_unit",
        string="ราคาล่าสุด (ปีงบฯ)",
    )
    fy_avg_price_unit = fields.Float(
        related="product_variant_id.fy_avg_price_unit",
        string="ราคาเฉลี่ย (ปีงบฯ)",
    )
    fy_min_price_unit = fields.Float(
        related="product_variant_id.fy_min_price_unit",
        string="ราคาต่ำสุด (ปีงบฯ)",
    )
    fy_max_price_unit = fields.Float(
        related="product_variant_id.fy_max_price_unit",
        string="ราคาสูงสุด (ปีงบฯ)",
    )
    fy_purchase_count = fields.Integer(
        related="product_variant_id.fy_purchase_count",
        string="ครั้งที่ซื้อ (ปีงบฯ)",
    )
    fy_purchase_amount = fields.Float(
        related="product_variant_id.fy_purchase_amount",
        string="มูลค่ารวม (ปีงบฯ)",
    )

    def action_view_fy_purchase_history(self):
        self.ensure_one()
        return self.product_variant_id.action_view_fy_purchase_history()
