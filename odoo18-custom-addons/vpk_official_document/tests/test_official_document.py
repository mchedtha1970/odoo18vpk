# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOfficialDocument(TransactionCase):
    def test_generate_docx_from_lines(self):
        template = self.env["vpk.official.document.template"].search(
            [("code", "=", "wa_committee_order")],
            limit=1,
        )
        self.assertTrue(template, "Default Word template should be loaded")
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "wa_committee_order",
                "template_id": template.id,
                "agency": "โรงพยาบาลวชิระภูเก็ต",
                "item_summary": "วัสดุสำนักงาน",
                "procurement_method": "วิธีเฉพาะเจาะจง",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "นายทดสอบ ประธาน",
                            "position": "หัวหน้ากลุ่มงาน",
                            "role": "chairman",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "นางทดสอบ กรรมการ",
                            "position": "นักวิชาการพัสดุ",
                            "role": "committee",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "นางสาวทดสอบ เลขา",
                            "position": "เจ้าพนักงานพัสดุ",
                            "role": "secretary",
                        },
                    ),
                ],
            }
        )
        document.action_generate_docx()
        self.assertEqual(document.state, "generated")
        self.assertTrue(document.docx_file)
        self.assertIn("คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ", document.docx_filename)
        if not document._soffice_path():
            self.skipTest("LibreOffice is required to generate PDF from the Word template")
        document.action_generate_pdf()
        self.assertTrue(document.pdf_file)
        self.assertTrue(document.pdf_attachment_id)
        self.assertTrue(document.pdf_filename.endswith(".pdf"))
        self.assertTrue(document.has_pdf)
        self.assertIn(document.pdf_attachment_id, document.generated_attachment_ids)
        self.assertTrue(document.pdf_attachment_id.mimetype.startswith("application/pdf"))
        pdf_content = document.pdf_file
        import base64

        self.assertTrue(base64.b64decode(pdf_content).startswith(b"%PDF"))

    def test_generate_integrity_form(self):
        template = self.env["vpk.official.document.template"].search(
            [("code", "=", "integrity_over_100k")],
            limit=1,
        )
        self.assertTrue(template, "Integrity Word template should be loaded")
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "integrity_over_100k",
                "template_id": template.id,
                "head_officer_name": "นางสาวปรีดา สุดขาว",
                "head_officer_position": "หัวหน้าเจ้าหน้าที่",
                "officer_name": "นางทดสอบ เจ้าหน้าที่",
                "officer_position": "นักวิชาการพัสดุ",
                "line_ids": [
                    (0, 0, {"name": "นายทดสอบ ประธาน", "role": "chairman"}),
                    (0, 0, {"name": "นางทดสอบ กรรมการ", "role": "committee"}),
                ],
            }
        )
        document.action_generate_docx()
        self.assertTrue(document.docx_file)
        self.assertIn("แบบแสดงความบริสุทธิ์ใจ", document.docx_filename)

    def test_generate_spec_price_committee_form(self):
        template = self.env["vpk.official.document.template"].search(
            [("code", "=", "spec_price_committee")],
            limit=1,
        )
        self.assertTrue(template, "Spec committee Word template should be loaded")
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "spec_price_committee",
                "template_id": template.id,
                "agency": "กลุ่มงานพัสดุ โรงพยาบาลวชิระภูเก็ต",
                "recipient": "ผู้ว่าราชการจังหวัดภูเก็ต",
                "item_summary": "วัสดุสำนักงาน",
                "procurement_method": "วิธีเฉพาะเจาะจง",
                "line_ids": [
                    (0, 0, {"name": "นายทดสอบ ประธาน", "role": "chairman"}),
                    (0, 0, {"name": "นางทดสอบ กรรมการ", "role": "committee"}),
                ],
            }
        )
        document.action_generate_docx()
        self.assertTrue(document.docx_file)
        self.assertIn("ขออนุมัติแต่งตั้งคณะกรรมการกำหนดคุณลักษณะ", document.docx_filename)

    def test_generate_specific_method_approval_form(self):
        template = self.env["vpk.official.document.template"].search(
            [("code", "=", "specific_method_approval")],
            limit=1,
        )
        self.assertTrue(template, "Specific method Word template should be loaded")
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "specific_method_approval",
                "template_id": template.id,
                "agency": "กลุ่มงานพัสดุ โรงพยาบาลวชิระภูเก็ต",
                "recipient": "ผู้ว่าราชการจังหวัดภูเก็ต",
                "item_summary": "วัสดุสำนักงาน",
                "officer_name": "นางทดสอบ เจ้าหน้าที่",
                "head_officer_name": "นางสาวปรีดา สุดขาว",
                "amount_total": 123456,
                "line_ids": [
                    (0, 0, {"name": "นายทดสอบ ประธาน", "role": "chairman"}),
                ],
            }
        )
        document.action_generate_docx()
        self.assertTrue(document.docx_file)
        self.assertIn("รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง", document.docx_filename)
        self.assertEqual(document.work_detail, "รายละเอียดตามเอกสารแนบท้าย")
        import base64
        from odoo.addons.vpk_official_document.tests.test_docx_renderer import _docx_text

        text = _docx_text(base64.b64decode(document.docx_file))
        self.assertNotIn("ราคาต่อหน่วย (บาท)", text)
        self.assertNotIn("จำนวนเงิน (บาท)", text)

    def test_reopen_existing_order_for_same_request(self):
        request = self.env["purchase.request"].search([], limit=1)
        if not request:
            self.skipTest("No purchase request in test database")
        Document = self.env["vpk.official.document"]
        existing = Document._find_existing_wa_committee_order(request=request)
        if not existing:
            existing = Document.create(
                {
                    "document_type": "wa_committee_order",
                    "request_id": request.id,
                    "line_ids": [
                        (0, 0, {"name": "นายทดสอบ ประธาน", "role": "chairman"}),
                    ],
                }
            )
        opened = Document.create_from_purchase_request(request)
        self.assertEqual(existing, opened)
        opened_again = request.action_create_wa_committee_order()
        self.assertEqual(opened_again.get("res_id"), existing.id)

    def test_request_validation_sends_packet_to_director_inbox(self):
        if not hasattr(type(self.env["purchase.request"]), "request_validation"):
            self.skipTest("Tier validation is not installed")
        request = self.env["purchase.request"].search(
            [("state", "=", "draft"), ("review_ids", "=", False)],
            limit=1,
        )
        if not request:
            self.skipTest("No draft purchase request without reviews")
        if not request.work_acceptance_committee_ids:
            self.skipTest("Draft PR has no work acceptance committee")
        Definition = self.env["tier.definition"]
        if not Definition.search([("model", "=", "purchase.request")], limit=1):
            model = self.env["ir.model"]._get("purchase.request")
            Definition.create(
                {
                    "name": "ทดสอบอนุมัติ PR",
                    "model_id": model.id,
                    "review_type": "individual",
                    "reviewer_id": self.env.user.id,
                    "definition_type": "domain",
                    "definition_domain": "[]",
                    "sequence": 10,
                    "company_id": False,
                }
            )
        Document = self.env["vpk.official.document"]
        order = Document.create_from_purchase_request(request)
        approval = Document.create_specific_method_approval_from_purchase_request(
            request
        )
        fake_pdf = "JVBERi0xLjQK"
        for doc in order | approval:
            attachment = self.env["ir.attachment"].create(
                {
                    "name": "%s.pdf" % doc.name,
                    "datas": fake_pdf,
                    "res_model": doc._name,
                    "res_id": doc.id,
                    "mimetype": "application/pdf",
                }
            )
            doc.write(
                {
                    "pdf_file": fake_pdf,
                    "pdf_filename": "%s.pdf" % doc.name,
                    "pdf_attachment_id": attachment.id,
                }
            )
        request.request_validation()
        self.assertTrue(request.review_ids)
        self.assertTrue(
            order.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
        )
        self.assertTrue(
            approval.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
        )
        self.assertTrue(request.has_approval_attachments)

    def test_send_for_signature_sets_waiting_status(self):
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "wa_committee_order",
                "agency": "โรงพยาบาลวชิระภูเก็ต",
                "line_ids": [
                    (0, 0, {"name": "นายทดสอบ ประธาน", "role": "chairman"}),
                ],
            }
        )
        self.assertEqual(document.signature_state, "not_sent")
        fake_pdf = "JVBERi0xLjQK"
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.pdf" % document.name,
                "datas": fake_pdf,
                "res_model": document._name,
                "res_id": document.id,
                "mimetype": "application/pdf",
            }
        )
        document.write(
            {
                "pdf_file": fake_pdf,
                "pdf_filename": "%s.pdf" % document.name,
                "pdf_attachment_id": attachment.id,
                "state": "generated",
            }
        )
        document.action_send_for_signature()
        self.assertEqual(document.state, "to_approve")
        self.assertEqual(document.signature_state, "waiting")
        document.with_context(skip_validation_check=True).write(
            {
                "signed_on": fields.Datetime.now(),
                "state": "approved",
            }
        )
        self.assertEqual(document.signature_state, "signed")

    def test_specific_method_approval_signs_in_sequence(self):
        from odoo.fields import Command

        password = "SeqSign@2569"
        officer = self.env["res.users"].create(
            {
                "name": "นายทดสอบ เจ้าหน้าที่ลำดับ",
                "login": "seq.officer",
                "password": password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        head = self.env["res.users"].create(
            {
                "name": "นางทดสอบ หัวหน้าเจ้าหน้าที่ลำดับ",
                "login": "seq.head",
                "password": password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        director = self.env["res.users"].create(
            {
                "name": "นายทดสอบ ผู้อำนวยการลำดับ",
                "login": "seq.director",
                "password": password,
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "specific_method_approval",
                "officer_id": officer.id,
                "head_officer_id": head.id,
                "signer_id": director.id,
                "state": "to_approve",
            }
        )
        document._vpk_create_sequential_sign_reviews()
        reviews = document.review_ids.sorted("sequence")
        self.assertEqual(len(reviews), 3)
        self.assertEqual(reviews[0].status, "pending")
        self.assertEqual(reviews[1].status, "waiting")
        self.assertEqual(reviews[2].status, "waiting")
        self.assertIn(officer, reviews[0].reviewer_ids)
        self.assertIn(head, reviews[1].reviewer_ids)
        self.assertIn(director, reviews[2].reviewer_ids)
        self.assertTrue(document.with_user(officer).can_review)
        self.assertFalse(document.with_user(head).can_review)
        self.assertFalse(document.with_user(director).can_review)
        document.with_user(officer).validate_tier()
        reviews.invalidate_recordset()
        document.invalidate_recordset()
        self.assertEqual(reviews[0].status, "approved")
        self.assertEqual(reviews[1].status, "pending")
        self.assertEqual(document.state, "to_approve")
        self.assertTrue(document.with_user(head).can_review)
        self.assertFalse(document.with_user(director).can_review)
        self.assertEqual(
            document._signature_name_for_user(officer),
            document.officer_name,
        )
        self.assertEqual(
            document._signature_name_for_user(head),
            document.head_officer_name,
        )
        self.assertEqual(
            document._signature_name_for_user(director),
            document.signer_name,
        )

    def test_integrity_over_100k_signs_in_sequence(self):
        from odoo.fields import Command

        password = "SeqSign@2569"
        group_user = self.env.ref("base.group_user").id
        officer = self.env["res.users"].create(
            {
                "name": "นายทดสอบ เจ้าหน้าที่ความบริสุทธิ์",
                "login": "seq.integrity.officer",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        head = self.env["res.users"].create(
            {
                "name": "นางทดสอบ หัวหน้าเจ้าหน้าที่ความบริสุทธิ์",
                "login": "seq.integrity.head",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        chairman = self.env["res.users"].create(
            {
                "name": "นายทดสอบ ประธานกรรมการความบริสุทธิ์",
                "login": "seq.integrity.chair",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        member = self.env["res.users"].create(
            {
                "name": "นางทดสอบ กรรมการความบริสุทธิ์",
                "login": "seq.integrity.member",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "integrity_over_100k",
                "officer_id": officer.id,
                "head_officer_id": head.id,
                "state": "to_approve",
                "line_ids": [
                    Command.create(
                        {
                            "name": "นายทดสอบ ประธานกรรมการความบริสุทธิ์",
                            "role": "chairman",
                            "sequence": 10,
                            "user_id": chairman.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "นางทดสอบ กรรมการความบริสุทธิ์",
                            "role": "committee",
                            "sequence": 20,
                            "user_id": member.id,
                        }
                    ),
                ],
            }
        )
        document._vpk_create_integrity_sign_reviews()
        reviews = document.review_ids.sorted("sequence")
        self.assertEqual(len(reviews), 4)
        self.assertEqual(reviews[0].status, "pending")
        self.assertEqual(reviews[1].status, "waiting")
        self.assertEqual(reviews[2].status, "waiting")
        self.assertEqual(reviews[3].status, "waiting")
        self.assertIn(officer, reviews[0].reviewer_ids)
        self.assertIn(head, reviews[1].reviewer_ids)
        self.assertIn(chairman, reviews[2].reviewer_ids)
        self.assertIn(member, reviews[3].reviewer_ids)
        self.assertTrue(document.with_user(officer).can_review)
        self.assertFalse(document.with_user(head).can_review)
        self.assertFalse(document.with_user(chairman).can_review)
        self.assertFalse(document.with_user(member).can_review)
        document.with_user(officer).validate_tier()
        reviews.invalidate_recordset()
        document.invalidate_recordset()
        self.assertEqual(reviews[0].status, "approved")
        self.assertEqual(reviews[1].status, "pending")
        self.assertEqual(document.state, "to_approve")
        self.assertTrue(document.with_user(head).can_review)
        self.assertFalse(document.with_user(chairman).can_review)
        document.with_user(head).validate_tier()
        reviews.invalidate_recordset()
        document.invalidate_recordset()
        self.assertEqual(reviews[1].status, "approved")
        self.assertEqual(reviews[2].status, "pending")
        self.assertEqual(document.state, "to_approve")
        self.assertTrue(document.with_user(chairman).can_review)
        self.assertFalse(document.with_user(member).can_review)
        self.assertEqual(
            document._signature_name_for_user(chairman),
            "นายทดสอบ ประธานกรรมการความบริสุทธิ์",
        )
        document.with_user(chairman).validate_tier()
        reviews.invalidate_recordset()
        document.invalidate_recordset()
        self.assertEqual(reviews[2].status, "approved")
        self.assertEqual(reviews[3].status, "pending")
        self.assertEqual(document.state, "to_approve")
        self.assertTrue(document.with_user(member).can_review)
        self.assertEqual(
            document._signature_name_for_user(member),
            "นางทดสอบ กรรมการความบริสุทธิ์",
        )
        document.with_user(member).validate_tier()
        reviews.invalidate_recordset()
        document.invalidate_recordset()
        self.assertEqual(reviews[3].status, "approved")
        self.assertEqual(document.state, "approved")
        self.assertEqual(document.signature_state, "signed")

    def test_purchase_user_can_send_approval_for_signature(self):
        from odoo.fields import Command

        password = "SeqSign@2569"
        group_user = self.env.ref("base.group_user").id
        group_purchase = self.env.ref("purchase.group_purchase_user").id
        procurement = self.env["res.users"].create(
            {
                "name": "ผู้ทดสอบพัสดุส่งอนุมัติ",
                "login": "seq.procurement.sender",
                "password": password,
                "groups_id": [Command.set([group_user, group_purchase])],
            }
        )
        officer = self.env["res.users"].create(
            {
                "name": "ผู้ทดสอบเจ้าหน้าที่ส่งอนุมัติ",
                "login": "seq.officer.sender",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        head = self.env["res.users"].create(
            {
                "name": "ผู้ทดสอบหัวหน้าเจ้าหน้าที่ส่งอนุมัติ",
                "login": "seq.head.sender",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        director = self.env["res.users"].create(
            {
                "name": "ผู้ทดสอบผู้อำนวยการส่งอนุมัติ",
                "login": "seq.director.sender",
                "password": password,
                "groups_id": [Command.set([group_user])],
            }
        )
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "specific_method_approval",
                "officer_id": officer.id,
                "head_officer_id": head.id,
                "signer_id": director.id,
                "state": "generated",
            }
        )
        fake_pdf = "JVBERi0xLjQK"
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.pdf" % document.name,
                "datas": fake_pdf,
                "res_model": document._name,
                "res_id": document.id,
                "mimetype": "application/pdf",
            }
        )
        document.write(
            {
                "pdf_file": fake_pdf,
                "pdf_filename": "%s.pdf" % document.name,
                "pdf_attachment_id": attachment.id,
            }
        )
        document.with_user(procurement).action_send_for_signature()
        self.assertEqual(document.state, "to_approve")
        self.assertEqual(document.signature_state, "waiting")
        reviews = document.review_ids.sorted("sequence")
        self.assertEqual(len(reviews), 3)
        self.assertIn(officer, reviews[0].reviewer_ids)
