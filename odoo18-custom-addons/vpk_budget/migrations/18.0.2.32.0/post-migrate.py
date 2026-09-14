import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    posts = env["account.budget.post"].search([])
    if not posts:
        return
    posts._compute_account_code()
    posts.flush_recordset(["account_code"])
    _logger.info("Recomputed account_code for %s budget posts", len(posts))
