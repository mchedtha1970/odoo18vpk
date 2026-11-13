# -*- coding: utf-8 -*-
from odoo import models

# ฟิลด์ที่ Odoo อาจเขียนบนบิลอื่นในลำดับเดียวกันตอน reset เป็นร่าง
_SEQUENCE_GAP_EXCEPTIONS = ["made_sequence_gap"]


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_after_validation_exceptions(self):
        """อนุญาตอัปเดต made_sequence_gap หลังอนุมัติแล้ว.

        ตอน button_draft ของบิลหนึ่ง Odoo จะเขียน made_sequence_gap ให้บิลถัดไป
        ในลำดับเดียวกัน ซึ่งยังอยู่ในสถานะ validated → ถ้าไม่ยกเว้นจะ error
        "You are not allowed to write those fields after validation".
        """
        return list(
            set(super()._get_after_validation_exceptions() + _SEQUENCE_GAP_EXCEPTIONS)
        )

    def _get_under_validation_exceptions(self):
        return list(
            set(super()._get_under_validation_exceptions() + _SEQUENCE_GAP_EXCEPTIONS)
        )

    def button_draft(self):
        """รีเซ็ตเป็นร่างได้แม้เคยผ่าน tier validation แล้ว."""
        return super(
            AccountMove, self.with_context(skip_validation_check=True)
        ).button_draft()

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
