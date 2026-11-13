# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VpkPaymentVoucherCreateWizard(models.TransientModel):
    _name = "vpk.payment.voucher.create.wizard"
    _description = "สร้างใบสำคัญจ่ายจากใบเรียกเก็บ"

    voucher_id = fields.Many2one(
        comodel_name="vpk.payment.voucher",
        string="ใบสำคัญจ่าย (ถ้ามี)",
    )
    bill_ids = fields.Many2many(
        comodel_name="account.move",
        string="ใบเรียกเก็บ",
        domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="แหล่งเงิน / ชื่อกองทุน",
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        check_company=True,
    )
    available_bank_account_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_available_bank_account_ids",
    )
    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="บัญชีธนาคารที่ตัดจ่าย",
        domain="[('id', 'in', available_bank_account_ids)]",
    )
    company_partner_id = fields.Many2one(
        comodel_name="res.partner",
        default=lambda self: self.env.company.partner_id,
    )
    memo_subject = fields.Char(
        string="เรื่อง",
        default="ขออนุมัติเบิกจ่ายเงิน",
    )

    def _banks_linked_to_journal(self, journal):
        if not journal:
            return self.env["res.partner.bank"]
        banks = journal.bank_account_id
        partner = self.company_partner_id or self.env.company.partner_id
        banks |= self.env["res.partner.bank"].search(
            [
                ("journal_id", "=", journal.id),
                ("partner_id", "=", partner.id),
            ]
        )
        return banks.filtered(lambda bank: bool(bank))

    @api.depends("journal_id", "journal_id.bank_account_id", "company_id", "company_partner_id")
    def _compute_available_bank_account_ids(self):
        for wizard in self:
            wizard.available_bank_account_ids = wizard._banks_linked_to_journal(
                wizard.journal_id
            )

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        banks = self._banks_linked_to_journal(self.journal_id)
        self.available_bank_account_ids = banks
        preferred = self.journal_id.bank_account_id if self.journal_id else False
        if preferred and preferred in banks:
            self.bank_account_id = preferred
        elif self.bank_account_id not in banks:
            self.bank_account_id = banks[:1] if banks else False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if active_model == "account.move" and active_ids:
            bills = self.env["account.move"].browse(active_ids).filtered(
                lambda move: move.move_type == "in_invoice" and move.state == "posted"
            )
            res["bill_ids"] = [(6, 0, bills.ids)]
        return res

    def action_create_voucher(self):
        self.ensure_one()
        bills = self.bill_ids.filtered(
            lambda move: move.move_type == "in_invoice" and move.state == "posted"
        )
        if not bills:
            raise UserError(_("เลือกใบเรียกเก็บที่ POST แล้วอย่างน้อย 1 รายการ"))

        extra = {
            "journal_id": self.journal_id.id,
            "bank_account_id": self.bank_account_id.id,
            "memo_subject": self.memo_subject or _("ขออนุมัติเบิกจ่ายเงิน"),
        }
        if self.voucher_id:
            voucher = self.voucher_id
            existing_moves = voucher.line_ids.mapped("move_id")
            new_bills = bills - existing_moves
            lines = []
            seq = max(voucher.line_ids.mapped("sequence") or [0]) + 10
            for bill in new_bills:
                lines.append(
                    (
                        0,
                        0,
                        {
                            "sequence": seq,
                            "partner_id": bill.partner_id.id,
                            "partner_name": bill.partner_id.name,
                            "bill_ref": bill.name if bill.name != "/" else bill.ref or "",
                            "amount": bill.amount_residual or bill.amount_total,
                            "move_id": bill.id,
                        },
                    )
                )
                seq += 10
            vals = {"line_ids": lines, "bill_ids": [(4, bill.id) for bill in new_bills]}
            if self.journal_id:
                vals["journal_id"] = self.journal_id.id
            if self.bank_account_id:
                vals["bank_account_id"] = self.bank_account_id.id
            if self.memo_subject:
                vals["memo_subject"] = self.memo_subject
            voucher.write(vals)
        else:
            voucher = self.env["vpk.payment.voucher"].create_from_bills(bills, extra)

        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสำคัญจ่าย"),
            "res_model": "vpk.payment.voucher",
            "res_id": voucher.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
