# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    generate_deferred_expense_entries_method = fields.Selection(
        selection=[
            ("manual", "Manually & Based on report"),
            ("on_validation", "On bill validation"),
        ],
        string="Generate Deferred Expense Entries",
        default="manual",
        required=True,
    )
    generate_deferred_revenue_entries_method = fields.Selection(
        selection=[
            ("manual", "Manually & Based on report"),
            ("on_validation", "On invoice validation"),
        ],
        string="Generate Deferred Revenue Entries",
        default="manual",
        required=True,
    )
    deferred_expense_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Deferred Expense Journal",
        domain="[('type', '=', 'general')]",
        check_company=True,
    )
    deferred_revenue_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Deferred Revenue Journal",
        domain="[('type', '=', 'general')]",
        check_company=True,
    )
    deferred_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Deferred Expense Account",
        check_company=True,
    )
    deferred_revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Deferred Revenue Account",
        check_company=True,
    )
