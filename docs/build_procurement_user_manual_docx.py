#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Thai Word user manual for VPK procurement: PR → e-GP → PO."""
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "คู่มือการใช้งาน" / "คู่มือการใช้งาน-ระบบจัดซื้อจัดจ้าง.docx"
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


_FIG_COUNTER = [0]


def caption(doc, text, marked=True):
    # เลขภาพรันอัตโนมัติ ไม่ต้องแก้เลขเองเมื่อเพิ่ม/ลบภาพ
    if re.search(r"ภาพที่\s+\d+", text):
        _FIG_COUNTER[0] += 1
        text = re.sub(r"ภาพที่\s+\d+", f"ภาพที่ {_FIG_COUNTER[0]}", text, count=1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)
    label = text if (not marked or text.startswith("▲")) else f"▲ {text}"
    add_text(p, label, 10, False, MUTED)


def picture(doc, name, width_cm=16.2, cap="", marked=True):
    path = FIG / name
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    if cap:
        caption(doc, cap, marked=marked)


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


def contract_section(doc):
    """8.3 บันทึกสัญญาจากกระบวนการ e-GP (ใช้ทั้งในเล่มเต็มและไฟล์ส่วนเพิ่ม)."""
    heading(doc, "8.3 บันทึกสัญญาจากกระบวนการ e-GP", 2)
    body(
        doc,
        "งานที่ต้องทำสัญญากับผู้ชนะ เช่น งานจ้าง งานเช่า หรือซื้อเป็นงวด "
        "พัสดุบันทึกสัญญาในทะเบียนสัญญา โดยเริ่มจากเอกสารกระบวนการ e-GP ของงานนั้น "
        "ระบบดึงคู่ค้า มูลค่า และเลขที่โครงการ e-GP มาให้ ไม่ต้องพิมพ์ซ้ำ "
        "สัญญาที่ยืนยันแล้วใช้เป็นฐานตรวจวงเงินเมื่อเปิดใบขอซื้อและใบสั่งซื้อในงวดถัดไป",
    )
    callout(
        doc,
        "ใครทำได้",
        "ปุ่ม เปิดทะเบียนสัญญา และ ยืนยันสัญญา แสดงเฉพาะผู้ใช้สิทธิ์ผู้จัดการจัดซื้อ "
        "และต้องเลือกผู้ชนะในกระบวนการ e-GP แล้ว จึงจะได้คู่ค้าและมูลค่าตามผู้ชนะ",
        "info",
    )

    heading(doc, "8.3.1 เปิดทะเบียนสัญญาจากเอกสาร e-GP", 3)
    steps(
        doc,
        ["เปิดเอกสารกระบวนการ e-GP ที่เลือกผู้ชนะแล้ว ปุ่ม เปิดทะเบียนสัญญา อยู่ที่แถบปุ่มหัวเอกสาร"],
        start=1,
    )
    picture(doc, "Screenshot_ch8_ctr_egp_btn.png", 16.6, "ภาพที่ 102  ปุ่มเปิดทะเบียนสัญญาที่หัวเอกสาร e-GP")
    steps(
        doc,
        [
            "กด เปิดทะเบียนสัญญา ระบบสร้างสัญญาสถานะ แบบร่าง พร้อมรหัสสัญญา CTR/ปี/เลขวิ่ง "
            "คู่ค้าคือผู้ชนะ มูลค่าคือยอดเสนอราคาของผู้ชนะ "
            "(ถ้ายังไม่เลือกผู้ชนะ ใช้ผู้จำหน่ายและยอดรวมของใบขอซื้อแทน) "
            "และอ้างอิงเอกสาร e-GP กับเลขที่โครงการ e-GP ให้อัตโนมัติ",
        ],
        start=2,
    )
    picture(doc, "Screenshot_ch8_ctr_form_draft.png", 16.6, "ภาพที่ 103  ทะเบียนสัญญาแบบร่างที่สร้างจากเอกสาร e-GP")
    steps(
        doc,
        ["ตรวจข้อมูลหัวสัญญาให้ตรงกับสัญญาที่ลงนามจริง แก้ไขได้เฉพาะสถานะแบบร่าง"],
        start=3,
    )
    make_table(
        doc,
        ["ช่อง", "ใส่อะไร"],
        [
            ["คู่ค้า", "ผู้ขายที่ทำสัญญา ดึงจากผู้ชนะ แก้ได้ถ้าไม่ตรงสัญญา"],
            ["มูลค่ารวมสัญญา", "วงเงินตามสัญญา ใช้เป็นฐานตรวจยอดคงเหลือของ PR และ PO"],
            ["วันเริ่มสัญญา", "ค่าเริ่มต้นคือวันที่สร้าง แก้เป็นวันที่ตามสัญญา"],
            ["ระยะเวลาสัญญา (วัน)", "ค่าเริ่มต้น 365 วัน ใช้คำนวณวันสิ้นสุดเมื่อกดยืนยัน"],
            ["วันสิ้นสุดสัญญา", "เว้นว่างได้ ถ้าว่าง ระบบคำนวณจากวันเริ่มสัญญาและระยะเวลาสัญญา"],
        ],
        [5.2, 11.0],
    )

    heading(doc, "8.3.2 แบ่งงวดงาน (ถ้าสัญญาแบ่งจ่ายเป็นงวด)", 3)
    steps(
        doc,
        [
            "ในแท็บ เงื่อนไขแบ่งงวด กด สร้างรายการงวดงาน เลือกจำนวนงวด "
            "และวิธีแบ่ง แบ่งเท่ากัน หรือ กำหนดเอง (สร้างงวดเปล่า) แล้วกด สร้างงวด",
        ],
        start=1,
    )
    picture(doc, "Screenshot_ch8_ctr_wizard.png", 12.0, "ภาพที่ 104  หน้าต่างสร้างรายการงวดงาน")
    steps(
        doc,
        [
            "แก้ชื่องวด สินค้า/บริการ มูลค่า และกำหนดจ่ายในตารางให้ตรงสัญญา "
            "ผลรวมมูลค่าทุกงวดต้องเท่ากับมูลค่ารวมสัญญา ไม่เช่นนั้นกดยืนยันสัญญาไม่ได้",
        ],
        start=2,
    )
    picture(doc, "Screenshot_ch8_ctr_installments.png", 16.6, "ภาพที่ 105  รายการงวดงานของสัญญา ช่องใช้แล้วจะถูกติ๊กเมื่อมีใบขอซื้อเบิกงวดนั้น")

    heading(doc, "8.3.3 แนบเอกสารสัญญา เงื่อนไข และหลักประกัน", 3)
    steps(
        doc,
        [
            "แท็บ เอกสารสัญญา กด เอกสารสัญญา แล้วแนบสัญญาที่ลงนามแล้ว TOR "
            "และเอกสารประกอบ แนบได้หลายไฟล์",
            "แท็บ เงื่อนไขข้อตกลง บันทึกเงื่อนไขสำคัญของสัญญา",
            "แท็บ หลักประกัน กด เพิ่มรายการ ถ้ามีหลักประกันสัญญา เช่น หนังสือค้ำประกันธนาคาร "
            "ใส่เลขที่หนังสือ มูลค่า และวันเริ่มกับวันสิ้นสุดความคุ้มครอง",
        ],
        start=1,
    )
    picture(doc, "Screenshot_ch8_ctr_docs.png", 16.6, "ภาพที่ 106  แท็บเอกสารสัญญา สำหรับแนบสัญญาที่ลงนามแล้วและเอกสารประกอบ")

    heading(doc, "8.3.4 ยืนยันสัญญา", 3)
    steps(
        doc,
        [
            "ตรวจข้อมูลครบแล้วกด ยืนยันสัญญา ระบบตรวจว่ามีคู่ค้า มีมูลค่ารวมสัญญา "
            "และผลรวมงวดเท่ากับมูลค่ารวมสัญญา",
            "สถานะเปลี่ยนจาก แบบร่าง เป็น มีผลบังคับใช้ ระบบบันทึกวันที่ยืนยันสัญญา "
            "และคำนวณวันสิ้นสุดสัญญาให้ถ้าเว้นว่างไว้",
        ],
        start=1,
    )
    picture(doc, "Screenshot_ch8_ctr_confirmed.png", 16.6, "ภาพที่ 107  สัญญาสถานะมีผลบังคับใช้ แสดงวันที่ยืนยันและวันสิ้นสุดสัญญา")
    callout(
        doc,
        "แก้ไขหลังยืนยัน",
        "สัญญาที่มีผลบังคับใช้แก้ข้อมูลหัวสัญญาไม่ได้ ถ้าต้องแก้ ให้กด ยกเลิก แล้ว ตั้งเป็นแบบร่าง "
        "สัญญาที่ยังมี PR หรือ PO ใช้งานอยู่ยกเลิกไม่ได้ เมื่อสัญญาสิ้นสุดแล้วกด ปิดสัญญา",
        "warn",
    )

    heading(doc, "8.3.5 เปิดสัญญากลับจากเอกสาร e-GP", 3)
    steps(
        doc,
        [
            "ที่เอกสาร e-GP กดปุ่ม เพิ่มเติม แล้วเลือกปุ่ม สัญญา เพื่อเปิดทะเบียนสัญญาของงานนี้ "
            "หรือเปิดจากเมนู ระบบจัดซื้อจัดจ้าง → จัดการสั่งซื้อ → ทะเบียนสัญญา",
        ],
        start=1,
    )
    picture(doc, "Screenshot_ch8_ctr_stat_btn.png", 16.6, "ภาพที่ 108  ปุ่มสัญญาในเมนู เพิ่มเติม ของเอกสาร e-GP")

    heading(doc, "8.3.6 สัญญากับใบขอซื้อและใบสั่งซื้อในงวดถัดไป", 3)
    make_table(
        doc,
        ["เอกสาร", "ระบบทำอะไรเมื่อผูกสัญญา"],
        [
            [
                "ใบขอซื้อ (PR)",
                "เลือกรหัสสัญญาในใบขอซื้อ ระบบดึงงวดงานที่ยังไม่ถูกใช้มาเป็นรายการสินค้า "
                "และตรวจวงเงินจากสัญญาแทนการตรวจงบประมาณ",
            ],
            [
                "ใบสั่งซื้อ (PO)",
                "เมื่อกดยืนยัน ระบบตรวจว่ามูลค่าไม่เกินยอดคงเหลือของสัญญา "
                "ถ้าเกินจะยืนยันไม่ได้ ผ่านแล้วตัดลดยอดคงเหลือและปิดใบขอซื้อที่ผูกกันให้",
            ],
            [
                "ใบแจ้งหนี้",
                "ใบแจ้งหนี้ที่สร้างจากใบสั่งซื้อของสัญญา ผูกกับสัญญาเดียวกัน "
                "ดูย้อนได้ในแท็บ ติดตามสัญญา (Tracking)",
            ],
        ],
        [4.0, 12.2],
    )


def build():
    _FIG_COUNTER[0] = 0
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
                "จัดทำเอกสารคู่มือฉบับแรก",
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
        "บทที่ 4 หน่วยงาน — เปิดใบขอซื้อ",
        "บทที่ 5 ขั้นตอนการทำงานของหน่วยงานพัสดุ",
        "บทที่ 7 พัสดุ — นำใบขอซื้อเข้ากระบวนการ e-GP",
        "บทที่ 8 เปิดใบสั่งซื้อ (PO) เมื่อได้ผู้ชนะ",
        "บทที่ 9 กระบวนการตรวจรับ",
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
            ["หน่วยงาน", "จัดซื้อ → ใบขอซื้อ", "สร้างใบขอซื้อ เช็คงบ ใส่แท็บรายชื่อคณะกรรมการ ทำเอกสารอนุมัติขอซื้อ แล้วกดส่งพัสดุ"],
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

    heading(doc, "บทที่ 4 หน่วยงาน — เปิดใบขอซื้อ", 1)
    body(
        doc,
        "บทนี้ใช้บัญชีหน่วยงาน เข้าเมนู ใบขอซื้อ แล้วกดสร้าง เมื่อบันทึก "
        "ระบบจะออกเลขที่อัตโนมัติรูปแบบ PR + ปี พ.ศ. 2 หลัก + เดือน + Running Number 3 หลัก "
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
        "Screenshot_PR6910005.png",
        16.6,
        "ภาพที่ 6  ใบขอซื้อ PR6910005",
    )
    picture(
        doc,
        "Screenshot_New_PR.png",
        16.6,
        "ภาพที่ 7  หน้าจอใบขอซื้อ",
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
        14.22,
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
        13.9,
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
        13.79,
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
        14.08,
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
        13.83,
        "ภาพที่ 12  เลือกกลุ่มงบประมาณ",
    )
    steps(
        doc,
        [
            "เลือกรับสินค้าเข้าคลัง Receipts ของคลังที่ต้องการให้ของเข้า",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_PR_picking_type.png",
        16.6,
        "ภาพที่ 13  เลือกการรับสินค้าเข้าคลัง",
    )
    steps(
        doc,
        [
            "ใส่คำขอจัดซื้อในช่องคำอธิบาย จากนั้นใส่รายการวัสดุหรือครุภัณฑ์ และเช็คงบประมาณตามหัวข้อถัดไป",
        ],
        start=8,
    )
    picture(doc, "Screenshot_PR_description.png", 16.6)
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
    heading(doc, "4.3 หน่วยงาน บันทึกข้อมูลในแต่ละแท็บ", 2)
    body(
        doc,
        "หลังกรอกหัวเอกสารแล้ว หน่วยงาน ใส่รายการวัสดุหรือครุภัณฑ์ที่จะขอซื้อในแท็บสินค้า "
        "กดตรวจสอบงบประมาณที่หัวเอกสาร แล้วดูผลที่แท็บตรวจสอบงบประมาณ "
        "ใส่รายชื่อคณะกรรมการที่เกี่ยวข้อง ทำเอกสารอนุมัติขอซื้อส่งอนุมัติ "
        "จากนั้นกดส่งเอกสารให้พัสดุ ดำเนินการต่อ",
    )
    picture(doc, "Screenshot_TAB_dept_tabs.png", 16.6, "ภาพที่ 14  แท็บบนใบขอซื้อ ของหน่วยงาน")
    picture(doc, "Screenshot_TAB_overview_items.png", 16.6, "ภาพที่ 15  ภาพรวมแท็บสินค้า")
    picture(doc, "Screenshot_TAB_overview_committee.png", 16.6, "ภาพที่ 16  ภาพรวมแท็บรายชื่อคณะกรรมการ")
    picture(doc, "Screenshot_TAB_overview_budget.png", 16.6, "ภาพที่ 17  ภาพรวมแท็บตรวจสอบงบประมาณ")
    picture(doc, "Screenshot_TAB_overview_approval.png", 16.6, "ภาพที่ 18  ภาพรวมแท็บเอกสารอนุมัติขอซื้อ")
    make_table(
        doc,
        ["แท็บ", "ผู้ดำเนินการ", "ทำอะไร"],
        [
            ["สินค้า", "หน่วยงาน", "ใส่รายการวัสดุหรือครุภัณฑ์ที่จะขอซื้อ จำนวน หน่วย และงบประมาณ"],
            ["รายชื่อคณะกรรมการ", "หน่วยงาน", "ใส่รายชื่อคณะกรรมการ"],
            ["ตรวจสอบงบประมาณ", "หน่วยงาน", "ดูผลหลังกดปุ่มตรวจสอบงบประมาณ"],
            ["เอกสารอนุมัติขอซื้อ", "หน่วยงาน", "ออกรายงานอนุมัติขอซื้อและส่งลงนาม"],
        ],
        [4.0, 3.6, 8.6],
    )

    heading(doc, "4.3.1 แท็บสินค้า", 3)
    body(
        doc,
        "แท็บนี้เป็นแท็บแรกและสำคัญที่สุด ถ้าไม่มีบรรทัดสินค้า ระบบจะส่งขออนุมัติไม่ได้ "
        "กดเพิ่มรายการที่ท้ายตาราง แล้วกรอกทีละบรรทัดขณะใบยังเป็นร่าง",
    )
    steps(
        doc,
        [
            "เปิดแท็บสินค้า แล้วกด เพิ่มรายการ ที่ท้ายตาราง",
        ],
    )
    picture(doc, "Screenshot_TAB_ITEM_add_line.png", 16.6, "ภาพที่ 19  ปุ่มเพิ่มรายการที่ท้ายตารางสินค้า")
    steps(
        doc,
        [
            "เลือกสินค้าจากรหัสหรือชื่อ เมื่อเลือกแล้วระบบจะเติมชื่อ หน่วยนับ และชื่อสำหรับซื้อใน e-GP ให้",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_ITEM_product.png", 16.6)
    steps(
        doc,
        [
            "ใส่จำนวนที่ขอ และตรวจหน่วยวัดให้ถูกต้อง เช่น กล่อง ขวด ชิ้น",
        ],
        start=3,
    )
    picture(doc, "Screenshot_TAB_ITEM_qty_uom.png", 3.92, "ภาพที่ 20  จำนวนและหน่วยวัดของรายการสินค้า")
    steps(
        doc,
        [
            "ใส่วันที่ต้องการของ ถ้าไม่ใส่ระบบจะใช้วันที่สร้างใบ",
        ],
        start=4,
    )
    picture(doc, "Screenshot_TAB_ITEM_date.png", 3.81, "ภาพที่ 21  วันที่ร้องขอของรายการสินค้า")
    steps(
        doc,
        [
            "ใส่งบประมาณของบรรทัดนั้น เป็นยอดรวมของรายการ ไม่ใช่ราคาต่อหน่วยถ้าหน้าจอแสดงเป็นยอดงบ",
        ],
        start=5,
    )
    picture(doc, "Screenshot_TAB_ITEM_budget.png", 3.39, "ภาพที่ 22  งบประมาณของรายการสินค้า")
    steps(
        doc,
        [
            "ตรวจชื่อสำหรับซื้อใน e-GP ถ้าชื่อในคลังไม่ตรงประกาศ ให้แก้ในช่องนี้",
        ],
        start=6,
    )
    picture(doc, "Screenshot_TAB_ITEM_egp_name.png", 11.22, "ภาพที่ 23  ชื่อสำหรับซื้อใน e-GP")
    steps(
        doc,
        [
            "ถ้ามีคุณลักษณะเฉพาะ กดปุ่มดู/แนบไฟล์ PDF ของรายการนั้น",
        ],
        start=7,
    )
    picture(doc, "Screenshot_TAB_ITEM_spec.png", 7.02, "ภาพที่ 24  ปุ่มดู/แนบไฟล์คุณลักษณะของรายการ")
    picture(
        doc,
        "Screenshot_TAB_ITEM_spec_popup.png",
        16.6,
        "ภาพที่ 25  เมื่อกดปุ่มจะมีหน้าจอให้/แนบไฟล์คุณลักษณะของรายการ",
    )
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
            ["ไฟล์คุณลักษณะ", "ถ้ามี", "กดดู/แนบไฟล์ PDF แยกรายการ"],
        ],
        [4.8, 2.4, 9.0],
    )
    callout(
        doc,
        "อย่าส่งใบที่ยังไม่มีสินค้า",
        "ถ้าตารางสินค้าว่าง หรือจำนวนเป็น 0 ระบบจะไม่ส่งขออนุมัติ "
        "กรณีมีการแก้รายการสินค้าแล้วต้องกดเช็คงบประมาณอีกครั้งก่อนส่ง",
        "warn",
    )

    heading(doc, "4.3.2 แท็บรายชื่อคณะกรรมการ", 3)
    body(
        doc,
        "เปิดแท็บรายชื่อคณะกรรมการ เพื่อบันทึกกรรมการที่เกี่ยวข้องกับใบนี้ "
        "เลือกพนักงานจากรายชื่อ ที่มีในระบบ "
        "ชื่อ แผนก อีเมล และ โทรศัพท์จะเติมให้อัตโนมัติเมื่อเลือกพนักงาน",
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
            "เปิดแท็บรายชื่อคณะกรรมการ แล้วกด เพิ่มรายการ ในกลุ่มคณะกรรมการที่เกี่ยวข้อง "
            "จำนวนคณะกรรมการในแต่ละชุด หรือ ต้องมีชุดคณะกรรมการอะไรบ้าง ขึ้นอยู่กับวิธีการจัดซื้อจัดจ้าง",
        ],
    )
    picture(doc, "Screenshot_TAB_committee_add.png", 16.6, "ภาพที่ 26  กดปุ่มเพิ่มรายการ")
    steps(
        doc,
        [
            "เลือกรายชื่อกรรมการ",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_committee_roles.png", 4.25, "ภาพที่ 27  เลือกชื่อกรรมการ")
    steps(
        doc,
        [
            "ระบบจะเติมชื่อคณะกรรมการ แผนก และอีเมลที่ทำงานให้ ตรวจว่ามีประธานเพียง 1 คน",
        ],
        start=3,
    )
    picture(doc, "Screenshot_TAB_committee_filled.png", 16.6, "ภาพที่ 28  ชื่อ แผนก อีเมล และประธานเพียง 1 คน")
    steps(
        doc,
        [
            "บันทึกใบขอซื้อ",
        ],
        start=4,
    )
    picture(doc, "Screenshot_TAB_committee_save.png", 6.49, "ภาพที่ 31  ปุ่มบันทึกด้วยตนเองของใบขอซื้อ")
    heading(doc, "4.3.3 แท็บตรวจสอบงบประมาณ", 3)
    body(
        doc,
        "แท็บตรวจสอบงบประมาณเป็นขั้นตอนของหน่วยงาน "
        "ต้องตรวจระหว่างเปิดใบขอซื้อ ขณะใบยังเป็นฉบับร่าง "
        "หลังจากใส่รายการวัสดุหรือครุภัณฑ์ในแท็บสินค้าแล้ว "
        "ให้กดปุ่มเช็คงบประมาณที่หัวเอกสาร แล้วเปิดแท็บนี้เพื่อดูผล "
        "ยอดที่ขอต้องตรงกับรายการสินค้า และสถานะต้องเป็นงบเพียงพอ จึงส่งพัสดุได้ "
        "ถ้างบไม่พอ ให้แก้หน่วยงาน แหล่งเงิน หมวดงบ หรือยอดในแท็บสินค้า แล้วกดเช็คอีกครั้ง "
        "เมื่อสถานะเป็นงบเพียงพอแล้ว ทำแท็บเอกสารอนุมัติขอซื้อตามหัวข้อถัดไป",
    )
    steps(
        doc,
        [
            "กดปุ่มเช็คงบประมาณที่หัวเอกสาร ขณะสถานะยังเป็นฉบับร่าง",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_TAB_44_check_btn.png",
        3.42,
        "ภาพที่ 32  ปุ่มตรวจสอบงบประมาณที่หัวเอกสาร ขณะหน่วยงานเปิดใบขอซื้อ",
    )
    steps(
        doc,
        [
            "เมื่อกดปุ่มแล้ว เปิดแท็บตรวจสอบงบประมาณ ดูสถานะเช็คงบ งบประมาณที่จอง และงบคงเหลือหลังหักใบนี้",
        ],
        start=2,
    )
    picture(doc, "Screenshot_TAB_44_enough_detail.png", 4.96)
    picture(
        doc,
        "Screenshot_TAB_44_enough.png",
        16.6,
        "ภาพที่ 33  ผลเช็คงบของใบขอซื้อ เป็นงบเพียงพอ",
    )
    picture(
        doc,
        "Screenshot_TAB_44_insufficient.png",
        9.53,
        "ภาพที่ 34  ผลเช็คงบของใบขอซื้อ กรณีไม่พอ",
    )
    heading(doc, "4.3.4 แท็บเอกสารอนุมัติขอซื้อ", 3)
    body(
        doc,
        "แท็บนี้เป็นงานของหน่วยงาน ทำหลังจากใส่รายการสินค้า "
        "ตรวจงบได้สถานะงบเพียงพอ และใส่รายชื่อคณะกรรมการแล้ว "
        "ใช้แท็บนี้ออกบันทึกข้อความอนุมัติขอซื้อ แล้วส่งลงนามตามลำดับในตารางผู้ลงนาม "
        "เลขที่ในบันทึกขอจากปุ่มขอเลขจากระบบสารบรรณที่ฟอร์มเอกสารนั้น "
        "เพราะใบขอซื้อมีเอกสารที่เกี่ยวข้องหลายใบ แต่ละฉบับต้องขอเลขของตนเอง",
    )
    steps(
        doc,
        [
            "เปิดแท็บเอกสารอนุมัติขอซื้อ แล้วกดปุ่มออกบันทึกข้อความอนุมัติขอซื้อ "
            "ระบบสร้างเอกสารบันทึกโดย ดึงข้อมูลจากใบขอซื้อ ผู้ลงนามเอกสาร "
            "เพิ่มในหัวข้อผู้อนุมัติตอนท้าย ของฟอร์ม "
            "จากนั้นปุ่มจะเปลี่ยนเป็นเปิดบันทึกข้อความอนุมัติขอซื้อ",
        ],
    )
    picture(
        doc,
        "Screenshot_approval_create_btn.png",
        16.6,
        "ภาพที่ 35  ปุ่มสร้างเอกสารขออนุมัติขอซื้อ",
        marked=False,
    )
    picture(
        doc,
        "Screenshot_approval_form_header.png",
        16.6,
        "ภาพที่ 35  ส่วนหัวของฟอร์ม Template เอกสาร",
        marked=False,
    )
    picture(
        doc,
        "Screenshot_approval_form_body.png",
        16.6,
        "ภาพที่ 36  Template ส่วนเนื้อหาของ เอกสาร",
        marked=False,
    )
    body(doc, "สามารถปรับเปลี่ยนข้อความใน Template ได้")
    picture(
        doc,
        "Screenshot_approval_signers.png",
        16.6,
        "ภาพที่ 37  ส่วนเพิ่มผู้ลงนาม ตามลำดับ",
        marked=False,
    )
    body(doc, "สามารถเพิ่ม หรือปรับเปลี่ยนผู้ลงนามได้")
    steps(
        doc,
        [
            "ที่หัวฟอร์มเอกสารกดปุ่มขอเลขจากระบบสารบรรณ เพื่อออกเลขของเอกสารฉบับนี้ "
            "อย่ากดขอเลขจากใบขอซื้อ เพราะใบขอซื้อมีเอกสารที่เกี่ยวข้องหลายใบ แต่ละฉบับต้องมีเลขของตนเอง",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_TAB_approval_saraban.png",
        16.6,
        "ภาพที่ 37  ปุ่มขอเลขจากระบบสารบรรณที่ฟอร์มเอกสารอนุมัติขอซื้อ",
        marked=False,
    )
    steps(
        doc,
        [
            "ที่หัวบันทึกกดปุ่มพิมพ์ PDF แล้วเปิดไฟล์ตรวจข้อความ",
        ],
        start=3,
    )
    picture(
        doc,
        "Screenshot_approval_print_btn.png",
        9.56,
        "ภาพที่ 38  ปุ่มสร้างเอกสาร PDF",
        marked=False,
    )
    picture(
        doc,
        "Screenshot_approval_pdf_created.png",
        16.6,
        "ภาพที่ 39  เอกสาร PDF ที่ถูกสร้าง",
        marked=False,
    )
    picture(
        doc,
        "Screenshot_approval_pdf_sample.png",
        12.10,
        "ภาพที่ 39  ภาพตัวอย่าง เอกสารขออนุมัติขอซื้อที่สร้างจากระบบ",
        marked=False,
    )
    steps(
        doc,
        [
            "กดส่งเพื่อลงนามที่แถวเอกสารหรือที่หัวบันทึก ระบบจะส่งลงนามตามลำดับ",
        ],
        start=6,
    )
    picture(
        doc,
        "Screenshot_approval_send_btn.png",
        12.63,
        "ภาพที่ 39  รูปปุ่มส่งอนุมัติลงนาม",
        marked=False,
    )
    picture(
        doc,
        "Screenshot_approval_send_dialog.png",
        16.6,
        "ภาพที่ 40  รูปหลังกดปุ่มส่งลงนาม ให้กดส่งเอกสาร",
        marked=False,
    )
    picture(
        doc,
        "Screenshot_approval_waiting.png",
        16.6,
        "ภาพที่ 40  แสดงสถานะเอกสารรอลงนาม",
        marked=False,
    )
    picture(doc, "Screenshot_approval_inbox.png", 16.6)
    body(doc, "โดยเอกสารจะไปรอในกล่องอนุมัติ ของผู้ลงนามที่ได้กำหนดไว้")
    caption(
        doc,
        "ภาพที่ 41  แสดงเอกสารรออนุมัติ ในกล่องลงนามของ ผู้ลงนามนั้นๆ",
        marked=False,
    )
    steps(
        doc,
        [
            "ลงนามเอกสาร ให้กดเปิด PDF และกดปุ่มลงนาม",
        ],
        start=7,
    )
    picture(
        doc,
        "Screenshot_approval_signer_doc.png",
        16.6,
        "ภาพที่ 42  แสดงเอกสารของ ผู้ลงนาม",
        marked=False,
    )
    picture(doc, "Screenshot_approval_sign_screen.png", 16.6)
    picture(
        doc,
        "Screenshot_approval_sign_pad.png",
        16.6,
        "ภาพที่ 42  แสดงหน้าจอลงลายเซ็น",
        marked=False,
    )
    caption(doc, "ภาพที่ 43  แสดงหน้าจอเมื่อลงลายเซ็นแล้ว", marked=False)
    body(doc, "กดปุ่มยอมรับและลงนาม")
    picture(
        doc,
        "Screenshot_approval_signed.png",
        12.31,
        "ภาพที่ 44  รูปแสดงลายเซ็นบนเอกสารผู้ลงนามรายอื่น จะมีเอกสารไปรอ ในกล่องของตัวเอง และทำขั้นตอนเหมือนกัน โดยเมื่อลงนามครบแล้ว ใบขอซื้อจะถูกเปลี่ยนสถานะเป็น อนุมัติเพื่อส่งให้ พัสดุดำเนินการต่อไป",
        marked=False,
    )
    heading(doc, "4.3.5 ส่งใบขอซื้อให้พัสดุ", 3)
    body(
        doc,
        "เมื่อเปิดใบขอซื้อเรียบร้อยแล้วคือใส่รายการวัสดุหรือครุภัณฑ์ครบ"
        "แท็บตรวจสอบงบประมาณเป็นงบเพียงพอ "
        "และส่งบันทึกข้อความอนุมัติขอซื้อเพื่อลงนามครบแล้ว"
        "ให้กดปุ่มส่งพัสดุที่หัวเอกสาร"
        "เพื่อส่งใบขอซื้อต่อไปให้หน่วยงานพัสดุหรือจัดซื้อดำเนินการต่อ"
        "สถานะจะเปลี่ยนจากฉบับร่างเป็นส่งพัสดุแล้ว "
        "จากนั้นฝ่ายพัสดุรับงานและทำแท็บเอกสารที่เหลือ",
    )
    steps(
        doc,
        [
            "กดปุ่มส่งพัสดุที่หัวเอกสาร",
        ],
    )
    picture(
        doc,
        "Screenshot_TAB_44_send_btn.png",
        4.0,
        "ภาพที่ 35  ปุ่มส่งพัสดุที่หัวเอกสาร เมื่อเปิดใบขอซื้อเรียบร้อยแล้ว",
    )
    steps(
        doc,
        [
            "ตรวจว่าสถานะเปลี่ยนเป็นส่งพัสดุแล้ว และขึ้นข้อความว่าใบนี้ส่งมาจากหน่วยงานแล้ว",
        ],
        start=2,
    )
    picture(
        doc,
        "Screenshot_PR_status_sent.png",
        16.6,
        "ภาพที่ 35  สถานะใบขอซื้อ เปลี่ยนเป็นส่งพัสดุแล้ว",
    )
    heading(doc, "บทที่ 5 ขั้นตอนการทำงานของหน่วยงานพัสดุ", 1)
    body(
        doc,
        "หลังจากหน่วยงานส่งใบขอซื้อมาแล้ว หน่วยงานพัสดุหรือจัดซื้อรับใบที่สถานะส่งพัสดุแล้ว แล้วดำเนินการตามลำดับนี้",
    )
    heading(doc, "5.1 รับงาน", 2)
    steps(
        doc,
        ["เข้าเมนูระบบจัดซื้อจัดจ้าง -> ข้อมูลใบขอซื้อ -> Dashboard พัสดุรับงาน ให้กดรับงาน เปิดทำรายการ"],
    )
    picture(
        doc,
        "Screenshot_ch5_dashboard_work.png",
        16.6,
        "ภาพที่ 36  หน้าจอ Dashboard พัสดุรับงาน",
        marked=False,
    )
    steps(
        doc,
        ["ออกเอกสารราชการที่เกี่ยวข้อง เช่น แต่งตั้งคณะกรรมการตรวจรับ , รายงานขออนุมัติจัดซื้อจัดจ้าง"],
        start=2,
    )
    body(doc, "เปิดแท็บเอกสารราชการที่เกี่ยวข้อง")
    picture(doc, "Screenshot_ch5_related_docs_tab.png", 16.6, "ภาพที่ 37  แท็บเอกสารราชการที่เกี่ยวข้อง")
    picture(doc, "Screenshot_ch5_doc_type_menu.png", 16.6, "ภาพที่ 38  รูปแสดงเอกสารที่จะสร้างให้เลือก")
    picture(doc, "Screenshot_ch5_select_committee_doc.png", 16.6, "ภาพที่ 39  รูปแสดงเลือกสร้างเอกสารคณะกรรมการตรวจรับ")
    body(doc, "กดสร้างเอกสาร")
    picture(
        doc,
        "Screenshot_ch5_order_created.png",
        16.6,
        "ภาพที่ 40  หลังกดสร้าง หน้าจอจะเปิดคำสั่ง โดยขั้นตอนการสร้างเอกสารและส่งลงนาม จะทำงานเหมือนกับเอกสารขออนุมัติขอซื้อ ข้างต้น กดสร้าง PDF ระบบจะสร้างเอกสาร ตาม Template ที่ผูกไว้ให้ และ ทำการส่งลงนามตามลำดับ",
    )
    picture(doc, "Screenshot_ch5_committee_order_sample.png", 10.2, "ภาพที่ 41  ตัวอย่าง เอกสารแต่งตั้งกรรมการตรวจรับ")
    picture(doc, "Screenshot_ch5_specific_method_sample.png", 16.6, "ภาพที่ 41  ตัวอย่าง รายงานขออนุมัติซื้อ ด้วยวิธีเฉพาะเจาะจง")
    body(doc, "ถ้าวงเงินมากกว่า 100,000 บาท ให้สร้างแบบแสดงความบริสุทธิ์ใจ จากระบบได้")
    steps(
        doc,
        ["เปิดแท็บเอกสารราชการที่เกี่ยวข้อง ตรวจว่าเอกสารที่ออกจากใบนี้ลงนามหรืออนุมัติครบหรือไม่"],
        start=3,
    )
    picture(doc, "Screenshot_ch5_related_docs_done.png", 16.6, "ภาพที่ 42  แท็บเอกสารราชการที่เกี่ยวข้องของหน่วยงานพัสดุ")
    steps(
        doc,
        ["เมื่อใบขอซื้อได้ลงนามอนุมัติ้เอกสารครบแล้ว กดส่งรายการเข้าระบบ e-GP เพื่อเดินกระบวนการจัดซื้อต่อไป"],
        start=4,
    )
    picture(doc, "Screenshot_ch5_send_egp_btn.png", 16.6, "ภาพที่ 43  ปุ่มส่งรายการเข้าระบบ e-GP หลังเอกสารครบ")

    heading(doc, "บทที่ 7 พัสดุ — นำใบขอซื้อเข้ากระบวนการ e-GP", 1)
    body(
        doc,
        "เมื่อใบขอซื้อจากหน่วยงาน ได้รับการอนุมัติ หรือ เอกสารที่เกี่ยวข้องลงนามครบแล้ว พัสดุ/จัดซื้อ จะส่งเอกสารเข้าระบบ กระบวนการ e-GP",
    )
    heading(doc, "7.1 ส่งใบขอซื้อเข้ากระบวนการ e-GP", 2)
    body(
        doc,
        "กระบวนการ e-GP ในระบบนี้ใช้รองรับและเก็บข้อมูลที่ได้จากการทำในระบบ e-GP จริง เช่น ไฟล์ที่สร้างจากระบบ e-GP เลขเอกสาร หรือชื่อโครงการ เพื่อใช้อ้างอิงในการทำงานและเชื่อมกับงานอื่น",
    )
    steps(doc, ["เปิดใบขอซื้อที่อนุมัติแล้ว"])
    picture(doc, "Screenshot_ch7_approved_pr.png", 16.6, "ภาพที่ 44  รูปใบขอซื้อที่อนุมัติแล้ว")
    steps(doc, ["กดปุ่ม ส่งรายการเข้าระบบ e-GP"], start=2)
    picture(doc, "Screenshot_ch7_send_egp_header.png", 4.2, "ภาพที่ 63  ปุ่มส่งรายการเข้าระบบ e-GP ที่หัวใบขอซื้อ")
    steps(doc, ["ตรวจรายการสินค้าในหน้าต่าง กระบวนการ eGP ว่าครบตามใบขอซื้อ"], start=3)
    picture(doc, "Screenshot_ch7_egp_wizard_lines.png", 16.6, "ภาพที่ 64  หน้าต่างกระบวนการ eGP แสดงรายการสินค้าจากใบขอซื้อ")
    steps(
        doc,
        ["กดปุ่ม กระบวนการ eGP ระบบจะสร้างเอกสารกระบวนการ e-GP จากใบขอซื้อที่อนุมัติแล้ว เพื่อดำเนินการในส่วน e-GP ต่อไป"],
        start=4,
    )
    picture(doc, "Screenshot_ch7_egp_wizard_confirm.png", 5.0, "ภาพที่ 65  ปุ่มกระบวนการ eGP ในหน้าต่างยืนยัน")
    steps(
        doc,
        ["เปิดเอกสารที่สร้างได้จากปุ่มสถิติ กระบวนการ e-GP บนใบขอซื้อ หรือจากเมนู จัดซื้อ → กระบวนการ eGP"],
        start=5,
    )
    body(doc, "ในหน้าเอกสารใบขอซื้อ จะมีปุ่มสถิติแสดง รายการเอกสารต่างๆที่เกี่ยวข้องกับใบขอซื้อใบนี้")
    picture(doc, "Screenshot_ch7_egp_stat_btn.png", 16.6, "ภาพที่ 65  ปุ่มสถิติกระบวนการ e-GP บนใบขอซื้อ")
    heading(doc, "7.2 บันทึกข้อมูลที่เกี่ยวข้องในเอกสาร e-GP", 2)
    body(
        doc,
        "ข้อมูลที่บันทึกจะเป็นข้อมูลที่ได้จากระบบ e-GP ที่ทางพัสดุ/จัดซื้อทำการเปิด รวมถึง File ต่างๆที่ทำบน e-GP เพื่อให้รายการสอดคล้องมีข้อมูลในระบบ ERP",
    )
    steps(doc, ["บันทึกเลขที่โครงการ และชื่อโครงการ"])
    picture(
        doc,
        "Screenshot_ch7_project_fields.png",
        16.6,
        "ภาพที่ 66  ช่องใส่เลขที่ โครงการ และ ชื่อโครงการ e-GP",
        marked=False,
    )
    body(
        doc,
        "ขั้นที่ 2  เข้าแท็ปเอกสารที่เปิดในระบบ e-GP แนบ file ต่างๆ ที่ได้จาก e-GP เช่น ประกาศร่าง , รายงานผลการพิจารณาจัดซื้อจัดจ้าง และประกาศผู้ชนะ เป็นต้น",
    )
    picture(
        doc,
        "Screenshot_ch7_egp_files.png",
        16.6,
        "ภาพที่ 66  แสดงการแนบ File เอกสาร e-GP",
        marked=False,
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
        [4.5, 11.5],
    )
    steps(doc, ["เข้าแท็ปเปรียบเทียบราคา ใส่ข้อมูลผู้เสนอราคา"], start=3)
    picture(
        doc,
        "Screenshot_ch7_compare_prices.png",
        16.6,
        "ภาพที่ 67  แสดงข้อมูลเปรียบเทียบราคา",
        marked=False,
    )
    steps(doc, ["เลือกผู้ชนะ ให้กดเลือก ผู้ชนะในรายการ"], start=4)
    picture(
        doc,
        "Screenshot_ch7_pick_winner.png",
        16.6,
        "ภาพที่ 68  แสดงการเลือกผู้ชนะ",
        marked=False,
    )
    callout(
        doc,
        "ยังสร้าง PO ไม่ได้ตอนนี้",
        "แม้ติ๊กผู้ชนะแล้ว ปุ่มสร้าง POจะยังไม่พร้อมจนกว่าจะจัดทำและอนุมัติ รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง",
        "warn",
    )
    heading(doc, "ขั้นที่ 5 จัดทำรายงานผลและประกาศผู้ชนะ กดปุ่ม จัดทำรายงานผลและขออนุมัติ ในแท็บเปรียบเทียบราคา", 2)
    picture(doc, "Screenshot_ch7_award_button.png", 12.6, "ภาพที่ 69  ปุ่มจัดทำรายงานผลและขออนุมัติ ในแท็บเปรียบเทียบราคา")
    steps(
        doc,
        ["ระบบเปิด Template รายงานผลพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง ตรวจเรื่อง เกณฑ์การพิจารณา ข้อเสนอที่ได้รับการคัดเลือก และวงเงินที่ขออนุมัติ"],
        start=6,
    )
    picture(doc, "Screenshot_ch7_award_template.png", 16.6, "ภาพที่ 70  รายงานผลการพิจารณา ตรวจเรื่อง เกณฑ์ และวงเงินที่ขออนุมัติ")
    steps(
        doc,
        ["กด พิมพ์รายงาน ระบบจะสร้างรายงานตาม Template ให้ และแนบเอกสารไว้ใน แท็ปเอกสารที่เปิดในระบบ e-GP ให้"],
        start=3,
    )
    picture(doc, "Screenshot_ch7_print_award.png", 9.7, "ภาพที่ 85  ปุ่มสร้างรายการจากข้อเสนอ eGP")
    picture(doc, "Screenshot_ch7_award_sample.png", 15.3, "ภาพที่ 86 ตัวอย่างรายงานผลการพิจารณา จากระบบ")
    picture(doc, "Screenshot_ch7_award_created.png", 16.6, "ภาพที่ 87 เอกสารผลการพิจารณา ที่สร้างจากระบบ")
    steps(
        doc,
        ["กดส่งลงนาม รายการจากเข้าไปส่งกล่องอนุมัติเอกสารตามลำดับเหมือน การส่งลงนามในขอซื้อก่อนหน้านี้"],
        start=4,
    )
    picture(doc, "Screenshot_ch7_award_send.png", 3.2, "ภาพที่ 87  แถวรายงานผลการพิจารณาในแท็บเอกสาร e-GP พร้อมปุ่มส่งเพื่อลงนาม")
    picture(doc, "Screenshot_ch7_award_waiting.png", 16.6, "ภาพที่ 88  แสดงสถานะเอกสาร รอลงนาม")
    steps(
        doc,
        ["เมื่อเอกสารรายงานผลการพิจารณา ได้รับการลงนาม ให้กดประกาศผู้ชนะ ในแท็ปเปรียบเทียบราคา"],
        start=5,
    )
    picture(doc, "Screenshot_ch7_winner_button.png", 6.8, "ภาพที่ 89  แสดงปุ่มประกาศผู้ชนะ")
    body(doc, "เอกสารประกาศผู้ชนะจะแสดงใน แท็ปเอกสารที่เปิดใน e-GP จากนั้นส่งลงนาม")
    picture(doc, "Screenshot_ch7_winner_row.png", 16.6, "ภาพที่ 90 แถวประกาศผู้ชนะในแท็บเอกสาร e-GP พร้อมไฟล์ PDF")
    make_table(
        doc,
        ["เอกสาร", "ลำดับลงนามในกล่องงานรออนุมัติ"],
        [
            ["รายงานผลการพิจารณา", "เจ้าหน้าที่ แล้วหัวหน้าเจ้าหน้าที่ แล้วผู้อำนวยการ"],
            ["ประกาศผู้ชนะ", "ผู้อำนวยการ"],
        ],
        [5.5, 10.5],
    )
    body(doc, "เมื่อลงนามครบ จะไปขั้นตอนเปิดรายการ PO")

    heading(doc, "บทที่ 8 เปิดใบสั่งซื้อ (PO) เมื่อได้ผู้ชนะ", 1)
    body(doc, "เปิด PO ได้จากเอกสารกระบวนการ e-GP หรือจากใบขอซื้อต้นทาง เมื่อปุ่ม สร้าง PO แสดงขึ้น แสดงว่าเงื่อนไขครบแล้ว")
    heading(doc, "8.1 สร้าง PO", 2)
    steps(doc, ["เปิดเอกสารกระบวนการ e-GP แล้วกด สร้าง PO"])
    picture(doc, "Screenshot_ch9_create_po_btn.png", 6.4, "ภาพที่ 91  ปุ่มสร้าง PO ที่ต้องกดบนเอกสารกระบวนการ e-GP")
    steps(doc, ["ตรวจหน้าต่างว่าผู้ขายคือผู้ชนะที่เลือกไว้ เปลี่ยนเป็นรายอื่นไม่ได้"], start=2)
    picture(doc, "Screenshot_ch8_po_wizard.png", 12.8, "ภาพที่ 92  หน้าต่างสร้าง PO แสดงผู้ขายผู้ชนะ (เปลี่ยนรายอื่นไม่ได้)")
    steps(doc, ["ใส่เลขอ้างอิงใบเสนอราคา e-GP ถ้ามี แล้วกด สร้าง PO"], start=3)
    picture(doc, "Screenshot_ch8_po_header.png", 16.6, "ภาพที่ 93  ส่วนหัวของเอกสาร PO")
    picture(doc, "Screenshot_ch8_po_footer.png", 16.6, "ภาพที่ 94  ส่วนท้ายของเอกสาร PO")
    steps(doc, ["ให้พิมพ์ไฟล์และส่งเข้าแอปผู้ขายตามข้อ 8.2"], start=4)
    heading(doc, "8.2 ส่งใบสั่งซื้อให้ผู้ขายยืนยัน", 2)
    body(
        doc,
        "หลังสร้างใบสั่งซื้อแล้ว พัสดุส่งไฟล์ใบสั่งซื้อเข้าแอปผู้ขาย "
        "ผู้ขายเห็นเฉพาะใบที่ส่งเข้าแอป เมื่อลงลายเซ็นและกดบันทึก "
        "สถานะบนใบสั่งซื้อจะกลับมาเป็น ผู้ขายยืนยันแล้ว",
    )
    heading(doc, "8.2.1 พิมพ์ไฟล์ใบสั่งซื้อ และ กดส่งเข้าแอปผู้ขาย", 3)
    steps(
        doc,
        [
            "เปิดฟอร์มใบสั่งซื้อ กดปุ่มพิมพใบสั่งซื้อ ระบบจะสร้าง File ใบสั่งซื้อแนบ "
            "ในแท็ป File ใบสั่งซื้อ กด เปิด File",
        ],
        start=1,
    )
    picture(doc, "Screenshot_ch8_po_print_btn.png", 11.0, "ภาพที่ 95  ปุ่มพิมพ์ใบสั่งซื้อ")
    picture(doc, "Screenshot_ch8_po_files_tab.png", 16.6, "ภาพที่ 96  File แนบของเอกสาร ใบสั่งซื้อ")
    picture(doc, "Screenshot_ch8_po_print_sample.png", 13.9, "ภาพที่ 97  ตัวอย่าง ใบสั่งซื้อ")
    steps(
        doc,
        [
            "กดส่งเข้า แอปผู้ขาย เพื่อยืนยัน เมื่อส่งสำเร็จ "
            "สถานะการยืนยันเปลี่ยนจาก ยังไม่ส่ง เป็น รอผู้ขายยืนยัน",
        ],
        start=2,
    )
    picture(doc, "Screenshot_ch8_po_send_btn.png", 4.6, "ภาพที่ 98  ปุ่มส่งเข้าแอปผู้ขาย")
    picture(doc, "Screenshot_ch8_po_waiting.png", 5.4, "ภาพที่ 99  รูปสถานะ ใบสั่งซื้อ รอยืนยัน")
    heading(doc, "8.2.2 ผู้ขายยืนยัน ใบสั่งซื้อผ่านแอป", 3)
    steps(
        doc,
        ["ผู้ขายเปิดแอป ระบบบริการผู้จำหน่าย ด้วยบัญชี User Portal จะเห็นการ์ดรอยืนยันและยืนยันแล้ว"],
        start=1,
    )
    pictures(
        doc,
        [
            ("Screenshot_ch8_app_1.png", 4.3),
            ("Screenshot_ch8_app_2.png", 4.3),
            ("Screenshot_ch8_app_3.png", 4.3),
        ],
        "ภาพที่ 100  แอป ระบบบริการผู้จำหน่าย ของผู้ขาย มีการ์ดรอยืนยันสำหรับเปิดเอกสารที่จัดซื้อส่งมา",
    )
    steps(
        doc,
        [
            "กดการ์ด รอยืนยัน แล้วแตะใบสั่งซื้อในรายการ เพื่อเปิดเอกสารและดูไฟล์ PDF "
            "จากนั้นกด ลงนามยืนยัน วาดลายเซ็น กดบันทึก",
        ],
        start=2,
    )
    pictures(
        doc,
        [
            ("Screenshot_ch8_app_4.png", 4.3),
            ("Screenshot_ch8_app_5.png", 4.3),
            ("Screenshot_ch8_app_6.png", 4.3),
        ],
    )
    pictures(
        doc,
        [
            ("Screenshot_ch8_app_7.png", 4.3),
            ("Screenshot_ch8_app_8.png", 4.3),
        ],
        "ภาพที่ 101  แสดงการยืนยันและลงนามเอกสารใบสั่งซื้อ",
    )
    heading(doc, "8.2.3 ใบสั่งซื้อ ยืนยันจากผู้ขาย", 3)
    body(
        doc,
        "เมื่อผู้ขายยืนยันใบสั่งซื้อ จากแอป ระบบจะทำการยืนยันเอกสาร "
        "เปลี่ยนสถานะเป็น ผู้ขายยืนยันแล้ว และ สร้างใบรอรับสินค้าให้อัตโนมัติ",
    )
    picture(doc, "Screenshot_ch8_po_confirmed.png", 7.5, "ภาพที่ 102  รูปแสดงสถานะ การยืนยันจากผู้ขาย")

    contract_section(doc)

    heading(doc, "บทที่ 9 กระบวนการตรวจรับ", 1)
    body(
        doc,
        "หลังผู้ขายยืนยันใบสั่งซื้อแล้ว และผู้ขายจะส่งมอบงาน กรรมการตรวจรับ "
        "บันทึกผลตรวจรับในเมนู จัดซื้อ → บันทึกรับมอบงาน",
    )
    heading(doc, "9.1 สร้างใบตรวจรับ", 2)
    steps(
        doc,
        [
            "เปิดเมนู บันทึกรับมอบงาน",
            "กด สร้างใบตรวจรับ ระบบเปิดบันทึกรับมอบงานฉบับร่าง และออกเลขที่ให้",
            "เลือกผู้ขาย (Vendor) และเลือกใบสั่งซื้อ (Purchase Order) ให้ตรงใบที่ยืนยันแล้ว"
            "ระบบจะดึงรายการ สินค้าจากใบสั่งซื้อมาใส่ให้",
            "ตรวจแท็บรายการสินค้า ให้จำนวนและราคามาจากใบสั่งซื้อ ถ้าส่งมอบไม่ครบ "
            "ให้แก้จำนวนเฉพาะแถวที่รับจริง จากนั้นกดตรวจรับ",
        ],
        start=1,
    )
    picture(
        doc,
        "Screenshot_ch9_create_inspection_btn.png",
        16.6,
        "ภาพที่ 103  ปุ่มสร้างใบตรวจรับบนใบสั่งซื้อที่เป็นคำสั่งซื้อ อยู่ถัดจากรับสินค้า",
    )
    callout(
        doc,
        "สร้างซ้ำไม่ได้",
        "ใบสั่งซื้อที่มีใบตรวจรับแล้วยังคงเปิดใบเดิมได้ แต่ปุ่ม สร้างใบตรวจรับ จะไม่แสดงซ้ำ",
        "warn",
    )
    heading(doc, "9.2 กรอกผลการตรวจรับ", 2)
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
    heading(doc, "9.3 กดตรวจรับ", 2)
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
                "กดขอเลขที่ฟอร์มเอกสารที่เกี่ยวข้องแต่ละฉบับ",
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
