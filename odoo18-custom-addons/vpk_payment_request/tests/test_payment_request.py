# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPaymentRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        unit = cls.env.ref("uom.product_uom_unit")
        cls.partner = cls.env["res.partner"].create(
            {"name": "ผู้ขายทดสอบขออนุมัติเบิกจ่าย", "supplier_rank": 1}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "สินค้าทดสอบขออนุมัติเบิกจ่าย",
                "is_storable": True,
                "purchase_ok": True,
                "uom_id": unit.id,
                "uom_po_id": unit.id,
                "standard_price": 100.0,
                "purchase_method": "purchase",
            }
        )
        cls.order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "name": cls.product.display_name,
                            "product_qty": 2.0,
                            "product_uom": unit.id,
                            "price_unit": 100.0,
                            "date_planned": fields.Datetime.now(),
                        }
                    )
                ],
            }
        )
        cls.order.button_confirm()

    def _create_wa(self, state="draft"):
        order = self.order
        wa = self.env["work.acceptance"].create(
            {
                "purchase_id": order.id,
                "partner_id": order.partner_id.id,
                "date_due": fields.Date.today(),
                "wa_line_ids": [
                    Command.create(
                        {
                            "purchase_line_id": line.id,
                            "name": line.name,
                            "product_id": line.product_id.id,
                            "product_uom": line.product_uom.id,
                            "price_unit": line.price_unit,
                            "product_qty": line.product_qty,
                        }
                    )
                    for line in order.order_line
                ],
            }
        )
        if state != "draft":
            wa.sudo().write({"state": state})
        return wa

    def _approve(self, doc):
        doc.with_context(skip_validation_check=True).write({"state": "approved"})

    def test_cannot_request_before_acceptance(self):
        self.assertFalse(self.order.can_request_payment)
        with self.assertRaises(UserError):
            self.order.action_request_payment_approval()
        self._create_wa(state="draft")
        self.order.invalidate_recordset()
        self.assertFalse(self.order.can_request_payment)
        with self.assertRaises(UserError):
            self.order.action_request_payment_approval()

    def test_request_after_acceptance_and_forward_to_ap(self):
        wa = self._create_wa(state="accept")
        self.order.invalidate_recordset()
        self.assertTrue(self.order.can_request_payment)
        action = self.order.action_request_payment_approval()
        wizard = self.env["vpk.payment.request.wizard"].browse(action["res_id"])
        self.assertEqual(wizard.wa_id, wa)
        result = wizard.action_confirm()
        doc = self.env["vpk.document.studio.document"].browse(result["res_id"])
        self.assertEqual(doc.document_type_code, "payment_request")
        self.assertEqual(doc.purchase_id, self.order)
        self.assertEqual(doc.wa_id, wa)
        self.assertEqual(doc.payment_state, "draft")
        self.assertAlmostEqual(doc.payment_amount, wa.payment_amount)
        self.assertIn("จำนวนเงินที่ขอเบิกจ่ายสุทธิ", doc.body)
        # ใบตรวจรับนี้มีใบขอแล้ว: ขอซ้ำไม่ได้
        self.order.invalidate_recordset()
        self.assertFalse(self.order.can_request_payment)
        with self.assertRaises(UserError):
            self.order.action_request_payment_approval()
        # ยังไม่ลงนามครบ: ส่งเจ้าหนี้ไม่ได้
        with self.assertRaises(UserError):
            doc.action_send_to_ap()
        # ลงนามครบ → ยังไม่ส่งเจ้าหนี้จนกว่าจะกดปุ่ม
        self._approve(doc)
        doc.invalidate_recordset()
        self.order.invalidate_recordset()
        self.assertEqual(doc.payment_state, "approved")
        self.assertTrue(self.order.can_send_payment_to_ap)
        with self.assertRaises(UserError):
            doc.action_create_ap_bill()
        self.order.action_send_payment_to_ap()
        doc.invalidate_recordset()
        self.order.invalidate_recordset()
        self.assertFalse(self.order.can_send_payment_to_ap)
        with self.assertRaises(UserError):
            doc.action_send_to_ap()
        self.assertEqual(doc.payment_state, "wait_ap")
        self.assertTrue(doc.payment_ap_forwarded_on)
        # เจ้าหนี้ดึงรายการ → ใบเรียกเก็บฉบับร่างผูก WA
        doc.action_create_ap_bill()
        doc.invalidate_recordset()
        bill = doc.payment_bill_id
        self.assertTrue(bill)
        self.assertEqual(bill.state, "draft")
        self.assertEqual(bill.wa_id, wa)
        self.assertEqual(bill.payment_request_id, doc)
        self.assertEqual(doc.payment_state, "billed")
        # กดซ้ำเปิดใบเดิม ไม่สร้างซ้ำ
        doc.action_create_ap_bill()
        self.assertEqual(doc.payment_bill_id, bill)
        # dashboard เจ้าหนี้เห็นรายการ (ตั้งหนี้ฉบับร่าง)
        data = self.env["vpk.document.studio.document"].get_payment_ap_dashboard()
        counts = {kpi["key"]: kpi["count"] for kpi in data["kpis"]}
        self.assertGreaterEqual(counts["billed"], 1)
        # ยังไม่ POST: ส่งการเงินไม่ได้
        with self.assertRaises(UserError):
            doc.action_send_to_finance()
        # จำลองการอนุมัติ/POST ใบเรียกเก็บ (การ POST จริงต้องใช้ผังบัญชีครบ)
        self.env.cr.execute("UPDATE account_move SET state = 'posted' WHERE id = %s", [bill.id])
        bill.invalidate_recordset()
        self.env.add_to_compute(doc._fields["payment_state"], doc)
        doc.invalidate_recordset()
        self.assertEqual(doc.payment_state, "posted")
        doc.action_send_to_finance()
        doc.invalidate_recordset()
        self.assertEqual(doc.payment_state, "to_finance")
        self.assertTrue(doc.payment_finance_sent_on)
        with self.assertRaises(UserError):
            doc.action_send_to_finance()
        # Dashboard การเงิน: เห็นรายการรอทำจ่าย และดึงรายการไปหน้าลงทะเบียนจ่ายได้
        fin = self.env["vpk.document.studio.document"].get_payment_finance_dashboard()
        fin_counts = {kpi["key"]: kpi["count"] for kpi in fin["kpis"]}
        self.assertGreaterEqual(fin_counts["to_finance"], 1)
        self.assertIn(doc.id, [row["id"] for row in fin["rows"]])
        # ต้องมีใบขอเบิกเงินอัปโหลดกรมบัญชีกลางแล้วก่อนดึงรายการทำจ่าย
        if "vpk.disbursement.form" in self.env:
            with self.assertRaises(UserError):
                doc.action_open_register_payment()
            kb = self.env["vpk.disbursement.form"].action_create_from_invoice(bill)
            kb.write({"state": "uploaded"})
            fin = self.env["vpk.document.studio.document"].get_payment_finance_dashboard()
            row = next(r for r in fin["rows"] if r["id"] == doc.id)
            self.assertTrue(row.get("can_register_payment"))
        pay_action = doc.action_open_register_payment()
        self.assertEqual(pay_action.get("type"), "ir.actions.client")
        self.assertEqual(pay_action.get("tag"), "display_notification")
        draft = self.env["account.payment"].search(
            [
                ("vpk_payment_request_id", "=", doc.id),
                ("state", "=", "draft"),
                ("payment_type", "=", "outbound"),
            ],
            limit=1,
        )
        self.assertTrue(draft, "ต้องสร้างรายการชำระเงินฉบับร่างโดยไม่เปิด wizard")
        # จ่ายแล้ว → สถานะทำจ่ายแล้ว และออกจากรายการรอทำจ่าย
        self.env.cr.execute(
            "UPDATE account_move SET payment_state = 'paid' WHERE id = %s", [bill.id]
        )
        bill.invalidate_recordset()
        self.env.add_to_compute(doc._fields["payment_state"], doc)
        doc.invalidate_recordset()
        self.assertEqual(doc.payment_state, "paid")
        with self.assertRaises(UserError):
            doc.action_open_register_payment()

    def test_cannot_create_bill_before_approved(self):
        self._create_wa(state="accept")
        action = self.order.action_request_payment_approval()
        doc = self.env["vpk.document.studio.document"].browse(
            self.env["vpk.payment.request.wizard"].browse(action["res_id"]).action_confirm()["res_id"]
        )
        with self.assertRaises(UserError):
            doc.action_create_ap_bill()

    def test_cancel_frees_acceptance(self):
        self._create_wa(state="accept")
        action = self.order.action_request_payment_approval()
        doc = self.env["vpk.document.studio.document"].browse(
            self.env["vpk.payment.request.wizard"].browse(action["res_id"]).action_confirm()["res_id"]
        )
        doc.action_cancel()
        self.order.invalidate_recordset()
        self.assertTrue(self.order.can_request_payment)
