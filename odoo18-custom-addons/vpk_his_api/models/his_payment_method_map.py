# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


METHOD_ALIASES = {
    "prepaid": "advance",
    "deposit": "advance",
    "advance_apply": "advance",
    "prepaid_in": "advance_in",
    "deposit_in": "advance_in",
}
ADVANCE_APPLY_CODES = frozenset(
    {"advance", "prepaid", "deposit", "advance_apply"}
)
ADVANCE_IN_CODES = frozenset({"advance_in", "prepaid_in", "deposit_in"})


def canonical_payment_method_code(code):
    return METHOD_ALIASES.get((code or "").strip().lower(), (code or "").strip().lower())


def is_advance_apply_code(code):
    return canonical_payment_method_code(code) == "advance"


def is_advance_in_code(code):
    return canonical_payment_method_code(code) == "advance_in"


class HisPaymentMethodMap(models.Model):
    _name = "vpk.his.payment.method.map"
    _description = "HIS Payment Method Mapping"
    _order = "code"
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char(
        required=True,
        index=True,
        help="รหัสวิธีรับเงินที่ HIS ส่งมา เช่น cash, transfer, credit_card, "
        "advance, advance_in, ar_claim",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        check_company=True,
        domain="[('type', 'in', ('cash', 'bank'))]",
    )
    journal_type = fields.Selection(
        [("cash", "Cash"), ("bank", "Bank")],
        help="ใช้ตอน auto-bind ถ้ายังไม่ได้ผูกสมุดรายวัน",
    )
    is_entitlement = fields.Boolean(
        string="ประเภทสิทธิ์ (พักลูกหนี้)",
        default=False,
        help="รับชำระแบบ POS ด้วยสิทธิ์: ไม่ลงเงินสด/ธนาคาร "
        "แต่ตั้งลูกหนี้สิทธิ์ให้อยู่ใน aging จนกองทุนโอนมาเคลียร์",
    )
    create_payment = fields.Boolean(
        default=True,
        help="ติ๊กเมื่อเป็นเงินสด/โอน/บัตร ที่รับจริงที่เคาน์เตอร์ "
        "ไม่ติ๊กเมื่อเป็นประเภทสิทธิ์ (พักลูกหนี้)",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "uniq_code_company",
            "unique(code, company_id)",
            "Payment method mapping must be unique per code and company.",
        ),
    ]

    @api.model
    def _normalize_code(self, code):
        return (code or "").strip().lower()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = self._normalize_code(vals["code"])
            if vals.get("is_entitlement"):
                vals["create_payment"] = False
                vals["journal_id"] = False
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            vals = dict(vals, code=self._normalize_code(vals["code"]))
        if vals.get("is_entitlement"):
            vals = dict(vals, create_payment=False, journal_id=False)
        return super().write(vals)

    @api.onchange("is_entitlement")
    def _onchange_is_entitlement(self):
        if self.is_entitlement:
            self.create_payment = False
            self.journal_id = False
            self.journal_type = False

    @api.model
    def find_map(self, code, company=None):
        code = canonical_payment_method_code(code)
        if not code:
            return self.browse()
        company = company or self.env.company
        return self.search(
            [("code", "=", code), ("company_id", "=", company.id), ("active", "=", True)],
            limit=1,
        )

    @api.model
    def _bind_entitlement_tenders(self, company=None):
        """POS-style entitlement tenders: park as AR, never cash journals."""
        company = company or self.env.company
        specs = [
            ("ar_claim", "ลูกหนี้สิทธิ์", False),
            ("sso", "สิทธิ์ประกันสังคม", "SSO"),
            ("uc", "สิทธิ์ UC / บัตรทอง", "UC"),
            ("csmbs", "สิทธิ์เบิกจ่ายตรง", "CSMBS"),
        ]
        Map = self.sudo()
        for code, name, _ent in specs:
            rec = Map.search(
                [("code", "=", code), ("company_id", "=", company.id)],
                limit=1,
            )
            vals = {
                "name": name,
                "is_entitlement": True,
                "create_payment": False,
                "journal_id": False,
                "journal_type": False,
                "company_id": company.id,
            }
            if rec:
                rec.write(vals)
            else:
                Map.create(dict(vals, code=code))
        self._bind_advance_tenders(company)

    @api.model
    def _bind_advance_tenders(self, company=None):
        """Prepaid: receive cash into liability, later apply against the visit bill."""
        company = company or self.env.company
        Map = self.sudo()
        specs = [
            ("advance", "ตัดเงินล่วงหน้า", True),
            ("advance_in", "รับเงินล่วงหน้า", False),
        ]
        for code, name, create_payment in specs:
            rec = Map.search(
                [("code", "=", code), ("company_id", "=", company.id)],
                limit=1,
            )
            vals = {
                "name": name,
                "is_entitlement": False,
                "create_payment": create_payment,
                "company_id": company.id,
            }
            if rec:
                rec.write(vals)
            else:
                Map.create(dict(vals, code=code))

    def _auto_bind(self):
        Journal = self.env["account.journal"].sudo()
        company = self.env.company
        self._bind_entitlement_tenders(company)
        for rec in self.sudo().search([]):
            if rec.is_entitlement or rec.code in (
                "sso",
                "uc",
                "csmbs",
                "ar_claim",
                "advance",
                "advance_in",
            ):
                if rec.is_entitlement and rec.journal_id:
                    rec.journal_id = False
                continue
            if rec.journal_id or not rec.journal_type or not rec.create_payment:
                continue
            journal = Journal.search(
                [("type", "=", rec.journal_type), ("company_id", "=", company.id)],
                limit=1,
            )
            if journal:
                rec.journal_id = journal.id
        self.env["vpk.his.receipt.journal.mixin"]._bind_sso_receipt_journal(company)
        self.env["vpk.his.receipt.journal.mixin"]._bind_his_cash_journal(company)
        self.env["vpk.his.receipt.journal.mixin"]._bind_his_advance_journal(company)

    def action_auto_bind(self):
        self._auto_bind()
        return True
