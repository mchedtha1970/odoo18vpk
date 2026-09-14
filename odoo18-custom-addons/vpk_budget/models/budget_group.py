from odoo import fields, models


class VpkBudgetGroup(models.Model):
    _name = "vpk.budget.group"
    _description = "Budget Group"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    material_sub_type_ids = fields.One2many(
        comodel_name="vpk.budget.material.sub.type",
        inverse_name="budget_group_id",
        string="ประเภทวัสดุย่อย",
    )

    _sql_constraints = [
        (
            "vpk_budget_group_code_uniq",
            "unique(code)",
            "Budget group code must be unique.",
        ),
    ]
