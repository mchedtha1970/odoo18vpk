from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    material_sub_type_id = fields.Many2one(
        comodel_name="vpk.budget.material.sub.type",
        string="ประเภทงบประมาณ",
        index=True,
    )
