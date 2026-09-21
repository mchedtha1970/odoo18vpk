#!/usr/bin/env python3
"""Build the ประกาศผู้ชนะ Word template with {{placeholders}}."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Twips

FONT = "TH Sarabun New"
OUT = Path(__file__).with_name("winner_announcement.docx")


def set_run_font(run, size_pt=16, bold=False):
    run.font.name = FONT
    run.font.size = Pt(size_pt)
    run.bold = bold
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        r_fonts.set(qn(attr), FONT)


def add_para(doc, text, *, size=16, bold=False, align="left", before=0, after=60, first_line=None, left=None):
    para = doc.add_paragraph()
    para.alignment = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
    }[align]
    pf = para.paragraph_format
    pf.space_before = Twips(before)
    pf.space_after = Twips(after)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if first_line is not None:
        pf.first_line_indent = Cm(first_line)
    if left is not None:
        pf.left_indent = Cm(left)
    run = para.add_run(text)
    set_run_font(run, size_pt=size, bold=bold)
    return para


def main():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(16)
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        r_fonts.set(qn(attr), FONT)

    add_para(doc, "( สำเนา )", size=22, bold=True, align="center", after=280)
    add_para(doc, "ประกาศ{{province}}", size=18, bold=True, align="center", after=80)
    add_para(doc, "เรื่อง {{subject}}", size=16, bold=True, align="center", after=40)
    add_para(doc, "————————————————", size=14, align="center", before=40, after=280)
    add_para(
        doc,
        "{{body}}",
        size=16,
        align="justify",
        before=80,
        after=400,
        first_line=1.2,
    )
    add_para(
        doc,
        "ประกาศ ณ วันที่ {{announce_date}}",
        size=16,
        align="center",
        before=200,
        after=280,
    )
    add_para(doc, "{{signer_name}}", size=16, align="center", after=40, left=1.8)
    add_para(doc, "({{signer_full}})", size=16, align="center", after=40, left=1.8)
    add_para(doc, "{{signer_title}}", size=16, align="center", after=40, left=1.8)
    add_para(doc, "{{signer_acting}}", size=16, align="center", after=40, left=1.8)
    add_para(doc, "สำเนาถูกต้อง", size=16, before=720, after=240)
    add_para(doc, "{{cert_name}}", size=16, after=40)
    add_para(doc, "({{cert_full}})", size=16, after=40)
    add_para(doc, "{{cert_title}}", size=16, after=240)
    add_para(doc, "ประกาศขึ้นเว็บวันที่ {{web_date}}", size=16, after=40)
    add_para(doc, "โดย {{web_by}}", size=16, after=0)

    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
