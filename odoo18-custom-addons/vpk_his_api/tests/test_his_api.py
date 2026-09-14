# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase


@tagged("post_install", "-at_install")
class TestHisApiCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["vpk.his.api.service"]
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("vpk_his_api.api_key", "test-his-key")
        ICP.set_param("vpk_his_api.enabled", "True")
        self._ensure_accounts()
        self.env["vpk.his.entitlement.map"]._auto_bind()
        self.env["vpk.his.payment.method.map"]._auto_bind()
        income = self.env["account.account"].search(
            [
                ("deprecated", "=", False),
                ("account_type", "=", "income"),
                ("code", "=", "4301020104.106"),
            ],
            limit=1,
        ) or self.env["account.account"].search(
            [("deprecated", "=", False), ("account_type", "=", "income")],
            limit=1,
        )
        receivable = self.env["account.account"].search(
            [
                ("deprecated", "=", False),
                ("account_type", "=", "asset_receivable"),
                ("code", "=", "1102050102.106"),
            ],
            limit=1,
        ) or self.env["account.account"].search(
            [("deprecated", "=", False), ("account_type", "=", "asset_receivable")],
            limit=1,
        )
        if income and receivable:
            for emap in self.env["vpk.his.entitlement.map"].search([]):
                emap.write(
                    {
                        "income_account_id": income.id,
                        "receivable_account_id": receivable.id,
                    }
                )
                emap.partner_id.with_company(self.env.company).write(
                    {"property_account_receivable_id": receivable.id}
                )
        if income:
            Journal = self.env["account.journal"]
            if not Journal.search(
                [("code", "=", "HINV"), ("company_id", "=", self.env.company.id)],
                limit=1,
            ):
                Journal.create(
                    {
                        "name": "HIS Invoices",
                        "code": "HINV",
                        "type": "sale",
                        "default_account_id": income.id,
                        "company_id": self.env.company.id,
                    }
                )
        cash_acc = self.env["account.account"].search(
            [
                ("deprecated", "=", False),
                ("account_type", "=", "asset_cash"),
            ],
            limit=1,
        )
        if cash_acc:
            Journal = self.env["account.journal"]
            cash_journal = Journal.search(
                [("code", "=", "HCSH"), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            if not cash_journal:
                cash_journal = Journal.create(
                    {
                        "name": "HIS Cash",
                        "code": "HCSH",
                        "type": "cash",
                        "default_account_id": cash_acc.id,
                        "company_id": self.env.company.id,
                    }
                )
            for method_line in cash_journal.inbound_payment_method_line_ids:
                if (
                    not method_line.payment_account_id
                    or method_line.payment_account_id.deprecated
                ):
                    method_line.payment_account_id = cash_acc.id
            cash_map = self.env["vpk.his.payment.method.map"].search(
                [
                    ("code", "=", "cash"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
            if cash_map:
                cash_map.journal_id = cash_journal.id

    def _ensure_accounts(self):
        Account = self.env["account.account"].sudo()
        specs = [
            ("4301020104.106", "รายได้ค่ารักษาชำระเงิน OP", "income", False),
            ("4301020104.107", "รายได้ค่ารักษาชำระเงิน IP", "income", False),
            ("4301020105.201", "รายได้ UC OP", "income", False),
            ("4301020105.202", "รายได้ UC IP", "income", False),
            ("4301020106.303", "รายได้ SSO OP", "income", False),
            ("4301020106.304", "รายได้ SSO IP", "income", False),
            ("4301020106.306", "รายได้ค่ารักษาประกันสังคม IP-เครือข่าย", "income", False),
            ("4301020104.401", "รายได้ CSMBS OP", "income", False),
            ("4301020104.402", "รายได้ CSMBS IP", "income", False),
            ("1102050102.106", "ลูกหนี้ชำระเอง OP", "asset_receivable", True),
            ("1102050102.107", "ลูกหนี้ชำระเอง IP", "asset_receivable", True),
            ("1102050101.201", "ลูกหนี้ UC OP", "asset_receivable", True),
            ("1102050101.202", "ลูกหนี้ UC IP", "asset_receivable", True),
            ("1102050101.301", "ลูกหนี้ SSO OP", "asset_receivable", True),
            ("1102050101.302", "ลูกหนี้ SSO IP", "asset_receivable", True),
            ("1102050101.401", "ลูกหนี้ CSMBS OP", "asset_receivable", True),
            ("1102050101.402", "ลูกหนี้ CSMBS IP", "asset_receivable", True),
            ("1101010101.101", "เงินสด HIS", "asset_cash", False),
            ("2103010103.101", "รายได้ค่าบริการอื่นรับล่วงหน้า", "liability_current", False),
        ]
        for code, name, acc_type, reconcile in specs:
            existing = Account.search([("code", "=", code)], limit=1)
            if existing:
                continue
            vals = {
                "code": code,
                "name": name,
                "account_type": acc_type,
                "reconcile": reconcile,
            }
            Account.create(vals)

    def _revenue_payload(self, external_id="HIS-REV-TEST-001"):
        return {
            "external_id": external_id,
            "source_system": "front_his",
            "business_date": "2026-08-22",
            "sales": [
                {
                    "line_external_id": "S1",
                    "entitlement_code": "SELF_PAY",
                    "service_type": "op",
                    "item_type": "service",
                    "amount_total": 150000.00,
                },
                {
                    "line_external_id": "S2",
                    "entitlement_code": "UC",
                    "service_type": "op",
                    "item_type": "drug",
                    "amount_total": 82000.00,
                },
            ],
            "payments": [
                {
                    "line_external_id": "P1",
                    "payment_method_code": "cash",
                    "entitlement_code": "SELF_PAY",
                    "amount": 150000.00,
                },
                {
                    "line_external_id": "P2",
                    "payment_method_code": "ar_claim",
                    "entitlement_code": "UC",
                    "amount": 82000.00,
                },
            ],
            "control_totals": {
                "sales_total": 232000.00,
                "payments_total": 232000.00,
            },
        }


@tagged("post_install", "-at_install")
class TestHisApiIngest(TestHisApiCommon):
    def test_ingest_revenue_ready(self):
        result = self.service.ingest_revenue(self._revenue_payload())
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "created")
        self.assertEqual(result["state"], "ready")
        self.assertEqual(result["http_status"], 202)
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        self.assertEqual(len(batch.sale_line_ids), 2)
        self.assertEqual(len(batch.payment_line_ids), 2)

    def test_ingest_idempotent_update_then_posted_replay(self):
        payload = self._revenue_payload("HIS-REV-TEST-IDEM")
        first = self.service.ingest_revenue(payload)
        payload["sales"][0]["amount_total"] = 151000.00
        payload["control_totals"]["sales_total"] = 233000.00
        payload["payments"][0]["amount"] = 151000.00
        payload["control_totals"]["payments_total"] = 233000.00
        second = self.service.ingest_revenue(payload)
        self.assertEqual(second["action"], "updated")
        self.assertEqual(second["batch_id"], first["batch_id"])
        batch = self.env["vpk.his.batch"].browse(first["batch_id"])
        batch.action_post()
        third = self.service.ingest_revenue(payload)
        self.assertEqual(third["action"], "unchanged")
        self.assertEqual(third["state"], "posted")
        self.assertEqual(third["http_status"], 200)

    def test_ingest_unknown_entitlement_error(self):
        payload = self._revenue_payload("HIS-REV-TEST-ERR")
        payload["sales"][0]["entitlement_code"] = "UNKNOWN_PAYER"
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "error")
        self.assertTrue(result["errors"])

    def test_control_total_mismatch(self):
        payload = self._revenue_payload("HIS-REV-TEST-CTRL")
        payload["control_totals"]["sales_total"] = 1.00
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "error")

    def test_requires_external_id(self):
        payload = self._revenue_payload()
        payload.pop("external_id")
        with self.assertRaises(UserError):
            self.service.ingest_revenue(payload)

    def test_strips_pii(self):
        payload = self._revenue_payload("HIS-REV-TEST-PII")
        payload["hn"] = "6500123"
        payload["patient_name"] = "ไม่ควรเก็บบันทึก"
        result = self.service.ingest_revenue(payload)
        log = self.env["vpk.his.api.log"].search(
            [("external_id", "=", "HIS-REV-TEST-PII")], limit=1
        )
        self.assertTrue(log)
        self.assertNotIn("6500123", log.request_body or "")
        self.assertNotIn("ไม่ควรเก็บบันทึก", log.request_body or "")
        self.assertEqual(result["state"], "ready")

    def test_stock_keeps_hn_vn(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        self.env["product.product"].create(
            {
                "name": "HIS HN Drug",
                "default_code": "99990",
                "is_storable": True,
                "type": "consu",
                "tracking": "none",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-HN-VN",
                "source_system": "front_his",
                "business_date": "2026-08-25",
                "issues": [
                    {
                        "product_code": "99990",
                        "warehouse_code": warehouse.code,
                        "qty": 1,
                        "hn": "6500123",
                        "vn": "6808250001",
                        "patient_name": "ต้องถูกตัดทิ้ง",
                    }
                ],
            }
        )
        self.assertEqual(result["state"], "ready", result.get("errors"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        line = batch.stock_line_ids
        self.assertEqual(line.hn, "6500123")
        self.assertEqual(line.vn, "6808250001")
        log = self.env["vpk.his.api.log"].search(
            [("external_id", "=", "HIS-STK-TEST-HN-VN")], limit=1
        )
        self.assertIn("6500123", log.request_body or "")
        self.assertIn("6808250001", log.request_body or "")
        self.assertNotIn("ต้องถูกตัดทิ้ง", log.request_body or "")

    def test_stock_patient_use_requires_hn_vn(self):
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        self.env["product.product"].create(
            {
                "name": "HIS Missing HN",
                "default_code": "99989",
                "is_storable": True,
                "type": "consu",
                "tracking": "none",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-NO-HN",
                "source_system": "front_his",
                "business_date": "2026-08-25",
                "issues": [
                    {
                        "product_code": "99989",
                        "warehouse_code": warehouse.code,
                        "qty": 1,
                        "reason": "patient_use",
                    }
                ],
            }
        )
        self.assertEqual(result["state"], "error")
        messages = " ".join(
            err.get("message") or "" for err in result["errors"]
        ).lower()
        self.assertIn("hn", messages)
        self.assertIn("vn", messages)

    def test_stock_unknown_product(self):
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-ERR",
                "source_system": "pharmacy_his",
                "business_date": "2026-08-22",
                "issues": [
                    {
                        "line_external_id": "I1",
                        "product_code": "NO-SUCH-DRUG",
                        "warehouse_code": self.env["stock.warehouse"].search([], limit=1).code,
                        "qty": 2,
                        "hn": "6500123",
                        "vn": "6808250001",
                    }
                ],
            }
        )
        self.assertEqual(result["state"], "error")


@tagged("post_install", "-at_install")
class TestHisPosting(TestHisApiCommon):
    def test_post_revenue_creates_invoice_and_payment(self):
        result = self.service.ingest_revenue(self._revenue_payload("HIS-REV-TEST-POST"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        self.assertEqual(batch.state, "ready")
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self.assertEqual(len(batch.invoice_ids), 2)
        self.assertTrue(all(inv.state == "posted" for inv in batch.invoice_ids))
        self.assertEqual(len(batch.payment_ids), 1)
        self.assertEqual(batch.payment_ids.amount, 150000.00)
        self.assertTrue(batch.payment_ids.is_reconciled or batch.invoice_ids.filtered(
            lambda m: m.partner_id == batch.payment_ids.partner_id
        ))

    def test_post_pos_style_multi_entitlement_parks_ar(self):
        self.env["vpk.his.payment.method.map"]._bind_entitlement_tenders()
        payload = {
            "external_id": "HIS-REV-TEST-POS-MULTI",
            "source_system": "front_his",
            "business_date": "2026-08-23",
            "sales": [
                {
                    "line_external_id": "T1-CASH",
                    "ticket_external_id": "POS-OPD-0001",
                    "entitlement_code": "SELF_PAY",
                    "service_type": "op",
                    "item_type": "service",
                    "amount_total": 50.00,
                },
                {
                    "line_external_id": "T1-SSO",
                    "ticket_external_id": "POS-OPD-0001",
                    "entitlement_code": "SSO",
                    "service_type": "op",
                    "item_type": "drug",
                    "amount_total": 200.00,
                },
                {
                    "line_external_id": "T1-UC",
                    "ticket_external_id": "POS-OPD-0001",
                    "entitlement_code": "UC",
                    "service_type": "op",
                    "item_type": "lab",
                    "amount_total": 80.00,
                },
            ],
            "payments": [
                {
                    "line_external_id": "T1-PAY-CASH",
                    "ticket_external_id": "POS-OPD-0001",
                    "payment_method_code": "cash",
                    "entitlement_code": "SELF_PAY",
                    "amount": 50.00,
                },
                {
                    "line_external_id": "T1-PAY-SSO",
                    "ticket_external_id": "POS-OPD-0001",
                    "payment_method_code": "sso",
                    "amount": 200.00,
                },
                {
                    "line_external_id": "T1-PAY-UC",
                    "ticket_external_id": "POS-OPD-0001",
                    "payment_method_code": "uc",
                    "amount": 80.00,
                },
            ],
            "control_totals": {"sales_total": 330.00, "payments_total": 330.00},
        }
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "ready", result.get("errors"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self.assertEqual(len(batch.invoice_ids), 3)
        self.assertEqual(len(batch.payment_ids), 1)
        self.assertEqual(batch.payment_ids.amount, 50.00)
        sso_partner = self.env.ref("vpk_his_api.partner_payer_sso_op")
        uc_partner = self.env.ref("vpk_his_api.partner_payer_uc_op")
        sso_inv = batch.invoice_ids.filtered(lambda i: i.partner_id == sso_partner)
        uc_inv = batch.invoice_ids.filtered(lambda i: i.partner_id == uc_partner)
        self.assertEqual(sso_inv.amount_residual, 200.00)
        self.assertEqual(uc_inv.amount_residual, 80.00)
        self.assertIn(sso_inv.payment_state, ("not_paid", "partial", "in_payment"))
        self.assertIn(uc_inv.payment_state, ("not_paid", "partial", "in_payment"))
        ar_lines = (sso_inv | uc_inv).line_ids.filtered(
            lambda l: l.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(ar_lines)
        self.assertTrue(all(ar_lines.mapped("date_maturity")))
        action = self.env["vpk.his.entitlement.map"].action_open_outstanding_ar()
        self.assertEqual(action["res_model"], "account.move")
        open_moves = self.env["account.move"].search(action["domain"])
        self.assertIn(sso_inv, open_moves)
        self.assertIn(uc_inv, open_moves)

    def test_post_ipd_partial_self_pay_and_entitlement_ar(self):
        self.env["vpk.his.payment.method.map"]._bind_entitlement_tenders()
        self.env["vpk.his.entitlement.map"]._tag_entitlement_payers()
        payload = {
            "external_id": "HIS-REV-TEST-IPD-PARTIAL",
            "source_system": "front_his",
            "business_date": "2026-08-23",
            "sales": [
                {
                    "line_external_id": "IPD-SELF",
                    "ticket_external_id": "POS-IPD-0001",
                    "entitlement_code": "SELF_PAY",
                    "service_type": "ip",
                    "item_type": "service",
                    "department_code": "IPD",
                    "amount_total": 15000.00,
                },
                {
                    "line_external_id": "IPD-SSO",
                    "ticket_external_id": "POS-IPD-0001",
                    "entitlement_code": "SSO",
                    "service_type": "ip",
                    "item_type": "drug",
                    "department_code": "IPD",
                    "amount_total": 80000.00,
                },
            ],
            "payments": [
                {
                    "line_external_id": "IPD-PAY-CASH",
                    "ticket_external_id": "POS-IPD-0001",
                    "payment_method_code": "cash",
                    "amount": 5000.00,
                },
                {
                    "line_external_id": "IPD-PAY-SSO",
                    "ticket_external_id": "POS-IPD-0001",
                    "payment_method_code": "sso",
                    "amount": 80000.00,
                },
                {
                    "line_external_id": "IPD-PAY-AR",
                    "ticket_external_id": "POS-IPD-0001",
                    "payment_method_code": "ar_claim",
                    "entitlement_code": "SELF_PAY",
                    "amount": 10000.00,
                },
            ],
            "control_totals": {"sales_total": 95000.00, "payments_total": 95000.00},
        }
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "ready", result.get("errors"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        cash_line = batch.payment_line_ids.filtered(
            lambda l: l.payment_method_code == "cash"
        )
        self.assertEqual(cash_line.service_type, "ip")
        self.assertEqual((cash_line.entitlement_code or "").upper(), "SELF_PAY")
        self.assertEqual(
            cash_line.entitlement_map_id.partner_id,
            self.env.ref("vpk_his_api.partner_payer_self_pay_ip"),
        )
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self_pay_partner = self.env.ref("vpk_his_api.partner_payer_self_pay_ip")
        sso_partner = self.env.ref("vpk_his_api.partner_payer_sso_ip")
        self_pay_inv = batch.invoice_ids.filtered(
            lambda i: i.partner_id == self_pay_partner
        )
        sso_inv = batch.invoice_ids.filtered(lambda i: i.partner_id == sso_partner)
        self.assertEqual(len(self_pay_inv), 1)
        self.assertEqual(len(sso_inv), 1)
        self.assertEqual(self_pay_inv.amount_total, 15000.00)
        self.assertEqual(self_pay_inv.amount_residual, 10000.00)
        self.assertEqual(sso_inv.amount_residual, 80000.00)
        self.assertEqual(len(batch.payment_ids), 1)
        self.assertEqual(batch.payment_ids.amount, 5000.00)
        self.assertEqual(batch.payment_ids.partner_id, self_pay_partner)
        action = self.env["vpk.his.entitlement.map"].action_open_outstanding_ar()
        open_moves = self.env["account.move"].search(action["domain"])
        self.assertIn(self_pay_inv, open_moves)
        self.assertIn(sso_inv, open_moves)

    def test_post_advance_apply_and_cash_topup(self):
        self.env["vpk.his.payment.method.map"]._bind_advance_tenders()
        self.env["vpk.his.receipt.journal.mixin"]._bind_his_advance_journal()
        payload = {
            "external_id": "HIS-REV-TEST-ADVANCE-TOPUP",
            "source_system": "front_his",
            "business_date": "2026-08-25",
            "sales": [
                {
                    "line_external_id": "ADV-SALE",
                    "ticket_external_id": "POS-OPD-ADV-1",
                    "entitlement_code": "SELF_PAY",
                    "service_type": "op",
                    "item_type": "service",
                    "amount_total": 15000.00,
                }
            ],
            "payments": [
                {
                    "line_external_id": "ADV-APPLY",
                    "ticket_external_id": "POS-OPD-ADV-1",
                    "payment_method_code": "advance",
                    "amount": 10000.00,
                },
                {
                    "line_external_id": "ADV-CASH",
                    "ticket_external_id": "POS-OPD-ADV-1",
                    "payment_method_code": "cash",
                    "amount": 5000.00,
                },
            ],
            "control_totals": {"sales_total": 15000.00, "payments_total": 15000.00},
        }
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "ready", result.get("errors"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        apply_line = batch.payment_line_ids.filtered(
            lambda l: l.payment_method_code == "advance"
        )
        self.assertEqual(apply_line.service_type, "op")
        self.assertEqual((apply_line.entitlement_code or "").upper(), "SELF_PAY")
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self_pay = self.env.ref("vpk_his_api.partner_payer_self_pay_op")
        inv = batch.invoice_ids.filtered(lambda i: i.partner_id == self_pay)
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv.amount_total, 15000.00)
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(len(batch.payment_ids), 2)
        amounts = sorted(batch.payment_ids.mapped("amount"))
        self.assertEqual(amounts, [5000.00, 10000.00])
        cash_pay = batch.payment_ids.filtered(lambda p: p.journal_id.code == "HCSH")
        adv_pay = batch.payment_ids.filtered(lambda p: p.journal_id.code == "HADV")
        self.assertEqual(cash_pay.amount, 5000.00)
        self.assertEqual(adv_pay.amount, 10000.00)

    def test_post_advance_in_then_visit_apply(self):
        self.env["vpk.his.receipt.journal.mixin"]._bind_his_advance_journal()
        in_result = self.service.ingest_revenue(
            {
                "external_id": "HIS-ADV-TEST-IN-001",
                "source_system": "front_his",
                "business_date": "2026-08-20",
                "payments": [
                    {
                        "line_external_id": "DEP-1",
                        "ticket_external_id": "DEP-0001",
                        "payment_method_code": "advance_in",
                        "amount": 10000.00,
                    }
                ],
                "control_totals": {"payments_total": 10000.00},
            }
        )
        self.assertEqual(in_result["state"], "ready", in_result.get("errors"))
        in_batch = self.env["vpk.his.batch"].browse(in_result["batch_id"])
        in_batch.action_post()
        self.assertEqual(in_batch.state, "posted")
        self.assertFalse(in_batch.invoice_ids)
        visit = self.service.ingest_revenue(
            {
                "external_id": "HIS-ADV-TEST-VISIT-001",
                "source_system": "front_his",
                "business_date": "2026-08-25",
                "sales": [
                    {
                        "line_external_id": "V1",
                        "ticket_external_id": "POS-OPD-ADV-2",
                        "entitlement_code": "SELF_PAY",
                        "service_type": "op",
                        "item_type": "service",
                        "amount_total": 10000.00,
                    }
                ],
                "payments": [
                    {
                        "line_external_id": "V1-ADV",
                        "ticket_external_id": "POS-OPD-ADV-2",
                        "payment_method_code": "prepaid",
                        "amount": 10000.00,
                    }
                ],
                "control_totals": {"sales_total": 10000.00, "payments_total": 10000.00},
            }
        )
        self.assertEqual(visit["state"], "ready", visit.get("errors"))
        visit_batch = self.env["vpk.his.batch"].browse(visit["batch_id"])
        visit_batch.action_post()
        inv = visit_batch.invoice_ids
        self.assertEqual(inv.amount_residual, 0.0)
        self.assertEqual(visit_batch.payment_ids.journal_id.code, "HADV")

    def test_post_stock_consumption(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        product = self.env["product.product"].create(
            {
                "name": "HIS Test Drug",
                "default_code": "99991",
                "is_storable": True,
                "type": "consu",
                "tracking": "none",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 50
        )
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-POST",
                "source_system": "pharmacy_his",
                "business_date": "2026-08-22",
                "issues": [
                    {
                        "line_external_id": "I1",
                        "product_code": "99991",
                        "warehouse_code": warehouse.code,
                        "qty": 3,
                        "reason": "patient_use",
                        "hn": "6500123",
                        "vn": "6808250001",
                    }
                ],
            }
        )
        self.assertEqual(result["state"], "ready", result.get("errors"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self.assertEqual(len(batch.picking_ids), 1)
        self.assertEqual(batch.picking_ids.state, "done")
        qty = product.with_context(location=warehouse.lot_stock_id.id).qty_available
        self.assertEqual(qty, 47.0)

    def test_stock_requires_lot_when_tracked(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        product = self.env["product.product"].create(
            {
                "name": "HIS Lot Drug",
                "default_code": "99992",
                "is_storable": True,
                "type": "consu",
                "tracking": "lot",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-LOT-REQ",
                "source_system": "front_his",
                "business_date": "2026-08-25",
                "issues": [
                    {
                        "product_code": "99992",
                        "item_type": "drug",
                        "warehouse_code": warehouse.code,
                        "qty": 2,
                        "hn": "6500123",
                        "vn": "6808250001",
                    }
                ],
            }
        )
        self.assertEqual(result["state"], "error")
        messages = " ".join(err.get("message") or "" for err in result["errors"])
        self.assertIn("lot", messages.lower())
        lookup = self.service.list_products(codes=["99992"])
        self.assertEqual(lookup["products"][0]["lot_required"], True)
        self.assertEqual(product.tracking, "lot")

    def test_stock_daily_summary_with_lots(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        drug = self.env["product.product"].create(
            {
                "name": "HIS Paracetamol",
                "default_code": "99993",
                "is_storable": True,
                "type": "consu",
                "tracking": "lot",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        supply = self.env["product.product"].create(
            {
                "name": "HIS Glove",
                "default_code": "99994",
                "is_storable": True,
                "type": "consu",
                "tracking": "none",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        lot_a = self.env["stock.lot"].create(
            {"name": "LOT-A", "product_id": drug.id, "company_id": self.env.company.id}
        )
        lot_b = self.env["stock.lot"].create(
            {"name": "LOT-B", "product_id": drug.id, "company_id": self.env.company.id}
        )
        Quant = self.env["stock.quant"].with_context(inventory_mode=True)
        Quant.create(
            {
                "product_id": drug.id,
                "location_id": warehouse.lot_stock_id.id,
                "lot_id": lot_a.id,
                "inventory_quantity": 20,
            }
        ).action_apply_inventory()
        Quant.create(
            {
                "product_id": drug.id,
                "location_id": warehouse.lot_stock_id.id,
                "lot_id": lot_b.id,
                "inventory_quantity": 10,
            }
        ).action_apply_inventory()
        Quant.create(
            {
                "product_id": supply.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": 50,
            }
        ).action_apply_inventory()
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-DAILY-LOT",
                "source_system": "front_his",
                "business_date": "2026-08-25",
                "items": [
                    {
                        "line_external_id": "DRUG-PARA",
                        "product_code": "99993",
                        "item_type": "drug",
                        "warehouse_code": warehouse.code,
                        "qty": 18,
                        "reason": "patient_use",
                        "hn": "6500123",
                        "vn": "6808250001",
                        "lots": [
                            {"lot_name": "LOT-A", "qty": 12},
                            {"lot_name": "LOT-B", "qty": 6},
                        ],
                    },
                    {
                        "line_external_id": "SUP-GLOVE",
                        "product_code": "99994",
                        "item_type": "medical_supply",
                        "warehouse_code": warehouse.code,
                        "qty": 40,
                        "reason": "patient_use",
                        "hn": "6500123",
                        "vn": "6808250001",
                    },
                ],
                "control_totals": {"qty_total": 58},
            }
        )
        self.assertEqual(result["state"], "ready", result.get("errors"))
        self.assertEqual(result["stock_qty_total"], 58.0)
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        self.assertEqual(len(batch.stock_line_ids), 3)
        self.assertEqual(batch.stock_line_ids.filtered(lambda l: l.lot_name == "LOT-A").qty, 12)
        self.assertTrue(all(line.hn == "6500123" for line in batch.stock_line_ids))
        self.assertTrue(all(line.vn == "6808250001" for line in batch.stock_line_ids))
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self.assertEqual(batch.picking_ids.state, "done")
        drug_move = batch.picking_ids.move_ids.filtered(lambda m: m.product_id == drug)
        self.assertEqual(sum(drug_move.mapped("quantity")), 18.0)
        self.assertEqual(len(drug_move.move_line_ids), 2)
        lots_done = {ml.lot_id.name: ml.quantity for ml in drug_move.move_line_ids}
        self.assertEqual(lots_done.get("LOT-A"), 12.0)
        self.assertEqual(lots_done.get("LOT-B"), 6.0)
        drug_qty = drug.with_context(location=warehouse.lot_stock_id.id).qty_available
        supply_qty = supply.with_context(location=warehouse.lot_stock_id.id).qty_available
        self.assertEqual(drug_qty, 12.0)
        self.assertEqual(supply_qty, 10.0)

    def test_stock_qty_control_mismatch(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.env["product.product"].create(
            {
                "name": "HIS Ctrl Drug",
                "default_code": "99995",
                "is_storable": True,
                "type": "consu",
                "tracking": "none",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        result = self.service.ingest_stock_issues(
            {
                "external_id": "HIS-STK-TEST-QTY-CTRL",
                "source_system": "front_his",
                "business_date": "2026-08-25",
                "issues": [
                    {
                        "product_code": "99995",
                        "warehouse_code": warehouse.code,
                        "qty": 3,
                        "hn": "6500123",
                        "vn": "6808250001",
                    }
                ],
                "control_totals": {"qty_total": 99},
            }
        )
        self.assertEqual(result["state"], "error")

    def test_reversal_revenue(self):
        result = self.service.ingest_revenue(self._revenue_payload("HIS-REV-TEST-ORIG"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        batch.action_post()
        reversal = self.service.ingest_revenue(
            {
                "external_id": "HIS-REV-TEST-REV1",
                "source_system": "front_his",
                "business_date": "2026-08-23",
                "batch_type": "reversal",
                "original_external_id": "HIS-REV-TEST-ORIG",
            }
        )
        self.assertEqual(reversal["state"], "ready", reversal.get("errors"))
        rev_batch = self.env["vpk.his.batch"].browse(reversal["batch_id"])
        rev_batch.action_post()
        self.assertEqual(rev_batch.state, "posted")
        self.assertTrue(rev_batch.invoice_ids)
        self.assertTrue(
            any(inv.move_type == "out_refund" for inv in rev_batch.invoice_ids)
            or any(inv.reversed_entry_id for inv in rev_batch.invoice_ids)
        )

    def test_validate_button_after_mapping_fix(self):
        payload = self._revenue_payload("HIS-REV-TEST-FIX")
        payload["sales"][0]["entitlement_code"] = "NEWPAY"
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "error")
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        partner = self.env.ref("vpk_his_api.partner_payer_self_pay_op")
        income = self.env["account.account"].search(
            [("code", "=", "4301020104.106")], limit=1
        )
        self.env["vpk.his.entitlement.map"].create(
            {
                "name": "New Payer OP",
                "code": "NEWPAY",
                "service_type": "op",
                "item_type": "all",
                "partner_id": partner.id,
                "income_account_id": income.id,
                "create_payment": True,
            }
        )
        batch.action_validate()
        self.assertEqual(batch.state, "ready")


@tagged("post_install", "-at_install")
class TestHisRemittance(TestHisApiCommon):
    def test_remittance_groups_rights_and_tenders(self):
        self.env["vpk.his.entitlement.map"]._ensure_remittance_labels()
        payload = {
            "external_id": "HIS-REV-TEST-REMIT-001",
            "source_system": "front_his",
            "business_date": "2026-08-23",
            "shift": "evening",
            "sales": [
                {
                    "line_external_id": "T1-CASH",
                    "ticket_external_id": "6296/712",
                    "entitlement_code": "SELF_PAY",
                    "service_type": "op",
                    "item_type": "service",
                    "amount_total": 50.00,
                },
                {
                    "line_external_id": "T1-SSO",
                    "ticket_external_id": "6296/712",
                    "entitlement_code": "SSO",
                    "service_type": "op",
                    "item_type": "drug",
                    "amount_total": 200.00,
                },
                {
                    "line_external_id": "T2-UC",
                    "ticket_external_id": "6296/780",
                    "entitlement_code": "UC",
                    "service_type": "op",
                    "item_type": "lab",
                    "amount_total": 80.00,
                },
                {
                    "line_external_id": "T2-CARD",
                    "ticket_external_id": "6296/780",
                    "entitlement_code": "SELF_PAY",
                    "service_type": "op",
                    "item_type": "service",
                    "amount_total": 15.20,
                },
            ],
            "payments": [
                {
                    "line_external_id": "T1-PAY-CASH",
                    "ticket_external_id": "6296/712",
                    "payment_method_code": "cash",
                    "entitlement_code": "SELF_PAY",
                    "amount": 50.00,
                },
                {
                    "line_external_id": "T1-PAY-SSO",
                    "ticket_external_id": "6296/712",
                    "payment_method_code": "sso",
                    "amount": 200.00,
                },
                {
                    "line_external_id": "T2-PAY-UC",
                    "ticket_external_id": "6296/780",
                    "payment_method_code": "uc",
                    "amount": 80.00,
                },
                {
                    "line_external_id": "T2-PAY-CARD",
                    "ticket_external_id": "6296/780",
                    "payment_method_code": "credit_card",
                    "entitlement_code": "SELF_PAY",
                    "amount": 15.20,
                },
            ],
            "control_totals": {"sales_total": 345.20, "payments_total": 345.20},
        }
        result = self.service.ingest_revenue(payload)
        self.assertEqual(result["state"], "ready", result.get("errors"))
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        wizard = self.env["vpk.his.remittance.wizard"].create(
            {
                "date_from": batch.business_date,
                "date_to": batch.business_date,
                "batch_ids": [Command.set(batch.ids)],
                "cashier_name": "นส.ผกาวดี กอบธัญการณ์",
                "cashier_job": "เจ้าพนักงานการเงินและบัญชี",
                "cancelled_count": 2,
            }
        )
        data = wizard.prepare_report_data()
        rows = {row["code"]: row for row in data["rows"]}
        self.assertEqual(rows["SELF_PAY"]["op_count"], 2)
        self.assertEqual(rows["SELF_PAY"]["op_amount"], 65.20)
        self.assertEqual(rows["SSO"]["op_count"], 1)
        self.assertEqual(rows["SSO"]["op_amount"], 200.00)
        self.assertEqual(rows["UC"]["op_count"], 1)
        self.assertEqual(rows["UC"]["op_amount"], 80.00)
        self.assertEqual(rows["SSO"]["label"], "(30) ปกส. (รพ.วชิระภูเก็ต)")
        self.assertEqual(data["receipt_count"], 2)
        self.assertEqual(data["receipt_from"], "6296/712")
        self.assertEqual(data["receipt_to"], "6296/780")
        self.assertEqual(data["cancelled_count"], 2)
        self.assertEqual(data["grand_total"], 345.20)
        self.assertEqual(data["cash_op"], 50.00)
        self.assertEqual(data["card_op"], 15.20)
        self.assertEqual(data["entitlement_ar"], 280.00)
        self.assertIn("2569", data["date_from_disp"])
        action = wizard.action_print()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["report_name"], "vpk_his_api.report_his_remittance")

    def test_post_stock_requisition(self):
        src_wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        dest_wh = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id), ("id", "!=", src_wh.id)],
            limit=1,
        )
        if not dest_wh:
            dest_wh = self.env["stock.warehouse"].create(
                {
                    "name": "HIS Front Test",
                    "code": "TFRNT",
                    "company_id": self.env.company.id,
                }
            )
        product = self.env["product.product"].create(
            {
                "name": "HIS Requisition Drug",
                "default_code": "99988",
                "is_storable": True,
                "type": "consu",
                "tracking": "none",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product, src_wh.lot_stock_id, 100
        )
        result = self.service.ingest_stock_requisitions(
            {
                "external_id": "HIS-REQ-TEST-POST",
                "source_system": "front_his",
                "business_date": "2026-08-26",
                "source_warehouse_code": src_wh.code,
                "dest_warehouse_code": dest_wh.code,
                "department_code": "OPD",
                "lines": [
                    {
                        "line_external_id": "R1",
                        "product_code": "99988",
                        "item_type": "drug",
                        "qty": 10,
                    }
                ],
                "control_totals": {"qty_total": 10},
            }
        )
        self.assertEqual(result["state"], "ready", result.get("errors"))
        self.assertEqual(result["batch_type"], "stock_requisition")
        batch = self.env["vpk.his.batch"].browse(result["batch_id"])
        self.assertEqual(batch.source_warehouse_id, src_wh)
        self.assertEqual(batch.dest_warehouse_id, dest_wh)
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self.assertEqual(len(batch.picking_ids), 1)
        self.assertEqual(batch.picking_ids.state, "done")
        self.assertEqual(
            batch.picking_ids.location_id, batch.source_location_id
        )
        self.assertEqual(
            batch.picking_ids.location_dest_id, batch.dest_location_id
        )
        src_qty = product.with_context(location=src_wh.lot_stock_id.id).qty_available
        dest_qty = product.with_context(location=dest_wh.lot_stock_id.id).qty_available
        self.assertEqual(src_qty, 90.0)
        self.assertEqual(dest_qty, 10.0)

    def test_stock_requisition_requires_lines(self):
        src_wh = self.env["stock.warehouse"].search([], limit=1)
        result = self.service.ingest_stock_requisitions(
            {
                "external_id": "HIS-REQ-TEST-EMPTY",
                "source_system": "front_his",
                "business_date": "2026-08-26",
                "source_warehouse_code": src_wh.code,
                "dest_warehouse_code": src_wh.code,
                "lines": [],
            }
        )
        self.assertEqual(result["state"], "error")


@tagged("post_install", "-at_install")
class TestHisApiHttp(HttpCase):
    def test_health_no_auth(self):
        response = self.url_open("/vpk/api/v1/his/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["service"], "vpk_his_api")

    def test_revenue_requires_api_key(self):
        response = self.url_open(
            "/vpk/api/v1/his/revenue",
            data='{"external_id": "X"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 401)
