from odoo import models


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_custom_move_fields(self):
        return super()._get_custom_move_fields() + ["restrict_lot_id"]

    def _get_stock_move_values(
        self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values
    ):
        move_values = super()._get_stock_move_values(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
        )
        orderpoint = values.get("orderpoint_id")
        if orderpoint:
            move_values["orderpoint_id"] = orderpoint.id
        restrict_lot = values.get("restrict_lot_id")
        if restrict_lot:
            move_values["restrict_lot_id"] = restrict_lot.id
        return move_values

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        move_values = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        if move_to_copy.restrict_lot_id:
            move_values["restrict_lot_id"] = move_to_copy.restrict_lot_id.id
        if move_to_copy.orderpoint_id:
            move_values["orderpoint_id"] = move_to_copy.orderpoint_id.id
        return move_values
