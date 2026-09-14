from odoo import fields, models


class VpkBudgetFundSource(models.Model):
    _name = "vpk.budget.fund.source"
    _description = "Budget Fund Source"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [
        (
            "vpk_budget_fund_source_code_uniq",
            "unique(code)",
            "Fund source code must be unique.",
        ),
    ]
