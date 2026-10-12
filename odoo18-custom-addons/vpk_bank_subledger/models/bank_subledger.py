# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.vpk_bank_subledger.data.snapshot_2569_08 import OPENING_DATE, SNAPSHOT


class BankSubledgerAccount(models.Model):
    _name = "vpk.bank.subledger.account"
    _description = "บัญชีคุมเงินฝากธนาคาร"
    _order = "sequence, id"
    _rec_name = "name"
    _rec_names_search = ["acc_number", "name"]

    sequence = fields.Integer(default=10)
    acc_number = fields.Char(string="เลขที่บัญชี", required=True)
    name = fields.Char(string="ชื่อบัญชี", required=True)
    account_id = fields.Many2one(
        "account.account",
        string="ผังบัญชี",
        required=True,
        check_company=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    active = fields.Boolean(default=True)
    note = fields.Text(string="หมายเหตุ")
    move_ids = fields.One2many("vpk.bank.subledger.move", "subledger_id", string="รายการรับจ่าย")
    balance = fields.Monetary(string="คงเหลือ", compute="_compute_balance")

    _sql_constraints = [
        (
            "bank_slice_unique",
            "unique(company_id, account_id, acc_number, name)",
            "เลขที่บัญชีนี้ถูกจัดสรรเข้าผังบัญชีนี้แล้ว",
        ),
    ]

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = "%s %s" % (rec.acc_number or "", rec.name or "")

    @api.model
    def _slices_for(self, company, acc_number, account=None):
        domain = [("company_id", "=", company.id), ("acc_number", "=", acc_number)]
        if account:
            domain.append(("account_id", "=", account.id))
        return self.search(domain)

    @api.depends("move_ids.debit", "move_ids.credit")
    def _compute_balance(self):
        grouped = {
            account: (debit, credit)
            for account, debit, credit in self.env["vpk.bank.subledger.move"]._read_group(
                [("subledger_id", "in", self.ids)],
                ["subledger_id"],
                ["debit:sum", "credit:sum"],
            )
        }
        for rec in self:
            debit, credit = grouped.get(rec, (0.0, 0.0))
            rec.balance = (debit or 0.0) - (credit or 0.0)

    @api.model
    def load_opening_snapshot(self):
        """Create the bank slices and the 31 August 2569 allocated balance once."""
        company = self.env["res.company"].search([("name", "ilike", "วชิระ")], limit=1) or self.env.company
        accounts = self.env["account.account"].with_company(company)
        opening_date = fields.Date.to_date(OPENING_DATE)
        created_books = 0
        created_moves = 0
        missing = []
        for sequence, gl_code, acc_number, name, balance in SNAPSHOT:
            account = accounts.search([("code", "=", gl_code)], limit=1)
            if not account:
                missing.append(gl_code)
                continue
            book = self.search([
                ("company_id", "=", company.id),
                ("account_id", "=", account.id),
                ("acc_number", "=", acc_number),
                ("name", "=", name),
            ], limit=1)
            if not book:
                book = self.create({
                    "sequence": sequence,
                    "company_id": company.id,
                    "account_id": account.id,
                    "acc_number": acc_number,
                    "name": name,
                })
                created_books += 1
            if not balance:
                continue
            already = self.env["vpk.bank.subledger.move"].search_count([
                ("subledger_id", "=", book.id),
                ("line_type", "=", "opening"),
                ("date", "=", opening_date),
            ])
            if already:
                continue
            debit = balance if balance > 0 else 0.0
            credit = -balance if balance < 0 else 0.0
            self.env["vpk.bank.subledger.move"].create({
                "subledger_id": book.id,
                "date": opening_date,
                "line_type": "opening",
                "debit": debit,
                "credit": credit,
                "name": "ยอดยกมา ณ 31 สิงหาคม 2569",
            })
            created_moves += 1
        if missing:
            raise UserError(_("ไม่พบผังบัญชี %s") % ", ".join(sorted(set(missing))))
        return created_books, created_moves


class BankSubledgerMove(models.Model):
    _name = "vpk.bank.subledger.move"
    _description = "รายการรับจ่ายเงินฝากธนาคาร"
    _order = "date, id"

    subledger_id = fields.Many2one(
        "vpk.bank.subledger.account",
        string="บัญชีธนาคาร",
        required=True,
        ondelete="cascade",
        index=True,
    )
    date = fields.Date(string="วันที่", required=True, default=fields.Date.context_today, index=True)
    line_type = fields.Selection(
        [
            ("opening", "ยอดยกมา"),
            ("receipt", "รับ"),
            ("payment", "จ่าย"),
        ],
        string="ประเภท",
        required=True,
        default="receipt",
    )
    name = fields.Char(string="คำอธิบาย")
    ref = fields.Char(string="อ้างอิง")
    debit = fields.Monetary(string="รับ")
    credit = fields.Monetary(string="จ่าย")
    company_id = fields.Many2one(related="subledger_id.company_id", store=True)
    currency_id = fields.Many2one(related="subledger_id.currency_id")
    account_id = fields.Many2one(related="subledger_id.account_id", store=True)
    acc_number = fields.Char(related="subledger_id.acc_number", store=True)
    move_line_id = fields.Many2one(
        "account.move.line",
        string="บรรทัดสมุดรายวัน",
        ondelete="cascade",
        index=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "move_line_unique",
            "unique(move_line_id)",
            "บรรทัดสมุดรายวันนี้ถูกบันทึกในบัญชีคุมแล้ว",
        ),
    ]

    @api.constrains("line_type", "debit", "credit")
    def _check_amounts(self):
        for rec in self:
            if rec.debit < 0 or rec.credit < 0:
                raise ValidationError(_("จำนวนเงินต้องไม่ติดลบ"))
            if rec.debit and rec.credit:
                raise ValidationError(_("บันทึกได้ข้างเดียว รับหรือจ่าย"))
            if rec.line_type == "receipt" and not rec.debit:
                raise ValidationError(_("รายการรับต้องใส่จำนวนฝั่งรับ"))
            if rec.line_type == "payment" and not rec.credit:
                raise ValidationError(_("รายการจ่ายต้องใส่จำนวนฝั่งจ่าย"))
            if rec.line_type == "opening" and not rec.debit and not rec.credit:
                raise ValidationError(_("ยอดยกมาต้องมีจำนวนเงิน"))

    @api.onchange("line_type")
    def _onchange_line_type(self):
        if self.line_type == "receipt":
            self.credit = 0.0
        elif self.line_type == "payment":
            self.debit = 0.0
