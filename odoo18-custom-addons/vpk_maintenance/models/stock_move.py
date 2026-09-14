# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    maintenance_request_id = fields.Many2one(
        comodel_name="maintenance.request",
        string="คำขอซ่อมบำรุง",
        related="picking_id.maintenance_request_id",
        store=True,
        index=True,
    )
    parts_qty = fields.Float(
        string="จำนวน",
        compute="_compute_parts_value",
        digits="Product Unit of Measure",
    )
    parts_unit_cost = fields.Float(
        string="ต้นทุน/หน่วย",
        compute="_compute_parts_value",
        digits="Product Price",
    )
    parts_value = fields.Monetary(
        string="มูลค่า",
        compute="_compute_parts_value",
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="สกุลเงิน",
    )

    @api.depends(
        "quantity",
        "product_uom_qty",
        "state",
        "product_id.standard_price",
        "stock_valuation_layer_ids.value",
        "stock_valuation_layer_ids.unit_cost",
        "company_id",
    )
    def _compute_parts_value(self):
        for move in self:
            qty = move.quantity if move.state == "done" else move.product_uom_qty
            move.parts_qty = qty
            layers = move.stock_valuation_layer_ids
            if layers:
                value = abs(sum(layers.mapped("value")))
                move.parts_value = value
                move.parts_unit_cost = (value / qty) if qty else 0.0
            else:
                unit = move.product_id.standard_price or 0.0
                move.parts_unit_cost = unit
                move.parts_value = unit * qty
