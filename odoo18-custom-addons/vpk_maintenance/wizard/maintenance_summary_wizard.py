# -*- coding: utf-8 -*-
from datetime import date, timezone
from zoneinfo import ZoneInfo

from odoo import _, api, fields, models
from odoo.exceptions import UserError

THAI_MONTHS = (
    "",
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
THAI_MONTH_ABBR = (
    "",
    "มค.",
    "กพ.",
    "มีค.",
    "เมย.",
    "พค.",
    "มิย.",
    "กค.",
    "สค.",
    "กย.",
    "ตค.",
    "พย.",
    "ธค.",
)
MAX_MONTHS = 24


class MaintenanceRequestSummaryWizard(models.TransientModel):
    _name = "maintenance.request.summary.wizard"
    _description = "สรุปใบงานช่างซ่อมบำรุง"

    date_from = fields.Date(string="ตั้งแต่วันที่", required=True, default=lambda self: self._default_date_from())
    date_to = fields.Date(string="ถึงวันที่", required=True, default=fields.Date.context_today)
    team_id = fields.Many2one(
        comodel_name="maintenance.team",
        string="ทีม",
        help="เว้นว่างเพื่อรวมทุกทีม",
    )

    @api.model
    def _default_date_from(self):
        today = fields.Date.context_today(self)
        if today.month >= 10:
            return today.replace(month=10, day=1)
        return today.replace(year=today.year - 1, month=10, day=1)

    def _report_font_css(self):
        return self.env["maintenance.request"]._report_font_css()

    def _iter_months(self, date_from, date_to):
        cursor = date(date_from.year, date_from.month, 1)
        last = date(date_to.year, date_to.month, 1)
        months = []
        while cursor <= last:
            months.append(cursor)
            if len(months) > MAX_MONTHS:
                raise UserError(_("เลือกช่วงวันที่ได้ไม่เกิน %s เดือน") % MAX_MONTHS)
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return months

    def _fiscal_year_be(self, day):
        year = day.year + 543
        if day.month >= 10:
            year += 1
        return year

    def _prepare_summary(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("วันที่เริ่มต้นต้องไม่เกินวันที่สิ้นสุด"))
        months = self._iter_months(self.date_from, self.date_to)
        month_index = {(day.year, day.month): index for index, day in enumerate(months)}
        company = self.env.company
        domain = [
            ("archive", "=", False),
            ("request_date", ">=", self.date_from),
            ("request_date", "<=", self.date_to),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company.id),
        ]
        if self.team_id:
            domain.append(("maintenance_team_id", "=", self.team_id.id))
            teams = self.team_id
        else:
            teams = self.env["maintenance.team"].search(
                ["|", ("company_id", "=", False), ("company_id", "=", company.id)],
                order="name",
            )
        requests = self.env["maintenance.request"].search(domain)
        counts = {}
        unassigned = [0] * len(months)
        unassigned_total = 0
        for request in requests:
            day = request.request_date
            if not day:
                continue
            index = month_index.get((day.year, day.month))
            if index is None:
                continue
            team = request.maintenance_team_id
            if not team:
                unassigned[index] += 1
                unassigned_total += 1
                continue
            bucket = counts.setdefault(team.id, [0] * len(months))
            bucket[index] += 1

        known_ids = set(teams.ids)
        extra_teams = self.env["maintenance.team"].browse(
            [team_id for team_id in counts if team_id not in known_ids]
        ).sorted(key=lambda team: team.name or "")
        teams = teams + extra_teams
        rows = []
        for team in teams:
            cells = counts.get(team.id, [0] * len(months))
            rows.append({
                "name": team.name,
                "cells": [value or "" for value in cells],
                "total": sum(cells),
            })
        if not self.team_id and unassigned_total:
            rows.append({
                "name": "ไม่ระบุทีม",
                "cells": [value or "" for value in unassigned],
                "total": unassigned_total,
            })
        for sequence, row in enumerate(rows, start=1):
            row["sequence"] = sequence

        column_totals = [0] * len(months)
        for request in requests:
            day = request.request_date
            if not day:
                continue
            index = month_index.get((day.year, day.month))
            if index is not None:
                column_totals[index] += 1

        now = fields.Datetime.now().replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Asia/Bangkok"))
        return {
            "hospital": company.name or "",
            "fiscal_year": self._fiscal_year_be(self.date_from),
            "period": "ตั้งแต่ เดือน %s %s - %s %s" % (
                THAI_MONTHS[self.date_from.month],
                self.date_from.year + 543,
                THAI_MONTHS[self.date_to.month],
                self.date_to.year + 543,
            ),
            "months": [
                {"label": "%s%s" % (THAI_MONTH_ABBR[day.month], (day.year + 543) % 100)}
                for day in months
            ],
            "rows": rows,
            "column_totals": column_totals,
            "grand_total": sum(column_totals),
            "printed_on": "สรุป ณ วันที่ %02d/%d/%s เวลา %02d.%02dน." % (
                now.day,
                now.month,
                now.year + 543,
                now.hour,
                now.minute,
            ),
            "team_name": self.team_id.name or "",
        }

    def action_print(self):
        self.ensure_one()
        self._prepare_summary()
        return self.env.ref(
            "vpk_maintenance.action_report_maintenance_summary"
        ).report_action(self)
