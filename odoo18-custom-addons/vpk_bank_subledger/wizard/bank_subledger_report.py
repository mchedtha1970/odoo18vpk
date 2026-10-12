# -*- coding: utf-8 -*-
import base64
import io
from collections import defaultdict

import xlsxwriter

from odoo import _, fields, models
from odoo.exceptions import UserError

THAI_MONTHS = (
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
)


class BankSubledgerReport(models.TransientModel):
    _name = "vpk.bank.subledger.report"
    _description = "รายงานเงินฝากธนาคาร"

    date_from = fields.Date(string="ตั้งแต่วันที่", required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string="ถึงวันที่", required=True, default=fields.Date.context_today)
    account_id = fields.Many2one("account.account", string="ผังบัญชี")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    hide_zero = fields.Boolean(string="ซ่อนรายการยอดศูนย์")
    line_ids = fields.One2many("vpk.bank.subledger.report.line", "wizard_id")

    def action_compute(self):
        self.ensure_one()
        self._fill_lines()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายงานเงินฝากธนาคาร"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_export_xlsx(self):
        self.ensure_one()
        self._fill_lines()
        content = self._render_xlsx()
        attachment = self.env["ir.attachment"].create({
            "name": "รายงานเงินฝากธนาคาร.xlsx",
            "type": "binary",
            "datas": base64.b64encode(content),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _fill_lines(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด"))
        self.line_ids.unlink()
        domain = [("company_id", "=", self.company_id.id), ("active", "=", True)]
        if self.account_id:
            domain.append(("account_id", "=", self.account_id.id))
        books = self.env["vpk.bank.subledger.account"].search(domain)
        moves = self.env["vpk.bank.subledger.move"].search([
            ("subledger_id", "in", books.ids),
            ("date", "<=", self.date_to),
        ])
        buckets = defaultdict(lambda: {"before": 0.0, "opening": 0.0, "receipt": 0.0, "payment": 0.0})
        for move in moves:
            bucket = buckets[move.subledger_id.id]
            amount = move.debit - move.credit
            if move.date < self.date_from:
                bucket["before"] += amount
            elif move.line_type == "opening":
                bucket["opening"] += amount
            elif move.line_type == "receipt":
                bucket["receipt"] += move.debit
            elif move.line_type == "payment":
                bucket["payment"] += move.credit
        values = []
        sequence = 0
        grand = {"opening": 0.0, "receipt": 0.0, "payment": 0.0, "closing": 0.0}
        for account in books.mapped("account_id").sorted(key=lambda item: item.code or ""):
            group_books = books.filtered(lambda book, account=account: book.account_id == account)
            group = {"opening": 0.0, "receipt": 0.0, "payment": 0.0, "closing": 0.0}
            detail = []
            for book in group_books:
                bucket = buckets[book.id]
                opening = bucket["before"] + bucket["opening"]
                closing = opening + bucket["receipt"] - bucket["payment"]
                if self.hide_zero and not any((opening, bucket["receipt"], bucket["payment"], closing)):
                    continue
                detail.append({
                    "account_id": account.id,
                    "gl_code": account.code,
                    "gl_name": account.name,
                    "acc_number": book.acc_number,
                    "sub_name": book.name,
                    "opening": opening,
                    "receipt": bucket["receipt"],
                    "payment": bucket["payment"],
                    "closing": closing,
                })
                for key in ("opening", "receipt", "payment"):
                    group[key] += detail[-1][key]
                group["closing"] += closing
            if not detail:
                continue
            for row in detail:
                sequence += 1
                row["sequence"] = sequence
                row["wizard_id"] = self.id
                values.append(row)
            sequence += 1
            values.append({
                "wizard_id": self.id,
                "sequence": sequence,
                "account_id": account.id,
                "gl_code": account.code,
                "gl_name": account.name,
                "sub_name": "รวม",
                "is_total": True,
                "opening": group["opening"],
                "receipt": group["receipt"],
                "payment": group["payment"],
                "closing": group["closing"],
            })
            for key in grand:
                grand[key] += group[key]
        if values:
            sequence += 1
            values.append({
                "wizard_id": self.id,
                "sequence": sequence,
                "sub_name": "รวมทั้งสิ้น",
                "is_total": True,
                "opening": grand["opening"],
                "receipt": grand["receipt"],
                "payment": grand["payment"],
                "closing": grand["closing"],
            })
        if values:
            self.env["vpk.bank.subledger.report.line"].create(values)

    def _thai_date(self, value):
        return "%s %s %s" % (value.day, THAI_MONTHS[value.month - 1], value.year + 543)

    def _render_xlsx(self):
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        sheet = workbook.add_worksheet("เงินฝากธนาคาร")
        title = workbook.add_format({"font_name": "TH Sarabun New", "font_size": 18, "bold": True, "align": "center"})
        header = workbook.add_format({"font_name": "TH Sarabun New", "font_size": 14, "bold": True, "border": 1, "align": "center", "bg_color": "#D9E2F3"})
        text = workbook.add_format({"font_name": "TH Sarabun New", "font_size": 14, "border": 1})
        money = workbook.add_format({"font_name": "TH Sarabun New", "font_size": 14, "border": 1, "num_format": "#,##0.00"})
        total_text = workbook.add_format({"font_name": "TH Sarabun New", "font_size": 14, "border": 1, "bold": True})
        total_money = workbook.add_format({"font_name": "TH Sarabun New", "font_size": 14, "border": 1, "bold": True, "num_format": "#,##0.00"})
        titles = (
            self.company_id.name or "โรงพยาบาลวชิระภูเก็ต",
            "รายงานเงินฝากธนาคาร",
            "ตั้งแต่วันที่ %s ถึงวันที่ %s" % (self._thai_date(self.date_from), self._thai_date(self.date_to)),
        )
        for row, value in enumerate(titles):
            sheet.merge_range(row, 0, row, 7, value, title)
            sheet.set_row(row, 24)
        columns = ("ผังบัญชี", "ชื่อผังบัญชี", "เลขที่บัญชี", "ชื่อบัญชี", "ยอดยกมา", "รับ", "จ่าย", "คงเหลือ")
        for col, value in enumerate(columns):
            sheet.write(3, col, value, header)
        sheet.set_column(0, 0, 18)
        sheet.set_column(1, 1, 42)
        sheet.set_column(2, 2, 20)
        sheet.set_column(3, 3, 55)
        sheet.set_column(4, 7, 16)
        for offset, line in enumerate(self.line_ids):
            row = 4 + offset
            label_fmt = total_text if line.is_total else text
            amount_fmt = total_money if line.is_total else money
            sheet.write(row, 0, line.gl_code or "", label_fmt)
            sheet.write(row, 1, "" if line.is_total and line.sub_name == "รวมทั้งสิ้น" else (line.gl_name or ""), label_fmt)
            sheet.write(row, 2, line.acc_number or "", label_fmt)
            sheet.write(row, 3, line.sub_name or "", label_fmt)
            sheet.write_number(row, 4, line.opening, amount_fmt)
            sheet.write_number(row, 5, line.receipt, amount_fmt)
            sheet.write_number(row, 6, line.payment, amount_fmt)
            sheet.write_number(row, 7, line.closing, amount_fmt)
        workbook.close()
        return buffer.getvalue()


class BankSubledgerReportLine(models.TransientModel):
    _name = "vpk.bank.subledger.report.line"
    _description = "บรรทัดรายงานเงินฝากธนาคาร"
    _order = "sequence, id"

    wizard_id = fields.Many2one("vpk.bank.subledger.report", required=True, ondelete="cascade")
    sequence = fields.Integer()
    account_id = fields.Many2one("account.account")
    gl_code = fields.Char(string="ผังบัญชี")
    gl_name = fields.Char(string="ชื่อผังบัญชี")
    acc_number = fields.Char(string="เลขที่บัญชี")
    sub_name = fields.Char(string="ชื่อบัญชี")
    opening = fields.Monetary(string="ยอดยกมา")
    receipt = fields.Monetary(string="รับ")
    payment = fields.Monetary(string="จ่าย")
    closing = fields.Monetary(string="คงเหลือ")
    is_total = fields.Boolean()
    currency_id = fields.Many2one(related="wizard_id.company_id.currency_id")
