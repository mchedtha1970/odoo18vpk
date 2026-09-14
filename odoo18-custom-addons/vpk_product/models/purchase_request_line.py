# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    egp_purchase_name = fields.Text(
        string="ชื่อสำหรับซื้อใน e-GP",
        copy=True,
        help="ดึงจากสินค้าเมื่อเลือกในรายการ สามารถแก้ไขได้ต่อรายการ",
    )

    def _sync_egp_purchase_name_from_product(self):
        for line in self:
            product = line.product_id
            line.egp_purchase_name = product.egp_purchase_name or False if product else False

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super().onchange_product_id()
        self._sync_egp_purchase_name_from_product()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        Product = self.env["product.product"]
        for vals in vals_list:
            if vals.get("product_id") and not vals.get("egp_purchase_name"):
                product = Product.browse(vals["product_id"])
                vals["egp_purchase_name"] = product.egp_purchase_name or False
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("product_id") and "egp_purchase_name" not in vals:
            product = self.env["product.product"].browse(vals["product_id"])
            vals = dict(vals, egp_purchase_name=product.egp_purchase_name or False)
        return super().write(vals)
