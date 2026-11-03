# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """วัสดุทั่วไป - อื่นๆ เลือกรายการจากหมวดสินค้า Expenses"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    expense_categ = env.ref("product.cat_expense", raise_if_not_found=False)
    if not expense_categ:
        return
    env["vpk.budget.material.sub.type"].with_context(active_test=False).search(
        [
            ("name", "=", "อื่นๆ"),
            ("budget_group_id.code", "=", "GENERAL_SUPPLY"),
            ("product_categ_id", "=", False),
        ]
    ).write({"product_categ_id": expense_categ.id})
