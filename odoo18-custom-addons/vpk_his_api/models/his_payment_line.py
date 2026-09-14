# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.tools.float_utils import float_is_zero

from .his_payment_method_map import is_advance_apply_code, is_advance_in_code

LINE_STATES = [
    ("ok", "OK"),
    ("error", "Error"),
]

METHOD_TO_ENTITLEMENT = {
    "sso": "SSO",
    "uc": "UC",
    "csmbs": "CSMBS",
}


class HisPaymentLine(models.Model):
    _name = "vpk.his.payment.line"
    _description = "HIS Revenue Payment Line"
    _order = "id"

    batch_id = fields.Many2one(
        "vpk.his.batch", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    line_external_id = fields.Char(index=True)
    payment_method_code = fields.Char(required=True)
    payment_method_map_id = fields.Many2one(
        "vpk.his.payment.method.map", ondelete="set null"
    )
    entitlement_code = fields.Char()
    entitlement_map_id = fields.Many2one("vpk.his.entitlement.map", ondelete="set null")
    ticket_external_id = fields.Char(
        index=True,
        help="รหัสใบรับบริการ/ใบเสร็จ POS ของคนไข้ ใช้เมื่อจ่ายหลายสิทธิ์ในใบเดียว",
    )
    service_type = fields.Selection(
        [("op", "OP"), ("ip", "IP")],
        help="ประเภทบริการของใบนี้ ถ้าว่างจะอนุมานจากบรรทัดขายในใบเดียวกัน",
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related="batch_id.currency_id")
    journal_code = fields.Char()
    journal_id = fields.Many2one("account.journal")
    payment_id = fields.Many2one("account.payment", ondelete="set null")
    line_state = fields.Selection(LINE_STATES, default="ok")
    error_message = fields.Text()

    def _validate_line(self):
        self.ensure_one()
        errors = []
        PMap = self.env["vpk.his.payment.method.map"]
        EMap = self.env["vpk.his.entitlement.map"]
        pmap = PMap.find_map(self.payment_method_code, company=self.company_id)
        self.payment_method_map_id = pmap.id if pmap else False
        if not pmap:
            errors.append(
                _("No payment method mapping for %s") % self.payment_method_code
            )
        is_entitlement = bool(pmap and pmap.is_entitlement)
        is_advance_in = is_advance_in_code(self.payment_method_code)
        is_advance_apply = is_advance_apply_code(self.payment_method_code)
        if is_entitlement and not self.entitlement_code:
            inferred = METHOD_TO_ENTITLEMENT.get((self.payment_method_code or "").lower())
            if inferred:
                self.entitlement_code = inferred
        journal = self.env["account.journal"]
        if self.journal_code:
            journal = self.env["account.journal"].search(
                [
                    ("code", "=", self.journal_code),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if not journal:
                errors.append(_("Unknown journal code %s") % self.journal_code)
        elif pmap and pmap.create_payment and not is_entitlement:
            journal = pmap.journal_id
            if not journal:
                errors.append(
                    _("Payment method %s has no journal") % self.payment_method_code
                )
        elif is_advance_in:
            journal = pmap.journal_id if pmap else self.env["account.journal"]
            if not journal:
                journal = self.env["vpk.his.receipt.journal.mixin"]._ensure_his_cash_journal(
                    self.company_id
                )
        self.journal_id = journal.id if journal else False
        if is_entitlement and not self.entitlement_code:
            errors.append(
                _("Entitlement payment %s requires entitlement_code")
                % self.payment_method_code
            )
        service_type = self._infer_service_type()
        if service_type:
            self.service_type = service_type
        if not self.entitlement_code and not is_entitlement:
            inferred = self._infer_self_pay_code()
            if not inferred and (is_advance_apply or is_advance_in):
                inferred = "SELF_PAY"
            self.entitlement_code = inferred
        if self.entitlement_code:
            emap = EMap.find_map(
                self.entitlement_code,
                service_type=self.service_type or "op",
                company=self.company_id,
            )
            self.entitlement_map_id = emap.id if emap else False
            if not emap:
                errors.append(
                    _("No entitlement mapping for payment %s") % self.entitlement_code
                )
        if float_is_zero(self.amount, precision_digits=2):
            errors.append(_("Payment amount must not be zero"))
        self.line_state = "error" if errors else "ok"
        self.error_message = "\n".join(errors) if errors else False
        return not errors

    def _sale_lines_for_ticket(self):
        self.ensure_one()
        sales = self.batch_id.sale_line_ids
        ticket = (self.ticket_external_id or "").strip()
        if ticket:
            matched = sales.filtered(
                lambda l: (l.ticket_external_id or "").strip() == ticket
            )
            if matched:
                return matched
        return sales

    def _infer_service_type(self):
        self.ensure_one()
        if self.service_type in ("op", "ip"):
            return self.service_type
        sales = self._sale_lines_for_ticket()
        if self.entitlement_code:
            same_right = sales.filtered(
                lambda l: (l.entitlement_code or "").upper()
                == (self.entitlement_code or "").upper()
            )
            if same_right:
                sales = same_right
        types = {st for st in sales.mapped("service_type") if st}
        if types == {"ip"} or ("ip" in types and "op" not in types):
            return "ip"
        if types == {"op"}:
            return "op"
        if "ip" in types:
            return "ip"
        return "op"

    def _infer_self_pay_code(self):
        """Cash/card/transfer without entitlement_code pairs to SELF_PAY on the ticket."""
        self.ensure_one()
        sales = self._sale_lines_for_ticket().filtered(
            lambda l: (l.entitlement_code or "").upper() == "SELF_PAY"
        )
        return "SELF_PAY" if sales else False
