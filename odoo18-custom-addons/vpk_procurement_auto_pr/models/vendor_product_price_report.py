# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    vendor_reference = fields.Char(
        string="รหัสผู้จำหน่าย",
        related="partner_id.ref",
        store=True,
        index=True,
    )
    internal_product_code = fields.Char(
        string="รหัสสินค้าภายใน",
        compute="_compute_vendor_price_report_fields",
        store=True,
        index=True,
    )
    report_product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า",
        compute="_compute_vendor_price_report_fields",
        store=True,
    )
    report_category_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดสินค้า",
        related="product_tmpl_id.categ_id",
        store=True,
        index=True,
    )
    report_unit_price = fields.Float(
        string="ราคาสินค้าผู้จำหน่าย",
        related="price",
        store=True,
        aggregator="avg",
    )

    @api.depends(
        "product_id",
        "product_id.default_code",
        "product_tmpl_id",
        "product_tmpl_id.default_code",
        "product_tmpl_id.product_variant_id",
    )
    def _compute_vendor_price_report_fields(self):
        for supplier_info in self:
            product = (
                supplier_info.product_id
                or supplier_info.product_tmpl_id.product_variant_id
            )
            supplier_info.report_product_id = product
            supplier_info.internal_product_code = (
                product.default_code
                or supplier_info.product_tmpl_id.default_code
                or ""
            )
