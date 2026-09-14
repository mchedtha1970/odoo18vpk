# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


CREDIT_NOTE_TYPES = ("out_refund", "in_refund")
CREDIT_NOTE_EDIT_FIELDS = {
    "partner_id",
    "ref",
    "date",
    "invoice_date",
    "invoice_date_due",
    "invoice_line_ids",
    "line_ids",
    "journal_id",
    "currency_id",
    "fiscal_position_id",
    "invoice_payment_term_id",
    "invoice_origin",
    "narration",
}


class AccountMove(models.Model):
    _inherit = "account.move"

    can_edit_credit_note = fields.Boolean(
        string="มีสิทธิ์แก้ไขใบลดหนี้",
        compute="_compute_credit_note_permissions",
    )
    can_create_credit_note = fields.Boolean(
        string="มีสิทธิ์สร้างใบลดหนี้",
        compute="_compute_credit_note_permissions",
    )

    @api.depends_context("uid")
    def _compute_credit_note_permissions(self):
        can_edit = self.env.su or self.env.user.has_group(
            "vpk_procurement_auto_pr.group_credit_note_editor"
        )
        can_create = self.env.su or self.env.user.has_group(
            "vpk_procurement_auto_pr.group_credit_note_creator"
        )
        for move in self:
            move.can_edit_credit_note = can_edit
            move.can_create_credit_note = can_create

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su and any(
            vals.get(
                "move_type",
                self.env.context.get("default_move_type", "entry"),
            )
            in CREDIT_NOTE_TYPES
            for vals in vals_list
        ) and not self.env.user.has_group(
            "vpk_procurement_auto_pr.group_credit_note_creator"
        ):
            raise AccessError(
                _(
                    "คุณไม่มีสิทธิ์สร้างเอกสารลดหนี้ "
                    "กรุณาติดต่อผู้ดูแลระบบเพื่อขอสิทธิ์ "
                    "'สร้างเอกสารลดหนี้'"
                )
            )
        return super().create(vals_list)

    def write(self, vals):
        protected_change = bool(CREDIT_NOTE_EDIT_FIELDS.intersection(vals))
        restricted_moves = self.filtered(
            lambda move: move.move_type in CREDIT_NOTE_TYPES
            and move.state == "draft"
        )
        if (
            protected_change
            and restricted_moves
            and not self.env.su
            and not self.env.user.has_group(
                "vpk_procurement_auto_pr.group_credit_note_editor"
            )
        ):
            raise AccessError(
                _(
                    "คุณไม่มีสิทธิ์แก้ไขเอกสารลดหนี้ "
                    "กรุณาติดต่อผู้ดูแลระบบเพื่อขอสิทธิ์ "
                    "'แก้ไขเอกสารลดหนี้'"
                )
            )
        return super().write(vals)


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self, is_modify=False):
        if not self.env.su and not self.env.user.has_group(
            "vpk_procurement_auto_pr.group_credit_note_creator"
        ):
            raise AccessError(
                _("คุณไม่มีสิทธิ์สร้างเอกสารลดหนี้")
            )
        return super().reverse_moves(is_modify=is_modify)
