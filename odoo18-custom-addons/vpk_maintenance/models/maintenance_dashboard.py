# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.misc import formatLang

TZ = ZoneInfo("Asia/Bangkok")
MONTHS = (
    "",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
)
SUB_STATES = (
    ("waiting_assessment", "รอประเมิน", "orange"),
    ("assessed", "ประเมินแล้ว", "blue"),
    ("repairing", "กำลังซ่อม", "blue"),
    ("waiting_parts", "รออะไหล่", "orange"),
    ("waiting_disposal", "รอจำหน่าย", "red"),
    ("repaired", "ซ่อมเสร็จ", "green"),
)
OPEN_STATES = [key for key, _label, _tone in SUB_STATES if key != "repaired"]
STATE_TONE = {key: tone for key, _label, tone in SUB_STATES}


class MaintenanceRequestDashboard(models.Model):
    _inherit = "maintenance.request"

    @api.model
    def get_maintenance_dashboard(self, period="7d"):
        """งานซ่อมที่ยังไม่ปิด และความเคลื่อนไหวของสถานะในช่วงที่เลือก"""
        period = period if period in ("today", "7d", "30d") else "7d"
        now_local, start_utc, start_date = self._maint_bounds(period)
        start_utc_s = fields.Datetime.to_string(start_utc)
        start_date_s = fields.Date.to_string(start_date)
        now_s = fields.Datetime.to_string(fields.Datetime.now())
        company = self._maint_company_domain()
        labels = dict(self._fields["sub_state"]._description_selection(self.env))
        open_domain = company + [
            ("archive", "=", False),
            ("sub_state", "in", OPEN_STATES),
        ]
        repaired_domain = company + [
            "|",
            ("sub_state", "=", "repaired"),
            ("stage_id.done", "=", True),
            "|",
            ("write_date", ">=", start_utc_s),
            ("close_date", ">=", start_date_s),
        ]
        created_domain = company + [("create_date", ">=", start_utc_s)]
        overdue_domain = open_domain + [
            ("schedule_date", "!=", False),
            ("schedule_date", "<", now_s),
        ]

        counts = self._maint_state_counts(open_domain)
        open_count = sum(counts.get(key, 0) for key in OPEN_STATES)
        repaired_count = self.search_count(repaired_domain)
        created_count = self.search_count(created_domain)
        parts_amount = self._maint_parts_amount(company, start_utc_s)
        movement = self._maint_movement(company, start_utc, now_local, labels)
        period_label = {"today": "วันนี้", "7d": "7 วัน", "30d": "30 วัน"}[period]

        flow = []
        for key, label, tone in SUB_STATES:
            if key == "repaired":
                count = repaired_count
                domain = repaired_domain
                title = "ซ่อมเสร็จในช่วงนี้"
            else:
                count = counts.get(key, 0)
                domain = open_domain + [("sub_state", "=", key)]
                title = label
            flow.append(self._maint_step(key, label, count, tone, title, domain))

        return {
            "period": period,
            "date_label": self._maint_thai_date(now_local),
            "updated_at": now_local.strftime("%H:%M"),
            "period_label": period_label,
            "kpis": [
                self._maint_kpi("open", "งานค้าง", open_count, "เรื่อง", "ยังไม่ปิดงาน", "alert" if open_count else "green", self._maint_action("งานซ่อมที่ยังไม่ปิด", open_domain)),
                self._maint_kpi("assess", "รอประเมิน", counts.get("waiting_assessment", 0), "เรื่อง", "ยังไม่ประเมิน", "orange", self._maint_action("รอประเมิน", open_domain + [("sub_state", "=", "waiting_assessment")])),
                self._maint_kpi("repairing", "กำลังซ่อม", counts.get("repairing", 0), "เรื่อง", "อยู่ในระหว่างซ่อม", "blue", self._maint_action("กำลังซ่อม", open_domain + [("sub_state", "=", "repairing")])),
                self._maint_kpi("parts", "รออะไหล่", counts.get("waiting_parts", 0), "เรื่อง", "ซ่อมค้างเพราะอะไหล่", "orange", self._maint_action("รออะไหล่", open_domain + [("sub_state", "=", "waiting_parts")])),
                self._maint_kpi("done", "ซ่อมเสร็จ", repaired_count, "เรื่อง", period_label, "green", self._maint_action("ซ่อมเสร็จในช่วงนี้", repaired_domain)),
                self._maint_kpi("value", "มูลค่าอะไหล่", self._maint_money(parts_amount), "ที่จ่ายแล้ว", period_label, "blue", self._maint_action("งานที่มีการเบิกอะไหล่", company + [("parts_move_ids.state", "=", "done"), ("parts_move_ids.date", ">=", start_utc_s)]), money=True),
            ],
            "flow": flow,
            "teams": self._maint_teams(open_domain),
            "departments": self._maint_departments(open_domain),
            "movement": movement,
            "movement_count": len(movement),
            "jobs": self._maint_jobs(open_domain, now_local, labels),
            "alerts": self._maint_alerts(overdue_domain, open_domain),
        }

    @api.model
    def get_maintenance_mobile_home(self, period="today"):
        data = self.get_maintenance_dashboard(period)
        return {
            "period": data["period"],
            "period_label": data["period_label"],
            "date_label": data["date_label"],
            "updated_at": data["updated_at"],
            "kpis": [
                {
                    "key": kpi["key"],
                    "label": kpi["label"],
                    "value": kpi["value"],
                    "hint": kpi["hint"],
                    "foot": kpi["foot"],
                    "tone": kpi["tone"],
                    "money": kpi["money"],
                    "filter": {
                        "open": "open",
                        "assess": "waiting_assessment",
                        "repairing": "repairing",
                        "parts": "waiting_parts",
                        "done": "repaired",
                        "value": "with_parts",
                    }.get(kpi["key"], "open"),
                }
                for kpi in data["kpis"]
            ],
            "jobs": data["jobs"],
            "alerts": [
                {
                    "id": alert["id"],
                    "name": alert["name"],
                    "message": alert["message"],
                    "detail": alert["detail"],
                }
                for alert in data["alerts"]
            ],
        }

    def _maint_company_domain(self):
        company = self.env.company
        return ["|", ("company_id", "=", False), ("company_id", "=", company.id)]

    def _maint_bounds(self, period):
        now_local = datetime.now(TZ)
        days = {"today": 0, "7d": 6, "30d": 29}[period]
        start_local = (now_local - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        return now_local, start_utc, start_local.date()

    def _maint_thai_date(self, value):
        return "%s %s %s" % (value.day, MONTHS[value.month], value.year + 543)

    def _maint_when(self, value, now_local):
        if not value:
            return ""
        local = value.replace(tzinfo=timezone.utc).astimezone(TZ)
        if local.date() == now_local.date():
            return "วันนี้ %s" % local.strftime("%H:%M")
        return "%s %s %s" % (local.day, MONTHS[local.month], str(local.year + 543)[-2:])

    def _maint_money(self, amount):
        return formatLang(self.env, amount or 0.0, currency_obj=self.env.company.currency_id)

    def _maint_action(self, name, domain):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "maintenance.request",
            "view_mode": "list,form",
            "views": [[False, "list"], [False, "form"]],
            "domain": domain,
            "target": "current",
        }

    def _maint_kpi(self, key, label, value, hint, foot, tone, action, money=False):
        return {
            "key": key,
            "label": label,
            "value": value,
            "hint": hint,
            "foot": foot,
            "tone": tone,
            "money": money,
            "action": action,
        }

    def _maint_step(self, key, label, count, tone, title, domain):
        return {
            "key": key,
            "label": label,
            "count": count,
            "tone": tone if count else "gray",
            "action": self._maint_action(title, domain),
        }

    def _maint_state_counts(self, open_domain):
        grouped = self._read_group(open_domain, ["sub_state"], ["__count"])
        return {state or "": count for state, count in grouped}

    def _maint_parts_amount(self, company_domain, start_utc_s):
        requests = self.search(company_domain)
        if not requests:
            return 0.0
        try:
            moves = self.env["stock.move"].sudo().search([
                ("maintenance_request_id", "in", requests.ids),
                ("state", "=", "done"),
                ("date", ">=", start_utc_s),
            ])
        except AccessError:
            return 0.0
        return sum(moves.mapped("parts_value"))

    def _maint_teams(self, open_domain):
        grouped = self._read_group(open_domain, ["maintenance_team_id", "sub_state"], ["__count"])
        by_team = {}
        for team, state, count in grouped:
            bucket = by_team.setdefault(team.id if team else 0, {})
            bucket[state] = count
        company = self.env.company
        teams = self.env["maintenance.team"].search([
            "|", ("company_id", "=", False), ("company_id", "=", company.id),
        ], order="id")
        rows = [self._maint_team_row(team.id, team.name, by_team.get(team.id, {}), open_domain) for team in teams]
        if by_team.get(0):
            rows.append(self._maint_team_row(0, "ไม่ระบุทีม", by_team[0], open_domain))
        rows.sort(key=lambda row: (-row["open"], row["name"]))
        return rows

    def _maint_team_row(self, team_id, name, states, open_domain):
        open_count = sum(states.get(key, 0) for key in OPEN_STATES)
        segments = []
        for key, label, tone in SUB_STATES:
            if key == "repaired":
                continue
            count = states.get(key, 0)
            segments.append({
                "key": key,
                "label": label,
                "count": count,
                "tone": tone,
                "width": round((count * 100.0 / open_count), 1) if open_count else 0,
            })
        domain = open_domain + [("maintenance_team_id", "=", team_id or False)]
        return {
            "id": team_id,
            "name": name,
            "open": open_count,
            "segments": segments,
            "action": self._maint_action(name, domain),
        }

    def _maint_departments(self, open_domain):
        grouped = self._read_group(open_domain, ["department_id"], ["__count"])
        rows = []
        for department, count in grouped:
            if not department:
                continue
            rows.append({
                "id": department.id,
                "name": department.name,
                "count": count,
                "action": self._maint_action(
                    department.name,
                    open_domain + [("department_id", "=", department.id)],
                ),
            })
        rows.sort(key=lambda row: (-row["count"], row["name"]))
        return rows

    def _maint_jobs(self, open_domain, now_local, labels):
        requests = self.search(open_domain, order="write_date desc, id desc", limit=8)
        return [self._maint_job_row(request, now_local, labels) for request in requests]

    def _maint_job_row(self, request, now_local, labels):
        state = request.sub_state
        return {
            "id": request.id,
            "model": "maintenance.request",
            "name": request.name or "",
            "team": request.maintenance_team_id.name or "ไม่ระบุทีม",
            "assignee": request.user_id.name or "ยังไม่มอบหมาย",
            "equipment": request.equipment_id.sudo().display_name or "",
            "status": labels.get(state, state or ""),
            "tone": STATE_TONE.get(state, "blue"),
            "when": self._maint_when(request.write_date, now_local),
        }

    def _maint_movement(self, company_domain, start_utc, now_local, labels):
        requests = self.search(company_domain)
        if not requests:
            return []
        allowed = set(requests.ids)
        created = self.search(company_domain + [("create_date", ">=", fields.Datetime.to_string(start_utc))], order="create_date desc", limit=20)
        initial = self._maint_initial_states(created)
        events = []
        for request in created:
            state = initial.get(request.id) or labels.get(request.sub_state, "")
            events.append((request.create_date, {
                "key": "open-%s" % request.id,
                "id": request.id,
                "model": "maintenance.request",
                "name": request.name or "",
                "team": request.maintenance_team_id.name or "",
                "before": "",
                "after": "เปิดคำขอ",
                "status": state,
                "tone": "blue",
                "when": self._maint_when(request.create_date, now_local),
            }))
        events.extend(self._maint_tracking_events(allowed, start_utc, now_local))
        events.sort(key=lambda item: item[0] or datetime.min, reverse=True)
        rows = []
        seen = set()
        for _stamp, row in events:
            if row["key"] in seen:
                continue
            seen.add(row["key"])
            rows.append(row)
            if len(rows) == 12:
                break
        return rows

    def _maint_initial_states(self, requests):
        """สถานะแรกของคำขอที่เปิดในช่วงนี้ จากค่าเดิมของประวัติสถานะ"""
        if not requests:
            return {}
        field = self.env["ir.model.fields"].sudo()._get("maintenance.request", "sub_state")
        if not field:
            return {}
        messages = self.env["mail.message"].sudo().search([
            ("model", "=", "maintenance.request"),
            ("res_id", "in", requests.ids),
        ])
        trackings = self.env["mail.tracking.value"].sudo().search([
            ("mail_message_id", "in", messages.ids),
            ("field_id", "=", field.id),
        ], order="id")
        initial = {}
        for tracking in trackings:
            res_id = tracking.mail_message_id.res_id
            if res_id not in initial and tracking.old_value_char:
                initial[res_id] = tracking.old_value_char
        return initial

    def _maint_tracking_events(self, allowed_ids, start_utc, now_local):
        fields_to_follow = self.env["ir.model.fields"].sudo().search([
            ("model", "=", "maintenance.request"),
            ("name", "in", ("sub_state", "stage_id")),
        ])
        if not fields_to_follow or not allowed_ids:
            return []
        messages = self.env["mail.message"].sudo().search([
            ("model", "=", "maintenance.request"),
            ("res_id", "in", list(allowed_ids)),
            ("date", ">=", fields.Datetime.to_string(start_utc)),
        ])
        trackings = self.env["mail.tracking.value"].sudo().search([
            ("mail_message_id", "in", messages.ids),
            ("field_id", "in", fields_to_follow.ids),
        ], order="id desc")
        field_names = {field.id: field.name for field in fields_to_follow}
        request_map = {request.id: request for request in self.browse(list(allowed_ids)).exists()}
        events = []
        for tracking in trackings:
            message = tracking.mail_message_id
            request = request_map.get(message.res_id)
            if not request:
                continue
            field_name = field_names.get(tracking.field_id.id)
            new_label = tracking.new_value_char or ""
            old_label = tracking.old_value_char or ""
            if field_name == "sub_state":
                tone = next((tone for _key, label, tone in SUB_STATES if label == new_label or new_label.startswith(label)), "blue")
            else:
                tone = "green" if new_label in ("ซ่อมแล้ว", "Repaired") else "blue"
            events.append((message.date, {
                "key": "track-%s" % tracking.id,
                "id": request.id,
                "model": "maintenance.request",
                "name": request.name or "",
                "team": request.maintenance_team_id.name or "",
                "before": old_label,
                "after": new_label or "อัปเดตสถานะ",
                "status": new_label,
                "tone": tone,
                "when": self._maint_when(message.date, now_local),
            }))
        return events

    def _maint_alerts(self, overdue_domain, open_domain):
        alerts = []
        for request in self.search(overdue_domain, order="schedule_date, id", limit=4):
            alerts.append(self._maint_alert(request, "เกินกำหนดตามตาราง", request.maintenance_team_id.name or ""))
        for request in self.search(open_domain + [("sub_state", "=", "waiting_parts")], order="write_date, id", limit=4):
            alerts.append(self._maint_alert(request, "รออะไหล่", request.equipment_id.sudo().display_name or ""))
        for request in self.search(open_domain + [("sub_state", "=", "waiting_assessment"), ("user_id", "=", False)], order="request_date, id", limit=3):
            alerts.append(self._maint_alert(request, "รอมอบหมายช่าง", request.department_id.name or ""))
        for request in self.search(open_domain + [("sub_state", "=", "waiting_disposal")], order="write_date, id", limit=3):
            alerts.append(self._maint_alert(request, "รอแทงจำหน่าย", request.equipment_id.sudo().display_name or ""))
        unique = []
        seen = set()
        for alert in alerts:
            key = (alert["id"], alert["message"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(alert)
            if len(unique) == 8:
                break
        return unique

    def _maint_alert(self, request, message, detail):
        return {
            "id": request.id,
            "model": "maintenance.request",
            "name": request.name or "",
            "message": message,
            "detail": detail or "",
            "action_label": "เปิดคำขอ",
        }
