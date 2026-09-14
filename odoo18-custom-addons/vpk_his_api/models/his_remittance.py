# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import socket
from collections import defaultdict
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round

from .his_payment_method_map import is_advance_apply_code, is_advance_in_code

ENTITLEMENT_TENDER_CODES = frozenset({"sso", "uc", "csmbs", "ar_claim"})
CREDIT_CARD_CODES = frozenset({"credit_card", "card", "creditcard"})
TRANSFER_CODES = frozenset({"transfer", "bank", "promptpay"})


def _round_amt(amount):
    return float_round(amount or 0.0, precision_digits=2)


def _fmt_amt(amount):
    return "{:,.2f}".format(_round_amt(amount))


class HisBatch(models.Model):
    _inherit = "vpk.his.batch"

    def action_open_remittance_wizard(self):
        batches = self.filtered(lambda b: b.batch_type == "revenue")
        if not batches:
            raise UserError(_("ใบนำส่งเงินใช้กับชุดรายได้ HIS เท่านั้น"))
        dates = batches.mapped("business_date")
        tickets = [
            t
            for t in batches.mapped("sale_line_ids.ticket_external_id")
            if t
        ]
        shifts = {s for s in batches.mapped("shift") if s}
        vals = {
            "date_from": min(dates),
            "date_to": max(dates),
            "batch_ids": [(6, 0, batches.ids)],
            "company_id": batches[0].company_id.id,
        }
        if len(shifts) == 1:
            vals["shift"] = shifts.pop()
        if tickets:
            vals["receipt_from"] = min(tickets)
            vals["receipt_to"] = max(tickets)
        create_dates = batches.mapped("create_date")
        write_dates = batches.mapped("write_date")
        if create_dates:
            vals["datetime_from"] = min(create_dates)
        if write_dates:
            vals["datetime_to"] = max(write_dates)
        wizard = self.env["vpk.his.remittance.wizard"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบนำส่งเงิน"),
            "res_model": "vpk.his.remittance.wizard",
            "view_mode": "form",
            "target": "new",
            "res_id": wizard.id,
        }

    @api.model
    def prepare_remittance_data(self, batches, options=None):
        """Aggregate HIS sale/payment lines into ใบนำส่งเงิน rows."""
        options = options or {}
        batches = batches.filtered(lambda b: b.batch_type == "revenue")
        company = options.get("company") or (
            batches[:1].company_id if batches else self.env.company
        )
        Map = self.env["vpk.his.entitlement.map"]
        sale_lines = batches.mapped("sale_line_ids")
        payment_lines = batches.mapped("payment_line_ids")

        groups = defaultdict(
            lambda: {
                "op_tickets": set(),
                "ip_tickets": set(),
                "op_noticket": 0,
                "ip_noticket": 0,
                "op_amount": 0.0,
                "ip_amount": 0.0,
            }
        )
        all_tickets = set()
        no_ticket_count = 0
        ticket_types = defaultdict(set)
        for line in sale_lines:
            code = (line.entitlement_code or "").strip().upper()
            group = groups[code]
            amount = line.amount_total or 0.0
            ticket = (line.ticket_external_id or "").strip()
            is_ip = line.service_type == "ip"
            if ticket:
                all_tickets.add(ticket)
                ticket_types[ticket].add(line.service_type)
                if is_ip:
                    group["ip_tickets"].add(ticket)
                    group["ip_amount"] += amount
                else:
                    group["op_tickets"].add(ticket)
                    group["op_amount"] += amount
            else:
                no_ticket_count += 1
                if is_ip:
                    group["ip_noticket"] += 1
                    group["ip_amount"] += amount
                else:
                    group["op_noticket"] += 1
                    group["op_amount"] += amount

        rows = []
        for code, group in groups.items():
            seq, label, _emap = Map.remittance_display(code, company=company)
            op_count = len(group["op_tickets"]) + group["op_noticket"]
            ip_count = len(group["ip_tickets"]) + group["ip_noticket"]
            op_amount = _round_amt(group["op_amount"])
            ip_amount = _round_amt(group["ip_amount"])
            total = _round_amt(op_amount + ip_amount)
            rows.append(
                {
                    "code": code,
                    "seq": seq,
                    "label": label,
                    "op_count": op_count,
                    "ip_count": ip_count,
                    "op_amount": op_amount,
                    "ip_amount": ip_amount,
                    "total": total,
                    "op_amount_disp": _fmt_amt(op_amount),
                    "ip_amount_disp": _fmt_amt(ip_amount),
                    "total_disp": _fmt_amt(total),
                }
            )
        rows.sort(key=lambda row: (row["seq"], row["code"]))
        for index, row in enumerate(rows, 1):
            row["no"] = index

        def _split_op_ip(amount, ticket):
            types = ticket_types.get(ticket) or set()
            if types == {"ip"}:
                return 0.0, amount
            return amount, 0.0

        cash_op = cash_ip = 0.0
        card_op = card_ip = 0.0
        transfer_op = transfer_ip = 0.0
        entitlement_ar = 0.0
        for pay in payment_lines:
            method = (pay.payment_method_code or "").strip().lower()
            pmap = pay.payment_method_map_id
            is_entitlement = bool(
                (pmap and pmap.is_entitlement) or method in ENTITLEMENT_TENDER_CODES
            )
            amount = pay.amount or 0.0
            if is_entitlement:
                entitlement_ar += amount
                continue
            if is_advance_apply_code(method):
                continue
            op_amt, ip_amt = _split_op_ip(
                amount, (pay.ticket_external_id or "").strip()
            )
            if is_advance_in_code(method) or method in ("cash",):
                cash_op += op_amt
                cash_ip += ip_amt
            elif method in CREDIT_CARD_CODES:
                card_op += op_amt
                card_ip += ip_amt
            elif method in TRANSFER_CODES:
                transfer_op += op_amt
                transfer_ip += ip_amt
            else:
                cash_op += op_amt
                cash_ip += ip_amt

        total_op = _round_amt(sum(row["op_amount"] for row in rows))
        total_ip = _round_amt(sum(row["ip_amount"] for row in rows))
        grand_total = _round_amt(total_op + total_ip)
        receipt_count = options.get("receipt_count")
        if not receipt_count:
            receipt_count = len(all_tickets) if all_tickets else no_ticket_count
        tickets_sorted = sorted(all_tickets)
        receipt_from = options.get("receipt_from") or (
            tickets_sorted[0] if tickets_sorted else ""
        )
        receipt_to = options.get("receipt_to") or (
            tickets_sorted[-1] if tickets_sorted else ""
        )
        currency = (
            batches[:1].currency_id
            if batches
            else company.currency_id or self.env.company.currency_id
        )
        return {
            "rows": rows,
            "total_op_count": sum(row["op_count"] for row in rows),
            "total_ip_count": sum(row["ip_count"] for row in rows),
            "total_op": total_op,
            "total_ip": total_ip,
            "grand_total": grand_total,
            "total_op_disp": _fmt_amt(total_op),
            "total_ip_disp": _fmt_amt(total_ip),
            "grand_total_disp": _fmt_amt(grand_total),
            "receipt_count": receipt_count,
            "receipt_from": receipt_from,
            "receipt_to": receipt_to,
            "cancelled_count": options.get("cancelled_count") or 0,
            "cash_op": _round_amt(cash_op),
            "cash_ip": _round_amt(cash_ip),
            "card_op": _round_amt(card_op),
            "card_ip": _round_amt(card_ip),
            "transfer_op": _round_amt(transfer_op),
            "transfer_ip": _round_amt(transfer_ip),
            "entitlement_ar": _round_amt(entitlement_ar),
            "cash_op_disp": _fmt_amt(cash_op),
            "cash_ip_disp": _fmt_amt(cash_ip),
            "card_op_disp": _fmt_amt(card_op),
            "card_ip_disp": _fmt_amt(card_ip),
            "transfer_op_disp": _fmt_amt(transfer_op),
            "transfer_ip_disp": _fmt_amt(transfer_ip),
            "entitlement_ar_disp": _fmt_amt(entitlement_ar),
            "amount_in_words": self._remittance_amount_in_words(
                currency, grand_total
            ),
            "batch_names": ", ".join(batches.mapped("name")),
            "ticket_count": len(all_tickets),
        }

    @api.model
    def _remittance_amount_in_words(self, currency, amount):
        if not currency:
            return ""
        try:
            return currency.with_context(lang="th_TH").amount_to_text(amount)
        except Exception:
            return currency.amount_to_text(amount)


class HisRemittanceWizard(models.TransientModel):
    _name = "vpk.his.remittance.wizard"
    _description = "ใบนำส่งเงิน HIS"

    date_from = fields.Date(
        string="ตั้งแต่วันที่",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string="ถึงวันที่",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    datetime_from = fields.Datetime(string="ตั้งแต่เวลา")
    datetime_to = fields.Datetime(string="ถึงเวลา")
    shift = fields.Char(string="กะ")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    batch_ids = fields.Many2many(
        "vpk.his.batch",
        string="ชุด HIS",
        domain="[('batch_type', '=', 'revenue'), ('company_id', '=', company_id)]",
    )
    cashier_name = fields.Char(
        string="ผู้ส่งเงิน",
        default=lambda self: self.env.user.name,
    )
    cashier_job = fields.Char(
        string="ตำแหน่ง",
        default=lambda self: self._default_cashier_job(),
    )
    receipt_from = fields.Char(string="ใบเสร็จเลขที่เริ่ม")
    receipt_to = fields.Char(string="ใบเสร็จเลขที่สิ้นสุด")
    receipt_count = fields.Integer(
        string="จำนวนใบเสร็จ",
        help="เว้น 0 เพื่อให้นับจากรหัสใบเสร็จในชุด HIS",
    )
    cancelled_count = fields.Integer(string="จำนวนใบเสร็จที่ยกเลิก")

    @api.model
    def _default_cashier_job(self):
        user = self.env.user
        if "employee_id" in user._fields and user.employee_id:
            employee = user.employee_id
            if employee.job_id:
                return employee.job_id.name
            if getattr(employee, "job_title", False):
                return employee.job_title
        return user.partner_id.function or ""

    def _get_batches(self):
        self.ensure_one()
        if self.batch_ids:
            return self.batch_ids.filtered(lambda b: b.batch_type == "revenue")
        domain = [
            ("company_id", "=", self.company_id.id),
            ("batch_type", "=", "revenue"),
            ("business_date", ">=", self.date_from),
            ("business_date", "<=", self.date_to),
            ("state", "in", ("ready", "posted")),
        ]
        if self.shift:
            domain.append(("shift", "=", self.shift))
        return self.env["vpk.his.batch"].search(domain)

    def prepare_report_data(self):
        self.ensure_one()
        batches = self._get_batches()
        data = self.env["vpk.his.batch"].prepare_remittance_data(
            batches,
            options={
                "company": self.company_id,
                "receipt_from": self.receipt_from,
                "receipt_to": self.receipt_to,
                "receipt_count": self.receipt_count,
                "cancelled_count": self.cancelled_count,
            },
        )
        data.update(self._header_values(batches))
        return data

    def _header_values(self, batches):
        self.ensure_one()
        dt_from = self.datetime_from
        dt_to = self.datetime_to
        if batches and not dt_from:
            create_dates = batches.mapped("create_date")
            dt_from = min(create_dates) if create_dates else False
        if batches and not dt_to:
            write_dates = batches.mapped("write_date")
            dt_to = max(write_dates) if write_dates else False
        printed_at = fields.Datetime.now()
        try:
            terminal = socket.gethostname() or ""
        except Exception:
            terminal = ""
        return {
            "hospital_name": self.company_id.name,
            "cashier_name": self.cashier_name or self.env.user.name,
            "cashier_job": self.cashier_job or "",
            "shift": self.shift or (batches[:1].shift if batches else ""),
            "date_from_disp": self._format_be(self.date_from),
            "date_to_disp": self._format_be(self.date_to),
            "datetime_from_disp": self._format_be(dt_from or self.date_from),
            "datetime_to_disp": self._format_be(dt_to or self.date_to),
            "printed_at_disp": self._format_be(printed_at),
            "terminal": terminal or self.env.user.login,
            "printer_user": self.env.user.name,
        }

    def _format_be(self, value):
        if not value:
            return ""
        if isinstance(value, datetime):
            local = fields.Datetime.context_timestamp(self, value)
            return "%d/%d/%d %s" % (
                local.day,
                local.month,
                local.year + 543,
                local.strftime("%H:%M:%S"),
            )
        if isinstance(value, date):
            return "%d/%d/%d" % (value.day, value.month, value.year + 543)
        return str(value)

    def action_print(self):
        self.ensure_one()
        if not self._get_batches():
            raise UserError(_("ไม่มีชุดรายได้ HIS ในช่วงวันที่ที่เลือก"))
        return self.env.ref(
            "vpk_his_api.action_report_his_remittance"
        ).with_context(discard_logo_check=True).report_action(self)
