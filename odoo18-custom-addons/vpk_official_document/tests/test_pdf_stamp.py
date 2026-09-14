# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import io

from odoo.tests import TransactionCase, tagged

from odoo.addons.vpk_official_document.models.pdf_stamp import (
    SignatureStampError,
    stamp_signature_on_pdf,
)


def _pdf_with_names(names_by_page, y=180):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for index, name in enumerate(names_by_page):
        if index:
            pdf.showPage()
        pdf.setFont("Helvetica", 12)
        pdf.drawString(300, y, "(%s)" % name)
    pdf.save()
    return buffer.getvalue()


def _red_signature_png():
    from PIL import Image

    image = Image.new("RGBA", (240, 80), (0, 0, 0, 0))
    for x in range(20, 220):
        for y in range(20, 60):
            image.putpixel((x, y), (200, 0, 0, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestPdfStamp(TransactionCase):
    def test_stamp_above_last_matching_name(self):
        pdf_bytes = _pdf_with_names(["Other Person", "John Approver"])
        stamped = stamp_signature_on_pdf(
            pdf_bytes,
            _red_signature_png(),
            ["(John Approver)", "John Approver"],
        )
        self.assertTrue(stamped.startswith(b"%PDF"))

        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(stamped)
        self.assertEqual(len(pdf), 2)
        last_page = pdf[1]
        bitmap = last_page.render(scale=2)
        image = bitmap.to_pil()
        width, height = image.size
        # Name is at PDF y=180; signature sits just above it.
        sample_x = int(360 * 2)
        sample_y = height - int(210 * 2)
        pixel = image.getpixel((sample_x, sample_y))
        pdf.close()
        self.assertGreater(pixel[0], 120)
        self.assertLess(pixel[1], 80)

    def test_stamp_missing_name_raises(self):
        pdf_bytes = _pdf_with_names(["Someone Else"])
        with self.assertRaises(SignatureStampError):
            stamp_signature_on_pdf(
                pdf_bytes,
                _red_signature_png(),
                ["John Approver"],
            )

    def test_apply_signature_to_generated_pdf(self):
        template = self.env["vpk.official.document.template"].search(
            [("code", "=", "wa_committee_order")],
            limit=1,
        )
        if not template:
            self.skipTest("Default Word template is not loaded")
        document = self.env["vpk.official.document"].create(
            {
                "document_type": "wa_committee_order",
                "template_id": template.id,
                "agency": "โรงพยาบาลวชิระภูเก็ต",
                "item_summary": "วัสดุสำนักงาน",
                "procurement_method": "วิธีเฉพาะเจาะจง",
                "signer_name": "John Approver",
                "line_ids": [
                    (0, 0, {"name": "นายทดสอบ ประธาน", "role": "chairman"}),
                    (0, 0, {"name": "นางทดสอบ กรรมการ", "role": "committee"}),
                ],
            }
        )
        if not document._soffice_path():
            self.skipTest("LibreOffice is required to generate PDF")
        document.action_generate_pdf()
        document.write({"state": "to_approve"})
        signature = base64.b64encode(_red_signature_png()).decode()
        document._apply_signature_to_pdf(signature)
        self.assertTrue(document.approver_signature)
        self.assertTrue(document.signed_on)
        self.assertIn("-signed.pdf", document.pdf_filename or "")
        pdf_content = base64.b64decode(document.pdf_file)
        self.assertTrue(pdf_content.startswith(b"%PDF"))
        self.assertGreater(len(pdf_content), 1000)
