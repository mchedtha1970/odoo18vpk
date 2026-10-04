import logging
from collections import defaultdict

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _vpk_auto_requisition_route(self):
        """คืน (ตำแหน่งต้นทาง, ประเภทใบโอน) ของใบเบิกอัตโนมัติ

        ถ้าคลังนี้มีคลังเติมสต็อกหลัก เช่น คลังยาดึงจากคลังกลาง
        ต้นทางคือสต็อกของคลังนั้น ตำแหน่งกฎจะเป็นปลายทางได้ทั้งตำแหน่งคลังและตำแหน่งย่อย
        """
        self.ensure_one()
        warehouse = self.warehouse_id
        if not warehouse or not self.location_id:
            return False
        source_wh = warehouse.vpk_replenishment_source_wh_id if (
            "vpk_replenishment_source_wh_id" in warehouse._fields
        ) else False
        if source_wh and source_wh.int_type_id and source_wh.lot_stock_id:
            return source_wh.lot_stock_id, source_wh.int_type_id
        stock_loc = warehouse.lot_stock_id
        if (
            not warehouse.int_type_id
            or not stock_loc
            or self.location_id == stock_loc
            or not self.location_id.parent_path.startswith(stock_loc.parent_path)
        ):
            return False
        return stock_loc, warehouse.int_type_id

    @api.model
    def _cron_auto_internal_requisition(self):
        """สร้างใบขอเบิกภายใน (Internal Transfer Draft) อัตโนมัติ
        ตามเกณฑ์สต็อกขั้นต่ำ-ขั้นสูง (Min-Max)
        ถ้าคลังมีคลังเติมสต็อกหลัก ใบโอนจะออกจากคลังนั้น เช่น จากคลังกลางไปคลังยา
        """
        Picking = self.env["stock.picking"]
        Move = self.env["stock.move"]
        groups = defaultdict(list)
        routes = {}

        for op in self.search([]):
            route = op._vpk_auto_requisition_route()
            if not route:
                continue
            source_loc, int_type = route
            on_hand = op.product_id.with_context(
                location=op.location_id.id
            ).qty_available
            if on_hand >= op.product_min_qty:
                continue
            need = op.product_max_qty - on_hand
            if need <= 0:
                continue
            key = (source_loc.id, op.location_id.id, int_type.id)
            routes[key] = (source_loc, op.location_id, int_type)
            groups[key].append({
                "product_id": op.product_id.id,
                "qty": need,
                "uom_id": op.product_id.uom_id.id,
                "product_name": op.product_id.display_name,
            })

        today = fields.Date.context_today(self)
        day_start = fields.Datetime.to_string(
            fields.Datetime.start_of(fields.Datetime.now(), "day")
        )
        total_picks = 0
        for key, items in groups.items():
            source_loc, dest_loc, int_type = routes[key]
            existing = Picking.search([
                ("picking_type_id", "=", int_type.id),
                ("location_id", "=", source_loc.id),
                ("location_dest_id", "=", dest_loc.id),
                ("state", "=", "draft"),
                ("scheduled_date", ">=", day_start),
            ], limit=1)
            if existing:
                _logger.info(
                    "Auto-requisition: skip %s → %s (already exists: %s)",
                    source_loc.complete_name, dest_loc.complete_name, existing.name,
                )
                continue

            pick = Picking.create({
                "picking_type_id": int_type.id,
                "location_id": source_loc.id,
                "location_dest_id": dest_loc.id,
                "scheduled_date": fields.Datetime.now(),
                "origin": _("เบิกอัตโนมัติ %s") % today,
            })
            for item in items:
                Move.create({
                    "name": _("เบิก %(product)s → %(dest)s") % {
                        "product": item["product_name"],
                        "dest": dest_loc.complete_name,
                    },
                    "product_id": item["product_id"],
                    "product_uom_qty": item["qty"],
                    "product_uom": item["uom_id"],
                    "picking_id": pick.id,
                    "location_id": source_loc.id,
                    "location_dest_id": dest_loc.id,
                })
            total_picks += 1
            _logger.info(
                "Auto-requisition: created %s (%d items) %s → %s",
                pick.name, len(items),
                source_loc.complete_name, dest_loc.complete_name,
            )

        _logger.info(
            "Auto-requisition completed: %d internal transfers created", total_picks
        )
