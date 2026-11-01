# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestProcurementAssign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env["purchase.request"]
        cls.officer_group = cls.env.ref(
            "vpk_tier_validation.group_vpk_procurement_officer"
        )
        cls.manager_group = cls.env.ref(
            "purchase_request.group_purchase_request_manager"
        )
        cls.user_group = cls.env.ref("base.group_user")
        cls.officer = cls.env["res.users"].create(
            {
                "name": "เจ้าหน้าที่พัสดุทดสอบ",
                "login": "vpk_inbox_officer",
                "email": "vpk_inbox_officer@test.vpk",
                "groups_id": [(6, 0, [cls.user_group.id, cls.officer_group.id])],
            }
        )
        cls.other_officer = cls.env["res.users"].create(
            {
                "name": "เจ้าหน้าที่พัสดุอีกคน",
                "login": "vpk_inbox_officer2",
                "email": "vpk_inbox_officer2@test.vpk",
                "groups_id": [(6, 0, [cls.user_group.id, cls.officer_group.id])],
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "หัวหน้าพัสดุทดสอบ",
                "login": "vpk_inbox_manager",
                "email": "vpk_inbox_manager@test.vpk",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.user_group.id,
                            cls.manager_group.id,
                            cls.officer_group.id,
                        ],
                    )
                ],
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "สินค้าทดสอบกล่องรวม",
                "type": "consu",
                "purchase_ok": True,
            }
        )

    def _create_inbox_request(self):
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        vals = {
            "requested_by": self.env.user.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": self.product.id,
                        "name": self.product.name,
                        "product_qty": 1.0,
                        "estimated_cost": 100.0,
                    },
                )
            ],
        }
        if picking_type:
            vals["picking_type_id"] = picking_type.id
        request = self.Request.create(vals)
        vals = {
            "state": "sent_to_procurement",
            "sent_to_procurement_date": fields.Datetime.now(),
            "procurement_owner_id": False,
        }
        if "budget_check_state" in request._fields:
            vals["budget_check_state"] = "enough"
        request.with_context(
            skip_validation_check=True,
            skip_check_state_condition=True,
        ).write(vals)
        return request

    def test_send_to_procurement_lands_in_unassigned_inbox(self):
        request = self._create_inbox_request()
        self.assertEqual(request.state, "sent_to_procurement")
        self.assertFalse(request.procurement_owner_id)
        self.assertEqual(request.procurement_inbox_stage, "waiting")
        stats = self.Request.with_user(self.manager).get_procurement_inbox_stats()
        self.assertGreaterEqual(stats["unassigned"], 1)

    def test_officer_cannot_self_claim(self):
        request = self._create_inbox_request()
        with self.assertRaises(UserError):
            request.with_user(self.officer).action_claim_procurement()

    def test_manager_assigns_to_officer(self):
        request = self._create_inbox_request()
        wizard = (
            self.env["purchase.request.assign.wizard"]
            .with_user(self.manager)
            .with_context(active_ids=request.ids, active_id=request.id)
            .create({"user_id": self.officer.id, "note": "ดำเนินการยา"})
        )
        wizard.action_confirm_assign()
        self.assertEqual(request.procurement_owner_id, self.officer)
        self.assertEqual(request.procurement_assigned_by, self.manager)
        self.assertEqual(request.procurement_inbox_stage, "claimed")
        activities = request.activity_ids.filtered(
            lambda act: act.user_id == self.officer
        )
        self.assertTrue(activities)

    def test_manager_can_forward_to_another_officer(self):
        request = self._create_inbox_request()
        request.with_user(self.manager).action_assign_procurement(self.officer)
        request.with_user(self.manager).action_assign_procurement(self.other_officer)
        self.assertEqual(request.procurement_owner_id, self.other_officer)
        self.assertEqual(request.procurement_assigned_by, self.manager)
        self.assertTrue(
            request.activity_ids.filtered(lambda act: act.user_id == self.other_officer)
        )
        self.assertFalse(
            request.activity_ids.filtered(lambda act: act.user_id == self.officer)
        )

    def test_officer_cannot_verify_unassigned(self):
        request = self._create_inbox_request()
        with self.assertRaises(UserError):
            request.with_user(self.officer).action_verify_procurement()

    def test_unclaim_returns_to_central_inbox(self):
        request = self._create_inbox_request()
        request.with_user(self.manager).action_assign_procurement(self.officer)
        request.with_user(self.manager).action_unclaim_procurement()
        self.assertFalse(request.procurement_owner_id)
        self.assertFalse(request.procurement_assigned_by)
        self.assertEqual(request.procurement_inbox_stage, "waiting")
