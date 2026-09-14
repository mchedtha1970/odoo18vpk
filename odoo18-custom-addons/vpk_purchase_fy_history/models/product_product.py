# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import timedelta

from odoo import _, api, fields, models


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "vpk.purchase.fy.history.mixin"]

    fy_period_label = fields.Char(
        string="ปีงบประมาณ",
        compute="_compute_fy_purchase_history",
    )
    fy_purchased_qty = fields.Float(
        string="ปริมาณเคยซื้อ (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
        digits="Product Unit of Measure",
    )
    fy_last_price_unit = fields.Float(
        string="ราคาล่าสุด (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
        digits="Product Price",
    )
    fy_avg_price_unit = fields.Float(
        string="ราคาเฉลี่ย (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
        digits="Product Price",
    )
    fy_min_price_unit = fields.Float(
        string="ราคาต่ำสุด (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
        digits="Product Price",
    )
    fy_max_price_unit = fields.Float(
        string="ราคาสูงสุด (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
        digits="Product Price",
    )
    fy_purchase_count = fields.Integer(
        string="ครั้งที่ซื้อ (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
    )
    fy_purchase_amount = fields.Float(
        string="มูลค่ารวม (ปีงบฯ)",
        compute="_compute_fy_purchase_history",
        digits="Product Price",
    )

    def _compute_fy_purchase_history(self):
        for product in self:
            stats = product._compute_fy_purchase_stats(product)
            product.fy_period_label = stats["label"]
            product.fy_purchased_qty = stats["qty"]
            product.fy_last_price_unit = stats["last_price"]
            product.fy_avg_price_unit = stats["avg_price"]
            product.fy_min_price_unit = stats["min_price"]
            product.fy_max_price_unit = stats["max_price"]
            product.fy_purchase_count = stats["count"]
            product.fy_purchase_amount = stats["amount"]

    def action_view_fy_purchase_history(self):
        self.ensure_one()
        date_from, date_to = self._get_fiscal_period()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "vpk_purchase_fy_history.action_purchase_line_fy_history"
        )
        action["name"] = _("ประวัติซื้อปีงบฯ — %s") % self.display_name
        action["domain"] = [
            ("product_id", "=", self.id),
            ("display_type", "=", False),
            ("order_id.state", "in", ("purchase", "done")),
            ("order_id.date_order", ">=", fields.Datetime.to_datetime(date_from)),
            (
                "order_id.date_order",
                "<",
                fields.Datetime.to_datetime(date_to + timedelta(days=1)),
            ),
        ]
        return action
