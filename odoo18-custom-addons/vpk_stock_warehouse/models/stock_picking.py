# -*- coding: utf-8 -*-
from ast import literal_eval

from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    vpk_central_chain = fields.Boolean(
        string="ลำดับโอนคลังกลาง",
        copy=False,
    )
    vpk_central_chain_role = fields.Selection(
        [
            ("pick", "หยิบของ"),
            ("pack", "แพ็คลงกล่อง"),
            ("deliver", "อัปเดตปลายทาง"),
        ],
        string="ขั้นของลำดับโอน",
        copy=False,
    )

    @api.depends("picking_type_id", "partner_id")
    def _compute_location_id(self):
        if self.env.context.get("vpk_keep_picking_locations"):
            return
        super()._compute_location_id()
        if not self.env.context.get("vpk_request_from_central"):
            return
        if self.env.context.get("vpk_central_chain_role"):
            return
        stock = self.env["stock.warehouse"]._vpk_central_warehouse().lot_stock_id
        if not stock:
            return
        for picking in self:
            if picking.vpk_central_chain or picking.vpk_central_chain_role:
                continue
            if picking.state in ("cancel", "done") or picking.return_id:
                continue
            if picking.picking_type_id.code != "internal":
                continue
            picking.location_id = stock

    def action_vpk_transfer_request(self):
        """เปิดรายการขอโอน และตั้งต้นทางเป็นคลังกลางตอนสร้างใบใหม่"""
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_internal"
        )
        context = dict(literal_eval(action.get("context") or "{}"))
        context["vpk_request_from_central"] = True
        central = self.env["stock.warehouse"]._vpk_central_warehouse()
        if central.int_type_id:
            context["default_picking_type_id"] = central.int_type_id.id
        if central.lot_stock_id:
            context["default_location_id"] = central.lot_stock_id.id
            context["default_location_dest_id"] = central.lot_stock_id.id
            action["domain"] = [
                ("picking_type_id.code", "=", "internal"),
                ("location_id", "child_of", central.lot_stock_id.id),
            ]
        action["name"] = _("ขอโอนสินค้า")
        action["display_name"] = _("ขอโอนสินค้า")
        action["context"] = context
        return action

    def _vpk_is_central_transfer_request(self):
        """ใบร่างโอนออกจากคลังกลางไปคลังอื่น ยังไม่ใช่ใบหยิบหรือใบแพ็ค"""
        self.ensure_one()
        if self.state != "draft" or self.return_id or self.vpk_central_chain:
            return False
        if not self.move_ids:
            return False
        central = self.env["stock.warehouse"]._vpk_central_warehouse()
        stock = central.lot_stock_id
        if not central or not stock or self.picking_type_id != central.int_type_id:
            return False
        dest = self.location_dest_id
        if (
            not self.location_id
            or not dest
            or dest.usage != "internal"
            or not self.location_id._child_of(stock)
            or dest._child_of(stock)
        ):
            return False
        return True

    def _vpk_start_central_transfer_flow(self):
        """รับใบแล้ว ดึงรายการ แล้วเปิดใบแพ็คและใบอัปเดตปลายทางให้รอต่อกัน"""
        self.ensure_one()
        central = self.env["stock.warehouse"]._vpk_central_warehouse()
        central._vpk_configure_central_transfer_flow()
        central.invalidate_recordset()
        pick_type = central.pick_type_id
        pack_type = central.pack_type_id
        pack_loc = central.wh_pack_stock_loc_id
        output_loc = central.wh_output_stock_loc_id
        if not pick_type or not pack_type or not pack_loc or not output_loc:
            return super().action_confirm()

        final_dest = self.location_dest_id
        if not self.group_id:
            self.group_id = self.env["procurement.group"].create(
                {
                    "name": self.name or _("โอนจากคลังกลาง"),
                    "move_type": self.move_type,
                }
            )
        self.with_context(vpk_request_from_central=False).write(
            {
                "picking_type_id": pick_type.id,
                "location_id": central.lot_stock_id.id,
                "location_dest_id": pack_loc.id,
                "vpk_central_chain": True,
                "vpk_central_chain_role": "pick",
            }
        )
        moves = self.move_ids.filtered(lambda move: move.state not in ("done", "cancel"))
        moves.write(
            {
                "location_final_id": final_dest.id,
                "group_id": self.group_id.id,
                "warehouse_id": central.id,
            }
        )
        res = super(StockPicking, self).action_confirm()
        self.action_assign()

        pack_moves = self.env["stock.move"]
        deliver_moves = self.env["stock.move"]
        for move in self.move_ids.filtered(lambda item: item.state not in ("done", "cancel")):
            if move.move_dest_ids:
                continue
            pack_move = move._vpk_chain_move(
                pack_loc, output_loc, final_dest, pack_type, central
            )
            deliver_move = pack_move._vpk_chain_move(
                output_loc, final_dest, final_dest, central.int_type_id, central
            )
            pack_moves |= pack_move
            deliver_moves |= deliver_move
        chain_ctx = {
            "vpk_keep_picking_locations": True,
            "vpk_request_from_central": False,
        }
        if pack_moves:
            pack_moves.with_context(
                **chain_ctx, vpk_central_chain_role="pack"
            )._action_confirm(merge=False)
        if deliver_moves:
            deliver_moves.with_context(
                **chain_ctx, vpk_central_chain_role="deliver"
            )._action_confirm(merge=False)
        return res

    def action_confirm(self):
        starters = self.filtered(lambda picking: picking._vpk_is_central_transfer_request())
        res = super(StockPicking, self - starters).action_confirm()
        for picking in starters:
            picking._vpk_start_central_transfer_flow()
        return res

    def action_vpk_print_pick_slip(self):
        self.ensure_one()
        return self.env.ref("stock.action_report_picking").report_action(self)
