# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _tier_validation_check_state_on_write(self, vals):
        """Allow auto-post for depreciation / skip_validation_check flows.

        base_tier_validation blocks state→posted when need_validation is set,
        but does not honour skip_validation_check in this method. Asset compute
        posts journal entries with allow_asset + skip_validation_check from
        account_move_tier_validation.action_post — honour those contexts here.
        Also skip for pure journal entries (move_type=entry) so depreciation
        never requires invoice-style approval.
        """
        if self.env.context.get("skip_validation_check") or self.env.context.get(
            "allow_asset"
        ):
            return
        # Posting asset depreciation (and similar auto entries)
        if vals.get(self._state_field) in self._state_to and all(
            move.move_type == "entry" for move in self
        ):
            return
        return super()._tier_validation_check_state_on_write(vals)
