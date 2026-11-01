# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged

PDF = base64.b64encode(b"%PDF-1.4\n%%EOF\n")


@tagged("post_install", "-at_install")
class TestContractDocument(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        partner = cls.env["res.partner"].create({"name": "คู่ค้าทดสอบ"})
        cls.contract = cls.env["purchase.contract"].create(
            {"partner_id": partner.id, "amount_total": 1000.0}
        )
        cls.doc_type = cls.env.ref(
            "vpk_purchase_contract_document.studio_document_type_contract_document"
        )

    def _wizard(self, **vals):
        return (
            self.env["vpk.contract.document.add.wizard"]
            .with_context(default_contract_id=self.contract.id)
            .create({"studio_document_type_id": self.doc_type.id, **vals})
        )

    def test_attach_mode_creates_document(self):
        wizard = self._wizard(add_mode="attach", file=PDF, filename="contract.pdf")
        wizard.action_confirm()
        document = self.contract.contract_document_ids
        self.assertEqual(len(document), 1)
        self.assertEqual(document.document_type_id, self.doc_type)
        self.assertEqual(document.signature_state, "not_sent")
        self.assertTrue(document.attachment_id)
        self.assertEqual(document.action_preview_document()["type"], "ir.actions.act_url")

    def test_attach_mode_requires_file(self):
        with self.assertRaises(UserError):
            self._wizard(add_mode="attach").action_confirm()

    def test_send_for_signature_creates_studio_document(self):
        self._wizard(add_mode="attach", file=PDF, filename="contract.pdf").action_confirm()
        document = self.contract.contract_document_ids
        self.env["purchase.contract.document.signer"].create(
            {"document_id": document.id, "user_id": self.env.user.id, "is_sign": True}
        )
        self.assertEqual(document.signer_summary, self.env.user.name)
        studio = document._ensure_studio_document()
        self.assertEqual(document.studio_document_id, studio)
        self.assertEqual(studio.source_ref, self.contract)
        self.assertEqual(studio.vpk_approver_line_ids.user_id, self.env.user)


@tagged("post_install", "-at_install")
class TestDepartmentContractDocumentReadonly(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept = cls.env["res.users"].create(
            {
                "name": "หน่วยงานดูเอกสารสัญญา",
                "login": "vpk_dept_contract_doc_ro",
                "email": "vpk_dept_contract_doc_ro@test.vpk",
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
        partner = cls.env["res.partner"].create({"name": "คู่ค้าเอกสารสัญญา"})
        cls.contract = cls.env["purchase.contract"].create(
            {"partner_id": partner.id, "amount_total": 1000.0}
        )
        product = cls.env["product.product"].create(
            {"name": "สินค้าเอกสารสัญญา", "purchase_ok": True, "type": "consu"}
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
        cls.env["purchase.request"].create(vals)
        doc_type = cls.env.ref(
            "vpk_purchase_contract_document.studio_document_type_contract_document"
        )
        cls.document = cls.env["purchase.contract.document"].create(
            {
                "contract_id": cls.contract.id,
                "document_type_id": doc_type.id,
            }
        )

    def test_department_can_read_contract_and_documents(self):
        contract = self.contract.with_user(self.dept)
        self.assertEqual(contract.name, self.contract.name)
        self.assertEqual(contract.contract_document_ids, self.document)
        action = self.env["purchase.request"].search(
            [("requested_by", "=", self.dept.id)], limit=1
        ).with_user(self.dept).action_open_related_contract()
        self.assertEqual(action.get("flags", {}).get("mode"), "readonly")

    def test_department_cannot_write_contract_document(self):
        with self.assertRaises(AccessError):
            self.document.with_user(self.dept).write({"notes": "แก้ไม่ได้"})
