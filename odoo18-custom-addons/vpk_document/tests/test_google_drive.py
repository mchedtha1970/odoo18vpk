# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.vpk_document.models.google_drive import (
    DOCS_MIME,
    build_auth_url,
    build_multipart,
    google_error_text,
)


@tagged("post_install", "-at_install")
class TestVpkDocumentGoogle(TransactionCase):
    def test_auth_url_uses_client_and_redirect(self):
        url = build_auth_url("client-123", "http://localhost:8069/vpk_document/google/callback", "state-1")
        self.assertIn("client_id=client-123", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8069%2Fvpk_document%2Fgoogle%2Fcallback", url)
        self.assertIn("drive.file", url)

    def test_upload_converts_to_google_sheet(self):
        body, content_type = build_multipart("budget.xlsx", b"PK-fake", "application/vnd.ms-excel")
        self.assertIn("multipart/related", content_type)
        self.assertIn(b"application/vnd.google-apps.spreadsheet", body)
        self.assertIn(b"budget.xlsx", body)

    def test_upload_converts_word_to_google_doc(self):
        body, content_type = build_multipart(
            "letter.docx",
            b"PK-fake",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DOCS_MIME,
        )
        self.assertIn("multipart/related", content_type)
        self.assertIn(b"application/vnd.google-apps.document", body)
        self.assertIn(b"letter.docx", body)

    def test_google_error_text_omits_raw_payload(self):
        text = google_error_text({
            "error": {
                "message": "The requested conversion is not supported.",
                "errors": [{"reason": "badRequest"}],
            }
        })
        self.assertIn("conversion is not supported", text)
        self.assertIn("badRequest", text)
        self.assertEqual(google_error_text({"error": {"message": "  too   long  "}}), "too long")

    def test_settings_roundtrip_and_excel_only(self):
        wizard = self.env["vpk.document.google.settings"].create({
            "client_id": "client-123",
            "client_secret": "secret-456",
        })
        wizard.action_save()
        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(params.get_param("vpk_document.google_client_id"), "client-123")
        self.assertEqual(params.get_param("vpk_document.google_client_secret"), "secret-456")
        category = self.env["vpk.document.category"].create({"name": "ทดสอบ Google"})
        document = self.env["vpk.document"].create({
            "name": "รูป",
            "category_id": category.id,
            "file_name": "photo.png",
            "file": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        })
        with self.assertRaises(UserError):
            document.action_open_google_sheet()
        word = self.env["vpk.document"].create({
            "name": "จดหมาย",
            "category_id": category.id,
            "file_name": "letter.docx",
            "file": "UEstZmFrZQ==",
        })
        action = word.action_open_google_sheet()
        self.assertEqual(action["url"], "/vpk_document/google/open/%s" % word.id)
        wizard.write({"client_secret": False})
        wizard.action_save()
        self.assertEqual(
            params.get_param("vpk_document.google_client_secret"),
            "secret-456",
        )

    def test_state_is_bound_to_user(self):
        service = self.env["vpk.document.google.service"]
        state = service._make_state(15)
        self.assertEqual(service._read_state(state), 15)
        with self.assertRaises(UserError):
            service._read_state(state + "x")
