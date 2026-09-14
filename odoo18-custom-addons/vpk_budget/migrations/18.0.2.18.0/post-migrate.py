import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    form_types = env["vpk.budget.request.form.type"].with_context(active_test=False).search(
        []
    )
    for form_type in form_types:
        if (
            form_type.code
            and form_type.code.startswith("แบบฟอร์ม")
            and form_type.name != form_type.code
        ):
            form_type.name = form_type.code

    env["vpk.budget.request.form.type"]._sync_department_budget_request_menus()
    _logger.info("Aligned form type names with form codes and refreshed request menus")
