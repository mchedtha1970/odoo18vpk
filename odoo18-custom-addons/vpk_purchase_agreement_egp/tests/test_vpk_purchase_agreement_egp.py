# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestVpkPurchaseAgreementEgp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Vendor A", "supplier_rank": 1})
        cls.partner_b = cls.env["res.partner"].create({"name": "Vendor B", "supplier_rank": 1})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Medical Supply",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        cls.requisition = cls.env["purchase.requisition"].create(
            {
                "requisition_type": "egp_procurement",
                "egp_reference": "EGP-PRJ-001",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_qty": 5.0,
                        },
                    )
                ],
            }
        )

    def test_egp_agreement_sequence_and_confirm(self):
        self.assertTrue(self.requisition.name.startswith("EGP/"))
        self.requisition.action_confirm()
        self.assertEqual(self.requisition.state, "confirmed")

    def test_create_rfq_propagates_origin(self):
        self.requisition.action_confirm()
        wizard = self.env["purchase.requisition.create.rfq"].create(
            {
                "requisition_id": self.requisition.id,
                "partner_id": self.partner.id,
                "egp_bid_reference": "BID-001",
            }
        )
        action = wizard.action_create_rfq()
        purchase_order = self.env["purchase.order"].browse(action["res_id"])
        self.assertEqual(purchase_order.requisition_id, self.requisition)
        self.assertIn("EGP-PRJ-001", purchase_order.origin)
        self.assertIn(self.requisition.name, purchase_order.origin)
        self.assertIn("BID-001", purchase_order.origin)
        self.assertEqual(purchase_order.order_line[0].product_qty, 5.0)
        self.assertEqual(purchase_order.order_line[0].price_unit, 0.0)

    def test_alternative_keeps_requisition(self):
        self.requisition.action_confirm()
        first_rfq = self.env["purchase.order"].create(
            self.requisition._prepare_rfq_vals(self.partner, "BID-A")
        )
        alternative_wizard = self.env["purchase.requisition.create.alternative"].create(
            {
                "origin_po_id": first_rfq.id,
                "partner_id": self.partner_b.id,
                "copy_products": True,
            }
        )
        action = alternative_wizard.action_create_alternative()
        second_rfq = self.env["purchase.order"].browse(action["res_id"])
        self.assertEqual(second_rfq.requisition_id, self.requisition)
        self.assertEqual(second_rfq.origin, first_rfq.origin)

    def test_egp_document_auto_reference(self):
        self.requisition.egp_reference = "EGP-PROJECT-999"
        invitation_type = self.env.ref(
            "vpk_purchase_agreement_egp.egp_document_type_invitation"
        )
        document = self.env["purchase.requisition.egp.document"].new(
            {
                "requisition_id": self.requisition.id,
                "document_type_id": invitation_type.id,
            }
        )
        document._onchange_document_type_id()
        self.assertEqual(document.egp_reference, "EGP-PROJECT-999")

    def test_egp_document_preview(self):
        invitation_type = self.env.ref(
            "vpk_purchase_agreement_egp.egp_document_type_invitation"
        )
        document = self.env["purchase.requisition.egp.document"].create(
            {
                "requisition_id": self.requisition.id,
                "document_type_id": invitation_type.id,
                "egp_reference": "EGP-INV-001",
                "document_file": "dGVzdA==",
                "document_filename": "invitation.pdf",
            }
        )
        self.assertTrue(document.attachment_id)
        action = document.action_preview_document()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertIn(str(document.attachment_id.id), action["url"])
        self.requisition._update_egp_reference_from_documents()
        self.assertEqual(self.requisition.egp_reference, "EGP-INV-001")

    def test_egp_flow_stage_progression(self):
        self.assertEqual(self.requisition.egp_flow_stage, "draft")
        self.requisition.action_confirm()
        self.assertEqual(self.requisition.egp_flow_stage, "confirmed")
        invitation_type = self.env.ref(
            "vpk_purchase_agreement_egp.egp_document_type_invitation"
        )
        self.env["purchase.requisition.egp.document"].create(
            {
                "requisition_id": self.requisition.id,
                "document_type_id": invitation_type.id,
            }
        )
        self.assertEqual(self.requisition.egp_flow_stage, "egp_docs")
        self.env["purchase.order"].create(
            self.requisition._prepare_rfq_vals(self.partner, "BID-A")
        )
        self.assertEqual(self.requisition.egp_flow_stage, "rfq")
        self.env["purchase.order"].create(
            self.requisition._prepare_rfq_vals(self.partner_b, "BID-B")
        )
        self.assertEqual(self.requisition.egp_flow_stage, "compare")
        self.assertIn("vpk_egp_flow_current", self.requisition.egp_flow_html)

    def test_pr_create_rfq_from_linked_agreement(self):
        purchase_type = self.env.ref("l10n_th_gov_purchase_request.purchase_type_001")
        procurement_type = self.env.ref("l10n_th_gov_purchase_request.procurement_type_001")
        procurement_method = self.env.ref("l10n_th_gov_purchase_request.procurement_specific")
        request = self.env["purchase.request"].create(
            {
                "purchase_type_id": purchase_type.id,
                "procurement_type_id": procurement_type.id,
                "procurement_method_id": procurement_method.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 5.0,
                        },
                    )
                ],
            }
        )
        request.write({"state": "approved"})
        self.requisition.action_confirm()
        self.requisition.line_ids[0].write(
            {"purchase_request_lines": [(4, request.line_ids[0].id)]}
        )
        request.invalidate_recordset()
        self.assertEqual(request.egp_requisition_id, self.requisition)
        self.assertTrue(request.can_create_egp_rfq)
        action = request.action_open_create_rfq_wizard()
        self.assertEqual(action["res_model"], "purchase.requisition.create.rfq")
        wizard = self.env["purchase.requisition.create.rfq"].create(
            {
                "requisition_id": self.requisition.id,
                "partner_id": self.partner.id,
                "egp_bid_reference": "BID-PR-001",
            }
        )
        po_action = wizard.action_create_rfq()
        purchase_order = self.env["purchase.order"].browse(po_action["res_id"])
        self.assertEqual(purchase_order.requisition_id, self.requisition)

    def test_create_rfq_from_pr_keeps_qty_uom_and_winner_price(self):
        purchase_type = self.env.ref("l10n_th_gov_purchase_request.purchase_type_001")
        procurement_type = self.env.ref("l10n_th_gov_purchase_request.procurement_type_001")
        procurement_method = self.env.ref("l10n_th_gov_purchase_request.procurement_specific")
        request = self.env["purchase.request"].create(
            {
                "purchase_type_id": purchase_type.id,
                "procurement_type_id": procurement_type.id,
                "procurement_method_id": procurement_method.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 300.0,
                            "product_uom_id": self.product.uom_id.id,
                            "estimated_cost": 26643.0,
                        },
                    )
                ],
            }
        )
        request.write({"state": "approved"})
        self.requisition.write({"purchase_request_id": request.id})
        self.requisition.action_confirm()
        self.env["purchase.requisition.egp.bid"].create(
            {
                "requisition_id": self.requisition.id,
                "partner_id": self.partner.id,
                "amount_total": 26643.0,
                "is_winner": True,
            }
        )
        vals = self.requisition._prepare_rfq_vals(self.partner, "BID-WIN")
        purchase_order = self.env["purchase.order"].create(vals)
        line = purchase_order.order_line
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_qty, 300.0)
        self.assertEqual(line.product_uom, self.product.uom_id)
        self.assertAlmostEqual(line.price_unit, 88.81, places=2)
        self.assertAlmostEqual(line.price_subtotal, 26643.0, places=2)

    def _vpk_make_egp_purchase_request(self):
        purchase_type = self.env.ref("l10n_th_gov_purchase_request.purchase_type_001")
        procurement_type = self.env.ref("l10n_th_gov_purchase_request.procurement_type_001")
        procurement_method = self.env.ref(
            "l10n_th_gov_purchase_request.procurement_specific"
        )
        return self.env["purchase.request"].create(
            {
                "purchase_type_id": purchase_type.id,
                "procurement_type_id": procurement_type.id,
                "procurement_method_id": procurement_method.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 5.0,
                        },
                    )
                ],
            }
        )

    def _vpk_mark_document_approved(self, document):
        document.review_ids.unlink()
        self.env.cr.execute(
            "UPDATE vpk_official_document SET state = 'approved' WHERE id = %s",
            [document.id],
        )
        document.invalidate_recordset()
        return document

    def test_send_to_egp_button_requires_related_documents(self):
        request = self._vpk_make_egp_purchase_request()
        request.write({"state": "approved"})
        request.invalidate_recordset()
        self.assertFalse(request.can_send_to_egp)
        Document = self.env["vpk.official.document"]
        order = self._vpk_mark_document_approved(
            Document.create(
                {
                    "document_type": "wa_committee_order",
                    "request_id": request.id,
                }
            )
        )
        integrity = self._vpk_mark_document_approved(
            Document.create(
                {
                    "document_type": "integrity_over_100k",
                    "request_id": request.id,
                }
            )
        )
        request.invalidate_recordset()
        self.assertFalse(
            request.can_send_to_egp,
            "ต้องมีรายงานขออนุมัติด้วย จึงจะส่ง e-GP ได้",
        )
        approval = self._vpk_mark_document_approved(
            Document.create(
                {
                    "document_type": "specific_method_approval",
                    "request_id": request.id,
                }
            )
        )
        request.invalidate_recordset()
        self.assertTrue(request.can_send_to_egp)
        integrity.with_context(skip_validation_check=True).write({"state": "to_approve"})
        request.invalidate_recordset()
        self.assertFalse(request.can_send_to_egp)
        self._vpk_mark_document_approved(integrity)
        request.invalidate_recordset()
        self.assertTrue(request.can_send_to_egp)
        action = request.action_send_to_egp()
        self.assertEqual(
            action["res_model"],
            "purchase.request.line.make.purchase.requisition",
        )
        self.assertEqual(order.state, "approved")
        self.assertEqual(approval.state, "approved")
