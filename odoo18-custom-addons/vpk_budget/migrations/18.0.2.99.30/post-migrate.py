# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Give budget-linked vendor bill lines the budget department's analytic."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env["account.move.line"].search(
        [
            ("move_id.move_type", "in", ("in_invoice", "in_refund")),
            ("move_id.state", "!=", "cancel"),
            ("display_type", "=", "product"),
            ("analytic_distribution", "=", False),
            "|",
            ("budget_line_id", "!=", False),
            ("purchase_line_id.budget_line_id", "!=", False),
        ]
    )
    lines._vpk_apply_budget_analytic()
