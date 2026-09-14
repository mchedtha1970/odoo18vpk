# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models
from odoo.tools import SQL

from .medical_item_classification import HOSPITAL_ITEM_TYPES


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    hospital_item_type = fields.Selection(
        selection=HOSPITAL_ITEM_TYPES,
        string="ประเภทสินค้า/พัสดุ",
        readonly=True,
    )

    def _select(self) -> SQL:
        return SQL(
            "%s, t.hospital_item_type AS hospital_item_type",
            super()._select(),
        )

    def _group_by(self) -> SQL:
        return SQL(
            "%s, t.hospital_item_type",
            super()._group_by(),
        )
