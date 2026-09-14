import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = env["departmental.budget.request"].search([])
    if not requests:
        return
    requests._compute_total_received_budget_amount()
    requests.flush_recordset(["total_received_budget_amount"])
    _logger.info(
        "Recomputed total_received_budget_amount from allocated_budget_amount for %s requests",
        len(requests),
    )
