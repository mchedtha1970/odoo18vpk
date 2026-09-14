# -*- coding: utf-8 -*-


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["vpk.budget.asset.category"].action_sync_from_product_categories()
