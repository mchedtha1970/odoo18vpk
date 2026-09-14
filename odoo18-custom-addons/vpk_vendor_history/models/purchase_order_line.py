from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def action_open_purchase_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.order_id.display_name,
            "res_model": "purchase.order",
            "res_id": self.order_id.id,
            "view_mode": "form",
            "target": "current",
        }
