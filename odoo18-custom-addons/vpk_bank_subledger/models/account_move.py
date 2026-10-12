# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted._vpk_sync_bank_subledger()
        return posted

    def button_draft(self):
        lines = self.line_ids
        res = super().button_draft()
        self._vpk_clear_bank_subledger(lines)
        return res

    def button_cancel(self):
        lines = self.line_ids
        res = super().button_cancel()
        self._vpk_clear_bank_subledger(lines)
        return res

    def _vpk_clear_bank_subledger(self, lines):
        moves = self.env["vpk.bank.subledger.move"].search([("move_line_id", "in", lines.ids)])
        moves.unlink()

    def _vpk_sync_bank_subledger(self):
        SubMove = self.env["vpk.bank.subledger.move"]
        for line in self.line_ids.filtered("vpk_bank_subledger_id"):
            if line.company_currency_id.is_zero(line.debit) and line.company_currency_id.is_zero(line.credit):
                continue
            line_type = "receipt" if line.debit else "payment"
            vals = {
                "subledger_id": line.vpk_bank_subledger_id.id,
                "date": line.date,
                "line_type": line_type,
                "debit": line.debit if line_type == "receipt" else 0.0,
                "credit": line.credit if line_type == "payment" else 0.0,
                "name": line.name or line.move_id.ref or line.move_id.name,
                "ref": line.move_id.name,
                "move_line_id": line.id,
            }
            existing = SubMove.search([("move_line_id", "=", line.id)], limit=1)
            if existing:
                existing.write(vals)
            else:
                SubMove.create(vals)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    vpk_bank_subledger_id = fields.Many2one(
        "vpk.bank.subledger.account",
        string="บัญชีเงินฝาก",
        check_company=True,
        help="เลือกก้อนเงินของเลขบัญชีธนาคาร แล้วเปลี่ยนรหัสผังได้เฉพาะรหัสที่เลขบัญชีนี้ถูกจัดสรรไว้",
    )

    @api.onchange("vpk_bank_subledger_id")
    def _onchange_vpk_bank_subledger_id(self):
        if self.vpk_bank_subledger_id:
            self.account_id = self.vpk_bank_subledger_id.account_id

    @api.onchange("account_id")
    def _onchange_account_id_switch_bank_slice(self):
        subledger = self.vpk_bank_subledger_id
        if not subledger or not self.account_id or self.account_id == subledger.account_id:
            return
        candidates = self.env["vpk.bank.subledger.account"]._slices_for(
            self.company_id or self.move_id.company_id,
            subledger.acc_number,
            self.account_id,
        )
        if len(candidates) == 1:
            self.vpk_bank_subledger_id = candidates
            return
        rejected = self.account_id
        self.account_id = subledger.account_id
        if candidates:
            message = _(
                "เลขที่บัญชี %s มีหลายก้อนในผัง %s ให้เลือกชื่อก้อนจากช่องบัญชีเงินฝาก",
                subledger.acc_number,
                rejected.display_name,
            )
        else:
            message = _(
                "เลขที่บัญชี %s ไม่ได้จัดสรรเข้าผัง %s เลือกได้เฉพาะรหัสที่เลขบัญชีนี้ผูกไว้",
                subledger.acc_number,
                rejected.display_name,
            )
        return {"warning": {"title": _("รหัสผังบัญชี"), "message": message}}

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._vpk_align_bank_slice()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("vpk_skip_bank_align") and {"vpk_bank_subledger_id", "account_id"} & set(vals):
            self._vpk_align_bank_slice()
        return res

    def _vpk_align_bank_slice(self):
        for line in self:
            subledger = line.vpk_bank_subledger_id
            if not subledger:
                continue
            if not line.account_id or line.account_id == subledger.account_id:
                if line.account_id != subledger.account_id:
                    line.with_context(vpk_skip_bank_align=True).account_id = subledger.account_id
                continue
            candidates = self.env["vpk.bank.subledger.account"]._slices_for(
                line.company_id, subledger.acc_number, line.account_id
            )
            if len(candidates) == 1:
                line.with_context(vpk_skip_bank_align=True).vpk_bank_subledger_id = candidates
            elif not candidates:
                raise UserError(_(
                    "เลขที่บัญชี %s ไม่ได้จัดสรรเข้าผัง %s",
                    subledger.acc_number,
                    line.account_id.display_name,
                ))
            else:
                raise UserError(_(
                    "เลขที่บัญชี %s มีหลายก้อนในผัง %s ให้เลือกบัญชีเงินฝากให้ตรงก้อน",
                    subledger.acc_number,
                    line.account_id.display_name,
                ))


class AccountPayment(models.Model):
    _inherit = "account.payment"

    vpk_bank_subledger_id = fields.Many2one(
        "vpk.bank.subledger.account",
        string="บัญชีเงินฝาก",
        check_company=True,
        help="เลือกก้อนเงินของเลขบัญชีธนาคาร แล้วเปลี่ยนรหัสผังได้เฉพาะรหัสที่เลขบัญชีนี้ถูกจัดสรรไว้",
    )
    vpk_bank_gl_account_id = fields.Many2one(
        "account.account",
        string="รหัสผังบัญชี",
        check_company=True,
    )
    vpk_bank_account_domain_ids = fields.Many2many(
        "account.account",
        compute="_compute_vpk_bank_account_domain",
    )

    @api.depends("vpk_bank_subledger_id", "vpk_bank_subledger_id.acc_number", "company_id")
    def _compute_vpk_bank_account_domain(self):
        Slice = self.env["vpk.bank.subledger.account"]
        for payment in self:
            subledger = payment.vpk_bank_subledger_id
            if not subledger:
                payment.vpk_bank_account_domain_ids = False
                continue
            payment.vpk_bank_account_domain_ids = Slice._slices_for(
                payment.company_id, subledger.acc_number
            ).account_id

    @api.onchange("vpk_bank_subledger_id")
    def _onchange_vpk_bank_subledger_id(self):
        if self.vpk_bank_subledger_id:
            self.vpk_bank_gl_account_id = self.vpk_bank_subledger_id.account_id

    @api.onchange("vpk_bank_gl_account_id")
    def _onchange_vpk_bank_gl_account_id(self):
        subledger = self.vpk_bank_subledger_id
        account = self.vpk_bank_gl_account_id
        if not subledger or not account or account == subledger.account_id:
            return
        candidates = self.env["vpk.bank.subledger.account"]._slices_for(
            self.company_id, subledger.acc_number, account
        )
        if len(candidates) == 1:
            self.vpk_bank_subledger_id = candidates
            return
        self.vpk_bank_gl_account_id = subledger.account_id
        if candidates:
            message = _(
                "เลขที่บัญชี %s มีหลายก้อนในผังนี้ ให้เลือกชื่อก้อนจากช่องบัญชีเงินฝาก",
                subledger.acc_number,
            )
        else:
            message = _(
                "เลขที่บัญชี %s ไม่ได้จัดสรรเข้าผังนี้",
                subledger.acc_number,
            )
        return {"warning": {"title": _("รหัสผังบัญชี"), "message": message}}

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._vpk_align_payment_slice()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("vpk_skip_bank_align") and {"vpk_bank_subledger_id", "vpk_bank_gl_account_id"} & set(vals):
            self._vpk_align_payment_slice()
        return res

    def _vpk_align_payment_slice(self):
        for payment in self:
            subledger = payment.vpk_bank_subledger_id
            account = payment.vpk_bank_gl_account_id
            if subledger and not account:
                payment.with_context(vpk_skip_bank_align=True).vpk_bank_gl_account_id = subledger.account_id
                continue
            if not subledger or not account or account == subledger.account_id:
                continue
            candidates = self.env["vpk.bank.subledger.account"]._slices_for(
                payment.company_id, subledger.acc_number, account
            )
            if len(candidates) == 1:
                payment.with_context(vpk_skip_bank_align=True).vpk_bank_subledger_id = candidates
            elif not candidates:
                raise UserError(_(
                    "เลขที่บัญชี %s ไม่ได้จัดสรรเข้าผัง %s",
                    subledger.acc_number,
                    account.display_name,
                ))
            else:
                raise UserError(_(
                    "เลขที่บัญชี %s มีหลายก้อนในผัง %s ให้เลือกบัญชีเงินฝากให้ตรงก้อน",
                    subledger.acc_number,
                    account.display_name,
                ))

    def _get_valid_liquidity_accounts(self):
        accounts = super()._get_valid_liquidity_accounts()
        if self.vpk_bank_subledger_id:
            accounts |= self.vpk_bank_subledger_id.account_id
        return accounts

    def _prepare_move_liquidity_lines(self, default_values):
        lines = super()._prepare_move_liquidity_lines(default_values)
        subledger = self.vpk_bank_subledger_id
        if not subledger:
            return lines
        for line in lines:
            line["account_id"] = subledger.account_id.id
            line["vpk_bank_subledger_id"] = subledger.id
        return lines
