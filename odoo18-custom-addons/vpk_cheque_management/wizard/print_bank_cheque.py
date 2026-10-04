# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


def split_amount_words(words, limit):
    if not words or not limit or len(words) <= limit:
        return words or "", ""
    cut = words.rfind(" ", 0, limit + 1)
    if cut <= 0:
        cut = limit
    return words[:cut].rstrip(), words[cut:].lstrip()


class VpkBankChequePrintWizard(models.TransientModel):
    _name = "vpk.bank.cheque.print.wizard"
    _description = "พิมพ์เช็ค"

    cheque_book_id = fields.Many2one("vpk.bank.cheque.book", string="สมุดเช็ค", required=True)
    cheque_leaf_id = fields.Many2one(
        "vpk.bank.cheque.leaf",
        string="เลขที่เช็ค",
        required=True,
        domain="['|', ('id', '=', cheque_leaf_id), '&', ('book_id', '=', cheque_book_id), ('state', '=', 'blank')]",
    )
    partner_id = fields.Many2one("res.partner", string="ผู้รับเงิน")
    pay_name_line1 = fields.Char(string="สั่งจ่าย")
    pay_name_line2 = fields.Char(string="สั่งจ่าย บรรทัด 2")
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount = fields.Monetary(string="จำนวนเงิน", required=True)
    amount_in_words = fields.Char(string="จำนวนเงินตัวอักษร")
    amount_in_words_line2 = fields.Char(string="จำนวนเงินตัวอักษร บรรทัด 2")
    date = fields.Date(string="วันที่บนเช็ค", required=True, default=fields.Date.context_today)
    is_ac_pay = fields.Boolean(string="ขีดคร่อม A/C Pay", default=True)
    is_preview = fields.Boolean()
    move_id = fields.Many2one("account.move", string="ใบเรียกเก็บ")
    payment_id = fields.Many2one("account.payment", string="การจ่ายเงิน")
    has_pay_line2 = fields.Boolean(compute="_compute_template_flags")
    has_amount_line2 = fields.Boolean(compute="_compute_template_flags")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        document = self._active_document()
        if not document:
            return values
        values.update({
            "partner_id": document.partner_id.id,
            "pay_name_line1": document.partner_id.name or "",
            "currency_id": document.currency_id.id,
        })
        if document._name == "account.move":
            values["move_id"] = document.id
            values["amount"] = document.amount_total
        elif document._name == "account.payment":
            values["payment_id"] = document.id
            values["amount"] = document.amount
        currency = self.env["res.currency"].browse(values.get("currency_id"))
        if currency and values.get("amount") is not None:
            values["amount_in_words"] = currency.with_context(lang="th_TH").amount_to_text(
                values["amount"]
            )
        return values

    def _active_document(self):
        model_name = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        if model_name in ("account.move", "account.payment") and active_id:
            return self.env[model_name].browse(active_id).exists()
        return self.env["account.move"]

    @api.depends("cheque_book_id")
    def _compute_template_flags(self):
        for wizard in self:
            attributes = wizard.cheque_book_id.template_id.line_ids.mapped("attribute_id.attribute")
            wizard.has_pay_line2 = "pay_line2" in attributes
            wizard.has_amount_line2 = "amount_line_2" in attributes

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            self.pay_name_line1 = self.partner_id.name

    @api.onchange("amount", "currency_id", "cheque_book_id")
    def _onchange_amount(self):
        if self.currency_id:
            self._fill_amount_words()

    @api.onchange("cheque_book_id")
    def _onchange_cheque_book_id(self):
        if not self.cheque_book_id:
            return
        if self.cheque_leaf_id.book_id != self.cheque_book_id:
            leaf = self.env["vpk.bank.cheque.leaf"].search(
                [
                    ("book_id", "=", self.cheque_book_id.id),
                    ("state", "=", "blank"),
                ],
                order="cheque_number asc",
                limit=1,
            )
            self.cheque_leaf_id = leaf

    def _fill_amount_words(self):
        for wizard in self:
            currency = wizard.currency_id or self.env.company.currency_id
            words = currency.with_context(lang="th_TH").amount_to_text(wizard.amount or 0.0)
            limit = wizard.cheque_book_id.template_id.max_char_in_line1
            line1, line2 = split_amount_words(words, limit)
            wizard.amount_in_words = line1
            wizard.amount_in_words_line2 = line2

    def _check_ready(self):
        self.ensure_one()
        if self.cheque_leaf_id.state == "cancelled":
            raise UserError(_("เช็คใบนี้ถูกยกเลิกแล้ว"))
        if self.cheque_leaf_id.book_id != self.cheque_book_id:
            raise UserError(_("เลขที่เช็คไม่ได้อยู่ในสมุดที่เลือก"))
        if not self.pay_name_line1:
            raise UserError(_("ใส่ชื่อผู้รับเงินบนเช็ค"))
        if not self.cheque_book_id.template_id.line_ids:
            raise UserError(_("แบบเช็คนี้ยังไม่มีตำแหน่งรายการ"))

    def _mark_printed(self):
        self.ensure_one()
        if self.cheque_leaf_id.state == "printed":
            return
        self.cheque_leaf_id.write({
            "partner_id": self.partner_id.id,
            "paid_to": self.pay_name_line1,
            "pay_name_line2": self.pay_name_line2,
            "issue_date": self.date,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "amount_in_words": self.amount_in_words,
            "amount_in_words_line2": self.amount_in_words_line2,
            "is_ac_pay": self.is_ac_pay,
            "move_id": self.move_id.id,
            "payment_id": self.payment_id.id,
            "state": "printed",
        })

    def cheque_line_value(self, line):
        self.ensure_one()
        attribute = line.attribute_id.attribute
        if attribute == "cheque_date":
            return line.attribute_id.format_date_value(self.date)
        if attribute == "pay_line1":
            return self.pay_name_line1 or ""
        if attribute == "pay_line2":
            return self.pay_name_line2 or ""
        if attribute == "amount_line_1":
            return self.amount_in_words or ""
        if attribute == "amount_line_2":
            return self.amount_in_words_line2 or ""
        if attribute == "amount_box":
            return "{:,.2f}".format(self.amount or 0.0)
        if attribute == "account_number":
            return self.cheque_book_id.account_number or ""
        if attribute == "ac_pay" and self.is_ac_pay:
            return "A/C Pay"
        return ""

    def action_print_preview(self):
        self.ensure_one()
        self._check_ready()
        self.is_preview = True
        self.cheque_book_id.template_id._apply_cheque_paperformat()
        return self.env.ref(
            "vpk_cheque_management.action_report_cheque_print"
        ).report_action(self)

    def action_print(self):
        self.ensure_one()
        self._check_ready()
        self.is_preview = False
        self._mark_printed()
        self.cheque_book_id.template_id._apply_cheque_paperformat()
        return self.env.ref(
            "vpk_cheque_management.action_report_cheque_print"
        ).report_action(self)
