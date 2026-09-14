# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class ProductUomChangeWizard(models.TransientModel):
    _name = "vpk.product.uom.change.wizard"
    _description = "Change Product UoM Wizard"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
    )
    current_uom_id = fields.Many2one(
        "uom.uom",
        string="Current UoM",
        related="product_tmpl_id.uom_id",
        readonly=True,
    )
    uom_category_id = fields.Many2one(
        related="current_uom_id.category_id",
        readonly=True,
    )
    new_uom_id = fields.Many2one(
        "uom.uom",
        string="New UoM",
        required=True,
        domain="[('category_id', '=', uom_category_id)]",
    )
    update_uom_po = fields.Boolean(
        string="Update Purchase UoM",
        default=True,
        help="If Purchase UoM equals the current product UoM, set it to the new UoM.",
    )
    convert_prices = fields.Boolean(
        string="Convert Sale Price & Cost",
        default=True,
        help="Recalculate list price and cost according to the UoM conversion factor.",
    )
    update_document_uom = fields.Boolean(
        string="Update document lines using current UoM",
        default=True,
        help="Also change SO/PO/stock lines that use the current product UoM "
        "to the new UoM (quantities converted).",
    )
    confirm = fields.Boolean(
        string="I understand this will rewrite historical stock quantities",
        default=False,
    )

    stock_move_count = fields.Integer(compute="_compute_impact")
    stock_move_line_count = fields.Integer(compute="_compute_impact")
    quant_count = fields.Integer(compute="_compute_impact")
    svl_count = fields.Integer(compute="_compute_impact")
    sale_line_count = fields.Integer(compute="_compute_impact")
    purchase_line_count = fields.Integer(compute="_compute_impact")
    factor_preview = fields.Char(compute="_compute_impact", string="Conversion")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if (
            not res.get("product_tmpl_id")
            and self.env.context.get("active_model") == "product.template"
            and self.env.context.get("active_id")
        ):
            res["product_tmpl_id"] = self.env.context["active_id"]
        return res

    @api.depends("product_tmpl_id", "new_uom_id", "current_uom_id")
    def _compute_impact(self):
        Move = self.env["stock.move"]
        MoveLine = self.env["stock.move.line"]
        Quant = self.env["stock.quant"]
        for wiz in self:
            product_ids = wiz.product_tmpl_id.with_context(
                active_test=False
            ).product_variant_ids.ids
            if not product_ids:
                wiz.update(
                    {
                        "stock_move_count": 0,
                        "stock_move_line_count": 0,
                        "quant_count": 0,
                        "svl_count": 0,
                        "sale_line_count": 0,
                        "purchase_line_count": 0,
                        "factor_preview": False,
                    }
                )
                continue
            domain = [("product_id", "in", product_ids)]
            wiz.stock_move_count = Move.sudo().search_count(domain)
            wiz.stock_move_line_count = MoveLine.sudo().search_count(domain)
            wiz.quant_count = Quant.sudo().search_count(domain)
            wiz.svl_count = (
                self.env["stock.valuation.layer"].sudo().search_count(domain)
                if "stock.valuation.layer" in self.env
                else 0
            )
            wiz.sale_line_count = (
                self.env["sale.order.line"].sudo().search_count(domain)
                if "sale.order.line" in self.env
                else 0
            )
            wiz.purchase_line_count = (
                self.env["purchase.order.line"].sudo().search_count(domain)
                if "purchase.order.line" in self.env
                else 0
            )
            if (
                wiz.current_uom_id
                and wiz.new_uom_id
                and wiz.current_uom_id != wiz.new_uom_id
            ):
                sample = wiz.current_uom_id._compute_quantity(
                    1.0, wiz.new_uom_id, round=False
                )
                wiz.factor_preview = _(
                    "1 %(old)s = %(qty)s %(new)s",
                    old=wiz.current_uom_id.display_name,
                    qty=sample,
                    new=wiz.new_uom_id.display_name,
                )
            else:
                wiz.factor_preview = False

    def _product_variants(self):
        self.ensure_one()
        return self.product_tmpl_id.with_context(active_test=False).product_variant_ids

    def _factor(self, old_uom, new_uom):
        return new_uom.factor / (old_uom.factor or 1.0)

    def _price_factor(self, old_uom, new_uom):
        return (old_uom.factor or 1.0) / (new_uom.factor or 1.0)

    def _convert_qty(self, qty, from_uom, to_uom):
        if float_is_zero(qty, precision_digits=12) or from_uom == to_uom:
            return qty
        return from_uom._compute_quantity(qty, to_uom, round=False)

    def _convert_price(self, price, from_uom, to_uom):
        if float_is_zero(price, precision_digits=12) or from_uom == to_uom:
            return price
        return from_uom._compute_price(price, to_uom)

    def action_apply(self):
        self.ensure_one()
        if not self.confirm:
            raise UserError(
                _(
                    "Please confirm that you understand historical quantities will be rewritten."
                )
            )
        if not self.new_uom_id:
            raise UserError(_("Please select the new Unit of Measure."))
        if self.new_uom_id == self.current_uom_id:
            raise UserError(_("New UoM must be different from the current UoM."))
        if self.new_uom_id.category_id != self.current_uom_id.category_id:
            raise UserError(
                _(
                    "New UoM must belong to the same category as the current UoM (%s)."
                )
                % self.current_uom_id.category_id.display_name
            )

        products = self._product_variants()
        if not products:
            raise UserError(_("Product has no variants to update."))

        old_uom = self.current_uom_id
        new_uom = self.new_uom_id
        product_ids = tuple(products.ids)

        self._update_quants(product_ids, old_uom, new_uom)
        self._update_valuation_layers(product_ids, old_uom, new_uom)
        self._update_orderpoints(product_ids, old_uom, new_uom)
        self._update_packaging(products.ids, old_uom, new_uom)

        if self.update_document_uom:
            self._update_stock_moves(product_ids, old_uom, new_uom)
            self._update_stock_move_lines(product_ids, old_uom, new_uom)
            self._update_scraps(product_ids, old_uom, new_uom)
            self._update_sale_lines(product_ids, old_uom, new_uom)
            self._update_purchase_lines(product_ids, old_uom, new_uom)
            self._update_purchase_request_lines(product_ids, old_uom, new_uom)
            self._update_purchase_requisition_lines(product_ids, old_uom, new_uom)
            self._update_account_move_lines(product_ids, old_uom, new_uom)

        # Convert stored "qty in product UoM" for lines that keep another line UoM
        self._scale_product_uom_stored_qty(product_ids, old_uom, new_uom)

        tmpl_vals = {}
        if self.convert_prices:
            self._update_product_prices(products, old_uom, new_uom)
            tmpl_vals["list_price"] = self._convert_price(
                self.product_tmpl_id.list_price, old_uom, new_uom
            )

        if self.update_uom_po and self.product_tmpl_id.uom_po_id == old_uom:
            tmpl_vals["uom_po_id"] = new_uom.id
        elif self.product_tmpl_id.uom_po_id.category_id != new_uom.category_id:
            tmpl_vals["uom_po_id"] = new_uom.id

        tmpl_vals["uom_id"] = new_uom.id
        self.product_tmpl_id.with_context(vpk_allow_uom_change=True).write(tmpl_vals)

        # Recompute stored product-UoM quantities via SQL (ORM inverse forbids
        # writing product_qty / assigning via _compute_product_qty directly).
        self._sql_recompute_move_product_qty(product_ids)
        self._sql_recompute_move_line_product_uom_qty(product_ids)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("UoM updated"),
                "message": _(
                    "Product UoM changed from %(old)s to %(new)s. Related quantities were converted.",
                    old=old_uom.display_name,
                    new=new_uom.display_name,
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _sql_recompute_move_product_qty(self, product_ids):
        """Set stock_move.product_qty = convert(product_uom_qty → product.uom_id)."""
        self.env.cr.execute(
            """
            UPDATE stock_move AS sm
               SET product_qty = CASE
                    WHEN move_uom.id = prod_uom.id THEN sm.product_uom_qty
                    WHEN COALESCE(move_uom.factor, 0) = 0 THEN sm.product_uom_qty
                    ELSE sm.product_uom_qty / move_uom.factor * prod_uom.factor
               END
              FROM uom_uom AS move_uom,
                   product_product AS pp,
                   product_template AS pt,
                   uom_uom AS prod_uom
             WHERE sm.product_id IN %s
               AND sm.product_uom = move_uom.id
               AND sm.product_id = pp.id
               AND pp.product_tmpl_id = pt.id
               AND pt.uom_id = prod_uom.id
            """,
            (product_ids,),
        )
        self.env["stock.move"].invalidate_model(["product_qty"])

    def _sql_recompute_move_line_product_uom_qty(self, product_ids):
        """Set stock_move_line.quantity_product_uom from line UoM → product UoM."""
        self.env.cr.execute(
            """
            UPDATE stock_move_line AS sml
               SET quantity_product_uom = CASE
                    WHEN line_uom.id = prod_uom.id THEN sml.quantity
                    WHEN COALESCE(line_uom.factor, 0) = 0 THEN sml.quantity
                    ELSE sml.quantity / line_uom.factor * prod_uom.factor
               END
              FROM uom_uom AS line_uom,
                   product_product AS pp,
                   product_template AS pt,
                   uom_uom AS prod_uom
             WHERE sml.product_id IN %s
               AND sml.product_uom_id = line_uom.id
               AND sml.product_id = pp.id
               AND pp.product_tmpl_id = pt.id
               AND pt.uom_id = prod_uom.id
            """,
            (product_ids,),
        )
        self.env["stock.move.line"].invalidate_model(["quantity_product_uom"])

    def _update_quants(self, product_ids, old_uom, new_uom):
        factor = self._factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE stock_quant
               SET quantity = quantity * %s,
                   reserved_quantity = reserved_quantity * %s
             WHERE product_id IN %s
            """,
            (factor, factor, product_ids),
        )
        self.env["stock.quant"].invalidate_model(
            ["quantity", "reserved_quantity", "available_quantity"]
        )

    def _update_valuation_layers(self, product_ids, old_uom, new_uom):
        if "stock.valuation.layer" not in self.env:
            return
        factor = self._factor(old_uom, new_uom)
        price_factor = self._price_factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE stock_valuation_layer
               SET quantity = quantity * %s,
                   remaining_qty = remaining_qty * %s,
                   unit_cost = unit_cost * %s
             WHERE product_id IN %s
            """,
            (factor, factor, price_factor, product_ids),
        )
        self.env["stock.valuation.layer"].invalidate_model(
            ["quantity", "remaining_qty", "unit_cost"]
        )

    def _update_orderpoints(self, product_ids, old_uom, new_uom):
        if "stock.warehouse.orderpoint" not in self.env:
            return
        ops = (
            self.env["stock.warehouse.orderpoint"]
            .sudo()
            .search([("product_id", "in", list(product_ids))])
        )
        for op in ops:
            vals = {
                "product_min_qty": self._convert_qty(
                    op.product_min_qty, old_uom, new_uom
                ),
                "product_max_qty": self._convert_qty(
                    op.product_max_qty, old_uom, new_uom
                ),
            }
            if op.qty_multiple:
                vals["qty_multiple"] = self._convert_qty(
                    op.qty_multiple, old_uom, new_uom
                )
            op.write(vals)

    def _update_packaging(self, product_ids, old_uom, new_uom):
        packs = self.env["product.packaging"].sudo().search(
            [("product_id", "in", product_ids)]
        )
        for pack in packs:
            pack.qty = self._convert_qty(pack.qty, old_uom, new_uom)

    def _update_stock_moves(self, product_ids, old_uom, new_uom):
        factor = self._factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE stock_move
               SET product_uom = %s,
                   product_uom_qty = product_uom_qty * %s,
                   quantity = quantity * %s
             WHERE product_id IN %s
               AND product_uom = %s
            """,
            (new_uom.id, factor, factor, product_ids, old_uom.id),
        )
        self.env["stock.move"].invalidate_model(
            ["product_uom", "product_uom_qty", "quantity", "product_qty"]
        )

    def _update_stock_move_lines(self, product_ids, old_uom, new_uom):
        factor = self._factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE stock_move_line
               SET product_uom_id = %s,
                   quantity = quantity * %s
             WHERE product_id IN %s
               AND product_uom_id = %s
            """,
            (new_uom.id, factor, product_ids, old_uom.id),
        )
        self.env["stock.move.line"].invalidate_model(
            ["product_uom_id", "quantity", "quantity_product_uom"]
        )

    def _update_scraps(self, product_ids, old_uom, new_uom):
        if "stock.scrap" not in self.env:
            return
        factor = self._factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE stock_scrap
               SET product_uom_id = %s,
                   scrap_qty = scrap_qty * %s
             WHERE product_id IN %s
               AND product_uom_id = %s
            """,
            (new_uom.id, factor, product_ids, old_uom.id),
        )

    def _update_sale_lines(self, product_ids, old_uom, new_uom):
        if "sale.order.line" not in self.env:
            return
        factor = self._factor(old_uom, new_uom)
        price_factor = self._price_factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE sale_order_line
               SET product_uom = %s,
                   product_uom_qty = product_uom_qty * %s,
                   qty_delivered = qty_delivered * %s,
                   qty_invoiced = qty_invoiced * %s,
                   price_unit = price_unit * %s
             WHERE product_id IN %s
               AND product_uom = %s
            """,
            (
                new_uom.id,
                factor,
                factor,
                factor,
                price_factor,
                product_ids,
                old_uom.id,
            ),
        )
        self.env["sale.order.line"].invalidate_model()

    def _update_purchase_lines(self, product_ids, old_uom, new_uom):
        if "purchase.order.line" not in self.env:
            return
        factor = self._factor(old_uom, new_uom)
        price_factor = self._price_factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE purchase_order_line
               SET product_uom = %s,
                   product_qty = product_qty * %s,
                   qty_received = qty_received * %s,
                   qty_invoiced = qty_invoiced * %s,
                   price_unit = price_unit * %s
             WHERE product_id IN %s
               AND product_uom = %s
            """,
            (
                new_uom.id,
                factor,
                factor,
                factor,
                price_factor,
                product_ids,
                old_uom.id,
            ),
        )
        self.env["purchase.order.line"].invalidate_model()

    def _update_purchase_request_lines(self, product_ids, old_uom, new_uom):
        if "purchase.request.line" not in self.env:
            return
        factor = self._factor(old_uom, new_uom)
        self.env.cr.execute(
            """
            UPDATE purchase_request_line
               SET product_uom_id = %s,
                   product_qty = product_qty * %s
             WHERE product_id IN %s
               AND product_uom_id = %s
            """,
            (new_uom.id, factor, product_ids, old_uom.id),
        )

    def _update_purchase_requisition_lines(self, product_ids, old_uom, new_uom):
        if "purchase.requisition.line" not in self.env:
            return
        Line = self.env["purchase.requisition.line"]
        uom_field = (
            "product_uom_id" if "product_uom_id" in Line._fields else "product_uom"
        )
        if "product_qty" not in Line._fields:
            return
        factor = self._factor(old_uom, new_uom)
        self.env.cr.execute(
            f"""
            UPDATE purchase_requisition_line
               SET {uom_field} = %s,
                   product_qty = product_qty * %s
             WHERE product_id IN %s
               AND {uom_field} = %s
            """,
            (new_uom.id, factor, product_ids, old_uom.id),
        )

    def _update_account_move_lines(self, product_ids, old_uom, new_uom):
        if "account.move.line" not in self.env:
            return
        factor = self._factor(old_uom, new_uom)
        price_factor = self._price_factor(old_uom, new_uom)
        # Keep debit/credit/balance; only sync qty/UoM/unit price display
        self.env.cr.execute(
            """
            UPDATE account_move_line
               SET product_uom_id = %s,
                   quantity = quantity * %s,
                   price_unit = price_unit * %s
             WHERE product_id IN %s
               AND product_uom_id = %s
            """,
            (new_uom.id, factor, price_factor, product_ids, old_uom.id),
        )

    def _scale_product_uom_stored_qty(self, product_ids, old_uom, new_uom):
        """Scale qty stored in product UoM when line UoM was not the old base UoM."""
        factor = self._factor(old_uom, new_uom)
        # Moves still using another UoM: product_qty was in old product UoM
        self.env.cr.execute(
            """
            UPDATE stock_move
               SET product_qty = product_qty * %s
             WHERE product_id IN %s
               AND product_uom != %s
            """,
            (factor, product_ids, new_uom.id),
        )
        self.env.cr.execute(
            """
            UPDATE stock_move_line
               SET quantity_product_uom = quantity_product_uom * %s
             WHERE product_id IN %s
               AND product_uom_id != %s
            """,
            (factor, product_ids, new_uom.id),
        )

    def _update_product_prices(self, products, old_uom, new_uom):
        for product in products:
            if "standard_price" in product._fields:
                new_cost = self._convert_price(product.standard_price, old_uom, new_uom)
                product.with_context(disable_auto_svl=True).standard_price = new_cost
