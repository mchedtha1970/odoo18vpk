# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestVendorApiService(TransactionCase):
    def setUp(self):
        super().setUp()
        self.service = self.env["vpk.vendor.api.service"]
        self.env["ir.config_parameter"].sudo().set_param(
            "vpk_vendor_api.api_key", "test-vendor-key"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "vpk_vendor_api.enabled", "True"
        )

    def test_register_create_and_upsert(self):
        payload = {
            "external_id": "EXT-VENDOR-001",
            "company_type": "company",
            "name_company": "ทดสอบ Vendor API",
            "partner_company_type_code": "บจก.",
            "vat": "0123456789012",
            "company_registry": "00000",
            "email": "vendor-api-test@example.com",
            "phone": "021111111",
            "street": "1 Test Road",
            "zip": "10400",
            "country_code": "TH",
            "banks": [
                {
                    "acc_number": "1234567890",
                    "bank_name": "ธนาคารทดสอบ Vendor API",
                    "acc_holder_name": "ทดสอบ Vendor API",
                }
            ],
            "contacts": [
                {
                    "name": "ผู้ติดต่อทดสอบ",
                    "email": "contact-api@example.com",
                    "phone": "0811111111",
                    "function": "Sales",
                }
            ],
        }
        result = self.service.register_vendor(payload)
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "created")
        partner = self.env["res.partner"].browse(result["partner_id"])
        self.assertEqual(partner.vpk_vendor_external_id, "EXT-VENDOR-001")
        self.assertGreaterEqual(partner.supplier_rank, 1)
        self.assertTrue(partner.bank_ids)
        self.assertTrue(partner.child_ids)

        payload["name_company"] = "ทดสอบ Vendor API Updated"
        payload["phone"] = "022222222"
        result2 = self.service.register_vendor(payload)
        self.assertEqual(result2["action"], "updated")
        self.assertEqual(result2["partner_id"], partner.id)
        self.assertEqual(partner.name_company, "ทดสอบ Vendor API Updated")
        self.assertEqual(partner.phone, "022222222")

    def test_register_requires_name(self):
        with self.assertRaises(UserError):
            self.service.register_vendor(
                {
                    "external_id": "EXT-NO-NAME",
                    "company_type": "company",
                    "vat": "0999999999999",
                }
            )

    def test_register_with_documents_base64(self):
        import base64

        pdf_bytes = b"%PDF-1.4 vendor commercial doc test"
        payload = {
            "external_id": "EXT-VENDOR-DOC-001",
            "company_type": "company",
            "name_company": "Vendor มีเอกสาร",
            "vat": "0333333333333",
            "company_registry": "00000",
            "documents": [
                {
                    "filename": "commercial_registration.pdf",
                    "display_name": "หนังสือรับรองบริษัท",
                    "doc_type": "commercial_registration",
                    "mimetype": "application/pdf",
                    "content_base64": base64.b64encode(pdf_bytes).decode(),
                }
            ],
        }
        result = self.service.register_vendor(payload)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(result["documents"][0]["doc_type"], "commercial_registration")
        partner = self.env["res.partner"].browse(result["partner_id"])
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
        )
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments.name, "commercial_registration.pdf")

        # Replace same file
        result2 = self.service.upload_vendor_documents(
            partner,
            [
                {
                    "filename": "commercial_registration.pdf",
                    "doc_type": "commercial_registration",
                    "display_name": "หนังสือรับรองบริษัท",
                    "content_base64": base64.b64encode(pdf_bytes + b" v2").decode(),
                    "replace": True,
                }
            ],
        )
        self.assertEqual(result2["documents"][0]["action"], "updated")
        self.assertEqual(
            len(
                self.env["ir.attachment"].search(
                    [("res_model", "=", "res.partner"), ("res_id", "=", partner.id)]
                )
            ),
            1,
        )
