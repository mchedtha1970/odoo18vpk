from odoo import fields, models


class BudgetMaterialType(models.Model):
    _name = "budget.material.type"
    _description = "Budget Material Type"
    _order = "budget_post_id, sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="Budgetary Position",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="budget_post_id.company_id",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "budget_material_type_name_post_uniq",
            "unique(name, budget_post_id)",
            "Material type name must be unique per budgetary position.",
        )
    ]
