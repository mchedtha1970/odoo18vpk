# -*- coding: utf-8 -*-
from ast import literal_eval
from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

THAI_MONTHS_SHORT = (
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
)
THAI_MONTHS_LONG = (
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
)

# Leaf codes used for structure charts / AML monthly & analytic breakdown
REV_LEAF_CODES = (
    "PL_BUDGET",
    "PL_SALES",
    "PL_GRANT",
    "PL_DONATION",
    "PL_INTEREST",
    "PL_OTHER_IN",
    "PL_LAND",
)
EXP_LEAF_CODES = (
    "PL_STAFF",
    "PL_OPS",
    "PL_DEP",
    "PL_OTHER_EXP",
    "PL_REMIT",
)
LINE_META = (
    ("PL_BUDGET", "รายได้จากเงินงบประมาณ", "revenue"),
    ("PL_SALES", "รายได้จากการขายสินค้าและบริการ", "revenue"),
    ("PL_GRANT", "รายได้จากเงินช่วยเหลือ", "revenue"),
    ("PL_DONATION", "รายได้จากการรับบริจาค", "revenue"),
    ("PL_INTEREST", "รายได้ดอกเบี้ย", "revenue"),
    ("PL_OTHER_IN", "รายได้อื่น", "revenue"),
    ("PL_LAND", "รายได้แผ่นดิน", "revenue"),
    ("PL_GOV", "รวมรายได้จากรัฐบาล", "revenue_total"),
    ("PL_OTHER", "รวมรายได้จากแหล่งอื่น", "revenue_total"),
    ("PL_REV", "รวมรายได้จากการดำเนินงาน", "revenue_total"),
    ("PL_STAFF", "ค่าใช้จ่ายด้านบุคลากร", "expense"),
    ("PL_OPS", "ค่าใช้จ่ายดำเนินการ", "expense"),
    ("PL_DEP", "ค่าเสื่อมราคาและค่าตัดจำหน่าย", "expense"),
    ("PL_OTHER_EXP", "ค่าใช้จ่ายอื่น", "expense"),
    ("PL_REMIT", "รายได้แผ่นดินนำส่งคลัง", "expense"),
    ("PL_EXP", "รวมค่าใช้จ่ายจากการดำเนินงาน", "expense_total"),
    ("PL_RESULT", "รายได้สูง(ต่ำ)กว่าค่าใช้จ่ายจากการดำเนินงาน", "result"),
    ("PL_RESULT_NET", "รายได้สูง(ต่ำ)กว่าค่าใช้จ่ายสุทธิ", "result"),
)


class AccountReport(models.Model):
    _inherit = "account.report"

    @api.model
    def get_pl_dashboard_data(self, fiscal_year=None, compare=True, analytic_id=None):
        today = fields.Date.context_today(self)
        current_year = self._pl_year_of(today)
        years = self._pl_year_options(current_year)
        fiscal_year = int(fiscal_year or current_year)
        if fiscal_year not in years:
            years.insert(0, fiscal_year)

        analytic_id = int(analytic_id or 0)
        date_from, date_to = self._pl_period(fiscal_year)
        compare_year = fiscal_year - 1 if compare else None
        compare_from = compare_to = None
        if compare_year:
            compare_from, compare_to = self._pl_period(compare_year)

        current = self._pl_period_snapshot(date_from, date_to, analytic_id)
        previous = (
            self._pl_period_snapshot(compare_from, compare_to, analytic_id)
            if compare_year
            else self._pl_empty_snapshot()
        )
        months = self._pl_monthly_series(date_from, date_to, analytic_id)
        months_prev = (
            self._pl_monthly_series(compare_from, compare_to, analytic_id)
            if compare_year
            else []
        )
        departments = self._pl_department_rows(date_from, date_to)
        analytics = self._pl_analytic_options()
        unposted = self._pl_unposted_count(date_from, date_to)

        def yoy(curr, prev):
            if not compare_year or not prev:
                return None
            return round((curr - prev) / abs(prev) * 100.0, 1)

        rev = current["revenue"]
        exp = current["expense"]
        net = current["net"]
        prev_rev = previous["revenue"]
        prev_exp = previous["expense"]
        prev_net = previous["net"]
        margin = (net / rev * 100.0) if rev else 0.0
        prev_margin = (prev_net / prev_rev * 100.0) if prev_rev else 0.0

        return {
            "fiscal_year": fiscal_year,
            "fiscal_year_be": fiscal_year + 543,
            "compare_year": compare_year,
            "compare_year_be": (compare_year + 543) if compare_year else None,
            "compare": bool(compare_year),
            "year_options": years,
            "year_option_labels": [
                {"value": y, "label": "ปีงบประมาณ %s (%s)" % (y + 543, y)} for y in years
            ],
            "analytic_id": analytic_id,
            "analytics": analytics,
            "as_of_label": "ข้อมูล ณ วันที่ %s %s %s"
            % (today.day, THAI_MONTHS_LONG[today.month - 1], today.year + 543),
            "period_label": "ปีงบประมาณ %s · %s – %s"
            % (
                fiscal_year + 543,
                self._pl_thai_date(date_from),
                self._pl_thai_date(date_to),
            ),
            "company_name": self.env.company.name,
            "unposted_count": unposted,
            "kpis": {
                "revenue": rev,
                "expense": exp,
                "net": net,
                "margin_pct": round(margin, 1),
                "yoy_revenue_pct": yoy(rev, prev_rev),
                "yoy_expense_pct": yoy(exp, prev_exp),
                "yoy_net_pct": yoy(net, prev_net),
                "prev_revenue": prev_rev,
                "prev_expense": prev_exp,
                "prev_net": prev_net,
                "prev_margin_pct": round(prev_margin, 1),
            },
            "revenue_structure": current["revenue_structure"],
            "expense_structure": current["expense_structure"],
            "lines": current["lines"],
            "prev_lines": previous["lines"] if compare_year else [],
            "yoy_categories": self._pl_yoy_categories(current, previous) if compare_year else [],
            "months": months,
            "months_prev": months_prev,
            "departments": departments,
            "report_action_xmlid": "vpk_hospital_balance_sheet.action_profit_and_loss",
        }

    # ------------------------------------------------------------------ helpers
    @api.model
    def _pl_report(self):
        return self.env.ref("vpk_hospital_balance_sheet.profit_and_loss")

    @api.model
    def _pl_year_of(self, day):
        """ปีงบประมาณราชการ (ค.ศ. ของวันสิ้นปีงบ) เช่น ต.ค.2025 → 2026."""
        day = fields.Date.to_date(day)
        return day.year + 1 if day.month >= 10 else day.year

    @api.model
    def _pl_year_options(self, current_year):
        return list(range(current_year, current_year - 6, -1))

    @api.model
    def _pl_period(self, year):
        """ปีงบประมาณราชการ: 1 ต.ค. (ปี-1) ถึง 30 ก.ย. ปีที่ระบุ (ค.ศ.)."""
        ce = int(year)
        return date(ce - 1, 10, 1), date(ce, 9, 30)

    @api.model
    def _pl_thai_date(self, day):
        return "%s %s %s" % (day.day, THAI_MONTHS_SHORT[day.month - 1], day.year + 543)

    @api.model
    def _pl_month_label(self, day):
        """ป้ายเดือนตามปีงบประมาณ เช่น ต.ค.68 … ก.ย.69"""
        be_short = str(day.year + 543)[-2:]
        return "%s %s" % (THAI_MONTHS_SHORT[day.month - 1], be_short)

    @api.model
    def _pl_empty_snapshot(self):
        return {
            "revenue": 0.0,
            "expense": 0.0,
            "net": 0.0,
            "balances": {},
            "lines": [],
            "revenue_structure": [],
            "expense_structure": [],
        }

    @api.model
    def _pl_period_snapshot(self, date_from, date_to, analytic_id=0):
        balances = self._pl_balances_for_period(date_from, date_to, analytic_id)
        rev = balances.get("PL_REV", 0.0)
        exp = balances.get("PL_EXP", 0.0)
        net = balances.get("PL_RESULT_NET", balances.get("PL_RESULT", rev - exp))
        lines = []
        for code, name, kind in LINE_META:
            amount = balances.get(code, 0.0)
            base = rev if kind.startswith("revenue") else exp if kind.startswith("expense") else rev
            pct = (amount / base * 100.0) if base else 0.0
            lines.append(
                {
                    "code": code,
                    "name": name,
                    "kind": kind,
                    "amount": amount,
                    "pct": round(pct, 2),
                }
            )
        revenue_structure = [
            {"key": "gov", "label": "จากรัฐบาล", "amount": balances.get("PL_GOV", 0.0)},
            {"key": "sales", "label": "ขายสินค้าและบริการ", "amount": balances.get("PL_SALES", 0.0)},
            {
                "key": "other",
                "label": "รายได้อื่น",
                "amount": max(balances.get("PL_OTHER", 0.0) - balances.get("PL_SALES", 0.0), 0.0),
            },
        ]
        expense_structure = [
            {"key": "ops", "label": "ดำเนินการ", "amount": balances.get("PL_OPS", 0.0)},
            {"key": "other", "label": "อื่น", "amount": balances.get("PL_OTHER_EXP", 0.0) + balances.get("PL_REMIT", 0.0)},
            {"key": "staff", "label": "บุคลากร", "amount": balances.get("PL_STAFF", 0.0)},
            {"key": "dep", "label": "เสื่อมราคา", "amount": balances.get("PL_DEP", 0.0)},
        ]
        return {
            "revenue": rev,
            "expense": exp,
            "net": net,
            "balances": balances,
            "lines": lines,
            "revenue_structure": revenue_structure,
            "expense_structure": expense_structure,
        }

    @api.model
    def _pl_balances_for_period(self, date_from, date_to, analytic_id=0):
        if analytic_id:
            return self._pl_balances_from_aml(date_from, date_to, analytic_id)
        report = self._pl_report()
        previous_options = {
            "date": {
                "date_from": fields.Date.to_string(date_from),
                "date_to": fields.Date.to_string(date_to),
                "mode": "range",
                "filter": "custom",
            },
            "unfold_all": False,
        }
        options = report.get_options(previous_options)
        lines = report.with_context(no_format=True)._get_lines(options)

        balances = {}
        ReportLine = self.env["account.report.line"]
        for line in lines:
            model, res_id = report._get_model_info_from_id(line["id"])
            if model != "account.report.line" or not res_id:
                continue
            report_line = ReportLine.browse(res_id)
            if not report_line.code:
                continue
            columns = line.get("columns") or []
            value = 0.0
            if columns:
                col = columns[0]
                value = col.get("no_format")
                if value is None:
                    value = col.get("name") or 0.0
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    value = 0.0
            balances[report_line.code] = value
        return balances

    @api.model
    def _pl_balances_from_aml(self, date_from, date_to, analytic_id=0):
        """Aggregate leaf PL lines from move lines (supports analytic filter)."""
        leaf_map = self._pl_leaf_account_map()
        balances = {}
        for code, (accounts, sign) in leaf_map.items():
            balances[code] = self._pl_aml_sum(accounts, date_from, date_to, sign, analytic_id)
        balances["PL_GOV"] = balances.get("PL_BUDGET", 0.0)
        balances["PL_OTHER"] = sum(
            balances.get(code, 0.0)
            for code in ("PL_SALES", "PL_GRANT", "PL_DONATION", "PL_INTEREST", "PL_OTHER_IN", "PL_LAND")
        )
        balances["PL_REV"] = balances["PL_GOV"] + balances["PL_OTHER"]
        balances["PL_EXP"] = sum(
            balances.get(code, 0.0)
            for code in ("PL_STAFF", "PL_OPS", "PL_DEP", "PL_OTHER_EXP", "PL_REMIT")
        )
        balances["PL_RESULT"] = balances["PL_REV"] - balances["PL_EXP"]
        balances["PL_RESULT_NET"] = balances["PL_RESULT"]
        return balances

    @api.model
    def _pl_yoy_categories(self, current, previous):
        pairs = (
            ("รัฐบาล", "PL_GOV"),
            ("ขาย/บริการ", "PL_SALES"),
            ("รายได้อื่น", None),  # computed
            ("บุคลากร", "PL_STAFF"),
            ("ดำเนินการ", "PL_OPS"),
            ("เสื่อมราคา", "PL_DEP"),
            ("ค่าใช้จ่ายอื่น", "PL_OTHER_EXP"),
        )
        rows = []
        for label, code in pairs:
            if code is None:
                curr = max(
                    current["balances"].get("PL_OTHER", 0.0)
                    - current["balances"].get("PL_SALES", 0.0),
                    0.0,
                )
                prev = max(
                    previous["balances"].get("PL_OTHER", 0.0)
                    - previous["balances"].get("PL_SALES", 0.0),
                    0.0,
                )
            else:
                curr = current["balances"].get(code, 0.0)
                prev = previous["balances"].get(code, 0.0)
            rows.append({"label": label, "current": curr, "previous": prev})
        return rows

    @api.model
    def _pl_account_domain_from_aml_domain(self, domain):
        """Convert move-line domain terms on account_id.* into account.account domain."""
        if not isinstance(domain, (list, tuple)):
            return [("id", "=", 0)]
        converted = []
        for term in domain:
            if isinstance(term, str):
                converted.append(term)
                continue
            if not isinstance(term, (list, tuple)) or len(term) != 3:
                continue
            field, operator, value = term
            if field == "account_id":
                converted.append(("id", operator, value))
            elif field.startswith("account_id."):
                converted.append((field.split(".", 1)[1], operator, value))
            elif field == "account_id.code":
                converted.append(("code", operator, value))
        return converted or [("id", "=", 0)]

    @api.model
    def _pl_leaf_account_map(self):
        """Map leaf PL codes -> (account recordset, sign) where sign mirrors report subformula."""
        report = self._pl_report()
        ReportLine = self.env["account.report.line"]
        Account = self.env["account.account"]
        result = {}
        for code in REV_LEAF_CODES + EXP_LEAF_CODES:
            line = ReportLine.search(
                [("report_id", "=", report.id), ("code", "=", code)],
                limit=1,
            )
            if not line:
                result[code] = (Account, -1.0 if code in REV_LEAF_CODES else 1.0)
                continue
            accounts = Account
            sign = -1.0 if code in REV_LEAF_CODES else 1.0
            for expr in line.expression_ids.filtered(lambda e: e.engine == "domain" and e.label == "balance"):
                try:
                    domain = literal_eval(expr.formula) if isinstance(expr.formula, str) else expr.formula
                except (ValueError, SyntaxError):
                    continue
                account_domain = self._pl_account_domain_from_aml_domain(domain)
                accounts |= Account.search(account_domain)
                if expr.subformula and "sum" in expr.subformula:
                    sign = -1.0 if expr.subformula.strip().startswith("-") else 1.0
            result[code] = (accounts, sign)
        return result

    @api.model
    def _pl_aml_amount_by_month(self, date_from, date_to, analytic_id=0):
        leaf_map = self._pl_leaf_account_map()
        rev_accounts = self.env["account.account"]
        exp_accounts = self.env["account.account"]
        rev_sign = -1.0
        exp_sign = 1.0
        for code, (accounts, sign) in leaf_map.items():
            if code in REV_LEAF_CODES:
                rev_accounts |= accounts
                rev_sign = sign
            else:
                exp_accounts |= accounts
                exp_sign = sign

        months = []
        cursor = date_from.replace(day=1)
        end = date_to
        while cursor <= end:
            month_start = cursor
            month_end = min(cursor + relativedelta(months=1, days=-1), end)
            rev = self._pl_aml_sum(rev_accounts, month_start, month_end, rev_sign, analytic_id)
            exp = self._pl_aml_sum(exp_accounts, month_start, month_end, exp_sign, analytic_id)
            months.append(
                {
                    "key": "%04d-%02d" % (month_start.year, month_start.month),
                    "label": self._pl_month_label(month_start),
                    "month": month_start.month,
                    "revenue": rev,
                    "expense": exp,
                    "net": rev - exp,
                }
            )
            cursor = cursor + relativedelta(months=1)
        return months

    @api.model
    def _pl_monthly_series(self, date_from, date_to, analytic_id=0):
        return self._pl_aml_amount_by_month(date_from, date_to, analytic_id)

    @api.model
    def _pl_aml_sum(self, accounts, date_from, date_to, sign, analytic_id=0):
        if not accounts:
            return 0.0
        MoveLine = self.env["account.move.line"]
        domain = [
            ("account_id", "in", accounts.ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("parent_state", "=", "posted"),
            ("company_id", "in", self.env.companies.ids),
        ]
        if analytic_id:
            # Filter lines whose analytic_distribution includes the analytic account
            lines = MoveLine.search(domain)
            total = 0.0
            key = str(analytic_id)
            for line in lines:
                dist = line.analytic_distribution or {}
                pct = dist.get(key)
                if pct is None:
                    continue
                total += (line.balance or 0.0) * (float(pct) / 100.0)
            return total * sign
        return self._pl_aml_balance_sum(domain) * sign

    @api.model
    def _pl_aml_balance_sum(self, domain):
        MoveLine = self.env["account.move.line"]
        if hasattr(MoveLine, "_read_group"):
            groups = MoveLine._read_group(domain, aggregates=["balance:sum"])
            return (groups[0][0] if groups else 0.0) or 0.0
        grouped = MoveLine.read_group(domain, ["balance"], [])
        return (grouped[0]["balance"] if grouped else 0.0) or 0.0

    @api.model
    def _pl_department_rows(self, date_from, date_to, limit=12):
        leaf_map = self._pl_leaf_account_map()
        rev_accounts = self.env["account.account"]
        exp_accounts = self.env["account.account"]
        for code, (accounts, _sign) in leaf_map.items():
            if code in REV_LEAF_CODES:
                rev_accounts |= accounts
            else:
                exp_accounts |= accounts

        rev_by = self._pl_analytic_totals(rev_accounts, date_from, date_to, sign=-1.0)
        exp_by = self._pl_analytic_totals(exp_accounts, date_from, date_to, sign=1.0)
        analytic_ids = set(rev_by) | set(exp_by)
        Analytic = self.env["account.analytic.account"]
        rows = []
        for analytic_id in analytic_ids:
            if not analytic_id:
                continue
            analytic = Analytic.browse(analytic_id)
            if not analytic.exists():
                continue
            rev = rev_by.get(analytic_id, 0.0)
            exp = exp_by.get(analytic_id, 0.0)
            rows.append(
                {
                    "id": analytic_id,
                    "name": analytic.display_name,
                    "revenue": rev,
                    "expense": exp,
                    "net": rev - exp,
                }
            )
        rows.sort(key=lambda r: abs(r["revenue"]) + abs(r["expense"]), reverse=True)
        top = rows[:limit]
        rest = rows[limit:]
        if rest:
            top.append(
                {
                    "id": 0,
                    "name": "อื่นๆ / รวมหน่วยงานที่เหลือ",
                    "revenue": sum(r["revenue"] for r in rest),
                    "expense": sum(r["expense"] for r in rest),
                    "net": sum(r["net"] for r in rest),
                }
            )
        # Unallocated (no analytic)
        unalloc_rev = self._pl_aml_sum_without_analytic(rev_accounts, date_from, date_to, -1.0)
        unalloc_exp = self._pl_aml_sum_without_analytic(exp_accounts, date_from, date_to, 1.0)
        if unalloc_rev or unalloc_exp:
            top.append(
                {
                    "id": -1,
                    "name": "ไม่ระบุศูนย์ต้นทุน",
                    "revenue": unalloc_rev,
                    "expense": unalloc_exp,
                    "net": unalloc_rev - unalloc_exp,
                }
            )
        total_rev = sum(r["revenue"] for r in top) or 1.0
        for row in top:
            row["pct"] = round(row["revenue"] / total_rev * 100.0, 1)
            max_bar = max((abs(r["revenue"]) + abs(r["expense"])) for r in top) or 1.0
            row["width"] = round((abs(row["revenue"]) + abs(row["expense"])) / max_bar * 100.0, 1)
        return top

    @api.model
    def _pl_analytic_totals(self, accounts, date_from, date_to, sign=1.0):
        if not accounts:
            return {}
        MoveLine = self.env["account.move.line"]
        lines = MoveLine.search(
            [
                ("account_id", "in", accounts.ids),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("parent_state", "=", "posted"),
                ("company_id", "in", self.env.companies.ids),
                ("analytic_distribution", "!=", False),
            ]
        )
        totals = defaultdict(float)
        for line in lines:
            dist = line.analytic_distribution or {}
            balance = line.balance or 0.0
            for key, pct in dist.items():
                try:
                    analytic_id = int(key)
                except (TypeError, ValueError):
                    continue
                totals[analytic_id] += balance * (float(pct) / 100.0) * sign
        return totals

    @api.model
    def _pl_aml_sum_without_analytic(self, accounts, date_from, date_to, sign):
        if not accounts:
            return 0.0
        MoveLine = self.env["account.move.line"]
        lines = MoveLine.search(
            [
                ("account_id", "in", accounts.ids),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("parent_state", "=", "posted"),
                ("company_id", "in", self.env.companies.ids),
            ]
        )
        total = 0.0
        for line in lines:
            if line.analytic_distribution:
                continue
            total += line.balance or 0.0
        return total * sign

    @api.model
    def _pl_analytic_options(self):
        Analytic = self.env["account.analytic.account"]
        domain = []
        if "company_id" in Analytic._fields:
            domain = [("company_id", "in", [False] + self.env.companies.ids)]
        elif "company_ids" in Analytic._fields:
            domain = ["|", ("company_ids", "=", False), ("company_ids", "in", self.env.companies.ids)]
        accounts = Analytic.search(domain, order="name", limit=300)
        return [{"id": 0, "name": "ทุกหน่วยงาน"}] + [
            {"id": acc.id, "name": acc.display_name} for acc in accounts
        ]

    @api.model
    def _pl_unposted_count(self, date_from, date_to):
        return self.env["account.move"].search_count(
            [
                ("date", "<=", date_to),
                ("state", "=", "draft"),
                ("company_id", "in", self.env.companies.ids),
                ("move_type", "in", ("entry", "out_invoice", "in_invoice", "out_refund", "in_refund")),
            ]
        )
