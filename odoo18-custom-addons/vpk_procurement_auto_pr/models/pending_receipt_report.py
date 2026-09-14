# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    material_category_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดวัสดุ",
        related="product_id.categ_id",
        store=True,
        index=True,
    )
    qty_pending_receipt = fields.Float(
        string="จำนวนค้างรับ",
        compute="_compute_pending_receipt",
        store=True,
        digits="Product Unit of Measure",
    )
    receipt_progress_percent_line = fields.Float(
        string="รับแล้ว (%)",
        compute="_compute_pending_receipt",
        store=True,
    )
    pending_receipt_amount = fields.Monetary(
        string="มูลค่าค้างรับ",
        compute="_compute_pending_receipt",
        store=True,
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="สกุลเงินบริษัท",
        related="order_id.company_id.currency_id",
        store=True,
    )

    @api.depends(
        "product_qty",
        "qty_received",
        "price_unit",
        "discount",
        "currency_id",
        "order_id.currency_id",
        "order_id.company_id.currency_id",
        "order_id.date_order",
    )
    def _compute_pending_receipt(self):
        for line in self:
            pending_qty = max(line.product_qty - line.qty_received, 0.0)
            line.qty_pending_receipt = pending_qty
            line.receipt_progress_percent_line = (
                min(line.qty_received / line.product_qty * 100.0, 100.0)
                if line.product_qty > 0
                else 0.0
            )
            net_pending_amount = (
                pending_qty
                * line.price_unit
                * (1.0 - (line.discount or 0.0) / 100.0)
            )
            company = line.order_id.company_id
            currency = line.order_id.currency_id
            if company and currency:
                conversion_date = (
                    line.order_id.date_order.date()
                    if line.order_id.date_order
                    else fields.Date.context_today(line)
                )
                net_pending_amount = currency._convert(
                    net_pending_amount,
                    company.currency_id,
                    company,
                    conversion_date,
                )
            line.pending_receipt_amount = net_pending_amount
