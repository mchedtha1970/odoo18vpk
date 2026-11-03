# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestWorkAcceptanceDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        unit = cls.env.ref("uom.product_uom_unit")
        cls.partner = cls.env["res.partner"].create(
            {"name": "ผู้ขายแดชบอร์ดตรวจรับ", "supplier_rank": 1}
        )
        cls.goods = cls.env["product.product"].create(
            {
                "name": "สินค้าตรวจรับแดชบอร์ด",
                "is_storable": True,
                "purchase_ok": True,
                "uom_id": unit.id,
                "uom_po_id": unit.id,
                "standard_price": 10.0,
                "list_price": 10.0,
            }
        )
        cls.service = cls.env["product.product"].create(
            {
                "name": "บริการตรวจรับแดชบอร์ด",
                "type": "service",
                "purchase_ok": True,
                "purchase_method": "purchase",
                "uom_id": unit.id,
                "uom_po_id": unit.id,
                "standard_price": 100.0,
                "list_price": 100.0,
            }
        )
        cls.WA = cls.env["work.acceptance"]

    def _create_po(self, product, qty=5.0):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "name": product.display_name,
                            "product_qty": qty,
                            "product_uom": product.uom_id.id,
                            "price_unit": product.standard_price or 10.0,
                            "date_planned": fields.Datetime.now(),
                        }
                    )
                ],
            }
        )

    def _pass_qc(self, picking):
        if "vpk.stock.qc" not in self.env:
            return
        QC = self.env["vpk.stock.qc"]
        qc = picking.qc_ids[:1] or QC.create({"picking_id": picking.id})
        if qc.check_ids:
            qc.check_ids.write({"quality_state": "pass"})
        if qc.line_ids:
            qc.line_ids.write({"result": "pass"})
        if qc.state == "draft":
            qc.action_confirm()

    def _validate_picking(self, picking):
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        self._pass_qc(picking)
        result = picking.with_context(skip_qc_wizard=True).button_validate()
        if isinstance(result, dict) and result.get("res_model"):
            wizard = (
                self.env[result["res_model"]]
                .with_context(**result.get("context", {}))
                .browse(result.get("res_id"))
            )
            if hasattr(wizard, "process"):
                wizard.process()
            elif hasattr(wizard, "button_validate"):
                wizard.button_validate()

    def _create_vendor_bill(self, order):
        Move = self.env["account.move"]
        invoice = Move.create(
            {
                "move_type": "in_invoice",
                "partner_id": order.partner_id.id,
                "invoice_date": fields.Date.context_today(order),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": line.product_id.id,
                            "quantity": line.product_qty,
                            "price_unit": line.price_unit,
                            "purchase_line_id": line.id,
                            "name": line.name,
                        }
                    )
                    for line in order.order_line
                ],
            }
        )
        return invoice

    def _po_keys(self, rows):
        return {row["key"] for row in rows}

    def test_goods_received_appear_until_accepted(self):
        order = self._create_po(self.goods, 8.0)
        order.button_confirm()
        picking = order.picking_ids[:1]
        self.assertTrue(picking)
        self._validate_picking(picking)
        self.assertEqual(picking.state, "done")
        data = self.WA.get_work_acceptance_dashboard()
        self.assertIn(f"po:{order.id}", self._po_keys(data["goods"]["rows"]))
        goods_row = next(
            row for row in data["goods"]["rows"] if row["key"] == f"po:{order.id}"
        )
        qc = picking.qc_id or picking.qc_ids[:1]
        self.assertTrue(qc)
        self.assertEqual(goods_row["qc_label"], qc.name)
        self.assertEqual(goods_row["qc_key"], f"qc:{qc.id}")
        qc_action = self.WA.action_open_dashboard_item(goods_row["qc_key"])
        self.assertEqual(qc_action.get("res_model"), "vpk.stock.qc")
        self.assertEqual(qc_action.get("res_id"), qc.id)
        action = self.WA.action_open_dashboard_item(f"po:{order.id}")
        self.assertEqual(action.get("res_model"), "work.acceptance")
        wa = self.WA.create(
            {
                "purchase_id": order.id,
                "partner_id": order.partner_id.id,
                "date_due": fields.Datetime.now(),
                "date_receive": fields.Datetime.now(),
                "wa_line_ids": [
                    Command.create(
                        {
                            "purchase_line_id": order.order_line.id,
                            "product_id": self.goods.id,
                            "name": self.goods.display_name,
                            "product_qty": 8.0,
                            "product_uom": self.goods.uom_id.id,
                            "price_unit": order.order_line.price_unit,
                        }
                    )
                ],
            }
        )
        self.assertEqual(wa.qc_id, qc)
        wa.button_accept()
        data = self.WA.get_work_acceptance_dashboard()
        self.assertNotIn(f"po:{order.id}", self._po_keys(data["goods"]["rows"]))

    def test_service_with_vendor_bill_appears(self):
        order = self._create_po(self.service, 3.0)
        order.button_confirm()
        data = self.WA.get_work_acceptance_dashboard()
        self.assertNotIn(f"po:{order.id}", self._po_keys(data["services"]["rows"]))
        bill = self._create_vendor_bill(order)
        self.assertTrue(bill.invoice_line_ids.purchase_line_id)
        data = self.WA.get_work_acceptance_dashboard()
        self.assertIn(f"po:{order.id}", self._po_keys(data["services"]["rows"]))
        kpi = {item["id"]: item for item in data["kpis"]}
        self.assertGreaterEqual(int(kpi["services"]["value"]), 1)
