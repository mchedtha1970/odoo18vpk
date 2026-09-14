# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


SERVICE_TYPES = [
    ("op", "OP"),
    ("ip", "IP"),
    ("both", "OP/IP"),
]

ITEM_TYPES = [
    ("all", "ทุกรายการ"),
    ("service", "ค่าบริการ"),
    ("drug", "ยา"),
    ("medical_supply", "เวชภัณฑ์"),
    ("lab", "แล็บ"),
    ("other", "อื่นๆ"),
]


class HisEntitlementMap(models.Model):
    _name = "vpk.his.entitlement.map"
    _description = "HIS Entitlement Mapping"
    _order = "code, service_type, item_type"
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char(
        required=True,
        index=True,
        help="รหัสสิทธิ์ที่ HIS ส่งมา เช่น SELF_PAY, UC, SSO, CSMBS",
    )
    service_type = fields.Selection(SERVICE_TYPES, required=True, default="op")
    item_type = fields.Selection(
        ITEM_TYPES,
        default="all",
        required=True,
        help="all = ค่าเริ่มต้นของสิทธิ์+ประเภทบริการนี้",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Payer",
        required=True,
        check_company=True,
        ondelete="restrict",
    )
    income_account_id = fields.Many2one(
        "account.account",
        string="Income Account",
        domain="[('account_type', 'in', ('income', 'income_other'))]",
    )
    receivable_account_id = fields.Many2one(
        "account.account",
        string="Receivable Account",
        domain="[('account_type', '=', 'asset_receivable')]",
    )
    cash_account_id = fields.Many2one(
        "account.account",
        string="Cash Account",
        domain="[('account_type', '=', 'asset_cash')]",
    )
    receipt_journal_id = fields.Many2one(
        "account.journal",
        string="Entitlement Receipt Journal",
        check_company=True,
        domain="[('type', 'in', ('cash', 'bank'))]",
        help="สมุดรับชำระจากสิทธิ์ ยอดพักรอเคลียร์จนกองทุนโอนเงินเข้าบัญชีโรงพยาบาล",
    )
    income_account_code = fields.Char(
        help="รหัสบัญชีรายได้ใน CoA (ใช้ตอน auto-bind)",
    )
    receivable_account_code = fields.Char(
        help="รหัสบัญชีลูกหนี้ใน CoA (ใช้ตอน auto-bind)",
    )
    cash_account_code = fields.Char(
        help="รหัสบัญชีเงินสดใน CoA (ใช้ตอน auto-bind)",
    )
    create_payment = fields.Boolean(
        default=False,
        help="ถ้าติ๊ก จะจับคู่รับเงินสด/โอนกับใบแจ้งหนี้ของสิทธิ์นี้",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True)
    remittance_sequence = fields.Integer(
        string="ลำดับใบนำส่งเงิน",
        help="เรียงแถวในรายงานใบนำส่งเงิน ให้ตรงรหัสสิทธิ์ของ รพ. เช่น 13, 30, 51",
    )
    remittance_label = fields.Char(
        string="ชื่อในใบนำส่งเงิน",
        help="เช่น (13) เงินสด, (30) ปกส. (รพ.วชิระภูเก็ต)",
    )

    REMITTANCE_DEFAULTS = {
        "SELF_PAY": (13, "(13) เงินสด"),
        "CSMBS": (26, "(26) โครงการจ่ายตรง"),
        "SSO": (30, "(30) ปกส. (รพ.วชิระภูเก็ต)"),
        "UC": (51, "(51) บัตรทอง / UC"),
    }

    _sql_constraints = [
        (
            "uniq_code_service_item_company",
            "unique(code, service_type, item_type, company_id)",
            "Entitlement mapping must be unique per code, service type, item type and company.",
        ),
    ]

    @api.model
    def _normalize_code(self, code):
        return (code or "").strip().upper()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = self._normalize_code(vals["code"])
            default = self.REMITTANCE_DEFAULTS.get(vals.get("code") or "")
            if default:
                vals.setdefault("remittance_sequence", default[0])
                vals.setdefault("remittance_label", default[1])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            vals = dict(vals, code=self._normalize_code(vals["code"]))
        return super().write(vals)

    @api.model
    def find_map(self, code, service_type=None, item_type=None, company=None):
        """Resolve mapping with fallbacks: exact item_type → default item → both."""
        code = self._normalize_code(code)
        if not code:
            return self.browse()
        company = company or self.env.company
        service_type = (service_type or "op").lower()
        item_type = item_type or "all"
        domain_base = [
            ("code", "=", code),
            ("company_id", "=", company.id),
            ("active", "=", True),
        ]
        candidates = [
            [("service_type", "=", service_type), ("item_type", "=", item_type)],
            [("service_type", "=", service_type), ("item_type", "=", "all")],
            [("service_type", "=", "both"), ("item_type", "=", item_type)],
            [("service_type", "=", "both"), ("item_type", "=", "all")],
        ]
        for extra in candidates:
            rec = self.search(domain_base + extra, limit=1)
            if rec:
                return rec
        return self.browse()

    @api.model
    def _find_account_by_code(self, code):
        if not code:
            return self.env["account.account"]
        Account = self.env["account.account"].sudo()
        company = self.env.company
        rec = Account.search(
            [
                ("code", "=", code),
                ("deprecated", "=", False),
                ("company_ids", "in", company.id),
            ],
            limit=1,
        )
        if rec:
            return rec
        rec = Account.search(
            [("code", "=", code), ("deprecated", "=", False)], limit=1
        )
        if rec:
            return rec
        return Account.search(
            [
                ("code", "=like", code + "%"),
                ("deprecated", "=", False),
                ("company_ids", "in", company.id),
            ],
            limit=1,
        )

    @api.model
    def _resolve_income_account(self, rec):
        """Bind income from the mapped code, then hospital CoA fallbacks."""
        if rec.income_account_id:
            return rec.income_account_id
        codes = []
        if rec.income_account_code:
            codes.append(rec.income_account_code)
        # รพ.วชิระภูเก็ต ไม่มี 4301020106.304 — ใช้รายได้ SSO IP-เครือข่าย / กองทุน
        if rec.code == "SSO" and rec.service_type == "ip":
            codes.extend(["4301020106.306", "4301020106.303"])
        seen = set()
        for code in codes:
            if not code or code in seen:
                continue
            seen.add(code)
            acc = rec._find_account_by_code(code)
            if acc:
                return acc
        if rec.service_type == "ip":
            op_map = self.search(
                [
                    ("code", "=", rec.code),
                    ("service_type", "=", "op"),
                    ("item_type", "=", rec.item_type),
                    ("company_id", "=", rec.company_id.id),
                    ("active", "=", True),
                    ("income_account_id", "!=", False),
                ],
                limit=1,
            )
            if op_map:
                return op_map.income_account_id
        return self.env["account.account"]

    @api.model
    def _auto_bind(self):
        """Fill account_id fields from stored account codes when CoA exists."""
        maps = self.sudo().search([])
        for rec in maps:
            vals = {}
            if not rec.income_account_id:
                acc = self._resolve_income_account(rec)
                if acc:
                    vals["income_account_id"] = acc.id
            if not rec.receivable_account_id and rec.receivable_account_code:
                acc = rec._find_account_by_code(rec.receivable_account_code)
                if acc:
                    vals["receivable_account_id"] = acc.id
            if not rec.cash_account_id and rec.cash_account_code:
                acc = rec._find_account_by_code(rec.cash_account_code)
                if acc:
                    vals["cash_account_id"] = acc.id
            if vals:
                rec.write(vals)
            if (
                rec.receivable_account_id
                and rec.partner_id
                and rec.receivable_account_id.account_type == "asset_receivable"
            ):
                rec.partner_id.sudo().with_company(rec.company_id).write(
                    {"property_account_receivable_id": rec.receivable_account_id.id}
                )

    def _register_hook(self):
        super()._register_hook()
        try:
            self.env["vpk.his.payment.method.map"]._bind_entitlement_tenders()
            self.env["vpk.his.receipt.journal.mixin"]._bind_sso_receipt_journal()
            self.env["vpk.his.receipt.journal.mixin"]._bind_his_cash_journal()
            self.env["vpk.his.receipt.journal.mixin"]._bind_his_advance_journal()
            self.env["vpk.his.entitlement.map"]._auto_bind()
            self.env["vpk.his.entitlement.map"]._tag_entitlement_payers()
            self.env["vpk.his.entitlement.map"]._ensure_remittance_labels()
        except Exception:
            _logger.exception("Could not ensure HIS entitlement POS tenders")

    def action_auto_bind(self):
        self._auto_bind()
        self.env["vpk.his.payment.method.map"]._bind_entitlement_tenders(
            self.env.company
        )
        self.env["vpk.his.receipt.journal.mixin"]._bind_sso_receipt_journal(
            self.env.company
        )
        self.env["vpk.his.receipt.journal.mixin"]._bind_his_cash_journal(
            self.env.company
        )
        self.env["vpk.his.receipt.journal.mixin"]._bind_his_advance_journal(
            self.env.company
        )
        self._tag_entitlement_payers()
        self._ensure_remittance_labels()
        return True

    @api.model
    def _ensure_remittance_labels(self):
        """Fill hospital remittance names on existing maps when still blank."""
        for rec in self.sudo().search([]):
            default = self.REMITTANCE_DEFAULTS.get(rec.code)
            if not default:
                continue
            vals = {}
            if not rec.remittance_sequence:
                vals["remittance_sequence"] = default[0]
            if not rec.remittance_label:
                vals["remittance_label"] = default[1]
            if vals:
                rec.write(vals)

    @api.model
    def remittance_display(self, code, company=None):
        """Sequence and label for ใบนำส่งเงิน, with hospital defaults."""
        code = self._normalize_code(code)
        company = company or self.env.company
        maps = self.search(
            [
                ("code", "=", code),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ]
        )
        emap = maps[:1]
        for rec in maps:
            if rec.remittance_label or rec.remittance_sequence:
                emap = rec
                break
        default = self.REMITTANCE_DEFAULTS.get(code, (99, code))
        seq = (emap.remittance_sequence if emap else 0) or default[0]
        if emap and emap.remittance_label:
            label = emap.remittance_label
        elif default[1] != code:
            label = default[1]
        elif emap:
            label = emap.name
        else:
            label = code
        return seq, label, emap

    @api.model
    def _tag_entitlement_payers(self):
        """Tag fund and IPD patient payers so open invoices appear on AR."""
        fund_cat = self.env.ref(
            "vpk_his_api.partner_category_entitlement_payer", raise_if_not_found=False
        )
        if not fund_cat:
            fund_cat = self.env["res.partner.category"].sudo().search(
                [("name", "=", "ลูกหนี้สิทธิ HIS")], limit=1
            )
        if not fund_cat:
            fund_cat = self.env["res.partner.category"].sudo().create(
                {"name": "ลูกหนี้สิทธิ HIS"}
            )
        ipd_cat = self.env.ref(
            "vpk_his_api.partner_category_ipd_patient", raise_if_not_found=False
        )
        if not ipd_cat:
            ipd_cat = self.env["res.partner.category"].sudo().search(
                [("name", "=", "ลูกหนี้คนไข้ IPD HIS")], limit=1
            )
        if not ipd_cat:
            ipd_cat = self.env["res.partner.category"].sudo().create(
                {"name": "ลูกหนี้คนไข้ IPD HIS"}
            )
        fund_maps = self.sudo().search(
            [("code", "in", ("UC", "SSO", "CSMBS")), ("active", "=", True)]
        )
        ipd_maps = self.sudo().search(
            [
                ("code", "=", "SELF_PAY"),
                ("service_type", "=", "ip"),
                ("active", "=", True),
            ]
        )
        for partner in fund_maps.mapped("partner_id"):
            if fund_cat not in partner.category_id:
                partner.write({"category_id": [(4, fund_cat.id)]})
            partner.with_company(self.env.company).write(
                {"property_inbound_payment_method_line_id": False}
            )
        for partner in ipd_maps.mapped("partner_id"):
            if ipd_cat not in partner.category_id:
                partner.write({"category_id": [(4, ipd_cat.id)]})
            partner.with_company(self.env.company).write(
                {"property_inbound_payment_method_line_id": False}
            )
        return fund_cat | ipd_cat

    @api.model
    def _outstanding_ar_partners(self):
        maps = self.search(
            [
                ("active", "=", True),
                ("company_id", "=", self.env.company.id),
                "|",
                ("code", "in", ("UC", "SSO", "CSMBS")),
                "&",
                ("code", "=", "SELF_PAY"),
                ("service_type", "=", "ip"),
            ]
        )
        return maps.mapped("partner_id")

    def action_open_outstanding_ar(self):
        partners = self._outstanding_ar_partners()
        search_view = self.env.ref(
            "vpk_his_api.view_his_outstanding_ar_search", raise_if_not_found=False
        )
        result = {
            "type": "ir.actions.act_window",
            "name": _("ลูกหนี้คงค้าง"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "in", partners.ids),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial", "in_payment")),
            ],
            "context": {
                "default_move_type": "out_invoice",
                "search_default_unpaid": 1,
            },
        }
        if search_view:
            result["search_view_id"] = [search_view.id, "search"]
        return result

    def action_open_aged_receivable(self):
        action = self.env.ref(
            "account_reports.action_account_report_ar", raise_if_not_found=False
        )
        if not action:
            return self.action_open_outstanding_ar()
        result = action.sudo().read()[0]
        result["name"] = _("Aged Receivable — ลูกหนี้สิทธิ")
        return result
