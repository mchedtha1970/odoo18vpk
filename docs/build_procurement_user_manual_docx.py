#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Thai Word user manual for VPK procurement: PR → e-GP → PO."""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "คู่มือการใช้งาน-ระบบจัดซื้อจัดจ้าง.docx"
FIG = ROOT / "manual_assets" / "figures"

NAVY = RGBColor(0x0B, 0x68, 0x48)
TEAL = RGBColor(0x0B, 0x68, 0x48)
SLATE = RGBColor(0x2A, 0x33, 0x3A)
MUTED = RGBColor(0x7D, 0x8A, 0x9E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xC6, 0x28, 0x28)
AMBER = RGBColor(0xC4, 0x7E, 0x14)
HEADER_FILL = "0B6848"
META_FILL = "EAF3F1"
LOGO = FIG / "moph_logo.png"


def set_run(run, size=12, bold=False, color=SLATE, font_name="Prompt"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), font_name)


def add_text(p, text, size=12, bold=False, color=SLATE):
    run = p.add_run(text)
    set_run(run, size, bold, color)
    return run


def shade_cell(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_border(cell, color="D7DEE6"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def cell_text(cell, text, size=11, bold=False, color=SLATE, align="left", fill=None):
    if fill:
        shade_cell(cell, fill)
    set_cell_border(cell)
    p = cell.paragraphs[0]
    p.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    p.clear()
    add_text(p, text, size, bold, color)
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_before = Pt(2)
        paragraph.paragraph_format.space_after = Pt(2)


def set_narrow_cell_margin(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), "80")
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def make_table(doc, headers, rows, col_widths=None, header_fill=HEADER_FILL):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, h in enumerate(headers):
        cell_text(table.rows[0].cells[i], h, 11, True, WHITE, "center", header_fill)
        set_narrow_cell_margin(table.rows[0].cells[i])
    for r, row in enumerate(rows, 1):
        fill = "F6F8FA" if r % 2 == 0 else "FFFFFF"
        for c, val in enumerate(row):
            cell_text(table.rows[r].cells[c], val, 11, False, SLATE, "left", fill)
            set_narrow_cell_margin(table.rows[r].cells[c])
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table


def add_border_line(paragraph, edge="bottom", color="0B6848", size="12"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), size)
    el.set(qn("w:space"), "6")
    el.set(qn("w:color"), color)
    pBdr.append(el)
    pPr.append(pBdr)


def add_bottom_line(paragraph, color="0B6848", size="12"):
    add_border_line(paragraph, "bottom", color, size)


def page_title(doc, text, center=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(14)
    add_text(p, text, 18, True, TEAL)
    return p


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run(run, 18 if level == 1 else 14 if level == 2 else 13, True, TEAL)
    p.paragraph_format.space_before = Pt(16 if level == 1 else 12)
    p.paragraph_format.space_after = Pt(8)
    if level == 1:
        add_bottom_line(p)
    return p


def body(doc, text, size=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.15
    add_text(p, text, size)
    return p


def bullets(doc, items, numbered=False):
    for item in items:
        p = doc.add_paragraph(style="List Number" if numbered else "List Bullet")
        p.clear()
        add_text(p, item, 12)
        p.paragraph_format.space_after = Pt(3)


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)
    label = text if text.startswith("▲") else f"▲ {text}"
    add_text(p, label, 10, False, MUTED)


def picture(doc, name, width_cm=16.2, cap=""):
    path = FIG / name
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    if cap:
        caption(doc, cap)


def callout(doc, title, text, tone="info"):
    fill = {"info": "E5F5F3", "warn": "FDF3E0", "danger": "FBECEA", "ok": "E5F5EA"}[tone]
    title_color = {
        "info": TEAL,
        "warn": AMBER,
        "danger": RED,
        "ok": RGBColor(0x2C, 0x7A, 0x45),
    }[tone]
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    shade_cell(cell, fill)
    set_cell_border(cell, "D7DEE6")
    p1 = cell.paragraphs[0]
    add_text(p1, title, 12, True, title_color)
    p2 = cell.add_paragraph()
    add_text(p2, text, 12, False, SLATE)
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_after = Pt(4)
    doc.add_paragraph()


def steps(doc, items, start=1):
    for i, item in enumerate(items, start):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        add_text(p, f"ขั้นที่ {i}  ", 12, True, TEAL)
        add_text(p, item, 12, False, SLATE)


def header_footer(doc):
    section = doc.sections[0]
    section.header_distance = Cm(0.8)
    section.footer_distance = Cm(1.0)
    header = section.header
    header.is_linked_to_previous = False
    header.paragraphs[0].text = ""
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_border_line(fp, "top", "C5CDD6", "6")
    add_text(fp, "ระบบจัดซื้อจัดจ้าง · ระบบ ERP รพ.วชิระภูเก็ต | หน้า ", 9, False, MUTED)
    run = fp.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)
    set_run(run, 9, False, MUTED)


def setup_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Prompt"
    normal.font.size = Pt(12)
    normal.font.color.rgb = SLATE
    rPr = normal.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), "Prompt")
    pf = normal.paragraph_format
    pf.space_after = Pt(8)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.15


def build():
    doc = Document()
    setup_styles(doc)
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.2)
    header_footer(doc)

    logo_p = doc.add_paragraph()
    logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo_p.paragraph_format.space_before = Pt(12)
    logo_p.paragraph_format.space_after = Pt(8)
    logo_p.add_run().add_picture(str(LOGO), width=Cm(3.4))

    hosp = doc.add_paragraph()
    hosp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hosp.paragraph_format.space_after = Pt(0)
    add_text(hosp, "โรงพยาบาลวชิระภูเก็ต", 16, True, SLATE)
    hosp_en = doc.add_paragraph()
    hosp_en.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hosp_en.paragraph_format.space_after = Pt(18)
    add_text(hosp_en, "VACHIRAPHUKET HOSPITAL", 11, True, MUTED)

    dtype = doc.add_paragraph()
    dtype.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dtype.paragraph_format.space_after = Pt(6)
    add_text(dtype, "เอกสารคู่มือการใช้งาน (User Manual)", 13, False, MUTED)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)
    add_text(title, "ระบบจัดซื้อจัดจ้าง", 28, True, TEAL)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(10)
    add_text(sub, "ใบขอซื้อ  →  กระบวนการ e-GP  →  ใบสั่งซื้อ", 14, True, SLATE)

    sub2 = doc.add_paragraph()
    sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub2.paragraph_format.space_after = Pt(22)
    add_text(sub2, "ระบบบริหารทรัพยากรองค์กร (ERP)", 13, False, MUTED)

    info = [
        ("รหัสเอกสาร", "UM-ERP-PROC-001"),
        ("ชื่อระบบ", "จัดซื้อจัดจ้าง · ใบขอซื้อ · กระบวนการ e-GP · ใบสั่งซื้อ"),
        ("เวอร์ชันเอกสาร", "1.0"),
        ("วันที่จัดทำ", "10 กันยายน พ.ศ. 2569"),
        ("สถานะเอกสาร", "ฉบับส่งมอบ (Released)"),
        ("กลุ่มผู้อ่าน", "เจ้าหน้าที่หน่วยงาน พัสดุ และผู้เกี่ยวข้อง"),
        ("จัดทำโดย", "ทีมพัฒนาระบบ ERP"),
        ("จัดทำเพื่อ", "โรงพยาบาลวชิระภูเก็ต"),
    ]
    table = doc.add_table(rows=len(info), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(info):
        cell_text(table.rows[i].cells[0], k, 11, True, TEAL, "left", META_FILL)
        cell_text(table.rows[i].cells[1], v, 11, False, SLATE, "left", "FFFFFF")
        table.rows[i].cells[0].width = Cm(4.8)
        table.rows[i].cells[1].width = Cm(11.4)
        set_narrow_cell_margin(table.rows[i].cells[0])
        set_narrow_cell_margin(table.rows[i].cells[1])

    doc.add_page_break()

    page_title(doc, "ประวัติการแก้ไขเอกสาร (Document Revision History)", center=True)
    make_table(
        doc,
        ["เวอร์ชัน", "วันที่", "รายละเอียดการแก้ไข", "ผู้จัดทำ"],
        [
            [
                "1.0",
                "30 ส.ค. 2569",
                "จัดทำเอกสารคู่มือฉบับแรก ครอบคลุมเปิดใบขอซื้อ ส่งเข้ากระบวนการ e-GP และเปิด PO ผู้ชนะ",
                "ทีมพัฒนาระบบ ERP",
            ],
            [
                "1.1",
                "26 ก.ย. 2569",
                "เพิ่มการส่งใบสั่งซื้อเข้าแอปผู้ขาย และภาพประกอบขั้นตอน 7.4",
                "ทีมพัฒนาระบบ ERP",
            ],
        ],
        [2.4, 3.0, 7.4, 3.4],
    )
    note = doc.add_paragraph()
    note.paragraph_format.space_before = Pt(8)
    add_text(
        note,
        "เอกสารฉบับนี้จัดทำขึ้นเพื่อเป็นคู่มือการใช้งานระบบจัดซื้อจัดจ้าง สำหรับเจ้าหน้าที่ของโรงพยาบาลวชิระภูเก็ต "
        "โปรดอ่านและปฏิบัติตามขั้นตอนที่ระบุไว้ หากพบปัญหาการใช้งานให้ติดต่อผู้ดูแลระบบ",
        12,
        False,
        MUTED,
    )

    doc.add_page_break()

    page_title(doc, "สารบัญ")
    toc_items = [
        "บทที่ 1 เข้าสู่ระบบและบัญชีฝึกอบรม",
        "บทที่ 2 ภาพรวมวงจรจัดซื้อจัดจ้าง",
        "บทที่ 3 บทบาทผู้ใช้และแผนที่เมนู",
        "บทที่ 4 หน่วยงาน — เปิดใบขอซื้อ และบันทึกแต่ละแท็บ",
        "บทที่ 5 พัสดุ — นำใบขอซื้อเข้ากระบวนการ e-GP",
        "บทที่ 6 ดำเนินการ e-GP จนได้ผู้ชนะ",
        "บทที่ 7 เปิดใบสั่งซื้อ (PO) เมื่อได้ผู้ชนะ",
        "บทที่ 8 ข้อผิดพลาดที่พบบ่อย",
        "บทที่ 9 แบบฝึกหัดในห้องอบรม",
        "ภาคผนวก ก คำศัพท์ในระบบ",
        "ภาคผนวก ข ช่องทางสอบถาม",
    ]
    for item in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.space_before = Pt(2)
        add_text(p, item, 13, False, SLATE)

    doc.add_page_break()

    heading(doc, "บทที่ 1 เข้าสู่ระบบและบัญชีฝึกอบรม", 1)
    body(
        doc,
        "ก่อนเริ่มใช้งาน ให้เปิดเบราว์เซอร์แล้วเข้าสู่ระบบ ERP ตามลิงก์ที่แจ้ง "
        "โดยให้ใช้ บัญชีตามบทบาทของตนเอง",
    )
    picture(
        doc,
        "Screenshot_login.png",
        16.2,
        "ภาพที่ 1  หน้าจอเข้าสู่ระบบ",
    )
    picture(doc, "fig_proc_cover.png", 16.2, "ภาพที่ 2  ภาพรวมคู่มือระบบจัดซื้อจัดจ้าง")
    make_table(
        doc,
        ["บทบาท", "บัญชี", "รหัสผ่าน", "ใช้ทำอะไร"],
        [
            ["หน่วยงาน", "uat.dept", "VpkUat@2569", "สร้างใบขอซื้อ เช็คงบ ส่งพัสดุ"],
            ["พัสดุ / จัดซื้อ", "uat.procurement", "VpkUat@2569", "รับใบจากหน่วยงาน ส่งเข้า e-GP คัดเลือกผู้ชนะ เปิด PO"],
            ["เจ้าหน้าที่", "uat.officer", "VpkUat@2569", "ลงนามแบบแสดงความบริสุทธิ์ใจและรายงานขออนุมัติเป็นลำดับแรก"],
            ["หัวหน้าเจ้าหน้าที่", "uat.head_officer", "VpkUat@2569", "ลงนามแบบแสดงความบริสุทธิ์ใจและรายงานขออนุมัติเป็นลำดับที่สอง"],
            ["ผู้อำนวยการโรงพยาบาล", "uat.director", "VpkUat@2569", "ลงนามคำสั่งแต่งตั้ง และลงนามรายงานขออนุมัติเป็นลำดับสุดท้าย"],
            ["งานงบประมาณ", "uat.budget", "VpkUat@2569", "ดูวงเงินจองและคงเหลือ"],
            ["ประธานกรรมการตรวจรับ", "uat.committee1", "VpkUat@2569", "ถูกเลือกเป็นประธาน ลงนามแบบแสดงความบริสุทธิ์ใจตามลำดับ และลงนามใบตรวจรับ"],
            ["กรรมการตรวจรับ", "uat.committee2", "VpkUat@2569", "ถูกเลือกเป็นกรรมการ ลงนามแบบแสดงความบริสุทธิ์ใจตามลำดับ และลงนามใบตรวจรับ"],
            ["กรรมการและเลขานุการ", "uat.committee3", "VpkUat@2569", "ถูกเลือกเป็นเลขา ลงนามแบบแสดงความบริสุทธิ์ใจตามลำดับ และลงนามใบตรวจรับ"],
        ],
        [3.5, 3.4, 3.4, 6.0],
    )
    steps(
        doc,
        [
            "เปิดเบราว์เซอร์ แล้วไปที่ระบบ Odoo ของโรงพยาบาล",
            "ใส่บัญชีตามบทบาท จากนั้นเข้าแอป จัดซื้อ",
            "ตรวจว่าเมนูที่เห็นตรงกับสิทธิ์ของตน หน่วยงานจะไม่สร้างใบสั่งซื้อเอง",
            "ถ้าเข้าไม่ได้ ให้แจ้งผู้ประสานทันที อย่าใช้บัญชีของผู้อื่น",
        ],
    )
    callout(
        doc,
        "ข้อควรจำตอนเข้าสู่ระบบ",
        "รหัสผ่านชุดฝึกอบรมเป็นชุดเดียวกันทั้งบัญชีหน่วยงาน พัสดุ เจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ งานงบ และกรรมการตรวจรับทั้ง 3 คน "
        "หลังอบรมจริงควรเปลี่ยนรหัสผ่านตามนโยบายความปลอดภัยของโรงพยาบาล",
        "warn",
    )

    heading(doc, "บทที่ 2 ภาพรวมวงจรจัดซื้อจัดจ้าง", 1)
    body(
        doc,
        "คู่มือนี้ครอบคลุมเฉพาะเส้นทางจัดซื้อผ่าน e-GP ซึ่งเป็นเส้นทางหลักเมื่อหน่วยงานขอซื้อ "
        "แล้วพัสดุต้องประกาศ/เชิญเสนอราคา คัดเลือกผู้ชนะ แล้วจึงออกใบสั่งซื้อ "
        "ห้ามสลับลำดับ และห้ามเปิด PO ตรงจากใบขอซื้อประเภทนี้",
    )
    picture(doc, "fig_proc_flow.png", 16.2, "ภาพที่ 3  วงจรงานจากใบขอซื้อถึงใบสั่งซื้อ")
    heading(doc, "2.1 สามขั้นตอนที่ผู้ใช้ต้องจำ", 2)
    make_table(
        doc,
        ["ขั้น", "เอกสารในระบบ", "ผู้ทำ", "ผลที่เกิด"],
        [
            ["1", "ใบขอซื้อ (PR)", "หน่วยงาน", "ระบุของที่ต้องการ เช็คงบ ส่งพัสดุ"],
            ["2", "กระบวนการ e-GP", "พัสดุ / จัดซื้อ", "เชิญเสนอราคา เปรียบเทียบ เลือกผู้ชนะ"],
            ["3", "ใบสั่งซื้อ (PO)", "พัสดุ / จัดซื้อ", "ออกคำสั่งซื้อให้ผู้ชนะแล้วยืนยัน"],
        ],
        [1.6, 4.4, 3.6, 6.6],
    )
    heading(doc, "2.2 เงื่อนไขสำคัญ", 2)
    bullets(
        doc,
        [
            "เลือกประเภทการจัดซื้อเป็น จัดซื้อจัดจ้างผ่านพัสดุ จึงจะส่งเข้ากระบวนการ e-GP ได้",
            "ส่งเข้า e-GP ได้เมื่อใบขอซื้ออนุมัติแล้ว และเอกสารที่เกี่ยวข้องอนุมัติครบทุกฉบับ",
            "เปิด PO ได้เมื่อมีผู้ชนะ และรายงานผลการพิจารณาได้รับอนุมัติแล้ว",
        ],
    )
    callout(
        doc,
        "เส้นทางอื่นที่ไม่ใช่ e-GP",
        "ประเภทการจัดซื้อแบบวงเงินเล็กน้อย 79 วรรคสอง หรือ ว.119 ไม่ได้เดินตามคู่มือนี้ "
        "ใช้เมื่อเป็นค่าใช้จ่ายวงเงินเล็กน้อยตามระเบียบ อย่าสับสนกับเส้นทาง e-GP",
        "info",
    )

    heading(doc, "บทที่ 3 บทบาทผู้ใช้และเมนูที่ใช้บ่อย", 1)
    picture(doc, "fig_proc_roles.png", 16.2, "ภาพที่ 4  บทบาทในวงจรจัดซื้อจัดจ้าง")
    picture(doc, "fig_proc_menus.png", 16.2, "ภาพที่ 5  แผนที่เมนูที่ใช้บ่อย")
    heading(doc, "3.1 เมนูที่แต่ละบทบาทใช้", 2)
    make_table(
        doc,
        ["บทบาท", "เมนูหลัก", "หมายเหตุ"],
        [
            ["หน่วยงาน", "จัดซื้อ → ใบขอซื้อ", "สร้างใบขอซื้อ เช็คงบ ใส่แท็บรายชื่อคณะกรรมการ แล้วกดส่งพัสดุ"],
            ["พัสดุ", "จัดซื้อ → ใบขอซื้อ → รอรับจากหน่วยงาน", "เปิดใบที่หน่วยงานส่งแล้ว ออกเอกสารแต่งตั้งและอนุมัติขอซื้อ แล้วส่งอนุมัติ"],
            ["พัสดุ", "จัดซื้อ → ใบขอซื้อ", "เปิดใบที่อนุมัติแล้ว กดส่งรายการเข้าระบบ e-GP"],
            ["พัสดุ", "จัดซื้อ → กระบวนการ eGP", "ทำเอกสาร เชิญเสนอราคา เลือกผู้ชนะ"],
            ["พัสดุ", "จัดซื้อ → ใบสั่งซื้อ", "เปิดและยืนยัน PO ของผู้ชนะ"],
            ["เจ้าหน้าที่", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามแบบแสดงความบริสุทธิ์ใจและรายงานขออนุมัติเป็นลำดับแรก"],
            ["หัวหน้าเจ้าหน้าที่", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามสองเอกสารชุดนี้เมื่อเจ้าหน้าที่ลงนามแล้ว"],
            ["ผู้อำนวยการโรงพยาบาล", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามคำสั่งแต่งตั้ง และลงนามรายงานขออนุมัติเมื่อเจ้าหน้าที่กับหัวหน้าลงนามครบ"],
            ["งานงบ", "งบประมาณ / รายการงบ", "ดูวงเงินจองหลังส่ง PR"],
            ["กรรมการตรวจรับ", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามแบบแสดงความบริสุทธิ์ใจตามลำดับในเอกสาร แล้วลงนามใบตรวจรับที่เมนูใบตรวจรับงาน"],
        ],
        [3.2, 6.0, 7.0],
    )

    heading(doc, "บทที่ 4 หน่วยงาน — เปิดใบขอซื้อ และบันทึกแต่ละแท็บ", 1)
    body(
        doc,
        "บทนี้ใช้บัญชีหน่วยงาน เข้าเมนู จัดซื้อ → ใบขอซื้อ แล้วกดสร้าง "
        "เมื่อบันทึก ระบบจะออกเลขที่อัตโนมัติรูปแบบ PR + ปี พ.ศ. 2 หลัก + เดือน + เลขวิ่ง 3 หลัก "
        "เช่น PR6908001 ช่องเลขที่แก้เองไม่ได้",
    )
    heading(doc, "4.1 กรอกหัวเอกสาร", 2)
    steps(
        doc,
        [
            "เข้าเมนู ใบขอซื้อ แล้วกดสร้าง",
        ],
    )
    picture(
        doc,
        "Screenshot_menu_PR.png",
        16.2,
        "ภาพที่ 6  เมนูใบขอซื้อ",
    )
    picture(
        doc,
        "Screenshot_New_PR.png",
        16.2,
        "ภาพที่ 7  หน้าจอสร้างใบขอซื้อใหม่ (ร่าง)",
    )
    steps(
        doc,
        [
            "เลือกประเภทพัสดุ เช่น ซื้อ/จ้าง/เช่า (หรือจ้างที่ปรึกษา / จ้างออกแบบและควบคุมงานก่อสร้าง ตามงานจริง)",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_PR_procurement_type.png",
        16.2,
        "ภาพที่ 8  เลือกประเภทพัสดุ",
    )
    steps(
        doc,
        [
            "เลือกประเภทการจัดซื้อเป็น จัดซื้อจัดจ้างผ่านพัสดุ เพื่อให้ใบนี้เข้ากระบวนการ e-GP",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_PR_purchase_type.png",
        16.2,
        "ภาพที่ 9  เลือกประเภทการจัดซื้อ",
    )
    steps(
        doc,
        [
            "เลือกวิธีการจัดซื้อจัดจ้าง เช่น เฉพาะเจาะจง, E-bidding, คัดเลือก, หรือประกาศเชิญชวนทั่วไป",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_PR_procurement_method.png",
        16.2,
        "ภาพที่ 10  เลือกวิธีการจัดซื้อจัดจ้าง",
    )
    steps(
        doc,
        [
            "เลือกประเภทสิ่งที่จะซื้อ หน่วยงานงบประมาณ แหล่งเงิน และหมวดงบประมาณ ให้ตรงงบที่อนุมัติ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_PR_budget_keys.png",
        16.2,
        "ภาพที่ 11  ประเภทสิ่งที่จะซื้อ หน่วยงานงบประมาณ แหล่งเงิน และหมวดงบประมาณ",
    )
    steps(
        doc,
        [
            "ถ้าซื้อวัสดุ ต้องเลือกกลุ่มงบประมาณด้วย",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_PR_budget_group.png",
        16.2,
        "ภาพที่ 12  เลือกกลุ่มงบประมาณ",
    )
    steps(
        doc,
        [
            "เลือกประเภทการรับสินค้าเฉพาะ Receipts ของคลังที่ต้องการให้ของเข้า",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_PR_picking_type.png",
        16.2,
        "ภาพที่ 13  เลือกประเภทการรับสินค้า",
    )
    steps(
        doc,
        [
            "ใส่คำขอจัดซื้อในช่องรายละเอียด จากนั้นบันทึกข้อมูลในแต่ละแท็บตามหัวข้อถัดไป",
        ],
        start=8,
    )
    heading(doc, "4.2 ช่องหัวเอกสารที่ต้องใส่ให้ถูก", 2)
    make_table(
        doc,
        ["ช่องในระบบ", "ตัวอย่าง", "ทำไมต้องถูก"],
        [
            ["ประเภทพัสดุ", "ซื้อ/จ้าง/เช่า", "กำหนดลักษณะงานจัดซื้อ"],
            ["ประเภทการจัดซื้อ", "จัดซื้อจัดจ้างผ่านพัสดุ", "เปิดเส้นทาง e-GP"],
            ["วิธีการจัดซื้อจัดจ้าง", "E-bidding / เฉพาะเจาะจง", "ต้องตรงวิธีที่หน่วยงานใช้จริง"],
            ["ประเภทสิ่งที่จะซื้อ", "วัสดุ / ครุภัณฑ์ / โครงการ / ก่อสร้าง", "ใช้จับคู่กับหมวดงบ"],
            ["หน่วยงานงบประมาณ", "หน่วยงานของตน", "ต้องตรงงบในแผน"],
            ["แหล่งเงิน", "เงินบำรุง", "ห้ามใช้เงินคนละแหล่ง"],
            ["หมวดงบประมาณ", "วัสดุ", "ต้องตรงบรรทัดงบที่อนุมัติ"],
            ["ประเภทการรับสินค้า", "คลังยา: Receipts", "เลือกได้เฉพาะ Receipts"],
            ["ชื่อสำหรับซื้อใน e-GP", "ชื่อตามประกาศ", "ใช้ตอนจัดซื้อใน e-GP"],
        ],
        [4.4, 5.2, 6.6],
    )
    callout(
        doc,
        "ขอเลขสารบรรณกดที่หัวเอกสาร",
        "ไม่มีแท็บสารบรรณบนใบขอซื้อ กดปุ่ม ขอเลขสารบรรณ ที่หัวเอกสาร "
        "เพื่อออกเลขสำหรับรายงานขออนุมัติจัดซื้อจัดจ้าง "
        "คำสั่งแต่งตั้ง แบบแสดงความบริสุทธิ์ใจ และหนังสือราชการอื่น "
        "เปิดเอกสารนั้นแล้วกด ขอเลขจากระบบสารบรรณ แต่ละฉบับได้เลขของตนเอง "
        "แล้วแสดงที่ช่อง ที่ ในไฟล์ที่พิมพ์",
        "info",
    )

    heading(doc, "4.3 บันทึกข้อมูลในแต่ละแท็บ", 2)
    body(
        doc,
        "หลังกรอกหัวเอกสารแล้ว ให้เลื่อนลงมาที่แถบแท็บด้านล่างของใบขอซื้อ "
        "ลำดับแท็บตรงกับระบบ คือ สินค้า รายชื่อคณะกรรมการ เอกสารแต่งตั้งคณะกรรมการ "
        "เอกสารแสดงความบริสุทธิ์ใจ เอกสารขออนุมัติจัดซื้อจัดจ้าง เอกสารราชการที่เกี่ยวข้อง และตรวจสอบงบประมาณ "
        "บันทึกจากซ้ายไปขวาตามลำดับ แล้วจึงกดเช็คงบประมาณ ส่งพัสดุ และขออนุมัติ "
        "แท็บที่ต้องกรอกขณะเป็นร่างคือ สินค้า และรายชื่อคณะกรรมการ "
        "แท็บเอกสารแต่งตั้งคณะกรรมการ และแท็บเอกสารแสดงความบริสุทธิ์ใจ ใช้กดออกเอกสารแล้วส่งเพื่อลงนาม "
        "แท็บเอกสารขออนุมัติจัดซื้อจัดจ้างแสดงเฉพาะรายงานขออนุมัติ "
        "แท็บเอกสารราชการที่เกี่ยวข้องใช้ดูเอกสารราชการทั้งหมดที่ออกจากใบนี้ "
        "แท็บตรวจสอบงบประมาณใช้ดูผลเช็คงบ",
    )
    picture(doc, "fig_proc_pr_tabs.png", 16.2, "ภาพที่ 14  แท็บบนใบขอซื้อ ตรงกับแถบแท็บในระบบ พร้อมคำอธิบาย")
    picture(doc, "Screenshot_TAB_overview_items.png", 16.2, "ภาพที่ 15  ภาพรวมแท็บสินค้า")
    picture(doc, "Screenshot_TAB_overview_committee.png", 16.2, "ภาพที่ 16  ภาพรวมแท็บรายชื่อคณะกรรมการ")
    picture(doc, "Screenshot_TAB_overview_wa.png", 16.2, "ภาพที่ 17  ภาพรวมแท็บเอกสารแต่งตั้งคณะกรรมการ")
    picture(doc, "Screenshot_TAB_overview_integrity.png", 16.2, "ภาพที่ 18  ภาพรวมแท็บเอกสารแสดงความบริสุทธิ์ใจ")
    picture(doc, "Screenshot_TAB_overview_approval.png", 16.2, "ภาพที่ 19  ภาพรวมแท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง")
    picture(doc, "Screenshot_TAB_overview_official.png", 16.2, "ภาพที่ 20  ภาพรวมแท็บเอกสารราชการที่เกี่ยวข้อง")
    picture(doc, "Screenshot_TAB_overview_budget.png", 16.2, "ภาพที่ 21  ภาพรวมแท็บตรวจสอบงบประมาณ")
    make_table(
        doc,
        ["แท็บ", "ต้องบันทึกหรือไม่", "ทำอะไร"],
        [
            ["สินค้า", "ต้อง", "เพิ่มรายการของ จำนวน หน่วย งบประมาณ และชื่อซื้อ e-GP"],
            ["รายชื่อคณะกรรมการ", "ควร", "ใส่กรรมการตรวจรับ จัดซื้อจัดจ้าง และราคากลาง"],
            ["เอกสารแต่งตั้งคณะกรรมการ", "ตามที่ใช้", "ออกคำสั่งแต่งตั้งตรวจรับ แล้วส่งเพื่อลงนามให้ผู้อำนวยการ"],
            ["เอกสารแสดงความบริสุทธิ์ใจ", "เมื่อวงเงินมากกว่า 100,000 บาท", "ออกแบบ แล้วส่งเพื่อลงนามตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และกรรมการ"],
            ["เอกสารขออนุมัติจัดซื้อจัดจ้าง", "ตามที่ใช้", "ออกรายงานขออนุมัติ แล้วส่งเพื่อลงนามตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และผู้อำนวยการ"],
            ["เอกสารราชการที่เกี่ยวข้อง", "ไม่กรอกเอง", "ดูรายการเอกสารราชการทั้งหมดที่ออกจากใบขอซื้อนี้"],
            ["ตรวจสอบงบประมาณ", "ไม่กรอกเอง", "ดูผลหลังกดปุ่มเช็คงบประมาณที่หัวเอกสาร"],
        ],
        [4.0, 3.6, 8.6],
    )

    heading(doc, "4.3.1 แท็บสินค้า", 3)
    body(
        doc,
        "แท็บนี้เป็นแท็บแรกและสำคัญที่สุด ถ้าไม่มีบรรทัดสินค้า ระบบจะส่งขออนุมัติไม่ได้ "
        "กดเพิ่มรายการที่ท้ายตาราง แล้วกรอกทีละบรรทัดขณะใบยังเป็นร่าง",
    )
    picture(doc, "Screenshot_TAB_ITEM.png", 16.2, "ภาพที่ 22  แท็บสินค้า เพิ่มรายการ จำนวน หน่วย และงบประมาณ")
    steps(
        doc,
        [
            "เปิดแท็บสินค้า แล้วกด เพิ่มรายการ ที่ท้ายตาราง",
        ],
    )
    picture(doc, "Screenshot_TAB_ITEM_add_line.png", 16.2, "ภาพที่ 23  ปุ่มเพิ่มรายการที่ท้ายตารางสินค้า")
    steps(
        doc,
        [
            "เลือกสินค้าจากรหัสหรือชื่อ เมื่อเลือกแล้วระบบจะเติมชื่อ หน่วยนับ และชื่อสำหรับซื้อใน e-GP ให้",
            "ใส่จำนวนที่ขอ และตรวจหน่วยวัดให้ถูกต้อง เช่น กล่อง ขวด ชิ้น",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_ITEM_qty_uom.png", 16.2, "ภาพที่ 24  จำนวนและหน่วยวัดของรายการสินค้า")
    steps(
        doc,
        [
            "ใส่วันที่ต้องการของ ถ้าไม่ใส่ระบบจะใช้วันที่สร้างใบ",
        ],
        start=4,
    )
    picture(doc, "Screenshot_TAB_ITEM_date.png", 16.2, "ภาพที่ 25  วันที่ร้องขอของรายการสินค้า")
    steps(
        doc,
        [
            "ใส่งบประมาณของบรรทัดนั้น เป็นยอดรวมของรายการ ไม่ใช่ราคาต่อหน่วยถ้าหน้าจอแสดงเป็นยอดงบ",
        ],
        start=5,
    )
    picture(doc, "Screenshot_TAB_ITEM_budget.png", 16.2, "ภาพที่ 26  งบประมาณของรายการสินค้า")
    steps(
        doc,
        [
            "ตรวจชื่อสำหรับซื้อใน e-GP ถ้าชื่อในคลังไม่ตรงประกาศ ให้แก้ในช่องนี้",
        ],
        start=6,
    )
    picture(doc, "Screenshot_TAB_ITEM_egp_name.png", 16.2, "ภาพที่ 27  ชื่อสำหรับซื้อใน e-GP")
    steps(
        doc,
        [
            "ถ้ามีคุณลักษณะเฉพาะ กดปุ่มดู/แนบไฟล์ เพื่อใส่รายละเอียด รูปสแกน หรือไฟล์ PDF ของรายการนั้น",
        ],
        start=7,
    )
    picture(doc, "Screenshot_TAB_ITEM_spec.png", 16.2, "ภาพที่ 28  ปุ่มดู/แนบไฟล์คุณลักษณะของรายการ")
    steps(
        doc,
        [
            "เพิ่มรายการถัดไปจนครบ แล้วดูยอดรวมงบประมาณที่ขอที่ท้ายแท็บ",
        ],
        start=8,
    )
    make_table(
        doc,
        ["คอลัมน์ในแท็บสินค้า", "ต้องใส่", "หมายเหตุ"],
        [
            ["สินค้า / รหัสสินค้า", "ใช่", "เลือกจากข้อมูลหลัก อย่าพิมพ์ชื่อลอยถ้ามีรหัสแล้ว"],
            ["จำนวน", "ใช่", "ต้องมากกว่า 0"],
            ["หน่วยวัด", "ใช่", "ตามหน่วยซื้อของสินค้า"],
            ["วันที่ต้องการ", "ควร", "วันที่หน่วยงานต้องการของ"],
            ["งบประมาณ", "ใช่", "ยอดที่ใช้เช็คงบของบรรทัดนี้"],
            ["ชื่อสำหรับซื้อใน e-GP", "ควร", "ชื่อที่จะใช้ตอนประกาศ/จัดซื้อ e-GP"],
            ["ไฟล์คุณลักษณะ", "ถ้ามี", "กดดู/แนบไฟล์ เพื่อสแกนหรือแนบ PDF แยกรายการ"],
        ],
        [4.8, 2.4, 9.0],
    )
    callout(
        doc,
        "อย่าส่งใบที่ยังไม่มีสินค้า",
        "ถ้าตารางสินค้าว่าง หรือจำนวนเป็น 0 ระบบจะกันการส่งขออนุมัติ "
        "หลังแก้รายการแล้วต้องกดเช็คงบประมาณอีกครั้งก่อนส่ง",
        "warn",
    )

    heading(doc, "4.3.2 แท็บรายชื่อคณะกรรมการ", 3)
    body(
        doc,
        "เปิดแท็บรายชื่อคณะกรรมการ เพื่อบันทึกกรรมการที่เกี่ยวข้องกับใบนี้ "
        "เลือกพนักงานจากรายชื่อที่มีในระบบ อย่าสร้างพนักงานใหม่จากหน้านี้ "
        "ชื่อ แผนก อีเมล และโทรศัพท์จะเติมให้อัตโนมัติเมื่อเลือกพนักงาน",
    )
    body(
        doc,
        "ชุดตัวอย่างด้านล่างใช้กับใบขอซื้อประเภท ซื้อ/จ้าง/เช่า ผ่านพัสดุ วงเงินไม่เกิน 500,000 บาท "
        "เช่น ใบตัวอย่าง PR6909001 ยอด 8,000 บาท "
        "ต้องมีกรรมการตรวจรับอย่างน้อย 3 คน และแต่ละคนในใบเดียวกันห้ามซ้ำ "
        "เลือกพนักงานจากบัญชีฝึกอบรม uat.committee1 คนที่ 1 (ประธาน)  uat.committee2 คนที่ 2 (กรรมการ)  uat.committee3 คนที่ 3 (เลขา)",
    )
    heading(doc, "ข้อมูลตัวอย่าง — คณะกรรมการตรวจรับ", 3)
    make_table(
        doc,
        ["ลำดับ", "พนักงาน (ตัวอย่าง)", "บทบาท", "หน่วยงาน"],
        [
            ["1", "ผู้ทดสอบกรรมการตรวจรับ คนที่ 1", "ประธาน", "หน่วยงานทดสอบ"],
            ["2", "ผู้ทดสอบกรรมการตรวจรับ คนที่ 2", "กรรมการ", "หน่วยงานทดสอบ"],
            ["3", "ผู้ทดสอบกรรมการตรวจรับ คนที่ 3", "กรรมการ", "หน่วยงานทดสอบ"],
        ],
        [2.2, 5.0, 3.2, 5.8],
    )
    callout(
        doc,
        "คนเดียวกันห้ามซ้ำในใบเดียว",
        "ระบบไม่ให้เลือกพนักงานคนเดียวกันซ้ำในใบขอซื้อใบเดียวกัน แม้คนละชุดกรรมการ "
        "ชุดฝึกอบรมใช้กรรมการตรวจรับ 3 คน จาก uat.committee1–3 "
        "ถ้ามีกรรมการมากกว่า 1 คน ในชุดเดียวกัน ต้องมีประธานเพียง 1 คน",
        "warn",
    )
    make_table(
        doc,
        ["กลุ่มในแท็บ", "ใช้เมื่อ", "สิ่งที่ต้องใส่"],
        [
            ["คณะกรรมการตรวจรับ", "ทุกใบที่มีการตรวจรับของ", "พนักงาน บทบาท ประธาน/กรรมการ"],
            ["คณะกรรมการจัดซื้อจัดจ้าง", "ใบที่ต้องมีกรรมการพิจารณา", "พนักงาน บทบาท ประธาน/กรรมการ"],
            ["คณะกรรมการกำหนดราคากลาง", "เมื่อต้องตั้งราคากลาง", "พนักงาน บทบาท ตามที่หน่วยงานกำหนด"],
        ],
        [5.2, 5.4, 5.6],
    )
    picture(
        doc,
        "Screenshot_TAB_commitee.png",
        16.2,
        "ภาพที่ 29  แท็บรายชื่อคณะกรรมการ เพิ่มกรรมการตรวจรับ 3 คน จากชุดฝึกอบรม",
    )
    steps(
        doc,
        [
            "เปิดแท็บรายชื่อคณะกรรมการ แล้วกด เพิ่มรายการ ในกลุ่มคณะกรรมการตรวจรับ",
        ],
    )
    picture(doc, "Screenshot_TAB_committee_add.png", 16.2, "ภาพที่ 30  ปุ่มเพิ่มรายการในกลุ่มคณะกรรมการตรวจรับ")
    steps(
        doc,
        [
            "เลือกพนักงานจากชุดฝึกอบรม คนที่ 1 เป็นประธาน คนที่ 2 และคนที่ 3 เป็นกรรมการ",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_committee_roles.png", 16.2, "ภาพที่ 31  เลือกพนักงานและบทบาทในคณะกรรมการตรวจรับ")
    steps(
        doc,
        [
            "ระบบจะเติมชื่อคณะกรรมการ แผนก และอีเมลที่ทำงานให้ ตรวจว่ามีประธานเพียง 1 คน",
        ],
        start=3,
    )
    picture(doc, "Screenshot_TAB_committee_filled.png", 16.2, "ภาพที่ 32  ชื่อ แผนก อีเมล และประธานเพียง 1 คน")
    steps(
        doc,
        [
            "ถ้าใบนั้นต้องมีกรรมการพิจารณา ให้เพิ่มในกลุ่มคณะกรรมการจัดซื้อจัดจ้าง ด้วยวิธีเดียวกัน",
        ],
        start=4,
    )
    picture(doc, "Screenshot_TAB_committee_procure_add.png", 16.2, "ภาพที่ 33  ปุ่มเพิ่มรายการในกลุ่มคณะกรรมการจัดซื้อจัดจ้าง")
    steps(
        doc,
        [
            "ถ้าต้องกำหนดราคากลาง ให้เพิ่มรายชื่อในกลุ่มคณะกรรมการกำหนดราคากลาง",
        ],
        start=5,
    )
    picture(doc, "Screenshot_TAB_committee_price_add.png", 16.2, "ภาพที่ 34  ปุ่มเพิ่มรายการในกลุ่มคณะกรรมการกำหนดราคากลาง")
    steps(
        doc,
        [
            "บันทึกใบขอซื้อ แล้วตรวจว่าคนเดียวกันไม่ซ้ำในใบเดียวกัน",
        ],
        start=6,
    )
    picture(doc, "Screenshot_TAB_committee_save.png", 16.2, "ภาพที่ 35  ปุ่มบันทึกด้วยตนเองของใบขอซื้อ")
    callout(
        doc,
        "กติกาจำนวนกรรมการ",
        "ถ้ามีกรรมการมากกว่า 1 คน ในชุดเดียวกัน ต้องมีประธานเพียง 1 คน "
        "ถ้ามีคนเดียว ห้ามตั้งเป็นประธาน "
        "งานจ้างที่ปรึกษาต้องมีกรรมการจัดซื้อและกรรมการตรวจรับอย่างน้อยชุดละ 5 คน "
        "งานจ้างออกแบบและควบคุมงานก่อสร้างต้องมีกรรมการตรวจรับอย่างน้อย 3 คน",
        "warn",
    )
    heading(doc, "4.3.3 แท็บเอกสารแต่งตั้งคณะกรรมการ", 3)
    body(
        doc,
        "เมื่อบันทึกคณะกรรมการตรวจรับครบแล้ว พัสดุออกคำสั่งแต่งตั้งจากแท็บเอกสารแต่งตั้งคณะกรรมการ "
        "ระบบดึงรายชื่อจากกลุ่มคณะกรรมการตรวจรับในแท็บรายชื่อคณะกรรมการมาใส่คำสั่ง ไม่ต้องพิมพ์รายชื่อใหม่ "
        "จากนั้นตรวจข้อความ พิมพ์ PDF แล้วกด ส่งเพื่อลงนาม ให้ผู้อำนวยการโรงพยาบาล",
    )
    picture(
        doc,
        "Screenshot_TAB_wa_committee.png",
        16.2,
        "ภาพที่ 36  แท็บเอกสารแต่งตั้งคณะกรรมการของใบขอซื้อ PR6909006",
    )
    steps(
        doc,
        [
            "บันทึกใบขอซื้อให้มีกรรมการตรวจรับในแท็บคณะกรรมการก่อน อย่างน้อย 1 คน ตามกติกาจำนวนกรรมการของประเภทงาน",
            "อยู่ที่แท็บเอกสารแต่งตั้งคณะกรรมการ แล้วกดปุ่ม ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_create_button.png",
        16.2,
        "ภาพที่ 37  ปุ่มออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
    )
    steps(
        doc,
        [
            "ระบบเปิดเอกสารคำสั่งแต่งตั้ง และดึงรายชื่อกรรมการตรวจรับ เรื่อง อำนาจหน้าที่ และข้อความเริ่มต้นให้อัตโนมัติ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_order_pulled.png",
        16.2,
        "ภาพที่ 38  เอกสารคำสั่งที่ดึงเรื่องและรายชื่อกรรมการตรวจรับ",
    )
    steps(
        doc,
        [
            "ตรวจช่องเลขที่จากสารบรรณ แล้วกด ขอเลขจากระบบสารบรรณ ที่หัวคำสั่ง เพื่อออกเลขเฉพาะคำสั่งนี้ อย่าใช้เลขจากใบขอซื้อ เลขนี้จะไปแสดงที่ช่อง ที่ ในคำสั่ง",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_saraban.png",
        16.2,
        "ภาพที่ 39  ช่องเลขที่จากสารบรรณและปุ่มขอเลขจากระบบสารบรรณ",
    )
    steps(
        doc,
        [
            "ตรวจเลขที่คำสั่ง ปี พ.ศ. เรื่อง รายชื่อในแท็บคณะกรรมการของเอกสารคำสั่ง และชื่อผู้ลงนาม",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_order_check.png",
        16.2,
        "ภาพที่ 40  เลขที่คำสั่ง ปี พ.ศ. เรื่อง และผู้ลงนาม",
    )
    steps(
        doc,
        [
            "ถ้าแก้รายชื่อบนใบขอซื้อภายหลัง ให้กด ดึงรายชื่อจากแท็บคณะกรรมการ แล้วกด สร้างข้อความจากข้อมูล",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_pull_text.png",
        14.0,
        "ภาพที่ 41  ปุ่มดึงรายชื่อจากแท็บคณะกรรมการและสร้างข้อความจากข้อมูล",
    )
    steps(
        doc,
        [
            "กด พิมพ์ PDF เพื่อเปิดไฟล์สำหรับพิมพ์และเก็บสำเนา หรือกด สร้างไฟล์ Word เพื่อดาวน์โหลดแบบฟอร์ม .docx",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_print.png",
        8.2,
        "ภาพที่ 42  ปุ่มสร้างไฟล์ Word และพิมพ์ PDF",
    )
    steps(
        doc,
        [
            "กด ส่งเพื่อลงนาม ในแถวเอกสาร คำสั่งชุดนี้ส่งให้ผู้อำนวยการโรงพยาบาล (uat.director) ลงนาม",
        ],
        start=8,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_send.png",
        7.2,
        "ภาพที่ 43  ปุ่มส่งเพื่อลงนามในแถวเอกสารคำสั่ง",
    )
    steps(
        doc,
        [
            "ครั้งถัดไปบนใบเดียวกัน ปุ่มจะเปลี่ยนเป็น เปิดคำสั่งแต่งตั้งคณะกรรมการตรวจรับ ไม่สร้างเอกสารซ้ำ",
        ],
        start=9,
    )
    picture(
        doc,
        "Screenshot_TAB_wa_open.png",
        9.8,
        "ภาพที่ 44  ปุ่มเปิดคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
    )
    make_table(
        doc,
        ["ปุ่ม / จุดที่กด", "ใช้ทำอะไร"],
        [
            [
                "ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
                "สร้างคำสั่งจากใบขอซื้อ ดึงรายชื่อกรรมการตรวจรับ",
            ],
            [
                "เปิดคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
                "เปิดคำสั่งที่ออกแล้วของใบนี้ ไม่สร้างใหม่",
            ],
            [
                "ดึงรายชื่อจากแท็บคณะกรรมการ",
                "รีเฟรชรายชื่อในคำสั่งให้ตรงกับใบขอซื้อ",
            ],
            ["สร้างข้อความจากข้อมูล", "สร้างเรื่องและย่อหน้าตามข้อมูลล่าสุด"],
            ["ขอเลขจากระบบสารบรรณ", "ออกเลขสารบรรณเฉพาะคำสั่งนี้ แยกจากเลขเอกสารอนุมัติขอซื้อ"],
            ["สร้างไฟล์ Word", "สร้างและดาวน์โหลดไฟล์ .docx ตามแบบฟอร์ม"],
            ["พิมพ์ PDF", "สร้างไฟล์ PDF เปิดดูแล้วพิมพ์ได้ ระบบแนบไฟล์ไว้ที่เอกสาร"],
            ["ส่งเพื่อลงนาม", "ส่งคำสั่งเข้ากล่องงานรออนุมัติของผู้อำนวยการ"],
            [
                "สถิติ หนังสือราชการ",
                "เปิดรายการหนังสือที่ออกจากใบนี้ รวมคำสั่งแต่งตั้ง",
            ],
        ],
        [6.4, 9.8],
    )
    body(
        doc,
        "ตัวอย่างด้านล่างคือคำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุที่พิมพ์จากระบบ "
        "หัวเอกสารเป็นคำสั่งโรงพยาบาลวชิระภูเก็ต รายชื่อตรงกับกรรมการตรวจรับชุดฝึกอบรม "
        "ผู้ทดสอบกรรมการตรวจรับ คนที่ 1–3 และลงนามโดยผู้อำนวยการโรงพยาบาล",
    )
    picture(
        doc,
        "Screenshot_WA_committee_order_PR6909001.png",
        14.8,
        "ภาพที่ 45  ตัวอย่างคำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ ที่พิมพ์จากระบบ",
    )
    callout(
        doc,
        "ใครกดออกคำสั่งได้",
        "หน่วยงานสร้างใบขอซื้อ บันทึกรายชื่อกรรมการ แล้วกดส่งพัสดุและขออนุมัติ "
        "พัสดุสร้างเอกสารคำสั่งแต่งตั้ง แบบแสดงความบริสุทธิ์ใจ และรายงานขออนุมัติ แล้วกดส่งเพื่อลงนาม "
        "ปุ่มออกคำสั่งแต่งตั้งอยู่ที่แท็บเอกสารแต่งตั้งคณะกรรมการ "
        "ปุ่มออกแบบแสดงความบริสุทธิ์ใจอยู่ที่แท็บเอกสารแสดงความบริสุทธิ์ใจ "
        "บัญชีหน่วยงานใช้บันทึกรายชื่อกรรมการได้ แต่โดยปกติจะไม่เห็นปุ่มออกเอกสารและพิมพ์ "
        "เมนูสำรองอยู่ที่ จัดซื้อและผู้ขาย → หนังสือราชการ → คำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
        "info",
    )
    callout(
        doc,
        "ยังไม่มีกรรมการตรวจรับ ออกคำสั่งไม่ได้",
        "ระบบจะเตือนให้บันทึกคณะกรรมการตรวจรับในแท็บคณะกรรมการก่อน "
        "ใบขอซื้อหนึ่งใบออกคำสั่งชุดนี้ได้หนึ่งฉบับ "
        "ถ้าต้องการออกใหม่ ให้ยกเลิกคำสั่งเดิมก่อน",
        "warn",
    )
    body(
        doc,
        "รายชื่อกรรมการในแท็บรายชื่อคณะกรรมการยังถูกนำไปใช้ในหนังสือราชการอัตโนมัติ "
        "คณะกรรมการพิจารณาผล e-bidding ดึงจากคณะกรรมการจัดซื้อจัดจ้าง "
        "และคณะกรรมการตรวจรับพัสดุดึงจากคณะกรรมการตรวจรับ",
    )

    heading(doc, "4.3.4 แท็บเอกสารแสดงความบริสุทธิ์ใจ", 3)
    body(
        doc,
        "แบบแสดงความบริสุทธิ์ใจใช้เปิดเผยว่าเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และคณะกรรมการตรวจรับพัสดุ "
        "ไม่มีผลประโยชน์ทับซ้อนกับการจัดซื้อจัดจ้างครั้งนั้น "
        "แบบฟอร์มนี้กำหนดสำหรับวงเงินมากกว่า 100,000 บาท "
        "กดออกจากแท็บเอกสารแสดงความบริสุทธิ์ใจ รายชื่อกรรมการดึงจากแท็บรายชื่อคณะกรรมการ "
        "หลังพิมพ์ PDF ให้กด ส่งเอกสารอนุมัติ จากปุ่ม ส่งเพื่อลงนาม ระบบส่งให้ลงนามตามลำดับ ห้ามข้ามขั้น "
        "เจ้าหน้าที่ → หัวหน้าเจ้าหน้าที่ → กรรมการตามลำดับในเอกสาร (ประธานก่อน แล้วกรรมการคนถัดไป) "
        "ผู้อำนวยการไม่ลงนามเอกสารชุดนี้",
    )
    picture(
        doc,
        "fig_proc_integrity.png",
        16.2,
        "ภาพที่ 46  สร้างเอกสารแสดงความบริสุทธิ์ใจ พิมพ์ PDF ส่งเอกสารอนุมัติ แล้วลงนามตามลำดับ",
    )
    steps(
        doc,
        [
            "บันทึกกรรมการตรวจรับในแท็บรายชื่อคณะกรรมการให้ครบ แล้วบันทึกใบขอซื้อ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_committee.png",
        16.2,
        "ภาพที่ 47  คณะกรรมการตรวจรับในแท็บรายชื่อคณะกรรมการ",
    )
    steps(
        doc,
        [
            "เปิดแท็บเอกสารแสดงความบริสุทธิ์ใจ แล้วกดปุ่ม ออกแบบแสดงความบริสุทธิ์ใจ",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_create.png",
        16.2,
        "ภาพที่ 48  แท็บเอกสารแสดงความบริสุทธิ์ใจและปุ่มออกแบบแสดงความบริสุทธิ์ใจ",
    )
    steps(
        doc,
        [
            "ระบบเปิดเอกสารแบบแสดงความบริสุทธิ์ใจ และดึงเจ้าหน้าที่จากบัญชีฝึกอบรม uat.officer "
            "(ผู้ทดสอบเจ้าหน้าที่) หัวหน้าเจ้าหน้าที่จาก uat.head_officer (ผู้ทดสอบหัวหน้าเจ้าหน้าที่) "
            "และกรรมการตรวจรับจากแท็บรายชื่อคณะกรรมการ ตามลำดับประธานแล้วกรรมการ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_pulled.png",
        16.2,
        "ภาพที่ 49  เอกสารแบบแสดงความบริสุทธิ์ใจที่ดึงเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และกรรมการตรวจรับ",
    )
    steps(
        doc,
        [
            "ตรวจชื่อและตำแหน่งให้ครบ ถ้ายังไม่ตรงให้แก้ช่องบนเอกสารก่อนพิมพ์ "
            "กรรมการต้องผูกบัญชีผู้ใช้ เช่น uat.committee1–3 จึงจะลงนามในระบบได้",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_names.png",
        12.0,
        "ภาพที่ 50  ชื่อและตำแหน่งเจ้าหน้าที่กับหัวหน้าเจ้าหน้าที่",
    )
    steps(
        doc,
        [
            "กด ขอเลขจากระบบสารบรรณ ที่หัวเอกสาร เพื่อออกเลขเฉพาะแบบนี้ แยกจากเลขใบขอซื้อ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_saraban.png",
        16.2,
        "ภาพที่ 51  ช่องเลขที่จากสารบรรณและปุ่มขอเลขจากระบบสารบรรณ",
    )
    steps(
        doc,
        [
            "ถ้าแก้รายชื่อบนใบขอซื้อภายหลัง ให้กด ดึงรายชื่อจากแท็บคณะกรรมการ",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_pull.png",
        12.0,
        "ภาพที่ 52  ปุ่มดึงรายชื่อจากแท็บคณะกรรมการ",
    )
    steps(
        doc,
        [
            "กด พิมพ์ PDF เพื่อสร้างไฟล์สำหรับประทับลายเซ็น หรือกด สร้างไฟล์ Word เพื่อดาวน์โหลดแบบฟอร์ม .docx",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_print.png",
        10.0,
        "ภาพที่ 53  ปุ่มสร้างไฟล์ Word และพิมพ์ PDF",
    )
    steps(
        doc,
        [
            "กลับไปที่แท็บเอกสารแสดงความบริสุทธิ์ใจ แล้วกด ส่งเอกสารอนุมัติ จากปุ่ม ส่งเพื่อลงนาม ในแถวเอกสาร",
        ],
        start=8,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_send.png",
        7.2,
        "ภาพที่ 54  ปุ่มส่งเพื่อลงนามในแถวเอกสารแบบแสดงความบริสุทธิ์ใจ",
    )
    steps(
        doc,
        [
            "เจ้าหน้าที่ (uat.officer) เปิดเมนู การอนุมัติตามลำดับ → งานรออนุมัติของฉัน เปิดไฟล์แล้วลงนาม",
        ],
        start=9,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_inbox.png",
        16.2,
        "ภาพที่ 55  กล่องงานรออนุมัติของฉันของเจ้าหน้าที่ มีแบบแสดงความบริสุทธิ์ใจ",
    )
    steps(
        doc,
        [
            "เมื่อเจ้าหน้าที่ลงนามแล้ว หัวหน้าเจ้าหน้าที่จึงเห็นรายการนี้ แล้วลงนามเป็นลำดับที่สอง",
        ],
        start=10,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_menu.png",
        8.0,
        "ภาพที่ 56  เมนูการอนุมัติตามลำดับ → งานรออนุมัติของฉัน",
    )
    steps(
        doc,
        [
            "จากนั้นกรรมการลงนามตามลำดับในเอกสาร ประธาน (uat.committee1) แล้วกรรมการคนที่ 2 และ 3 "
            "คนที่ยังไม่ถึงลำดับจะยังไม่เห็นรายการในกล่องงานรออนุมัติ",
        ],
        start=11,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_sign_order.png",
        16.2,
        "ภาพที่ 57  ลำดับกรรมการตรวจรับในเอกสาร ประธานแล้วกรรมการ",
    )
    steps(
        doc,
        [
            "ครั้งถัดไปบนใบเดียวกัน ปุ่มจะเปลี่ยนเป็น เปิดแบบแสดงความบริสุทธิ์ใจ ไม่สร้างเอกสารซ้ำ",
        ],
        start=12,
    )
    picture(
        doc,
        "Screenshot_TAB_integrity_open.png",
        9.8,
        "ภาพที่ 58  ปุ่มเปิดแบบแสดงความบริสุทธิ์ใจ",
    )
    make_table(
        doc,
        ["ปุ่ม / จุดที่กด", "ใช้ทำอะไร"],
        [
            [
                "ออกแบบแสดงความบริสุทธิ์ใจ",
                "สร้างแบบจากใบขอซื้อ ดึงเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และกรรมการตรวจรับ",
            ],
            [
                "เปิดแบบแสดงความบริสุทธิ์ใจ",
                "เปิดแบบที่ออกแล้วของใบนี้ ไม่สร้างใหม่",
            ],
            [
                "ดึงรายชื่อจากแท็บคณะกรรมการ",
                "รีเฟรชรายชื่อกรรมการตรวจรับให้ตรงกับใบขอซื้อ",
            ],
            ["ขอเลขจากระบบสารบรรณ", "ออกเลขสารบรรณเฉพาะแบบนี้ แยกจากเลขเอกสารอนุมัติขอซื้อ"],
            ["สร้างไฟล์ Word", "สร้างและดาวน์โหลดไฟล์ .docx ตามแบบฟอร์ม"],
            ["พิมพ์ PDF", "สร้างไฟล์ PDF สำหรับประทับลายเซ็น ระบบแนบไฟล์ไว้ที่เอกสาร"],
            [
                "ส่งเอกสารอนุมัติ / ส่งเพื่อลงนาม",
                "ส่งเข้ากล่องงานรออนุมัติตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ แล้วกรรมการ กดหลังพิมพ์ PDF",
            ],
        ],
        [6.4, 9.8],
    )
    heading(doc, "ข้อมูลตัวอย่าง — ผู้ลงนามแบบแสดงความบริสุทธิ์ใจ", 3)
    make_table(
        doc,
        ["ลำดับลงนาม", "บัญชีฝึกอบรม", "ชื่อที่ปรากฏ"],
        [
            ["1 เจ้าหน้าที่", "uat.officer", "ผู้ทดสอบเจ้าหน้าที่"],
            ["2 หัวหน้าเจ้าหน้าที่", "uat.head_officer", "ผู้ทดสอบหัวหน้าเจ้าหน้าที่"],
            ["3 ประธานกรรมการ", "uat.committee1", "ผู้ทดสอบกรรมการตรวจรับ คนที่ 1"],
            ["4 กรรมการ", "uat.committee2", "ผู้ทดสอบกรรมการตรวจรับ คนที่ 2"],
            ["5 กรรมการ", "uat.committee3", "ผู้ทดสอบกรรมการตรวจรับ คนที่ 3"],
        ],
        [4.4, 4.4, 7.4],
    )
    callout(
        doc,
        "ลงนามตามลำดับ ห้ามข้ามขั้น",
        "แบบแสดงความบริสุทธิ์ใจไม่ส่งให้ผู้อำนวยการ "
        "และไม่ผูกกับการอนุมัติใบขอซื้อ "
        "เอกสารถึงสถานะลงนามแล้วเมื่อกรรมการคนสุดท้ายลงนามครบ "
        "ถ้ายังไม่เห็นรายการในกล่องงานรออนุมัติ ให้ตรวจว่าคนก่อนหน้าลงนามแล้วหรือยัง",
        "warn",
    )
    callout(
        doc,
        "ใช้เมื่อวงเงินมากกว่า 100,000 บาท",
        "ชื่อแบบฟอร์มคือ แบบแสดงความบริสุทธิ์ใจ (วงเงินมากกว่า 100,000 บาท) "
        "ถ้าวงเงินไม่ถึงเกณฑ์นี้ ไม่ต้องออกเอกสารชุดนี้ "
        "เมนูสำรองอยู่ที่ จัดซื้อและผู้ขาย → หนังสือราชการ → แบบแสดงความบริสุทธิ์ใจ",
        "info",
    )
    body(
        doc,
        "ตัวอย่างด้านล่างคือแบบแสดงความบริสุทธิ์ใจที่พิมพ์จากระบบ "
        "รายชื่อเป็นชุดฝึกอบรม ผู้ทดสอบหัวหน้าเจ้าหน้าที่ ผู้ทดสอบเจ้าหน้าที่ "
        "และผู้ทดสอบกรรมการตรวจรับ คนที่ 1–3 "
        "หลังกดพิมพ์ PDF จะได้เอกสารลักษณะนี้ ถ้ามีกรรมการหลายคน ช่องลงนามจะต่อในหน้าถัดไป",
    )
    picture(
        doc,
        "Screenshot_integrity_PR6909001_p1.png",
        14.8,
        "ภาพที่ 59  ตัวอย่างแบบแสดงความบริสุทธิ์ใจ ที่พิมพ์จากระบบ",
    )

    heading(doc, "4.3.5 แท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง", 3)
    body(
        doc,
        "แท็บนี้อยู่ถัดจากเอกสารแสดงความบริสุทธิ์ใจ ใช้รายงานขออนุมัติจัดซื้อจัดจ้าง "
        "วิธีในรายงานตามที่เลือกในใบขอซื้อ เช่น เฉพาะเจาะจง อีบิดดิ้ง คัดเลือก หรือวิธีอื่น "
        "ระบบดึงรายการสินค้าเป็นข้อความในกล่องข้อ ๒ วงเงิน กรรมการตรวจรับ "
        "เจ้าหน้าที่ (uat.officer) หัวหน้าเจ้าหน้าที่ (uat.head_officer) "
        "และผู้ลงนามผู้อำนวยการโรงพยาบาล (uat.director) จากค่าตั้งต้นหนังสือราชการ "
        "ไม่ต้องพิมพ์รายงานใหม่ทั้งฉบับ และไม่ใส่ตารางรายการในข้อ ๒ ทั้งหน้าจอและไฟล์ที่พิมพ์ "
        "หลังพิมพ์ PDF ให้กด ส่งเพื่อลงนาม ระบบส่งให้ลงนามตามลำดับ "
        "เจ้าหน้าที่ → หัวหน้าเจ้าหน้าที่ → ผู้อำนวยการ ห้ามข้ามขั้น",
    )
    picture(
        doc,
        "fig_proc_approval.png",
        16.2,
        "ภาพที่ 60  ออกหนังสือขออนุมัติจัดซื้อจัดจ้างจากแท็บเอกสารขออนุมัติ แล้วพิมพ์",
    )
    steps(
        doc,
        [
            "บันทึกแท็บสินค้าและกรรมการตรวจรับให้ครบ แล้วบันทึกใบขอซื้อ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_prereq.png",
        16.2,
        "ภาพที่ 61  แท็บสินค้าที่บันทึกรายการครบก่อนออกหนังสือขออนุมัติ",
    )
    steps(
        doc,
        [
            "เปิดแท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง แล้วกดปุ่มออกหนังสือขออนุมัติจัดซื้อจัดจ้าง ข้อความปุ่มตามวิธีที่เลือกในใบขอซื้อ",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_create.png",
        16.2,
        "ภาพที่ 62  แท็บเอกสารขออนุมัติจัดซื้อจัดจ้างและปุ่มออกหนังสือขออนุมัติ",
    )
    steps(
        doc,
        [
            "ระบบเปิดรายงานขออนุมัติ และเติมเรื่อง วงเงิน เหตุผล กรรมการตรวจรับ และผู้ลงนามให้อัตโนมัติ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_pulled.png",
        16.2,
        "ภาพที่ 63  รายงานขออนุมัติที่ดึงเรื่อง ผู้ลงนาม หัวหน้าเจ้าหน้าที่ และเจ้าหน้าที่",
    )
    steps(
        doc,
        [
            "ตรวจช่องเลขที่จากสารบรรณ ที่หัวหนังสือ เลขนี้มาจากปุ่ม ขอเลขสารบรรณ บนใบขอซื้อ ถ้ายังว่างให้กลับไปกดที่ใบขอซื้อ หรือกด ขอเลขจากระบบสารบรรณ บนรายงานนี้ ระบบใช้เลขชุดเดียวกัน เลขนี้จะไปแสดงที่ช่อง ที่ ในรายงาน",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_saraban.png",
        16.2,
        "ภาพที่ 64  ช่องเลขที่จากสารบรรณและปุ่มขอเลขจากระบบสารบรรณ",
    )
    steps(
        doc,
        [
            "ดูกลุ่ม ๒. รายละเอียดงานที่จัดซื้อ จัดจ้าง มีกล่องข้อความอย่างเดียว ไม่มีตารางรายการ ระบบดึงจากแท็บสินค้าเป็นข้อความ เช่น ๑. ชื่อสินค้า  จำนวน  ๘๐  ขวด  เป็นเงิน  ๘,๐๐๐.๐๐  บาท",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_work2.png",
        16.2,
        "ภาพที่ 65  กลุ่มข้อ ๒ รายละเอียดงานที่จัดซื้อ จัดจ้าง เป็นข้อความ",
    )
    steps(
        doc,
        [
            "ตรวจและแก้ข้อความในกล่องข้อ ๒ ได้ตามต้องการ แล้วตรวจย่อหน้าแรก ข้อ ๑-๑๐ ยอดเงิน รายชื่อกรรมการ และชื่อผู้ลงนาม",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_check.png",
        16.2,
        "ภาพที่ 66  ย่อหน้าแรก ข้อ ๑ และข้อ ๒ ในรายงานขออนุมัติ",
    )
    steps(
        doc,
        [
            "ถ้าแก้สินค้าบนใบขอซื้อภายหลัง ให้กด สร้างข้อความจากข้อมูล เพื่อดึงรายการใหม่เข้ากล่องข้อ ๒ ถ้าแก้กรรมการให้กด ดึงรายชื่อจากแท็บคณะกรรมการ",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_pull_text.png",
        12.0,
        "ภาพที่ 67  ปุ่มดึงรายชื่อจากแท็บคณะกรรมการและสร้างข้อความจากข้อมูล",
    )
    steps(
        doc,
        [
            "กด พิมพ์ PDF ระบบสร้างไฟล์ Word ใหม่จากกล่องข้อความก่อน แล้วแปลงเป็น PDF ข้อ ๒ ในไฟล์ที่พิมพ์เป็นข้อความอย่างเดียว ไม่มีตารางลำดับ รายการ ราคาต่อหน่วย",
        ],
        start=8,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_print.png",
        10.0,
        "ภาพที่ 68  ปุ่มสร้างไฟล์ Word และพิมพ์ PDF",
    )
    steps(
        doc,
        [
            "เปิดดู PDF ตรวจว่าข้อ ๒ เป็นบรรทัดข้อความตามกล่อง ถ้ายังเห็นตารางรายการ ให้ปิดไฟล์เก่าแล้วกด พิมพ์ PDF อีกครั้ง",
        ],
        start=9,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_pdf.png",
        16.2,
        "ภาพที่ 69  แท็บไฟล์ที่สร้าง มี PDF ของรายงานขออนุมัติ",
    )
    steps(
        doc,
        [
            "ถ้าต้องการไฟล์ .docx ให้กด สร้างไฟล์ Word หลังตรวจกล่องข้อ ๒ แล้ว",
        ],
        start=10,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_word.png",
        7.2,
        "ภาพที่ 70  ปุ่มสร้างไฟล์ Word",
    )
    steps(
        doc,
        [
            "กลับไปที่แท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง แล้วกด ส่งเพื่อลงนาม ในแถวเอกสาร "
            "หรือกดขออนุมัติบนใบขอซื้อเมื่อเอกสารชุดอนุมัติครบ ระบบจะส่งรายงานเข้าลำดับลงนามเช่นกัน",
        ],
        start=11,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_send.png",
        7.2,
        "ภาพที่ 71  ปุ่มส่งเพื่อลงนามในแถวเอกสารขออนุมัติ",
    )
    steps(
        doc,
        [
            "เจ้าหน้าที่ (uat.officer) เปิดเมนู การอนุมัติตามลำดับ → งานรออนุมัติของฉัน แล้วลงนามเป็นลำดับแรก",
        ],
        start=12,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_inbox.png",
        16.2,
        "ภาพที่ 72  กล่องงานรออนุมัติของฉันของเจ้าหน้าที่",
    )
    steps(
        doc,
        [
            "เมื่อเจ้าหน้าที่ลงนามแล้ว หัวหน้าเจ้าหน้าที่จึงเห็นรายการนี้ แล้วลงนามเป็นลำดับที่สอง",
        ],
        start=13,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_menu.png",
        8.0,
        "ภาพที่ 73  เมนูการอนุมัติตามลำดับ → งานรออนุมัติของฉัน",
    )
    steps(
        doc,
        [
            "เมื่อหัวหน้าเจ้าหน้าที่ลงนามแล้ว ผู้อำนวยการ (uat.director) จึงเห็นรายงานแล้วลงนามเป็นลำดับสุดท้าย",
        ],
        start=14,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_director.png",
        12.0,
        "ภาพที่ 74  ผู้ลงนามผู้อำนวยการโรงพยาบาลในรายงานขออนุมัติ",
    )
    steps(
        doc,
        [
            "ครั้งถัดไปบนใบเดียวกัน ปุ่มจะเปลี่ยนเป็นเปิดหนังสือขออนุมัติจัดซื้อจัดจ้าง ไม่สร้างเอกสารซ้ำ",
        ],
        start=15,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_open.png",
        12.0,
        "ภาพที่ 75  ปุ่มเปิดหนังสือขออนุมัติจัดซื้อจัดจ้าง",
    )
    make_table(
        doc,
        ["ปุ่ม / จุดที่กด", "ใช้ทำอะไร"],
        [
            [
                "ออกหนังสือขออนุมัติจัดซื้อจัดจ้าง",
                "สร้างรายงานขออนุมัติจากใบขอซื้อ วิธีตามที่เลือกในใบขอซื้อ",
            ],
            [
                "เปิดหนังสือขออนุมัติจัดซื้อจัดจ้าง",
                "เปิดรายงานที่ออกแล้วของใบนี้ ไม่สร้างใหม่",
            ],
            [
                "ดึงรายชื่อจากแท็บคณะกรรมการ",
                "รีเฟรชกรรมการตรวจรับให้ตรงกับใบขอซื้อ",
            ],
            ["สร้างข้อความจากข้อมูล", "สร้างเรื่อง ข้อ ๒ จากรายการสินค้า และข้อ ๑-๑๐ ตามข้อมูลล่าสุด"],
            ["ขอเลขจากระบบสารบรรณ", "ใช้เลขเดียวกับปุ่มขอเลขสารบรรณบนใบขอซื้อ สำหรับรายงานขออนุมัติ"],
            ["สร้างไฟล์ Word", "สร้างไฟล์ .docx จากกล่องข้อ ๒ โดยไม่มีตารางรายการ แล้วดาวน์โหลด"],
            [
                "พิมพ์ PDF",
                "สร้าง Word ใหม่จากกล่องข้อ ๒ แล้วแปลงเป็น PDF เปิดดูได้ ข้อ ๒ ไม่มีตารางรายการ",
            ],
            [
                "ส่งเพื่อลงนาม",
                "ส่งเข้ากล่องงานรออนุมัติตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ แล้วผู้อำนวยการ",
            ],
        ],
        [7.6, 8.6],
    )
    callout(
        doc,
        "ข้อ ๒ เป็นข้อความ ไม่ใช่ตาราง",
        "บนหน้าจอรายงานมีกล่องข้อความข้อ ๒ อย่างเดียว เมื่อกดพิมพ์ PDF ระบบสร้างไฟล์ Word ชุดใหม่จากกล่องนี้แล้วแปลงเป็น PDF "
        "ไฟล์ที่พิมพ์จึงไม่มีตารางลำดับ รายการ จำนวน หน่วย ราคาต่อหน่วย "
        "ถ้าเปิดไฟล์เก่าแล้วยังเห็นตาราง ให้ปิดแล้วกด พิมพ์ PDF อีกครั้ง",
        "ok",
    )
    callout(
        doc,
        "วิธีตามที่เลือกในใบขอซื้อ",
        "รายงานชุดนี้ดึงวิธีการจัดซื้อจัดจ้างจากใบขอซื้อ จึงอาจเป็นเฉพาะเจาะจง อีบิดดิ้ง คัดเลือก หรือวิธีอื่น "
        "ใบขอซื้อหนึ่งใบออกได้หนึ่งฉบับ ถ้าต้องการออกใหม่ ให้ยกเลิกฉบับเดิมก่อน "
        "เมนูสำรองอยู่ที่ จัดซื้อและผู้ขาย → หนังสือราชการ → รายงานขออนุมัติจัดซื้อจัดจ้าง",
        "info",
    )
    heading(doc, "ข้อมูลตัวอย่าง — ผู้ลงนามรายงานขออนุมัติ", 3)
    make_table(
        doc,
        ["ลำดับลงนาม", "บัญชีฝึกอบรม", "ชื่อที่ปรากฏ"],
        [
            ["1 เจ้าหน้าที่", "uat.officer", "ผู้ทดสอบเจ้าหน้าที่"],
            ["2 หัวหน้าเจ้าหน้าที่", "uat.head_officer", "ผู้ทดสอบหัวหน้าเจ้าหน้าที่"],
            ["3 ผู้อำนวยการโรงพยาบาล", "uat.director", "ผู้ทดสอบผู้อำนวยการโรงพยาบาล"],
        ],
        [4.8, 4.4, 7.0],
    )
    callout(
        doc,
        "ลงนามตามลำดับ ห้ามข้ามขั้น",
        "ผู้อำนวยการยังไม่เห็นรายงานขออนุมัติจนกว่าเจ้าหน้าที่และหัวหน้าเจ้าหน้าที่ลงนามครบ "
        "คำสั่งแต่งตั้งคณะกรรมการตรวจรับส่งให้ผู้อำนวยการลงนามโดยตรง ไม่ผ่านเจ้าหน้าที่ "
        "เมื่อคำสั่งแต่งตั้งและรายงานขออนุมัติลงนามครบ ระบบอนุมัติใบขอซื้อให้อัตโนมัติ "
        "แบบแสดงความบริสุทธิ์ใจลงนามแยกต่างหาก ไม่ผูกกับการอนุมัติใบขอซื้อ",
        "warn",
    )
    body(
        doc,
        "ตัวอย่างด้านล่างคือรายงานขออนุมัติที่พิมพ์จากระบบ ทั้ง 3 หน้า "
        "ข้อ ๒ เป็นข้อความจากกล่อง ไม่ใช่ตาราง วงเงิน 1,000 บาท "
        "กรรมการตรวจรับเป็นชุดฝึกอบรม คนที่ 1–3 "
        "และลงนามโดยผู้ทดสอบเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และผู้อำนวยการโรงพยาบาล",
    )
    picture(
        doc,
        "Screenshot_approval_PR6909001_p1.png",
        14.8,
        "ภาพที่ 76  ตัวอย่างรายงานขออนุมัติจัดซื้อจัดจ้าง ที่พิมพ์จากระบบ (หน้าแรก)",
    )
    picture(
        doc,
        "Screenshot_approval_PR6909001_p2.png",
        14.8,
        "ภาพที่ 77  ตัวอย่างรายงานขออนุมัติจัดซื้อจัดจ้าง (หน้าที่สอง รายชื่อกรรมการตรวจรับ)",
    )
    picture(
        doc,
        "Screenshot_approval_PR6909001_p3.png",
        14.8,
        "ภาพที่ 78  ตัวอย่างรายงานขออนุมัติจัดซื้อจัดจ้าง (หน้าลงนาม)",
    )
    heading(doc, "หลังกดส่งอนุมัติ — งานรออนุมัติของฉัน", 3)
    body(
        doc,
        "เมื่อพัสดุกดส่งเพื่อลงนาม หรือกดส่งอนุมัติ รายการจะไปปรากฏในกล่อง "
        "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน ของผู้ที่ถึงลำดับลงนาม "
        "ตัวอย่างด้านล่างคือแดชบอร์ดงานรออนุมัติของเจ้าหน้าที่ (uat.officer) หลังส่งแล้ว "
        "จะเห็นทั้งแบบแสดงความบริสุทธิ์ใจ และรายงานขออนุมัติจัดซื้อจัดจ้าง เป็นขั้นที่ 1 "
        "หัวหน้าเจ้าหน้าที่และผู้อำนวยการจะเห็นรายการในกล่องนี้เมื่อถึงลำดับของตน ห้ามข้ามขั้น",
    )
    picture(
        doc,
        "Screenshot_my_approvals_inbox.png",
        16.2,
        "ภาพที่ 79  หลังกดส่งอนุมัติ รายการไปปรากฏในกล่องงานรออนุมัติของฉัน",
    )
    heading(doc, "เปิดเอกสารลงนามจากระบบ", 3)
    body(
        doc,
        "จากกล่องงานรออนุมัติของฉัน กดเปิด PDF ของรายการที่ถึงลำดับของตน "
        "ระบบเปิดไฟล์เอกสารด้านหลัง แล้วกดปุ่ม ลงนาม ที่มุมล่างขวา "
        "หน้าต่าง ใช้ลายเซ็นของคุณ จะให้วาดลายเซ็น หรือโหลดรูปลายเซ็น "
        "ตรวจข้อความแล้วยอมรับและลงนาม ลายเซ็นจะประทับบนไฟล์ PDF ตามชื่อผู้ลงนามในเอกสาร "
        "ถ้ายังไม่ถึงลำดับ ปุ่มลงนามจะยังใช้ไม่ได้",
    )
    steps(
        doc,
        [
            "กดกล่องรายการ หรือกด เปิด PDF จากงานรออนุมัติของฉัน",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_sign_step_open_pdf.png",
        16.2,
        "ภาพที่ 80  กล่องงานรออนุมัติของฉันและปุ่มเปิด PDF",
    )
    steps(
        doc,
        [
            "เลื่อนดูเอกสารให้ครบ แล้วกดปุ่ม ลงนาม",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_sign_step_sign_btn.png",
        16.2,
        "ภาพที่ 81  แถบล่างของหน้าต่างเอกสารและปุ่มลงนาม",
    )
    steps(
        doc,
        [
            "เลือก วาด เพื่อลงลายเซ็นด้วยมือ หรือ โหลด เพื่อใช้ไฟล์รูปลายเซ็น",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_sign_step_draw.png",
        14.0,
        "ภาพที่ 82  หน้าต่างใช้ลายเซ็นของคุณ แท็บวาดและโหลด",
    )
    steps(
        doc,
        [
            "อ่านข้อความยอมรับแล้วกด ยอมรับและลงนาม",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_sign_step_accept.png",
        8.0,
        "ภาพที่ 83  ปุ่มยอมรับและลงนาม",
    )
    steps(
        doc,
        [
            "ถ้าไม่ต้องการลงนาม ให้กด ยกเลิก หรือ ไม่อนุมัติ ตามสิทธิ์ของรายการนั้น",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_sign_step_cancel.png",
        10.0,
        "ภาพที่ 84  ปุ่มยกเลิก และปุ่มไม่อนุมัติ",
    )
    heading(doc, "รูปแบบที่แสดงผลในแอปมือถือ", 3)
    body(
        doc,
        "ผู้ลงนามดูและอนุมัติชุดเดียวกันจากแอปมือถือได้ แยกแท็บ รออนุมัติ กับ อนุมัติแล้ว "
        "แต่ละการ์ดแสดงประเภทเอกสาร สถานะ เลขใบขอซื้อ เลขที่หนังสือ ผู้ส่ง ผู้ลงนาม "
        "สถานะเอกสาร และวันที่ตรวจ กดการ์ดเพื่อดูรายละเอียดหรือเปิด PDF "
        "ตัวอย่างด้านล่างคือหน้าจอผู้อำนวยการโรงพยาบาล แท็บอนุมัติแล้ว "
        "คำสั่งแต่งตั้งคณะกรรมการตรวจรับเป็นอนุมัติแล้ว "
        "รายงานขออนุมัติจัดซื้อจัดจ้างที่ยังรอลงนามจะแสดงสถานะรออนุมัติจนกว่าจะลงนามครบ",
    )
    make_table(
        doc,
        ["จุดที่เห็นในแอป", "ความหมาย"],
        [
            ["แท็บรออนุมัติ", "รายการที่ถึงลำดับของตน ยังไม่ได้ลงนาม"],
            ["แท็บอนุมัติแล้ว", "รายการที่ตนลงนามแล้ว หรือประวัติที่เกี่ยวกับตน"],
            ["ประเภทเอกสาร", "เช่น คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ รายงานขออนุมัติจัดซื้อจัดจ้าง"],
            ["เลขที่ / อ้างอิง", "เลขหนังสือราชการ เช่น กค/2026/0025 และเลขใบขอซื้อ PR6909003"],
            ["สถานะบนการ์ด", "รออนุมัติ หรือ อนุมัติแล้ว"],
            ["แตะเพื่อดูรายละเอียด / PDF", "เปิดเนื้อหาเอกสารและลงนามได้เมื่อถึงลำดับ"],
        ],
        [5.2, 11.0],
    )
    picture(
        doc,
        "Screenshot_mobile_approvals.png",
        8.4,
        "ภาพที่ 85  รูปแบบรายการอนุมัติในแอปมือถือ แท็บอนุมัติแล้ว",
    )

    heading(doc, "4.3.6 แท็บเอกสารราชการที่เกี่ยวข้อง", 3)
    body(
        doc,
        "แท็บนี้อยู่ถัดจากเอกสารขออนุมัติจัดซื้อจัดจ้าง "
        "ใช้ดูรายการเอกสารราชการที่ออกจากใบขอซื้อใบนี้ทั้งหมด "
        "เช่น คำสั่งแต่งตั้งคณะกรรมการตรวจรับ แบบแสดงความบริสุทธิ์ใจ "
        "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดคุณลักษณะ และรายงานขออนุมัติจัดซื้อจัดจ้าง "
        "ไม่สร้างเอกสารใหม่จากแท็บนี้ ให้กดปุ่มออกเอกสารที่แท็บเอกสารแต่งตั้งคณะกรรมการ "
        "แท็บเอกสารแสดงความบริสุทธิ์ใจ หรือแท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง",
    )
    steps(
        doc,
        [
            "เปิดแท็บเอกสารราชการที่เกี่ยวข้อง หลังออกหนังสือจากแท็บเอกสารแต่งตั้ง "
            "เอกสารแสดงความบริสุทธิ์ใจ หรือเอกสารขออนุมัติแล้ว",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_official_open.png",
        16.2,
        "ภาพที่ 86  แท็บเอกสารราชการที่เกี่ยวข้องและรายการหนังสือที่ออกจากใบขอซื้อ",
    )
    steps(
        doc,
        [
            "ตรวจรายการว่ามีประเภทเอกสาร เลขที่ เลขที่จากสารบรรณ วันที่ เรื่อง สถานะการลงนาม และสถานะเอกสารครบตามที่ออกจริง",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_official_columns.png",
        16.2,
        "ภาพที่ 87  คอลัมน์ประเภท เลขที่ เลขสารบรรณ วันที่ เรื่อง และสถานะในรายการ",
    )
    steps(
        doc,
        [
            "กดแถวเอกสารเพื่อเปิดดู แล้วกด ขอเลขจากระบบสารบรรณ ที่หัวเอกสารนั้น ถ้าเป็นรายงานขออนุมัติจะใช้เลขจากใบขอซื้อ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_official_open_row.png",
        16.2,
        "ภาพที่ 88  เปิดเอกสารจากแถวแล้วตรวจช่องเลขที่จากสารบรรณและปุ่มขอเลข",
    )
    make_table(
        doc,
        ["คอลัมน์ที่เห็น", "ความหมาย"],
        [
            ["ประเภท", "ชนิดหนังสือราชการที่ออกจากใบนี้"],
            ["เลขที่เอกสาร", "เลขที่หนังสือในระบบ"],
            ["เลขที่จากสารบรรณ", "เลขที่ไปแสดงที่ช่อง ที่ ในไฟล์ที่พิมพ์ แต่ละเอกสารคนละเลข ยกเว้นรายงานขออนุมัติที่ใช้เลขจากใบขอซื้อ"],
            ["วันที่", "วันที่บนเอกสาร"],
            ["เรื่อง", "ชื่อเรื่องที่ระบบเติมจากใบขอซื้อ"],
            ["สถานะการลงนาม", "ยังไม่ส่งลงนาม / รอลงนาม / ลงนามแล้ว"],
            ["สถานะ", "ร่าง / สร้างไฟล์แล้ว / รออนุมัติ / อนุมัติแล้ว / ยกเลิก"],
        ],
        [5.2, 11.0],
    )
    callout(
        doc,
        "แท็บเอกสารขออนุมัติมีแค่รายงานขออนุมัติ",
        "แท็บเอกสารขออนุมัติจัดซื้อจัดจ้างแสดงเฉพาะรายงานขออนุมัติจัดซื้อจัดจ้าง "
        "เอกสารราชการอื่นของใบเดียวกันไปดูที่แท็บเอกสารราชการที่เกี่ยวข้อง",
        "info",
    )

    heading(doc, "4.3.7 แท็บตรวจสอบงบประมาณ", 3)
    body(
        doc,
        "อย่าพิมพ์ยอดคงเหลือเอง ให้กดปุ่ม เช็คงบประมาณ ที่หัวเอกสาร แล้วมาดูผลในแท็บนี้ "
        "ช่องประเภทสิ่งที่จะซื้อ หน่วยงาน กลุ่มงบ แหล่งเงิน และหมวดงบ ต้องตรงกับหัวเอกสาร",
    )
    steps(
        doc,
        [
            "ตรวจว่าหัวเอกสารและแท็บสินค้าบันทึกแล้ว",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_budget_header.png",
        16.2,
        "ภาพที่ 89  หัวเอกสารและมิติงบประมาณที่ใช้เช็คงบ",
    )
    steps(
        doc,
        [
            "กดปุ่ม เช็คงบประมาณ ที่แถบหัวเอกสาร ขณะสถานะยังเป็นร่าง",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_budget_check_btn.png",
        12.0,
        "ภาพที่ 90  ปุ่มเช็คงบประมาณที่แถบหัวเอกสารขณะเป็นร่าง",
    )
    steps(
        doc,
        [
            "เปิดแท็บตรวจสอบงบประมาณ ดูสถานะเช็คงบ ยอดที่ขอ ยอดคงเหลือ และข้อความผลตรวจ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_budget_result.png",
        16.2,
        "ภาพที่ 91  แท็บตรวจสอบงบประมาณ สถานะ ยอดจอง ยอดคงเหลือ และผลตรวจ",
    )
    steps(
        doc,
        [
            "ถ้าเป็น งบเพียงพอ จึงไปกดส่งพัสดุ แล้วจึงขออนุมัติ",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_TAB_budget_enough.png",
        16.2,
        "ภาพที่ 92  สถานะเช็คงบเป็นงบเพียงพอ พร้อมยอดจองและยอดคงเหลือ",
    )
    picture(
        doc,
        "Screenshot_TAB_budget_send.png",
        5.0,
        "ภาพที่ 93  ปุ่มส่งพัสดุหลังเช็คงบผ่าน",
    )
    steps(
        doc,
        [
            "ถ้าไม่ผ่าน ให้กลับไปแก้หัวเอกสารหรือยอดในแท็บสินค้า แล้วกดเช็คงบอีกครั้ง",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_TAB_budget_fix.png",
        16.2,
        "ภาพที่ 94  หัวเอกสารที่ต้องแก้เมื่อเช็คงบไม่ผ่าน แล้วกดเช็คงบอีกครั้ง",
    )
    make_table(
        doc,
        ["ช่องที่เห็นในแท็บ", "อ่านอย่างไร"],
        [
            ["สถานะเช็คงบ", "ยังไม่ได้เช็ค / งบเพียงพอ / งบไม่พอ"],
            ["งบประมาณที่ขอ", "รวมจากบรรทัดสินค้า"],
            ["งบคงเหลือ", "วงเงินที่ใช้ซื้อเพิ่มได้ก่อนส่งใบนี้"],
            ["จองงบประมาณแล้ว", "ติ๊กเมื่อส่งขออนุมัติแล้ว ระบบกันเงินให้"],
            ["ข้อความผลตรวจ", "บอกว่ามิติงบตรงแผนหรือไม่ และขาดอะไร"],
        ],
        [5.2, 11.0],
    )

    heading(doc, "4.4 เช็คงบประมาณ แล้วส่งพัสดุ", 2)
    steps(
        doc,
        [
            "บันทึกใบขอซื้อก่อน ระบบจะออกเลขที่ให้",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_44_save_number.png",
        10.0,
        "ภาพที่ 95  บันทึกใบขอซื้อแล้วระบบออกเลขที่ให้",
    )
    steps(
        doc,
        [
            "กดปุ่ม เช็คงบประมาณ ที่หัวเอกสาร ขณะสถานะยังเป็นร่าง",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_44_check_btn.png",
        5.0,
        "ภาพที่ 96  ปุ่มเช็คงบประมาณที่หัวเอกสารขณะเป็นร่าง",
    )
    steps(
        doc,
        [
            "ดูแท็บตรวจสอบงบประมาณ ว่ารายการเป็น งบเพียงพอ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_44_enough.png",
        16.2,
        "ภาพที่ 97  สถานะเช็คงบเป็นงบเพียงพอ",
    )
    steps(
        doc,
        [
            "ถ้าไม่ผ่าน ให้แก้หน่วยงาน แหล่งเงิน หมวด กลุ่มวัสดุ หรือยอด แล้วเช็คอีกครั้ง",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_TAB_44_fix.png",
        16.2,
        "ภาพที่ 98  หัวเอกสารที่ต้องแก้เมื่อเช็คงบไม่ผ่าน แล้วกดเช็คงบอีกครั้ง",
    )
    steps(
        doc,
        [
            "กดปุ่ม ส่งพัสดุ สถานะจะเปลี่ยนเป็น ส่งพัสดุแล้ว "
            "เจ้าหน้าที่พัสดุจะเห็นใบนี้ที่เมนู จัดซื้อ → ใบขอซื้อ → รอรับจากหน่วยงาน",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_TAB_44_send_btn.png",
        5.0,
        "ภาพที่ 99  ปุ่มส่งพัสดุหลังเช็คงบผ่าน",
    )
    picture(
        doc,
        "Screenshot_TAB_44_status_sent.png",
        12.0,
        "ภาพที่ 100  สถานะเปลี่ยนเป็น ส่งพัสดุแล้ว",
    )
    steps(
        doc,
        [
            "จากนั้นกดปุ่ม ยืนยันขอซื้อ (ขออนุมัติ) ระบบจองงบ "
            "และส่งไฟล์คำสั่งแต่งตั้งคณะกรรมการตรวจรับให้ผู้อำนวยการลงนาม "
            "พร้อมส่งรายงานขออนุมัติจัดซื้อจัดจ้างเข้าลำดับลงนาม "
            "เจ้าหน้าที่ → หัวหน้าเจ้าหน้าที่ → ผู้อำนวยการ "
            "เมื่อคำสั่งแต่งตั้งและรายงานขออนุมัติลงนามครบ ระบบจะอนุมัติใบขอซื้อให้อัตโนมัติ",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_TAB_44_confirm_btn.png",
        5.0,
        "ภาพที่ 101  ปุ่มยืนยันขอซื้อ (ขออนุมัติ) หลังส่งพัสดุ",
    )
    callout(
        doc,
        "หลังกดขออนุมัติ ให้ลงนามไฟล์เอกสารตามลำดับ ไม่ใช่กล่องใบขอซื้อ",
        "คำสั่งแต่งตั้งคณะกรรมการตรวจรับส่งเข้ากล่องงานรออนุมัติของผู้อำนวยการ (uat.director) โดยตรง "
        "รายงานขออนุมัติจัดซื้อจัดจ้างส่งให้เจ้าหน้าที่ (uat.officer) ลงนามก่อน แล้วหัวหน้าเจ้าหน้าที่ แล้วจึงผู้อำนวยการ "
        "เปิดเมนู การอนุมัติตามลำดับ → งานรออนุมัติของฉัน จะเห็นกล่องเอกสารตามลำดับของตน "
        "เมื่อลงนามครบทั้งสองฉบับ ใบขอซื้อจะเปลี่ยนเป็นอนุมัติเอง "
        "ถ้ายังไม่มีกรรมการตรวจรับในแท็บรายชื่อคณะกรรมการ ระบบจะยังไม่ให้กดขออนุมัติ "
        "ถ้าไม่อนุมัติฉบับใดฉบับหนึ่ง ระบบจะตีกลับใบขอซื้อด้วย "
        "แบบแสดงความบริสุทธิ์ใจกด ส่งเพื่อลงนาม จากแท็บของตนเอง ไม่ผูกกับปุ่มขออนุมัติใบขอซื้อ",
        "info",
    )
    callout(
        doc,
        "เช็คงบผ่าน ยังไม่เท่ากับกันเงิน",
        "เช็คงบเป็นการถามว่ารอบนี้ซื้อได้ไหม เมื่อกดขออนุมัติ ระบบจึงจองงบ "
        "ใบอื่นจะใช้วงเงินซ้ำไม่ได้จนกว่าใบนี้จะถูกยกเลิก หรือถูกครอบคลุมด้วยใบสั่งซื้อ",
        "warn",
    )
    heading(doc, "4.5 สิ่งที่หน่วยงานทำได้หลังส่ง", 2)
    make_table(
        doc,
        ["สถานะ", "หน่วยงานทำได้", "หน่วยงานทำไม่ได้"],
        [
            ["ร่าง", "แก้รายการ เช็คงบ ลบใบ กดส่งพัสดุ", "กดขออนุมัติเองไม่ได้ จนกว่าจะส่งพัสดุ"],
            ["ส่งพัสดุแล้ว", "เปิดดู และกดขออนุมัติ", "พัสดุเห็นรายการนี้แล้ว"],
            ["รออนุมัติ", "เปิดดูสถานะ", "แก้รายการหลักไม่ได้"],
            ["อนุมัติ", "เปิดดู และรอพัสดุส่งเข้า e-GP", "สร้าง PO เองไม่ได้"],
            ["ปฏิเสธ", "ตั้งเป็นร่าง แก้ แล้วส่งใหม่", "ใช้วงเงินจากใบนี้ไม่ได้จนกว่าจะอนุมัติใหม่"],
        ],
        [3.2, 6.4, 6.6],
    )
    callout(
        doc,
        "ส่งไม่ได้ เพราะอะไร",
        "ระบบจะกันการส่งถ้าเช็คงบยังไม่ผ่าน ไม่มีบรรทัดสินค้า มิติงบไม่ครบ "
        "หรือเป็นใบเร่งด่วนแต่ยังไม่ระบุเหตุผล หรือยังไม่มีบรรทัดในแท็บสินค้า ให้อ่านข้อความบนหน้าจอแล้วแก้ในใบเดิม",
        "danger",
    )

    heading(doc, "บทที่ 5 พัสดุ — นำใบขอซื้อเข้ากระบวนการ e-GP", 1)
    body(
        doc,
        "บทนี้ใช้บัญชีพัสดุ เมื่อหน่วยงานกดส่งพัสดุแล้ว เปิดเมนู จัดซื้อ → ใบขอซื้อ → รอรับจากหน่วยงาน "
        "จะเห็นใบสถานะ ส่งพัสดุแล้ว จากนั้นออกเอกสารและกดขออนุมัติได้ "
        "ส่งเข้า e-GP ได้เมื่อใบขอซื้ออนุมัติแล้ว เอกสารที่เกี่ยวข้องอนุมัติครบทุกฉบับ "
        "และประเภทการจัดซื้อเป็น จัดซื้อจัดจ้างผ่านพัสดุ "
        "อย่ากดปุ่ม สร้างใบขอเสนอราคา บนใบขอซื้อประเภทนี้ ระบบจะแจ้งให้ใช้ปุ่ม ส่งรายการเข้าระบบ e-GP แทน",
    )
    heading(doc, "5.1 รับใบขอซื้อจากหน่วยงาน", 2)
    steps(
        doc,
        [
            "เข้าเมนู จัดซื้อ → ใบขอซื้อ → รอรับจากหน่วยงาน",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_51_menu_inbox.png",
        8.0,
        "ภาพที่ 102  เมนูรอรับจากหน่วยงาน",
    )
    steps(
        doc,
        [
            "เปิดใบที่สถานะ ส่งพัสดุแล้ว",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_51_status_sent.png",
        12.0,
        "ภาพที่ 103  สถานะส่งพัสดุแล้วบนใบขอซื้อ",
    )
    steps(
        doc,
        [
            "ตรวจรายการสินค้า คณะกรรมการ และเอกสาร แล้วออกคำสั่ง แบบแสดงความบริสุทธิ์ใจ หรือรายงานตามที่ต้องใช้",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_51_tabs_docs.png",
        16.2,
        "ภาพที่ 104  แท็บสินค้า คณะกรรมการ และเอกสารบนใบขอซื้อ",
    )
    steps(
        doc,
        [
            "กดขออนุมัติเมื่อเอกสารครบ รอลงนามตามลำดับจนใบขอซื้อเป็น Approved",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_51_confirm_btn.png",
        5.0,
        "ภาพที่ 105  ปุ่มยืนยันขอซื้อ (ขออนุมัติ)",
    )
    steps(
        doc,
        [
            "เมื่อเอกสารที่เกี่ยวข้องอนุมัติครบทุกฉบับ ปุ่ม ส่งรายการเข้าระบบ e-GP จะแสดงที่หัวใบขอซื้อ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_51_egp_btn.png",
        6.0,
        "ภาพที่ 106  ปุ่มส่งรายการเข้าระบบ e-GP ที่หัวใบขอซื้อ",
    )
    heading(doc, "5.2 ส่งใบขอซื้อเข้ากระบวนการ e-GP", 2)
    steps(
        doc,
        [
            "เปิดใบขอซื้อที่อนุมัติแล้ว จากเมนู จัดซื้อ → ใบขอซื้อ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_52_menu_pr.png",
        16.2,
        "ภาพที่ 107  เมนูจัดซื้อ → ใบขอซื้อ",
    )
    steps(
        doc,
        [
            "ตรวจแท็บเอกสารราชการที่เกี่ยวข้องว่าทุกฉบับสถานะอนุมัติแล้ว",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_52_official_docs.png",
        16.2,
        "ภาพที่ 108  แท็บเอกสารราชการที่เกี่ยวข้องที่อนุมัติครบ",
    )
    steps(
        doc,
        [
            "เมื่อเอกสารครบ ปุ่ม ส่งรายการเข้าระบบ e-GP จะแสดงที่หัวใบขอซื้อ แล้วกดปุ่มนี้",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_52_egp_btn.png",
        6.0,
        "ภาพที่ 109  ปุ่มส่งรายการเข้าระบบ e-GP ที่หัวใบขอซื้อ",
    )
    steps(
        doc,
        [
            "ตรวจรายการสินค้าในหน้าต่าง กระบวนการ eGP ว่าครบตามใบขอซื้อ",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_52_wizard_lines.png",
        16.2,
        "ภาพที่ 110  หน้าต่างกระบวนการ eGP แสดงรายการสินค้าจากใบขอซื้อ",
    )
    steps(
        doc,
        [
            "กดปุ่ม กระบวนการ eGP ระบบจะสร้างเอกสารกระบวนการ e-GP จากใบขอซื้อที่อนุมัติแล้ว เพื่อดำเนินการในส่วน e-GP ต่อไป",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_52_egp_process_btn.png",
        5.0,
        "ภาพที่ 111  ปุ่มกระบวนการ eGP ในหน้าต่างยืนยัน",
    )
    steps(
        doc,
        [
            "เปิดเอกสารที่สร้างได้จากปุ่มสถิติ กระบวนการ e-GP บนใบขอซื้อ หรือจากเมนู จัดซื้อ → กระบวนการ eGP",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_52_egp_stat_btn.png",
        5.0,
        "ภาพที่ 112  ปุ่มสถิติกระบวนการ e-GP บนใบขอซื้อ",
    )
    heading(doc, "5.3 สิ่งที่ระบบสร้างให้อัตโนมัติ", 2)
    bullets(
        doc,
        [
            "เลขที่กระบวนการ e-GP รูปแบบ EGP/ปี/เลขวิ่ง เช่น EGP/2026/0001",
            "การอ้างอิงใบขอซื้อต้นทาง และวงเงินงบประมาณตามใบขอซื้อ",
            "ประเภทพัสดุ ประเภทการจัดซื้อ และวิธีการจัดซื้อจัดจ้าง ตามที่ระบุในใบขอซื้อ",
            "รายการสินค้าตามบรรทัดใบขอซื้อ",
        ],
    )
    heading(doc, "5.4 ตรวจร่างแล้วกดยืนยัน", 2)
    steps(
        doc,
        [
            "เปิดเอกสารกระบวนการ e-GP ที่เพิ่งสร้าง สถานะเป็นร่าง",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_54_draft_open.png",
        16.2,
        "ภาพที่ 113  เอกสารกระบวนการ e-GP สถานะร่าง (Draft PA)",
    )
    steps(
        doc,
        [
            "ใส่เลขที่โครงการ (e-GP) และชื่อโครงการ ตามที่ประกาศจริง",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_54_project_fields.png",
        10.0,
        "ภาพที่ 114  ฟิลด์เลขที่โครงการ (e-GP) และชื่อโครงการ",
    )
    steps(
        doc,
        [
            "ตรวจรายการสินค้า จำนวน และหน่วยนับ ห้ามยืนยันถ้ายังไม่มีบรรทัดสินค้า หรือจำนวนเป็น 0",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_54_product_lines.png",
        14.0,
        "ภาพที่ 115  แท็บสินค้า ตรวจจำนวนและหน่วยนับ",
    )
    steps(
        doc,
        [
            "กดยืนยันเอกสาร แถบขั้นตอนจะเลื่อนจากร่างไปยืนยัน",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_54_confirm_btn.png",
        6.0,
        "ภาพที่ 116  ปุ่มยืนยันเอกสารกระบวนการ e-GP",
    )
    steps(
        doc,
        [
            "ดูแถบสถานะที่หัวเอกสารว่าขั้นถัดไปคือบันทึกเอกสาร e-GP",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_54_statusbar_next.png",
        14.0,
        "ภาพที่ 117  แถบสถานะหลังยืนยัน ขั้นถัดไปคือ e-GP Documents",
    )
    callout(
        doc,
        "ยืนยันไม่ได้",
        "ระบบจะกันการยืนยันถ้ายังไม่มีรายการสินค้า หรือมีบรรทัดที่จำนวนน้อยกว่าหรือเท่ากับศูนย์ "
        "ให้กลับไปแก้ในเอกสารร่างก่อน",
        "danger",
    )

    heading(doc, "บทที่ 6 ดำเนินการ e-GP จนได้ผู้ชนะ", 1)
    body(
        doc,
        "หลังยืนยันเอกสารแล้ว พัสดุทำงานในแท็บของกระบวนการ e-GP ตามลำดับ "
        "อย่าข้ามไปสร้าง PO ก่อนเลือกผู้ชนะและอนุมัติรายงานผล",
    )
    picture(doc, "fig_proc_egp_steps.png", 16.2, "ภาพที่ 118  ขั้นตอนในกระบวนการ e-GP")
    heading(doc, "6.1 บันทึกเอกสาร e-GP", 2)
    body(
        doc,
        "เปิดแท็บเอกสาร e-GP แล้วเพิ่มบรรทัดตามประเภทเอกสารที่มี "
        "ใส่เลขที่อ้างอิง วันที่ และแนบไฟล์ แล้วบันทึก",
    )
    make_table(
        doc,
        ["ประเภทเอกสาร", "ใช้เมื่อ"],
        [
            ["ประกาศร่าง", "มีประกาศร่าง TOR / ร่างประกาศ"],
            ["ประกาศเชิญชวน", "มีประกาศเชิญชวน เลขที่โครงการ e-GP มักดึงจากบรรทัดนี้"],
            ["ประกาศผู้ชนะ", "หลังคัดเลือกผู้ชนะแล้ว"],
            ["TOR", "แนบขอบเขตงาน / รายละเอียดคุณลักษณะ"],
            ["สัญญา", "เมื่อมีร่างสัญญาหรือสัญญา"],
        ],
        [5.0, 11.2],
    )
    heading(doc, "6.2 เชิญเสนอราคาและรับข้อเสนอ", 2)
    steps(
        doc,
        [
            "เปิดแท็บเชิญเสนอราคา แล้วเพิ่มบรรทัดผู้ประกอบการที่เชิญ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_62_invite_tab.png",
        16.2,
        "ภาพที่ 119  แท็บเชิญเสนอราคา และปุ่มเพิ่มรายการ",
    )
    steps(
        doc,
        [
            "เปิดใบเชิญแต่ละราย ตรวจสินค้า วันที่เชิญ และกำหนดยื่น แล้วกด บันทึกส่งคำเชิญ",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_62_invite_form.png",
        14.0,
        "ภาพที่ 120  ใบเชิญเสนอราคา ตรวจรายละเอียดแล้วกดบันทึกส่งคำเชิญ",
    )
    steps(
        doc,
        [
            "เมื่อได้รับข้อเสนอ กด ได้รับข้อเสนอ / บันทึกราคา หรือปุ่ม รับข้อเสนอ จากรายการ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_62_respond_btn.png",
        14.0,
        "ภาพที่ 121  ปุ่มได้รับข้อเสนอ / บันทึกราคา บนใบเชิญที่ส่งแล้ว",
    )
    steps(
        doc,
        [
            "ระบบจะสร้างข้อเสนอราคาให้นำไปบันทึกในแท็บเปรียบเทียบราคา",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_62_compare_bids.png",
        16.2,
        "ภาพที่ 122  แท็บเปรียบเทียบราคา แสดงข้อเสนอที่สร้างจากใบเชิญ",
    )
    steps(
        doc,
        [
            "พิมพ์ใบเชิญได้จากปุ่ม พิมพ์ใบเชิญ ถ้าต้องส่งเป็นเอกสาร",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_62_print_btn.png",
        6.0,
        "ภาพที่ 123  ปุ่มพิมพ์ใบเชิญ",
    )
    heading(doc, "6.3 เปรียบเทียบราคาและเลือกผู้ชนะ", 2)
    steps(
        doc,
        [
            "เปิดแท็บเปรียบเทียบราคา ตรวจผู้เสนอราคา เลขที่ใบเสนอราคา วันที่ และราคาที่เสนอ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_63_compare_tab.png",
        16.2,
        "ภาพที่ 124  แท็บเปรียบเทียบราคา ตรวจผู้เสนอราคาและราคาที่เสนอ",
    )
    steps(
        doc,
        [
            "เปิดรายละเอียดข้อเสนอเพื่อใส่ราคารายบรรทัดถ้าจำเป็น",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_63_bid_detail.png",
        14.0,
        "ภาพที่ 125  รายละเอียดข้อเสนอราคาและรายการราคา",
    )
    steps(
        doc,
        [
            "ติ๊กช่องผู้ชนะที่รายที่ได้รับการคัดเลือก ระบบอนุญาตผู้ชนะได้ทีละ 1 ราย",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_63_winner_check.png",
        14.0,
        "ภาพที่ 126  ติ๊กช่องผู้ชนะในแท็บเปรียบเทียบราคา",
    )
    steps(
        doc,
        [
            "เมื่อมีผู้ชนะแล้ว แถบขั้นตอนจะเลื่อนไปเลือกผู้ชนะ",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_63_award_statusbar.png",
        12.0,
        "ภาพที่ 127  แถบสถานะหลังเลือกผู้ชนะ (Award Vendor)",
    )
    callout(
        doc,
        "ยังสร้าง PO ไม่ได้ตอนนี้",
        "แม้ติ๊กผู้ชนะแล้ว ปุ่มสร้าง RFQ/PO ผู้ชนะจะยังไม่พร้อมจนกว่าจะจัดทำและอนุมัติ "
        "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง",
        "warn",
    )
    heading(doc, "6.4 จัดทำรายงานผลและประกาศผู้ชนะ", 2)
    steps(
        doc,
        [
            "กดปุ่ม จัดทำรายงานผลและขออนุมัติ ในแท็บเปรียบเทียบราคา",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_64_create_report_btn.png",
        10.0,
        "ภาพที่ 128  ปุ่มจัดทำรายงานผลและขออนุมัติ ในแท็บเปรียบเทียบราคา",
    )
    steps(
        doc,
        [
            "ตรวจเรื่อง เกณฑ์การพิจารณา ข้อเสนอที่ได้รับการคัดเลือก และวงเงินที่ขออนุมัติ",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_64_report_fields.png",
        14.0,
        "ภาพที่ 129  รายงานผลการพิจารณา ตรวจเรื่อง เกณฑ์ และวงเงินที่ขออนุมัติ",
    )
    steps(
        doc,
        [
            "กด สร้างรายการจากข้อเสนอ eGP ถ้าตารางผลการพิจารณายังว่าง",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_64_generate_lines_btn.png",
        7.0,
        "ภาพที่ 130  ปุ่มสร้างรายการจากข้อเสนอ eGP",
    )
    steps(
        doc,
        [
            "กด ส่งขออนุมัติ จากนั้นผู้อนุมัติที่มีสิทธิ์กด อนุมัติ",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_64_submit_approve_btn.png",
        12.0,
        "ภาพที่ 131  ปุ่มส่งขออนุมัติ และปุ่มอนุมัติ",
    )
    steps(
        doc,
        [
            "ถ้าต้องประกาศ กด สร้างประกาศผู้ชนะ แล้วกด เผยแพร่ประกาศ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_64_publish_winner.png",
        12.0,
        "ภาพที่ 132  ปุ่มสร้างประกาศผู้ชนะ และปุ่มเผยแพร่ประกาศ",
    )
    make_table(
        doc,
        ["เอกสาร", "เลขที่ตัวอย่าง", "สถานะที่ต้องได้ก่อนเปิด PO"],
        [
            ["รายงานผลการพิจารณา", "AR-EGP/2026/0001", "อนุมัติแล้ว"],
            ["ประกาศผู้ชนะ", "WIN-EGP/2026/0001", "เผยแพร่แล้ว (ถ้าใช้ประกาศ)"],
            ["ใบเชิญเสนอราคา", "INV-EGP/2026/0001", "ได้รับข้อเสนอแล้วอย่างน้อยรายผู้ชนะ"],
        ],
        [5.2, 4.8, 6.2],
    )

    heading(doc, "บทที่ 7 เปิดใบสั่งซื้อ (PO) เมื่อได้ผู้ชนะ", 1)
    body(
        doc,
        "เปิด PO ได้จากเอกสารกระบวนการ e-GP หรือจากใบขอซื้อต้นทาง "
        "เมื่อปุ่ม สร้าง RFQ/PO ผู้ชนะ แสดงขึ้น แสดงว่าเงื่อนไขครบแล้ว",
    )
    picture(doc, "fig_proc_po.png", 16.2, "ภาพที่ 133  เงื่อนไขและลำดับการเปิด PO")
    heading(doc, "7.1 เงื่อนไขที่ต้องครบก่อนกดปุ่ม", 2)
    bullets(
        doc,
        [
            "กระบวนการ e-GP ยืนยันแล้ว",
            "มีข้อเสนอราคาที่ติ๊กเป็นผู้ชนะ",
            "รายงานผลการพิจารณาได้รับอนุมัติแล้ว",
        ],
        numbered=True,
    )
    heading(doc, "7.2 สร้าง RFQ/PO ผู้ชนะ", 2)
    steps(
        doc,
        [
            "เปิดกระบวนการ e-GP หรือเปิดใบขอซื้อต้นทาง แล้วกด สร้าง RFQ/PO ผู้ชนะ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_72_create_rfq_btn.png",
        7.0,
        "ภาพที่ 134  ปุ่มสร้าง RFQ/PO ผู้ชนะ บนกระบวนการ e-GP",
    )
    steps(
        doc,
        [
            "ตรวจหน้าต่างว่าผู้ขายคือผู้ชนะที่เลือกไว้ เปลี่ยนเป็นรายอื่นไม่ได้",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_72_wizard_vendor.png",
        12.0,
        "ภาพที่ 135  หน้าต่างสร้าง RFQ/PO แสดงผู้ขายผู้ชนะ (เปลี่ยนรายอื่นไม่ได้)",
    )
    steps(
        doc,
        [
            "ใส่เลขอ้างอิงใบเสนอราคา e-GP ถ้ามี แล้วกด สร้าง RFQ/PO ผู้ชนะ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_72_wizard_form.png",
        12.0,
        "ภาพที่ 136  กรอกเลขอ้างอิงใบเสนอราคา e-GP แล้วกดสร้าง RFQ/PO ผู้ชนะ",
    )
    steps(
        doc,
        [
            "ระบบสร้างใบสั่งซื้อโดยดึงสินค้าและจำนวนจากใบขอซื้อ และดึงราคาจากข้อเสนอผู้ชนะ",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_72_po_lines.png",
        14.0,
        "ภาพที่ 137  รายการสินค้าในใบสั่งซื้อที่สร้างจากผู้ชนะ",
    )
    steps(
        doc,
        [
            "ตรวจคลังรับของให้ตรงประเภท Receipt ที่ระบุในใบขอซื้อ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_72_picking_type.png",
        14.0,
        "ภาพที่ 138  ช่องส่งถึง (คลังรับของ) เช่น คลังกลาง: Receipts",
    )
    steps(
        doc,
        [
            "ยังไม่ต้องยืนยันใบสั่งซื้อในขั้นนี้ ให้พิมพ์ไฟล์และส่งเข้าแอปผู้ขายตามข้อ 7.4",
        ],
        start=6,
    )
    callout(
        doc,
        "สร้างซ้ำไม่ได้",
        "ถ้ามี RFQ/PO ของผู้ขายรายนี้ในกระบวนการเดียวกันอยู่แล้ว ระบบจะกันการสร้างซ้ำ "
        "ให้เปิดเอกสารเดิมจากปุ่มสถิติใบสั่งซื้อ อย่าสร้างใหม่ด้วยมือ",
        "warn",
    )
    heading(doc, "7.3 สิ่งที่ต้องเห็นหลังยืนยัน PO", 2)
    make_table(
        doc,
        ["จุดที่ตรวจ", "ผลที่ต้องเห็น"],
        [
            ["ใบสั่งซื้อ", "ผู้ขายเป็นผู้ชนะ สินค้าจำนวนตรงใบขอซื้อ ราคาตรงข้อเสนอผู้ชนะ"],
            ["ใบขอซื้อต้นทาง", "สถานะออกใบสั่งซื้อแล้ว / มีเอกสาร PO อ้างอิง"],
            ["กระบวนการ e-GP", "มี RFQ/PO ของผู้ชนะ ขั้นงานเลื่อนไปเลือกผู้ชนะหรือปิดงาน"],
            ["งบประมาณ", "ยอดจอง PR ลด ยอดผูกพัน PO เพิ่ม คงเหลือไม่เปลี่ยน ณ จุดยืนยัน PO"],
        ],
        [5.0, 11.2],
    )
    heading(doc, "7.4 ส่งใบสั่งซื้อของผู้ชนะให้ผู้ขายยืนยัน", 2)
    body(
        doc,
        "หลังสร้างใบสั่งซื้อของผู้ชนะแล้ว พัสดุส่งไฟล์ใบสั่งซื้อเข้าแอปผู้ขาย "
        "ทำจากใบขอซื้อต้นทาง แท็บ ใบสั่งซื้อ ซึ่งอยู่ถัดจากแท็บเอกสารราชการที่เกี่ยวข้อง "
        "ผู้ขายเห็นเฉพาะใบที่ส่งเข้าแอป เมื่อลงลายเซ็นและกดบันทึก สถานะบนใบสั่งซื้อจะกลับมาเป็น ผู้ขายยืนยันแล้ว",
    )
    callout(
        doc,
        "อย่ายืนยันใบสั่งซื้อเองก่อนส่ง",
        "ถ้าต้องการให้ผู้ขายเป็นผู้ลงนามยืนยัน อย่ากด ยืนยันการสั่งซื้อ ก่อนส่ง "
        "ใบต้องยังเป็นฉบับร่างหรือสถานะส่งแล้ว เมื่อผู้ขายบันทึกลายเซ็น ระบบจะยืนยันใบสั่งซื้อให้ "
        "และยอดงบย้ายจากจองใบขอซื้อเป็นผูกพันใบสั่งซื้อ",
        "warn",
    )
    heading(doc, "7.4.1 พิมพ์ไฟล์ใบสั่งซื้อ", 3)
    steps(
        doc,
        ["เปิดใบขอซื้อต้นทางของงานนี้ ด้วยบัญชีพัสดุ"],
        start=1,
    )
    picture(
        doc,
        "Screenshot_741_open_pr.png",
        15.2,
        "ภาพที่ 139  เปิดใบขอซื้อต้นทาง เลขที่เอกสารอยู่ที่หัวหน้าจอ",
    )
    steps(
        doc,
        ["เปิดแท็บ ใบสั่งซื้อ ตรวจว่าแถวที่เห็นเป็นใบของผู้ชนะ เลขที่ตรงใบที่เพิ่งสร้าง"],
        start=2,
    )
    picture(
        doc,
        "Screenshot_741_po_row.png",
        15.2,
        "ภาพที่ 140  แท็บใบสั่งซื้อ แถวของผู้ชนะ เลขที่ตรงใบที่สร้าง คอลัมน์ไฟล์ยังว่าง",
    )
    steps(
        doc,
        [
            "ถ้าคอลัมน์ไฟล์ยังไม่มีไอคอน PDF ให้กด พิมพ์ PDF ที่แถวนั้น ระบบบันทึกไฟล์ไว้ในรายการ ไม่ได้ดาวน์โหลดแยก",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_741_print.png",
        15.2,
        "ภาพที่ 141  ก่อนมีไฟล์ สถานะยังไม่ส่ง และมีปุ่มพิมพ์ PDF",
    )
    steps(
        doc,
        ["เมื่อมีไฟล์แล้ว ปุ่ม ส่งเข้าแอปผู้ขาย จะแสดงที่แถวเดียวกัน"],
        start=4,
    )
    picture(
        doc,
        "Screenshot_741_send.png",
        15.2,
        "ภาพที่ 142  เมื่อมีไฟล์แล้ว ปุ่มส่งเข้าแอปผู้ขายแสดงในแถวเดียวกัน",
    )
    heading(doc, "7.4.2 ส่งเข้าแอปผู้ขาย", 3)
    steps(
        doc,
        [
            "ตรวจว่าผู้ขายมีบัญชีแอปผู้ขาย (User Portal) แล้ว ถ้ายังไม่มี ให้สร้างจากปุ่ม สร้าง User Portal บนใบสั่งซื้อ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_742_portal.png",
        15.2,
        "ภาพที่ 143  ปุ่มสร้าง User Portal บนใบสั่งซื้อ ใช้เมื่อผู้ขายยังไม่มีบัญชีแอป",
    )
    steps(
        doc,
        ["กด ส่งเข้าแอปผู้ขาย บนแถวใบสั่งซื้อ"],
        start=2,
    )
    picture(
        doc,
        "Screenshot_742_send.png",
        15.2,
        "ภาพที่ 144  กดส่งเข้าแอปผู้ขายที่แถวใบสั่งซื้อ ขณะสถานะยังไม่ส่ง",
    )
    steps(
        doc,
        ["เมื่อส่งสำเร็จ สถานะการยืนยันเปลี่ยนจาก ยังไม่ส่ง เป็น รอผู้ขายยืนยัน"],
        start=3,
    )
    picture(
        doc,
        "Screenshot_742_waiting.png",
        15.2,
        "ภาพที่ 145  หลังส่งแล้ว สถานะการยืนยันเป็นรอผู้ขายยืนยัน",
    )
    steps(
        doc,
        [
            "ผู้ขายเปิดแอป ระบบบริการผู้จำหน่าย ด้วยบัญชี User Portal จะเห็นการ์ดรอยืนยันและยืนยันแล้ว",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_742_vendor_app.png",
        10.5,
        "ภาพที่ 146  แอป ระบบบริการผู้จำหน่าย ของผู้ขาย มีการ์ดรอยืนยันสำหรับเปิดเอกสารที่จัดซื้อส่งมา",
    )
    steps(
        doc,
        ["กดการ์ด รอยืนยัน แล้วแตะใบสั่งซื้อในรายการ เพื่อเปิดเอกสารและดูไฟล์ PDF"],
        start=5,
    )
    picture(
        doc,
        "Screenshot_742_vendor_open.png",
        10.5,
        "ภาพที่ 147  เปิดใบสั่งซื้อในแอป เห็นไฟล์ PDF และปุ่มลงนามยืนยัน",
    )
    steps(
        doc,
        ["กด ลงนามยืนยัน แล้วลงลายเซ็นในกรอบ ถ้าเส้นไม่ชัดให้กด ล้าง แล้วลงใหม่"],
        start=6,
    )
    picture(
        doc,
        "Screenshot_742_vendor_sign.png",
        10.5,
        "ภาพที่ 148  หน้าลงลายเซ็นเพื่อยืนยันใบสั่งซื้อ มีกรอบลงนาม และปุ่มล้าง ยกเลิก บันทึก",
    )
    steps(
        doc,
        [
            "กด บันทึก สถานะในแอปเป็นยืนยันแล้ว และบนใบสั่งซื้อในระบบกลับมาเป็นผู้ขายยืนยันแล้ว โดยฝ่ายจัดซื้อไม่ต้องกดยืนยันซ้ำ",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_742_vendor_save.png",
        14.0,
        "ภาพที่ 149  ปุ่มล้าง ยกเลิก และบันทึก หลังลงลายเซ็นให้กดบันทึก",
    )
    picture(
        doc,
        "Screenshot_742_confirmed.png",
        15.2,
        "ภาพที่ 150  หลังผู้ขายกดบันทึกในแอป สถานะการยืนยันเป็นผู้ขายยืนยันแล้ว และสถานะใบสั่งซื้อเป็นคำสั่งซื้อ",
    )
    callout(
        doc,
        "ผู้ขายยืนยันที่ไหน",
        "ผู้ขายทำในแอป ระบบบริการผู้จำหน่าย เท่านั้น "
        "เปิดใบที่อยู่ในการ์ดรอยืนยัน ลงลายเซ็น แล้วกดบันทึก "
        "สถานะยืนยันจะกลับมาที่ใบสั่งซื้อในระบบ",
        "info",
    )
    heading(doc, "7.4.3 สิ่งที่ต้องเห็นหลังผู้ขายยืนยัน", 3)
    make_table(
        doc,
        ["จุดที่ตรวจ", "ผลที่ต้องเห็น"],
        [
            ["แท็บใบสั่งซื้อ บนใบขอซื้อ", "สถานะการยืนยันเป็น ผู้ขายยืนยันแล้ว (ป้ายสีเขียว)"],
            ["ใบสั่งซื้อ แท็บใบสั่งซื้อ VPK", "สถานะการยืนยันเป็น ผู้ขายยืนยันแล้ว และเปิดไฟล์ PDF ได้"],
            ["สถานะใบสั่งซื้อ", "เป็น Purchase Order ไม่ใช่ใบขอเสนอราคา"],
            ["ปุ่มส่งเข้าแอปผู้ขาย", "ไม่แสดงซ้ำ เพราะส่งเข้าแอปแล้ว"],
        ],
        [5.4, 10.8],
    )
    picture(
        doc,
        "Screenshot_74_confirmed_badge.png",
        15.2,
        "ภาพที่ 151  หลังผู้ขายยืนยัน ป้ายสถานะเป็นผู้ขายยืนยันแล้ว และสถานะใบสั่งซื้อเป็นคำสั่งซื้อ",
    )
    picture(
        doc,
        "Screenshot_74_vpk_file.png",
        14.0,
        "ภาพที่ 152  แท็บใบสั่งซื้อ VPK แสดงชื่อไฟล์ สถานะผู้ขายยืนยันแล้ว และปุ่มเปิดไฟล์ PDF",
    )
    heading(doc, "7.5 ปิดกระบวนการ e-GP", 2)
    body(
        doc,
        "เมื่อเลือกผู้ชนะและเปิด PO แล้ว หากนโยบายให้ปิดงาน กด ปิดข้อตกลง (เลือกผู้ชนะแล้ว) "
        "ในแท็บเปรียบเทียบราคา ระบบจะปิดได้เมื่อมีผู้ชนะแล้ว",
    )

    heading(doc, "บทที่ 8 ข้อผิดพลาดที่พบบ่อย", 1)
    picture(doc, "fig_proc_do_dont.png", 16.2, "ภาพที่ 153  สิ่งที่ควรทำและไม่ควรทำ")
    make_table(
        doc,
        ["อาการ", "สาเหตุที่พบบ่อย", "วิธีแก้"],
        [
            [
                "กดขออนุมัติ PR ไม่ได้",
                "ยังไม่ได้เช็คงบ หรือผลเป็นงบไม่พอ",
                "กดเช็คงบประมาณ แก้ยอดหรือมิติงบ แล้วส่งใหม่",
            ],
            [
                "เช็คงบไม่เจอวงเงิน",
                "หน่วยงาน แหล่งเงิน หมวด หรือกลุ่มวัสดุไม่ตรงแผน",
                "เปิดงบที่อนุมัติแล้วเทียบทีละช่อง",
            ],
            [
                "กดสร้างใบขอเสนอราคาจาก PR ไม่ได้",
                "ประเภทการจัดซื้อเป็นจัดซื้อจัดจ้างผ่านพัสดุ",
                "ถูกต้องแล้ว ให้ใช้ปุ่ม ส่งรายการเข้าระบบ e-GP แทน",
            ],
            [
                "ไม่เห็นปุ่ม ส่งรายการเข้าระบบ e-GP",
                "เอกสารที่เกี่ยวข้องยังอนุมัติไม่ครบ หรือมีกระบวนการ e-GP แล้ว",
                "ตรวจแท็บเอกสารราชการที่เกี่ยวข้องให้ทุกฉบับเป็นอนุมัติแล้ว แล้วรีเฟรชใบขอซื้อ",
            ],
            [
                "ส่งกระบวนการ e-GP ไม่ได้",
                "ใบขอซื้อยังไม่อนุมัติ เอกสารยังไม่ครบ หรือเลือกประเภทผิด",
                "รออนุมัติเอกสารให้ครบ และตรวจว่าเป็นจัดซื้อจัดจ้างผ่านพัสดุ",
            ],
            [
                "ยืนยันกระบวนการ e-GP ไม่ได้",
                "ไม่มีบรรทัดสินค้า หรือจำนวนเป็น 0",
                "ตรวจรายการสินค้าในเอกสารร่าง",
            ],
            [
                "ปุ่มสร้าง RFQ/PO ผู้ชนะไม่ขึ้น",
                "ยังไม่มีผู้ชนะ หรือรายงานผลยังไม่อนุมัติ",
                "ติ๊กผู้ชนะ แล้วจัดทำและอนุมัติรายงานผล",
            ],
            [
                "สร้าง PO แล้วผู้ขายไม่ใช่ผู้ชนะ",
                "พยายามเปลี่ยนผู้ขายในหน้าต่างสร้าง",
                "ระบบล็อกผู้ขายเป็นผู้ชนะ เปิดเอกสารเดิม",
            ],
            [
                "ยืนยัน PO แล้วยอดจองยังอยู่",
                "ยังไม่ได้ Confirm หรือ PO ยังไม่ครอบคลุมใบขอซื้อ",
                "ตรวจว่ายืนยันแล้ว และยอดครอบคลุม PR",
            ],
            [
                "ไม่เห็นปุ่ม ส่งเข้าแอปผู้ขาย ในแท็บใบสั่งซื้อ",
                "ยังไม่ได้กด พิมพ์ PDF หรือส่งเข้าแอปไปแล้ว",
                "กด พิมพ์ PDF ที่แถวนั้นก่อน ถ้าสถานะเป็น รอผู้ขายยืนยัน แปลว่าส่งเข้าแอปแล้ว",
            ],
            [
                "กดส่งแล้วขึ้นว่ายังไม่มีบัญชีแอปผู้ขาย",
                "ผู้ชนะยังไม่มี User Portal",
                "กด สร้าง User Portal บนใบสั่งซื้อ แล้วแจ้งชื่อผู้ใช้และรหัสผ่านให้ผู้ขายเข้าแอป",
            ],
            [
                "ผู้ขายลงนามแล้ว แต่สถานะยังเป็น รอผู้ขายยืนยัน",
                "ยังไม่ได้กดบันทึกบนหน้าลายเซ็น หรือใบถูกยืนยันเองก่อนส่ง",
                "ให้ผู้ขายกดบันทึกอีกครั้ง และตรวจว่าตอนส่งใบยังไม่ถูกกดยืนยันการสั่งซื้อ",
            ],
            [
                "กดออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับไม่ได้",
                "ยังไม่มีรายชื่อในกลุ่มคณะกรรมการตรวจรับ",
                "บันทึกกรรมการตรวจรับในแท็บคณะกรรมการแล้วกดใหม่",
            ],
            [
                "ไม่เห็นปุ่มออกคำสั่งหรือพิมพ์ PDF",
                "ใช้บัญชีหน่วยงาน หรือยังไม่ได้ออกคำสั่ง",
                "ให้พัสดุกดจากแท็บเอกสารแต่งตั้งคณะกรรมการ แล้วใช้ พิมพ์ PDF บนเอกสารคำสั่ง",
            ],
            [
                "ชื่อเจ้าหน้าที่ในแบบแสดงความบริสุทธิ์ใจไม่ตรง",
                "ยังไม่ได้ตั้งค่าเจ้าหน้าที่/หัวหน้าเจ้าหน้าที่ หรือสร้างเอกสารก่อนมีบัญชีฝึกอบรม",
                "ใช้บัญชี uat.officer และ uat.head_officer แล้วแก้ช่องบนเอกสาร หรือกดออกเอกสารใหม่หลังตั้งค่าแล้ว",
            ],
            [
                "ไม่เห็นเอกสารในกล่องงานรออนุมัติของฉัน",
                "ยังไม่ถึงลำดับลงนามของตน หรือยังไม่ได้กดส่งเพื่อลงนาม",
                "แบบแสดงความบริสุทธิ์ใจต้องให้เจ้าหน้าที่ลงนามก่อนหัวหน้า แล้วจึงกรรมการตามลำดับ "
                "รายงานขออนุมัติต้องให้เจ้าหน้าที่ลงนามก่อนหัวหน้า แล้วจึงผู้อำนวยการ",
            ],
            [
                "กรรมการลงนามแบบแสดงความบริสุทธิ์ใจไม่ได้",
                "กรรมการยังไม่มีบัญชีผู้ใช้ หรือเจ้าหน้าที่/หัวหน้ายังไม่ลงนาม",
                "ผูกพนักงานกรรมการกับบัญชี เช่น uat.committee1–3 แล้วรอให้ลำดับก่อนหน้าลงนามครบ",
            ],
            [
                "ชื่อผู้ลงนามในหนังสือราชการไม่ตรง",
                "ยังไม่ได้ตั้งค่าผู้อำนวยการ หรือสร้างเอกสารก่อนมีบัญชีฝึกอบรม",
                "ใช้บัญชี uat.director แล้วแก้ช่องผู้ลงนามบนเอกสาร หรือกดออกเอกสารใหม่หลังตั้งค่าแล้ว",
            ],
        ],
        [4.4, 5.6, 6.2],
    )

    heading(doc, "บทที่ 9 แบบฝึกหัดในห้องอบรม", 1)
    body(
        doc,
        "ทำตามลำดับนี้ในรอบอบรม ใช้หน่วยงาน แหล่งเงิน และสินค้าชุดเดียวกันทั้งรอบ "
        "วิทยากรเป็นคนเดียวที่เปลี่ยนชุดข้อมูลกลาง ห้ามใช้ admin กดครบทุกขั้น",
    )
    make_table(
        doc,
        ["ข้อ", "ผู้ทำ", "งาน", "ผลที่ต้องเห็น"],
        [
            ["1", "ทุกคน", "เข้าสู่ระบบด้วยบัญชีตามบทบาท", "เห็นเมนูตามสิทธิ์"],
            ["2", "หน่วยงาน", "สร้าง PR ประเภทจัดซื้อจัดจ้างผ่านพัสดุ แล้วเช็คงบ", "ได้เลข PR งบเพียงพอ"],
            ["3", "หน่วยงาน", "ใส่กรรมการตรวจรับ 3 คน จาก uat.committee1–3", "มีประธาน 1 คน และกรรมการครบ"],
            ["4", "พัสดุ", "ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ พิมพ์ PDF แล้วกดส่งเพื่อลงนาม", "ได้ไฟล์คำสั่ง สถานะรอลงนาม"],
            ["5", "พัสดุ", "ออกแบบแสดงความบริสุทธิ์ใจ ตรวจชื่อแล้วพิมพ์ PDF จากนั้นกดส่งเพื่อลงนาม", "ได้ไฟล์แบบ สถานะรอลงนาม เจ้าหน้าที่เห็นรายการก่อน"],
            [
                "6",
                "เจ้าหน้าที่ → หัวหน้า → กรรมการ",
                "ลงนามแบบแสดงความบริสุทธิ์ใจตามลำดับ uat.officer แล้ว uat.head_officer แล้ว uat.committee1–3 ห้ามข้าม",
                "ลงนามครบเมื่อกรรมการคนสุดท้ายลงนาม ผู้อำนวยการไม่ลงนามชุดนี้",
            ],
            [
                "7",
                "พัสดุ",
                "ออกหนังสือขออนุมัติจัดซื้อจัดจ้าง ตรวจกล่องข้อ ๒ แล้วพิมพ์ PDF จากนั้นกดส่งเพื่อลงนาม",
                "ได้รายงานขออนุมัติ ข้อ ๒ เป็นข้อความ ไม่มีตารางรายการ สถานะรอลงนาม",
            ],
            ["8", "หน่วยงาน", "กดส่งพัสดุ แล้วกดขออนุมัติ", "สถานะส่งพัสดุแล้ว พัสดุเห็นรายการ และจองงบ"],
            [
                "9",
                "เจ้าหน้าที่ → หัวหน้า → ผ.อ",
                "ลงนามรายงานขออนุมัติตามลำดับ และผ.อ ลงนามคำสั่งแต่งตั้ง",
                "ใบขอซื้อเป็น Approved เมื่อคำสั่งแต่งตั้งและรายงานลงนามครบ",
            ],
            ["10", "พัสดุ", "กดส่งรายการเข้าระบบ e-GP จากใบที่เอกสารอนุมัติครบ", "ได้เอกสาร EGP/ปี/เลขวิ่ง"],
            ["11", "พัสดุ", "ยืนยันกระบวนการ เชิญ รับข้อเสนอ เลือกผู้ชนะ", "มีผู้ชนะ 1 ราย"],
            ["12", "พัสดุ / ผู้อนุมัติ", "จัดทำรายงานผล ส่ง และอนุมัติ", "รายงานผลเป็นอนุมัติแล้ว"],
            ["13", "พัสดุ", "สร้าง RFQ/PO ผู้ชนะ", "ผู้ขายเป็นผู้ชนะ ใบยังเป็นฉบับร่าง"],
            [
                "14",
                "พัสดุ",
                "ที่ใบขอซื้อ แท็บใบสั่งซื้อ กด พิมพ์ PDF แล้วกด ส่งเข้าแอปผู้ขาย",
                "สถานะการยืนยันเป็น รอผู้ขายยืนยัน หลังผู้ขายลงนามจะเป็น ผู้ขายยืนยันแล้ว",
            ],
        ],
        [1.4, 2.8, 6.2, 5.8],
    )
    callout(
        doc,
        "จบรอบอบรมเมื่อไร",
        "ผู้เรียนอธิบายได้ว่าทำไมเปิด PO จากใบขอซื้อประเภทนี้ไม่ได้โดยตรง "
        "สร้างใบขอซื้อจนอนุมัติได้ ส่งเข้า e-GP จนได้ผู้ชนะ และเปิด PO ผู้ชนะได้ "
        "โดยไม่ต้องให้วิทยากรกดแทน",
        "ok",
    )

    heading(doc, "ภาคผนวก ก  คำศัพท์ในระบบ", 1)
    make_table(
        doc,
        ["คำในระบบ", "พูดกับผู้ใช้", "หมายเหตุ"],
        [
            ["ใบขอซื้อ / PR", "ใบขอซื้อของหน่วยงาน", "Purchase Request"],
            ["กระบวนการ e-GP", "แฟ้มจัดซื้อหลังอนุมัติ PR", "เดิมเรียก Purchase Agreement"],
            ["ส่งรายการเข้าระบบ e-GP", "ปุ่มส่งใบขอซื้อที่อนุมัติแล้วเข้าแฟ้ม e-GP", "แสดงเมื่อเอกสารที่เกี่ยวข้องอนุมัติครบ"],
            ["ใบเชิญเสนอราคา", "หนังสือเชิญผู้ประกอบการ", "INV-EGP/ปี/เลขวิ่ง"],
            ["ข้อเสนอราคา / Bid", "ราคาที่ผู้ประกอบการยื่น", "แท็บเปรียบเทียบราคา"],
            ["ผู้ชนะ", "รายที่ได้รับการคัดเลือก", "ติ๊กได้ทีละ 1 ราย"],
            ["รายงานผลการพิจารณา", "ขออนุมัติสั่งซื้อ/สั่งจ้าง", "AR-EGP/ปี/เลขวิ่ง"],
            ["ประกาศผู้ชนะ", "ประกาศผลการคัดเลือก", "WIN-EGP/ปี/เลขวิ่ง"],
            ["สร้าง RFQ/PO ผู้ชนะ", "เปิดใบสั่งซื้อให้ผู้ชนะ", "หลังรายงานผลอนุมัติ"],
            ["ใบสั่งซื้อ / PO", "คำสั่งซื้อที่ยืนยันกับผู้ขาย", "Purchase Order"],
            [
                "ส่งเข้าแอปผู้ขาย",
                "ส่งไฟล์ใบสั่งซื้อของผู้ชนะเข้าแอปให้ลงนาม",
                "อยู่ที่แท็บใบสั่งซื้อบนใบขอซื้อ หลังกด พิมพ์ PDF ผู้ขายลงนามแล้วสถานะกลับมาที่ใบสั่งซื้อ",
            ],
            [
                "สถานะการยืนยัน",
                "ยังไม่ส่ง / รอผู้ขายยืนยัน / ผู้ขายยืนยันแล้ว",
                "ผู้ขายยืนยันแล้ว เมื่อลงนามในพอร์ทัลผู้ขาย",
            ],
            ["Receipts", "ประเภทรับของเข้าคลังจากผู้ขาย", "เลือกบนใบขอซื้อ"],
            [
                "ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
                "สร้างคำสั่งแต่งตั้งจากแท็บเอกสารแต่งตั้งคณะกรรมการ",
                "ดึงรายชื่อกรรมการตรวจรับ แล้วส่งให้ผู้อำนวยการลงนาม",
            ],
            ["พิมพ์ PDF / สร้างไฟล์ Word", "พิมพ์หรือดาวน์โหลดคำสั่งแต่งตั้ง", "อยู่บนเอกสารหนังสือราชการ"],
            [
                "ออกแบบแสดงความบริสุทธิ์ใจ",
                "สร้างแบบเปิดเผยผลประโยชน์ทับซ้อน",
                "แท็บเอกสารแสดงความบริสุทธิ์ใจ วงเงินมากกว่า 100,000 บาท",
            ],
            [
                "ส่งเพื่อลงนาม",
                "ส่งไฟล์ PDF เข้ากล่องงานรออนุมัติตามลำดับผู้ลงนาม",
                "แบบบริสุทธิ์ใจ: เจ้าหน้าที่ หัวหน้า กรรมการ / รายงานขออนุมัติ: เจ้าหน้าที่ หัวหน้า ผ.อ",
            ],
            [
                "งานรออนุมัติของฉัน",
                "กล่องงานที่ถึงลำดับให้ตนลงนาม",
                "คนที่ยังไม่ถึงลำดับจะยังไม่เห็นรายการ",
            ],
            [
                "ออกหนังสือขออนุมัติจัดซื้อจัดจ้าง",
                "สร้างรายงานขออนุมัติตามวิธีที่เลือกในใบขอซื้อ",
                "แท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง",
            ],
            [
                "เอกสารแต่งตั้งคณะกรรมการ",
                "แท็บออกคำสั่งแต่งตั้งตรวจรับ",
                "อยู่ถัดจากแท็บรายชื่อคณะกรรมการ",
            ],
            [
                "เอกสารแสดงความบริสุทธิ์ใจ",
                "แท็บออกแบบเปิดเผยผลประโยชน์ทับซ้อน",
                "ลงนามเจ้าหน้าที่ หัวหน้า แล้วกรรมการตามลำดับ",
            ],
            [
                "เอกสารราชการที่เกี่ยวข้อง",
                "รายการหนังสือราชการทั้งหมดของใบขอซื้อ",
                "แท็บถัดจากเอกสารขออนุมัติจัดซื้อจัดจ้าง",
            ],
            [
                "เลขที่จากสารบรรณ",
                "เลขที่เอกสารจากระบบสารบรรณบนหนังสือราชการ",
                "รายงานขออนุมัติใช้เลขใบขอซื้อ เอกสารอื่นกดขอเลขแยก",
            ],
            [
                "ขอเลขจากระบบสารบรรณ",
                "ปุ่มบนหนังสือราชการหรือคำสั่ง เพื่อออกเลขของเอกสารนั้น",
                "อยู่ที่หัวเอกสารหนังสือราชการ",
            ],
            ["เจ้าหน้าที่", "ผู้ทดสอบเจ้าหน้าที่", "บัญชี uat.officer"],
            ["หัวหน้าเจ้าหน้าที่", "ผู้ทดสอบหัวหน้าเจ้าหน้าที่", "บัญชี uat.head_officer"],
            ["ผู้อำนวยการโรงพยาบาล / ผู้ลงนาม", "ผู้ทดสอบผู้อำนวยการโรงพยาบาล", "บัญชี uat.director"],
            ["จองงบ", "กันเงินไว้ระหว่างรอซื้อ", "เกิดตอนขออนุมัติ PR"],
            ["ผูกพันงบ", "ผูกเงินกับคำสั่งซื้อ", "เกิดตอนยืนยัน PO"],
        ],
        [5.4, 5.4, 5.4],
    )

    heading(doc, "ภาคผนวก ข  ช่องทางสอบถาม", 1)
    bullets(
        doc,
        [
            "ติดขัดเรื่องสิทธิ์หรือเข้าสู่ระบบไม่ได้: งานเทคโนโลยีสารสนเทศ",
            "ติดขัดเรื่องวงเงิน แหล่งเงิน หมวดงบ: งานงบประมาณ",
            "ติดขัดเรื่องใบขอซื้อ กระบวนการ e-GP ผู้ขาย และใบสั่งซื้อ: งานพัสดุ",
            "ติดขัดเรื่องใบตั้งเจ้าหนี้และการลงบัญชี: งานการเงิน",
        ],
    )
    body(
        doc,
        "เอกสารคู่กัน: คู่มือการใช้งานระบบงบประมาณ (UM-ERP-BUD-001) "
        "แผนการทดสอบระบบขอซื้อ จัดซื้อ และงานคลังสินค้า และใบบันทึกผล UAT "
        "ใช้เมื่อต้องการตรวจว่าระบบพร้อม Go-Live ไม่ใช่เอกสารสอนในห้องอบรมผู้ใช้ทั่วไป",
    )

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(24)
    add_text(p, "— จบบทคู่มือ —", 12, True, TEAL)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_text(
        p2,
        "โรงพยาบาลวชิระภูเก็ต  ·  ระบบจัดซื้อจัดจ้างบน Odoo 18  ·  เวอร์ชันเอกสาร 1.0",
        11,
        False,
        MUTED,
    )

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
