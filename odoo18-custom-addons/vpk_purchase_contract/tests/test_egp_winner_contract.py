# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "egp_winner_contract")
class TestEgpWinnerContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Winner Vendor A", "supplier_rank": 1}
        )
        cls.partner_b = cls.env["res.partner"].create(
            {"name": "Winner Vendor B", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Winner Product A",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        cls.product_b = cls.env["product.product"].create(
            {
                "name": "Winner Product B",
                "purchase_ok": True,
                "type": "consu",
            }
        )

    def _make_requisition(self, consideration):
        return self.env["purchase.requisition"].create(
            {
                "requisition_type": "egp_procurement",
                "egp_consideration_type": consideration,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 2.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_b.id,
                            "product_qty": 3.0,
                        },
                    ),
                ],
            }
        )

    def test_line_mode_creates_contract_per_winning_vendor(self):
        requisition = self._make_requisition("line")
        BidLine = self.env["purchase.requisition.egp.bid.line"].with_context(
            default_requisition_id=requisition.id
        )
        line_a = BidLine.create(
            {
                "partner_id": self.partner.id,
                "product_id": self.product.id,
                "product_qty": 2.0,
                "price_unit": 100.0,
                "is_winner": True,
            }
        )
        BidLine.create(
            {
                "partner_id": self.partner_b.id,
                "product_id": self.product_b.id,
                "product_qty": 3.0,
                "price_unit": 50.0,
                "is_winner": True,
            }
        )
        action = requisition.action_create_purchase_contract()
        contracts = self.env["purchase.contract"].search(
            [("requisition_id", "=", requisition.id)]
        )
        self.assertEqual(len(contracts), 2)
        self.assertEqual(action["res_model"], "purchase.contract")
        contract_a = contracts.filtered(lambda rec: rec.partner_id == self.partner)
        self.assertEqual(len(contract_a.line_ids), 1)
        self.assertEqual(contract_a.line_ids.product_id, self.product)
        self.assertAlmostEqual(contract_a.amount_total, 200.0)
        self.assertEqual(contract_a.line_ids.egp_bid_line_id, line_a)

    def test_total_mode_copies_winner_products(self):
        requisition = self._make_requisition("total")
        bid = self.env["purchase.requisition.egp.bid"].create(
            {
                "requisition_id": requisition.id,
                "partner_id": self.partner.id,
                "amount_total": 450.0,
                "is_winner": True,
            }
        )
        if bid.line_ids:
            for line in bid.line_ids:
                if line.product_id == self.product:
                    line.write({"price_unit": 100.0, "product_qty": 2.0})
                elif line.product_id == self.product_b:
                    line.write({"price_unit": 50.0, "product_qty": 3.0})
        action = requisition.action_create_purchase_contract()
        contract = requisition.contract_ids
        self.assertEqual(action.get("res_id"), contract.id)
        self.assertEqual(len(contract), 1)
        self.assertEqual(contract.partner_id, self.partner)
        self.assertEqual(len(contract.line_ids), 2)
        self.assertAlmostEqual(contract.amount_total, bid.amount_total)

    def test_contract_has_egp_control_and_po_number(self):
        contract = self.env["purchase.contract"].create(
            {
                "partner_id": self.partner.id,
                "amount_total": 300.0,
                "egp_contract_control_no": "68129483488",
            }
        )
        self.assertTrue(contract.name)
        self.assertEqual(contract.contract_po_number, contract.name)
        self.assertEqual(contract.egp_contract_control_no, "68129483488")
        contract.write({"contract_po_number": "CTR/2026/0009"})
        self.assertEqual(contract.contract_po_number, "CTR/2026/0009")

    def test_essence_print_uses_contract_egp_fields(self):
        requisition = self._make_requisition("total")
        self.env["purchase.requisition.egp.bid"].create(
            {
                "requisition_id": requisition.id,
                "partner_id": self.partner.id,
                "amount_total": 450.0,
                "is_winner": True,
            }
        )
        requisition.action_create_purchase_contract()
        contract = requisition.contract_ids
        contract.write(
            {
                "egp_contract_control_no": "68129483488",
                "contract_po_number": "CTR/2026/0009",
            }
        )
        values = requisition._get_contract_essence_values()
        self.assertEqual(values["winner_rows"][0]["egp_control"], "68129483488")
        self.assertEqual(values["winner_rows"][0]["contract_no"], "CTR/2026/0009")

    def test_line_mode_requires_winners(self):
        requisition = self._make_requisition("line")
        with self.assertRaises(UserError):
            requisition.action_create_purchase_contract()
