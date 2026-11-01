# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDepartmentRelatedReadonly(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept = cls.env["res.users"].create(
            {
                "name": "หน่วยงานดูรายการต่อเนื่อง",
                "login": "vpk_dept_related_ro",
                "email": "vpk_dept_related_ro@test.vpk",
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
        cls.product = cls.env["product.product"].create(
            {
                "name": "สินค้าหน่วยงานดูต่อเนื่อง",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        picking_type = cls.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        vals = {
            "requested_by": cls.dept.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": cls.product.id,
                        "name": cls.product.name,
                        "product_qty": 1.0,
                        "estimated_cost": 100.0,
                    },
                )
            ],
        }
        if picking_type:
            vals["picking_type_id"] = picking_type.id
        cls.request = cls.env["purchase.request"].create(vals)
        cls.requisition = cls.env["purchase.requisition"].create(
            {
                "requisition_type": "egp_procurement",
                "egp_reference": "EGP-DEPT-RO",
                "purchase_request_id": cls.request.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 1.0,
                        },
                    )
                ],
            }
        )
        cls.other_requisition = cls.env["purchase.requisition"].create(
            {
                "requisition_type": "egp_procurement",
                "egp_reference": "EGP-OTHER",
            }
        )

    def test_department_is_related_viewer(self):
        self.assertTrue(
            self.env["purchase.request"]
            .with_user(self.dept)
            ._vpk_is_department_related_viewer()
        )

    def test_department_can_open_own_egp_readonly(self):
        request = self.request.with_user(self.dept)
        action = request.action_view_purchase_requisition()
        self.assertEqual(action["res_id"], self.requisition.id)
        self.assertFalse(action["context"].get("edit"))
        self.assertEqual(action.get("flags", {}).get("mode"), "readonly")
        self.assertTrue(self.requisition.with_user(self.dept).name)
        arch, _view = (
            self.env["purchase.requisition"]
            .with_user(self.dept)
            ._get_view(view_type="form")
        )
        self.assertEqual(arch.get("edit"), "false")

    def test_department_cannot_write_egp(self):
        with self.assertRaises(AccessError):
            self.requisition.with_user(self.dept).write(
                {"egp_reference": "CHANGED"}
            )

    def test_department_cannot_read_unrelated_egp(self):
        with self.assertRaises(AccessError):
            self.other_requisition.with_user(self.dept).name
