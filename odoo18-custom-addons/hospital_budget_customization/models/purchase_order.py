from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    budget_id = fields.Many2one(
        comodel_name="budget.budget",
        string="Budget Number",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    fund_source_id = fields.Many2one(
        comodel_name="budget.fund.source",
        string="Fund Source",
        tracking=True,
    )

    @api.onchange("order_line")
    def _onchange_order_line_sync_budget(self):
        for order in self:
            order._sync_budget_from_request_lines()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_budget_from_request_lines()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if "order_line" in vals and "budget_id" not in vals:
            self._sync_budget_from_request_lines()
        return res

    def _sync_budget_from_request_lines(self):
        for order in self:
            request_lines = order.order_line.mapped("purchase_request_lines")
            budgets = request_lines.mapped("request_id.budget_id")
            fund_sources = request_lines.mapped("request_id.fund_source_id")
            if len(budgets) == 1:
                order.budget_id = budgets.id
            if len(fund_sources) == 1:
                order.fund_source_id = fund_sources.id

    def button_confirm(self):
        self._check_budget_before_confirm()
        return super().button_confirm()

    def _check_budget_before_confirm(self):
        for order in self:
            if not order.budget_id:
                continue
            linked_requests = (
                order.order_line.mapped("purchase_request_lines").mapped("request_id")
            )
            snapshot = order.budget_id._get_budget_control_snapshot(
                exclude_order_id=order.id,
                exclude_request_ids=linked_requests.ids,
            )
            required_amount = order.currency_id._convert(
                order.amount_untaxed,
                order.company_id.currency_id,
                order.company_id,
                order.date_order or fields.Date.context_today(order),
            )
            if snapshot["available"] < required_amount:
                raise ValidationError(
                    _(
                        "Budget is insufficient for purchase order %(name)s.\n"
                        "Available: %(available).2f\n"
                        "PO Amount: %(required).2f\n"
                        "Please perform budget transfer/adjustment before confirmation."
                    )
                    % {
                        "name": order.name,
                        "available": snapshot["available"],
                        "required": required_amount,
                    }
                )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    fund_source_id = fields.Many2one(
        comodel_name="budget.fund.source",
        related="order_id.fund_source_id",
        store=True,
        readonly=True,
    )
