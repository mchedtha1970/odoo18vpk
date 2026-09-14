from odoo import fields, models


class BudgetFundSource(models.Model):
    _name = "budget.fund.source"
    _description = "Budget Fund Source"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag",
        string="Analytic Tags",
        help="Optional tags used to align this fund source with analytic dimensions.",
    )

    _sql_constraints = [
        ("budget_fund_source_code_uniq", "unique(code)", "Fund source code must be unique."),
    ]
