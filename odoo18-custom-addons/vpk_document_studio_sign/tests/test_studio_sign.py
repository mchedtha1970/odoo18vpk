# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import io

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


def _pdf_with_name(name):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica", 12)
    pdf.drawString(300, 180, "(%s)" % name)
    pdf.save()
    return buffer.getvalue()


def _signature_png():
    from PIL import Image

    image = Image.new("RGBA", (240, 80), (0, 0, 0, 0))
    for x in range(20, 220):
        for y in range(20, 60):
            image.putpixel((x, y), (200, 0, 0, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@tagged("post_install", "-at_install")
class TestStudioSign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.checker = new_test_user(cls.env, login="studio_sign_checker", groups="base.group_user")
        cls.director = new_test_user(
            cls.env, login="studio_sign_director", name="Director Test", groups="base.group_user"
        )
        cls.env["hr.employee"].create({"name": "Director Test", "user_id": cls.director.id})
        cls.template = cls.env["vpk.document.studio.template"].create(
            {"name": "แบบทดสอบลงนาม", "code": "test_sign_form"}
        )

    def _document(self, with_checker=True):
        document = self.env["vpk.document.studio.document"].create(
            {"template_id": self.template.id}
        )
        document.write(
            {
                "pdf_file": base64.b64encode(_pdf_with_name("Director Test")),
                "pdf_filename": "test.pdf",
                "state": "generated",
            }
        )
        lines = []
        if with_checker:
            lines.append((self.checker, True, False))
        lines.append((self.director, False, True))
        for sequence, (user, is_check, is_sign) in enumerate(lines, start=1):
            self.env["vpk.approval.line"].create(
                {
                    "res_model": document._name,
                    "res_id": document.id,
                    "sequence": sequence,
                    "user_id": user.id,
                    "is_check": is_check,
                    "is_sign": is_sign,
                }
            )
        return document

    def test_send_requires_approvers(self):
        document = self.env["vpk.document.studio.document"].create(
            {"template_id": self.template.id}
        )
        with self.assertRaises(UserError):
            document.action_send_for_signature()

    def test_check_then_sign_approves(self):
        document = self._document()
        document.action_send_for_signature()
        self.assertEqual(document.state, "to_approve")
        self.assertEqual(document.signature_state, "waiting")
        self.assertEqual(len(document.review_ids), 2)
        with self.assertRaises(UserError):
            document.action_generate_pdf()

        as_checker = document.with_user(self.checker)
        self.assertTrue(as_checker.vpk_secretary_can_screen)
        action = as_checker.action_open_sign_viewer()
        self.assertEqual(action["tag"], "vpk_document_sign_pdf_viewer")
        self.assertTrue(action["params"]["secretary_screen"])
        as_checker.action_secretary_mark_checked()
        as_checker.action_secretary_send_director()

        as_director = document.with_user(self.director)
        as_director.invalidate_recordset()
        self.assertTrue(as_director.can_review)
        original = document.pdf_file
        as_director.action_apply_signature(_signature_png())
        document.invalidate_recordset()
        self.assertEqual(document.state, "approved")
        self.assertEqual(document.signature_state, "signed")
        self.assertTrue(document.signed_on)
        self.assertNotEqual(document.pdf_file, original)
        self.assertIn("-signed", document.pdf_filename)

    def test_reject_returns_to_generated(self):
        document = self._document(with_checker=False)
        document.action_send_for_signature()
        document.with_user(self.director).reject_tier()
        document.invalidate_recordset()
        self.assertEqual(document.state, "generated")
        document.action_send_for_signature()
        self.assertEqual(document.state, "to_approve")
        self.assertEqual(
            document.review_ids.mapped("status"), ["pending"]
        )

    def test_review_opens_studio_viewer(self):
        document = self._document(with_checker=False)
        document.action_send_for_signature()
        review = document.review_ids.with_user(self.director)
        action = review.action_open_pdf_viewer()
        self.assertEqual(action["tag"], "vpk_document_sign_pdf_viewer")
        self.assertTrue(action["params"]["can_sign"])

    def test_saraban_number_fills_body_later(self):
        document = self.env["vpk.document.studio.document"].create(
            {"template_id": self.template.id}
        )
        body = document._interpolate_body_html(
            "<p>ที่ {{saraban_no_th}}</p><p>ข้อความเดิม</p>", document._merge_mapping()
        )
        self.assertIn("data-vpk-live-field", body)
        document.body = body.replace("ข้อความเดิม", "ข้อความที่แก้เอง")
        document.saraban_book_no = "12/2569"
        self.assertIn("๑๒/๒๕๖๙", document.body)
        self.assertIn("ข้อความที่แก้เอง", document.body)
        document.saraban_book_no = "34/2569"
        self.assertIn("๓๔/๒๕๖๙", document.body)
        self.assertNotIn("๑๒/๒๕๖๙", document.body)

    def test_saraban_number(self):
        document = self._document()
        document.action_request_saraban_number()
        self.assertTrue(document.saraban_book_no)
        self.assertEqual(document.saraban_document_id.studio_document_id, document)
        mapping = document._merge_mapping()
        self.assertEqual(mapping["saraban_no"], document.saraban_book_no)
        with self.assertRaises(UserError):
            document.action_request_saraban_number()
