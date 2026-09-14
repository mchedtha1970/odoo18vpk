# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import date_utils

# Used by account_reports deferred handlers
DEFERRED_DATE_MIN = fields.Date.to_date("1900-01-01")
DEFERRED_DATE_MAX = fields.Date.to_date("9999-12-31")


class AccountMove(models.Model):
    _inherit = "account.move"

    deferred_original_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move_deferred_rel",
        column1="deferred_move_id",
        column2="original_move_id",
        string="Original moves (deferred)",
        copy=False,
    )
    deferred_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move_deferred_rel",
        column1="original_move_id",
        column2="deferred_move_id",
        string="Deferred moves",
        copy=False,
    )

    @api.model
    def _get_deferred_amounts_by_line(self, lines, periods, is_reverse=False):
        """Prorate line balances into period buckets for deferred reports.

        ``lines`` is an iterable of dicts (from deferred report SQL) containing at least:
        balance, deferred_start_date, deferred_end_date, and grouping keys.
        ``periods`` is a list of (date_from, date_to, label) tuples.
        """
        results = []
        for line in lines:
            start = fields.Date.to_date(line.get("deferred_start_date"))
            end = fields.Date.to_date(line.get("deferred_end_date"))
            if not start or not end or end < start:
                continue
            total_days = (end - start).days + 1
            if total_days <= 0:
                continue
            balance = line.get("balance") or 0.0
            if is_reverse:
                balance = -balance
            for period in periods:
                if len(period) >= 2:
                    p_from, p_to = period[0], period[1]
                else:
                    continue
                overlap_start = max(start, p_from)
                overlap_end = min(end, p_to)
                if overlap_end < overlap_start:
                    period_amount = 0.0
                else:
                    overlap_days = (overlap_end - overlap_start).days + 1
                    period_amount = balance * overlap_days / total_days
                row = dict(line)
                row["period"] = period
                row["amount"] = period_amount
                results.append(row)
        return results
