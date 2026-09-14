# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountFiscalYear(models.Model):
    """Community stub of Enterprise account.fiscal.year for account_reports."""

    _name = "account.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_from desc"

    name = fields.Char(string="Name", required=True)
    date_from = fields.Date(
        string="Start Date",
        required=True,
        help="Start Date, included in the fiscal year.",
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        help="Ending Date, included in the fiscal year.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.constrains("date_from", "date_to", "company_id")
    def _check_dates(self):
        for fy in self:
            if fy.date_to < fy.date_from:
                raise ValidationError(
                    _("The ending date must not be prior to the starting date.")
                )
            overlap = self.search(
                [
                    ("id", "!=", fy.id),
                    ("company_id", "=", fy.company_id.id),
                    ("date_from", "<=", fy.date_to),
                    ("date_to", ">=", fy.date_from),
                ],
                limit=1,
            )
            if overlap:
                raise ValidationError(
                    _(
                        "This fiscal year overlaps with %(name)s (%(date_from)s - %(date_to)s).",
                        name=overlap.name,
                        date_from=overlap.date_from,
                        date_to=overlap.date_to,
                    )
                )
