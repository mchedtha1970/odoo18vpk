# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.tools.float_utils import float_compare

from .his_stock_line import STOCK_ITEM_TYPES

LINE_STATES = [
    ("ok", "OK"),
    ("error", "Error"),
]


class HisRequisitionLine(models.Model):
    _name = "vpk.his.requisition.line"
    _description = "HIS Stock Requisition Line"
    _order = "id"

    batch_id = fields.Many2one(
        "vpk.his.batch", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    line_external_id = fields.Char(index=True)
    product_code = fields.Char(required=True)
    product_id = fields.Many2one("product.product", ondelete="set null")
    item_type = fields.Selection(STOCK_ITEM_TYPES)
    uom = fields.Char(string="HIS UoM")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    qty = fields.Float(required=True, digits="Product Unit of Measure")
    lot_name = fields.Char()
    lot_id = fields.Many2one("stock.lot", ondelete="set null")
    picking_id = fields.Many2one("stock.picking", ondelete="set null")
    location_id = fields.Many2one(
        related="batch_id.source_location_id",
        string="Source Location",
    )
    line_state = fields.Selection(LINE_STATES, default="ok")
    error_message = fields.Text()

    def _normalize_product_code(self, code):
        code = (code or "").strip()
        if code.isdigit():
            return code.zfill(5)
        return code

    def _validate_line(self):
        self.ensure_one()
        errors = []
        batch = self.batch_id
        Product = self.env["product.product"].sudo()
        Lot = self.env["stock.lot"].sudo()
        Uom = self.env["uom.uom"].sudo()

        if not batch.source_warehouse_id:
            errors.append(_("Batch source warehouse is missing"))
        if not batch.dest_warehouse_id:
            errors.append(_("Batch destination warehouse is missing"))
        if (
            batch.source_warehouse_id
            and batch.dest_warehouse_id
            and batch.source_warehouse_id == batch.dest_warehouse_id
            and batch.source_location_id == batch.dest_location_id
        ):
            errors.append(_("Source and destination must differ"))

        code = self._normalize_product_code(self.product_code)
        product = Product.search([("default_code", "=", code)], limit=1)
        if not product and code != self.product_code:
            product = Product.search(
                [("default_code", "=", self.product_code.strip())], limit=1
            )
        self.product_id = product.id if product else False
        if not product:
            errors.append(_("Unknown product code %s") % self.product_code)
        elif not product.is_storable:
            errors.append(_("Product %s is not storable") % self.product_code)

        uom = self.env["uom.uom"]
        if product:
            if self.uom:
                uom = Uom.search([("name", "=", self.uom.strip())], limit=1)
                if not uom:
                    uom = Uom.search([("name", "ilike", self.uom.strip())], limit=1)
                if not uom:
                    errors.append(_("Unknown UoM %s") % self.uom)
                elif uom.category_id != product.uom_id.category_id:
                    errors.append(
                        _("UoM %s is not compatible with product %s")
                        % (self.uom, self.product_code)
                    )
            else:
                uom = product.uom_id
        self.uom_id = uom.id if uom else False

        if float_compare(self.qty, 0.0, precision_digits=4) <= 0:
            errors.append(_("qty must be greater than zero"))

        lot = self.env["stock.lot"]
        if self.lot_name and product:
            lot = Lot.search(
                [
                    ("name", "=", self.lot_name.strip()),
                    ("product_id", "=", product.id),
                    ("company_id", "in", [False, self.company_id.id]),
                ],
                limit=1,
            )
            if not lot:
                errors.append(
                    _("Unknown lot %s for product %s")
                    % (self.lot_name, self.product_code)
                )
        self.lot_id = lot.id if lot else False

        self.line_state = "error" if errors else "ok"
        self.error_message = "\n".join(errors) if errors else False
        return not errors
