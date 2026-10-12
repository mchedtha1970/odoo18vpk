# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields, models

THAI_MONTHS = (
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)
# Drop the default date header (row 0), the empty subheader row (row 1),
# and the column-name row (row 2, "จำนวนเงิน"). The first figure is written
# at original row 4; shift by -1 so it follows the title on row 3.
SKIP_BEFORE = 3
TABLE_SHIFT = -1


class AccountReport(models.Model):
    _inherit = "account.report"

    def _vpk_statement_kind(self):
        balance = self.env.ref("vpk_hospital_balance_sheet.balance_sheet", raise_if_not_found=False)
        cash = self.env.ref("vpk_hospital_balance_sheet.cash_flow", raise_if_not_found=False)
        profit = self.env.ref("vpk_hospital_balance_sheet.profit_and_loss", raise_if_not_found=False)
        notes = self.env.ref("vpk_hospital_balance_sheet.financial_notes", raise_if_not_found=False)
        cash_equivalent = self.env.ref("vpk_hospital_balance_sheet.cash_equivalent", raise_if_not_found=False)
        bank_number = self.env.ref("vpk_hospital_balance_sheet.bank_by_number", raise_if_not_found=False)
        if balance and self == balance:
            return "balance"
        if cash and self == cash:
            return "cash"
        if profit and self == profit:
            return "profit"
        if notes and self == notes:
            return "notes"
        if cash_equivalent and self == cash_equivalent:
            return "cash_equivalent"
        if bank_number and self == bank_number:
            return "bank_number"
        return None

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        if not self._vpk_statement_kind():
            return super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

        self._vpk_write_xlsx_title(workbook, sheet, options)
        originals = (sheet.write, sheet.write_datetime, sheet.merge_range)

        def shift_write(row, col, *args, **kwargs):
            if row < SKIP_BEFORE:
                return
            return originals[0](row + TABLE_SHIFT, col, *args, **kwargs)

        def shift_datetime(row, col, *args, **kwargs):
            if row < SKIP_BEFORE:
                return
            return originals[1](row + TABLE_SHIFT, col, *args, **kwargs)

        def shift_merge(first_row, first_col, last_row, last_col, data, *args, **kwargs):
            if first_row < SKIP_BEFORE:
                return
            # merge_range writes through sheet.write; keep the original so the row is not shifted twice.
            sheet.write = originals[0]
            sheet.write_datetime = originals[1]
            try:
                return originals[2](
                    first_row + TABLE_SHIFT,
                    first_col,
                    last_row + TABLE_SHIFT,
                    last_col,
                    data,
                    *args,
                    **kwargs,
                )
            finally:
                sheet.write = shift_write
                sheet.write_datetime = shift_datetime

        sheet.write = shift_write
        sheet.write_datetime = shift_datetime
        sheet.merge_range = shift_merge
        try:
            return super()._inject_report_into_xlsx_sheet(options, workbook, sheet)
        finally:
            sheet.write, sheet.write_datetime, sheet.merge_range = originals

    def _vpk_write_xlsx_title(self, workbook, sheet, options):
        header_format = workbook.add_format({
            "font_name": "TH Sarabun New",
            "font_size": 18,
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "font_color": "#000000",
        })
        company_name = self._vpk_xlsx_company_name(options)
        kind = self._vpk_statement_kind()
        if kind == "cash":
            lines = (
                "งบกระแสเงินสด (ทางตรง)",
                company_name,
                self._vpk_period_title(options, "สิ้นสุดวันที่"),
            )
        elif kind == "profit":
            lines = (
                company_name,
                "งบแสดงผลการดำเนินงานทางการเงิน (งบรายได้ ค่าใช้จ่าย)",
                self._vpk_period_title(options, "สิ้นสุด ณ วันที่"),
            )
        elif kind == "notes":
            lines = (
                company_name,
                "หมายเหตุประกอบงบการเงิน",
                self._vpk_period_title(options, "สิ้นสุด ณ วันที่"),
            )
        elif kind == "cash_equivalent":
            lines = (
                company_name,
                "เงินฝากธนาคาร จัดกลุ่มตามรหัสบัญชี",
                self._vpk_period_title(options, "ประจำเดือน สิ้นสุด"),
            )
        elif kind == "bank_number":
            lines = (
                "รายการเงินสดและเทียบเท่าเงินสด",
                company_name,
                self._vpk_month_title(options),
            )
        else:
            lines = (
                company_name,
                "งบแสดงฐานะการเงิน",
                self._vpk_period_title(options),
            )
        last_col = max(self._vpk_xlsx_last_col(options), 1)
        for row, text in enumerate(lines):
            sheet.set_row(row, 24)
            sheet.merge_range(row, 0, row, last_col, text, header_format)

    def _vpk_month_title(self, options):
        date_to = (options.get("date") or {}).get("date_to")
        as_of = fields.Date.to_date(date_to) if date_to else fields.Date.context_today(self)
        if not isinstance(as_of, date):
            as_of = fields.Date.context_today(self)
        return "ประจำเดือน  %s  %s" % (THAI_MONTHS[as_of.month - 1], as_of.year + 543)

    def _vpk_xlsx_company_name(self, options):
        names = [company["name"] for company in options.get("companies") or []]
        hospital = "โรงพยาบาลวชิระภูเก็ต"
        if hospital in names or not names:
            return hospital
        if len(names) == 1:
            return names[0]
        return self.env.company.name

    def _vpk_period_title(self, options, prefix="ประจำเดือน สิ้นสุด"):
        date_to = (options.get("date") or {}).get("date_to")
        as_of = fields.Date.to_date(date_to) if date_to else fields.Date.context_today(self)
        if not isinstance(as_of, date):
            as_of = fields.Date.context_today(self)
        return "%s %s %s %s" % (
            prefix,
            as_of.day,
            THAI_MONTHS[as_of.month - 1],
            as_of.year + 543,
        )

    def _vpk_xlsx_last_col(self, options):
        """Last column index of the exported table, so the title stays centered over it."""
        lines = self._filter_out_folded_children(
            self.with_context(no_format=True)._get_lines(options)
        )
        has_account = any(
            self._get_model_info_from_id(line.get("id"))[0] == "account.account"
            for line in lines
        )
        # Optional code column, the line-name column, then one cell per figure column.
        last_col = (1 if has_account else 0) + len(options.get("columns") or [])
        if options.get("show_horizontal_group_total"):
            last_col += 1
        if options.get("column_percent_comparison") == "growth":
            last_col += 1
        return last_col
