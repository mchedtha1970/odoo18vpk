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


def pictures(doc, images, cap=""):
    """Put several screenshots on one line, then an optional caption."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    for index, (name, width_cm) in enumerate(images):
        if index:
            p.add_run(" ")
        run = p.add_run()
        run.add_picture(str(FIG / name), width=Cm(width_cm))
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
            [
                "1.2",
                "30 ก.ย. 2569",
                "เพิ่มบทกระบวนการตรวจรับ หลังผู้ขายยืนยันใบสั่งซื้อ",
                "ทีมพัฒนาระบบ ERP",
            ],
            [
                "1.3",
                "30 ก.ย. 2569",
                "เพิ่มภาพประกอบบทที่ 10 จากใบสั่งซื้อที่เป็นคำสั่งซื้อและใบตรวจรับที่ตรวจรับแล้ว",
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
        "บทที่ 3 บทบาทผู้ใช้ เมนูและปุ่มที่ใช้งานบ่อย",
        "บทที่ 4 หน่วยงาน — เปิดใบขอซื้อ และบันทึกแต่ละแท็บ",
        "บทที่ 5 ขั้นตอนการทำงานของหน่วยงานพัสดุ",
        "บทที่ 6 ขั้นตอนการอนุมัติเอกสารใบขอซื้อ",
        "บทที่ 7 พัสดุ — นำใบขอซื้อเข้ากระบวนการ e-GP",
        "บทที่ 8 ดำเนินการ e-GP จนได้ผู้ชนะ",
        "บทที่ 9 เปิดใบสั่งซื้อ (PO) เมื่อได้ผู้ชนะ",
        "บทที่ 10 กระบวนการตรวจรับ",
        "บทที่ 11 ข้อผิดพลาดที่พบบ่อย",
        "บทที่ 12 แบบฝึกหัดในห้องอบรม",
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
            "เปิดเบราว์เซอร์ แล้วไปที่ระบบ ERP ของโรงพยาบาล",
            "ใส่บัญชีตามบทบาท จากนั้นเข้าแอป ตามบทบาท ดังนี้ บัญชีหน่วยงานให้เข้าระบบขอซื้อ บัญชี พัสดุ / จัดซื้อให้เข้าระบบจัดซื้อจัดจ้าง",
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
        "แล้วพัสดุต้องประกาศ/เชิญเสนอราคา คัดเลือกผู้ชนะ ออกใบสั่งซื้อ แล้วตรวจรับ "
        "ห้ามสลับลำดับ และห้ามเปิด PO ตรงจากใบขอซื้อประเภทนี้",
    )
    picture(doc, "fig_proc_flow.png", 16.2, "ภาพที่ 3  วงจรงานจากใบขอซื้อถึงใบสั่งซื้อ")
    heading(doc, "2.1 สี่ขั้นตอนที่ผู้ใช้ต้องจำ", 2)
    make_table(
        doc,
        ["ขั้น", "เอกสารในระบบ", "ผู้ทำ", "ผลที่เกิด"],
        [
            ["1", "ใบขอซื้อ (PR)", "หน่วยงาน", "ระบุของที่ต้องการ เช็คงบ ส่งพัสดุ"],
            ["2", "กระบวนการ e-GP", "พัสดุ / จัดซื้อ", "เชิญเสนอราคา เปรียบเทียบ เลือกผู้ชนะ"],
            ["3", "ใบสั่งซื้อ (PO)", "พัสดุ / จัดซื้อ", "ออกคำสั่งซื้อให้ผู้ชนะแล้ว ส่งให้ผู้ชนะยืนยัน"],
            ["4", "บันทึกรับมอบงาน", "พัสดุ", "ตรวจรับของจากผู้ขาย หลังผู้ขายยืนยันใบสั่งซื้อแล้ว"],
        ],
        [1.6, 4.4, 3.6, 6.6],
    )
    heading(doc, "2.2 เงื่อนไขสำคัญ", 2)
    bullets(
        doc,
        [
            "เลือกประเภทการจัดซื้อเป็น จัดซื้อจัดจ้างผ่านพัสดุ จึงจะส่งเข้ากระบวนการ e-GP ได้",
            "ส่งเข้า e-GP ได้เมื่อใบขอซื้ออนุมัติแล้ว และเอกสารที่เกี่ยวข้อง ลงนามหรืออนุมัติครบทุกฉบับ เช่น แต่งตั้งคณะกรรมการ อนุมัติรายงานขอซื้อ เป็นต้น",
            "เปิด PO ได้เมื่อมีผู้ชนะ และรายงานผลการพิจารณาได้รับอนุมัติแล้ว",
            "สร้างใบตรวจรับได้เมื่อใบสั่งซื้อเป็นคำสั่งซื้อแล้ว และยังไม่มีใบตรวจรับของใบนั้น",
            "คณะกรรมการตรวจรับใช้รายชื่อที่บันทึกไว้บนใบขอซื้อตั้งแต่บทที่ 4",
        ],
    )
    callout(
        doc,
        "เส้นทางอื่นที่ไม่ใช่ e-GP",
        "ประเภทการจัดซื้อแบบวงเงินเล็กน้อย 79 วรรคสอง หรือ ว.119 ไม่ได้เดินตามคู่มือนี้ "
        "ใช้เมื่อเป็นค่าใช้จ่ายวงเงินเล็กน้อยตามระเบียบ อย่าสับสนกับเส้นทาง e-GP",
        "info",
    )

    heading(doc, "บทที่ 3 บทบาทผู้ใช้ เมนูและปุ่มที่ใช้งานบ่อย", 1)
    picture(doc, "fig_proc_roles.png", 16.2, "ภาพที่ 4  บทบาทในวงจรจัดซื้อจัดจ้าง")
    picture(doc, "fig_proc_menus.png", 16.2, "ภาพที่ 5  เมนูและปุ่มที่ใช้งานบ่อย")
    heading(doc, "3.1 เมนูที่แต่ละบทบาทใช้", 2)
    make_table(
        doc,
        ["บทบาท", "เมนูหลัก", "หมายเหตุ"],
        [
            ["หน่วยงาน", "จัดซื้อ → ใบขอซื้อ", "สร้างใบขอซื้อ เช็คงบ ใส่แท็บรายชื่อคณะกรรมการ แล้วกดส่งพัสดุ"],
            ["พัสดุ", "จัดซื้อ → ใบขอซื้อ → รอรับจากหน่วยงาน", "เปิดใบที่หน่วยงานส่งแล้ว ออกเอกสารแต่งตั้งและอนุมัติขอซื้อ แล้วส่งอนุมัติ"],
            ["พัสดุ", "จัดซื้อ → ใบขอซื้อ", "เปิดใบที่อนุมัติแล้ว กดส่งรายการเข้าระบบ e-GP"],
            ["พัสดุ", "จัดซื้อ → กระบวนการ eGP", "ทำเอกสาร เชิญเสนอราคา เลือกผู้ชนะ"],
            ["พัสดุ", "จัดซื้อ → ใบสั่งซื้อ", "เปิดและยืนยัน PO ของผู้ชนะ แล้วกดสร้างใบตรวจรับ"],
            ["พัสดุ", "จัดซื้อ → บันทึกรับมอบงาน", "เปิดใบตรวจรับที่สร้างแล้ว กรอกผล แล้วกดตรวจรับ"],
            ["เจ้าหน้าที่", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามแบบแสดงความบริสุทธิ์ใจและรายงานขออนุมัติเป็นลำดับแรก"],
            ["หัวหน้าเจ้าหน้าที่", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามสองเอกสารชุดนี้เมื่อเจ้าหน้าที่ลงนามแล้ว"],
            ["ผู้อำนวยการโรงพยาบาล", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามคำสั่งแต่งตั้ง และลงนามรายงานขออนุมัติเมื่อเจ้าหน้าที่กับหัวหน้าลงนามครบ"],
            ["งานงบ", "งบประมาณ / รายการงบ", "ดูวงเงินจองหลังส่ง PR"],
            ["กรรมการตรวจรับ", "การอนุมัติตามลำดับ → งานรออนุมัติของฉัน", "ลงนามแบบแสดงความบริสุทธิ์ใจตามลำดับในเอกสาร รายชื่อชุดนี้ถูกดึงไปที่ใบตรวจรับ"],
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
        "ภาพที่ 7  หน้าจอใบขอซื้อ PR6909008 (ฉบับร่าง)",
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
            "ใส่คำขอจัดซื้อในช่องรายละเอียด จากนั้นใส่รายการวัสดุหรือครุภัณฑ์ และเช็คงบประมาณตามหัวข้อถัดไป",
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
        "หลังกรอกหัวเอกสารแล้ว หน่วยงานทำได้สองอย่างเท่านั้น "
        "คือ ใส่รายการวัสดุหรือครุภัณฑ์ที่จะขอซื้อในแท็บสินค้า "
        "และกดเช็คงบประมาณที่หัวเอกสาร แล้วดูผลที่แท็บตรวจสอบงบประมาณ "
        "แท็บอื่นทั้งหมดดำเนินการโดยฝ่ายพัสดุ "
        "หลังจากใบขอซื้อถูกส่งให้หน่วยงานพัสดุแล้ว "
        "ได้แก่ รายชื่อคณะกรรมการ เอกสารแต่งตั้งคณะกรรมการ "
        "เอกสารแสดงความบริสุทธิ์ใจ เอกสารขออนุมัติจัดซื้อจัดจ้าง และเอกสารราชการที่เกี่ยวข้อง",
    )
    picture(doc, "fig_proc_pr_tabs.png", 16.2, "ภาพที่ 14  แท็บบนใบขอซื้อ ตรงกับแถบแท็บในระบบ พร้อมคำอธิบาย")
    picture(doc, "Screenshot_TAB_overview_items.png", 16.2, "ภาพที่ 15  ภาพรวมแท็บสินค้า")
    picture(doc, "Screenshot_TAB_overview_committee.png", 16.2, "ภาพที่ 16  ภาพรวมแท็บรายชื่อคณะกรรมการ")
    picture(doc, "Screenshot_TAB_overview_budget.png", 16.2, "ภาพที่ 17  ภาพรวมแท็บตรวจสอบงบประมาณ")
    make_table(
        doc,
        ["แท็บ", "ผู้ดำเนินการ", "ทำอะไร"],
        [
            ["สินค้า", "หน่วยงาน", "ใส่รายการวัสดุหรือครุภัณฑ์ที่จะขอซื้อ จำนวน หน่วย และงบประมาณ"],
            ["รายชื่อคณะกรรมการ", "ฝ่ายพัสดุ", "ทำหลังจากใบขอซื้อถูกส่งให้หน่วยงานพัสดุแล้ว"],
            ["เอกสารแต่งตั้งคณะกรรมการ", "ฝ่ายพัสดุ", "ออกคำสั่งแต่งตั้ง หลังจากใบขอซื้อถูกส่งให้หน่วยงานพัสดุแล้ว"],
            ["เอกสารแสดงความบริสุทธิ์ใจ", "ฝ่ายพัสดุ", "ออกแบบและส่งลงนามเมื่อวงเงินมากกว่า 100,000 บาท หลังจากส่งให้หน่วยงานพัสดุแล้ว"],
            ["เอกสารขออนุมัติจัดซื้อจัดจ้าง", "ฝ่ายพัสดุ", "ออกรายงานขออนุมัติและส่งลงนาม หลังจากส่งให้หน่วยงานพัสดุแล้ว"],
            ["เอกสารราชการที่เกี่ยวข้อง", "ฝ่ายพัสดุ", "ดูเอกสารราชการที่ออกจากใบขอซื้อนี้ หลังจากส่งให้หน่วยงานพัสดุแล้ว"],
            ["ตรวจสอบงบประมาณ", "หน่วยงาน", "ดูผลหลังกดปุ่มเช็คงบประมาณที่หัวเอกสาร"],
        ],
        [4.0, 3.6, 8.6],
    )

    heading(doc, "4.3.1 แท็บสินค้า", 3)
    body(
        doc,
        "แท็บนี้เป็นแท็บแรกและสำคัญที่สุด ถ้าไม่มีบรรทัดสินค้า ระบบจะส่งขออนุมัติไม่ได้ "
        "กดเพิ่มรายการที่ท้ายตาราง แล้วกรอกทีละบรรทัดขณะใบยังเป็นร่าง",
    )
    picture(doc, "Screenshot_TAB_ITEM.png", 16.2, "ภาพที่ 18  แท็บสินค้า เพิ่มรายการ จำนวน หน่วย และงบประมาณ")
    steps(
        doc,
        [
            "เปิดแท็บสินค้า แล้วกด เพิ่มรายการ ที่ท้ายตาราง",
        ],
    )
    picture(doc, "Screenshot_TAB_ITEM_add_line.png", 16.2, "ภาพที่ 19  ปุ่มเพิ่มรายการที่ท้ายตารางสินค้า")
    steps(
        doc,
        [
            "เลือกสินค้าจากรหัสหรือชื่อ เมื่อเลือกแล้วระบบจะเติมชื่อ หน่วยนับ และชื่อสำหรับซื้อใน e-GP ให้",
            "ใส่จำนวนที่ขอ และตรวจหน่วยวัดให้ถูกต้อง เช่น กล่อง ขวด ชิ้น",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_ITEM_qty_uom.png", 8.0, "ภาพที่ 20  จำนวนและหน่วยวัดของรายการสินค้า")
    steps(
        doc,
        [
            "ใส่วันที่ต้องการของ ถ้าไม่ใส่ระบบจะใช้วันที่สร้างใบ",
        ],
        start=4,
    )
    picture(doc, "Screenshot_TAB_ITEM_date.png", 8.0, "ภาพที่ 21  วันที่ร้องขอของรายการสินค้า")
    steps(
        doc,
        [
            "ใส่งบประมาณของบรรทัดนั้น เป็นยอดรวมของรายการ ไม่ใช่ราคาต่อหน่วยถ้าหน้าจอแสดงเป็นยอดงบ",
        ],
        start=5,
    )
    picture(doc, "Screenshot_TAB_ITEM_budget.png", 8.0, "ภาพที่ 22  งบประมาณของรายการสินค้า")
    steps(
        doc,
        [
            "ตรวจชื่อสำหรับซื้อใน e-GP ถ้าชื่อในคลังไม่ตรงประกาศ ให้แก้ในช่องนี้",
        ],
        start=6,
    )
    picture(doc, "Screenshot_TAB_ITEM_egp_name.png", 16.2, "ภาพที่ 23  ชื่อสำหรับซื้อใน e-GP")
    steps(
        doc,
        [
            "ถ้ามีคุณลักษณะเฉพาะ กดปุ่มดู/แนบไฟล์ เพื่อใส่รายละเอียด รูปสแกน หรือไฟล์ PDF ของรายการนั้น",
        ],
        start=7,
    )
    picture(doc, "Screenshot_TAB_ITEM_spec.png", 16.2, "ภาพที่ 24  ปุ่มดู/แนบไฟล์คุณลักษณะของรายการ")
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
        "เช่น ใบขอซื้อ PR6909008 ยอด 2,320 บาท "
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
        "ภาพที่ 25  แท็บรายชื่อคณะกรรมการ เพิ่มกรรมการตรวจรับ 3 คน จากชุดฝึกอบรม",
    )
    steps(
        doc,
        [
            "เปิดแท็บรายชื่อคณะกรรมการ แล้วกด เพิ่มรายการ ในกลุ่มคณะกรรมการตรวจรับ",
        ],
    )
    picture(doc, "Screenshot_TAB_committee_add.png", 16.2, "ภาพที่ 26  ปุ่มเพิ่มรายการในกลุ่มคณะกรรมการตรวจรับ")
    steps(
        doc,
        [
            "เลือกพนักงานจากชุดฝึกอบรม คนที่ 1 เป็นประธาน คนที่ 2 และคนที่ 3 เป็นกรรมการ",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_committee_roles.png", 16.2, "ภาพที่ 27  เลือกพนักงานและบทบาทในคณะกรรมการตรวจรับ")
    steps(
        doc,
        [
            "ระบบจะเติมชื่อคณะกรรมการ แผนก และอีเมลที่ทำงานให้ ตรวจว่ามีประธานเพียง 1 คน",
        ],
        start=3,
    )
    picture(doc, "Screenshot_TAB_committee_filled.png", 16.2, "ภาพที่ 28  ชื่อ แผนก อีเมล และประธานเพียง 1 คน")
    steps(
        doc,
        [
            "ถ้าใบนั้นต้องมีกรรมการพิจารณา ให้เพิ่มในกลุ่มคณะกรรมการจัดซื้อจัดจ้าง ด้วยวิธีเดียวกัน",
        ],
        start=4,
    )
    picture(doc, "Screenshot_TAB_committee_procure_add.png", 16.2, "ภาพที่ 29  ปุ่มเพิ่มรายการในกลุ่มคณะกรรมการจัดซื้อจัดจ้าง")
    steps(
        doc,
        [
            "ถ้าต้องกำหนดราคากลาง ให้เพิ่มรายชื่อในกลุ่มคณะกรรมการกำหนดราคากลาง",
        ],
        start=5,
    )
    picture(doc, "Screenshot_TAB_committee_price_add.png", 16.2, "ภาพที่ 30  ปุ่มเพิ่มรายการในกลุ่มคณะกรรมการกำหนดราคากลาง")
    steps(
        doc,
        [
            "บันทึกใบขอซื้อ แล้วตรวจว่าคนเดียวกันไม่ซ้ำในใบเดียวกัน",
        ],
        start=6,
    )
    picture(doc, "Screenshot_TAB_committee_save.png", 8.0, "ภาพที่ 31  ปุ่มบันทึกด้วยตนเองของใบขอซื้อ")
    callout(
        doc,
        "กติกาจำนวนกรรมการ",
        "ถ้ามีกรรมการมากกว่า 1 คน ในชุดเดียวกัน ต้องมีประธานเพียง 1 คน "
        "ถ้ามีคนเดียว ห้ามตั้งเป็นประธาน "
        "งานจ้างที่ปรึกษาต้องมีกรรมการจัดซื้อและกรรมการตรวจรับอย่างน้อยชุดละ 5 คน "
        "งานจ้างออกแบบและควบคุมงานก่อสร้างต้องมีกรรมการตรวจรับอย่างน้อย 3 คน",
        "warn",
    )
    heading(doc, "4.3.3 แท็บตรวจสอบงบประมาณ", 3)
    body(
        doc,
        "แท็บตรวจสอบงบประมาณเป็นขั้นตอนของหน่วยงาน "
        "ต้องตรวจระหว่างเปิดใบขอซื้อ ขณะใบยังเป็นฉบับร่าง "
        "หลังจากใส่รายการวัสดุหรือครุภัณฑ์ในแท็บสินค้าแล้ว "
        "ให้กดปุ่มเช็คงบประมาณที่หัวเอกสาร แล้วเปิดแท็บนี้เพื่อดูผล "
        "ยอดที่ขอต้องตรงกับรายการสินค้า และสถานะต้องเป็นงบเพียงพอ จึงส่งพัสดุได้ "
        "ถ้างบไม่พอ ให้แก้หน่วยงาน แหล่งเงิน หมวดงบ หรือยอดในแท็บสินค้า แล้วกดเช็คอีกครั้ง "
        "แท็บถัดไปเป็นงานของฝ่ายพัสดุ หลังจากใบขอซื้อถูกส่งให้หน่วยงานพัสดุแล้ว",
    )
    steps(
        doc,
        [
            "ตรวจหัวเอกสารว่าประเภทสิ่งที่จะซื้อ หน่วยงานงบประมาณ แหล่งเงิน และหมวดงบตรงแผน",
            "กดปุ่มเช็คงบประมาณที่หัวเอกสาร ขณะสถานะยังเป็นฉบับร่าง",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_44_check_btn.png",
        5.0,
        "ภาพที่ 32  ปุ่มเช็คงบประมาณที่หัวเอกสาร ขณะหน่วยงานเปิดใบขอซื้อ",
    )
    steps(
        doc,
        [
            "เปิดแท็บตรวจสอบงบประมาณ ดูสถานะเช็คงบ งบประมาณที่จอง และงบคงเหลือหลังหักใบนี้",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_44_enough.png",
        12.0,
        "ภาพที่ 33  ผลเช็คงบของใบขอซื้อ PR6909008 เป็นงบเพียงพอ",
    )
    callout(
        doc,
        "หน่วยงานตรวจงบก่อนส่งพัสดุ",
        "รูปนี้เป็นใบขอซื้อ PR6909008 รายการวัสดุ 4 ขวด ยอด 2,320 บาท "
        "สถานะเช็คงบเป็นงบเพียงพอ และยังไม่ได้จองงบ "
        "ระบบจะจองงบเมื่อส่งขออนุมัติ",
        "info",
    )
    heading(doc, "4.3.4 ส่งใบขอซื้อให้พัสดุ", 3)
    body(
        doc,
        "เมื่อเปิดใบขอซื้อเรียบร้อยแล้ว คือใส่รายการวัสดุหรือครุภัณฑ์ครบ "
        "และแท็บตรวจสอบงบประมาณเป็นงบเพียงพอ "
        "ให้กดปุ่มส่งพัสดุที่หัวเอกสาร "
        "เพื่อส่งใบขอซื้อต่อไปให้หน่วยงานพัสดุหรือจัดซื้อดำเนินการต่อ "
        "สถานะจะเปลี่ยนจากฉบับร่างเป็นส่งพัสดุแล้ว "
        "จากนั้นฝ่ายพัสดุรับงานและทำแท็บเอกสารที่เหลือ",
    )
    steps(
        doc,
        [
            "ตรวจว่าใบยังเป็นฉบับร่าง รายการสินค้าครบ และผลเช็คงบเป็นงบเพียงพอ",
            "กดปุ่มส่งพัสดุที่หัวเอกสาร",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_44_send_btn.png",
        4.0,
        "ภาพที่ 34  ปุ่มส่งพัสดุที่หัวเอกสาร เมื่อเปิดใบขอซื้อเรียบร้อยแล้ว",
    )
    steps(
        doc,
        [
            "ตรวจว่าสถานะเปลี่ยนเป็นส่งพัสดุแล้ว และขึ้นข้อความว่าใบนี้ส่งมาจากหน่วยงานแล้ว",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_TAB_44_status_sent.png",
        16.2,
        "ภาพที่ 35  สถานะใบขอซื้อ PR6909008 เปลี่ยนเป็นส่งพัสดุแล้ว",
    )
    callout(
        doc,
        "ส่งแล้วหน่วยงานไม่แก้รายการ",
        "ใบขอซื้อ PR6909008 หลังกดส่งพัสดุ สถานะเป็นส่งพัสดุแล้ว "
        "รอหน่วยงานพัสดุหรือจัดซื้อกดรับงาน "
        "หน่วยงานเปิดดูได้ แต่ไม่แก้รายการสินค้าหรือกดส่งซ้ำ",
        "info",
    )
    heading(doc, "บทที่ 5 ขั้นตอนการทำงานของหน่วยงานพัสดุ", 1)
    body(
        doc,
        "หลังจากหน่วยงานส่งใบขอซื้อมาแล้ว หน่วยงานพัสดุหรือจัดซื้อรับใบที่สถานะส่งพัสดุแล้ว "
        "แล้วดำเนินการตามลำดับนี้",
    )
    steps(
        doc,
        [
            "เปิด Dashboard พัสดุรับงาน เพื่อดูใบขอซื้อที่รอรับงาน แล้วกดรับงาน",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch5_dashboard_inbox.png",
        11.0,
        "ภาพที่ 36  Dashboard พัสดุรับงาน สำหรับใบขอซื้อที่รอรับงาน",
    )
    steps(
        doc,
        [
            "ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ เปิดเอกสาร แล้วพิมพ์ PDF",
        ],
        start=2,
    )
    body(doc, "เปิดแท็บเอกสารแต่งตั้งคณะกรรมการของใบที่รับงานแล้ว")
    picture(
        doc,
        "Screenshot_ch5_committee_before.png",
        16.2,
        "ภาพที่ 37  แท็บเอกสารแต่งตั้งคณะกรรมการก่อนกดออกคำสั่ง",
    )
    body(
        doc,
        "กดปุ่ม ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ "
        "ระบบสร้างคำสั่งและดึงรายชื่อกรรมการตรวจรับจากแท็บรายชื่อคณะกรรมการ",
    )
    picture(
        doc,
        "Screenshot_ch5_committee_after.png",
        16.2,
        "ภาพที่ 38  หลังกดออกคำสั่ง ปุ่มเปลี่ยนเป็นเปิดคำสั่ง และมีเอกสาร กค/2026/0071",
    )
    body(
        doc,
        "กดปุ่ม เปิดคำสั่งแต่งตั้งคณะกรรมการตรวจรับ หรือกดแถวเอกสาร เพื่อเปิดเอกสารที่ออกแล้ว "
        "ที่หัวเอกสารกดปุ่ม พิมพ์ PDF ระบบสร้างไฟล์ PDF ไว้ที่เอกสาร เปิดดูแล้วพิมพ์ได้",
    )
    picture(
        doc,
        "Screenshot_ch5_committee_open_print.png",
        16.2,
        "ภาพที่ 39  เปิดคำสั่งแล้ว กดพิมพ์ PDF ที่หัวเอกสาร",
    )
    body(doc, "ตรวจข้อความแล้วกด ส่งเพื่อลงนาม")
    steps(
        doc,
        [
            "ถ้าวงเงินมากกว่า 100,000 บาท ออกแบบแสดงความบริสุทธิ์ใจ เปิดเอกสาร แล้วพิมพ์ PDF",
        ],
        start=3,
    )
    body(doc, "เปิดแท็บเอกสารแสดงความบริสุทธิ์ใจของใบที่วงเงินมากกว่า 100,000 บาท")
    picture(
        doc,
        "Screenshot_TAB_integrity_create.png",
        16.2,
        "ภาพที่ 40  แท็บเอกสารแสดงความบริสุทธิ์ใจก่อนกดออกแบบ",
    )
    body(
        doc,
        "กดปุ่ม ออกแบบแสดงความบริสุทธิ์ใจ "
        "ระบบสร้างแบบและดึงรายชื่อจากแท็บรายชื่อคณะกรรมการ",
    )
    picture(
        doc,
        "Screenshot_ch5_integrity_list.png",
        16.2,
        "ภาพที่ 41  หลังกดออกแบบ แท็บเอกสารแสดงความบริสุทธิ์ใจมีรายการ กค/2026/0072",
    )
    body(doc, "กดปุ่ม เปิดแบบแสดงความบริสุทธิ์ใจ หรือกดแถวเอกสาร เพื่อเปิดเอกสารที่ออกแล้ว")
    picture(
        doc,
        "Screenshot_ch5_integrity_form.png",
        12.0,
        "ภาพที่ 42  ฟอร์มแบบแสดงความบริสุทธิ์ใจ กค/2026/0072 หลังกดเปิดแบบ",
    )
    body(doc, "ที่หัวเอกสารกดปุ่ม พิมพ์ PDF ระบบสร้างไฟล์ PDF ไว้ที่เอกสาร เปิดดูแล้วพิมพ์ได้")
    picture(
        doc,
        "Screenshot_TAB_integrity_print.png",
        12.0,
        "ภาพที่ 43  เปิดแบบแล้ว กดพิมพ์ PDF ที่หัวเอกสาร",
    )
    picture(
        doc,
        "Screenshot_ch5_integrity_pdf_p1.png",
        14.8,
        "ภาพที่ 44  แบบแสดงความบริสุทธิ์ใจ กค/2026/0072 หลังกดพิมพ์ PDF",
    )
    body(doc, "ตรวจข้อความแล้วกด ส่งเพื่อลงนาม ตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และกรรมการ")
    steps(
        doc,
        [
            "ออกเอกสารขออนุมัติจัดซื้อจัดจ้าง แล้วส่งเพื่อลงนามตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ และผู้อำนวยการ",
        ],
        start=4,
    )
    body(doc, "เปิดแท็บเอกสารขออนุมัติจัดซื้อจัดจ้างของใบที่รับงานแล้ว")
    picture(
        doc,
        "Screenshot_TAB_approval_create.png",
        12.0,
        "ภาพที่ 45  แท็บเอกสารขออนุมัติจัดซื้อจัดจ้างและปุ่มออกหนังสือขออนุมัติ",
    )
    body(
        doc,
        "กดปุ่ม ออกหนังสือขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง "
        "ระบบสร้างรายงานขออนุมัติไว้ในรายการของแท็บนี้",
    )
    picture(
        doc,
        "Screenshot_ch5_approval_list.png",
        16.2,
        "ภาพที่ 46  หลังกดออกหนังสือ แท็บเอกสารขออนุมัติจัดซื้อจัดจ้างมีรายการ กค/2026/0073",
    )
    body(
        doc,
        "กดปุ่ม เปิดหนังสือขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง หรือกดแถวเอกสาร เพื่อเปิดเอกสารที่ออกแล้ว",
    )
    picture(
        doc,
        "Screenshot_ch5_approval_form.png",
        12.0,
        "ภาพที่ 47  ฟอร์มรายงานขออนุมัติจัดซื้อจัดจ้าง กค/2026/0073 หลังกดเปิดเอกสาร",
    )
    body(
        doc,
        "ที่หัวเอกสารกดปุ่ม พิมพ์ PDF ระบบสร้างไฟล์ Word จากข้อมูลในฟอร์มแล้วแปลงเป็น PDF "
        "ไฟล์อยู่ที่เอกสารนี้ เปิดดูเพื่อตรวจข้อความก่อนกดส่งเพื่อลงนาม",
    )
    picture(
        doc,
        "Screenshot_ch5_approval_pdf_p1.png",
        14.8,
        "ภาพที่ 48  เอกสาร PDF รายงานขออนุมัติจัดซื้อจัดจ้าง กค/2026/0073 หลังกดพิมพ์ PDF (หน้าแรก)",
    )
    steps(
        doc,
        [
            "เปิดแท็บเอกสารราชการที่เกี่ยวข้อง ตรวจว่าเอกสารที่ออกจากใบนี้ลงนามหรืออนุมัติครบ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_TAB_official_open.png",
        16.2,
        "ภาพที่ 49  แท็บเอกสารราชการที่เกี่ยวข้องของหน่วยงานพัสดุ",
    )
    steps(
        doc,
        [
            "เมื่อใบขอซื้ออนุมัติแล้ว กดส่งรายการเข้าระบบ e-GP เพื่อเดินกระบวนการจัดซื้อต่อ",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_51_egp_btn.png",
        5.0,
        "ภาพที่ 50  ปุ่มส่งรายการเข้าระบบ e-GP หลังเอกสารครบ",
    )
    callout(
        doc,
        "เริ่มงานได้เมื่อได้รับใบจากหน่วยงาน",
        "หน่วยงานพัสดุทำขั้นตอนนี้หลังจากใบขอซื้อเป็นสถานะส่งพัสดุแล้ว เช่น ใบ PR6909008 "
        "รับงานก่อน แล้วจึงออกเอกสารแต่งตั้ง แสดงความบริสุทธิ์ใจ ขออนุมัติ และส่งเข้า e-GP ตามลำดับ",
        "info",
    )
    heading(doc, "บทที่ 6 ขั้นตอนการอนุมัติเอกสารใบขอซื้อ", 1)
    body(
        doc,
        "หลังจากพิมพ์ PDF ของคำสั่งแต่งตั้งคณะกรรมการตรวจรับ แบบแสดงความบริสุทธิ์ใจ "
        "หรือรายงานขออนุมัติจัดซื้อจัดจ้างแล้ว กดส่งเพื่อลงนามที่แถวเอกสาร "
        "ระบบส่งไฟล์เข้ากล่องงานรออนุมัติตามลำดับผู้ลงนาม "
        "ผู้ที่ถึงลำดับจึงเปิดกล่องนั้น แล้วลงนามได้ทั้งในระบบและในแอปมือถือ",
    )
    steps(
        doc,
        ["กดส่งเพื่อลงนามที่แถวเอกสาร หลังพิมพ์ PDF แล้ว"],
        start=1,
    )
    body(
        doc,
        "เปิดแท็บเอกสารราชการที่เกี่ยวข้อง "
        "เอกสารที่พิมพ์ PDF แล้วและยังต้องส่งลงนามจะขึ้นสถานะยังไม่ส่งลงนาม "
        "พร้อมปุ่มส่งเพื่อลงนามในแถวเดียวกัน "
        "เช่น คำสั่งแต่งตั้งคณะกรรมการตรวจรับ กค/2026/0071 "
        "แบบแสดงความบริสุทธิ์ใจ กค/2026/0072 "
        "และรายงานขออนุมัติจัดซื้อจัดจ้าง กค/2026/0073",
    )
    picture(
        doc,
        "Screenshot_ch6_official_pending.png",
        16.2,
        "ภาพที่ 51  แท็บเอกสารราชการที่เกี่ยวข้อง เอกสารที่ยังต้องส่งลงนาม",
    )
    body(
        doc,
        "คนที่ยังไม่ถึงลำดับจะยังไม่เห็นรายการ "
        "แบบแสดงความบริสุทธิ์ใจเริ่มที่เจ้าหน้าที่ แล้วหัวหน้าเจ้าหน้าที่ แล้วกรรมการตามลำดับในเอกสาร "
        "รายงานขออนุมัติเริ่มที่เจ้าหน้าที่ แล้วหัวหน้าเจ้าหน้าที่ แล้วผู้อำนวยการ "
        "คำสั่งแต่งตั้งคณะกรรมการตรวจรับส่งให้ผู้อำนวยการลงนาม",
    )
    picture(
        doc,
        "Screenshot_TAB_approval_send.png",
        8.0,
        "ภาพที่ 52  ปุ่มส่งเพื่อลงนามที่แถวเอกสาร",
    )
    steps(
        doc,
        ["ผู้ที่ถึงลำดับเข้าเมนู การอนุมัติตามลำดับ แล้วเปิด งานรออนุมัติของฉัน"],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_menu.png",
        6.0,
        "ภาพที่ 53  เมนูการอนุมัติตามลำดับ และงานรออนุมัติของฉัน",
    )
    picture(
        doc,
        "Screenshot_my_approvals_inbox.png",
        16.2,
        "ภาพที่ 54  กล่องงานรออนุมัติของฉัน คลิกการ์ดหรือกดเปิด PDF",
    )
    steps(
        doc,
        ["เปิด PDF ตรวจเอกสาร แล้วลงนามในระบบ"],
        start=3,
    )
    body(
        doc,
        "ที่การ์ดกดเปิด PDF ตรวจข้อความให้ครบ "
        "ที่แถบล่างกดลงนาม วาดลายเซ็นในแท็บวาด หรือโหลดไฟล์ลายเซ็นในแท็บโหลด "
        "จากนั้นกดยอมรับและลงนาม "
        "ถ้าไม่ลงนามให้กดไม่อนุมัติ ถ้ายังไม่ตัดสินใจให้กดปิดหรือยกเลิก",
    )
    picture(
        doc,
        "Screenshot_sign_step_open_pdf.png",
        16.2,
        "ภาพที่ 55  การ์ดในกล่องงานรออนุมัติ และปุ่มเปิด PDF",
    )
    picture(
        doc,
        "Screenshot_sign_step_sign_btn.png",
        16.2,
        "ภาพที่ 56  แถบล่างของเอกสาร มีปุ่มปิด ไม่อนุมัติ และลงนาม",
    )
    picture(
        doc,
        "Screenshot_sign_step_draw.png",
        12.0,
        "ภาพที่ 57  หน้าต่างลงลายเซ็น แท็บวาดและโหลด",
    )
    picture(
        doc,
        "Screenshot_sign_step_accept.png",
        8.0,
        "ภาพที่ 58  ปุ่มยอมรับและลงนาม",
    )
    steps(
        doc,
        ["ในแอปมือถือ เปิดแท็บรออนุมัติ แตะรายการ แล้วเปิด PDF เพื่อลงนาม"],
        start=4,
    )
    body(
        doc,
        "เข้าแอปด้วยบัญชีเดียวกับระบบ "
        "แท็บรออนุมัติแสดงเฉพาะงานที่ถึงลำดับของตน "
        "แตะเพื่อดูรายละเอียด / PDF แล้วลงนาม "
        "แท็บอนุมัติแล้วใช้ดูรายการที่ลงนามเสร็จแล้ว",
    )
    picture(
        doc,
        "Screenshot_mobile_approvals.png",
        7.2,
        "ภาพที่ 59  แอปมือถือ แท็บรออนุมัติและอนุมัติแล้ว",
    )
    callout(
        doc,
        "ยังไม่ถึงลำดับจะไม่เห็นงาน",
        "ทั้งในระบบและในแอป กล่องงานรออนุมัติแสดงเฉพาะรายการที่ถึงลำดับของตน "
        "ถ้ายังไม่เห็น ให้ตรวจว่าคนลำดับก่อนหน้าลงนามแล้ว และเอกสารถูกกดส่งเพื่อลงนามแล้ว",
        "info",
    )
    heading(doc, "บทที่ 7 พัสดุ — นำใบขอซื้อเข้ากระบวนการ e-GP", 1)
    body(
        doc,
        "บทนี้ใช้บัญชีพัสดุ เมื่อหน่วยงานกดส่งพัสดุแล้ว เปิดเมนู จัดซื้อ → ใบขอซื้อ → รอรับจากหน่วยงาน "
        "จะเห็นใบสถานะ ส่งพัสดุแล้ว จากนั้นออกเอกสารและส่งขอลงนาม"
        "เมื่อเอกสารลงนามเรียบร้อยแล้ว กด ส่งเข้า กระบวนการ e-GP ในระบบ",
    )
    heading(doc, "7.1 ส่งใบขอซื้อเข้ากระบวนการ e-GP", 2)
    body(
        doc,
        "กระบวนการ e-GP ในระบบนี้ใช้รองรับและเก็บข้อมูลที่ได้จากการทำในระบบ e-GP จริง "
        "เช่น ไฟล์ที่สร้างจากระบบ e-GP เลขเอกสาร หรือชื่อโครงการ "
        "เพื่อใช้อ้างอิงในการทำงานและเชื่อมกับงานอื่น",
    )
    steps(
        doc,
        [
            "เปิดใบขอซื้อที่อนุมัติแล้ว จากเมนู ระบบจัดซื้อจัดจ้าง → ข้อมูลใบขอซื้อ → ใบขอซื้อ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch7_pr_menu.png",
        16.2,
        "ภาพที่ 60  เมนูระบบจัดซื้อจัดจ้าง → ข้อมูลใบขอซื้อ → ใบขอซื้อ",
    )
    body(
        doc,
        "เปิดรายการในหน้านี้แล้วจะเข้าใบขอซื้อที่อนุมัติแล้ว "
        "เช่น PR6909008 สถานะที่หัวเอกสารเป็นอนุมัติแล้ว",
    )
    picture(
        doc,
        "Screenshot_ch7_pr_opened.png",
        16.2,
        "ภาพที่ 61  ใบขอซื้อ PR6909008 ที่เปิดจากรายการ สถานะอนุมัติแล้ว",
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
        "ภาพที่ 62  แท็บเอกสารราชการที่เกี่ยวข้องที่อนุมัติครบ",
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
        "ภาพที่ 63  ปุ่มส่งรายการเข้าระบบ e-GP ที่หัวใบขอซื้อ",
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
        "ภาพที่ 64  หน้าต่างกระบวนการ eGP แสดงรายการสินค้าจากใบขอซื้อ",
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
        "ภาพที่ 65  ปุ่มกระบวนการ eGP ในหน้าต่างยืนยัน",
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
        "ภาพที่ 66  ปุ่มสถิติกระบวนการ e-GP บนใบขอซื้อ",
    )
    heading(doc, "7.2 สิ่งที่ระบบสร้างให้อัตโนมัติ", 2)
    bullets(
        doc,
        [
            "เลขที่กระบวนการ e-GP รูปแบบ EGP/ปี/เลขวิ่ง เช่น EGP/2026/0001",
            "การอ้างอิงใบขอซื้อต้นทาง และวงเงินงบประมาณตามใบขอซื้อ",
            "ประเภทพัสดุ ประเภทการจัดซื้อ และวิธีการจัดซื้อจัดจ้าง ตามที่ระบุในใบขอซื้อ",
            "รายการสินค้าตามบรรทัดใบขอซื้อ",
        ],
    )
    heading(doc, "7.3 ตรวจร่างแล้วกดยืนยัน", 2)
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
        "ภาพที่ 67  เอกสารกระบวนการ e-GP สถานะร่าง (Draft PA)",
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
        "ภาพที่ 68  ฟิลด์เลขที่โครงการ (e-GP) และชื่อโครงการ",
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
        "ภาพที่ 69  แท็บสินค้า ตรวจจำนวนและหน่วยนับ",
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
        "ภาพที่ 70  ปุ่มยืนยันเอกสารกระบวนการ e-GP",
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
        "ภาพที่ 71  แถบสถานะหลังยืนยัน ขั้นถัดไปคือ e-GP Documents",
    )
    callout(
        doc,
        "ยืนยันไม่ได้",
        "ระบบจะกันการยืนยันถ้ายังไม่มีรายการสินค้า หรือมีบรรทัดที่จำนวนน้อยกว่าหรือเท่ากับศูนย์ "
        "ให้กลับไปแก้ในเอกสารร่างก่อน",
        "danger",
    )

    heading(doc, "บทที่ 8 ดำเนินการ e-GP จนได้ผู้ชนะ", 1)
    body(
        doc,
        "หลังยืนยันเอกสารแล้ว พัสดุทำงานในแท็บของกระบวนการ e-GP ตามลำดับ "
        "อย่าข้ามไปสร้าง PO ก่อนเลือกผู้ชนะและอนุมัติรายงานผล",
    )
    picture(doc, "fig_proc_egp_steps.png", 16.2, "ภาพที่ 72  ขั้นตอนในกระบวนการ e-GP")
    heading(doc, "8.1 บันทึกเอกสาร e-GP", 2)
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
    heading(doc, "8.2 เชิญเสนอราคาและรับข้อเสนอ", 2)
    steps(
        doc,
        [
            "เปิดแท็บเชิญเสนอราคา แล้วเพิ่มบรรทัดผู้ประกอบการที่เชิญ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_invite.png",
        16.2,
        "ภาพที่ 73  แท็บเชิญเสนอราคา ของ EGP/2026/0052 ที่อ้างอิง PR6909008",
    )
    steps(
        doc,
        [
            "กดดึงรายการสินค้าจากใบขอซื้อ ระบบนำสินค้า จำนวน และหน่วยจากใบขอซื้อที่อ้างอิงมาใส่ในใบเชิญสถานะร่าง",
        ],
        start=2,
    )
    body(
        doc,
        "ถ้าใบเชิญร่างมีรายการอยู่แล้ว รายการเดิมจะถูกแทนด้วยรายการจากใบขอซื้อ "
        "กดปุ่มนี้หลังเพิ่มผู้ประกอบการแล้ว "
        "ปุ่มเดียวกันอยู่ที่หน้าใบเชิญ แท็บรายการที่เชิญเสนอราคา",
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_invite.png",
        16.2,
        "ภาพที่ 74  ปุ่มดึงรายการสินค้าจากใบขอซื้อ บนใบเชิญของ PR6909008",
    )
    steps(
        doc,
        [
            "พิมพ์ใบเชิญได้จากปุ่ม พิมพ์ใบเชิญ ถ้าต้องส่งเป็นเอกสาร",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_print.png",
        6.0,
        "ภาพที่ 75  ปุ่มพิมพ์ใบเชิญ บนใบเชิญ INV-EGP/2026/0006",
    )
    steps(
        doc,
        [
            "เปิดใบเชิญแต่ละราย ตรวจสินค้าที่ดึงมา วันที่เชิญ และกำหนดยื่น แล้วกด บันทึกส่งคำเชิญ",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_form.png",
        14.0,
        "ภาพที่ 76  ใบเชิญ INV-EGP/2026/0006 รายการสินค้าที่ดึงจาก PR6909008",
    )
    steps(
        doc,
        [
            "เมื่อได้รับข้อเสนอ กด ได้รับข้อเสนอ / บันทึกราคา หรือปุ่ม รับข้อเสนอ จากรายการ",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_responded.png",
        16.2,
        "ภาพที่ 77  สถานะได้รับข้อเสนอแล้ว ของใบเชิญ INV-EGP/2026/0006",
    )
    steps(
        doc,
        [
            "ระบบจะสร้างข้อเสนอราคาให้นำไปบันทึกในแท็บเปรียบเทียบราคา",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_compare.png",
        16.2,
        "ภาพที่ 78  แท็บเปรียบเทียบราคา ข้อเสนอของ PR6909008",
    )
    heading(doc, "8.3 เปรียบเทียบราคาและเลือกผู้ชนะ", 2)
    steps(
        doc,
        [
            "เปิดแท็บเปรียบเทียบราคา ตรวจผู้เสนอราคา เลขที่ใบเสนอราคา วันที่ และราคาที่เสนอ หรือสามารถบันทึกราคาที่ช่องราคาที่เสนอได้โดยตรง",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_compare83.png",
        16.2,
        "ภาพที่ 79  แท็บเปรียบเทียบราคา ของ EGP/2026/0052 ที่อ้างอิง PR6909008",
    )
    body(
        doc,
        "เมื่อแท็บเปรียบเทียบราคามีรายการ แถบขั้นตอนเลื่อนไป Compare Prices เอง "
        "หรือกดที่แถบเพื่อเปลี่ยนขั้นได้",
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_statusbar.png",
        16.2,
        "ภาพที่ 80  แถบขั้นตอนของ EGP/2026/0052 อยู่ที่ Compare Prices และกดเปลี่ยนขั้นได้",
    )
    steps(
        doc,
        [
            "ติ๊กช่องผู้ชนะที่รายที่ได้รับการคัดเลือก ระบบอนุญาตผู้ชนะได้ทีละ 1 ราย",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_winner.png",
        16.2,
        "ภาพที่ 81  ช่องผู้ชนะของข้อเสนอ Q-11221122 บน PR6909008",
    )
    body(
        doc,
        "เมื่อติ๊กผู้ชนะแล้ว สถานะจะเปลี่ยนเป็น Award Vendor",
    )
    picture(
        doc,
        "Screenshot_ch8_pr6909008_statusbar_awarded.png",
        16.2,
        "ภาพที่ 82  แถบขั้นตอนของ EGP/2026/0052 อยู่ที่ Award Vendor",
    )
    callout(
        doc,
        "ยังสร้าง PO ไม่ได้ตอนนี้",
        "แม้ติ๊กผู้ชนะแล้ว ปุ่มสร้าง POจะยังไม่พร้อมจนกว่าจะจัดทำและอนุมัติ "
        "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง",
        "warn",
    )
    heading(doc, "8.4 จัดทำรายงานผลและประกาศผู้ชนะ", 2)
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
        "ภาพที่ 83  ปุ่มจัดทำรายงานผลและขออนุมัติ ในแท็บเปรียบเทียบราคา",
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
        "ภาพที่ 84  รายงานผลการพิจารณา ตรวจเรื่อง เกณฑ์ และวงเงินที่ขออนุมัติ",
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
        "ภาพที่ 85  ปุ่มสร้างรายการจากข้อเสนอ eGP",
    )
    steps(
        doc,
        [
            "กด พิมพ์รายงาน ระบบสร้างแถวในแท็บเอกสาร e-GP ให้เอง "
            "เลือก Title เป็นรายงานผลการพิจารณา และแนบไฟล์ PDF",
        ],
        start=4,
    )
    picture(
        doc,
        "Screenshot_ch8_award_print.png",
        16.2,
        "ภาพที่ 86  หน้ารายงานผล ปุ่มที่ใช้คือพิมพ์รายงาน",
    )
    steps(
        doc,
        [
            "เปิดกระบวนการ e-GP แท็บเอกสาร e-GP แล้วกด ส่งเพื่อลงนาม "
            "ที่แถวรายงานผลการพิจารณา รายการจะเข้ากล่องงานรออนุมัติ "
            "ปุ่ม View ใช้เปิดไฟล์",
        ],
        start=5,
    )
    picture(
        doc,
        "Screenshot_ch8_egp_send_sign.png",
        16.2,
        "ภาพที่ 87  แถวรายงานผลการพิจารณาในแท็บเอกสาร e-GP พร้อมปุ่มส่งเพื่อลงนามและ View",
    )
    steps(
        doc,
        [
            "ที่แท็บเปรียบเทียบราคา กด ประกาศผู้ชนะ "
            "ระบบสร้างแถวในแท็บเอกสาร e-GP ให้เอง "
            "เลือก Title เป็นประกาศผู้ชนะ และแนบไฟล์ PDF "
            "จากนั้นกด ส่งเพื่อลงนาม ที่แถวนั้น",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_ch8_winner_egp.png",
        16.2,
        "ภาพที่ 88  แถวประกาศผู้ชนะในแท็บเอกสาร e-GP พร้อมไฟล์ PDF เมื่อส่งแล้วสถานะเป็นรอลงนาม",
    )
    steps(
        doc,
        [
            "เมื่อส่งลงนามแล้ว เอกสารเข้ากล่องงานรออนุมัติของฉัน "
            "ในเมนูการอนุมัติตามลำดับ ของผู้ที่ถึงลำดับเท่านั้น "
            "ผู้ถัดไปจะเห็นรายการเมื่อคนก่อนหน้าลงนามแล้ว",
        ],
        start=7,
    )
    body(
        doc,
        "ลำดับลงนามของสองเอกสารนี้ต่างกันดังนี้",
    )
    make_table(
        doc,
        ["เอกสาร", "ลำดับลงนามในกล่องงานรออนุมัติ"],
        [
            [
                "รายงานผลการพิจารณา",
                "เจ้าหน้าที่ แล้วหัวหน้าเจ้าหน้าที่ แล้วผู้อำนวยการ",
            ],
            [
                "ประกาศผู้ชนะ",
                "ผู้อำนวยการ",
            ],
        ],
        [5.4, 10.8],
    )
    body(
        doc,
        "เมื่อลงนามครบ รายงานผลการพิจารณาจะเป็นอนุมัติแล้ว "
        "และแถวในแท็บเอกสาร e-GP เป็นลงนามแล้ว",
    )

    heading(doc, "บทที่ 9 เปิดใบสั่งซื้อ (PO) เมื่อได้ผู้ชนะ", 1)
    body(
        doc,
        "เปิด PO ได้จากเอกสารกระบวนการ e-GP หรือจากใบขอซื้อต้นทาง "
        "เมื่อปุ่ม สร้าง PO แสดงขึ้น แสดงว่าเงื่อนไขครบแล้ว",
    )
    picture(doc, "fig_proc_po.png", 16.2, "ภาพที่ 89  เงื่อนไขและลำดับการเปิด PO")
    heading(doc, "9.1 เงื่อนไขที่ต้องครบก่อนกดปุ่ม", 2)
    bullets(
        doc,
        [
            "กระบวนการ e-GP ยืนยันแล้ว",
            "มีข้อเสนอราคาที่ติ๊กเป็นผู้ชนะ",
            "รายงานผลการพิจารณาได้รับอนุมัติแล้ว",
        ],
        numbered=True,
    )
    heading(doc, "9.2 สร้าง PO", 2)
    steps(
        doc,
        [
            "เปิดเอกสารกระบวนการ e-GP แล้วกด สร้าง PO",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch9_open_egp.png",
        16.2,
        "ภาพที่ 90  เปิดเอกสารกระบวนการ e-GP เลขที่เอกสารอยู่ที่หัวหน้าจอ",
    )
    picture(
        doc,
        "Screenshot_ch9_create_po_btn.png",
        10.0,
        "ภาพที่ 91  ปุ่มสร้าง PO ที่ต้องกดบนเอกสารกระบวนการ e-GP",
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
        "ภาพที่ 92  หน้าต่างสร้าง PO แสดงผู้ขายผู้ชนะ (เปลี่ยนรายอื่นไม่ได้)",
    )
    steps(
        doc,
        [
            "ใส่เลขอ้างอิงใบเสนอราคา e-GP ถ้ามี แล้วกด สร้าง PO",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_72_wizard_form.png",
        12.0,
        "ภาพที่ 93  กรอกเลขอ้างอิงใบเสนอราคา e-GP แล้วกดสร้าง PO",
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
        "ภาพที่ 94  รายการสินค้าในใบสั่งซื้อที่สร้างจากผู้ชนะ",
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
        "ภาพที่ 95  ช่องส่งถึง (คลังรับของ) เช่น คลังกลาง: Receipts",
    )
    steps(
        doc,
        [
            "ยังไม่ต้องยืนยันใบสั่งซื้อในขั้นนี้ ให้พิมพ์ไฟล์และส่งเข้าแอปผู้ขายตามข้อ 9.3",
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
    heading(doc, "9.3 ส่งใบสั่งซื้อของผู้ชนะให้ผู้ขายยืนยัน", 2)
    body(
        doc,
        "หลังสร้างใบสั่งซื้อของผู้ชนะแล้ว พัสดุส่งไฟล์ใบสั่งซื้อเข้าแอปผู้ขาย "
        "ผู้ขายเห็นเฉพาะใบที่ส่งเข้าแอป เมื่อลงลายเซ็นและกดบันทึก "
        "สถานะบนใบสั่งซื้อจะกลับมาเป็น ผู้ขายยืนยันแล้ว",
    )
    heading(doc, "9.3.1 พิมพ์ไฟล์ใบสั่งซื้อ", 3)
    steps(
        doc,
        ["เปิดใบขอซื้อต้นทางของงานนี้ ด้วยบัญชีพัสดุ"],
        start=1,
    )
    picture(
        doc,
        "Screenshot_741_open_pr.png",
        15.2,
        "ภาพที่ 96  เปิดใบขอซื้อต้นทาง เลขที่เอกสารอยู่ที่หัวหน้าจอ",
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
        "ภาพที่ 97  แท็บใบสั่งซื้อ แถวของผู้ชนะ เลขที่ตรงใบที่สร้าง คอลัมน์ไฟล์ยังว่าง",
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
        "ภาพที่ 98  ก่อนมีไฟล์ สถานะยังไม่ส่ง และมีปุ่มพิมพ์ PDF",
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
        "ภาพที่ 99  เมื่อมีไฟล์แล้ว ปุ่มส่งเข้าแอปผู้ขายแสดงในแถวเดียวกัน",
    )
    heading(doc, "9.3.2 ส่งเข้าแอปผู้ขาย", 3)
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
        "ภาพที่ 100  ปุ่มสร้าง User Portal บนใบสั่งซื้อ ใช้เมื่อผู้ขายยังไม่มีบัญชีแอป",
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
        "ภาพที่ 101  กดส่งเข้าแอปผู้ขายที่แถวใบสั่งซื้อ ขณะสถานะยังไม่ส่ง",
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
        "ภาพที่ 102  หลังส่งแล้ว สถานะการยืนยันเป็นรอผู้ขายยืนยัน",
    )
    steps(
        doc,
        [
            "ผู้ขายเปิดแอป ระบบบริการผู้จำหน่าย ด้วยบัญชี User Portal จะเห็นการ์ดรอยืนยันและยืนยันแล้ว",
        ],
        start=4,
    )
    pictures(
        doc,
        [
            ("Screenshot_742_app_login.png", 4.5),
            ("Screenshot_742_app_home.png", 4.9),
            ("Screenshot_742_app_cards.png", 4.8),
        ],
        "ภาพที่ 103  แอป ระบบบริการผู้จำหน่าย ของผู้ขาย มีการ์ดรอยืนยันสำหรับเปิดเอกสารที่จัดซื้อส่งมา",
    )
    steps(
        doc,
        ["กดการ์ด รอยืนยัน แล้วแตะใบสั่งซื้อในรายการ เพื่อเปิดเอกสารและดูไฟล์ PDF"],
        start=5,
    )
    picture(
        doc,
        "Screenshot_742_app_waiting.png",
        4.8,
        "ภาพที่ 104  เปิดใบสั่งซื้อในแอป เห็นไฟล์ PDF และปุ่มลงนามยืนยัน",
    )
    steps(
        doc,
        ["กด ลงนามยืนยัน แล้วลงลายเซ็นในกรอบ ถ้าเส้นไม่ชัดให้กด ล้าง แล้วลงใหม่"],
        start=6,
    )
    pictures(
        doc,
        [
            ("Screenshot_742_app_open.png", 4.9),
            ("Screenshot_742_app_sign.png", 5.0),
        ],
        "ภาพที่ 105  หน้าลงลายเซ็นเพื่อยืนยันใบสั่งซื้อ มีกรอบลงนาม และปุ่มล้าง ยกเลิก บันทึก",
    )
    steps(
        doc,
        [
            "กด บันทึก สถานะในแอปเป็นยืนยันแล้ว และบนใบสั่งซื้อในระบบกลับมาเป็นผู้ขายยืนยันแล้ว โดยฝ่ายจัดซื้อไม่ต้องกดยืนยันซ้ำ",
        ],
        start=7,
    )
    pictures(
        doc,
        [
            ("Screenshot_742_app_saved.png", 4.9),
            ("Screenshot_742_app_done.png", 5.0),
        ],
        "ภาพที่ 106  ปุ่มล้าง ยกเลิก และบันทึก หลังลงลายเซ็นให้กดบันทึก",
    )
    picture(
        doc,
        "Screenshot_742_confirmed_row.png",
        16.6,
        "ภาพที่ 107  หลังผู้ขายกดบันทึกในแอป สถานะการยืนยันเป็นผู้ขายยืนยันแล้ว และสถานะใบสั่งซื้อเป็นคำสั่งซื้อ",
    )
    callout(
        doc,
        "ผู้ขายยืนยันที่ไหน",
        "ผู้ขายทำในแอป ระบบบริการผู้จำหน่าย เท่านั้น "
        "เปิดใบที่อยู่ในการ์ดรอยืนยัน ลงลายเซ็น แล้วกดบันทึก "
        "สถานะยืนยันจะกลับมาที่ใบสั่งซื้อในระบบ",
        "info",
    )
    caption(
        doc,
        "ภาพที่ 109  แท็บใบสั่งซื้อ VPK แสดงชื่อไฟล์ สถานะผู้ขายยืนยันแล้ว และปุ่มเปิดไฟล์ PDF",
    )
    heading(doc, "9.4 ปิดกระบวนการ e-GP", 2)
    body(
        doc,
        "เมื่อเลือกผู้ชนะและเปิด PO แล้ว หากนโยบายให้ปิดงาน กด ปิดข้อตกลง (เลือกผู้ชนะแล้ว) "
        "ในแท็บเปรียบเทียบราคา ระบบจะปิดได้เมื่อมีผู้ชนะแล้ว",
    )

    heading(doc, "บทที่ 10 กระบวนการตรวจรับ", 1)
    body(
        doc,
        "หลังผู้ขายยืนยันใบสั่งซื้อแล้ว และผู้ขายจะส่งมอบงาน กรรมการตรวจรับ "
        "บันทึกผลตรวจรับในเมนู จัดซื้อ → บันทึกรับมอบงาน",
    )
    heading(doc, "10.1 เงื่อนไขก่อนสร้างใบตรวจรับ", 2)
    make_table(
        doc,
        ["เงื่อนไข", "ผลที่ต้องเห็น"],
        [
            ["ผู้ขายยืนยันใบสั่งซื้อแล้ว", "สถานะการยืนยันเป็น ผู้ขายยืนยันแล้ว ตามข้อ 9.3"],
            ["ยังไม่มีใบตรวจรับของใบนี้", "ถ้ามีแล้ว ให้เปิดใบเดิมจากปุ่มสถิติบนใบสั่งซื้อ อย่าสร้างซ้ำ"],
            [
                "เคยมีคำสั่งแต่งตั้งคณะกรรมการตรวจรับ ของใบนี้",
                "แท็บคณะกรรมการตรวจรับมีรายชื่อชุดเดียวกับคำสั่งแต่งตั้ง",
            ],
        ],
        [5.6, 10.6],
    )
    heading(doc, "10.2 สร้างใบตรวจรับ", 2)
    steps(
        doc,
        [
            "เปิดเมนู บันทึกรับมอบงาน",
            "กด สร้างใบตรวจรับ ระบบเปิดบันทึกรับมอบงานฉบับร่าง และออกเลขที่ให้",
            "ตรวจผู้ขาย (Vendor) และเลือกใบสั่งซื้อ (Purchase Order) ให้ตรงใบที่ยืนยันแล้ว"
            "ระบบจะดึงรายการ สินค้าจากใบสั่งซื้อมาใส่ให้",
            "ตรวจแท็บรายการสินค้า ให้จำนวนและราคามาจากใบสั่งซื้อ ถ้าส่งมอบไม่ครบ ให้แก้จำนวนเฉพาะแถวที่รับจริง",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch10_po_button.png",
        16.2,
        "ภาพที่ 110  ปุ่มสร้างใบตรวจรับบนใบสั่งซื้อที่เป็นคำสั่งซื้อ อยู่ถัดจากรับสินค้า",
    )
    callout(
        doc,
        "สร้างซ้ำไม่ได้",
        "ใบสั่งซื้อที่มีใบตรวจรับแล้วยังคงเปิดใบเดิมได้ แต่ปุ่ม สร้างใบตรวจรับ จะไม่แสดงซ้ำ",
        "warn",
    )
    heading(doc, "10.3 กรอกผลการตรวจรับ", 2)
    body(
        doc,
        "กรอกขณะสถานะยังเป็น Draft หลังกดตรวจรับแล้วช่องเหล่านี้จะแก้ไม่ได้ "
        "ต้องกด กลับเป็นร่าง ก่อน จึงจะแก้ได้",
    )
    make_table(
        doc,
        ["ช่อง", "ใส่อะไร"],
        [
            ["ผลการตรวจรับ", "ตรวจรับครบถ้วน หรือ ตรวจรับบางส่วน ถ้าของส่งไม่ครบ"],
            ["วันที่ตรวจรับ", "วันที่คณะกรรมการตรวจรับ"],
            ["วันที่ส่งมอบงาน", "วันที่ผู้ขายส่งของจริง"],
            ["วันครบกำหนดตามสัญญา", "วันสิ้นสุดตามสัญญา ถ้าว่างระบบจะไม่คิดว่าส่งช้า"],
            ["ผู้ควบคุมงาน/ผู้ตรวจรับ", "ผู้ใช้ที่เป็นผู้ตรวจรับของงานนี้"],
            ["ค่าปรับ", "ใส่เมื่อส่งมอบช้าและมีค่าปรับ"],
            ["คณะกรรมการตรวจรับ", "ตรวจชื่อ บทบาทประธานกรรมการ กรรมการ และกรรมการและเลขานุการ"],
        ],
        [5.2, 11.0],
    )
    picture(
        doc,
        "Screenshot_ch10_form.png",
        16.2,
        "ภาพที่ 111  บันทึกรับมอบงานหลังตรวจรับ ผู้ขาย ใบสั่งซื้อ รายการสินค้า และสถานะ Accepted มาจากใบสั่งซื้อ",
    )
    picture(
        doc,
        "Screenshot_ch10_committee.png",
        16.2,
        "ภาพที่ 112  แท็บคณะกรรมการตรวจรับ ดึงชื่อจากคำสั่งแต่งตั้งของใบสั่งซื้อ",
    )
    callout(
        doc,
        "ส่งมอบช้า",
        "ถ้าวันที่ส่งมอบงานหลังวันครบกำหนดตามสัญญา ระบบขึ้นแถบ ส่งมอบงานล่าช้า และแสดงจำนวนวัน "
        "ให้ตรวจค่าปรับก่อนกดตรวจรับ",
        "warn",
    )
    heading(doc, "10.4 กดตรวจรับ", 2)
    steps(
        doc,
        [
            "กด ตรวจรับ",
            "หน้าต่างเลือกวันตรวจรับ (Accepted Date) เปิดขึ้น ตรวจวันให้ถูก แล้วกด Accept",
            "สถานะเปลี่ยนจาก Draft เป็น Accepted และช่อง Accepted Date ถูกเติมให้",
            "ถ้าผู้ขอซื้อมีอีเมล ระบบเข้าคิวส่งอีเมลแจ้งผู้ขอ สถานะแจ้งผู้ขอเป็น เข้าคิวส่งแล้ว",
        ],
        start=1,
    )
    callout(
        doc,
        "ผลไม่ผ่าน",
        "ถ้าเลือกผลการตรวจรับเป็น ไม่ผ่านการตรวจรับ ปุ่มตรวจรับจะกดไม่ผ่าน "
        "ให้บันทึกเหตุผลในแท็บหมายเหตุ อย่ากดตรวจรับเพื่อปิดงาน",
        "danger",
    )
    heading(doc, "บทที่ 11 ข้อผิดพลาดที่พบบ่อย", 1)
    picture(doc, "fig_proc_do_dont.png", 16.2, "ภาพที่ 114  สิ่งที่ควรทำและไม่ควรทำ")
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
                "ปุ่มสร้าง POไม่ขึ้น",
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
            [
                "ไม่เห็นปุ่ม สร้างใบตรวจรับ",
                "ใบสั่งซื้อยังไม่เป็นคำสั่งซื้อ หรือมีใบตรวจรับแล้ว",
                "ยืนยันใบสั่งซื้อก่อน ถ้ามีใบเดิมแล้วให้เปิดจากปุ่มสถิติบนใบสั่งซื้อ",
            ],
            [
                "กดตรวจรับไม่ได้",
                "ผลการตรวจรับเป็นไม่ผ่าน หรือยังไม่มีรายการสินค้า",
                "เลือกตรวจรับครบถ้วนหรือบางส่วน และตรวจว่ามีอย่างน้อย 1 รายการ",
            ],
        ],
        [4.4, 5.6, 6.2],
    )

    heading(doc, "บทที่ 12 แบบฝึกหัดในห้องอบรม", 1)
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
            ["12", "พัสดุ / ผู้อนุมัติ", "จัดทำรายงานผล พิมพ์รายงาน แล้วกดส่งเพื่อลงนามที่แท็บเอกสาร e-GP", "รายงานผลเข้ากล่องงานรออนุมัติ และเป็นอนุมัติแล้วเมื่อลงนามครบ"],
            ["13", "พัสดุ", "สร้าง PO", "ผู้ขายเป็นผู้ชนะ ใบยังเป็นฉบับร่าง"],
            [
                "14",
                "พัสดุ",
                "ที่ใบขอซื้อ แท็บใบสั่งซื้อ กด พิมพ์ PDF แล้วกด ส่งเข้าแอปผู้ขาย",
                "สถานะการยืนยันเป็น รอผู้ขายยืนยัน หลังผู้ขายลงนามจะเป็น ผู้ขายยืนยันแล้ว",
            ],
            [
                "15",
                "พัสดุ",
                "เปิดใบสั่งซื้อที่ยืนยันแล้ว กด สร้างใบตรวจรับ ตรวจรายการและคณะกรรมการ แล้วกดตรวจรับ",
                "บันทึกรับมอบงานเป็น Accepted ตามบทที่ 10",
            ],
        ],
        [1.4, 2.8, 6.2, 5.8],
    )
    callout(
        doc,
        "จบรอบอบรมเมื่อไร",
        "ผู้เรียนอธิบายได้ว่าทำไมเปิด PO จากใบขอซื้อประเภทนี้ไม่ได้โดยตรง "
        "สร้างใบขอซื้อจนอนุมัติได้ ส่งเข้า e-GP จนได้ผู้ชนะ เปิด PO ผู้ชนะได้ "
        "และบันทึกตรวจรับหลังผู้ขายยืนยัน โดยไม่ต้องให้วิทยากรกดแทน",
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
            ["สร้าง PO", "เปิดใบสั่งซื้อให้ผู้ชนะ", "หลังรายงานผลอนุมัติ"],
            ["ใบสั่งซื้อ / PO", "คำสั่งซื้อที่ยืนยันกับผู้ขาย", "Purchase Order"],
            [
                "บันทึกรับมอบงาน",
                "ใบตรวจรับหลังผู้ขายส่งของ",
                "เมนูจัดซื้อ สร้างจากปุ่มสร้างใบตรวจรับบนใบสั่งซื้อ",
            ],
            [
                "ตรวจรับ",
                "ปิดผลว่าของที่ส่งมาตรงใบสั่งซื้อ",
                "สถานะ Draft แล้วเป็น Accepted",
            ],
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
