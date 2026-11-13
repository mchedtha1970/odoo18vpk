# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64
import io

from odoo import api, models

PAYMENT_VOUCHER_TYPE_CODES = ("payment_voucher", "ใบสำคัญจ่าย")
PAYMENT_VOUCHER_TEMPLATE_CODE = "vpk_payment_voucher"


def _build_payment_voucher_docx_bytes():
    """Official-memo style Word for ใบสำคัญจ่าย (not purchase approval)."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(1.5)

    style = doc.styles["Normal"]
    style.font.name = "TH Sarabun New"
    style.font.size = Pt(16)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "TH Sarabun New")
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    def _style_run(run, bold=False, size=16):
        from docx.oxml import OxmlElement

        run.bold = bold
        run.font.size = Pt(size)
        run.font.name = "TH Sarabun New"
        r_pr = run._element.get_or_add_rPr()
        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            r_pr.insert(0, r_fonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            r_fonts.set(qn(attr), "TH Sarabun New")
        half = str(int(size * 2))
        for tag in ("w:sz", "w:szCs"):
            el = r_pr.find(qn(tag))
            if el is None:
                el = OxmlElement(tag)
                r_pr.append(el)
            el.set(qn("w:val"), half)
        if bold and r_pr.find(qn("w:bCs")) is None:
            r_pr.append(OxmlElement("w:bCs"))

    def add_center(text, bold=False, size=29):
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        _style_run(run, bold=bold, size=size)
        return paragraph

    def add_left(text, bold=False, size=16, first_line_indent=None):
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        if first_line_indent:
            paragraph.paragraph_format.first_line_indent = first_line_indent
        run = paragraph.add_run(text)
        _style_run(run, bold=bold, size=size)
        return paragraph

    add_center("บันทึกข้อความ", bold=True, size=29)
    add_left("ส่วนราชการ  {{agency}}  โทรศัพท์ {{memo_phone}}")
    add_left("ที่  {{memo_ref}}                                          วันที่  {{date}}")
    add_left("เรื่อง  {{memo_subject}}")
    add_left("เรียน  {{memo_to}}")
    add_left("{{intro_text}}", first_line_indent=Cm(1.25))

    table = doc.add_table(rows=2, cols=4)
    table.style = "Table Grid"
    headers = ["ลำดับที่", "บริษัท", "บิลเลขที่", "จำนวนเงิน บาท"]
    for index, label in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = label
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                _style_run(run, bold=True, size=16)

    # Repeatable data row for Document Studio merge
    row = table.rows[1].cells
    row[0].text = "{{items.no}}"
    row[1].text = "{{items.partner_name}}"
    row[2].text = "{{items.bill_ref}}"
    row[3].text = "{{items.amount}}"
    for cell in row:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                _style_run(run, bold=False, size=16)
    row[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    row[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    row[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

    add_left("รวมเป็นเงิน  {{amount_total}}  บาท")
    add_left("({{amount_total_text}})")
    add_left("{{purpose_text}}", first_line_indent=Cm(1.25))
    add_left("จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ", first_line_indent=Cm(1.25))
    add_left("{{approval_text}}")
    add_left("")
    add_left("({{proposer_name}})")
    add_left("{{proposer_position}}")
    add_left("")
    add_left("({{approver_name}})")
    add_left("{{approver_position}}")

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    @api.model
    def _vpk_install_payment_voucher_template(self):
        """Ensure ใบสำคัญจ่าย template uses payment-voucher Word (not purchase memo)."""
        Type = self.env["vpk.document.studio.document.type"].sudo().with_context(
            active_test=False
        )
        Template = self.sudo().with_context(active_test=False)
        Field = self.env["vpk.document.studio.field"].sudo()
        IrModel = self.env["ir.model"].sudo()
        IrField = self.env["ir.model.fields"].sudo()

        doc_type = Type.search(
            [
                ("code", "in", list(PAYMENT_VOUCHER_TYPE_CODES)),
                ("company_id", "in", [False, self.env.company.id]),
            ],
            order="id asc",
            limit=1,
        )
        if not doc_type:
            doc_type = Type.create(
                {
                    "code": "payment_voucher",
                    "name": "ใบสำคัญจ่าย",
                    "sequence": 240,
                    "company_id": False,
                }
            )
        elif doc_type.code == "ใบสำคัญจ่าย":
            # keep Thai code used in existing DB; also ensure English alias type exists
            if not Type.search([("code", "=", "payment_voucher")], limit=1):
                Type.create(
                    {
                        "code": "payment_voucher",
                        "name": "ใบสำคัญจ่าย",
                        "sequence": 241,
                        "company_id": False,
                    }
                )

        source_model = IrModel._get("vpk.payment.voucher")
        template = Template.search(
            [
                ("source_model_id", "=", source_model.id),
                "|",
                ("code", "=", PAYMENT_VOUCHER_TEMPLATE_CODE),
                ("document_type_id", "=", doc_type.id),
            ],
            order="id desc",
            limit=1,
        )
        if not template:
            template = Template.search(
                [
                    ("name", "=", "ใบสำคัญจ่าย"),
                    ("source_model_id", "=", source_model.id),
                ],
                limit=1,
            )
        vals = {
            "name": "ใบสำคัญจ่าย",
            "code": PAYMENT_VOUCHER_TEMPLATE_CODE,
            "document_type_id": doc_type.id,
            "source_model_id": source_model.id,
            "filename": "ใบสำคัญจ่าย.docx",
            "active": True,
        }
        if template:
            template.write(vals)
        else:
            vals["datas"] = base64.b64encode(_build_payment_voucher_docx_bytes())
            template = Template.create(vals)

        # Ensure mapped fields for voucher print
        voucher_model = source_model
        def _field(name):
            return IrField.search(
                [("model_id", "=", voucher_model.id), ("name", "=", name)], limit=1
            )

        # (code, label, type, map_field, map_sub_field[, number_format])
        field_specs = [
            ("agency", "ส่วนราชการ", "char", "memo_agency", None),
            ("memo_phone", "โทรศัพท์", "char", "memo_phone", None),
            ("memo_ref", "ที่", "char", "name", None),
            ("date", "วันที่", "date", "date", None),
            ("memo_subject", "เรื่อง", "char", "memo_subject", None),
            ("memo_to", "เรียน", "char", "memo_to", None),
            ("intro_text", "ข้อความนำ", "text", "intro_text", None),
            ("journal_id", "แหล่งเงิน", "char", "fund_name", None),
            ("bank_display", "บัญชีธนาคาร", "char", "bank_display", None),
            ("attachment_count", "จำนวนฉบับแนบ", "integer", "attachment_count", None),
            ("items", "รายการ", "many2one", "line_ids", "partner_name"),
            ("amount_total", "รวมเป็นเงิน", "float", "amount_total", None, "comma"),
            ("amount_total_text", "จำนวนเงินตัวอักษร", "char", "amount_total_text", None),
            ("purpose_text", "ข้อความสรุป", "text", "purpose_text", None),
            ("approval_text", "ข้อความอนุมัติ", "char", "approval_text", None),
            ("proposer_name", "ผู้เสนอ", "char", "proposer_name", None),
            ("proposer_position", "ตำแหน่งผู้เสนอ", "char", "proposer_position", None),
            ("approver_name", "ผู้อนุมัติ", "char", "approver_name", None),
            ("approver_position", "ตำแหน่งผู้อนุมัติ", "char", "approver_position", None),
        ]
        sequence = 10
        for spec in field_specs:
            code, name, field_type, map_name, sub_name = spec[:5]
            number_format = spec[5] if len(spec) > 5 else False
            field = template.field_ids.filtered(lambda rec, c=code: rec.code == c)[:1]
            map_field = _field(map_name)
            sub_field = False
            if sub_name and map_field and map_field.relation:
                sub_field = IrField.search(
                    [("model", "=", map_field.relation), ("name", "=", sub_name)],
                    limit=1,
                )
            field_vals = {
                "template_id": template.id,
                "code": code,
                "name": name,
                "field_type": field_type,
                "sequence": sequence,
                "map_model_id": voucher_model.id,
                "map_field_id": map_field.id if map_field else False,
                "map_sub_field_id": sub_field.id if sub_field else False,
            }
            if number_format:
                field_vals["number_format"] = number_format
            if field:
                field.write(field_vals)
            else:
                Field.create(field_vals)
            sequence += 10

        # Drop leftover / duplicate fields that are not used by the voucher memo
        keep = {spec[0] for spec in field_specs}
        stale = template.field_ids.filtered(lambda rec: rec.code not in keep)
        if stale:
            stale.unlink()

        # Keep user-uploaded Word (Garuda / layout). Only seed when empty.
        if not template.datas:
            template.write(
                {
                    "datas": base64.b64encode(_build_payment_voucher_docx_bytes()),
                    "filename": "ใบสำคัญจ่าย.docx",
                }
            )
        return True
