import logging
from collections import defaultdict

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    @api.model
    def _cron_auto_internal_requisition(self):
        """สร้างใบขอเบิกภายใน (Internal Transfer Draft) อัตโนมัติ
        ตามเกณฑ์สต็อกขั้นต่ำ-ขั้นสูง (Min-Max) ของแต่ละหอผู้ป่วย/หน่วยงาน
        """
        Picking = self.env["stock.picking"]
        Move = self.env["stock.move"]

        warehouses = self.env["stock.warehouse"].search([])
        total_picks = 0

        for wh in warehouses:
            stock_loc = wh.lot_stock_id
            int_type = wh.int_type_id
            if not int_type:
                continue

            orderpoints = self.search([
                ("warehouse_id", "=", wh.id),
                ("location_id", "child_of", stock_loc.id),
                ("location_id", "!=", stock_loc.id),
            ])
            if not orderpoints:
                continue

            ward_orders = defaultdict(list)

            for op in orderpoints:
                on_hand = op.product_id.with_context(
                    location=op.location_id.id
                ).qty_available
                if on_hand >= op.product_min_qty:
                    continue
                need = op.product_max_qty - on_hand
                if need <= 0:
                    continue
                ward_orders[op.location_id.id].append({
                    "product_id": op.product_id.id,
                    "qty": need,
                    "uom_id": op.product_id.uom_id.id,
                    "product_name": op.product_id.display_name,
                })

            today = fields.Date.context_today(self)
            for ward_loc_id, items in ward_orders.items():
                ward_loc = self.env["stock.location"].browse(ward_loc_id)

                existing = Picking.search([
                    ("picking_type_id", "=", int_type.id),
                    ("location_id", "=", stock_loc.id),
                    ("location_dest_id", "=", ward_loc_id),
                    ("state", "=", "draft"),
                    ("scheduled_date", ">=", fields.Datetime.to_string(
                        fields.Datetime.start_of(fields.Datetime.now(), "day")
                    )),
                ], limit=1)
                if existing:
                    _logger.info(
                        "Auto-requisition: skip %s → %s (already exists: %s)",
                        stock_loc.name, ward_loc.name, existing.name,
                    )
                    continue

                pick = Picking.create({
                    "picking_type_id": int_type.id,
                    "location_id": stock_loc.id,
                    "location_dest_id": ward_loc_id,
                    "scheduled_date": fields.Datetime.now(),
                    "origin": _("เบิกอัตโนมัติ %s") % today,
                })

                for item in items:
                    Move.create({
                        "name": _("เบิก %(product)s → %(ward)s") % {
                            "product": item["product_name"],
                            "ward": ward_loc.name,
                        },
                        "product_id": item["product_id"],
                        "product_uom_qty": item["qty"],
                        "product_uom": item["uom_id"],
                        "picking_id": pick.id,
                        "location_id": stock_loc.id,
                        "location_dest_id": ward_loc_id,
                    })

                total_picks += 1
                _logger.info(
                    "Auto-requisition: created %s (%d items) %s → %s",
                    pick.name, len(items), stock_loc.name, ward_loc.name,
                )

        _logger.info(
            "Auto-requisition completed: %d internal transfers created", total_picks
        )
