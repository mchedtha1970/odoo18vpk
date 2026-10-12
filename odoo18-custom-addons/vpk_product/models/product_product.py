# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    egp_purchase_name = fields.Text(
        related="product_tmpl_id.egp_purchase_name",
        string="ชื่อสำหรับซื้อใน e-GP",
        readonly=False,
    )
    generic_name = fields.Char(
        related="product_tmpl_id.generic_name", readonly=False, store=True,
    )
    trade_name = fields.Char(
        related="product_tmpl_id.trade_name", readonly=False, store=True,
    )
    manufacturer_name = fields.Char(
        related="product_tmpl_id.manufacturer_name", readonly=False,
    )
    distributor_name = fields.Char(
        related="product_tmpl_id.distributor_name", readonly=False,
    )
    packaging_type = fields.Char(
        related="product_tmpl_id.packaging_type", readonly=False,
    )
    pack_size = fields.Char(
        related="product_tmpl_id.pack_size", readonly=False,
    )
    storage_method = fields.Selection(
        related="product_tmpl_id.storage_method", readonly=False, store=True,
    )
    drug_category = fields.Char(
        related="product_tmpl_id.drug_category", readonly=False,
    )
    ned_group = fields.Selection(
        related="product_tmpl_id.ned_group", readonly=False, store=True,
    )
    pharmaco_group = fields.Char(
        related="product_tmpl_id.pharmaco_group", readonly=False,
    )
    generic_code = fields.Char(
        related="product_tmpl_id.generic_code", readonly=False, store=True,
    )
    tmt_tpu = fields.Char(
        related="product_tmpl_id.tmt_tpu", readonly=False, store=True,
    )
    tmt_fsn = fields.Char(related="product_tmpl_id.tmt_fsn", readonly=False)
    tmt_gpu = fields.Char(
        related="product_tmpl_id.tmt_gpu", readonly=False, store=True,
    )
    gmu_name = fields.Char(related="product_tmpl_id.gmu_name", readonly=False)
    manufacturer_market_code = fields.Char(
        related="product_tmpl_id.manufacturer_market_code", readonly=False,
    )
    vendor_product_code = fields.Char(
        related="product_tmpl_id.vendor_product_code", readonly=False, store=True,
    )
    drug_code_24 = fields.Char(
        related="product_tmpl_id.drug_code_24", readonly=False, store=True,
    )
