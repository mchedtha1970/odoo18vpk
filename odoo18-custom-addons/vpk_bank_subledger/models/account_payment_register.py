# -*- coding: utf-8 -*-
from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if payment_vals.get("vpk_bank_subledger_id"):
            return payment_vals
        Payment = self.env["account.payment"]
        if "vpk_bank_subledger_id" not in Payment._fields:
            return payment_vals
        journal = self.env["account.journal"].browse(payment_vals.get("journal_id")) or self.journal_id
        bank = getattr(self, "company_bank_id", False) or journal.bank_account_id
        subledger = Payment._vpk_find_bank_subledger(
            self.company_id, journal=journal, bank=bank
        )
        if subledger:
            payment_vals["vpk_bank_subledger_id"] = subledger.id
            payment_vals["vpk_bank_gl_account_id"] = subledger.account_id.id
        return payment_vals
