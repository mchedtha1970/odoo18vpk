import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    budget_lines = env["budget.lines"].search([("request_line_id", "!=", False)])
    for budget_line in budget_lines:
        line = budget_line.request_line_id
        if not line or line.received_budget_amount:
            continue
        line.received_budget_amount = budget_line.planned_amount
    requests = env["departmental.budget.request"].search([])
    if requests:
        requests._compute_total_received_budget_amount()
        requests.flush_recordset(["total_received_budget_amount"])
    _logger.info(
        "Backfilled received budget amounts for %s budget lines",
        len(budget_lines),
    )
