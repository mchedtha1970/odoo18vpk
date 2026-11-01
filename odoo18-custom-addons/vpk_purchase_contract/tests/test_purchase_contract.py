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

    def test_unlimited_contract_pulls_price_list_and_locks_unit_price(self):
        product_b = self.env["product.product"].create(
            {
                "name": "Unlimited Product B",
                "type": "consu",
                "purchase_ok": True,
            }
        )
        contract_type = self.env["purchase.contract.type"].create(
            {
                "name": "จะซื้อจะขายไม่จำกัดจำนวน",
                "code": "unlimited_qty_test",
                "quantity_policy": "unlimited",
            }
        )
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "contract_type_id": contract_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "รายการ A",
                            "product_qty": 10.0,
                            "price_unit": 25.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_b.id,
                            "name": "รายการ B",
                            "product_qty": 3.0,
                            "price_unit": 40.0,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(contract.quantity_policy, "unlimited")
        contract.action_confirm()

        request = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "contract_id": contract.id,
            }
        )
        self.assertFalse(request._has_contract_bypass_budget())
        request.action_pull_contract_price_list()
        self.assertEqual(len(request.line_ids), 2)
        line_a = request.line_ids.filtered(
            lambda line: line.product_id == self.product
        )
        self.assertEqual(line_a.product_qty, 0.0)
        self.assertEqual(line_a.budget_unit_price, 25.0)
        self.assertEqual(line_a.contract_line_id.price_unit, 25.0)

        line_a.write({"product_qty": 4.0, "budget_unit_price": 1.0})
        self.assertEqual(line_a.budget_unit_price, 25.0)
        self.assertAlmostEqual(line_a.estimated_cost, 100.0)

        draft = self.env["purchase.request"].new(
            {
                "requested_by": self.env.user.id,
                "contract_id": contract.id,
            }
        )
        warning = draft._onchange_contract_id()
        self.assertEqual(len(draft.line_ids), 2)
        self.assertTrue(all(not line.product_qty for line in draft.line_ids))
        self.assertEqual(
            set(draft.line_ids.mapped("budget_unit_price")), {25.0, 40.0}
        )
        self.assertEqual(warning["warning"]["title"], "ดึงรายการราคาแล้ว")

        line_a.write({"product_qty": 2.0})
        request.action_pull_contract_price_list()
        self.assertEqual(line_a.product_qty, 2.0)
        self.assertAlmostEqual(line_a.estimated_cost, 50.0)

    def test_unlimited_name_keeps_draft_contract_selectable(self):
        contract_type = self.env["purchase.contract.type"].create(
            {"name": "สัญญาจะซื้อจะขายแบบราคาคงที่ไม่จำกัดจำนวน"}
        )
        self.assertEqual(contract_type.quantity_policy, "unlimited")
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "contract_type_id": contract_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "รายการ A",
                            "product_qty": 5.0,
                            "price_unit": 12.5,
                        },
                    )
                ],
            }
        )
        self.assertEqual(contract.state, "draft")
        self.assertEqual(contract.quantity_policy, "unlimited")
        found = self.env["purchase.contract"].search(
            [
                ("id", "=", contract.id),
                "|",
                ("state", "=", "confirmed"),
                "&",
                ("quantity_policy", "=", "unlimited"),
                ("state", "=", "draft"),
            ]
        )
        self.assertEqual(found, contract)
        request = self.env["purchase.request"].new(
            {
                "requested_by": self.env.user.id,
                "contract_id": contract.id,
            }
        )
        warning = request._onchange_contract_id()
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.budget_unit_price, 12.5)
        self.assertEqual(request.line_ids.product_id, self.product)
        self.assertEqual(warning["warning"]["title"], "ดึงรายการราคาแล้ว")

    def test_calloff_line_keeps_contract_product_master(self):
        generic = self.env["product.product"].create(
            {
                "name": "ซื้อ/จ้าง/เช่า",
                "type": "service",
                "purchase_ok": True,
            }
        )
        procurement_type = self.env["procurement.type"].create(
            {"name": "ซื้อ/จ้าง/เช่า ทดสอบ", "product_id": generic.id}
        )
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "quantity_policy": "unlimited",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 5.0,
                            "price_unit": 12.5,
                        },
                    )
                ],
            }
        )
        contract.action_confirm()
        request = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "procurement_type_id": procurement_type.id,
                "contract_id": contract.id,
            }
        )
        request.action_pull_contract_price_list()
        line = request.line_ids
        self.assertEqual(line.product_id, self.product)
        self.assertNotEqual(line.product_id, generic)
        self.assertEqual(line.budget_unit_price, 12.5)

    def test_unlimited_contract_releases_bidding_budget_hold(self):
        bidding = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "description": "ประกวดราคาหายา",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.name,
                            "product_qty": 100.0,
                            "estimated_cost": 100000.0,
                        },
                    )
                ],
            }
        )
        bidding.write({"budget_reservation_active": True, "state": "in_progress"})
        requisition = self.env["purchase.requisition"].create(
            {
                "requisition_type": "egp_procurement",
                "purchase_request_id": bidding.id,
            }
        )
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "quantity_policy": "unlimited",
                "requisition_id": requisition.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 100.0,
                            "price_unit": 1000.0,
                        },
                    )
                ],
            }
        )
        contract.action_confirm()
        bidding.invalidate_recordset()
        self.assertTrue(bidding.price_agreement_only)
        self.assertFalse(bidding.budget_reservation_active)

        calloff = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "contract_id": contract.id,
            }
        )
        calloff.action_pull_contract_price_list()
        self.assertFalse(calloff.price_agreement_only)
        bidding._activate_budget_reservation()
        self.assertFalse(bidding.budget_reservation_active)

    def test_unlimited_calloff_skips_egp_and_uses_contract_vendor(self):
        contract_type = self.env["purchase.contract.type"].create(
            {
                "name": "จะซื้อจะขายไม่จำกัดจำนวน",
                "code": "unlimited_po_direct",
                "quantity_policy": "unlimited",
            }
        )
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "contract_type_id": contract_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 5.0,
                            "price_unit": 80.0,
                        },
                    )
                ],
            }
        )
        contract.action_confirm()
        purchase_type = self.env["purchase.type"].search(
            [("to_create", "=", "purchase_agreement")], limit=1
        )
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        request = self.env["purchase.request"].create(
            {
                "requested_by": self.env.user.id,
                "contract_id": contract.id,
                "purchase_type_id": purchase_type.id,
                "picking_type_id": picking_type.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 2.0,
                            "estimated_cost": 160.0,
                            "contract_line_id": contract.line_ids.id,
                        },
                    )
                ],
            }
        )
        request.write({"state": "in_progress"})
        self.assertTrue(request.is_unlimited_contract)
        self.assertFalse(request._vpk_can_send_to_egp())
        self.assertFalse(request.is_egp_procurement_flow)
        wizard_model = self.env["purchase.request.line.make.purchase.order"]
        wizard_model._check_valid_request_line(request.line_ids.ids)
        defaults = wizard_model.with_context(
            active_model="purchase.request",
            active_id=request.id,
            active_ids=request.ids,
        ).default_get(["supplier_id", "item_ids", "is_unlimited_contract_po"])
        self.assertEqual(defaults["supplier_id"], self.partner.id)
        self.assertTrue(defaults["is_unlimited_contract_po"])
