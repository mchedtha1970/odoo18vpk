from odoo import fields, models


class BudgetComparisonReportWizard(models.TransientModel):
    _name = "budget.comparison.report.wizard"
    _description = "Budget Comparison Report Wizard"

    budget_id = fields.Many2one(
        comodel_name="budget.budget",
        required=True,
    )
    fund_source_id = fields.Many2one(
        comodel_name="budget.fund.source",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Department / Analytic Account",
    )

    def action_print_report(self):
        self.ensure_one()
        data = {
            "wizard_id": self.id,
            "budget_id": self.budget_id.id,
            "fund_source_id": self.fund_source_id.id or False,
            "analytic_account_id": self.analytic_account_id.id or False,
        }
        return self.env.ref(
            "hospital_budget_customization.action_report_budget_comparison"
        ).report_action(self.budget_id, data=data)
