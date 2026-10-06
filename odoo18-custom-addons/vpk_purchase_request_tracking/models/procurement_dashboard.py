# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models

STAGES = [
    ("request", "ขอซื้อ/ขอจ้าง"),
    ("tor", "จัดทำ TOR / ราคากลาง"),
    ("announce", "ประกาศเชิญชวน"),
    ("review", "พิจารณาผล"),
    ("contract", "ลงนามสัญญา / PO"),
    ("receive", "ส่งมอบ / ตรวจรับ"),
    ("pay", "เบิกจ่าย"),
]
STAGE_INDEX = {key: index for index, (key, _label) in enumerate(STAGES)}
METHODS = [
    ("ebidding", "e-bidding"),
    ("selection", "คัดเลือก"),
    ("specific", "เฉพาะเจาะจง"),
    ("emarket", "e-market"),
]


class PurchaseRequestProcurementDashboard(models.Model):
    _inherit = "purchase.request"

    @api.model
    def get_procurement_dashboard_data(self, fiscal_year=None):
        today = fields.Date.context_today(self)
        current_year = self._proc_fiscal_year(today)
        years = self._proc_year_options(current_year)
        fiscal_year = fiscal_year or current_year
        if fiscal_year not in years:
            years.insert(0, fiscal_year)
        period_start, period_end = self._proc_period(fiscal_year)
        prev_start, prev_end = self._proc_period(str(int(fiscal_year) - 1))

        requests = self.search(
            [
                ("date_start", ">=", period_start),
                ("date_start", "<=", period_end),
                ("state", "!=", "rejected"),
            ],
            order="date_start desc, id desc",
        )
        previous = self.search_count(
            [
                ("date_start", ">=", prev_start),
                ("date_start", "<=", prev_end),
                ("state", "!=", "rejected"),
            ]
        )

        stage_counts = {key: 0 for key, _label in STAGES}
        method_map = {
            key: {"key": key, "label": label, "count": 0, "amount": 0.0}
            for key, label in METHODS
        }
        quarter_actual = [0.0, 0.0, 0.0, 0.0]
        projects = []
        total_amount = 0.0
        savings = 0.0
        disbursed = 0.0
        in_progress = 0
        late_count = 0
        late_before_receive = 0
        duration_days = []
        due_contracts = 0
        waiting_accept = 0
        waiting_approval = 0
        contracts = []

        for request in requests:
            amount = request.estimated_cost or 0.0
            total_amount += amount
            pos = request.mapped("line_ids.purchase_lines.order_id").filtered(
                lambda order: order.state != "cancel"
            )
            confirmed = pos.filtered(lambda order: order.state in ("purchase", "done"))
            requisitions = self._proc_requisitions(request)
            stage = self._proc_stage(request, confirmed, requisitions)
            method_key = self._proc_method_key(
                request.procurement_method_id.name
                if "procurement_method_id" in request._fields and request.procurement_method_id
                else ""
            )
            if method_key in method_map:
                method_map[method_key]["count"] += 1
                method_map[method_key]["amount"] += amount

            billed, bill_date = self._proc_billed(confirmed)
            disbursed += billed
            if bill_date:
                quarter = self._proc_quarter(bill_date, period_start)
                if quarter is not None:
                    quarter_actual[quarter] += billed
            po_amount = sum(confirmed.mapped("amount_total"))
            if confirmed and amount > po_amount:
                savings += amount - po_amount

            due = self._proc_due_date(request, confirmed)
            late = bool(
                due
                and due < today
                and request.state != "done"
                and stage != "pay"
            )
            if request.state == "done":
                status_key = "done"
                status_label = "เสร็จสิ้น"
            elif late:
                status_key = "late"
                status_label = "ล่าช้า"
                late_count += 1
                if STAGE_INDEX[stage] < STAGE_INDEX["receive"]:
                    late_before_receive += 1
            elif request.state in ("draft", "to_approve"):
                status_key = "approve"
                status_label = "รออนุมัติ"
            else:
                status_key = "progress"
                status_label = "กำลังดำเนินการ"

            if status_key == "progress":
                in_progress += 1
                if request.date_start:
                    duration_days.append((today - request.date_start).days)
            if request.state == "to_approve":
                waiting_approval += 1
            if stage == "receive":
                waiting_accept += 1
            due_contracts += self._proc_due_contracts(confirmed, today)

            if status_key != "done":
                stage_counts[stage] += 1
            projects.append(
                self._proc_project_row(
                    request, stage, status_key, status_label, amount, due, method_key
                )
            )
            for order in confirmed[:3]:
                contracts.append(
                    {
                        "id": order.id,
                        "name": order.name,
                        "partner": order.partner_id.name or "",
                        "request": request.name,
                        "amount": order.amount_total,
                        "state": "ส่งมอบแล้ว" if self._proc_received(order) else "อยู่ระหว่างสัญญา",
                    }
                )

        active_stages = sum(stage_counts.values())
        plan_each = total_amount / 4.0 if total_amount else 0.0
        method_max = max((item["amount"] for item in method_map.values()), default=1.0) or 1.0
        stage_max = max(stage_counts.values(), default=1) or 1
        avg_days = round(sum(duration_days) / len(duration_days)) if duration_days else 0
        paid_pct = (disbursed / total_amount * 100.0) if total_amount else 0.0
        savings_pct = (savings / total_amount * 100.0) if total_amount else 0.0
        year_delta = len(requests) - previous

        return {
            "fiscal_year": fiscal_year,
            "year_options": years,
            "as_of_label": "ข้อมูล ณ วันที่ %s %s %s" % (
                today.day,
                ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][today.month - 1],
                today.year + 543,
            ),
            "kpis": {
                "total": len(requests),
                "year_delta": year_delta,
                "amount": total_amount,
                "savings": savings,
                "savings_pct": savings_pct,
                "in_progress": in_progress,
                "avg_days": avg_days,
                "late": late_count,
                "late_note": "ส่วนใหญ่ยังไม่ขึ้นตรวจรับ" if late_count and late_before_receive >= late_count / 2.0 else "เลยกำหนดเสร็จ",
                "paid_pct": paid_pct,
            },
            "stages": [
                {
                    "key": key,
                    "label": label,
                    "count": stage_counts[key],
                    "width": stage_counts[key] / stage_max * 100.0,
                }
                for key, label in STAGES
            ],
            "open_stage_count": active_stages,
            "quarters": [
                {
                    "label": "ไตรมาส %s" % (index + 1),
                    "plan": plan_each,
                    "actual": quarter_actual[index],
                }
                for index in range(4)
            ],
            "quarter_max": max([plan_each, *quarter_actual, 1.0]),
            "methods": [
                {
                    **item,
                    "width": item["amount"] / method_max * 100.0,
                }
                for item in method_map.values()
            ],
            "alerts": [
                {"tone": "late", "text": "สัญญา %s ฉบับครบกำหนดส่งมอบภายใน 7 วัน" % due_contracts},
                {"tone": "progress", "text": "%s รายการรอคณะกรรมการตรวจรับพัสดุ" % waiting_accept},
                {"tone": "approve", "text": "%s คำขอรออนุมัติจากหัวหน้าหน่วยงาน" % waiting_approval},
            ],
            "projects": projects[:80],
            "project_total": len(projects),
            "contracts": contracts[:40],
        }

    def _proc_project_row(self, request, stage, status_key, status_label, amount, due, method_key):
        method_label = dict(METHODS).get(method_key, "ไม่ระบุวิธี")
        if "procurement_method_id" in request._fields and request.procurement_method_id:
            method_label = request.procurement_method_id.name
        description = (request.description or "").strip().split("\n")[0]
        if not description:
            product = request.line_ids[:1].product_id
            description = product.display_name if product else ""
        department = ""
        if "department_id" in request._fields and request.department_id:
            department = request.department_id.name
        index = STAGE_INDEX[stage]
        return {
            "id": request.id,
            "name": request.name,
            "description": description,
            "department": department or "ไม่ระบุหน่วยงาน",
            "method": method_label,
            "amount": amount,
            "stage_index": index,
            "stage_label": "ขั้นที่ %s: %s" % (index + 1, dict(STAGES)[stage]),
            "due": "%s %s %s" % (
                due.day,
                ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."][due.month - 1],
                str(due.year + 543)[-2:],
            ) if due else "—",
            "status_key": status_key,
            "status_label": status_label,
        }

    @api.model
    def _proc_requisitions(self, request):
        if "requisition_lines" not in request.line_ids._fields:
            return self.env["purchase.requisition"].browse()
        return request.line_ids.requisition_lines.requisition_id

    @api.model
    def _proc_stage(self, request, confirmed, requisitions):
        if request.state == "done":
            return "pay"
        if confirmed:
            billed, _bill_date = self._proc_billed(confirmed)
            if billed and billed + 1.0 >= sum(confirmed.mapped("amount_total")):
                return "pay"
            if all(self._proc_received(order) for order in confirmed):
                return "receive"
            return "contract"
        stages = set()
        if requisitions and "egp_flow_stage" in requisitions._fields:
            stages = set(filter(None, requisitions.mapped("egp_flow_stage")))
        if "compare" in stages:
            return "review"
        if stages & {"rfq", "egp_docs", "confirmed"}:
            return "announce"
        if "awarded" in stages:
            return "contract"
        if "done" in stages:
            return "pay"
        if request.state in ("draft", "to_approve"):
            return "request"
        return "tor"

    @api.model
    def _proc_received(self, order):
        if "receipt_status" in order._fields and order.receipt_status:
            return order.receipt_status == "full"
        lines = order.order_line.filtered("product_qty")
        return bool(lines) and all(line.qty_received >= line.product_qty for line in lines)

    @api.model
    def _proc_billed(self, orders):
        amount = 0.0
        bill_date = False
        for order in orders:
            if "invoice_ids" in order._fields:
                bills = order.invoice_ids.filtered(
                    lambda move: move.state == "posted" and move.move_type == "in_invoice"
                )
                refunds = order.invoice_ids.filtered(
                    lambda move: move.state == "posted" and move.move_type == "in_refund"
                )
                amount += sum(bills.mapped("amount_total")) - sum(refunds.mapped("amount_total"))
                dates = [bill.invoice_date for bill in bills if bill.invoice_date]
                if dates and (not bill_date or min(dates) < bill_date):
                    bill_date = min(dates)
            elif order.invoice_status == "invoiced":
                amount += order.amount_total
                if order.date_order and (not bill_date or order.date_order.date() < bill_date):
                    bill_date = order.date_order.date()
        return amount, bill_date

    @api.model
    def _proc_due_date(self, request, orders):
        dates = [line.date_required for line in request.line_ids if line.date_required]
        for order in orders:
            dates.extend(
                line.date_planned.date()
                for line in order.order_line
                if line.date_planned
            )
        return min(dates) if dates else False

    @api.model
    def _proc_due_contracts(self, orders, today):
        count = 0
        for order in orders:
            if self._proc_received(order):
                continue
            dates = [
                line.date_planned.date()
                for line in order.order_line
                if line.date_planned and line.qty_received < line.product_qty
            ]
            if dates and 0 <= (min(dates) - today).days <= 7:
                count += 1
        return count

    @api.model
    def _proc_method_key(self, name):
        text = (name or "").lower().replace(" ", "")
        if "ebidding" in text or "e-bidding" in (name or "").lower() or "ประกวด" in (name or ""):
            return "ebidding"
        if "คัดเลือก" in (name or ""):
            return "selection"
        if "เฉพาะเจาะจง" in (name or "") or "เฉพาะ" in (name or ""):
            return "specific"
        if "emarket" in text or "e-market" in (name or "").lower() or "ตลาด" in (name or ""):
            return "emarket"
        return "specific" if not name else "ebidding" if "bid" in text else "specific"

    @api.model
    def _proc_fiscal_year(self, day):
        end_year = day.year + 1 if day.month >= 10 else day.year
        return str(end_year + 543)

    @api.model
    def _proc_period(self, fiscal_year):
        ce = int(fiscal_year) - 543
        return date(ce - 1, 10, 1), date(ce, 9, 30)

    @api.model
    def _proc_quarter(self, day, period_start):
        index = (day.year - period_start.year) * 12 + day.month - period_start.month
        if 0 <= index <= 11:
            return index // 3
        return None

    @api.model
    def _proc_year_options(self, current_year):
        years = {current_year}
        for day in self.search([]).mapped("date_start"):
            if day:
                years.add(self._proc_fiscal_year(day))
        return sorted(years, reverse=True)
