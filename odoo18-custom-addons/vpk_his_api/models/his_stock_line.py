# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.tools.float_utils import float_compare

LINE_STATES = [
    ("ok", "OK"),
    ("error", "Error"),
]

STOCK_REASONS = [
    ("patient_use", "Patient Use"),
    ("ward_use", "Ward Use"),
    ("expired", "Expired"),
    ("adjust", "Adjustment"),
]

STOCK_ITEM_TYPES = [
    ("drug", "ยา"),
    ("medical_supply", "เวชภัณฑ์ไม่ใช่ยา"),
    ("other", "อื่นๆ"),
]

ITEM_TYPE_ALIASES = {
    "drug": "drug",
    "medicine": "drug",
    "ยา": "drug",
    "เวชภัณฑ์ยา": "drug",
    "medical_supply": "medical_supply",
    "supply": "medical_supply",
    "nondrug": "medical_supply",
    "non_drug": "medical_supply",
    "เวชภัณฑ์": "medical_supply",
    "เวชภัณฑ์ไม่ใช่ยา": "medical_supply",
    "other": "other",
}


class HisStockLine(models.Model):
    _name = "vpk.his.stock.line"
    _description = "HIS Stock Issue Line"
    _order = "id"

    batch_id = fields.Many2one(
        "vpk.his.batch", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    line_external_id = fields.Char(index=True)
    product_code = fields.Char(required=True)
    product_id = fields.Many2one("product.product", ondelete="set null")
    item_type = fields.Selection(STOCK_ITEM_TYPES)
    warehouse_code = fields.Char()
    warehouse_id = fields.Many2one("stock.warehouse", ondelete="set null")
    location_code = fields.Char()
    location_id = fields.Many2one("stock.location", ondelete="set null")
    department_code = fields.Char()
    unit_map_id = fields.Many2one("vpk.his.unit.map", ondelete="set null")
    uom = fields.Char(string="HIS UoM")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    qty = fields.Float(required=True, digits="Product Unit of Measure")
    lot_name = fields.Char()
    lot_id = fields.Many2one("stock.lot", ondelete="set null")
    hn = fields.Char(
        string="HN",
        index=True,
        help="รหัสโรงพยาบาลของคนไข้จาก HIS",
    )
    vn = fields.Char(
        string="VN",
        index=True,
        help="รหัสการมารับบริการจาก HIS",
    )
    reason = fields.Selection(STOCK_REASONS, default="patient_use", required=True)
    picking_id = fields.Many2one("stock.picking", ondelete="set null")
    scrap_id = fields.Many2one("stock.scrap", ondelete="set null")
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
        Product = self.env["product.product"].sudo()
        Warehouse = self.env["stock.warehouse"].sudo()
        Location = self.env["stock.location"].sudo()
        Lot = self.env["stock.lot"].sudo()
        Uom = self.env["uom.uom"].sudo()
        UnitMap = self.env["vpk.his.unit.map"]

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

        warehouse = self.env["stock.warehouse"]
        location = self.env["stock.location"]
        unit_map = self.env["vpk.his.unit.map"]

        if self.department_code:
            unit_map = UnitMap.find_map(self.department_code, company=self.company_id)
            self.unit_map_id = unit_map.id if unit_map else False
            if unit_map:
                warehouse = unit_map.warehouse_id
                location = unit_map.location_id or unit_map.warehouse_id.lot_stock_id
            elif not self.warehouse_code:
                errors.append(
                    _("No unit mapping for department %s") % self.department_code
                )

        if self.warehouse_code:
            warehouse = Warehouse.search(
                [
                    ("code", "=", self.warehouse_code.strip()),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if not warehouse:
                errors.append(_("Unknown warehouse code %s") % self.warehouse_code)
            elif not location:
                location = warehouse.lot_stock_id

        if not warehouse and not errors:
            errors.append(_("warehouse_code or mapped department_code is required"))

        if self.location_code and warehouse:
            loc = Location.search(
                [
                    ("barcode", "=", self.location_code.strip()),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if not loc:
                loc = Location.search(
                    [
                        ("name", "=", self.location_code.strip()),
                        ("id", "child_of", warehouse.lot_stock_id.id),
                    ],
                    limit=1,
                )
            if not loc:
                errors.append(_("Unknown location code %s") % self.location_code)
            else:
                location = loc

        self.warehouse_id = warehouse.id if warehouse else False
        self.location_id = location.id if location else False

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

        if self.reason == "patient_use":
            if not (self.hn or "").strip():
                errors.append(_("hn is required for patient dispensing"))
            if not (self.vn or "").strip():
                errors.append(_("vn is required for patient dispensing"))

        lot = self.env["stock.lot"]
        if product and product.tracking != "none" and not self.lot_name:
            errors.append(
                _("Product %s is lot-tracked; send lot_name or lots[]")
                % self.product_code
            )
        if product and product.tracking == "serial" and self.lot_name:
            if float_compare(self.qty, 1.0, precision_digits=4) != 0:
                errors.append(
                    _("Serial-tracked product %s requires qty 1 per serial")
                    % self.product_code
                )
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
