# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import io

from docx import Document
from odoo.tests import TransactionCase, tagged

from odoo.addons.vpk_document_studio.models.docx_merge import (
    extract_placeholders,
    merge_docx_bytes,
)


def make_docx(paragraphs, table_cells=None):
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    if table_cells:
        table = document.add_table(rows=1, cols=len(table_cells))
        for index, text in enumerate(table_cells):
            table.rows[0].cells[index].text = text
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def docx_text(content):
    document = Document(io.BytesIO(content))
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


@tagged("post_install", "-at_install")
class TestDocxMerge(TransactionCase):
    def test_merge_fills_paragraphs_and_table(self):
        template = make_docx(
            ["เรื่อง {{subject}}", "{{empty_line}}", "ลงชื่อ {{signer}}"],
            table_cells=["วันที่", "{{doc_date}}"],
        )
        content = merge_docx_bytes(
            template,
            {
                "subject": "ขออนุมัติลา",
                "empty_line": "",
                "signer": "นายทดสอบ",
                "doc_date": "24 ตุลาคม 2569",
            },
            known_codes={"subject", "empty_line", "signer", "doc_date"},
        )
        text = docx_text(content)
        self.assertIn("เรื่อง ขออนุมัติลา", text)
        self.assertIn("ลงชื่อ นายทดสอบ", text)
        self.assertIn("24 ตุลาคม 2569", text)
        self.assertNotIn("{{", text)
        self.assertNotIn("empty_line", text)

    def test_extract_placeholders(self):
        template = make_docx(
            ["{{subject}} และ {{subject}}", "วันที่ {{doc_date}}"],
            table_cells=["{{qty}}"],
        )
        self.assertEqual(
            extract_placeholders(template),
            ["subject", "doc_date", "qty"],
        )

    def test_unknown_placeholder_is_cleared(self):
        template = make_docx(["หัวข้อ {{missing}}", "{{empty_only}}"])
        content = merge_docx_bytes(
            template,
            {"subject": "ทดสอบ"},
            known_codes={"subject"},
        )
        text = docx_text(content)
        self.assertIn("หัวข้อ", text)
        self.assertNotIn("{{", text)
        self.assertNotIn("empty_only", text)
