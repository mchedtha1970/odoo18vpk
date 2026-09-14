import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vpk_budget_request_form_type'
        )
        """
    )
    if not cr.fetchone()[0]:
        return

    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    env["vpk.budget.request.form.type"]._sync_department_budget_request_menus()
    _logger.info("Synced departmental budget request menus per form type")
