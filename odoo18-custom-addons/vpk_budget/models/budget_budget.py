# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Budget(models.Model):
    _inherit = "budget.budget"

    @api.model
    def get_annual_expenditure_overview(self, fiscal_year=None):
        """Dashboard data for annual expenditure budget overview."""
        budgets = self.search([])
        year_options = []
        budget_by_year = {}
        for budget in budgets:
            be_year = str((budget.date_from or fields.Date.context_today(self)).year + 543)
            year_options.append(be_year)
            budget_by_year.setdefault(be_year, self.env["budget.budget"])
            budget_by_year[be_year] |= budget

        # Also include years from departmental requests.
        request_years = self.env["departmental.budget.request"].search([]).mapped("fiscal_year")
        year_options.extend([year for year in request_years if year])
        year_options = list(dict.fromkeys(sorted(year_options, reverse=True)))

        fiscal_year = fiscal_year or (
            year_options[0] if year_options else str(fields.Date.context_today(self).year + 543)
        )
        selected_budgets = budget_by_year.get(fiscal_year, self.env["budget.budget"])
        if not selected_budgets:
            # Fallback: budgets overlapping Thai fiscal year (Oct CE-1 to Sep CE)
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

        lines = selected_budgets.mapped("budget_line")
        total_budget = sum(lines.mapped("planned_amount"))
        allocated = total_budget
        actual = 0.0
        for line in lines:
            practical = line.practical_amount or 0.0
            actual += abs(practical) if practical < 0 else practical
        remaining = allocated - actual
        allocated_pct = (allocated / total_budget * 100.0) if total_budget else 0.0
        used_pct = (actual / allocated * 100.0) if allocated else 0.0
        remain_pct = (remaining / allocated * 100.0) if allocated else 0.0

        # Prior year comparison
        prior_year = str(int(fiscal_year) - 1) if fiscal_year.isdigit() else False
        prior_total = 0.0
        if prior_year and prior_year in budget_by_year:
            prior_total = sum(budget_by_year[prior_year].mapped("budget_line.planned_amount"))
        growth_pct = (
            ((total_budget - prior_total) / prior_total * 100.0) if prior_total else 0.0
        )

        # Department allocation
        colors = ["#3b82f6", "#f59e0b", "#8b5cf6", "#10b981", "#06b6d4", "#ef4444", "#64748b"]
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
            practical = line.practical_amount or 0.0
            vals["actual"] += abs(practical) if practical < 0 else practical

        department_rows = []
        for index, vals in enumerate(
            sorted(department_map.values(), key=lambda item: item["allocated"], reverse=True)
        ):
            allocated_amt = vals["allocated"]
            actual_amt = vals["actual"]
            remain_amt = allocated_amt - actual_amt
            usage_pct = (actual_amt / allocated_amt * 100.0) if allocated_amt else 0.0
            share_pct = (allocated_amt / allocated * 100.0) if allocated else 0.0
            department_rows.append(
                {
                    "id": vals["id"],
                    "name": vals["name"],
                    "allocated": allocated_amt,
                    "actual": actual_amt,
                    "remaining": remain_amt,
                    "usage_pct": usage_pct,
                    "share_pct": share_pct,
                    "color": colors[index % len(colors)],
                }
            )

        allocation_breakdown = [
            {
                "key": row["id"],
                "label": row["name"],
                "amount": row["allocated"],
                "percent": row["share_pct"],
                "color": row["color"],
            }
            for row in department_rows[:8]
            if row["allocated"]
        ]

        # KPI by budget request form type (สัดส่วนตามแบบฟอร์ม)
        form_colors = [
            "#16a34a",
            "#3b82f6",
            "#8b5cf6",
            "#f59e0b",
            "#06b6d4",
            "#ef4444",
            "#64748b",
            "#ec4899",
        ]
        form_icons = {
            "material": "fa-cubes",
            "asset": "fa-medkit",
            "construction": "fa-building",
            "project": "fa-folder-open",
        }
        request_domain = [("fiscal_year", "=", fiscal_year)] if fiscal_year else []
        form_requests = self.env["departmental.budget.request"].search(request_domain)
        form_map = {}
        for request in form_requests.filtered(lambda rec: rec.state != "rejected"):
            form_type = request.form_type_id
            key = form_type.id if form_type else 0
            vals = form_map.setdefault(
                key,
                {
                    "id": key,
                    "label": form_type.name if form_type else "ไม่ระบุแบบฟอร์ม",
                    "amount": 0.0,
                    "count": 0,
                    "section_key": False,
                },
            )
            if form_type and not vals["section_key"]:
                for section_key in ("material", "asset", "construction", "project"):
                    if form_type.has_section(section_key):
                        vals["section_key"] = section_key
                        break
            vals["amount"] += (
                request.total_received_budget_amount or request.total_amount or 0.0
            )
            vals["count"] += 1

        form_total = sum(item["amount"] for item in form_map.values()) or 0.0
        form_kpis = []
        for index, vals in enumerate(
            sorted(form_map.values(), key=lambda item: item["amount"], reverse=True)
        ):
            amount = vals["amount"]
            percent = (amount / form_total * 100.0) if form_total else 0.0
            section_key = vals["section_key"] or ""
            form_kpis.append(
                {
                    "id": vals["id"],
                    "label": vals["label"],
                    "amount": amount,
                    "count": vals["count"],
                    "percent": percent,
                    "color": form_colors[index % len(form_colors)],
                    "icon": form_icons.get(section_key, "fa-file-text-o"),
                    "subtitle": f"{vals['count']} รายการ · {percent:.1f}% ของคำขอ",
                }
            )

        # Monthly cumulative actual vs plan line
        month_labels = [
            "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
            "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
        ]
        monthly_actual = [0.0] * 12
        date_from = min(selected_budgets.mapped("date_from")) if selected_budgets else False
        date_to = max(selected_budgets.mapped("date_to")) if selected_budgets else False
        if date_from and date_to:
            analytic_lines = self.env["account.analytic.line"].search(
                [
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                    ("account_id", "in", lines.mapped("analytic_account_id").ids),
                ]
            )
            for analytic_line in analytic_lines:
                amount = analytic_line.amount or 0.0
                spent = abs(amount) if amount < 0 else 0.0
                if spent and analytic_line.date:
                    monthly_actual[analytic_line.date.month - 1] += spent

        # If no analytic spend yet, keep zeros but still show plan curve.
        cumulative_actual = []
        cumulative_plan = []
        running_actual = 0.0
        running_plan = 0.0
        monthly_plan = [(allocated / 12.0) if allocated else 0.0] * 12
        max_value = allocated or 1.0
        for index in range(12):
            running_actual += monthly_actual[index]
            running_plan += monthly_plan[index]
            max_value = max(max_value, running_actual, running_plan)
            cumulative_actual.append(
                {"label": month_labels[index], "amount": running_actual}
            )
            cumulative_plan.append(
                {"label": month_labels[index], "amount": running_plan}
            )

        # Recent budget requests as activity feed
        recent_domain = [("fiscal_year", "=", fiscal_year)] if fiscal_year else []
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
            "year_options": year_options or [fiscal_year],
            "cards": [
                {
                    "label": "งบประมาณทั้งหมด",
                    "amount": total_budget,
                    "subtitle": (
                        f"เพิ่มขึ้นจากปีก่อน +{growth_pct:.1f}%"
                        if growth_pct > 0
                        else (
                            f"ลดลงจากปีก่อน {growth_pct:.1f}%"
                            if growth_pct < 0
                            else "เทียบปีก่อนคงที่"
                        )
                    ),
                    "icon": "fa-university",
                    "color": "#3b82f6",
                    "tone": "up" if growth_pct >= 0 else "down",
                },
                {
                    "label": "จัดสรรแล้ว",
                    "amount": allocated,
                    "subtitle": f"คิดเป็น {allocated_pct:.1f}% ของงบรวม",
                    "icon": "fa-shield",
                    "color": "#8b5cf6",
                    "tone": "neutral",
                },
                {
                    "label": "เบิกจ่ายแล้วจริง",
                    "amount": actual,
                    "subtitle": f"ใช้ไปแล้ว {used_pct:.2f}%",
                    "icon": "fa-money",
                    "color": "#10b981",
                    "tone": "neutral",
                },
                {
                    "label": "งบประมาณคงเหลือ",
                    "amount": remaining,
                    "subtitle": f"คงเหลือใช้จ่ายได้ {remain_pct:.2f}%",
                    "icon": "fa-balance-scale",
                    "color": "#f59e0b",
                    "tone": "neutral",
                },
            ],
            "allocation_breakdown": allocation_breakdown,
            "form_kpis": form_kpis,
            "form_breakdown": [
                {
                    "key": item["id"],
                    "label": item["label"],
                    "amount": item["amount"],
                    "percent": item["percent"],
                    "color": item["color"],
                }
                for item in form_kpis
                if item["amount"]
            ],
            "department_rows": department_rows[:10],
            "recent_requests": recent_requests,
            "trend": {
                "actual_points": cumulative_actual,
                "plan_points": cumulative_plan,
                "max": max_value or 1.0,
            },
        }

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
