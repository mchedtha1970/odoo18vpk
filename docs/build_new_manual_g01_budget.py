#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the NEW Thai Word User Manual for Group 1: งบประมาณ (Budget)
Strictly aligned with:
  ภาพรวมการทำรายการในระบบ ERP ตามกลุ่มงาน.pdf

Features:
- Reference code in parentheses at the end of every heading: (2.1), (1.1), (1.2), (1.3), (1.4)
- Step-by-step interleaved screenshots: EVERY step (ขั้นตอนที่ 1, 2, 3...) is immediately
  followed by a visual screenshot and pointer caption so users can follow along easily.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
DOC_VERSION = "2.5"
OUT_DIR = ROOT / "คู่มือการใช้งาน-ตามผังภาพรวม"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "01-คู่มือการใช้งาน-กลุ่มงานงบประมาณ.docx"
FIG = ROOT / "manual_assets" / "figures"

PRIMARY = RGBColor(0x1D, 0x4E, 0xD8)  # Blue matching Lane 1 (#1d4ed8)
TEAL = RGBColor(0x0F, 0x76, 0x6E)     # Teal matching Lane 2 (#0f766e)
DARK_NAVY = RGBColor(0x0F, 0x29, 0x42)
SLATE = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
RED = RGBColor(0xC6, 0x28, 0x28)
AMBER = RGBColor(0xB4, 0x53, 0x09)
GREEN = RGBColor(0x15, 0x80, 0x3D)

HEADER_FILL = "1D4ED8"
SUBHEADER_FILL = "0F2942"
META_FILL = "EFF6FF"
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


def set_cell_border(cell, color="CBD5E1"):
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


def set_narrow_cell_margin(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), "90")
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def cell_text(cell, text, size=11, bold=False, color=SLATE, align="left", fill=None):
    if fill:
        shade_cell(cell, fill)
    set_cell_border(cell)
    set_narrow_cell_margin(cell)
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


def make_table(doc, headers, rows, col_widths=None, header_fill=HEADER_FILL):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, h in enumerate(headers):
        cell_text(table.rows[0].cells[i], h, 11, True, WHITE, "center", header_fill)
    for r, row in enumerate(rows, 1):
        fill = "F8FAFC" if r % 2 == 0 else "FFFFFF"
        for c, val in enumerate(row):
            cell_text(table.rows[r].cells[c], val, 11, False, SLATE, "left", fill)
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table


def add_border_line(paragraph, edge="bottom", color="1D4ED8", size="12"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{edge}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), size)
    el.set(qn("w:space"), "6")
    el.set(qn("w:color"), color)
    pBdr.append(el)
    pPr.append(pBdr)


def page_title(doc, text, center=False):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(12)
    add_text(p, text, 18, True, PRIMARY)
    return p


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run(
            run,
            17 if level == 1 else 14 if level == 2 else 12.5,
            True,
            PRIMARY if level == 1 else DARK_NAVY,
        )
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    if level == 1:
        add_border_line(p, "bottom", "1D4ED8", "12")
    return p


def body(doc, text, size=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.18
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
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    label = text if text.startswith("▲") else f"▲ {text}"
    add_text(p, label, 10, False, MUTED)


def picture(doc, name_or_path, width_cm=15.8, cap=""):
    path = Path(name_or_path)
    if not path.is_absolute():
        path = FIG / name_or_path
    if not path.exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    if cap:
        caption(doc, cap)


def step_with_pic(doc, num, text, img_name=None, width_cm=15.8, cap="", sub_bullets=None):
    """Add a numbered step box/line, optional sub-bullets, and immediately show its screenshot below."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    add_text(p, f"ขั้นตอนที่ {num}  ", 12, True, PRIMARY)
    add_text(p, text, 12, False, SLATE)
    if sub_bullets:
        bullets(doc, sub_bullets, numbered=False)
    if img_name:
        picture(doc, img_name, width_cm, cap)


def callout(doc, title, text, tone="info"):
    fill = {"info": "EFF6FF", "warn": "FEF3C7", "danger": "FEE2E2", "ok": "DCFCE7"}[tone]
    border = {"info": "93C5FD", "warn": "FCD34D", "danger": "FCA5A5", "ok": "86EFAC"}[tone]
    title_color = {"info": PRIMARY, "warn": AMBER, "danger": RED, "ok": GREEN}[tone]
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    shade_cell(cell, fill)
    set_cell_border(cell, border)
    set_narrow_cell_margin(cell)
    p1 = cell.paragraphs[0]
    add_text(p1, title, 11.5, True, title_color)
    p2 = cell.add_paragraph()
    add_text(p2, text, 11.5, False, SLATE)
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_after = Pt(3)
    doc.add_paragraph()


def task_summary_card(doc, code, title, desc, doc_name, menu_path, role, header_fill=HEADER_FILL):
    """Render a summary card with the reference code in parentheses at the end of the title."""
    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    rows_data = [
        ("หัวข้องานตามผังภาพรวม", f"{title} ({code})", True, header_fill, WHITE),
        ("รายละเอียดงาน (Task)", desc, False, "EFF6FF", SLATE),
        ("เอกสารในระบบ (Document)", doc_name, True, "FFFFFF", DARK_NAVY),
        ("เมนูใช้งาน / ผู้รับผิดชอบ", f"เมนู: {menu_path}   |   ผู้ปฏิบัติงาน: {role}", False, "F8FAFC", SLATE),
    ]
    for idx, (k, v, is_bold, bg, fg) in enumerate(rows_data):
        c0 = table.rows[idx].cells[0]
        c1 = table.rows[idx].cells[1]
        c0.width = Cm(4.8)
        c1.width = Cm(11.6)
        if idx == 0:
            cell_text(c0, k, 11, True, WHITE, "left", SUBHEADER_FILL)
            cell_text(c1, v, 11.5, True, fg, "left", bg)
        else:
            cell_text(c0, k, 10.5, True, DARK_NAVY, "left", "F1F5F9")
            cell_text(c1, v, 11, is_bold, fg, "left", bg)
    doc.add_paragraph()


def header_footer(doc):
    section = doc.sections[0]
    section.header_distance = Cm(0.8)
    section.footer_distance = Cm(1.0)
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_text(hp, "คู่มือการใช้งานระบบ ERP (VPK) — กลุ่มงานงบประมาณ (2.1, 1.1 – 1.4)", 8.5, False, MUTED)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_border_line(fp, "top", "CBD5E1", "6")
    add_text(fp, "โรงพยาบาลวชิระภูเก็ต · คู่มือปฏิบัติงานระบบงบประมาณ (2.1, 1.1 – 1.4) | หน้า ", 9, False, MUTED)
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
    pf.space_after = Pt(6)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.18


def build():
    doc = Document()
    setup_styles(doc)
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    header_footer(doc)

    # ==================== COVER PAGE ====================
    if LOGO.exists():
        logo_p = doc.add_paragraph()
        logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo_p.paragraph_format.space_before = Pt(8)
        logo_p.paragraph_format.space_after = Pt(6)
        logo_p.add_run().add_picture(str(LOGO), width=Cm(3.2))

    hosp = doc.add_paragraph()
    hosp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hosp.paragraph_format.space_after = Pt(0)
    add_text(hosp, "โรงพยาบาลวชิระภูเก็ต", 16, True, DARK_NAVY)

    hosp_en = doc.add_paragraph()
    hosp_en.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hosp_en.paragraph_format.space_after = Pt(14)
    add_text(hosp_en, "VACHIRAPHUKET HOSPITAL — ERP (VPK)", 10.5, True, MUTED)

    badge_p = doc.add_paragraph()
    badge_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    badge_p.paragraph_format.space_after = Pt(6)
    add_text(badge_p, "คู่มือการปฏิบัติงานตามผังสรุปภาพรวมการบันทึกรายการในระบบ ERP", 12.5, True, PRIMARY)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)
    add_text(title, "คู่มือการใช้งาน : กลุ่มงานงบประมาณ", 25, True, DARK_NAVY)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(16)
    add_text(
        sub,
        "การทำแผนตั้งของบประมาณประจำปี (2.1) · การรับคำขอตั้งแผนจากหน่วยงาน (1.1) · การรวบรวม พิจารณาจัดสรร (1.2)\n"
        "การส่งอนุมัติ ประกาศแจ้งงบที่อนุมัติ (1.3) · การติดตามการใช้งบผ่าน Dashboard (1.4)",
        11.0,
        False,
        SLATE,
    )

    info = [
        ("รหัสเอกสาร", "UM-ERP-VPK-G01"),
        ("เอกสารอ้างอิงหลัก", "ภาพรวมการทำรายการในระบบ ERP ตามกลุ่มงาน.pdf"),
        (
            "หัวข้อที่ครอบคลุม",
            "ทำแผนตั้งของบประมาณประจำปี (2.1), รับคำขอตั้งแผนจากหน่วยงาน (1.1), รวบรวม พิจารณาจัดสรร (1.2), "
            "ส่งอนุมัติ ประกาศแจ้งงบที่อนุมัติ (1.3), ติดตามการใช้งบผ่าน Dashboard (1.4)",
        ),
        ("โมดูลในระบบ", "vpk_budget, vpk_procurement_auto_pr, vpk_procurement_action_plan"),
        ("กลุ่มผู้ใช้งาน", "หน่วยงานผู้ขอตั้งงบประมาณ, เจ้าหน้าที่กลุ่มงานงบประมาณ และผู้บริหาร"),
        ("รูปแบบคู่มือ", "Step-by-Step พร้อมภาพหน้าจอประกอบใต้ทุกขั้นตอน"),
        ("เวอร์ชันเอกสาร", f"{DOC_VERSION} (วันที่ 20 ตุลาคม พ.ศ. 2569)"),
    ]
    table = doc.add_table(rows=len(info), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(info):
        cell_text(table.rows[i].cells[0], k, 10.5, True, PRIMARY, "left", META_FILL)
        cell_text(table.rows[i].cells[1], v, 10.5, False, SLATE, "left", "FFFFFF")
        table.rows[i].cells[0].width = Cm(4.6)
        table.rows[i].cells[1].width = Cm(11.8)

    doc.add_page_break()

    # ==================== TABLE OF CONTENTS & OVERVIEW ====================
    page_title(doc, "สารบัญและโครงสร้างคู่มือตามผังภาพรวม")
    body(
        doc,
        "คู่มือฉบับนี้จัดทำขึ้นโดยอ้างอิงตามเอกสาร “ภาพรวมการทำรายการในระบบ ERP ตามกลุ่มงาน.pdf” "
        "โดยระบุหมายเลขหัวข้ออ้างอิงจากผังภาพรวมไว้ในวงเล็บต่อท้ายชื่อหัวข้อของแต่ละบท และแสดงภาพหน้าจอประกอบใต้ทุกขั้นตอนเพื่อให้ผู้ใช้งานทำตามได้ทันที ดังนี้:",
    )

    make_table(
        doc,
        ["บทในคู่มือ", "หัวข้อในคู่มือ (พร้อมรหัสอ้างอิงผังภาพรวมต่อท้าย)", "งานที่ปฏิบัติในระบบ (Tasks)", "เอกสารในระบบ (Documents)"],
        [
            [
                "บทที่ 1",
                "การทำแผนตั้งของบประมาณประจำปี (2.1)",
                "บันทึกคำขอตั้งงบ 4 แบบ (วัสดุ/ครุภัณฑ์/ก่อสร้าง/โครงการ)",
                "ใบคำขอตั้งงบประมาณ",
            ],
            [
                "บทที่ 2",
                "การรับคำขอตั้งแผนจากหน่วยงาน (1.1)",
                "รับคำขอตั้งงบ(ในแผน/นอกแผน)",
                "ใบคำขอตั้งงบประจำปี / นอกแผน",
            ],
            [
                "บทที่ 3",
                "การรวบรวม พิจารณาจัดสรร (1.2)",
                "รวบรวมคำขอ พิจารณาจัดสรรงบประมาณและแผนจัดซื้อ",
                "รายละเอียดการขอตั้งแผนงบประมาณ",
            ],
            [
                "บทที่ 4",
                "การส่งอนุมัติ ประกาศแจ้งงบที่อนุมัติ (1.3)",
                "ส่งอนุมัติแผนงบประมาณ และประกาศแจ้งวงเงินที่อนุมัติ",
                "สรุปแผนงบที่จัดสรรและอนุมัติ",
            ],
            [
                "บทที่ 5",
                "การติดตามการใช้งบผ่าน Dashboard (1.4)",
                "ติดตามการใช้งบ ตรวจงบ PR (4.4) กันงบ & ตัดงบจริง",
                "Budget Dashboard, ผลตรวจงบ (แท็บ 4.4)",
            ],
        ],
        [2.0, 5.2, 5.0, 4.2],
    )

    picture(
        doc,
        "fig_erp_overview_page1.png",
        16.4,
        "ภาพที่ 1  ผังสรุปภาพรวมการบันทึกรายการในระบบ ERP ของกลุ่มงานต่างๆ (เอกสารอ้างอิง: ภาพรวมการทำรายการในระบบ ERP ตามกลุ่มงาน.pdf)",
    )

    doc.add_page_break()

    # ==================== CHAPTER 1 (2.1) ====================
    heading(doc, "บทที่ 1 การทำแผนตั้งของบประมาณประจำปี (2.1)", 1)
    task_summary_card(
        doc,
        code="2.1",
        title="ทำแผนตั้งของบประมาณประจำปี",
        desc="บันทึกคำขอตั้งงบ 4 แบบ (วัสดุ / ครุภัณฑ์ / ก่อสร้าง / โครงการ) และกดส่งใบคำขอให้หน่วยงบประมาณ",
        doc_name="ใบคำขอตั้งงบประมาณ (departmental.budget.request)",
        menu_path="งบประมาณ → บันทึกคำของบ → แบบฟอร์มตั้งงบวัสดุ / ครุภัณฑ์ / ก่อสร้าง / โครงการ",
        role="เจ้าหน้าที่หน่วยงานต่างๆ (ผู้ขอตั้งงบประมาณ)",
        header_fill="0F766E",
    )

    heading(doc, "1.1 การเข้าสู่ระบบและเลือกเมนูแบบฟอร์มคำของบทั้ง 4 ประเภท (2.1)", 2)
    body(
        doc,
        "หน่วยงานเริ่มต้นจัดทำแผนตั้งของบประมาณประจำปีโดยเข้าสู่ระบบด้วยบัญชีผู้ใช้งานของหน่วยงาน แล้วเปิดเมนู “งบประมาณ → บันทึกคำของบ” ซึ่งแบ่งออกเป็น 4 แบบฟอร์มตามประเภทงบประมาณ",
    )

    step_with_pic(
        doc,
        num=1,
        text="เปิดเว็บบราว์เซอร์เข้าสู่ระบบ ERP ของโรงพยาบาล กรอกชื่อผู้ใช้และรหัสผ่านของหน่วยงาน แล้วคลิกปุ่มเข้าสู่ระบบ",
        img_name="Screenshot_bud_step1_login.png",
        width_cm=13.5,
        cap="ภาพที่ 2  หน้าจอเข้าสู่ระบบ ERP สำหรับผู้ใช้งานหน่วยงาน (2.1)",
    )

    step_with_pic(
        doc,
        num=2,
        text="ที่แถบเมนูด้านซ้าย คลิกเลือกแอปพลิเคชัน “งบประมาณ” จากนั้นคลิกเมนู “บันทึกคำของบ” ระบบจะแสดงเมนูย่อยแบบฟอร์มทั้ง 4 ประเภท ให้เลือกคลิกให้ตรงกับประเภทงบที่จะขอ",
        img_name="Screenshot_bud_forms_menu.png",
        width_cm=4.8,
        cap="ภาพที่ 3  การเลือกเมนูย่อยแบบฟอร์มคำของบทั้ง 4 ประเภท ภายใต้เมนูบันทึกคำของบ (2.1)",
    )

    picture(
        doc,
        "fig_forms.png",
        15.8,
        "ภาพที่ 4  สรุปความแตกต่างของแบบฟอร์มคำขอตั้งงบประมาณทั้ง 4 ประเภท (2.1)",
    )

    make_table(
        doc,
        ["เมนูแบบฟอร์มคำของบ", "ใช้สำหรับขอตั้งงบอะไร", "ข้อมูลสำคัญที่ต้องระบุในรายการ"],
        [
            [
                "1. แบบฟอร์มตั้งงบวัสดุ",
                "ยา เวชภัณฑ์มิใช่ยา วัสดุการแพทย์ วัสดุวิทยาศาสตร์ วัสดุทั่วไป",
                "กลุ่มงบประมาณ-วัสดุ, ประเภทวัสดุย่อย, รายการสินค้า, หน่วยนับ, ปริมาณที่ขอ, ราคาต่อหน่วย และเหตุผล",
            ],
            [
                "2. แบบฟอร์มครุภัณฑ์",
                "ครุภัณฑ์การแพทย์ เครื่องมือ คอมพิวเตอร์ ครุภัณฑ์สำนักงาน",
                "หมวดงบประมาณ, กลุ่มครุภัณฑ์, รหัสครุภัณฑ์, จำนวนที่ขอ (ซื้อใหม่/ทดแทน/ขอเพิ่ม), ราคาต่อหน่วย และคำชี้แจง",
            ],
            [
                "3. แบบฟอร์ม ก่อสร้าง",
                "งานซ่อมแซม ต่อเติม ปรับปรุงอาคารและสิ่งก่อสร้าง",
                "รายการงานก่อสร้าง, พื้นที่ใช้งาน (ตร.ม.), สถานที่ก่อสร้าง, ลักษณะงาน (ปรับปรุง/ขยายต่อเติม) และราคา",
            ],
            [
                "4. แบบฟอร์มโครงการ",
                "ค่าใช้จ่ายในการจัดโครงการ อบรม กิจกรรมพัฒนาคุณภาพ",
                "ชื่อโครงการ, รายละเอียดค่าใช้จ่าย, ระยะเวลาดำเนินการ, กลุ่มเป้าหมาย, วัตถุประสงค์ และผู้รับผิดชอบ",
            ],
        ],
        [4.0, 5.0, 7.4],
        header_fill="0F766E",
    )

    heading(doc, "1.2 ขั้นตอนการบันทึกคำขอแบบที่ 1 : แบบฟอร์มตั้งงบวัสดุ (2.1)", 2)
    step_with_pic(
        doc,
        num=1,
        text="คลิกเมนู “บันทึกคำของบ → แบบฟอร์มตั้งงบวัสดุ” แล้วกดปุ่ม “สร้าง (New)” จากนั้นกรอกข้อมูลส่วนหัวเอกสารให้ครบถ้วน ได้แก่ หน่วยงาน/ศูนย์ต้นทุน, ชื่อแผนงบประมาณประจำปี และแหล่งเงิน (เช่น เงินบำรุง) โดยระบบจะกำหนดช่อง “แบบฟอร์มคำของบ” เป็น “แบบฟอร์มตั้งงบวัสดุ” ให้อัตโนมัติ",
        img_name="Screenshot_bud_new_material.png",
        width_cm=15.8,
        cap="ภาพที่ 5  ขั้นตอนที่ 1 เลือกเมนูแบบฟอร์มตั้งงบวัสดุและกรอกข้อมูลส่วนหัวเอกสาร (2.1)",
    )

    step_with_pic(
        doc,
        num=2,
        text="เลือก “ประเภทการตั้งงบประมาณ” ในส่วนหัวเอกสารว่าเป็น “ในแผน” หรือ “นอกแผน” (ค่าเริ่มต้นคือ ในแผน) โดยหากเป็นการขอตั้งงบประมาณประจำปีตามรอบปกติให้เลือก “ในแผน” แต่หากในระหว่างปีงบประมาณที่ตั้งไว้เดิมไม่เพียงพอและจำเป็นต้องตั้งแผนงบประมาณเพิ่มเติมเพื่อขออนุมัติดำเนินการจัดซื้อต่อไป ให้คลิกเลือกเป็น “นอกแผน”",
        img_name="Screenshot_bud_plan_type_option.png",
        width_cm=15.8,
        cap="ภาพที่ 6  ตัวเลือก “ประเภทการตั้งงบประมาณ : ในแผน / นอกแผน” ในส่วนหัวของใบคำขอตั้งงบประมาณทุกแบบฟอร์ม (กรอบสีแดง) (2.1)",
    )

    callout(
        doc,
        "การเลือกประเภทการตั้งงบประมาณ: “ในแผน” และ “นอกแผน” (2.1)",
        "• ในแผน (In-Plan): ใช้สำหรับการจัดทำคำขอตั้งแผนงบประมาณประจำปีตามรอบปกติของหน่วยงาน\n"
        "• นอกแผน (Off-Plan): ใช้ในกรณีที่งบประมาณที่ตั้งไว้เดิมในแผนไม่เพียงพอ หรือมีความจำเป็นเร่งด่วนต้องขอตั้งงบประมาณเพิ่มเติมระหว่างปี เมื่อหน่วยงบประมาณพิจารณาจัดสรรและกดอนุมัติใบคำขอตั้งงบนอกแผนแล้ว ยอดงบประมาณที่ได้รับอนุมัติจะถูกรวมเพิ่มเข้าไปในวงเงินแผนงบประมาณประจำปีทันที ทำให้หน่วยงานสามารถกดตรวจสอบงบประมาณในใบขอซื้อ (PR) ผ่านและดำเนินการจัดซื้อต่อไปได้",
        "info",
    )

    step_with_pic(
        doc,
        num=3,
        text="ในส่วน “โหลดรายการวัสดุ” เลือกวิธีเพิ่มรายการสินค้าเข้าสู่ใบคำขอ ซึ่งทำได้ 3 วิธีตามความสะดวก:",
        img_name="Screenshot_bud_load_material_btns.png",
        width_cm=14.5,
        cap="ภาพที่ 7  ขั้นตอนที่ 3 ปุ่มตัวช่วย “โหลดรายการ” จากฐานข้อมูลระบบ หรือ “โหลดจาก Excel” ในส่วนโหลดรายการวัสดุ (2.1)",
        sub_bullets=[
            "วิธีที่ 1 โหลดรายการจากระบบ: คลิกปุ่ม “โหลดรายการ” เลือกหมวดงบประมาณวัสดุที่ต้องการ ระบบจะดึงรหัสสินค้า ชื่อรายการ และหน่วยนับมาให้ทั้งหมด",
            "วิธีที่ 2 โหลดจากไฟล์ Excel: คลิกปุ่ม “โหลดจาก Excel” เพื่อดาวน์โหลดไฟล์แม่แบบมากรอกปริมาณที่ขอใน Excel แล้วอัปโหลดกลับเข้าระบบ (ดูรายละเอียดในขั้นตอนที่ 4 และ 5)",
            "วิธีที่ 3 เพิ่มทีละบรรทัด: คลิก “เพิ่มรายการ” ในตารางแท็บรายการวัสดุโดยตรง",
        ],
    )

    step_with_pic(
        doc,
        num=4,
        text="กรณีเลือก “โหลดจาก Excel”: ระบบจะเปิดหน้าต่างป๊อปอัป ให้ทำตามลำดับ (1) เลือก “หมวดงบประมาณ” ที่ต้องการ (2) คลิกปุ่ม “ดาวน์โหลดแบบฟอร์ม” เพื่อรับไฟล์ template-รายการวัสดุ.xlsx (3) เมื่อกรอกข้อมูลใน Excel เสร็จแล้ว คลิกปุ่ม “อัปโหลดไฟล์ของคุณ” เพื่อแนบไฟล์กลับเข้ามา และ (4) คลิกปุ่มสีเขียว “นำเข้า”",
        img_name="Screenshot_bud_excel_wizard.png",
        width_cm=13.8,
        cap="ภาพที่ 8  ขั้นตอนที่ 4 หน้าต่าง “โหลดรายการจาก Excel” แสดงลำดับ 1 เลือกหมวดงบ → 2 ดาวน์โหลดแบบฟอร์ม → 3 อัปโหลดไฟล์ → 4 กดนำเข้า (2.1)",
    )

    step_with_pic(
        doc,
        num=5,
        text="หน้าตาของไฟล์แม่แบบ “template-รายการวัสดุ.xlsx” ที่ดาวน์โหลดออกมา: ระบบจะดึงคอลัมน์ A (รหัสสินค้า), B (รายการ), C (หน่วยนับ), D (ราคาต่อหน่วย) และ G (หมวดงบประมาณ) มาให้เรียบร้อยแล้ว ให้ผู้ใช้งานกรอกตัวเลขเฉพาะในคอลัมน์ E “ปริมาณที่ขอ” (และคอลัมน์ F หมายเหตุ ถ้ามี) เฉพาะแถวรายการที่ต้องการขอตั้งงบ ส่วนแถวที่เว้นว่างไว้ระบบจะข้ามไม่นำเข้าให้อัตโนมัติ",
        img_name="Screenshot_bud_excel_template.png",
        width_cm=16.0,
        cap="ภาพที่ 9  ขั้นตอนที่ 5 ตัวอย่างไฟล์แม่แบบ Excel (template-รายการวัสดุ.xlsx) กรอกเฉพาะคอลัมน์ E “ปริมาณที่ขอ” ในแถวที่ต้องการ (2.1)",
    )

    step_with_pic(
        doc,
        num=6,
        text="เมื่อรายการวัสดุถูกโหลดเข้ามาในแท็บ “รายการวัสดุ” แล้ว ให้ตรวจสอบ “หน่วยนับ” รวมถึงตัวเลขในช่อง “ปริมาณที่ของบในปี 2570” และ “ราคา/หน่วยนับ” ให้ครบทุกบรรทัด ระบบจะคำนวณ “มูลค่าที่ของบ” ให้อัตโนมัติ",
        img_name="Screenshot_bud_request_lines.png",
        width_cm=15.8,
        cap="ภาพที่ 10  ขั้นตอนที่ 6 ตรวจสอบหน่วยนับ ปริมาณที่ขอ และราคาต่อหน่วยในแท็บรายการวัสดุ (กรอบสีแดง) (2.1)",
    )

    step_with_pic(
        doc,
        num=7,
        text="คลิกสลับไปที่แท็บ “แบบตั้งงบภาพรวม” เพื่อตรวจสอบยอดรวมคำขอตั้งแผนปีงบประมาณที่ระบบสรุปแยกตามหมวดหมู่ให้ และพิมพ์ “เหตุผลประกอบคำขอตั้งงบ” ในช่องด้านล่าง แล้วกดบันทึก",
        img_name="Screenshot_bud_request_summary.png",
        width_cm=15.8,
        cap="ภาพที่ 11  ขั้นตอนที่ 7 ตรวจสอบยอดสรุปในแท็บแบบตั้งงบภาพรวมและระบุเหตุผลประกอบคำขอ (2.1)",
    )

    heading(doc, "1.3 ขั้นตอนการบันทึกคำขอแบบที่ 2 : แบบฟอร์มครุภัณฑ์ (2.1)", 2)
    step_with_pic(
        doc,
        num=1,
        text="คลิกเมนู “บันทึกคำของบ → แบบฟอร์มครุภัณฑ์” แล้วกดปุ่ม “สร้าง (New)” ระบบจะตั้งค่าแบบฟอร์มคำของบเป็น “แบบฟอร์มครุภัณฑ์” ให้อัตโนมัติ",
        img_name="Screenshot_bud_new_asset.png",
        width_cm=15.8,
        cap="ภาพที่ 11  ขั้นตอนที่ 1 เปิดหน้าสร้างใบคำขอจากเมนูแบบฟอร์มครุภัณฑ์ (2.1)",
    )

    step_with_pic(
        doc,
        num=2,
        text="กรอกข้อมูลส่วนหัวเอกสาร ได้แก่ หน่วยงาน/ศูนย์ต้นทุน, ชื่อแผนงบประมาณประจำปี และแหล่งเงิน จากนั้นคลิกปุ่ม “โหลดรายการ” เพื่อดึงบัญชีครุภัณฑ์ หรือกดเพิ่มรายการเอง",
        img_name="Screenshot_bud_asset_header.png",
        width_cm=15.8,
        cap="ภาพที่ 12  ขั้นตอนที่ 2 กรอกส่วนหัวเอกสารคำของบครุภัณฑ์และคลิกปุ่มโหลดรายการ (กรอบสีแดง) (2.1)",
    )

    step_with_pic(
        doc,
        num=3,
        text="กรณีคลิกปุ่ม “โหลดรายการ” จะปรากฏหน้าต่างป๊อปอัป ให้คลิกเลือก “หมวดงบประมาณ” ของครุภัณฑ์ที่ต้องการ (เลือกได้มากกว่า 1 หมวด) แล้วคลิกปุ่มสีเขียว “โหลด”",
        img_name="Screenshot_bud_asset_wizard.png",
        width_cm=11.5,
        cap="ภาพที่ 13  ขั้นตอนที่ 3 เลือกหมวดงบประมาณครุภัณฑ์ในหน้าต่างป๊อปอัปแล้วกดปุ่มโหลด (2.1)",
    )

    step_with_pic(
        doc,
        num=4,
        text="ในแท็บ “แบบตั้งงบครุภัณฑ์” ตรวจสอบคอลัมน์ “รายละเอียด” (ซึ่งในบางครั้งคำอธิบายรายการครุภัณฑ์ที่จะซื้อจริงอาจแตกต่างจากชื่อมาตรฐานของ Data Master ในระบบที่โหลดมาตามหมวดหมู่ ผู้ใช้งานสามารถพิมพ์ปรับแก้ไขคำอธิบายในช่องรายละเอียดให้ตรงกับคุณลักษณะครุภัณฑ์ที่จะขอซื้อจริงได้ แต่ต้องเป็นรายการที่อยู่ในหมวดงบประมาณและกลุ่มครุภัณฑ์นั้นๆ ที่สอดคล้องกัน) จากนั้นกรอกจำนวนปัจจุบัน, อายุการใช้งาน และจำนวนที่ขอตั้งแยกตามลักษณะ (ขอซื้อใหม่ / ขอทดแทน / ขอเพิ่ม) พร้อมระบุราคาต่อหน่วย และเหตุผลคำชี้แจง ระบบจะคำนวณรวมจำนวนและงบประมาณที่ขอตั้งให้อัตโนมัติ",
        img_name="Screenshot_bud_asset_lines.png",
        width_cm=15.8,
        cap="ภาพที่ 14  ขั้นตอนที่ 4 ปรับแก้ไขคำอธิบายในช่องรายละเอียดให้ตรงกับรายการที่จะซื้อจริง (ภายใต้หมวดที่สอดคล้องกัน) และกรอกจำนวน/ราคาต่อหน่วย (2.1)",
    )

    callout(
        doc,
        "ข้อควรทราบเกี่ยวกับการแก้ไข “รายละเอียด” รายการครุภัณฑ์ให้ตรงกับของที่จะซื้อจริง (2.1)",
        "• ในบางครั้ง คำอธิบายรายการครุภัณฑ์ที่หน่วยงานต้องการจัดซื้อจริง อาจมีรายละเอียดหรือคุณลักษณะเฉพาะที่แตกต่างจากชื่อรายการมาตรฐาน (Master) ในระบบที่ดึงมาตามหมวดหมู่\n"
        "• ผู้ใช้งานสามารถพิมพ์ปรับแก้ไขข้อความในช่อง “รายละเอียด” บนบรรทัดรายการได้โดยตรง เพื่อให้ตรงกับรายการที่จะขอซื้อจริง\n"
        "• ข้อเน้นย้ำสำคัญ: รายการที่แก้ไขคำอธิบายนั้น จะต้องเป็นรายการครุภัณฑ์ที่อยู่ใน “หมวดงบประมาณ” และ “กลุ่มครุภัณฑ์/รหัสมาตรฐาน” เดียวกันที่สอดคล้องกันเท่านั้น ห้ามนำรายการข้ามหมวดหมู่มาใส่ปะปนกัน",
        "warn",
    )

    heading(doc, "1.4 ขั้นตอนการบันทึกคำขอแบบที่ 3 : แบบฟอร์มก่อสร้าง (2.1)", 2)
    step_with_pic(
        doc,
        num=1,
        text="คลิกเมนู “บันทึกคำของบ → แบบฟอร์ม ก่อสร้าง” แล้วกดปุ่ม “สร้าง (New)” ระบบจะเลือกแบบฟอร์มคำของบเป็น “แบบฟอร์ม ก่อสร้าง” ให้โดยอัตโนมัติ",
        img_name="Screenshot_bud_new_construction.png",
        width_cm=15.8,
        cap="ภาพที่ 15  ขั้นตอนที่ 1 เปิดหน้าสร้างใบคำขอจากเมนูแบบฟอร์มก่อสร้าง (2.1)",
    )

    step_with_pic(
        doc,
        num=2,
        text="กรอกข้อมูลส่วนหัวเอกสาร ได้แก่ หน่วยงาน/ศูนย์ต้นทุน, ชื่อแผนงบประมาณประจำปี และแหล่งเงิน ให้ครบถ้วน",
        img_name="Screenshot_bud_construction_header.png",
        width_cm=15.8,
        cap="ภาพที่ 16  ขั้นตอนที่ 2 กรอกข้อมูลส่วนหัวเอกสารใบคำขอตั้งงบก่อสร้าง (กรอบสีแดง) (2.1)",
    )

    step_with_pic(
        doc,
        num=3,
        text="ในแท็บ “แบบตั้งงบก่อสร้าง” คลิก “เพิ่มรายการ” แล้วระบุหมวดงบประมาณ, รายการ/ชื่อโครงการ, พื้นที่ใช้งาน (ตร.ม.), สถานที่ก่อสร้าง, หน่วยนับ, จำนวนที่ขอตั้ง, ราคาต่อหน่วย, ติ๊กเลือกลักษณะงาน (ขอปรับปรุง หรือ ขอขยาย/ต่อเติม) และระบุเหตุผลคำชี้แจง",
        img_name="Screenshot_bud_construction_lines.png",
        width_cm=15.8,
        cap="ภาพที่ 17  ขั้นตอนที่ 3 กรอกรายละเอียดงานก่อสร้าง พื้นที่ สถานที่ ราคา และลักษณะงานในแท็บแบบตั้งงบก่อสร้าง (2.1)",
    )

    heading(doc, "1.5 ขั้นตอนการบันทึกคำขอแบบที่ 4 : แบบฟอร์มโครงการ (2.1)", 2)
    step_with_pic(
        doc,
        num=1,
        text="คลิกเมนู “บันทึกคำของบ → แบบฟอร์มโครงการ” แล้วกดปุ่ม “สร้าง (New)” ระบบจะตั้งค่าแบบฟอร์มคำของบเป็น “แบบฟอร์มโครงการ” ให้อัตโนมัติ",
        img_name="Screenshot_bud_new_project.png",
        width_cm=15.8,
        cap="ภาพที่ 18  ขั้นตอนที่ 1 เปิดหน้าสร้างใบคำขอจากเมนูแบบฟอร์มโครงการ (2.1)",
    )

    step_with_pic(
        doc,
        num=2,
        text="กรอกข้อมูลส่วนหัวเอกสาร ได้แก่ หน่วยงาน/ศูนย์ต้นทุน, ชื่อแผนงบประมาณประจำปี และแหล่งเงิน ให้ครบถ้วน",
        img_name="Screenshot_bud_project_header.png",
        width_cm=15.8,
        cap="ภาพที่ 19  ขั้นตอนที่ 2 กรอกข้อมูลส่วนหัวเอกสารใบคำขอตั้งงบโครงการ (กรอบสีแดง) (2.1)",
    )

    step_with_pic(
        doc,
        num=3,
        text="ในแท็บ “แบบตั้งงบโครงการ” คลิก “เพิ่มรายการ” แล้วกรอกหมวดงบประมาณ, ชื่อโครงการ, รายละเอียดค่าใช้จ่าย, ระยะเวลาดำเนินการ, กลุ่มเป้าหมาย, จำนวนที่ขอตั้ง, ราคาต่อหน่วย, วัตถุประสงค์, ประโยชน์ที่คาดว่าจะได้รับ และผู้รับผิดชอบโครงการ",
        img_name="Screenshot_bud_project_lines.png",
        width_cm=15.8,
        cap="ภาพที่ 20  ขั้นตอนที่ 3 กรอกรายละเอียดโครงการ กลุ่มเป้าหมาย งบที่ขอ วัตถุประสงค์ และผู้รับผิดชอบ (2.1)",
    )

    heading(doc, "1.6 การกดส่งใบคำขอตั้งงบประมาณให้หน่วยงบประมาณ (2.1)", 2)
    step_with_pic(
        doc,
        num=1,
        text="เมื่อตรวจสอบรายการและเหตุผลครบถ้วนแล้ว ให้คลิกปุ่มสีเขียว “ส่งใบคำขอ” ที่มุมซ้ายบนของเอกสาร สถานะบนแถบขวาบนจะเปลี่ยนจาก “แบบร่าง” เป็น “ส่งหน่วยงบประมาณ” ทันที",
        img_name="Screenshot_bud_submit_btn.png",
        width_cm=15.5,
        cap="ภาพที่ 21  คลิกปุ่ม “ส่งใบคำขอ” (กรอบสีแดง) เพื่อส่งเอกสารจากสถานะแบบร่างไปยังหน่วยงบประมาณ (2.1)",
    )

    doc.add_page_break()

    # ==================== CHAPTER 2 (1.1) ====================
    heading(doc, "บทที่ 2 การรับคำขอตั้งแผนจากหน่วยงาน (1.1)", 1)
    task_summary_card(
        doc,
        code="1.1",
        title="รับคำขอตั้งแผนจากหน่วยงาน",
        desc="รับคำขอตั้งงบ(ในแผน/นอกแผน) จากหน่วยงานต่างๆ ที่ส่งเข้ามาในระบบ",
        doc_name="ใบคำขอตั้งงบประจำปี / นอกแผน (departmental.budget.request)",
        menu_path="งบประมาณ → รวบรวมคำของบ (หน่วยงบประมาณ)",
        role="เจ้าหน้าที่งานงบประมาณ",
    )

    heading(doc, "2.1 ขั้นตอนการตรวจสอบและกดรับเรื่องใบคำขอตั้งงบ (1.1)", 2)
    body(
        doc,
        "เมื่อหน่วยงานกดส่งใบคำขอตั้งงบประมาณ (ทั้งในแผนและนอกแผน) เข้ามาแล้ว เจ้าหน้าที่งานงบประมาณจะเข้าตรวจสอบความถูกต้องครบถ้วนและกดรับเรื่องตามขั้นตอนดังนี้:",
    )

    step_with_pic(
        doc,
        num=1,
        text="เข้าสู่ระบบด้วยบัญชีเจ้าหน้าที่งานงบประมาณ คลิกไอคอนแอปพลิเคชัน “งบประมาณ” ที่แถบเมนูด้านซ้าย",
        img_name="Screenshot_bud_step2_app.png",
        width_cm=4.5,
        cap="ภาพที่ 22  ขั้นตอนที่ 1 คลิกเข้าแอปพลิเคชัน “งบประมาณ” (1.1)",
    )

    step_with_pic(
        doc,
        num=2,
        text="ในแถบเมนูของระบบงบประมาณ คลิกเลือกเมนู “รวบรวมคำของบ (หน่วยงบประมาณ)” เพื่อเปิดดูรายการคำขอตั้งงบทั้งหมดที่ทุกหน่วยงานส่งเข้ามา",
        img_name="Screenshot_bud_menu_consolidate.png",
        width_cm=4.8,
        cap="ภาพที่ 23  ขั้นตอนที่ 2 คลิกเมนู “รวบรวมคำของบ (หน่วยงบประมาณ)” (กรอบสีแดง) (1.1)",
    )

    step_with_pic(
        doc,
        num=3,
        text="ในหน้ารายการ “รวบรวมคำของบ (หน่วยงบประมาณ)” ตรวจสอบรายการเอกสารใบคำขอตั้งงบ (เลขที่เอกสาร DBR/...) โดยสังเกตคอลัมน์ “ประเภทการตั้งงบ” ซึ่งจะแสดงป้ายสถานะแยกชัดเจนระหว่าง “ในแผน” (สีเขียว) และ “นอกแผน” (สีส้ม) พร้อมทั้งสามารถใช้ตัวกรองค้นหาแยกเฉพาะคำขอตั้งงบในแผนหรือนอกแผนได้ จากนั้นคลิกเปิดใบคำขอที่ต้องการตรวจสอบ",
        img_name="Screenshot_bud_list_plan_type.png",
        width_cm=15.8,
        cap="ภาพที่ 25  ขั้นตอนที่ 3 หน้ารายการรวมใบคำขอตั้งงบประมาณ แสดงคอลัมน์ “ประเภทการตั้งงบ (ในแผน / นอกแผน)” (กรอบสีแดง) (1.1)",
    )

    step_with_pic(
        doc,
        num=4,
        text="ตรวจสอบข้อมูลส่วนหัวเอกสาร (หน่วยงาน, แผนงบประมาณประจำปี, แบบฟอร์มคำของบ, แหล่งเงิน) และรายการคำขอว่าถูกต้องครบถ้วน จากนั้นคลิกปุ่ม “รับเรื่อง” บนแถบคำสั่งด้านบน สถานะของเอกสารจะเปลี่ยนจาก “ส่งหน่วยงบประมาณ” เป็น “รับเรื่องแล้ว” (หากข้อมูลไม่ครบถ้วน ให้คลิกปุ่ม “ตีกลับ” เพื่อให้หน่วยงานแก้ไข)",
        img_name="Screenshot_bud_request_form.png",
        width_cm=15.8,
        cap="ภาพที่ 25  ขั้นตอนที่ 4 ตรวจสอบรายละเอียดใบคำขอตั้งงบและสถานะบนแถบด้านขวาบนของเอกสาร (1.1)",
    )

    doc.add_page_break()

    # ==================== CHAPTER 3 (1.2) ====================
    heading(doc, "บทที่ 3 การรวบรวม พิจารณาจัดสรร (1.2)", 1)
    task_summary_card(
        doc,
        code="1.2",
        title="รวบรวม พิจารณาจัดสรร",
        desc="รวบรวมคำขอ พิจารณาจัดสรรงบประมาณและแผนจัดซื้อ",
        doc_name="รายละเอียดการขอตั้งแผนงบประมาณ",
        menu_path="งบประมาณ → รวบรวมคำของบ (หน่วยงบประมาณ) / รายละเอียดบรรทัดคำขอ",
        role="เจ้าหน้าที่งานงบประมาณ / คณะกรรมการพิจารณางบประมาณ",
    )

    heading(doc, "3.1 ขั้นตอนการเริ่มพิจารณาและบันทึกยอดจัดสรรรายบรรทัด (1.2)", 2)
    body(
        doc,
        "เมื่อใบคำขอตั้งงบอยู่ในสถานะ “รับเรื่องแล้ว” เจ้าหน้าที่งานงบประมาณจะรวบรวมข้อมูลเข้าที่ประชุมคณะกรรมการพิจารณางบประมาณ และบันทึกยอดวงเงินที่ได้รับการจัดสรรลงในระบบตามขั้นตอนดังนี้:",
    )

    step_with_pic(
        doc,
        num=1,
        text="เปิดใบคำขอตั้งงบที่มีสถานะ “รับเรื่องแล้ว” แล้วคลิกปุ่ม “เริ่มพิจารณา” ที่แถบด้านบนของเอกสาร สถานะของใบคำขอจะเปลี่ยนเป็น “อยู่ระหว่างพิจารณา” เพื่อเปิดให้บันทึกปรับเกลี่ยวงเงินจัดสรร",
        img_name="fig_request_flow.png",
        width_cm=15.8,
        cap="ภาพที่ 26  ขั้นตอนที่ 1 ผังลำดับการกดปุ่ม “รับเรื่อง” → “เริ่มพิจารณา” เพื่อเข้าสู่สถานะอยู่ระหว่างพิจารณา (1.2)",
    )

    step_with_pic(
        doc,
        num=2,
        text="ในตารางรายละเอียดรายการคำขอ (เช่น แท็บรายการวัสดุ หรือแท็บรายการครุภัณฑ์/ก่อสร้าง/โครงการ) ให้กรอกจำนวนและวงเงินที่ผ่านการพิจารณาจัดสรรลงในคอลัมน์ “ปริมาณที่จัดสรร” และ “มูลค่าที่จัดสรร (งบประมาณที่ได้รับ)” ทางด้านขวาสุดของทุกบรรทัด",
        img_name="Screenshot_bud_alloc_columns.png",
        width_cm=15.8,
        cap="ภาพที่ 27  ขั้นตอนที่ 2 กรอกตัวเลขในคอลัมน์ “ปริมาณที่จัดสรร” และ “มูลค่าที่จัดสรร” (กรอบสีแดงด้านขวาสุด) รายบรรทัด (1.2)",
    )

    step_with_pic(
        doc,
        num=3,
        text="คลิกเปิดแท็บ “แบบตั้งงบภาพรวม” เพื่อตรวจสอบยอดรวมคำขอตั้งแผนปีงบประมาณและเหตุผลประกอบคำขอเทียบกับกรอบวงเงินที่จัดสรร แล้วกดบันทึกเอกสาร",
        img_name="Screenshot_bud_request_summary.png",
        width_cm=15.8,
        cap="ภาพที่ 28  ขั้นตอนที่ 3 ตรวจสอบยอดรวมในแท็บแบบตั้งงบภาพรวมก่อนส่งอนุมัติ (1.2)",
    )

    callout(
        doc,
        "ข้อสำคัญในการใส่ยอดจัดสรร (1.2)",
        "• ยอดที่ใช้ควบคุมการเบิกจ่ายจริงในระบบคือ “งบประมาณที่ได้รับ (มูลค่าที่จัดสรร)” ไม่ใช่ยอดที่หน่วยงานขอ\n"
        "• ต้องระบุยอดจัดสรรให้ครบทุกบรรทัดรายการ (รายการที่ไม่ผ่านการอนุมัติให้ใส่ 0) มิฉะนั้นระบบจะไม่อนุญาตให้กดอนุมัติในบทที่ 4 (1.3)",
        "warn",
    )

    doc.add_page_break()

    # ==================== CHAPTER 4 (1.3) ====================
    heading(doc, "บทที่ 4 การส่งอนุมัติ ประกาศแจ้งงบที่อนุมัติ (1.3)", 1)
    task_summary_card(
        doc,
        code="1.3",
        title="ส่งอนุมัติ ประกาศแจ้งงบที่อนุมัติ",
        desc="ส่งอนุมัติแผนงบประมาณ และประกาศแจ้งวงเงินที่อนุมัติ",
        doc_name="สรุปแผนงบที่จัดสรรและอนุมัติ (crossovered.budget / vpk.procurement.annual.plan)",
        menu_path="งบประมาณ → รวบรวมคำของบ (กดอนุมัติ) และ สถานะคำของบประมาณ",
        role="หัวหน้ากลุ่มงานงบประมาณ / ผู้บริหารผู้อนุมัติแผน",
    )

    heading(doc, "4.1 ขั้นตอนการกดอนุมัติและประกาศแจ้งวงเงินที่อนุมัติ (1.3)", 2)
    body(
        doc,
        "เมื่อบันทึกยอดจัดสรรครบทุกบรรทัดรายการและผ่านความเห็นชอบจากผู้บริหารแล้ว งานงบประมาณจะทำการอนุมัติใบคำขอเพื่อซิงก์วงเงินเข้าสู่แผนงบประมาณประจำปีและประกาศแจ้งให้หน่วยงานทราบตามขั้นตอนดังนี้:",
    )

    step_with_pic(
        doc,
        num=1,
        text="เปิดใบคำขอตั้งงบประมาณที่มีสถานะ “อยู่ระหว่างพิจารณา” แล้วคลิกปุ่ม “อนุมัติ” บนแถบหัวเอกสาร สถานะที่มุมขวาบนจะเปลี่ยนเป็น “อนุมัติแล้ว” พร้อมแสดงยอดรวมในช่อง “งบประมาณที่ได้รับ” และผูกเข้ากับแผนงบประมาณประจำปี (Created Budget) โดยอัตโนมัติ",
        img_name="Screenshot_bud_alloc_header.png",
        width_cm=15.8,
        cap="ภาพที่ 29  ขั้นตอนที่ 1 เมื่อกดอนุมัติ สถานะเปลี่ยนเป็น “อนุมัติแล้ว” และแสดงยอด “งบประมาณที่ได้รับ” พร้อมแผนงบประมาณที่สร้างขึ้น (กรอบสีแดง) (1.3)",
    )

    step_with_pic(
        doc,
        num=2,
        text="ไปที่เมนู “การกำหนดค่า → งบประมาณประจำปี” (หรือเมนูรายการงบประมาณ) เพื่อตรวจสอบว่าวงเงินที่อนุมัติถูกซิงก์เข้าสู่แผนงบประมาณประจำปีเรียบร้อยแล้ว",
        img_name="Screenshot_bud_master_plan.png",
        width_cm=15.8,
        cap="ภาพที่ 30  ขั้นตอนที่ 2 ตรวจสอบแผนงบประมาณประจำปีที่ได้รับซิงก์วงเงินจากการอนุมัติคำของบ (1.3)",
    )

    step_with_pic(
        doc,
        num=3,
        text="ไปที่เมนู “สถานะคำของบประมาณ” เพื่อดูภาพรวมสรุปแผนงบที่จัดสรรและอนุมัติ (เปรียบเทียบยอดที่ขอตั้งกับยอดที่ได้รับจัดสรรแยกตามหมวดงบและรายหน่วยงาน) สำหรับใช้ประกาศแจ้งวงเงินที่อนุมัติให้แต่ละหน่วยงานนำไปใช้จ่าย",
        img_name="Screenshot_bud_status.png",
        width_cm=15.8,
        cap="ภาพที่ 31  ขั้นตอนที่ 3 หน้าจอสรุปแผนงบที่จัดสรรและอนุมัติ แสดงยอดอนุมัติแล้ว กราฟเทียบยอดจัดสรร และตารางรายหน่วยงาน (1.3)",
    )

    doc.add_page_break()

    # ==================== CHAPTER 5 (1.4) ====================
    heading(doc, "บทที่ 5 การติดตามการใช้งบผ่าน Dashboard (1.4)", 1)
    task_summary_card(
        doc,
        code="1.4",
        title="ติดตามการใช้งบผ่าน Dashboard",
        desc="ติดตามการใช้งบ ตรวจงบ PR (4.4) กันงบ & ตัดงบจริง",
        doc_name="Budget Dashboard, ผลตรวจงบ (แท็บ 4.4)",
        menu_path="งบประมาณ → ติดตามงบประมาณประจำปี และ แท็บตรวจสอบงบประมาณ (4.4) บนใบขอซื้อ (PR)",
        role="เจ้าหน้าที่งานงบประมาณ / ผู้บริหาร",
    )

    heading(doc, "5.1 ขั้นตอนการติดตามภาพรวมการใช้งบผ่าน Budget Dashboard (1.4)", 2)
    step_with_pic(
        doc,
        num=1,
        text="ไปที่เมนู “งบประมาณ → ติดตามงบประมาณประจำปี” เลือกตัวกรอง “ปีงบประมาณ”, “แหล่งเงิน” และ “หน่วยงาน” ที่มุมขวาบน ระบบจะแสดงการ์ดสรุปวงเงิน 5 ตัวชี้วัดหลัก (วงเงินที่ได้รับจัดสรร, เบิกจ่ายแล้ว, ก่อหนี้ผูกพัน, จองงบ PR และคงเหลือถึงสิ้นปีงบประมาณ) พร้อมแถบสถานะงบประมาณภาพรวม",
        img_name="Screenshot_bud_dashboard_cards.png",
        width_cm=15.8,
        cap="ภาพที่ 32  ขั้นตอนที่ 1 เลือกตัวกรองปีงบประมาณ/แหล่งเงิน/หน่วยงาน และดูการ์ดสรุป 5 ตัวชี้วัดบน Budget Dashboard (1.4)",
    )

    step_with_pic(
        doc,
        num=2,
        text="เลื่อนลงมาด้านล่างของหน้า Budget Dashboard เพื่อตรวจสอบกราฟผลเบิกจ่ายสะสมเทียบแผน, กราฟแท่งผลเบิกจ่ายตามกลุ่มงาน และตารางงบประมาณตามประเภทรายจ่าย หรือคลิกปุ่ม “ส่งออกรายงาน” มุมขวาบนเพื่อดาวน์โหลดข้อมูลออกเป็นไฟล์",
        img_name="Screenshot_bud_dashboard.png",
        width_cm=15.0,
        cap="ภาพที่ 33  ขั้นตอนที่ 2 ภาพรวม Budget Dashboard แบบเต็มหน้า แสดงกราฟเบิกจ่ายเทียบแผนและตารางรายจ่าย (1.4)",
    )

    step_with_pic(
        doc,
        num=3,
        text="ตรวจสอบความเคลื่อนไหวของวงเงินตามสูตรมาตรฐานของระบบ คือ “งบคงเหลือ = งบจัดสรร − (เบิกจ่ายจริง + ก่อหนี้ผูกพัน PO + จองงบ PR)” ซึ่งตัวเลขจะขยับอัตโนมัติตามสถานะเอกสารจัดซื้อและการเงิน",
        img_name="fig_formula.png",
        width_cm=15.5,
        cap="ภาพที่ 34  ขั้นตอนที่ 3 สูตรคำนวณงบคงเหลือและจังหวะการตัดยอดวงเงินในระบบ (1.4)",
    )

    heading(doc, "5.2 ขั้นตอนการตรวจงบใบขอซื้อ PR ในแท็บตรวจสอบงบประมาณ / แท็บ 4.4 (1.4)", 2)
    body(
        doc,
        "เมื่อคำขอตั้งงบประมาณได้รับอนุมัติและมียอดจัดสรรเข้าแผนงบประมาณประจำปีแล้ว หน่วยงานจะเปิดใบขอซื้อ (PR) ในระบบจัดซื้อจัดจ้างเพื่อใช้งบประมาณนั้น "
        "โดยระบบจะเชื่อมโยงข้อมูลการใช้งบประมาณตั้งแต่ใบขอซื้อ (PR) ไปยังใบสั่งซื้อ (PO) และใบตั้งเจ้าหนี้ (Vendor Bill) ตามรายละเอียดที่ระบุไว้ใน "
        "“คู่มือการใช้งานระบบงบประมาณ (รหัสเอกสาร UM-ERP-BUD-001)” บทที่ 6 (การใช้งบผ่านระบบจัดซื้อจัดจ้าง) และ บทที่ 7 (สูตรงบคงเหลือ) "
        "ควบคู่กับ “คู่มือการใช้งานระบบจัดซื้อจัดจ้าง (รหัสเอกสาร UM-ERP-PROC-001)” บทที่ 4 หัวข้อ 4.3.3 (แท็บตรวจสอบงบประมาณ) ดังนี้:",
    )

    picture(
        doc,
        "fig_spend_flow.png",
        15.8,
        "ภาพที่ 35  ลำดับผลกระทบต่องบประมาณตั้งแต่ใบขอซื้อ (PR) → ใบสั่งซื้อ (PO) → ใบตั้งเจ้าหนี้ (อ้างอิงคู่มือหน่วยงบประมาณ บทที่ 6) (1.4)",
    )

    callout(
        doc,
        "เอกสารคู่มืออ้างอิงสำหรับการตรวจสอบงบประมาณและการใช้งบ (1.4)",
        "• คู่มือการใช้งานระบบงบประมาณ (UM-ERP-BUD-001) ของหน่วยงบประมาณ:\n"
        "   - บทที่ 6 การใช้งบผ่านระบบจัดซื้อจัดจ้าง (ลำดับการกันงบ PR → ผูกพัน PO → ตัดงบใช้จริงจากบิล)\n"
        "   - บทที่ 7 สูตรงบคงเหลือ, หัวข้อ 7.1 ตัวอย่างตัวเลขตามจังหวะเวลา และ หัวข้อ 7.2 วิธีตรวจสอบเมื่อเช็คงบไม่ผ่าน\n"
        "• คู่มือการใช้งานกลุ่มงานงบประมาณ (UM-ERP-VPK-G01 ฉบับนี้):\n"
        "   - บทที่ 1 (2.1) หัวข้อ 1.2 ขั้นตอนที่ 2 การขอตั้งงบประมาณแบบ “นอกแผน” เมื่องบประมาณที่ตั้งไว้เดิมไม่เพียงพอ\n"
        "   - บทที่ 2 ถึง บทที่ 4 (1.1 – 1.3) ขั้นตอนการรับเรื่อง พิจารณาจัดสรร และอนุมัติงบนอกแผนเข้าสู่แผนประจำปี\n"
        "• คู่มือการใช้งานระบบจัดซื้อจัดจ้าง (UM-ERP-PROC-001):\n"
        "   - บทที่ 4 หัวข้อ 4.3.3 แท็บตรวจสอบงบประมาณ (ขั้นตอนการกดปุ่มเช็คงบประมาณขณะเปิดใบขอซื้อ PR)",
        "info",
    )

    body(
        doc,
        "รายละเอียดความหมายของยอดวงเงินแต่ละส่วนตาม “คู่มือการใช้งานระบบงบประมาณ (UM-ERP-BUD-001)” บทที่ 7 มีดังนี้:",
    )

    make_table(
        doc,
        ["รายการวงเงินในระบบ", "ความหมายตามคู่มือหน่วยงบประมาณ", "จังหวะที่เกิดผลในระบบ"],
        [
            [
                "งบจัดสรร (Allocated / Planned)",
                "วงเงินใช้จ่ายจริงที่หน่วยงบประมาณอนุมัติเข้าแผนประจำปี (รวมทั้งคำขอตั้งงบ “ในแผน” และ “นอกแผน”)",
                "เมื่อหน่วยงบประมาณกดปุ่ม “อนุมัติ” บนใบคำขอตั้งงบประมาณ (บทที่ 4 หัวข้อ 4.1)",
            ],
            [
                "จอง PR (PR Reserved)",
                "วงเงินที่กันไว้จากใบขอซื้อ (PR) ที่ผ่านการเช็คงบและส่งอนุมัติแล้ว แต่ยังไม่ได้ออกใบสั่งซื้อ",
                "เมื่อหน่วยงานกดเช็คงบผ่านเป็น “งบเพียงพอ” และกดส่งอนุมัติใบขอซื้อ (PR)",
            ],
            [
                "ผูกพัน PO (PO Committed)",
                "วงเงินที่ผูกพันตามใบสั่งซื้อหรือสัญญา (PO) ที่ยืนยันแล้ว และยังไม่ได้ตั้งเจ้าหนี้",
                "เมื่อเจ้าหน้าที่พัสดุกดยืนยันใบสั่งซื้อ (PO) ระบบจะย้ายยอดจากจอง PR มาเป็นผูกพัน PO",
            ],
            [
                "ใช้จริง (Actual / Practical)",
                "วงเงินเบิกจ่ายจริงที่ตัดจากใบแจ้งหนี้/ใบตั้งเจ้าหนี้ผู้ขายที่ผ่านรายการบัญชีแล้ว",
                "เมื่อการเงิน/บัญชีเจ้าหนี้กดยืนยันโพสต์ใบตั้งเจ้าหนี้ (Vendor Bill)",
            ],
            [
                "คงเหลือ (Available / Remaining)",
                "วงเงินที่ยังสามารถขอซื้อเพิ่มเติมได้ คำนวณจาก งบจัดสรร − ใช้จริง − จอง PR − ผูกพัน PO",
                "ระบบคำนวณอัตโนมัติแบบเรียลไทม์ทุกครั้งที่กดปุ่ม “เช็คงบประมาณ” และแสดงบน Dashboard",
            ],
        ],
        [4.0, 6.4, 6.0],
    )

    body(
        doc,
        "ตัวอย่างการเปลี่ยนแปลงตัวเลขวงเงินในแต่ละจังหวะ (อ้างอิงคู่มือหน่วยงบประมาณ บทที่ 7 หัวข้อ 7.1 สมมติได้รับจัดสรรงบวัสดุ 8,000 บาท และขอซื้อด้วยใบขอซื้อ PR จำนวน 3,000 บาท):",
    )

    make_table(
        doc,
        ["จังหวะการดำเนินงาน", "งบจัดสรร", "จอง PR", "ผูกพัน PO", "ใช้จริง", "งบคงเหลือ"],
        [
            ["1. เพิ่งอนุมัติคำของบเข้าแผน", "8,000", "0", "0", "0", "8,000"],
            ["2. กดเช็คงบบนใบขอซื้อ (PR) สถานะร่าง", "8,000", "0", "0", "0", "8,000"],
            ["3. ส่งอนุมัติใบขอซื้อ (PR) ยอด 3,000 บาท", "8,000", "3,000", "0", "0", "5,000"],
            ["4. พัสดุยืนยันใบสั่งซื้อ (PO) ทั้งจำนวน", "8,000", "0", "3,000", "0", "5,000"],
            ["5. การเงินโพสต์ใบตั้งเจ้าหนี้ 3,000 บาท", "8,000", "0", "0", "3,000", "5,000"],
        ],
        [6.0, 2.0, 2.0, 2.2, 2.0, 2.2],
    )

    body(
        doc,
        "ในการตรวจสอบงบประมาณของใบขอซื้อ (PR) ระบบใช้หลักเกณฑ์การจับคู่และตรวจสอบวงเงินจากแผนงบประมาณประจำปีตามขั้นตอนดังนี้:",
    )

    step_with_pic(
        doc,
        num=1,
        text="ตรวจสอบเงื่อนไข 4 มิติหลักบนใบขอซื้อ (PR) ให้ตรงกับแผนงบประมาณประจำปีที่ได้รับอนุมัติ (อ้างอิงคู่มือหน่วยงบประมาณ หัวข้อ 7.2) ได้แก่ (1) หน่วยงานที่ขอซื้อ/ศูนย์ต้นทุน (2) แหล่งเงิน (3) หมวดงบประมาณ และ (4) กลุ่มงบประมาณ-วัสดุ (กรณีขอซื้อวัสดุ) ทั้งนี้ สำหรับงบวัสดุและครุภัณฑ์ ระบบจะตรวจสอบลงลึกถึงระดับยอดจัดสรรรายสินค้า (Product Allocation) ส่วนงบก่อสร้างและโครงการจะตรวจสอบจากยอดรวมของหมวดงบประมาณ",
        img_name="fig_match_keys.png",
        width_cm=15.5,
        cap="ภาพที่ 36  ขั้นตอนที่ 1 เงื่อนไข 4 มิติที่ใช้จับคู่วงเงินระหว่างใบขอซื้อ (PR) กับแผนงบประมาณประจำปี (1.4)",
    )

    step_with_pic(
        doc,
        num=2,
        text="ที่ส่วนหัวของเอกสารใบขอซื้อ (PR) ขณะยังอยู่ในสถานะฉบับร่าง ให้คลิกปุ่มสีเขียว “เช็คงบประมาณ” เพื่อให้ระบบคำนวณและดึงยอดวงเงินคงเหลือล่าสุดจากแผนงบประมาณ (รวมยอดที่อนุมัติทั้งจากใบคำขอในแผนและนอกแผน)",
        img_name="Screenshot_TAB_44_check_btn.png",
        width_cm=4.2,
        cap="ภาพที่ 37  ขั้นตอนที่ 2 คลิกปุ่ม “เช็คงบประมาณ” ที่ส่วนหัวของใบขอซื้อ (PR) (1.4)",
    )

    step_with_pic(
        doc,
        num=3,
        text="คลิกเปิดแท็บ “ตรวจสอบงบประมาณ” (แท็บ 4.4 งานงบประมาณ) เพื่อดูรายละเอียดงบประมาณที่จองและงบคงเหลือหลังหักใบขอซื้อใบนี้",
        img_name="Screenshot_TAB_44_enough_detail.png",
        width_cm=6.5,
        cap="ภาพที่ 38  ขั้นตอนที่ 3 แสดงยอดงบประมาณที่จองและงบคงเหลือหลังหัก PR ใบนี้ (1.4)",
    )

    step_with_pic(
        doc,
        num=4,
        text="กรณีงบประมาณเพียงพอ: ระบบจะแสดงป้ายสถานะสีเขียว “งบเพียงพอ” พร้อมวันที่เช็คงบล่าสุด และแสดงตารางรายละเอียดผลการเช็คงบรายรายการ เมื่อหน่วยงานกดส่งอนุมัติใบขอซื้อ ระบบจะติ๊กช่อง “จองงบประมาณแล้ว” เพื่อกันวงเงินทันที",
        img_name="Screenshot_TAB_44_enough.png",
        width_cm=15.8,
        cap="ภาพที่ 39  ขั้นตอนที่ 4 ผลการตรวจงบในแท็บตรวจสอบงบประมาณ กรณี “งบเพียงพอ” (1.4)",
    )

    step_with_pic(
        doc,
        num=5,
        text="กรณีงบประมาณไม่เพียงพอ (อ้างอิงแนวทางแก้ไขตามคู่มือหน่วยงบประมาณ หัวข้อ 7.2 และการขอตั้งงบนอกแผนในบทที่ 1–4): ระบบจะแสดงป้ายแจ้งเตือนสีแดง “งบไม่เพียงพอ” และไม่อนุญาตให้ส่งอนุมัติใบขอซื้อ ให้ผู้ใช้งานตรวจสอบและดำเนินการดังนี้:",
        img_name="Screenshot_TAB_44_insufficient.png",
        width_cm=11.0,
        cap="ภาพที่ 40  ขั้นตอนที่ 5 ผลการตรวจงบกรณี “งบไม่เพียงพอ” ระบบแจ้งเตือนและป้องกันการใช้งบเกินแผน (1.4)",
        sub_bullets=[
            "1. ตรวจสอบความถูกต้องของข้อมูล 4 มิติบนหัวเอกสาร PR (หน่วยงาน, แหล่งเงิน, หมวดงบประมาณ, กลุ่มวัสดุ) ว่าเลือกตรงกับแผนงบประมาณที่ได้รับอนุมัติหรือไม่",
            "2. หากเลือกข้อมูลถูกต้องแล้วแต่วงเงินงบประมาณที่ตั้งไว้เดิมในแผนไม่เพียงพอ และมีความจำเป็นต้องจัดซื้อเพิ่มเติม ให้หน่วยงานไปที่โมดูล “งบประมาณ → บันทึกคำของบ” เพื่อสร้างใบคำขอตั้งงบประมาณเพิ่มเติม โดยเลือกตัวเลือก “ประเภทการตั้งงบประมาณ = นอกแผน” (อ้างอิงขั้นตอนใน บทที่ 1 หัวข้อ 1.2 ขั้นตอนที่ 2)",
            "3. เมื่อหน่วยงบประมาณดำเนินการ รับเรื่อง (บทที่ 2) → พิจารณาจัดสรรวงเงิน (บทที่ 3) → กดปุ่ม “อนุมัติ” ใบคำขอตั้งงบนอกแผน (บทที่ 4) เรียบร้อยแล้ว ยอดงบประมาณนอกแผนจะถูกซิงก์เพิ่มเข้าสู่แผนงบประมาณประจำปีทันที",
            "4. ให้หน่วยงานกลับมาเปิดใบขอซื้อ (PR) ใบเดิม แล้วคลิกปุ่ม “เช็คงบประมาณ” อีกครั้ง ระบบจะคำนวณรวมวงเงินนอกแผนที่เพิ่งได้รับอนุมัติ ทำให้สถานะเปลี่ยนเป็น “งบเพียงพอ” และสามารถดำเนินการส่งอนุมัติจัดซื้อต่อไปได้",
        ],
    )

    callout(
        doc,
        "สรุปวงจรการกันงบและตัดงบจริง (1.4)",
        "1. กันงบ (Reserve / จอง PR): เกิดขึ้นเมื่อใบขอซื้อ (PR) ผ่านการเช็คงบเป็น “งบเพียงพอ” และส่งอนุมัติ\n"
        "2. ผูกพันงบ (Commitment / ผูกพัน PO): เกิดขึ้นเมื่อกลุ่มงานพัสดุออกใบสั่งซื้อ (PO) และกดยืนยันคำสั่งซื้อ\n"
        "3. ตัดงบจริง (Actual / เบิกจ่ายแล้ว): เกิดขึ้นเมื่อกลุ่มงานเจ้าหนี้/การเงินบันทึกใบตั้งหนี้ (Vendor Bill) และกดยืนยันผ่านรายการบัญชี",
        "ok",
    )

    p_end = doc.add_paragraph()
    p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_end.paragraph_format.space_before = Pt(18)
    add_text(p_end, "— จบคู่มือการใช้งาน : กลุ่มงานงบประมาณ (2.1, 1.1 – 1.4) —", 12, True, PRIMARY)

    doc.save(OUT)
    print("Saved:", OUT)


if __name__ == "__main__":
    build()
