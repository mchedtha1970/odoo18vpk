# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    egp_purchase_name = fields.Text(
        related="product_tmpl_id.egp_purchase_name",
        string="ชื่อสำหรับซื้อใน e-GP",
        readonly=False,
    )
