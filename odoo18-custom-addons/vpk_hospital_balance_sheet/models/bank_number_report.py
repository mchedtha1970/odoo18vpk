# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import fields, models

from .bank_statement_2569_08 import STATEMENT_DATE_FROM, STATEMENT_DATE_TO, STATEMENT_ROWS

STATEMENT_FROM = fields.Date.to_date(STATEMENT_DATE_FROM)
STATEMENT_TO = fields.Date.to_date(STATEMENT_DATE_TO)


class BankNumberReportHandler(models.AbstractModel):
    _name = "vpk.bank.number.report.handler"
    _inherit = "account.report.custom.handler"
    _description = "รายงานเงินฝากธนาคารตามเลขที่บัญชีธนาคาร"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        options["ignore_totals_below_sections"] = True
        options["vpk_name_column_label"] = "เลขที่บัญชี"
        options["custom_columns_subheaders"] = [
            {"name": "", "colspan": 1},
            {"name": "รับ-จ่ายเดือนนี้", "colspan": 2},
            {"name": "ยอดคงเหลือ", "colspan": 2},
        ]

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        books = self._company_books(report, options)
        balances = self._balances_by_column_group(options, books)
        movements = self._movements_by_column_group(options, books)
        by_number = defaultdict(lambda: self.env["vpk.bank.subledger.account"])
        for book in books:
            by_number[book.acc_number] |= book

        lines = []
        sequence = 0
        grand = self._empty_values(options)
        seen = set()
        for number, name, _debit, _credit in STATEMENT_ROWS:
            seen.add(number)
            values = self._row_values(options, balances, movements, by_number.get(number), number, name)
            self._add_values(grand, values)
            lines.append((sequence, self._line(report, options, number, number, values)))
            sequence += 1
        for number in sorted(set(by_number) - seen):
            sample = by_number[number].sorted(key=lambda book: (book.sequence, book.id))[:1]
            values = self._row_values(options, balances, movements, by_number[number], number, sample.name)
            if not any(
                row["debit"] or row["credit"] or row["balance_debit"] or row["balance_credit"]
                for row in values.values()
            ):
                continue
            self._add_values(grand, values)
            lines.append((sequence, self._line(report, options, number, number, values)))
            sequence += 1
        for key in grand:
            grand[key]["account_name"] = ""
        total_id = report._get_generic_line_id(None, None, markup="total")
        lines.append((sequence, self._line(report, options, total_id, "รวม", grand, bold=True)))
        return lines

    def _company_books(self, report, options):
        return self.env["vpk.bank.subledger.account"].search([
            ("company_id", "in", report.get_report_company_ids(options)),
        ])

    def _period(self, options, column_group_key):
        forced = options["column_groups"][column_group_key]["forced_options"]
        date_info = forced.get("date") or options["date"]
        return fields.Date.to_date(date_info["date_from"]), fields.Date.to_date(date_info["date_to"])

    def _balances_by_column_group(self, options, books):
        balances = {}
        moves = self.env["vpk.bank.subledger.move"].search([("subledger_id", "in", books.ids)])
        for column_group_key in options["column_groups"]:
            _date_from, date_to = self._period(options, column_group_key)
            slot = {book.id: 0.0 for book in books}
            for move in moves:
                if move.date > date_to:
                    continue
                slot[move.subledger_id.id] += (move.debit or 0.0) - (move.credit or 0.0)
            balances[column_group_key] = slot
        return balances

    def _movements_by_column_group(self, options, books):
        movements = {}
        moves = self.env["vpk.bank.subledger.move"].search([
            ("subledger_id", "in", books.ids),
            ("line_type", "!=", "opening"),
        ])
        statement = {number: (debit, credit) for number, _name, debit, credit in STATEMENT_ROWS}
        for column_group_key in options["column_groups"]:
            date_from, date_to = self._period(options, column_group_key)
            slot = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
            if date_from <= STATEMENT_TO and date_to >= STATEMENT_FROM:
                for number, (debit, credit) in statement.items():
                    slot[number]["debit"] += debit
                    slot[number]["credit"] += credit
            for move in moves:
                if STATEMENT_FROM <= move.date <= STATEMENT_TO:
                    continue
                if move.date < date_from or move.date > date_to:
                    continue
                slot[move.acc_number]["debit"] += move.debit or 0.0
                slot[move.acc_number]["credit"] += move.credit or 0.0
            movements[column_group_key] = slot
        return movements

    def _empty_values(self, options):
        return {
            key: {
                "account_name": "",
                "debit": 0.0,
                "credit": 0.0,
                "balance_debit": 0.0,
                "balance_credit": 0.0,
            }
            for key in options["column_groups"]
        }

    def _row_values(self, options, balances, movements, books, number, name):
        values = self._empty_values(options)
        books = books or self.env["vpk.bank.subledger.account"]
        for key in options["column_groups"]:
            balance = sum(balances[key][book.id] for book in books)
            movement = movements[key].get(number) or {"debit": 0.0, "credit": 0.0}
            values[key] = {
                "account_name": name,
                "debit": movement["debit"],
                "credit": movement["credit"],
                "balance_debit": balance if balance > 0 else 0.0,
                "balance_credit": -balance if balance < 0 else 0.0,
            }
        return values

    def _add_values(self, grand, values):
        for key, row in values.items():
            grand[key]["debit"] += row["debit"]
            grand[key]["credit"] += row["credit"]
            grand[key]["balance_debit"] += row["balance_debit"]
            grand[key]["balance_credit"] += row["balance_credit"]

    def _line(self, report, options, markup, name, values, bold=False):
        columns = []
        for column in options["columns"]:
            label = column["expression_label"]
            value = values[column["column_group_key"]][label]
            column_dict = report._build_column_dict(value, column, options=options)
            if label == "balance_debit" and not value:
                column_dict["name"] = "-"
            elif label == "balance_credit" and not value:
                column_dict["name"] = ""
            columns.append(column_dict)
        line = {
            "id": report._get_generic_line_id(None, None, markup=markup),
            "name": name,
            "level": 1,
            "columns": columns,
            "unfoldable": False,
            "unfolded": False,
        }
        if bold:
            line["class"] = "fw-bold"
        return line
