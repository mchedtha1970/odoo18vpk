from odoo import api, models


class ReportBudgetComparison(models.AbstractModel):
    _name = "report.hospital_budget_customization.report_budget_comparison"
    _description = "Budget Comparison Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        budget = self.env["budget.budget"].browse(data.get("budget_id"))
        domain = [("budget_id", "=", budget.id)]
        if data.get("fund_source_id"):
            domain.append(("fund_source_id", "=", data["fund_source_id"]))
        if data.get("analytic_account_id"):
            domain.append(("analytic_account_id", "=", data["analytic_account_id"]))
        lines = self.env["budget.lines"].search(domain, order="analytic_account_id, id")
        return {
            "doc_ids": budget.ids,
            "doc_model": "budget.budget",
            "docs": budget,
            "lines": lines,
            "filters": {
                "fund_source": self.env["budget.fund.source"].browse(data.get("fund_source_id")),
                "analytic_account": self.env["account.analytic.account"].browse(
                    data.get("analytic_account_id")
                ),
            },
        }
