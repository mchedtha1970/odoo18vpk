# -*- coding: utf-8 -*-
from odoo import api, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        vals = super()._prepare_purchase_order_line(po, item)
        vals["egp_purchase_name"] = (
            item.line_id.egp_purchase_name
            or item.product_id.egp_purchase_name
            or False
        )
        return vals
