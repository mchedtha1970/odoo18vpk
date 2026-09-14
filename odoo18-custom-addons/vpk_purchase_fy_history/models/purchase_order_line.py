# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import timedelta

from odoo import _, api, fields, models


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["purchase.order.line", "vpk.purchase.fy.history.mixin"]

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
    fy_price_warning = fields.Char(
        string="แจ้งเตือนราคา",
        compute="_compute_fy_purchase_history",
    )

    @api.depends(
        "product_id",
        "price_unit",
        "order_id.partner_id",
        "order_id.date_order",
        "order_id.state",
    )
    def _compute_fy_purchase_history(self):
        for line in self:
            ref_date = (
                fields.Date.to_date(line.order_id.date_order)
                if line.order_id.date_order
                else fields.Date.context_today(line)
            )
            exclude = [line.order_id.id] if line.order_id else []
            stats = line._compute_fy_purchase_stats(
                line.product_id,
                partner=None,
                ref_date=ref_date,
                exclude_order_ids=exclude,
            )
            line.fy_period_label = stats["label"]
            line.fy_purchased_qty = stats["qty"]
            line.fy_last_price_unit = stats["last_price"]
            line.fy_avg_price_unit = stats["avg_price"]
            line.fy_min_price_unit = stats["min_price"]
            line.fy_max_price_unit = stats["max_price"]
            line.fy_purchase_count = stats["count"]
            warning = ""
            if (
                line.product_id
                and stats["count"]
                and line.price_unit
                and stats["max_price"]
                and line.price_unit > stats["max_price"] * 1.0001
            ):
                warning = _(
                    "ราคาสูงกว่าราคาสูงสุดที่เคยซื้อในปีงบฯ (%.2f)"
                ) % stats["max_price"]
            elif (
                line.product_id
                and stats["count"]
                and line.price_unit
                and stats["avg_price"]
                and line.price_unit > stats["avg_price"] * 1.2
            ):
                warning = _(
                    "ราคาสูงกว่าราคาเฉลี่ยปีงบฯ มากกว่า 20%% (เฉลี่ย %.2f)"
                ) % stats["avg_price"]
            line.fy_price_warning = warning

    def action_view_fy_purchase_history(self):
        self.ensure_one()
        if not self.product_id:
            return False
        ref_date = (
            fields.Date.to_date(self.order_id.date_order)
            if self.order_id.date_order
            else fields.Date.context_today(self)
        )
        date_from, date_to = self._get_fiscal_period(ref_date)
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "vpk_purchase_fy_history.action_purchase_line_fy_history"
        )
        action["name"] = _("ประวัติซื้อปีงบฯ — %s") % self.product_id.display_name
        action["domain"] = [
            ("product_id", "=", self.product_id.id),
            ("display_type", "=", False),
            ("order_id.state", "in", ("purchase", "done")),
            ("order_id.date_order", ">=", fields.Datetime.to_datetime(date_from)),
            (
                "order_id.date_order",
                "<",
                fields.Datetime.to_datetime(date_to + timedelta(days=1)),
            ),
        ]
        action["context"] = {
            "default_product_id": self.product_id.id,
            "search_default_product_id": self.product_id.id,
        }
        return action
