# -*- coding: utf-8 -*-


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = env["purchase.request"].search([("budget_check_message", "!=", False)])
    for request in requests:
        rows = request._rows_from_budget_check_message(request.budget_check_message)
        request._replace_budget_check_lines(rows)
