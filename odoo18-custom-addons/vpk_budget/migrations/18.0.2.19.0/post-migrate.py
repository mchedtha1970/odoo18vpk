import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    old_menu = env.ref(
        "vpk_budget.menu_departmental_budget_summary_wizard",
        raise_if_not_found=False,
    )
    if old_menu:
        old_menu.unlink()
    env["vpk.budget.request.form.type"]._sync_department_budget_request_menus()
    _logger.info("Synced departmental budget summary wizard menus per form type")
