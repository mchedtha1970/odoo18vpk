# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    daily_receipt_date = fields.Date(
        string="วันที่รับสินค้า",
        compute="_compute_daily_receipt_information",
        store=True,
        index=True,
    )
    is_daily_receipt_today = fields.Boolean(
        string="รับวันนี้",
        compute="_compute_is_daily_receipt_today",
        search="_search_is_daily_receipt_today",
    )
    daily_receipt_po_id = fields.Many2one(
        comodel_name="purchase.order",
        string="เลขที่ PO",
        related="move_id.purchase_line_id.order_id",
        store=True,
        index=True,
    )
    daily_receipt_vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จำหน่าย",
        related="daily_receipt_po_id.partner_id",
        store=True,
        index=True,
    )
    daily_receipt_category_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดสินค้า",
        related="product_id.categ_id",
        store=True,
        index=True,
    )
    daily_receipt_unit_price = fields.Float(
        string="ราคาต่อหน่วย",
        related="move_id.purchase_line_id.price_unit",
        store=True,
    )
    daily_receipt_discount = fields.Float(
        string="ส่วนลด (%)",
        related="move_id.purchase_line_id.discount",
        store=True,
    )
    daily_receipt_order_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="สกุลเงิน PO",
        related="daily_receipt_po_id.currency_id",
        store=True,
    )
    daily_receipt_company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="สกุลเงินบริษัท",
        related="company_id.currency_id",
        store=True,
    )
    daily_receipt_amount = fields.Monetary(
        string="มูลค่ารับสินค้า",
        compute="_compute_daily_receipt_information",
        store=True,
        currency_field="daily_receipt_company_currency_id",
    )

    @api.depends(
        "picking_id.date_done",
        "quantity",
        "move_id.purchase_line_id.price_unit",
        "move_id.purchase_line_id.discount",
        "move_id.purchase_line_id.order_id.currency_id",
        "move_id.purchase_line_id.order_id.date_order",
        "company_id.currency_id",
        "company_id.partner_id.tz",
    )
    def _compute_daily_receipt_information(self):
        for line in self:
            company_timezone = (
                line.company_id.partner_id.tz
                or "Asia/Bangkok"
            )
            line.daily_receipt_date = (
                fields.Datetime.context_timestamp(
                    line.with_context(tz=company_timezone),
                    line.picking_id.date_done,
                ).date()
                if line.picking_id.date_done
                else False
            )
            purchase_line = line.move_id.purchase_line_id
            amount = (
                line.quantity
                * purchase_line.price_unit
                * (1.0 - (purchase_line.discount or 0.0) / 100.0)
            )
            order = purchase_line.order_id
            company = line.company_id
            if order.currency_id and company:
                conversion_date = (
                    line.daily_receipt_date
                    or (
                        order.date_order.date()
                        if order.date_order
                        else False
                    )
                    or fields.Date.context_today(line)
                )
                amount = order.currency_id._convert(
                    amount,
                    company.currency_id,
                    company,
                    conversion_date,
                )
            line.daily_receipt_amount = amount

    def _compute_is_daily_receipt_today(self):
        today = fields.Date.context_today(
            self.with_context(tz="Asia/Bangkok")
        )
        for line in self:
            line.is_daily_receipt_today = (
                line.daily_receipt_date == today
            )

    @api.model
    def _search_is_daily_receipt_today(self, operator, value):
        today = fields.Date.context_today(
            self.with_context(tz="Asia/Bangkok")
        )
        is_today = (
            operator in ("=", "==") and value
        ) or (
            operator in ("!=", "<>") and not value
        )
        return [
            (
                "daily_receipt_date",
                "=" if is_today else "!=",
                today,
            )
        ]
