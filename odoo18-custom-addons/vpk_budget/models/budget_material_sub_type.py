from odoo import api, fields, models


class VpkBudgetMaterialSubType(models.Model):
    _name = "vpk.budget.material.sub.type"
    _description = "Budget Material Sub Type"
    _order = "budget_group_id, sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="ชื่อประเภทวัสดุย่อย", required=True)
    code = fields.Char(required=True)
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        string="กลุ่มงบประมาณ",
        required=True,
        ondelete="restrict",
    )
    active = fields.Boolean(default=True)
    description = fields.Text(string="รายละเอียด")

    _sql_constraints = [
        (
            "vpk_budget_material_sub_type_code_group_uniq",
            "unique(budget_group_id, code)",
            "Material sub type code must be unique within the same budget group.",
        ),
    ]

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = list(args or [])
        budget_group_id = self.env.context.get("material_sub_type_budget_group_id")
        if budget_group_id:
            args.append(("budget_group_id", "=", budget_group_id))
        return super().name_search(name, args, operator, limit)
