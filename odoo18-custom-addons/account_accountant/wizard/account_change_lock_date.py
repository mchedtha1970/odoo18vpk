# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import date_utils


class AccountChangeLockDate(models.TransientModel):
    """Minimal lock-date wizard expected by account_reports."""

    _name = "account.change.lock.date"
    _description = "Change Lock Date"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    fiscalyear_lock_date = fields.Date(
        string="Lock Date for All Users",
        related="company_id.fiscalyear_lock_date",
        readonly=False,
    )
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        related="company_id.tax_lock_date",
        readonly=False,
    )
    hard_lock_date = fields.Date(
        string="Hard Lock Date",
        related="company_id.hard_lock_date",
        readonly=False,
    )

    def _get_current_period_dates(self, lock_date_field):
        """Return (date_from, date_to) for the period ending at the given lock date."""
        self.ensure_one()
        company = self.company_id or self.env.company
        lock_date = getattr(company, lock_date_field, False) or fields.Date.context_today(self)
        # Default: calendar month containing the lock date
        date_from = date_utils.start_of(lock_date, "month")
        date_to = lock_date
        return date_from, date_to

    def _create_default_report_external_values(self, lock_date_field):
        """Hook overridden by account_reports when installed."""
        return True

    def action_change_lock_date(self):
        self.ensure_one()
        for field_name in ("fiscalyear_lock_date", "tax_lock_date", "hard_lock_date"):
            if field_name in self.env["res.company"]._fields and self[field_name]:
                self._create_default_report_external_values(field_name)
        return {"type": "ir.actions.act_window_close"}
