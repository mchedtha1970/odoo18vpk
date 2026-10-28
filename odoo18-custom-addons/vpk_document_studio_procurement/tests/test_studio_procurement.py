import base64

from odoo.tests import TransactionCase, tagged

from ..models.template_installer import DOCUMENT_TYPES, TEMPLATES

FAKE_PDF = base64.b64encode(b"%PDF-1.4\n%%EOF\n").decode()


@tagged("post_install", "-at_install")
class TestStudioProcurement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env["vpk.document.studio.document"]
        cls.Type = cls.env["vpk.document.studio.document.type"]
        cls.Template = cls.env["vpk.document.studio.template"]

    def _type(self, code):
        return self.Type.search([("code", "=", code)], limit=1)

    def _request_with_committee(self):
        request = self.env["purchase.request"].search(
            [("work_acceptance_committee_ids", "!=", False)], limit=1
        )
        if not request:
            self.skipTest("No purchase request with a work acceptance committee")
        return request

    def test_document_types_and_templates_installed(self):
        for code, _name, _model in DOCUMENT_TYPES:
            doc_type = self._type(code)
            self.assertTrue(doc_type, code)
            if code not in TEMPLATES:
                continue
            template = self.Template._vpk_template_for_type(doc_type)
            self.assertTrue(template, code)
            self.assertTrue(template.block_ids)
            self.assertIn("{{", template.layout_html or "")
            self.assertTrue(template.field_ids)

    def test_installer_is_idempotent(self):
        before = self.Template.search_count([])
        self.Template._vpk_install_procurement_templates()
        self.assertEqual(self.Template.search_count([]), before)

    def test_multiline_codes_are_text_fields(self):
        template = self.Template._vpk_template_for_type(self._type("wa_committee_order"))
        field = template.field_ids.filtered(lambda f: f.code == "committee_lines")
        self.assertEqual(field.field_type, "text")

    def test_committee_order_values_from_request(self):
        request = self._request_with_committee()
        document = self.Document._vpk_create_for_record(
            request, self._type("wa_committee_order")
        )
        self.assertEqual(document.request_id, request)
        self.assertEqual(document.document_type_code, "wa_committee_order")
        values = document.value_json or {}
        self.assertTrue(values.get("committee_lines"))
        self.assertTrue(values.get("subject"))
        self.assertTrue(document.vpk_approver_line_ids)

    def test_custom_type_gets_no_default_wording(self):
        request = self._request_with_committee()
        Values = self.env["vpk.procurement.document.values"]
        custom = Values.values_from_request(request, "custom_studio_type")
        self.assertEqual(custom["subject"], "")
        self.assertEqual(custom["body"], "")
        self.assertTrue(custom["item_summary"])
        committee = Values.values_from_request(request, "wa_committee_order")
        self.assertIn("แต่งตั้งคณะกรรมการตรวจรับพัสดุ", committee["subject"])
        self.assertTrue(committee["body"])

    def test_attach_uploaded_pdf_from_wizard(self):
        request = self._request_with_committee()
        action = request.action_open_add_studio_document_wizard()
        wizard = self.env["vpk.studio.document.add.wizard"].browse(action["res_id"])
        wizard.write(
            {
                "document_type_id": self._type("purchase_approval_memo").id,
                "add_mode": "attach",
                "file": FAKE_PDF,
                "filename": "memo.pdf",
            }
        )
        result = wizard.action_confirm()
        document = self.Document.browse(result["res_id"])
        self.assertEqual(document.source_mode, "uploaded")
        self.assertEqual(document.request_id, request)
        self.assertTrue(document.pdf_file)
        self.assertIn(document, request.studio_document_ids)

    def test_egp_wizard_uses_studio_document_type(self):
        requisition = self.env["purchase.requisition"].search([], limit=1)
        if not requisition:
            self.skipTest("No purchase agreement")
        studio_type = self.Type.create({"name": "รายงานทดสอบ e-GP", "code": "test_egp_studio"})
        template = self.Template.create(
            {
                "name": "แบบทดสอบ e-GP",
                "code": "test_egp_studio_tmpl",
                "document_type_id": studio_type.id,
            }
        )
        wizard = self.env["vpk.egp.document.add.wizard"].create(
            {"requisition_id": requisition.id, "add_mode": "studio"}
        )
        available = self.Type.search(
            [
                ("company_id", "in", [False, requisition.company_id.id]),
                ("template_ids.active", "=", True),
                "|",
                ("template_ids.source_model_name", "=", False),
                ("template_ids.source_model_name", "in", ["purchase.request", "purchase.requisition"]),
            ]
        )
        self.assertIn(studio_type, available)
        wizard.studio_document_type_id = studio_type
        wizard._onchange_studio_document_type()
        self.assertEqual(wizard.studio_template_id, template)
        wizard.action_confirm()
        egp_document = requisition.egp_document_ids.filtered(
            lambda doc: doc.document_type_code == "test_egp_studio"
        )
        self.assertTrue(egp_document)
        self.assertEqual(egp_document.studio_document_id.document_type_id, studio_type)
        studio_document = egp_document.studio_document_id
        studio_document.write({"pdf_file": FAKE_PDF, "pdf_filename": "studio.pdf"})
        self.assertEqual(egp_document.document_filename, "studio.pdf")
        self.assertTrue(egp_document.document_file)
        egp_document.unlink()
        self.assertFalse(studio_document.exists())

    def test_egp_wizard_attach_uses_studio_document_type(self):
        requisition = self.env["purchase.requisition"].search([], limit=1)
        if not requisition:
            self.skipTest("No purchase agreement")
        studio_type = self.Type.create({"name": "ไฟล์ทดสอบ e-GP", "code": "test_egp_attach"})
        wizard = self.env["vpk.egp.document.add.wizard"].create(
            {
                "requisition_id": requisition.id,
                "add_mode": "attach",
                "studio_document_type_id": studio_type.id,
                "file": FAKE_PDF,
                "filename": "egp.pdf",
            }
        )
        wizard.action_confirm()
        egp_document = requisition.egp_document_ids.filtered(
            lambda doc: doc.document_type_code == "test_egp_attach"
        )
        self.assertTrue(egp_document.document_file)
        self.assertEqual(egp_document._studio_document_type(), studio_type)

    def test_generate_committee_order_pdf(self):
        request = self._request_with_committee()
        document = self.Document._vpk_create_for_record(
            request, self._type("wa_committee_order")
        )
        if not document._soffice_path():
            self.skipTest("LibreOffice is required to render PDF")
        document.action_generate_pdf()
        self.assertTrue(base64.b64decode(document.pdf_file).startswith(b"%PDF"))
