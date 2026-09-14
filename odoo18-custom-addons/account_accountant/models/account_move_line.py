# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    deferred_start_date = fields.Date(
        string="Deferred Start Date",
        index=True,
        copy=False,
    )
    deferred_end_date = fields.Date(
        string="Deferred End Date",
        index=True,
        copy=False,
    )
