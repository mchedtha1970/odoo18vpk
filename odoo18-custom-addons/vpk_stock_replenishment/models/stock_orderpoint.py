import logging

from dateutil import relativedelta

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        if not self.ids:
            return res
        moves = self.env["stock.move"].search(
            [
                ("orderpoint_id", "in", self.ids),
                ("state", "not in", ("done", "cancel")),
            ]
        )
        for move in moves:
            orderpoint = move.orderpoint_id
            if not orderpoint:
                continue
            if move.location_dest_id != orderpoint.location_id:
                continue
            res[orderpoint.id] += move.product_uom._compute_quantity(
                move.product_uom_qty,
                orderpoint.product_uom,
                round=False,
            )
        return res

    def _vpk_uses_transfer_first(self):
        self.ensure_one()
        return bool(self.warehouse_id.vpk_replenishment_source_wh_id)

    def _vpk_get_source_free_qty(self, source_wh):
        self.ensure_one()
        if self.product_id.tracking == "none":
            return self.product_id.with_context(
                location=source_wh.lot_stock_id.id
            ).free_qty
        return self._vpk_get_lot_available_qty(source_wh.lot_stock_id)

    def _vpk_get_lot_available_qty(self, location):
        self.ensure_one()
        total = 0.0
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id", "child_of", location.id),
                ("lot_id", "!=", False),
            ]
        )
        for quant in quants:
            available = quant.quantity - quant.reserved_quantity
            if float_compare(available, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                total += available
        return total

    def _vpk_allocate_lots_from_location(self, location, qty):
        self.ensure_one()
        rounding = self.product_uom.rounding
        if self.product_id.tracking == "none":
            return [(False, qty)]

        quants = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id", "child_of", location.id),
                ("lot_id", "!=", False),
            ]
        )
        quants = quants.filtered(
            lambda quant: float_compare(
                quant.quantity - quant.reserved_quantity,
                0.0,
                precision_rounding=rounding,
            )
            > 0
        ).sorted(lambda quant: (quant.removal_date or quant.in_date, quant.id))

        allocations = []
        remaining = qty
        for quant in quants:
            if float_compare(remaining, 0.0, precision_rounding=rounding) <= 0:
                break
            available = quant.quantity - quant.reserved_quantity
            take = min(remaining, available)
            allocations.append((quant.lot_id, take))
            remaining -= take

        return allocations

    def _vpk_get_buy_route(self):
        self.ensure_one()
        buy_route = self.env.ref(
            "purchase_stock.route_warehouse0_buy", raise_if_not_found=False
        )
        if buy_route and buy_route in (
            self.warehouse_id.route_ids
            | self.product_id.route_ids
            | self.product_id.categ_id.total_route_ids
        ):
            return buy_route
        warehouse_buy_routes = self.warehouse_id.route_ids.filtered(
            lambda route: route.rule_ids.filtered(lambda rule: rule.action == "buy")
        )
        return warehouse_buy_routes[:1]

    def _vpk_prepare_procurement_origin(self):
        self.ensure_one()
        origins = self.env.context.get("origins", {}).get(self.id, False)
        if origins:
            return "%s - %s" % (self.display_name, ",".join(origins))
        return self.name

    def _vpk_post_assign_transfer_lots(self, source_wh, transfer_specs):
        """transfer_specs: list of (lot, qty) actually transferred."""
        if not transfer_specs:
            return
        Move = self.env["stock.move"]
        move_lot_qty = []
        for orderpoint in self:
            specs = [
                (lot, qty)
                for lot, qty in transfer_specs
                if lot and orderpoint.product_id.tracking != "none"
            ]
            if not specs:
                continue
            for lot, qty in specs:
                moves = Move.search(
                    [
                        ("orderpoint_id", "=", orderpoint.id),
                        ("product_id", "=", orderpoint.product_id.id),
                        ("location_id", "=", source_wh.lot_stock_id.id),
                        ("state", "not in", ("done", "cancel")),
                        ("restrict_lot_id", "in", (False, lot.id)),
                    ],
                    order="id desc",
                    limit=1,
                )
                if moves:
                    move_lot_qty.append((moves[0], lot, qty))
        Move._vpk_apply_lot_on_moves(move_lot_qty)

    def _vpk_run_transfer_then_pr(self, raise_user_error=True):
        Procurement = self.env["procurement.group"].Procurement
        procurements = []
        transfer_specs_by_orderpoint = {}

        for orderpoint in self:
            rounding = orderpoint.product_uom.rounding
            qty_needed = orderpoint.qty_to_order
            if float_compare(qty_needed, 0.0, precision_rounding=rounding) <= 0:
                continue

            source_wh = orderpoint.warehouse_id.vpk_replenishment_source_wh_id
            if not source_wh:
                continue

            date = orderpoint._get_orderpoint_procurement_date()
            global_visibility_days = self.env.context.get(
                "global_visibility_days",
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("stock.visibility_days", 0),
            )
            if global_visibility_days:
                date -= relativedelta.relativedelta(days=int(global_visibility_days))

            origin = orderpoint._vpk_prepare_procurement_origin()

            free_qty = orderpoint._vpk_get_source_free_qty(source_wh)
            transfer_qty = min(qty_needed, free_qty)
            purchase_qty = qty_needed - transfer_qty
            transfer_specs = []

            if float_compare(transfer_qty, 0.0, precision_rounding=rounding) > 0:
                resupply_route = orderpoint.warehouse_id._vpk_get_resupply_route(
                    source_wh
                )
                if not resupply_route:
                    _logger.warning(
                        "VPK replenishment: no resupply route from %s to %s for %s",
                        source_wh.name,
                        orderpoint.warehouse_id.name,
                        orderpoint.product_id.display_name,
                    )
                    purchase_qty = qty_needed
                    transfer_qty = 0.0
                else:
                    lot_allocations = orderpoint._vpk_allocate_lots_from_location(
                        source_wh.lot_stock_id, transfer_qty
                    )
                    if (
                        orderpoint.product_id.tracking != "none"
                        and not lot_allocations
                    ):
                        purchase_qty = qty_needed
                        transfer_qty = 0.0
                    else:
                        for lot, lot_qty in lot_allocations:
                            if float_is_zero(
                                lot_qty, precision_rounding=rounding
                            ):
                                continue
                            transfer_values = orderpoint._prepare_procurement_values(
                                date=date
                            )
                            transfer_values["route_ids"] = resupply_route
                            if lot:
                                transfer_values["restrict_lot_id"] = lot
                            procurements.append(
                                Procurement(
                                    orderpoint.product_id,
                                    lot_qty,
                                    orderpoint.product_uom,
                                    orderpoint.location_id,
                                    orderpoint.name,
                                    origin,
                                    orderpoint.company_id,
                                    transfer_values,
                                )
                            )
                            if lot:
                                transfer_specs.append((lot, lot_qty))

            if float_compare(purchase_qty, 0.0, precision_rounding=rounding) > 0:
                if not orderpoint.product_id.purchase_request:
                    _logger.info(
                        "VPK replenishment: %s needs purchase but purchase_request "
                        "is disabled; standard buy route will be used.",
                        orderpoint.product_id.display_name,
                    )
                buy_route = orderpoint._vpk_get_buy_route()
                purchase_values = orderpoint._prepare_procurement_values(date=date)
                if buy_route:
                    purchase_values["route_ids"] = buy_route
                procurements.append(
                    Procurement(
                        orderpoint.product_id,
                        purchase_qty,
                        orderpoint.product_uom,
                        orderpoint.location_id,
                        orderpoint.name,
                        origin,
                        orderpoint.company_id,
                        purchase_values,
                    )
                )

            transfer_specs_by_orderpoint[orderpoint.id] = transfer_specs

        if not procurements:
            return True

        try:
            self.env["procurement.group"].with_context(
                from_orderpoint=True
            ).run(procurements, raise_user_error=raise_user_error)
        except Exception as error:
            if raise_user_error:
                raise UserError(
                    _("Unable to run VPK replenishment: %s", error)
                ) from error
            _logger.exception("VPK replenishment procurement failed")
            return False

        for orderpoint in self:
            source_wh = orderpoint.warehouse_id.vpk_replenishment_source_wh_id
            specs = transfer_specs_by_orderpoint.get(orderpoint.id, [])
            orderpoint._vpk_post_assign_transfer_lots(source_wh, specs)

        return True

    def _procure_orderpoint_confirm(
        self, use_new_cursor=False, company_id=None, raise_user_error=True
    ):
        vpk_orderpoints = self.filtered(
            lambda orderpoint: orderpoint._vpk_uses_transfer_first()
        )
        standard_orderpoints = self - vpk_orderpoints

        if vpk_orderpoints:
            vpk_orderpoints._vpk_run_transfer_then_pr(
                raise_user_error=raise_user_error
            )
            vpk_orderpoints._post_process_scheduler()

        if not standard_orderpoints:
            return {}

        return super(
            StockWarehouseOrderpoint, standard_orderpoints
        )._procure_orderpoint_confirm(
            use_new_cursor=use_new_cursor,
            company_id=company_id,
            raise_user_error=raise_user_error,
        )
