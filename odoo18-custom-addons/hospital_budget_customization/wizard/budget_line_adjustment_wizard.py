from odoo import _, fields, models
from odoo.exceptions import ValidationError


class BudgetLineAdjustmentWizard(models.TransientModel):
    _name = "budget.line.adjustment.wizard"
    _description = "Budget Line Adjustment Wizard"

    budget_line_id = fields.Many2one(
        comodel_name="budget.lines",
        required=True,
        readonly=True,
    )
    current_planned_amount = fields.Float(
        related="budget_line_id.planned_amount",
        readonly=True,
        digits=0,
    )
    new_planned_amount = fields.Float(required=True, digits=0)
    reason = fields.Text(required=True)

    def action_apply_adjustment(self):
        self.ensure_one()
        if self.new_planned_amount == self.current_planned_amount:
            raise ValidationError(_("New planned amount must be different from current value."))
        self.budget_line_id.with_context(
            budget_adjustment_reason=self.reason
        ).write({"planned_amount": self.new_planned_amount})
        return {"type": "ir.actions.act_window_close"}
