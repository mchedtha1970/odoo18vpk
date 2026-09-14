# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    account_code = fields.Char(
        string="บัญชี",
        compute="_compute_account_code",
        store=True,
    )

    @api.depends("account_ids", "account_ids.code", "account_ids.name")
    def _compute_account_code(self):
        for post in self:
            labels = []
            for account in post.account_ids:
                if not account.code and not account.name:
                    continue
                code = account.code or ""
                name = account.name or ""
                labels.append(f"[{code}] {name}" if code else name)
            post.account_code = ", ".join(labels)
