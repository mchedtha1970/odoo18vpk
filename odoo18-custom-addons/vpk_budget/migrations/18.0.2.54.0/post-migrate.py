import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env["departmental.budget.request.line"].search(
        [("section_key", "=", "asset")]
    )
    if not lines:
        return
    lines._compute_allocated_budget_amount()
    lines.flush_recordset(["allocated_budget_amount"])
    requests = lines.mapped("request_id")
    requests._compute_total_received_budget_amount()
    requests.flush_recordset(["total_received_budget_amount"])
    _logger.info(
        "Synced allocated_budget_amount for %s asset lines / %s requests",
        len(lines),
        len(requests),
    )
