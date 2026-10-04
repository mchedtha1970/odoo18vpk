# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    vpk_vendor_loan_line_id = fields.Many2one(
        "vpk.vendor.loan.line",
        string="รายการยืมที่หักล้าง",
        copy=False,
        index=True,
    )
    vpk_loan_offset_done = fields.Boolean(
        string="หักล้างยืมแล้ว",
        copy=False,
    )

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        if not self.env.context.get("vpk_loan_offset"):
            moves._vpk_offset_vendor_loan()
        return moves

    def _vpk_loan_followup_location(self):
        """คลังยืมของรายการยืมค้างที่ใบรับนี้ต้องเข้า เพื่อหักล้างในคลังเดียวกัน"""
        self.ensure_one()
        line = self._vpk_open_loan_lines()[:1]
        return line.loan_id.location_dest_id

    def _vpk_open_loan_lines(self):
        """รายการยืมค้างที่สินค้าและผู้ขายตรงกับใบรับนี้"""
        self.ensure_one()
        picking = self.picking_id
        if (
            not picking
            or picking.vpk_vendor_loan_id
            or picking.picking_type_id.code != "incoming"
        ):
            return self.env["vpk.vendor.loan.line"]
        Line = self.env["vpk.vendor.loan.line"]
        domain = [
            ("product_id", "=", self.product_id.id),
            ("qty_remaining", ">", 0),
            ("loan_id.state", "in", ("received", "purchasing")),
        ]
        requests = self.env["purchase.request"]
        if self.purchase_line_id and "purchase_request_lines" in self.purchase_line_id._fields:
            requests = self.purchase_line_id.purchase_request_lines.request_id
        if requests:
            linked = Line.search(
                domain + [("loan_id.purchase_request_id", "in", requests.ids)],
                order="id",
            )
            if linked:
                return linked
        partner = picking.partner_id
        if not partner and self.purchase_line_id:
            partner = self.purchase_line_id.order_id.partner_id
        if not partner:
            return Line
        return Line.search(
            domain + [("loan_id.partner_id", "=", partner.id)],
            order="id",
        )

    def _vpk_vendor_loan_lines_for_receipt(self):
        """ใบรับของซื้อที่ตรงกับยืมค้าง ใช้หลังตรวจรับเสร็จ"""
        self.ensure_one()
        if self.state != "done":
            return self.env["vpk.vendor.loan.line"]
        return self._vpk_open_loan_lines()

    def _vpk_offset_vendor_loan(self):
        clearing = self.env.ref(
            "vpk_vendor_loan.location_vendor_loan_clearing",
            raise_if_not_found=False,
        )
        if not clearing:
            return
        for move in self.filtered(lambda item: not item.vpk_loan_offset_done):
            lines = move._vpk_vendor_loan_lines_for_receipt()
            if not lines:
                continue
            posted = []
            for move_line in move.move_line_ids.filtered(lambda item: item.quantity > 0):
                qty_left = move_line.quantity
                while (
                    float_compare(
                        qty_left, 0, precision_rounding=move.product_uom.rounding
                    )
                    > 0
                    and lines
                ):
                    loan_line = lines[0]
                    if float_compare(
                        loan_line.qty_remaining,
                        0,
                        precision_rounding=loan_line.product_uom_id.rounding,
                    ) <= 0:
                        lines = lines[1:]
                        continue
                    remaining_in_move_uom = loan_line.product_uom_id._compute_quantity(
                        loan_line.qty_remaining, move.product_uom
                    )
                    take = min(qty_left, remaining_in_move_uom)
                    if float_is_zero(take, precision_rounding=move.product_uom.rounding):
                        break
                    move._vpk_create_loan_offset(loan_line, move_line, take, clearing)
                    cleared = move.product_uom._compute_quantity(
                        take, loan_line.product_uom_id
                    )
                    loan_line.qty_cleared += cleared
                    qty_left -= take
                    posted.append((loan_line, cleared))
                    if float_compare(
                        loan_line.qty_remaining,
                        0,
                        precision_rounding=loan_line.product_uom_id.rounding,
                    ) <= 0:
                        lines = lines[1:]
            if posted:
                move.vpk_loan_offset_done = True
                loans = self.env["vpk.vendor.loan"]
                for loan_line, cleared in posted:
                    loans |= loan_line.loan_id
                    loan_line.loan_id.message_post(
                        body=_(
                            "หักล้าง %(qty)s %(uom)s ของ %(product)s "
                            "กับใบรับ %(picking)s คงค้างยืม %(left)s"
                        )
                        % {
                            "qty": cleared,
                            "uom": loan_line.product_uom_id.name,
                            "product": loan_line.product_id.display_name,
                            "picking": move.picking_id.name,
                            "left": loan_line.qty_remaining,
                        }
                    )
                loans._vpk_refresh_clear_state()

    def _vpk_create_loan_offset(self, loan_line, move_line, quantity, clearing):
        """ดึงจำนวนที่รับซ้ำออกจากคลัง เพราะของยืมเข้าสต็อกไปแล้ว"""
        self.ensure_one()
        offset = self.env["stock.move"].create(
            {
                "name": _("หักล้างยืม %s") % loan_line.loan_id.name,
                "product_id": self.product_id.id,
                "product_uom": self.product_uom.id,
                "product_uom_qty": quantity,
                "location_id": move_line.location_dest_id.id,
                "location_dest_id": clearing.id,
                "company_id": self.company_id.id,
                "origin": self.picking_id.name or self.origin,
                "vpk_vendor_loan_line_id": loan_line.id,
                "procure_method": "make_to_stock",
            }
        )
        offset._action_confirm(merge=False)
        self.env["stock.move.line"].create(
            {
                "move_id": offset.id,
                "product_id": self.product_id.id,
                "product_uom_id": self.product_uom.id,
                "quantity": quantity,
                "location_id": move_line.location_dest_id.id,
                "location_dest_id": clearing.id,
                "lot_id": move_line.lot_id.id,
                "picked": True,
                "company_id": self.company_id.id,
            }
        )
        offset.picked = True
        offset.with_context(vpk_loan_offset=True)._action_done()
        return offset
