# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    vpk_purchase_order_ids = fields.Many2many(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ",
        compute="_compute_vpk_purchase_order_ids",
    )

    @api.depends(
        "line_ids.purchase_lines.order_id",
        "line_ids.requisition_lines.requisition_id.purchase_ids",
    )
    def _compute_vpk_purchase_order_ids(self):
        for request in self:
            orders = request.mapped("line_ids.purchase_lines.order_id")
            orders |= request.mapped(
                "line_ids.requisition_lines.requisition_id.purchase_ids"
            )
            request.vpk_purchase_order_ids = orders
