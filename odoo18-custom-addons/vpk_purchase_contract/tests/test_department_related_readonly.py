# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDepartmentContractReadonly(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept = cls.env["res.users"].create(
            {
                "name": "หน่วยงานดูสัญญา",
                "login": "vpk_dept_contract_ro",
                "email": "vpk_dept_contract_ro@test.vpk",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref(
                                "purchase_request.group_purchase_request_user"
                            ).id,
                        ],
                    )
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "คู่ค้าดูสัญญา", "supplier_rank": 1}
        )
        cls.contract = cls.env["purchase.contract"].create(
            {
                "partner_id": cls.partner.id,
                "amount_total": 1000.0,
            }
        )
        cls.other = cls.env["purchase.contract"].create(
            {
                "partner_id": cls.partner.id,
                "amount_total": 500.0,
            }
        )
        product = cls.env["product.product"].create(
            {
                "name": "สินค้าดูสัญญา",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        picking_type = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        vals = {
            "requested_by": cls.dept.id,
            "contract_id": cls.contract.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": product.name,
                        "product_qty": 1.0,
                        "estimated_cost": 100.0,
                    },
                )
            ],
        }
        if picking_type:
            vals["picking_type_id"] = picking_type.id
        cls.request = cls.env["purchase.request"].create(vals)

    def test_department_can_open_own_contract_readonly(self):
        request = self.request.with_user(self.dept)
        action = request.action_open_related_contract()
        self.assertEqual(action["res_id"], self.contract.id)
        self.assertEqual(action.get("flags", {}).get("mode"), "readonly")
        self.assertTrue(self.contract.with_user(self.dept).name)
        arch, _view = (
            self.env["purchase.contract"].with_user(self.dept)._get_view(view_type="form")
        )
        self.assertEqual(arch.get("edit"), "false")

    def test_department_cannot_write_contract(self):
        with self.assertRaises(AccessError):
            self.contract.with_user(self.dept).write({"amount_total": 1.0})

    def test_department_cannot_read_unrelated_contract(self):
        with self.assertRaises(AccessError):
            self.other.with_user(self.dept).name
