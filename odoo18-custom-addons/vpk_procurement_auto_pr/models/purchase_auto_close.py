# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    auto_close_on_full_receipt = fields.Boolean(
        string="ปิด PO อัตโนมัติเมื่อรับครบ",
        default=True,
        tracking=True,
        help="ปิดใบสั่งซื้อเป็น Done เมื่อรับครบทุกรายการตามจำนวนที่สั่ง",
    )
    receipt_completion_percent = fields.Float(
        string="ความคืบหน้าการรับ (%)",
        compute="_compute_receipt_completion_percent",
        store=True,
    )
    auto_closed_on_receipt = fields.Boolean(
        string="ปิดจากการรับครบอัตโนมัติ",
        readonly=True,
        copy=False,
        tracking=True,
    )
    auto_closed_at = fields.Datetime(
        string="วันที่ปิดอัตโนมัติ",
        readonly=True,
        copy=False,
    )
    auto_closed_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ปิดอัตโนมัติโดย",
        readonly=True,
        copy=False,
    )
    auto_close_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="ใบรับสินค้าที่ทำให้ปิด PO",
        readonly=True,
        copy=False,
    )

    @api.depends("order_line.product_qty", "order_line.qty_received")
    def _compute_receipt_completion_percent(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda line: not line.display_type and line.product_qty > 0
            )
            ordered_qty = sum(lines.mapped("product_qty"))
            received_qty = sum(
                min(line.qty_received, line.product_qty) for line in lines
            )
            order.receipt_completion_percent = (
                min(received_qty / ordered_qty * 100.0, 100.0)
                if ordered_qty
                else 0.0
            )

    def _is_fully_received(self):
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda line: not line.display_type and line.product_qty > 0
        )
        return bool(lines) and all(
            float_compare(
                line.qty_received,
                line.product_qty,
                precision_rounding=line.product_uom.rounding,
            )
            >= 0
            for line in lines
        )

    def _auto_close_if_fully_received(self, picking):
        for order in self.filtered(
            lambda po: po.state == "purchase"
            and po.auto_close_on_full_receipt
        ):
            order.order_line.invalidate_recordset(["qty_received"])
            if not order._is_fully_received():
                continue
            order.button_done()
            order.write({
                "auto_closed_on_receipt": True,
                "auto_closed_at": fields.Datetime.now(),
                "auto_closed_by_id": self.env.user.id,
                "auto_close_picking_id": picking.id,
            })
            order.message_post(
                body=_(
                    "ระบบปิดใบสั่งซื้ออัตโนมัติ เนื่องจากรับพัสดุครบ "
                    "100%% จากใบรับสินค้า %s"
                )
                % picking.display_name
            )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        result = super()._action_done()
        for picking in self.filtered(
            lambda record: record.state == "done"
            and record.picking_type_code == "incoming"
        ):
            orders = picking.move_ids.purchase_line_id.order_id
            orders._auto_close_if_fully_received(picking)
        return result
