from odoo import fields, models


class BudgetLineAdjustmentLog(models.Model):
    _name = "budget.line.adjustment.log"
    _description = "Budget Line Adjustment Log"
    _order = "create_date desc, id desc"

    budget_line_id = fields.Many2one(
        comodel_name="budget.lines",
        required=True,
        ondelete="cascade",
    )
    budget_id = fields.Many2one(
        comodel_name="budget.budget",
        related="budget_line_id.budget_id",
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )
    old_amount = fields.Float(required=True, digits=0)
    new_amount = fields.Float(required=True, digits=0)
    delta_amount = fields.Float(compute="_compute_delta_amount", store=True, digits=0)
    reason = fields.Text(required=True)

    def _compute_delta_amount(self):
        for rec in self:
            rec.delta_amount = rec.new_amount - rec.old_amount
