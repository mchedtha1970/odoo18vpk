# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class VpkBankChequeBook(models.Model):
    _name = "vpk.bank.cheque.book"
    _description = "สมุดเช็ค"
    _order = "name"

    name = fields.Char(string="ชื่อสมุดเช็ค", required=True)
    active = fields.Boolean(default=True)
    template_id = fields.Many2one(
        "vpk.bank.cheque.template",
        string="แบบเช็ค",
        required=True,
        ondelete="restrict",
    )
    bank_id = fields.Many2one(related="template_id.bank_id", store=True)
    cheque_book_leaves = fields.Integer(string="จำนวนใบ", required=True, default=20)
    initial_cheque_number = fields.Integer(string="เลขที่เริ่มต้น", required=True)
    last_cheque_number = fields.Integer(
        string="เลขที่ใบสุดท้าย",
        compute="_compute_last_cheque_number",
        store=True,
    )
    account_number = fields.Char(
        string="เลขที่บัญชี",
        help="พิมพ์บนเช็คเมื่อแบบเช็คมีตำแหน่งเลขที่บัญชี",
    )
    leaf_ids = fields.One2many(
        "vpk.bank.cheque.leaf",
        "book_id",
        string="ใบเช็ค",
    )
    has_printed_leaf = fields.Boolean(compute="_compute_has_printed_leaf")

    @api.depends("cheque_book_leaves", "initial_cheque_number")
    def _compute_last_cheque_number(self):
        for book in self:
            if book.cheque_book_leaves and book.initial_cheque_number:
                book.last_cheque_number = (
                    book.initial_cheque_number + book.cheque_book_leaves - 1
                )
            else:
                book.last_cheque_number = 0

    @api.depends("leaf_ids.state")
    def _compute_has_printed_leaf(self):
        for book in self:
            book.has_printed_leaf = any(leaf.state == "printed" for leaf in book.leaf_ids)

    @api.model_create_multi
    def create(self, vals_list):
        books = super().create(vals_list)
        books._generate_leaves()
        return books

    def write(self, vals):
        number_fields = {"cheque_book_leaves", "initial_cheque_number"}
        if number_fields.intersection(vals) and any(book.has_printed_leaf for book in self):
            raise UserError(_("สมุดเช็คที่มีใบพิมพ์แล้ว เปลี่ยนช่วงเลขที่เช็คไม่ได้"))
        result = super().write(vals)
        if number_fields.intersection(vals):
            self.leaf_ids.filtered(lambda leaf: leaf.state == "blank").unlink()
            self._generate_leaves()
        return result

    def unlink(self):
        if any(book.has_printed_leaf for book in self):
            raise UserError(_("สมุดเช็คนี้มีเช็คที่พิมพ์แล้ว ลบไม่ได้"))
        return super().unlink()

    def _generate_leaves(self):
        leaves = self.env["vpk.bank.cheque.leaf"]
        for book in self:
            if not book.initial_cheque_number or not book.last_cheque_number:
                continue
            existing = set(book.leaf_ids.mapped("cheque_number"))
            vals_list = [
                {"cheque_number": number, "book_id": book.id}
                for number in range(book.initial_cheque_number, book.last_cheque_number + 1)
                if number not in existing
            ]
            if vals_list:
                leaves.create(vals_list)

    def action_create_leaves(self):
        for book in self:
            if not book.cheque_book_leaves:
                raise UserError(_("ใส่จำนวนใบเช็คก่อน"))
            if not book.initial_cheque_number:
                raise UserError(_("ใส่เลขที่เช็คใบแรกก่อน"))
        self._generate_leaves()


class VpkBankChequeLeaf(models.Model):
    _name = "vpk.bank.cheque.leaf"
    _description = "ใบเช็ค"
    _order = "cheque_number"
    _rec_name = "cheque_number"

    book_id = fields.Many2one(
        "vpk.bank.cheque.book",
        string="สมุดเช็ค",
        required=True,
        ondelete="cascade",
    )
    template_id = fields.Many2one(related="book_id.template_id", store=True)
    state = fields.Selection(
        [
            ("blank", "ยังไม่พิมพ์"),
            ("printed", "พิมพ์แล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="blank",
        required=True,
    )
    cheque_number = fields.Integer(string="เลขที่เช็ค", required=True)
    partner_id = fields.Many2one("res.partner", string="ผู้รับเงิน")
    paid_to = fields.Char(string="สั่งจ่าย")
    pay_name_line2 = fields.Char(string="สั่งจ่าย บรรทัด 2")
    issue_date = fields.Date(string="วันที่บนเช็ค")
    amount = fields.Monetary(string="จำนวนเงิน")
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน",
        default=lambda self: self.env.company.currency_id,
    )
    amount_in_words = fields.Char(string="จำนวนเงินตัวอักษร")
    amount_in_words_line2 = fields.Char(string="จำนวนเงินตัวอักษร บรรทัด 2")
    is_ac_pay = fields.Boolean(string="ขีดคร่อม A/C Pay")
    move_id = fields.Many2one("account.move", string="ใบเรียกเก็บ", ondelete="set null")
    payment_id = fields.Many2one("account.payment", string="การจ่ายเงิน", ondelete="set null")

    _sql_constraints = [
        (
            "cheque_number_book_uniq",
            "unique(book_id, cheque_number)",
            "เลขที่เช็คซ้ำในสมุดเดียวกัน",
        ),
    ]

    @api.constrains("cheque_number", "book_id")
    def _check_cheque_number_range(self):
        for leaf in self:
            book = leaf.book_id
            if not book.initial_cheque_number or not book.last_cheque_number:
                continue
            if leaf.cheque_number < book.initial_cheque_number or leaf.cheque_number > book.last_cheque_number:
                raise ValidationError(
                    _("เลขที่เช็ค %s อยู่นอกช่วง %s ถึง %s")
                    % (leaf.cheque_number, book.initial_cheque_number, book.last_cheque_number)
                )

    def action_print(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("เช็คใบนี้ถูกยกเลิกแล้ว"))
        wizard = self.env["vpk.bank.cheque.print.wizard"].create({
            "cheque_book_id": self.book_id.id,
            "cheque_leaf_id": self.id,
            "partner_id": self.partner_id.id,
            "pay_name_line1": self.paid_to or (self.partner_id.name or ""),
            "pay_name_line2": self.pay_name_line2,
            "amount": self.amount,
            "currency_id": (self.currency_id or self.env.company.currency_id).id,
            "date": self.issue_date or fields.Date.context_today(self),
            "is_ac_pay": self.is_ac_pay if self.state == "printed" else True,
            "move_id": self.move_id.id,
            "payment_id": self.payment_id.id,
            "amount_in_words": self.amount_in_words,
            "amount_in_words_line2": self.amount_in_words_line2,
        })
        if not wizard.amount_in_words:
            wizard._fill_amount_words()
        return {
            "type": "ir.actions.act_window",
            "name": _("พิมพ์เช็ค"),
            "res_model": "vpk.bank.cheque.print.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_cancel(self):
        cancelled = self.filtered(lambda leaf: leaf.state != "cancelled")
        cancelled.write({"state": "cancelled"})

    @api.depends("book_id.name", "cheque_number")
    def _compute_display_name(self):
        for leaf in self:
            leaf.display_name = "%s %s" % (leaf.book_id.name or "", leaf.cheque_number)
