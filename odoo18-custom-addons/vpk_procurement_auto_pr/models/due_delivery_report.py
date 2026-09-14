# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import timedelta

from odoo import api, fields, models


DELIVERY_ORDER_TYPES = [
    ("purchase", "ใบสั่งซื้อ"),
    ("hire", "ใบสั่งจ้าง"),
    ("repair", "ใบสั่งซ่อม"),
]


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    delivery_order_type = fields.Selection(
        selection=DELIVERY_ORDER_TYPES,
        string="ประเภทใบสั่ง",
        compute="_compute_delivery_order_type",
        store=True,
        index=True,
    )

    @api.depends(
        "procurement_nature",
        "pr_purchase_type_id.name",
        "order_line.name",
        "order_line.product_id.name",
        "order_line.product_id.categ_id.name",
    )
    def _compute_delivery_order_type(self):
        for order in self:
            classification_text = " ".join(
                filter(
                    None,
                    [
                        order.pr_purchase_type_id.name,
                        *order.order_line.mapped("name"),
                        *order.order_line.product_id.mapped("name"),
                        *order.order_line.product_id.categ_id.mapped("name"),
                    ],
                )
            ).lower()
            if "ซ่อม" in classification_text or "repair" in classification_text:
                order.delivery_order_type = "repair"
            elif order.procurement_nature == "hire":
                order.delivery_order_type = "hire"
            else:
                order.delivery_order_type = "purchase"


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    delivery_order_type = fields.Selection(
        selection=DELIVERY_ORDER_TYPES,
        string="ประเภทใบสั่ง",
        related="order_id.delivery_order_type",
        store=True,
        index=True,
    )
    delivery_due_date = fields.Date(
        string="กำหนดส่ง",
        compute="_compute_delivery_due_information",
        store=True,
        index=True,
    )
    delivery_days_remaining = fields.Integer(
        string="จำนวนวันคงเหลือ",
        compute="_compute_delivery_due_information",
    )
    delivery_due_status = fields.Selection(
        selection=[
            ("overdue", "เกินกำหนด"),
            ("today", "ครบกำหนดวันนี้"),
            ("due_7", "ครบกำหนดภายใน 7 วัน"),
            ("due_30", "ครบกำหนดภายใน 30 วัน"),
            ("future", "มากกว่า 30 วัน"),
        ],
        string="สถานะกำหนดส่ง",
        compute="_compute_delivery_due_information",
        search="_search_delivery_due_status",
    )

    @api.depends(
        "date_planned",
        "company_id.partner_id.tz",
    )
    def _compute_delivery_due_information(self):
        today = fields.Date.context_today(
            self.with_context(tz="Asia/Bangkok")
        )
        for line in self:
            timezone = line.company_id.partner_id.tz or "Asia/Bangkok"
            due_date = (
                fields.Datetime.context_timestamp(
                    line.with_context(tz=timezone),
                    line.date_planned,
                ).date()
                if line.date_planned
                else False
            )
            line.delivery_due_date = due_date
            line.delivery_days_remaining = (
                (due_date - today).days if due_date else 0
            )
            if not due_date or due_date > today + timedelta(days=30):
                line.delivery_due_status = "future"
            elif due_date < today:
                line.delivery_due_status = "overdue"
            elif due_date == today:
                line.delivery_due_status = "today"
            elif due_date <= today + timedelta(days=7):
                line.delivery_due_status = "due_7"
            else:
                line.delivery_due_status = "due_30"

    @api.model
    def _search_delivery_due_status(self, operator, value):
        if operator not in ("=", "=="):
            return []
        today = fields.Date.context_today(
            self.with_context(tz="Asia/Bangkok")
        )
        domains = {
            "overdue": [("delivery_due_date", "<", today)],
            "today": [("delivery_due_date", "=", today)],
            "due_7": [
                ("delivery_due_date", ">", today),
                ("delivery_due_date", "<=", today + timedelta(days=7)),
            ],
            "due_30": [
                ("delivery_due_date", ">", today + timedelta(days=7)),
                ("delivery_due_date", "<=", today + timedelta(days=30)),
            ],
            "future": [
                ("delivery_due_date", ">", today + timedelta(days=30)),
            ],
        }
        return domains.get(value, [])
