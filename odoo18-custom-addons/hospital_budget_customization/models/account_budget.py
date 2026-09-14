from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Budget(models.Model):
    _inherit = "budget.budget"

    approval_stage = fields.Selection(
        selection=[
            ("department", "Department Submitted"),
            ("budget_office", "Budget Office Review"),
            ("management", "Executive Review"),
            ("pending_provincial", "Pending Provincial Health Office"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="department",
        tracking=True,
    )
    approved_amount_total = fields.Float(
        compute="_compute_budget_totals",
        string="Approved Amount",
        digits=0,
    )
    actual_amount_total = fields.Float(
        compute="_compute_budget_totals",
        string="Actual Amount",
        digits=0,
    )
    encumbrance_amount_total = fields.Float(
        compute="_compute_budget_totals",
        string="Encumbrance Amount",
        digits=0,
    )
    available_amount_total = fields.Float(
        compute="_compute_budget_totals",
        string="Available Amount",
        digits=0,
    )

    def action_move_to_budget_office(self):
        self.write({"approval_stage": "budget_office"})

    def action_move_to_management(self):
        self.write({"approval_stage": "management"})

    def action_mark_pending_provincial(self):
        self.write({"approval_stage": "pending_provincial"})

    def action_mark_budget_approved(self):
        self.write({"approval_stage": "approved"})

    def action_mark_budget_rejected(self):
        self.write({"approval_stage": "rejected"})

    def _compute_budget_totals(self):
        for budget in self:
            snapshot = budget._get_budget_control_snapshot()
            budget.approved_amount_total = snapshot["approved"]
            budget.actual_amount_total = snapshot["actual"]
            budget.encumbrance_amount_total = snapshot["encumbrance"]
            budget.available_amount_total = snapshot["available"]

    def _get_budget_control_snapshot(
        self,
        exclude_request_id=False,
        exclude_order_id=False,
        exclude_request_ids=None,
    ):
        self.ensure_one()
        exclude_request_ids = set(exclude_request_ids or [])
        if exclude_request_id:
            exclude_request_ids.add(exclude_request_id)

        approved = sum(self.budget_line.mapped("planned_amount"))
        # Expenses are normally negative on practical_amount in this budget model.
        actual = sum(abs(v) for v in self.budget_line.mapped("practical_amount") if v < 0.0)
        encumbrance = self._get_open_pr_encumbrance(exclude_request_ids=exclude_request_ids)
        encumbrance += self._get_open_po_encumbrance(exclude_order_id=exclude_order_id)
        return {
            "approved": approved,
            "actual": actual,
            "encumbrance": encumbrance,
            "available": approved - actual - encumbrance,
        }

    def _get_open_pr_encumbrance(self, exclude_request_ids=None):
        self.ensure_one()
        exclude_request_ids = exclude_request_ids or set()
        requests = self.env["purchase.request"].search(
            [
                ("budget_id", "=", self.id),
                ("state", "in", ("to_approve", "approved")),
            ]
        )
        requests = requests.filtered(lambda r: r.id not in exclude_request_ids)
        total = 0.0
        for req in requests:
            amount = req.currency_id._convert(
                req.estimated_cost,
                req.company_id.currency_id,
                req.company_id,
                req.date_start or fields.Date.context_today(req),
            )
            total += amount
        return total

    def _get_open_po_encumbrance(self, exclude_order_id=False):
        self.ensure_one()
        orders = self.env["purchase.order"].search(
            [
                ("budget_id", "=", self.id),
                ("state", "in", ("to approve", "purchase")),
            ]
        )
        if exclude_order_id:
            orders = orders.filtered(lambda o: o.id != exclude_order_id)
        total = 0.0
        for order in orders:
            order_open = 0.0
            for line in order.order_line.filtered(lambda l: not l.display_type):
                if line.product_qty <= 0:
                    continue
                open_ratio = max((line.product_qty - line.qty_received) / line.product_qty, 0.0)
                order_open += line.price_subtotal * open_ratio
            converted = order.currency_id._convert(
                order_open,
                order.company_id.currency_id,
                order.company_id,
                order.date_order or fields.Date.context_today(order),
            )
            total += converted
        return total


class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    material_type_ids = fields.One2many(
        comodel_name="budget.material.type",
        inverse_name="budget_post_id",
        string="Material Types",
    )


class BudgetLines(models.Model):
    _inherit = "budget.lines"

    fund_source_id = fields.Many2one(
        comodel_name="budget.fund.source",
        string="Fund Source",
        tracking=True,
    )
    requested_amount = fields.Float(
        string="Requested Amount",
        digits=0,
        help="Original amount requested by the department before any adjustment.",
    )
    historical_amount_y1 = fields.Float(
        compute="_compute_historical_amounts",
        string="Actual Y-1",
        digits=0,
        help="Actual expenses for the same period one year back.",
    )
    historical_amount_y2 = fields.Float(
        compute="_compute_historical_amounts",
        string="Actual Y-2",
        digits=0,
        help="Actual expenses for the same period two years back.",
    )
    historical_amount_y3 = fields.Float(
        compute="_compute_historical_amounts",
        string="Actual Y-3",
        digits=0,
        help="Actual expenses for the same period three years back.",
    )
    adjustment_log_ids = fields.One2many(
        comodel_name="budget.line.adjustment.log",
        inverse_name="budget_line_id",
        string="Adjustment Logs",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "requested_amount" not in vals and "planned_amount" in vals:
                vals["requested_amount"] = vals["planned_amount"]
        return super().create(vals_list)

    def write(self, vals):
        should_track_adjustment = "planned_amount" in vals and not self.env.context.get(
            "skip_budget_adjustment_tracking"
        )
        if should_track_adjustment:
            review_stages = {
                "budget_office",
                "management",
                "pending_provincial",
                "approved",
            }
            needs_reason = any(line.budget_id.approval_stage in review_stages for line in self)
            reason = self.env.context.get("budget_adjustment_reason")
            if needs_reason and not reason:
                raise ValidationError(
                    _(
                        "Please provide an adjustment reason before changing Planned Amount. "
                        "Use the 'Adjust Budget Amount' action."
                    )
                )
            original_amounts = {line.id: line.planned_amount for line in self}
            res = super().write(vals)
            logs = []
            for line in self:
                old_amount = original_amounts.get(line.id, 0.0)
                new_amount = line.planned_amount
                if old_amount == new_amount:
                    continue
                if not needs_reason:
                    continue
                logs.append(
                    {
                        "budget_line_id": line.id,
                        "old_amount": old_amount,
                        "new_amount": new_amount,
                        "reason": reason,
                    }
                )
            if logs:
                self.env["budget.line.adjustment.log"].create(logs)
            return res
        return super().write(vals)

    def _compute_historical_amounts(self):
        aal_model = self.env["account.analytic.line"]
        for line in self:
            line.historical_amount_y1 = 0.0
            line.historical_amount_y2 = 0.0
            line.historical_amount_y3 = 0.0
            if not line.analytic_account_id or not line.general_budget_id.account_ids:
                continue
            line.historical_amount_y1 = line._get_historical_amount_by_year_offset(
                aal_model, year_offset=1
            )
            line.historical_amount_y2 = line._get_historical_amount_by_year_offset(
                aal_model, year_offset=2
            )
            line.historical_amount_y3 = line._get_historical_amount_by_year_offset(
                aal_model, year_offset=3
            )

    def _get_historical_amount_by_year_offset(self, aal_model, year_offset):
        self.ensure_one()
        date_from = self.date_from
        date_to = self.date_to
        if not date_from or not date_to:
            return 0.0
        from_prev = date_from - relativedelta(years=year_offset)
        to_prev = date_to - relativedelta(years=year_offset)
        domain = [
            ("account_id", "=", self.analytic_account_id.id),
            ("general_account_id", "in", self.general_budget_id.account_ids.ids),
            ("date", ">=", from_prev),
            ("date", "<=", to_prev),
        ]
        if self.company_id:
            domain.append(("company_id", "=", self.company_id.id))
        # Avoid read_group key differences across versions/custom overrides.
        lines = aal_model.search(domain)
        return sum(lines.mapped("amount"))

    def action_open_adjustment_wizard(self):
        self.ensure_one()
        return {
            "name": _("Adjust Budget Amount"),
            "type": "ir.actions.act_window",
            "res_model": "budget.line.adjustment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_budget_line_id": self.id,
                "default_new_planned_amount": self.planned_amount,
            },
        }
