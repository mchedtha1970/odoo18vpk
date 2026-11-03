# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestWorkAcceptanceCommittee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        unit = cls.env.ref("uom.product_uom_unit")
        cls.partner = cls.env["res.partner"].create(
            {"name": "ผู้ขายคณะกรรมการตรวจรับ", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "สินค้าคณะกรรมการตรวจรับ",
                "is_storable": True,
                "purchase_ok": True,
                "uom_id": unit.id,
                "uom_po_id": unit.id,
                "standard_price": 25.0,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "ประธานกรรมการตรวจรับทดสอบ"}
        )
        cls.egp_employee = cls.env["hr.employee"].create(
            {"name": "กรรมการ e-GP ทดสอบ"}
        )

    def _create_po(self):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 2.0,
                            "product_uom": self.product.uom_id.id,
                            "price_unit": 25.0,
                            "date_planned": fields.Datetime.now(),
                        }
                    )
                ],
            }
        )

    def test_committee_from_purchase_request(self):
        if "purchase.request" not in self.env:
            self.skipTest("purchase.request is not installed")
        picking_type = self.env.ref("stock.picking_type_in")
        request = self.env["purchase.request"].create(
            {
                "picking_type_id": picking_type.id,
                "requested_by": self.env.uid,
                "line_ids": [
                    Command.create(
                        {
                            "name": self.product.display_name,
                            "product_id": self.product.id,
                            "product_qty": 2.0,
                            "product_uom_id": self.product.uom_id.id,
                            "estimated_cost": 50.0,
                        }
                    )
                ],
                "work_acceptance_committee_ids": [
                    Command.create(
                        {
                            "employee_id": self.employee.id,
                            "name": self.employee.name,
                            "approve_role": "chairman",
                            "committee_type": "work_acceptance",
                        }
                    )
                ],
            }
        )
        order = self._create_po()
        order.order_line.purchase_request_lines = request.line_ids
        commands = order._get_wa_committee_from_pr()
        names = [command[2]["name"] for command in commands]
        self.assertIn(self.employee.name, names)
        self.assertTrue(
            any("ใบขอซื้อ" in (command[2].get("origin") or "") for command in commands)
        )
        wa = self.env["work.acceptance"].create(
            {
                "purchase_id": order.id,
                "partner_id": order.partner_id.id,
                "date_due": fields.Datetime.now(),
                "date_receive": fields.Datetime.now(),
            }
        )
        self.assertIn(self.employee.name, wa.committee_ids.mapped("name"))
        self.assertIn("ใบขอซื้อ", wa.committee_source or "")

    def test_committee_from_egp_requisition(self):
        if "purchase.requisition" not in self.env:
            self.skipTest("purchase.requisition is not installed")
        Requisition = self.env["purchase.requisition"]
        if "work_acceptance_committee_ids" not in Requisition._fields:
            self.skipTest("e-GP work acceptance committee is not installed")
        order = self._create_po()
        requisition = Requisition.create(
            {
                "vendor_id": self.partner.id,
                "user_id": self.env.uid,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 2.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": 25.0,
                        }
                    )
                ],
            }
        )
        requisition.write(
            {
                "work_acceptance_committee_ids": [
                    Command.create(
                        {
                            "employee_id": self.egp_employee.id,
                            "name": self.egp_employee.name,
                            "approve_role": "committee",
                            "committee_type": "work_acceptance",
                            "requisition_id": requisition.id,
                        }
                    )
                ]
            }
        )
        if "requisition_id" in order._fields:
            order.requisition_id = requisition
        commands = order._get_wa_committee_from_pr()
        names = [command[2]["name"] for command in commands]
        self.assertIn(self.egp_employee.name, names)
        self.assertTrue(
            any("e-GP" in (command[2].get("origin") or "") for command in commands)
        )
        wa = self.env["work.acceptance"].new(
            {
                "purchase_id": order.id,
                "partner_id": order.partner_id.id,
                "date_due": fields.Datetime.now(),
                "date_receive": fields.Datetime.now(),
            }
        )
        wa._onchange_purchase_id_load()
        self.assertIn(self.egp_employee.name, wa.committee_ids.mapped("name"))
