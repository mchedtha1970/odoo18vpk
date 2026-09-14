# -*- coding: utf-8 -*-
from odoo import api, fields, models


class VpkBudgetAssetType(models.Model):
    _name = "vpk.budget.asset.type"
    _description = "ประเภทครุภัณฑ์"
    _order = "sequence, code, id"

    sequence = fields.Integer(default=10)
    code = fields.Char(string="รหัส", required=True)
    name = fields.Char(string="ชื่อ", required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "vpk_budget_asset_type_code_uniq",
            "unique(code)",
            "รหัสประเภทครุภัณฑ์ต้องไม่ซ้ำ",
        ),
    ]

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            if rec.code and rec.name:
                rec.display_name = f"{rec.code}: {rec.name}"
            else:
                rec.display_name = rec.name or rec.code or ""
