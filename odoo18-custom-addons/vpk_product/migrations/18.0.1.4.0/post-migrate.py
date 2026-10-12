# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    product = env["product.template"]
    if "cold_chain" not in product._fields or "storage_method" not in product._fields:
        return
    cold_products = product.search(
        [("cold_chain", "=", True), ("storage_method", "=", False)]
    )
    if cold_products:
        cold_products.write({"storage_method": "cold"})
