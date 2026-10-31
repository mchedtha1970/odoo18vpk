# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import date, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPurchaseContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Contract Vendor", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Contract Product",
                "type": "consu",
                "purchase_ok": True,
                "list_price": 100.0,
                "standard_price": 100.0,
            }
        )
        cls.contract = cls.env["purchase.contract"].create(
            {
                "partner_id": cls.partner.id,
                "amount_total": 1000.0,
                "installment_ids": [
                    (0, 0, {"name": "งวดที่ 1", "amount": 400.0, "sequence": 1}),
                    (0, 0, {"name": "งวดที่ 2", "amount": 600.0, "sequence": 2}),
                ],
            }
        )
        cls.contract.action_confirm()

    def _create_pr(self, amount, contract=None):
        return self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "contract_id": (contract or self.contract).id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.name,
                            "product_qty": 1.0,
                            "estimated_cost": amount,
                        },
                    )
                ],
            }
        )

    def test_remaining_after_confirm(self):
        self.assertEqual(self.contract.amount_remaining, 1000.0)

    def test_payment_fields_default_in_amount_group(self):
        self.assertEqual(self.contract.payment_type, "installment")
        self.assertEqual(self.contract.has_advance_payment, "no_advance")
        self.contract.write(
            {
                "payment_type": "once",
                "has_advance_payment": "advance",
            }
        )
        self.assertEqual(self.contract.payment_type, "once")
        self.assertEqual(self.contract.has_advance_payment, "advance")

    def test_hard_block_over_balance(self):
        request = self._create_pr(1200.0)
        with self.assertRaises(UserError):
            request._check_contract_balance()

    def test_allow_within_balance(self):
        request = self._create_pr(400.0)
        request._check_contract_balance()

    def test_po_confirm_deducts_balance(self):
        request = self._create_pr(300.0)
        request.write({"state": "approved"})
        self.contract.invalidate_recordset()
        self.assertAlmostEqual(self.contract.amount_remaining, 700.0)

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.name,
                            "product_qty": 1.0,
                            "price_unit": 300.0,
                        },
                    )
                ],
            }
        )
        # Link PO line to PR line so covered amount transfers correctly
        request.line_ids[:1].purchase_lines = [(4, po.order_line[:1].id)]
        po.button_confirm()
        self.contract.invalidate_recordset()
        self.assertAlmostEqual(self.contract.amount_po_confirmed, 300.0)
        self.assertAlmostEqual(self.contract.amount_remaining, 700.0)

    def test_invoice_gets_contract(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.name,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        vals = po._prepare_invoice()
        self.assertEqual(vals.get("contract_id"), self.contract.id)

    def test_delivery_days_computed_from_due_date(self):
        start = date(2026, 10, 29)
        due = date(2026, 11, 28)
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "amount_total": 1000.0,
                "date_start": start,
                "delivery_due_date": due,
            }
        )
        self.assertEqual(contract.delivery_term_days, 30)
        self.assertEqual(contract.delivery_due_date, due)

    def test_delivery_due_date_computed_from_days(self):
        start = date(2026, 10, 29)
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "amount_total": 1000.0,
                "date_start": start,
                "delivery_term_days": 15,
            }
        )
        self.assertEqual(contract.delivery_due_date, date(2026, 11, 13))
        self.assertEqual(contract.delivery_term_days, 15)

    def test_delivery_fields_editable_and_stay_in_sync(self):
        start = date(2026, 10, 29)
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "amount_total": 1000.0,
                "date_start": start,
                "delivery_term_days": 10,
            }
        )
        contract.write({"delivery_due_date": date(2026, 12, 8)})
        self.assertEqual(contract.delivery_term_days, 40)
        contract.write({"delivery_term_days": 7})
        self.assertEqual(contract.delivery_due_date, date(2026, 11, 5))
        contract.write({"date_start": date(2026, 11, 1)})
        self.assertEqual(contract.delivery_term_days, 7)
        self.assertEqual(contract.delivery_due_date, date(2026, 11, 8))

    def test_delivery_due_date_cannot_precede_start(self):
        with self.assertRaises(ValidationError):
            self.env["purchase.contract"].create(
                {
                    "partner_id": self.partner.id,
                    "amount_total": 1000.0,
                    "date_start": date(2026, 10, 29),
                    "delivery_due_date": date(2026, 10, 20),
                }
            )

    def test_delivery_onchange_on_form(self):
        start = date(2026, 10, 29)
        with Form(self.env["purchase.contract"]) as form:
            form.partner_id = self.partner
            form.amount_total = 1000.0
            form.date_start = start
            form.delivery_term_days = 30
            self.assertEqual(form.delivery_due_date, start + timedelta(days=30))
            form.delivery_due_date = date(2026, 12, 28)
            self.assertEqual(form.delivery_term_days, 60)
