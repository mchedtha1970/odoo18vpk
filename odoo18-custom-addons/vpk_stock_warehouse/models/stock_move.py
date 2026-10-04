# -*- coding: utf-8 -*-
from odoo import Command, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    receipt_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        related="picking_id.picking_type_id.warehouse_id",
        string="คลังรับ",
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        related="picking_id.partner_id",
        string="ผู้ขาย",
    )

    def _vpk_chain_move(self, location, location_dest, location_final, picking_type, warehouse):
        """สร้างใบถัดไปที่รอใบนี้ โดยยังไม่จองของซ้ำ"""
        self.ensure_one()
        new_move = self.copy(
            {
                "product_uom_qty": self.product_uom_qty,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
                "location_final_id": location_final.id,
                "picking_id": False,
                "picking_type_id": picking_type.id,
                "warehouse_id": warehouse.id,
                "procure_method": "make_to_order",
                "origin": self.picking_id.name or self.origin or "",
                "group_id": self.group_id.id,
                "rule_id": False,
                "move_orig_ids": [Command.link(self.id)],
            }
        )
        if new_move.move_line_ids:
            new_move.move_line_ids.unlink()
        return new_move

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        role = self.env.context.get("vpk_central_chain_role")
        if role:
            vals["vpk_central_chain"] = True
            vals["vpk_central_chain_role"] = role
        return vals

    def action_open_receipt(self):
        self.ensure_one()
        if not self.picking_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": self.picking_id.display_name,
            "res_model": "stock.picking",
            "res_id": self.picking_id.id,
            "view_mode": "form",
            "target": "current",
        }
