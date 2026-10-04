# -*- coding: utf-8 -*-
from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        moves = super()._action_confirm(merge=merge, merge_into=merge_into)
        pickings = moves.filtered(
            lambda move: move.picking_id
            and move.picking_id.picking_type_code == "incoming"
            and not move.scrapped
        ).picking_id
        pickings._vpk_sync_receipt_qc_checks()
        return moves
