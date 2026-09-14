# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models
from odoo.tools import SQL


DRUG_LIST_TYPES = [
    ("ed", "ED (ยาในบัญชียาหลัก)"),
    ("non_ed", "Non-ED (ยานอกบัญชียาหลัก)"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    drug_list_type = fields.Selection(
        selection=DRUG_LIST_TYPES,
        string="ประเภทบัญชียา",
        index=True,
        tracking=True,
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    drug_list_type = fields.Selection(
        selection=DRUG_LIST_TYPES,
        string="ประเภทบัญชียา",
        related="product_tmpl_id.drug_list_type",
        store=True,
    )


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    drug_list_type = fields.Selection(
        selection=DRUG_LIST_TYPES,
        string="ประเภทบัญชียา",
        readonly=True,
    )

    def _select(self) -> SQL:
        return SQL(
            "%s, t.drug_list_type AS drug_list_type",
            super()._select(),
        )

    def _group_by(self) -> SQL:
        return SQL(
            "%s, t.drug_list_type",
            super()._group_by(),
        )
