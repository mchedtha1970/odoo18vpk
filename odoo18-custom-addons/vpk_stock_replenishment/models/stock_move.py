from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    orderpoint_id = fields.Many2one(
        comodel_name="stock.warehouse.orderpoint",
        string="Reordering Rule",
        index=True,
        readonly=True,
        copy=False,
    )
    restrict_lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Restrict Lot",
        copy=False,
        index=True,
        help="Lot to use for this replenishment move.",
    )

    @api.model
    def _vpk_apply_lot_on_moves(self, move_lot_qty_list):
        """Create move lines with lot for replenishment transfers."""
        MoveLine = self.env["stock.move.line"]
        for move, lot, qty in move_lot_qty_list:
            if not lot or move.product_id.tracking == "none":
                continue
            if float_is_zero(qty, precision_rounding=move.product_uom.rounding):
                continue
            move.write({"restrict_lot_id": lot.id})
            existing = move.move_line_ids.filtered(lambda ml: ml.lot_id == lot)
            if existing:
                existing.write({"quantity": qty})
                (move.move_line_ids - existing).unlink()
            else:
                move.move_line_ids.unlink()
                MoveLine.create(
                    {
                        "move_id": move.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": move.product_uom.id,
                        "quantity": qty,
                        "lot_id": lot.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                    }
                )
