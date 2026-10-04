# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models


TH_MONTHS = [
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
]
TH_MONTHS_FULL = [
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
]
EXPENSE_TYPES = [
    ("personnel", "งบบุคลากร"),
    ("operating", "งบดำเนินงาน"),
    ("asset", "งบลงทุน - ครุภัณฑ์"),
    ("construction", "งบลงทุน - สิ่งก่อสร้าง"),
    ("subsidy", "งบเงินอุดหนุน"),
    ("other", "งบรายจ่ายอื่น"),
]


class Budget(models.Model):
    _inherit = "budget.budget"

    @api.model
    def get_annual_expenditure_overview(self, fiscal_year=None, fund_source_id=None):
        """Hospital annual budget monitoring dashboard."""
        fiscal_year, year_options, selected_budgets = self._get_fiscal_year_budgets(
            fiscal_year
        )
        lines = selected_budgets.mapped("budget_line")
        fund_sources = self._overview_fund_sources(lines)
        if fund_source_id:
            lines = lines.filtered(
                lambda line: line.fund_source_id.id == int(fund_source_id)
            )

        period_start, period_end = self._overview_period(fiscal_year, selected_budgets)
        today = fields.Date.context_today(self)
        as_of = min(max(today, period_start), period_end) if period_start and period_end else today
        months_elapsed = self._months_elapsed(period_start, as_of)
        remaining_days = max((period_end - as_of).days, 0) if period_end else 0
        month_labels = [
            TH_MONTHS[(period_start.month - 1 + index) % 12] for index in range(12)
        ] if period_start else list(TH_MONTHS)

        committed_map, committed_monthly, po_count = self._committed_maps(lines, period_start)
        allocated = sum(lines.mapped("planned_amount"))
        actual = sum(self._line_spent_amount(line) for line in lines)
        committed = sum(committed_map.values())
        remaining = allocated - actual - committed
        plan_pct = (months_elapsed / 12.0 * 100.0) if months_elapsed else 0.0
        actual_pct = self._pct(actual, allocated)
        committed_pct = self._pct(committed, allocated)
        remaining_pct = self._pct(remaining, allocated)
        vs_plan = actual_pct - plan_pct

        prior_allocated, prior_actual = self._prior_year_totals(fiscal_year, fund_source_id)
        yoy_allocated_pct = self._pct(allocated - prior_allocated, prior_allocated) if prior_allocated else 0.0
        yoy_actual_pct = self._pct(actual - prior_actual, prior_actual) if prior_actual else 0.0

        type_map = {
            key: {
                "key": key,
                "name": label,
                "allocated": 0.0,
                "actual": 0.0,
                "committed": 0.0,
            }
            for key, label in EXPENSE_TYPES
        }
        department_map = {}
        for line in lines:
            planned = line.planned_amount or 0.0
            spent = self._line_spent_amount(line)
            line_committed = committed_map.get(line.id, 0.0)
            type_key, _type_label = self._expense_type_meta(line)
            type_vals = type_map[type_key]
            type_vals["allocated"] += planned
            type_vals["actual"] += spent
            type_vals["committed"] += line_committed

            department = line.analytic_account_id
            dept_key = department.id if department else 0
            dept_vals = department_map.setdefault(
                dept_key,
                {
                    "id": dept_key,
                    "name": department.name if department else "ไม่ระบุหน่วยงาน",
                    "allocated": 0.0,
                    "actual": 0.0,
                    "committed": 0.0,
                },
            )
            dept_vals["allocated"] += planned
            dept_vals["actual"] += spent
            dept_vals["committed"] += line_committed

        operating_amt = type_map["personnel"]["allocated"] + type_map["operating"]["allocated"]
        investment_amt = (
            type_map["asset"]["allocated"] + type_map["construction"]["allocated"]
        )
        operating_pct = self._pct(operating_amt, allocated)
        investment_pct = self._pct(investment_amt, allocated)

        department_rows = []
        for vals in sorted(
            department_map.values(), key=lambda item: item["allocated"], reverse=True
        )[:8]:
            usage_pct = self._pct(vals["actual"], vals["allocated"])
            tone = "warn" if usage_pct < max(plan_pct - 10.0, 0.0) else "ok"
            department_rows.append(
                {
                    "id": vals["id"],
                    "name": vals["name"],
                    "allocated": vals["allocated"],
                    "actual": vals["actual"],
                    "committed": vals["committed"],
                    "remaining": vals["allocated"] - vals["actual"] - vals["committed"],
                    "usage_pct": usage_pct,
                    "tone": tone,
                }
            )

        expense_types = []
        for key, label in EXPENSE_TYPES:
            vals = type_map[key]
            row_remaining = vals["allocated"] - vals["actual"] - vals["committed"]
            usage_pct = self._pct(vals["actual"], vals["allocated"])
            status_label, status_tone = self._usage_status(usage_pct, plan_pct)
            expense_types.append(
                {
                    "key": key,
                    "name": label,
                    "allocated": vals["allocated"],
                    "committed": vals["committed"],
                    "actual": vals["actual"],
                    "remaining": row_remaining,
                    "usage_pct": usage_pct,
                    "status_label": status_label,
                    "status_tone": status_tone,
                }
            )

        monthly_actual = self._monthly_actual(lines, period_start, period_end)
        cumulative_actual = []
        cumulative_committed = []
        cumulative_plan = []
        running_actual = 0.0
        running_committed = 0.0
        running_plan = 0.0
        monthly_plan = [(allocated / 12.0) if allocated else 0.0] * 12
        max_value = allocated or 1.0
        current_index = max(min(months_elapsed - 1, 11), 0)
        for index in range(12):
            running_actual += monthly_actual[index]
            running_committed += committed_monthly[index]
            running_plan += monthly_plan[index]
            max_value = max(max_value, running_actual, running_committed, running_plan)
            cumulative_actual.append(
                {"label": month_labels[index], "amount": running_actual}
            )
            cumulative_committed.append(
                {"label": month_labels[index], "amount": running_committed}
            )
            cumulative_plan.append(
                {"label": month_labels[index], "amount": running_plan}
            )

        project_data = self._overview_projects(
            fiscal_year, lines, committed_map, plan_pct, fund_source_id
        )
        projects = project_data["items"]
        project_total = project_data["total"]
        alerts = self._overview_alerts(
            allocated=allocated,
            actual=actual,
            committed=committed,
            remaining=remaining,
            remaining_days=remaining_days,
            po_count=po_count,
            plan_pct=plan_pct,
            department_rows=department_rows,
            expense_types=expense_types,
            fiscal_year=fiscal_year,
        )
        expiring_count = sum(
            1
            for line in lines
            if (line.planned_amount or 0.0)
            - self._line_spent_amount(line)
            - committed_map.get(line.id, 0.0)
            > 0
            and self._pct(self._line_spent_amount(line), line.planned_amount or 0.0) < 50.0
        )

        company = self.env.company
        org_label = " | ".join(
            part
            for part in (
                company.name or "โรงพยาบาล",
                "กลุ่มงานการเงินและบัญชี",
            )
            if part
        )
        as_of_label = (
            f"ข้อมูล ณ {as_of.day} {TH_MONTHS_FULL[as_of.month - 1]} {as_of.year + 543}"
            f" · เดือนที่ {months_elapsed} จาก 12 · อ้างอิงข้อมูลจากระบบงบประมาณ"
        )
        fy_end_label = (
            f"{period_end.day} {TH_MONTHS_FULL[period_end.month - 1]} {int(fiscal_year)}"
            if period_end
            else f"30 กันยายน {fiscal_year}"
        )

        return {
            "fiscal_year": fiscal_year,
            "year_options": year_options or [fiscal_year],
            "fund_source_id": int(fund_source_id) if fund_source_id else 0,
            "fund_sources": fund_sources,
            "company_name": company.name or "โรงพยาบาล",
            "org_label": org_label,
            "as_of_label": as_of_label,
            "fy_end_label": fy_end_label,
            "months_elapsed": months_elapsed,
            "remaining_days": remaining_days,
            "allocated": allocated,
            "actual": actual,
            "committed": committed,
            "remaining": remaining,
            "actual_pct": actual_pct,
            "committed_pct": committed_pct,
            "remaining_pct": remaining_pct,
            "plan_pct": plan_pct,
            "vs_plan": vs_plan,
            "operating_pct": operating_pct,
            "investment_pct": investment_pct,
            "yoy_allocated_pct": yoy_allocated_pct,
            "yoy_actual_pct": yoy_actual_pct,
            "po_count": po_count,
            "expiring_count": expiring_count,
            "department_rows": department_rows,
            "expense_types": expense_types,
            "projects": projects,
            "project_total": project_total,
            "alerts": alerts,
            "trend": {
                "actual_points": cumulative_actual,
                "committed_points": cumulative_committed,
                "plan_points": cumulative_plan,
                "max": max_value or 1.0,
                "current_index": current_index,
                "q3_index": 8,
                "q3_pct": actual_pct,
            },
        }

    @api.model
    def _pct(self, part, whole):
        return (part / whole * 100.0) if whole else 0.0

    @api.model
    def _overview_period(self, fiscal_year, selected_budgets):
        date_from = min(selected_budgets.mapped("date_from")) if selected_budgets else False
        date_to = max(selected_budgets.mapped("date_to")) if selected_budgets else False
        if date_from and date_to:
            return date_from, date_to
        try:
            be = int(fiscal_year)
            ce = be - 543
            return date(ce - 1, 10, 1), date(ce, 9, 30)
        except (TypeError, ValueError):
            today = fields.Date.context_today(self)
            return date(today.year, 1, 1), date(today.year, 12, 31)

    @api.model
    def _months_elapsed(self, period_start, as_of):
        if not period_start or not as_of:
            return 1
        value = (as_of.year - period_start.year) * 12 + as_of.month - period_start.month + 1
        return max(1, min(value, 12))

    @api.model
    def _month_index(self, value, period_start):
        if not value or not period_start:
            return None
        day = value.date() if hasattr(value, "date") else value
        index = (day.year - period_start.year) * 12 + day.month - period_start.month
        if 0 <= index < 12:
            return index
        return None

    @api.model
    def _overview_fund_sources(self, lines):
        options = [{"id": 0, "name": "ทุกแหล่งเงิน"}]
        seen = set()
        for source in lines.mapped("fund_source_id"):
            if not source or source.id in seen:
                continue
            seen.add(source.id)
            options.append({"id": source.id, "name": source.name})
        if len(options) == 1:
            for source in self.env["vpk.budget.fund.source"].search([]):
                options.append({"id": source.id, "name": source.name})
        return options

    @api.model
    def _expense_type_meta(self, line):
        post = line.general_budget_id
        name = (post.name or "").strip()
        section = post.section_key if post else False
        text = name
        if any(
            token in text
            for token in ("บุคลากร", "เงินเดือน", "ค่าจ้าง", "ค่าตอบแทน", "สวัสดิการ")
        ):
            return "personnel", "งบบุคลากร"
        if "อุดหนุน" in text:
            return "subsidy", "งบเงินอุดหนุน"
        if section == "asset" or "ครุภัณฑ์" in text:
            return "asset", "งบลงทุน - ครุภัณฑ์"
        if section == "construction" or "ก่อสร้าง" in text:
            return "construction", "งบลงทุน - สิ่งก่อสร้าง"
        if section == "material" or any(
            token in text
            for token in ("วัสดุ", "ดำเนินงาน", "ค่าใช้สอย", "สาธารณูปโภค", "ยา", "เวชภัณฑ์")
        ):
            return "operating", "งบดำเนินงาน"
        if section == "project":
            return "other", "งบรายจ่ายอื่น"
        return "other", "งบรายจ่ายอื่น"

    @api.model
    def _usage_status(self, usage_pct, plan_pct):
        if usage_pct >= 90.0:
            return "ใกล้เต็ม", "danger"
        if usage_pct < max(plan_pct - 8.0, 0.0):
            return "ต้องเร่งเบิก", "warn"
        return "ตามเป้า", "ok"

    @api.model
    def _committed_maps(self, lines, period_start):
        amounts = {line_id: 0.0 for line_id in lines.ids}
        monthly = [0.0] * 12
        if not lines:
            return amounts, monthly, 0
        po_lines = self.env["purchase.order.line"].sudo().search(
            [
                ("budget_line_id", "in", lines.ids),
                ("order_id.state", "in", ("purchase", "done")),
            ]
        )
        seen_po = set()
        for po_line in po_lines:
            amount = po_line._get_budget_open_committed_amount_company()
            line_id = po_line.budget_line_id.id
            amounts[line_id] = amounts.get(line_id, 0.0) + amount
            order = po_line.order_id
            if amount > 0 and order.id not in seen_po:
                seen_po.add(order.id)
            if amount:
                index = self._month_index(
                    order.date_approve or order.date_order, period_start
                )
                if index is not None:
                    monthly[index] += amount
        return amounts, monthly, len(seen_po)

    @api.model
    def _monthly_actual(self, lines, period_start, period_end):
        monthly = [0.0] * 12
        analytic_ids = lines.mapped("analytic_account_id").ids
        if not (period_start and period_end and analytic_ids):
            return monthly
        analytic_lines = self.env["account.analytic.line"].search(
            [
                ("date", ">=", period_start),
                ("date", "<=", period_end),
                ("account_id", "in", analytic_ids),
            ]
        )
        for analytic_line in analytic_lines:
            amount = analytic_line.amount or 0.0
            spent = abs(amount) if amount < 0 else 0.0
            if not spent:
                continue
            index = self._month_index(analytic_line.date, period_start)
            if index is not None:
                monthly[index] += spent
        return monthly

    @api.model
    def _prior_year_totals(self, fiscal_year, fund_source_id=None):
        if not str(fiscal_year).isdigit():
            return 0.0, 0.0
        _year, _options, prior_budgets = self._get_fiscal_year_budgets(str(int(fiscal_year) - 1))
        prior_lines = prior_budgets.mapped("budget_line")
        if fund_source_id:
            prior_lines = prior_lines.filtered(
                lambda line: line.fund_source_id.id == int(fund_source_id)
            )
        allocated = sum(prior_lines.mapped("planned_amount"))
        actual = sum(self._line_spent_amount(line) for line in prior_lines)
        return allocated, actual

    @api.model
    def _overview_projects(self, fiscal_year, lines, committed_map, plan_pct, fund_source_id=None):
        request_domain = [
            ("request_id.fiscal_year", "=", fiscal_year),
            ("request_id.state", "not in", ("rejected",)),
            ("section_key", "in", ("asset", "construction", "project")),
        ]
        if fund_source_id:
            request_domain.append(("request_id.fund_source_id", "=", int(fund_source_id)))
        request_lines = self.env["departmental.budget.request.line"].search(
            request_domain, order="total_amount desc, id desc", limit=40
        )
        line_by_request = {}
        for line in lines:
            if line.request_line_id:
                line_by_request.setdefault(line.request_line_id.id, self.env["budget.lines"])
                line_by_request[line.request_line_id.id] |= line

        projects = []
        if request_lines:
            for request_line in request_lines:
                linked = line_by_request.get(
                    request_line.id, self.env["budget.lines"]
                )
                allocated = (
                    sum(linked.mapped("planned_amount"))
                    if linked
                    else (request_line.total_amount or 0.0)
                )
                actual = sum(self._line_spent_amount(line) for line in linked)
                committed = sum(committed_map.get(line.id, 0.0) for line in linked)
                usage_pct = self._pct(actual, allocated)
                name = (request_line.item_name or request_line.budget_post_id.name or "").strip()
                if not name:
                    continue
                subtitle = ""
                if request_line.requested_quantity:
                    unit = request_line.unit_name or "รายการ"
                    subtitle = f"{request_line.requested_quantity:g} {unit}"
                elif request_line.section_key == "construction":
                    subtitle = request_line.construction_location or "งานก่อสร้าง"
                department = (
                    request_line.request_id.analytic_account_id.name
                    if request_line.request_id.analytic_account_id
                    else ""
                )
                projects.append(
                    {
                        "id": request_line.id,
                        "name": name,
                        "subtitle": subtitle,
                        "department": department,
                        "allocated": allocated,
                        "actual": actual,
                        "committed": committed,
                        "usage_pct": usage_pct,
                        "status_label": self._project_status(
                            actual, committed, usage_pct, request_line.section_key
                        ),
                        "status_tone": "warn"
                        if usage_pct < max(plan_pct - 10.0, 0.0) or (not actual and not committed)
                        else "ok",
                    }
                )
        else:
            project_map = {}
            for line in lines:
                type_key, _label = self._expense_type_meta(line)
                if type_key not in ("asset", "construction", "other"):
                    continue
                post = line.general_budget_id
                key = post.id if post else line.id
                vals = project_map.setdefault(
                    key,
                    {
                        "id": key,
                        "name": post.name if post else "โครงการลงทุน",
                        "department": line.analytic_account_id.name or "",
                        "allocated": 0.0,
                        "actual": 0.0,
                        "committed": 0.0,
                    },
                )
                vals["allocated"] += line.planned_amount or 0.0
                vals["actual"] += self._line_spent_amount(line)
                vals["committed"] += committed_map.get(line.id, 0.0)
            for vals in sorted(
                project_map.values(), key=lambda item: item["allocated"], reverse=True
            ):
                usage_pct = self._pct(vals["actual"], vals["allocated"])
                projects.append(
                    {
                        "id": vals["id"],
                        "name": vals["name"],
                        "subtitle": vals["department"],
                        "department": vals["department"],
                        "allocated": vals["allocated"],
                        "actual": vals["actual"],
                        "committed": vals["committed"],
                        "usage_pct": usage_pct,
                        "status_label": self._project_status(
                            vals["actual"], vals["committed"], usage_pct, "asset"
                        ),
                        "status_tone": "warn"
                        if usage_pct < max(plan_pct - 10.0, 0.0)
                        else "ok",
                    }
                )
        return {
            "items": projects[:5],
            "total": len(projects),
        }

    @api.model
    def _project_status(self, actual, committed, usage_pct, section_key):
        if usage_pct >= 90.0:
            return "ใกล้ครบวงเงิน"
        if actual and section_key == "construction":
            return "อยู่ระหว่างก่อสร้าง"
        if committed and not actual:
            return "รอส่งมอบ / สัญญา"
        if actual:
            return "มีความคืบหน้า"
        return "รอจัดซื้อ"

    @api.model
    def _overview_alerts(
        self,
        allocated,
        actual,
        committed,
        remaining,
        remaining_days,
        po_count,
        plan_pct,
        department_rows,
        expense_types,
        fiscal_year,
    ):
        alerts = []
        if committed > 0:
            alerts.append(
                {
                    "tone": "warn",
                    "title": "ก่อหนี้ผูกพัน ยังไม่ได้ตั้งเจ้าหนี้",
                    "detail": f"PO / สัญญาที่ยังไม่เบิกจ่าย {po_count} ฉบับ",
                    "badge": "รอเบิกจ่าย",
                    "amount": committed,
                }
            )
        if remaining_days <= 90 and remaining > 0:
            alerts.append(
                {
                    "tone": "warn",
                    "title": f"คงเหลือต้องเบิกก่อนสิ้นปีงบประมาณ {remaining_days} วัน",
                    "detail": f"วงเงินคงเหลือถึง 30 ก.ย. {fiscal_year}",
                    "badge": "ใกล้สิ้นปี",
                    "amount": remaining,
                }
            )
        for row in department_rows:
            if row["tone"] != "warn":
                continue
            alerts.append(
                {
                    "tone": "danger" if row["usage_pct"] < max(plan_pct - 20.0, 0.0) else "warn",
                    "title": f"{row['name']} เบิกจ่าย {row['usage_pct']:.0f}%",
                    "detail": f"ต่ำกว่าเป้าสิ้นงวด {plan_pct:.0f}% ของวงเงินที่ได้รับ",
                    "badge": "ต้องเร่งเบิก",
                    "amount": row["remaining"],
                }
            )
            if len(alerts) >= 5:
                break
        personnel = next(
            (item for item in expense_types if item["key"] == "personnel"), None
        )
        if personnel and personnel["remaining"] > 0 and personnel["usage_pct"] < plan_pct:
            alerts.append(
                {
                    "tone": "ok",
                    "title": f"งบบุคลากรคงเหลือ {personnel['remaining'] / 1000000:.2f} ล้านบาท",
                    "detail": "ยังเบิกจ่ายไม่ถึงเป้าตามช่วงเวลาของปีงบประมาณ",
                    "badge": "คงที่ตามแผน",
                    "amount": personnel["remaining"],
                }
            )
        construction = next(
            (item for item in expense_types if item["key"] == "construction"), None
        )
        if construction and construction["remaining"] > 0:
            alerts.append(
                {
                    "tone": "warn",
                    "title": "งานก่อสร้างยังเบิกจ่ายไม่ครบวงเงิน",
                    "detail": "ติดตามสัญญาและงวดงานเพื่อเร่งเบิกก่อนสิ้นปี",
                    "badge": "รอตรวจรับ",
                    "amount": construction["remaining"],
                }
            )
        seen = set()
        unique = []
        for alert in alerts:
            key = alert["title"]
            if key in seen:
                continue
            seen.add(key)
            unique.append(alert)
            if len(unique) >= 5:
                break
        if not unique and allocated:
            unique.append(
                {
                    "tone": "ok",
                    "title": "สถานะงบประมาณอยู่ในเกณฑ์ควบคุม",
                    "detail": f"เบิกจ่ายแล้ว {self._pct(actual, allocated):.1f}% ของวงเงินที่ได้รับจัดสรร",
                    "badge": "ตามเป้า",
                    "amount": remaining,
                }
            )
        return unique

    @api.model
    def _get_fiscal_year_budgets(self, fiscal_year=None):
        budgets = self.search([])
        year_options = []
        budget_by_year = {}
        for budget in budgets:
            be_year = str((budget.date_from or fields.Date.context_today(self)).year + 543)
            year_options.append(be_year)
            budget_by_year.setdefault(be_year, self.env["budget.budget"])
            budget_by_year[be_year] |= budget

        request_years = self.env["departmental.budget.request"].search([]).mapped("fiscal_year")
        year_options.extend([year for year in request_years if year])
        year_options = list(dict.fromkeys(sorted(year_options, reverse=True)))
        fiscal_year = fiscal_year or (
            year_options[0] if year_options else str(fields.Date.context_today(self).year + 543)
        )
        selected_budgets = budget_by_year.get(fiscal_year, self.env["budget.budget"])
        if not selected_budgets:
            try:
                be = int(fiscal_year)
                ce = be - 543
                date_from = fields.Date.to_date(f"{ce - 1}-10-01")
                date_to = fields.Date.to_date(f"{ce}-09-30")
                selected_budgets = self.search(
                    [
                        ("date_from", "<=", date_to),
                        ("date_to", ">=", date_from),
                    ]
                )
            except (TypeError, ValueError):
                selected_budgets = self.env["budget.budget"]
        return fiscal_year, year_options or [fiscal_year], selected_budgets

    @api.model
    def _line_spent_amount(self, line):
        practical = line.practical_amount or 0.0
        return abs(practical) if practical < 0 else practical

    @api.model
    def get_department_budget_dashboard(self, fiscal_year=None, department_id=None):
        """Dashboard data for departmental budget management."""
        fiscal_year, year_options, selected_budgets = self._get_fiscal_year_budgets(
            fiscal_year
        )
        lines = selected_budgets.mapped("budget_line")
        colors = ["#16a34a", "#8b5cf6", "#f59e0b", "#06b6d4", "#3b82f6", "#ef4444", "#64748b"]

        department_map = {}
        for line in lines:
            department = line.analytic_account_id
            key = department.id if department else 0
            vals = department_map.setdefault(
                key,
                {
                    "id": key,
                    "name": department.name if department else "ไม่ระบุหน่วยงาน",
                    "allocated": 0.0,
                    "actual": 0.0,
                },
            )
            vals["allocated"] += line.planned_amount or 0.0
            vals["actual"] += self._line_spent_amount(line)

        departments = []
        for index, vals in enumerate(
            sorted(department_map.values(), key=lambda item: item["name"])
        ):
            departments.append(
                {
                    "id": vals["id"],
                    "name": vals["name"],
                    "allocated": vals["allocated"],
                    "actual": vals["actual"],
                    "color": colors[index % len(colors)],
                }
            )

        if not departments:
            departments = [
                {
                    "id": 0,
                    "name": "ไม่ระบุหน่วยงาน",
                    "allocated": 0.0,
                    "actual": 0.0,
                    "color": colors[0],
                }
            ]

        selected_id = department_id
        if selected_id not in [dept["id"] for dept in departments]:
            selected_id = departments[0]["id"]
        selected_dept = next(dept for dept in departments if dept["id"] == selected_id)

        dept_lines = lines.filtered(
            lambda line: (line.analytic_account_id.id if line.analytic_account_id else 0)
            == selected_id
        )
        total_budget = sum(dept_lines.mapped("planned_amount"))
        spent = sum(self._line_spent_amount(line) for line in dept_lines)
        remaining = total_budget - spent
        usage_pct = (spent / total_budget * 100.0) if total_budget else 0.0

        # Project/control rows by budgetary position
        project_map = {}
        for line in dept_lines:
            post = line.general_budget_id
            key = post.id if post else 0
            vals = project_map.setdefault(
                key,
                {
                    "id": key,
                    "name": post.name if post else "ไม่ระบุหมวดงบประมาณ",
                    "allocated": 0.0,
                    "actual": 0.0,
                },
            )
            vals["allocated"] += line.planned_amount or 0.0
            vals["actual"] += self._line_spent_amount(line)

        project_rows = []
        for vals in sorted(project_map.values(), key=lambda item: item["allocated"], reverse=True):
            allocated_amt = vals["allocated"]
            actual_amt = vals["actual"]
            remain_amt = allocated_amt - actual_amt
            row_usage = (actual_amt / allocated_amt * 100.0) if allocated_amt else 0.0
            project_rows.append(
                {
                    "id": vals["id"],
                    "name": vals["name"],
                    "allocated": allocated_amt,
                    "actual": actual_amt,
                    "remaining": remain_amt,
                    "usage_pct": row_usage,
                    "bar_color": "#f59e0b" if row_usage >= 70 else "#16a34a",
                }
            )

        # Category breakdown by budget group / post
        category_map = {}
        for line in dept_lines:
            group = line.budget_group_id
            post = line.general_budget_id
            if group:
                key = f"g-{group.id}"
                label = group.name
            elif post:
                key = f"p-{post.id}"
                label = post.name
            else:
                key = "other"
                label = "อื่นๆ"
            vals = category_map.setdefault(
                key, {"key": key, "label": label, "amount": 0.0}
            )
            vals["amount"] += self._line_spent_amount(line) or (line.planned_amount or 0.0)

        category_total = sum(item["amount"] for item in category_map.values()) or 1.0
        category_breakdown = []
        for index, vals in enumerate(
            sorted(category_map.values(), key=lambda item: item["amount"], reverse=True)[:8]
        ):
            category_breakdown.append(
                {
                    "key": vals["key"],
                    "label": vals["label"],
                    "amount": vals["amount"],
                    "percent": vals["amount"] / category_total * 100.0,
                    "color": colors[index % len(colors)],
                }
            )

        recent_domain = [("fiscal_year", "=", fiscal_year)]
        if selected_id:
            recent_domain.append(("analytic_account_id", "=", selected_id))
        recent_requests = []
        for request in self.env["departmental.budget.request"].search(
            recent_domain, order="request_date desc, id desc", limit=6
        ):
            recent_requests.append(
                {
                    "id": request.id,
                    "name": request.name,
                    "department": request.analytic_account_id.name or "",
                    "date": request.request_date.isoformat() if request.request_date else "",
                    "amount": request.total_received_budget_amount
                    or request.total_amount
                    or 0.0,
                    "state": request.state,
                    "state_label": dict(
                        request._fields["state"]._description_selection(self.env)
                    ).get(request.state, request.state),
                }
            )

        return {
            "fiscal_year": fiscal_year,
            "year_options": year_options,
            "departments": departments,
            "selected_department_id": selected_id,
            "selected_department_name": selected_dept["name"],
            "cards": [
                {
                    "label": "งบประมาณทั้งหมดของแผนก",
                    "amount": total_budget,
                    "icon": "fa-clock-o",
                    "color": "#3b82f6",
                },
                {
                    "label": "เบิกใช้ไปแล้ว",
                    "amount": spent,
                    "icon": "fa-bullseye",
                    "color": "#ef4444",
                },
                {
                    "label": "งบประมาณคงเหลือ",
                    "amount": remaining,
                    "icon": "fa-check-circle",
                    "color": "#16a34a",
                },
                {
                    "label": "สัดส่วนการใช้งบ",
                    "amount": usage_pct,
                    "is_percent": True,
                    "icon": "fa-bolt",
                    "color": "#f59e0b",
                },
            ],
            "project_rows": project_rows,
            "category_breakdown": category_breakdown,
            "recent_requests": recent_requests,
        }
