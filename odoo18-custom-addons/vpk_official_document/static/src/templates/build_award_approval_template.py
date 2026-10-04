#!/usr/bin/env python3
"""Build รายงานผลการพิจารณาจัดซื้อจัดจ้าง Word template for vpk_official_document."""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Twips

FONT = "TH Sarabun New"
OUT = Path(__file__).with_name("award_approval.docx")
GARUDA = (
    Path(__file__).resolve().parents[4]
    / "vpk_purchase_agreement_egp"
    / "static"
    / "src"
    / "img"
    / "garuda.jpeg"
)


def _set_half_point(r_pr, tag, half):
    node = r_pr.find(qn(tag))
    if node is None:
        node = OxmlElement(tag)
        r_pr.append(node)
    node.set(qn("w:val"), str(half))


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
    # LibreOffice sizes Thai from szCs. Word uses sz. Both must match the template.
    half = int(size_pt * 2)
    _set_half_point(r_pr, "w:sz", half)
    _set_half_point(r_pr, "w:szCs", half)


def add_para(
    doc,
    text,
    *,
    size=18,
    bold=False,
    align="left",
    before=0,
    after=0,
    first_line=None,
):
    para = doc.add_paragraph()
    para.alignment = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "thai_justify": WD_ALIGN_PARAGRAPH.THAI_JUSTIFY,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    pf = para.paragraph_format
    pf.space_before = Twips(before)
    pf.space_after = Twips(after)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if first_line is not None:
        pf.first_line_indent = Cm(first_line)
    run = para.add_run(text)
    set_run_font(run, size_pt=size, bold=bold)
    return para


def _set_cell_borders(cell, *, grid=False, underline=False):
    tc_pr = cell._tc.get_or_add_tcPr()
    existing = tc_pr.find(qn("w:tcBorders"))
    if existing is not None:
        tc_pr.remove(existing)
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement("w:%s" % edge)
        if grid or (underline and edge == "bottom"):
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), "8" if grid else "6")
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), "000000")
        else:
            element.set(qn("w:val"), "nil")
        borders.append(element)
    tc_pr.append(borders)


def _set_cell_width(cell, width):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width)))
    tc_w.set(qn("w:type"), "dxa")


def _cell_text(cell, text, *, size=18, bold=False, align="left"):
    paragraph = cell.paragraphs[0]
    paragraph.alignment = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    pf = paragraph.paragraph_format
    pf.space_before = Twips(0)
    pf.space_after = Twips(0)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    lines = str(text).split("\n")
    if paragraph.runs:
        paragraph.runs[0].text = lines[0]
        run = paragraph.runs[0]
        for extra_run in paragraph.runs[1:]:
            extra_run.text = ""
    else:
        run = paragraph.add_run(lines[0])
    set_run_font(run, size_pt=size, bold=bold)
    for line in lines[1:]:
        extra = cell.add_paragraph()
        extra.alignment = paragraph.alignment
        extra.paragraph_format.space_before = Twips(0)
        extra.paragraph_format.space_after = Twips(0)
        extra.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        extra_run = extra.add_run(line)
        set_run_font(extra_run, size_pt=size, bold=bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _set_table_widths(table, widths):
    table.autofit = False
    table.allow_autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement("w:tblPr")
        tbl.insert(0, tbl_pr)
    total = sum(widths)
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        tbl.remove(grid)
    grid = OxmlElement("w:tblGrid")
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    tbl_pr.addnext(grid)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            _set_cell_width(cell, width)


def _set_cell_margins(table, dxa=60):
    tbl_pr = table._tbl.tblPr
    margins = OxmlElement("w:tblCellMar")
    for edge in ("top", "left", "bottom", "right"):
        node = OxmlElement("w:%s" % edge)
        node.set(qn("w:w"), str(dxa if edge in ("left", "right") else 40))
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    tbl_pr.append(margins)


def _set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is None:
        tr_pr.append(OxmlElement("w:tblHeader"))


def _prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    cant = tr_pr.find(qn("w:cantSplit"))
    if cant is None:
        cant = OxmlElement("w:cantSplit")
        tr_pr.append(cant)


def add_header_table(doc):
    table = doc.add_table(rows=3, cols=4)
    widths = [Cm(3.6), Cm(6.4), Cm(1.7), Cm(5.3)]
    dxa = [int(width.twips) for width in widths]
    _set_table_widths(table, dxa)
    table.rows[0].cells[1].merge(table.rows[0].cells[3])
    table.rows[2].cells[1].merge(table.rows[2].cells[3])
    labels = (
        (0, 0, "ส่วนราชการ"),
        (1, 0, "ที่"),
        (1, 2, "วันที่"),
        (2, 0, "เรื่อง"),
    )
    values = (
        (0, 1, "{{agency}}"),
        (1, 1, "{{memo_number}}"),
        (1, 3, "{{memo_date}}"),
        (2, 1, "{{subject}}"),
    )
    for row_idx, col_idx, text in labels:
        cell = table.rows[row_idx].cells[col_idx]
        _cell_text(cell, text, bold=True)
        _set_cell_borders(cell)
        tc_pr = cell._tc.get_or_add_tcPr()
        if tc_pr.find(qn("w:noWrap")) is None:
            tc_pr.append(OxmlElement("w:noWrap"))
    for row_idx, col_idx, text in values:
        cell = table.rows[row_idx].cells[col_idx]
        _cell_text(cell, text)
        _set_cell_borders(cell, underline=True)
    return table


def add_item_table(doc):
    table = doc.add_table(rows=3, cols=4)
    widths = [int(Cm(6.0).twips), int(Cm(4.6).twips), int(Cm(3.2).twips), int(Cm(3.2).twips)]
    _set_table_widths(table, widths)
    _set_cell_margins(table)
    headers = (
        "รายการพิจารณา",
        "รายชื่อผู้ยื่นข้อเสนอ",
        "ราคาที่เสนอ*",
        "ราคาที่ตกลง\nซื้อหรือจ้าง*",
    )
    for index, text in enumerate(headers):
        cell = table.rows[0].cells[index]
        _cell_text(cell, text, size=16, bold=True, align="center")
        _set_cell_borders(cell, grid=True)
    data = ("{{item_desc}}", "{{vendor_name}}", "{{offer_price}}", "{{agreed_price}}")
    aligns = ("left", "left", "right", "right")
    for index, (text, align) in enumerate(zip(data, aligns)):
        cell = table.rows[1].cells[index]
        _cell_text(cell, text, size=16, align=align)
        _set_cell_borders(cell, grid=True)
    table.rows[2].cells[0].merge(table.rows[2].cells[2])
    _cell_text(table.rows[2].cells[0], "รวม", size=16, bold=True, align="right")
    _cell_text(table.rows[2].cells[3], "{{total_amount}}", size=16, bold=True, align="right")
    for index in (0, 3):
        _set_cell_borders(table.rows[2].cells[index], grid=True)
    _set_repeat_header(table.rows[0])
    for row in table.rows:
        _prevent_row_split(row)
    return table


def add_memo_banner(doc):
    """Garuda on the left, บันทึกข้อความ beside it, vertically centered."""
    table = doc.add_table(rows=1, cols=2)
    widths = [int(Cm(3.8).twips), int(Cm(13.2).twips)]
    _set_table_widths(table, widths)
    left, right = table.rows[0].cells
    for cell in (left, right):
        _set_cell_borders(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    emblem = left.paragraphs[0]
    emblem.alignment = WD_ALIGN_PARAGRAPH.CENTER
    emblem.paragraph_format.space_before = Twips(0)
    emblem.paragraph_format.space_after = Twips(0)
    emblem.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    emblem.add_run().add_picture(str(GARUDA), width=Cm(2.7))
    _cell_text(right, "บันทึกข้อความ", size=44, bold=True, align="left")
    right.paragraphs[0].paragraph_format.left_indent = Cm(0.4)
    return table


def add_sign_block(doc, name_key, position_key):
    table = doc.add_table(rows=2, cols=2)
    widths = [int(Cm(8.5).twips), int(Cm(8.5).twips)]
    _set_table_widths(table, widths)
    for row in table.rows:
        for cell in row.cells:
            _set_cell_borders(cell)
    _cell_text(table.rows[0].cells[1], "({{%s}})" % name_key, align="center")
    _cell_text(table.rows[1].cells[1], "{{%s}}" % position_key, align="center")
    _cell_text(table.rows[0].cells[0], "")
    _cell_text(table.rows[1].cells[0], "")
    return table


def main():
    if not GARUDA.is_file():
        raise SystemExit("missing garuda image: %s" % GARUDA)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(18)
    r_pr = style.element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        r_fonts.set(qn(attr), FONT)
    _set_half_point(r_pr, "w:sz", 36)
    _set_half_point(r_pr, "w:szCs", 36)

    add_memo_banner(doc)
    add_header_table(doc)
    add_para(doc, "เรียน  {{recipient}}", before=160, after=80)
    add_para(
        doc,
        "{{intro}}",
        align="thai_justify",
        before=60,
        after=80,
        first_line=1.5,
    )
    add_item_table(doc)
    add_para(
        doc,
        "* ราคาที่เสนอ และราคาที่ตกลงซื้อหรือจ้าง เป็นราคารวมภาษีมูลค่าเพิ่มและภาษีอื่น "
        "ค่าขนส่ง ค่าจดทะเบียน และค่าใช้จ่ายอื่นๆ ทั้งปวง",
        size=16,
        before=40,
        after=80,
    )
    add_para(doc, "{{criteria}}", align="thai_justify", before=80, after=40, first_line=1.5)
    add_para(doc, "{{hospital_opinion}}", align="thai_justify", before=40, after=40, first_line=1.5)
    add_para(doc, "{{request_text}}", align="thai_justify", before=40, after=160, first_line=1.5)
    add_sign_block(doc, "officer_name", "officer_position")
    add_para(doc, "เรียน  {{recipient}}", before=200, after=40)
    add_para(doc, "- เพื่อโปรดพิจารณาเห็นควรอนุมัติ", after=0)
    add_para(doc, "- เป็นอำนาจของ{{approver_authority}}", after=120)
    add_para(doc, "({{head_officer_name}})", before=80)
    add_para(doc, "{{head_officer_position}}", after=200)
    add_sign_block(doc, "signer_name", "signer_position")
    acting = doc.add_table(rows=1, cols=2)
    _set_table_widths(acting, [int(Cm(8.5).twips), int(Cm(8.5).twips)])
    for cell in acting.rows[0].cells:
        _set_cell_borders(cell)
    _cell_text(acting.rows[0].cells[0], "")
    _cell_text(acting.rows[0].cells[1], "{{signer_acting}}", align="center")

    # Keep the page content width available to nested tables.
    doc.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
