# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import fields, models

# Each general-ledger code is a group root. Bank slices of that code are its children.
# Order and titles follow sheet "เงินฝากธนาคาร รพ.(ย่อย)". The combined header
# 1101020603-5.101 is split so each real account code is its own root.
GROUPS = (
    ("1101020603.101", "เงินฝาก ธ.-ใน งปม."),
    ("1101020605.101", "เงินฝากธนาคารรับจากคลัง (เงินกู้)"),
    ("1101030101.101", "เงินฝาก ธ.- กระแสรายวัน"),
    ("1101030101.103", "เงินฝาก ธ.- กระแสรายวันที่มีวัตถุประสงค์เฉพาะ"),
    ("1101030102.101", "เงินฝาก ธ.- ออมทรัพย์"),
    ("1101030102.102", "เงินฝาก ธ.-::รอจัดสรร"),
    ("1101030102.104", "เงินฝาก ธ.-::งบลงทุน UC"),
    ("1101030102.103", "เงินฝาก ธ.- ที่มีวัตถุประสงค์เฉพาะ ++ บริจาค (ปี'64-69)+ดบ.69"),
    ("1101030102.105", "เงินฝาก ธ.- ที่มีวัตถุประสงค์เฉพาะ(บริจาค) -ปี'63(ลงมา)"),
    ("1104010101.101", "เงินฝาก ธ.- เงินฝากประจำ"),
)


class CashEquivalentReportHandler(models.AbstractModel):
    _name = "vpk.cash.equivalent.report.handler"
    _inherit = "account.report.custom.handler"
    _description = "เงินฝากธนาคาร จัดกลุ่มตามรหัสบัญชี"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        options["ignore_totals_below_sections"] = True

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        books = self._company_books(report, options)
        figures = self._figures_by_column_group(options, books)
        grouped = defaultdict(lambda: self.env["vpk.bank.subledger.account"])
        for book in books.sorted(key=lambda item: (item.sequence, item.id)):
            grouped[book.account_id.with_company(book.company_id).code] |= book

        lines = []
        sequence = 0
        grand = self._empty_values(options)
        seen = set()
        for code, title in GROUPS:
            seen.add(code)
            sequence = self._append_group(
                report, options, lines, sequence, grand, figures, code, title, grouped.get(code),
            )
        for code in sorted(set(grouped) - seen):
            group_books = grouped[code]
            if not self._has_amount(options, figures, group_books):
                continue
            sequence = self._append_group(
                report, options, lines, sequence, grand, figures, code, code, group_books,
            )
        for key in grand:
            grand[key]["acc_number"] = ""
            grand[key]["account_name"] = ""
        total_id = report._get_generic_line_id(None, None, markup="total")
        lines.append((sequence, self._line(report, options, total_id, "รวม", grand, level=0, bold=True)))
        return lines

    def _append_group(self, report, options, lines, sequence, grand, figures, code, title, books):
        books = books or self.env["vpk.bank.subledger.account"]
        group_id = report._get_generic_line_id(None, None, markup=code)
        totals = self._books_values(options, figures, books, code, title)
        self._add_values(grand, totals)
        lines.append((
            sequence,
            self._line(report, options, group_id, code, totals, level=1, bold=True, unfoldable=True),
        ))
        sequence += 1
        for book in books:
            values = self._books_values(options, figures, book, book.acc_number, book.name)
            child_id = report._get_generic_line_id(
                "vpk.bank.subledger.account", book.id, parent_line_id=group_id,
            )
            lines.append((
                sequence,
                self._line(
                    report, options, child_id, book.acc_number, values,
                    level=3, parent_id=group_id,
                ),
            ))
            sequence += 1
        return sequence

    def _has_amount(self, options, figures, books):
        values = self._books_values(options, figures, books, "", "")
        return any(row["balance"] for row in values.values())

    def _company_books(self, report, options):
        company_ids = report.get_report_company_ids(options)
        return self.env["vpk.bank.subledger.account"].search([
            ("company_id", "in", company_ids),
        ])

    def _figures_by_column_group(self, options, books):
        figures = {}
        moves = self.env["vpk.bank.subledger.move"].search([
            ("subledger_id", "in", books.ids),
        ])
        for column_group_key in options["column_groups"]:
            forced = options["column_groups"][column_group_key]["forced_options"]
            date_info = forced.get("date") or options["date"]
            date_to = fields.Date.to_date(date_info["date_to"])
            slot = {book.id: 0.0 for book in books}
            for move in moves:
                if move.date > date_to:
                    continue
                slot[move.subledger_id.id] += (move.debit or 0.0) - (move.credit or 0.0)
            figures[column_group_key] = slot
        return figures

    def _empty_values(self, options):
        return {
            key: {
                "acc_number": "",
                "account_name": "",
                "balance": 0.0,
            }
            for key in options["column_groups"]
        }

    def _books_values(self, options, figures, books, number, name):
        values = self._empty_values(options)
        books = books or self.env["vpk.bank.subledger.account"]
        for key in options["column_groups"]:
            balance = 0.0
            for book in books:
                balance += figures[key][book.id]
            values[key] = {
                "acc_number": number,
                "account_name": name,
                "balance": balance,
            }
        return values

    def _add_values(self, grand, values):
        for key, row in values.items():
            grand[key]["balance"] += row["balance"]

    def _line(self, report, options, line_id, name, values, level, bold=False, unfoldable=False, parent_id=None):
        columns = []
        for column in options["columns"]:
            label = column["expression_label"]
            columns.append(report._build_column_dict(
                values[column["column_group_key"]][label],
                column,
                options=options,
            ))
        line = {
            "id": line_id,
            "name": name,
            "level": level,
            "columns": columns,
            "unfoldable": unfoldable,
            "unfolded": unfoldable,
        }
        if bold:
            line["class"] = "fw-bold"
        if parent_id:
            line["parent_id"] = parent_id
        return line
