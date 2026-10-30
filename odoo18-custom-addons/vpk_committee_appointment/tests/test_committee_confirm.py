from odoo.addons.base.tests.common import new_test_user
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestCommitteeConfirm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="vpk_committee_confirm_user",
            groups="base.group_user",
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "กรรมการทดสอบยืนยัน",
                "user_id": cls.user.id,
            }
        )
        purchase_type = cls.env.ref("l10n_th_gov_purchase_request.purchase_type_001")
        procurement_type = cls.env.ref(
            "l10n_th_gov_purchase_request.procurement_type_001"
        )
        procurement_method = cls.env.ref(
            "l10n_th_gov_purchase_request.procurement_specific"
        )
        cls.request = cls.env["purchase.request"].create(
            {
                "purchase_type_id": purchase_type.id,
                "procurement_type_id": procurement_type.id,
                "procurement_method_id": procurement_method.id,
            }
        )
        cls.member = cls.env["procurement.committee"].create(
            {
                "request_id": cls.request.id,
                "employee_id": cls.employee.id,
                "name": cls.employee.name,
                "committee_type": "work_acceptance",
                "approve_role": "chairman",
            }
        )

    def test_send_notify_sets_pending(self):
        self.request.action_request_committee_confirm()
        self.assertEqual(self.member.confirm_state, "pending")
        self.assertTrue(self.member.confirm_request_date)
        notification = self.env["mail.message"].search(
            [
                ("model", "=", "purchase.request"),
                ("res_id", "=", self.request.id),
                ("message_type", "=", "user_notification"),
                ("partner_ids", "in", self.user.partner_id.id),
            ],
            limit=1,
        )
        self.assertTrue(notification, "Committee user should receive an in-system notify")
        self.assertTrue(
            self.env["mail.activity"].search(
                [
                    ("res_model", "=", "purchase.request"),
                    ("res_id", "=", self.request.id),
                    ("user_id", "=", self.user.id),
                ],
                limit=1,
            )
        )

    def test_block_appointment_until_accepted(self):
        with self.assertRaises(UserError):
            self.request.action_create_committee_appointment()
        self.request.action_request_committee_confirm()
        with self.assertRaises(UserError):
            self.request.action_create_committee_appointment()
        self.member.with_user(self.user).sudo().action_accept_confirm()
        self.assertEqual(self.member.confirm_state, "accepted")
        action = self.request.action_create_committee_appointment()
        self.assertEqual(action["res_model"], "procurement.committee.appointment")

    def test_member_can_decline(self):
        self.request.action_request_committee_confirm()
        wizard = (
            self.env["procurement.committee.confirm.wizard"]
            .with_user(self.user)
            .create(
                {
                    "request_id": self.request.id,
                    "line_ids": [(6, 0, self.member.ids)],
                    "decline_reason": "ติดราชการ",
                }
            )
        )
        wizard.action_decline()
        self.assertEqual(self.member.confirm_state, "declined")
        self.assertEqual(self.member.confirm_note, "ติดราชการ")
        with self.assertRaises(UserError):
            self.request.action_create_committee_appointment()

    def test_other_user_cannot_accept(self):
        other = new_test_user(
            self.env,
            login="vpk_committee_confirm_other",
            groups="base.group_user",
        )
        self.request.action_request_committee_confirm()
        with self.assertRaises(UserError):
            self.member.with_user(other).sudo().action_accept_confirm()
