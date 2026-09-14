# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_request_ids = fields.Many2many(
        comodel_name="purchase.request",
        string="ใบขอซื้อ/จ้าง/เช่า",
        compute="_compute_purchase_request_ids",
    )
    has_purchase_request = fields.Boolean(
        string="อ้างอิงจาก PR",
        compute="_compute_purchase_request_ids",
        store=True,
        index=True,
    )

    @api.depends(
        "order_line.purchase_request_lines",
        "order_line.purchase_request_lines.request_id",
    )
    def _compute_purchase_request_ids(self):
        for order in self:
            requests = order.order_line.mapped("purchase_request_lines.request_id")
            order.purchase_request_ids = requests
            order.has_purchase_request = bool(requests)
