#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build volume 3 of the overview-based manuals: warehouse (diagram items 5.1–5.10).

Sources:
- docs/ภาพรวมการทำรายการในระบบ ERP ตามกลุ่มงาน.pdf
- docs/Workflow-Dataflow-งานคลังสินค้า.pptx
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from warehouse_dataflow_data import FUNCTIONS, INTEGRATION, PHASES  # noqa: E402

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "คู่มือการใช้งาน-ตามผังภาพรวม" / "03-คู่มือการใช้งาน-กลุ่มงานคลัง.docx"
FIG = ROOT / "manual_assets" / "figures"
LOGO = FIG / "moph_logo.png"
FIG_NO = {"n": 0}

GREEN = RGBColor(0x0B, 0x68, 0x48)
NAVY = RGBColor(0x0F, 0x29, 0x42)
BODY = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEADER_FILL = "0B6848"


def set_run(run, size=12, bold=False, color=BODY, font_name="Prompt"):
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


def add_text(p, text, size=12, bold=False, color=BODY):
    run = p.add_run(text)
    set_run(run, size, bold, color)
    return run


def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_border(cell, color="D7DEE6"):
    tcPr = cell._tc.get_or_add_tcPr()
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
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), "80")
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def cell_text(cell, text, size=11, bold=False, color=BODY, align="left", fill=None):
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
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    set_narrow_cell_margin(cell)


def make_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, header in enumerate(headers):
        cell_text(table.rows[0].cells[i], header, 11, True, WHITE, "center", HEADER_FILL)
    for r, row in enumerate(rows, 1):
        fill = "F6F8FA" if r % 2 == 0 else "FFFFFF"
        for c, val in enumerate(row):
            cell_text(table.rows[r].cells[c], val, 11, False, BODY, "left", fill)
    if col_widths:
        for row in table.rows:
            for i, width in enumerate(col_widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph()
    return table


def add_bottom_line(paragraph, color="0B6848", size="12"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    el = OxmlElement("w:bottom")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), size)
    el.set(qn("w:space"), "6")
    el.set(qn("w:color"), color)
    pBdr.append(el)
    pPr.append(pBdr)


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run(run, 17 if level == 1 else 14, True, GREEN if level == 1 else NAVY)
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    return p


def body(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    add_text(p, text, 12, False, BODY)
    return p


def figure(doc, name, cap, width=15.6):
    path = FIG / name
    if not path.exists():
        return
    FIG_NO["n"] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_together = True
    p.add_run().add_picture(str(path), width=Cm(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_before = Pt(0)
    c.paragraph_format.space_after = Pt(8)
    add_text(c, f"▲ ภาพที่ {FIG_NO['n']}  {cap}", 10, False, MUTED)


def step(doc, number, text, image=None, cap=""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if image:
        p.paragraph_format.keep_together = True
    add_text(p, f"ขั้นตอนที่ {number}  ", 12, True, GREEN)
    add_text(p, text, 12, False, BODY)
    if image:
        figure(doc, image, cap or text)
    return p


def bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.clear()
        add_text(p, item, 12)
        p.paragraph_format.space_after = Pt(3)


def numbered(doc, items):
    for index, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.5)
        p.paragraph_format.space_after = Pt(3)
        add_text(p, f"{index}. {item}", 12)


def set_table_widths(table, widths):
    table.autofit = False
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    total = int(sum(widths) * 567)
    tblW.set(qn("w:w"), str(total))
    tblW.set(qn("w:type"), "dxa")
    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for child in list(grid):
            grid.remove(child)
    else:
        grid = OxmlElement("w:tblGrid")
        tblPr.addnext(grid)
    for width in widths:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(int(width * 567)))
        grid.append(gc)
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = Cm(width)


def callout(doc, title, text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_widths(table, [16.4])
    cell = table.rows[0].cells[0]
    shade_cell(cell, "EAF3F1")
    set_cell_border(cell, "0B6848")
    p = cell.paragraphs[0]
    p.clear()
    add_text(p, title, 11.5, True, GREEN)
    p2 = cell.add_paragraph()
    add_text(p2, text, 11.5, False, BODY)
    p2.paragraph_format.space_after = Pt(2)
    doc.add_paragraph()


def meta_table(doc, rows):
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_widths(table, [4.6, 11.8])
    for r, (label, value) in enumerate(rows):
        cell_text(table.rows[r].cells[0], label, 10.5, True, GREEN, "left", "EAF3F1")
        cell_text(table.rows[r].cells[1], value, 10.5, False, BODY, "left", "FFFFFF")
    doc.add_paragraph()
    return table


def scope_table(doc, title, task, document, menu, code):
    rows = [
        ("หัวข้องานตามผังภาพรวม", title),
        ("รายละเอียดงาน (Task)", task),
        ("เอกสารในระบบ (Document)", document),
        ("เมนูใช้งาน / ผู้รับผิดชอบ", menu),
        ("รหัสใน Dataflow", code),
    ]
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_widths(table, [4.8, 11.6])
    cell_text(table.rows[0].cells[0], rows[0][0], 11, True, WHITE, "left", "0F2942")
    cell_text(table.rows[0].cells[1], rows[0][1], 11.5, True, WHITE, "left", "0B6848")
    for r, (label, value) in enumerate(rows[1:], 1):
        cell_text(table.rows[r].cells[0], label, 10.5, True, NAVY, "left", "F1F5F9")
        cell_text(table.rows[r].cells[1], value, 11, False, BODY, "left", "EAF3F1")
    doc.add_paragraph()
    return table


def add_page_number(paragraph):
    def _run():
        run = paragraph.add_run()
        set_run(run, 9, False, MUTED)
        return run._r

    begin = _run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    begin.append(fld)
    instr_run = _run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    instr_run.append(instr)
    end = _run()
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    end.append(fld_end)


def cover_line(doc, text, size, bold, color, space_after=0, space_before=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    add_text(p, text, size, bold, color)
    return p


def toc_title(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    add_text(p, text, 18, True, GREEN)
    return p


def build():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_text(header, "คู่มือการใช้งานระบบ ERP (VPK) — กลุ่มงานคลัง (5.1 – 5.10)", 8.5, False, MUTED)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pPr = footer._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), "6")
    top.set(qn("w:space"), "6")
    top.set(qn("w:color"), "CBD5E1")
    pBdr.append(top)
    pPr.append(pBdr)
    add_text(footer, "โรงพยาบาลวชิระภูเก็ต · คู่มือปฏิบัติงานระบบคลัง (5.1 – 5.10) | หน้า ", 9, False, MUTED)
    add_page_number(footer)

    if LOGO.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(LOGO), width=Cm(2.2))

    cover_line(doc, "โรงพยาบาลวชิระภูเก็ต", 16, True, NAVY, space_after=0)
    cover_line(doc, "VACHIRAPHUKET HOSPITAL — ERP (VPK)", 10.5, True, MUTED, space_after=8)
    cover_line(doc, "คู่มือการปฏิบัติงานตามผังสรุปภาพรวมการบันทึกรายการในระบบ ERP", 12.5, True, GREEN, space_after=4)
    cover_line(doc, "คู่มือการใช้งาน : กลุ่มงานคลัง", 24, True, NAVY, space_after=2)
    cover_line(doc, "รอรับสินค้าและสถานะงานคลัง (5.1) · ตรวจคุณภาพขาเข้า (5.2) · รับสินค้าเข้าคลัง (5.3)", 11, False, BODY)
    cover_line(doc, "จัดเก็บ (5.4) · เบิกจ่าย/ขอโอน (5.5) · เติมสินค้า (5.6) · ผลิตสินค้าภายใน (5.7)", 11, False, BODY)
    cover_line(doc, "รับของยืมด่วน (5.8) · ข้อมูลสินค้าและคลัง (5.9) · รับส่งข้อมูลกับ HIS (5.10)", 11, False, BODY, space_after=8)

    meta_table(
        doc,
        [
            ("รหัสเอกสาร", "UM-ERP-VPK-G03"),
            ("เอกสารอ้างอิงหลัก", "ภาพรวมการทำรายการในระบบ ERP ตามกลุ่มงาน.pdf และ Workflow-Dataflow-งานคลังสินค้า.pptx"),
            ("หัวข้อที่ครอบคลุม", "งานกลุ่มงานคลังข้อ 5.1 ถึง 5.10 และจุดที่หน่วยงานขอเบิกพัสดุตามข้อ 2.3"),
            ("โมดูลในระบบ", "stock, vpk_stock_warehouse, vpk_stock_qc, vpk_stock_location, vpk_vendor_loan, vpk_his_api, mrp"),
            ("กลุ่มผู้ใช้งาน", "เจ้าหน้าที่คลัง, ผู้ตรวจคุณภาพ, หน่วยงานผู้ขอเบิก, เภสัชกร, ผู้ผลิตยา"),
            ("รูปแบบคู่มือ", "แบ่งบทตามข้อบนผังภาพรวม อธิบายงานก่อน แล้วไล่ขั้นตอนที่ทำในระบบ"),
            ("เวอร์ชันเอกสาร", "1.0 (วันที่ 6 พฤศจิกายน พ.ศ. 2569)"),
            ("เอกสารคู่กัน", "คู่มือกลุ่มงานพัสดุ UM-ERP-VPK-G02 (ออกใบสั่งซื้อ 3.3 และสร้างใบตรวจรับ 3.4)"),
        ],
    )

    toc_title(doc, "สารบัญและโครงสร้างคู่มือตามผังภาพรวม")
    body(
        doc,
        "คู่มือฉบับนี้เป็นเล่มที่ 3 ของชุดคู่มือตามผังสรุปภาพรวม "
        "ครอบคลุมคอลัมน์กลุ่มงานคลัง ข้อ 5.1 ถึง 5.10 "
        "และงานขอเบิกพัสดุของหน่วยงานในข้อ 2.3 "
        "หมายเลขในวงเล็บต่อท้ายชื่อบทคือเลขข้อบนผังภาพรวม "
        "รหัส A–E และ W ในตารางขอบเขตงานคือรหัสฟังก์ชันใน Workflow & Dataflow งานคลังสินค้า "
        "รายละเอียดทั้งสายงานอยู่ในภาคผนวก ก",
    )
    make_table(
        doc,
        ["บทในคู่มือ", "หัวข้อในคู่มือ (รหัสอ้างอิงผังภาพรวม)", "งานที่ปฏิบัติในระบบ (Tasks)", "เอกสารในระบบ (Documents)"],
        [
            ["บทที่ 1", "รอรับสินค้าและติดตามสถานะงานคลัง (5.1)", "ดูคิวรับ ของรอโอน และของรอจ่าย ก่อนวันของมา", "Dashboard สถานะงานคลัง, ตารางการส่งจากผู้ขาย"],
            ["บทที่ 2", "ตรวจคุณภาพขาเข้า (5.2)", "นับของที่มาส่ง แล้วบันทึกผลตรวจคุณภาพ", "ใบตรวจคุณภาพขาเข้า (Stock QC)"],
            ["บทที่ 3", "รับสินค้าเข้าคลัง (5.3)", "QC ผ่าน แล้วกรรมการตรวจรับ จากนั้นรับของเข้าคลัง", "ใบตรวจรับพัสดุ (WA), ใบรับสินค้าเข้าคลัง"],
            ["บทที่ 4", "จัดเก็บ (5.4)", "จัดเก็บตามกฎตำแหน่งหลัง QC ผ่าน และเมื่อของถึงปลายทาง", "กฎจัดเก็บ (putaway)"],
            ["บทที่ 5", "เบิกจ่าย/ขอโอน (5.5) และขอเบิกของหน่วยงาน (2.3)", "รับใบเบิก หยิบ แพ็ค ส่งปลายทาง หรือจ่ายออก", "ใบเบิกพัสดุ, ใบหยิบ, ฉลากติดกล่อง, ใบจ่ายออก"],
            ["บทที่ 6", "การเติมสินค้า (5.6)", "เติมตามขั้นต่ำ-สูงสุด และเปิดใบขอซื้อเมื่อของไม่พอ", "ใบโอนอัตโนมัติ, ใบขอซื้อ"],
            ["บทที่ 7", "การผลิตสินค้าภายใน (5.7)", "ตั้งสูตร สั่งผลิต แล้วรับยาสำเร็จรูปเข้าคลัง", "ใบสั่งผลิต"],
            ["บทที่ 8", "รับของยืมด่วน (5.8)", "รับของยืมจากผู้ขาย แล้วเปิดขอซื้อตามหลัง", "ใบยืมพัสดุจากผู้ขาย"],
            ["บทที่ 9", "การจัดการข้อมูลสินค้าและคลัง (5.9)", "ดูแลโครงสร้างคลัง จุดเก็บ และข้อมูลสินค้าที่ใช้ทุกสายงาน", "ข้อมูลคลัง, ข้อมูลสินค้า"],
            ["บทที่ 10", "การรับส่งข้อมูลกับระบบ HIS (5.10)", "รับคำขอเบิกเติมและชุดตัดจ่าย แล้วให้เภสัชกรกด Post", "คิว HIS เบิกเติมคลัง, คิว HIS ตัดจ่ายสินค้า"],
        ],
        [2.0, 5.2, 4.8, 4.4],
    )

    body(
        doc,
        "รายการตัวอย่างที่ใช้เดินทั้งเล่มคือยา [00003] CARMINATIVE MIXTURE 180 ML GPO "
        "ผู้ขาย บ.ดีเคเอ็มเอส จก. ใบสั่งซื้อ P00003 ใบรับ WH/IN/00004 จำนวน 4.00 ขวด "
        "ล็อต L26001 หมดอายุ 31/12/2027 ต้นทุน 580.00 บาทต่อขวด "
        "จากนั้นโอน 1.00 ขวดไปคลังยา ผลิตยาพาราเซตามอลรุ่นย่อย 1,000.00 เม็ด "
        "และยืม [00002] MILK OF MAGNESIA 240 ML จำนวน 1.00 ขวด "
        "ภาพใต้แต่ละขั้นตอนคือหน้าจอของรายการตัวอย่างนี้",
    )
    figure(
        doc,
        "fig_erp_overview_page1.png",
        "ผังสรุปภาพรวมการบันทึกรายการในระบบ ERP คอลัมน์กลุ่มงานคลังคือข้อ 5.1 ถึง 5.10",
        16.2,
    )

    heading(doc, "บทที่ 1 รอรับสินค้าและติดตามสถานะงานคลัง (5.1)")
    scope_table(
        doc,
        "รอรับสินค้าและติดตามสถานะงานคลัง (5.1)",
        "ดูคิวงานรับ งานโอน และงานเบิกใช้ภายใน และดูแผนของที่จะมาส่งก่อนวันรับ",
        "Dashboard สถานะงานคลัง, ตารางการส่งจากผู้ขาย",
        "เมนู: สินค้าคงคลัง → Dashboard → สถานะงานคลัง และ ตารางการส่งจากผู้ขาย  |  ผู้ปฏิบัติ: เจ้าหน้าที่คลัง",
        "A2 ตารางการส่งจากผู้ขาย · แดชบอร์ดสามสายใน Dataflow",
    )
    body(
        doc,
        "ข้อ 5.1 เป็นจุดเริ่มของวันทำงานคลัง ยังไม่รับของเข้าสต็อกในหน้านี้ "
        "ใช้ดูว่างานค้างที่ขั้นใด แล้วเปิดใบจากสถานะนั้นไปทำตามบทถัดไป "
        "ใบรับสินค้าถูกสร้างให้อัตโนมัติเมื่อจัดซื้อยืนยันใบสั่งซื้อ ตามคู่มือพัสดุข้อ 3.3 และจุดเชื่อม W1",
    )
    heading(doc, "1.1 เปิดแดชบอร์ดสถานะงานคลัง (5.1)", 2)
    body(doc, "แดชบอร์ดแบ่งสามสาย ให้กดการ์ดสถานะเพื่อเปิดรายการของสถานะนั้น")
    step(doc, 1, "เข้าแอปสินค้าคงคลัง แล้วเปิด Dashboard → สถานะงานคลัง เลือกคลังที่จะดู ตัวอย่างนี้เลือกคลังกลาง (WH) และช่วง 30 วัน", "Screenshot_inv_ops_dashboard.png", "แดชบอร์ดสถานะงานคลังสินค้าของคลังกลาง แสดงการรับสินค้า การโอนสินค้า และการเบิกใช้ภายใน")
    step(doc, 2, "สายการรับสินค้า ดูลำดับ รอรถมา → ตรวจรับ → QC → จัดเก็บ → เสร็จสิ้น ใบ WH/IN/00004 ที่ยังไม่รับจะอยู่ช่วงรอรถมาหรือตรวจรับ")
    step(doc, 3, "สายการโอนสินค้า ดูลำดับ สร้างใบโอน → จัดสินค้า → ขนส่ง → รอรับ → รับแล้ว")
    step(doc, 4, "สายการเบิกใช้ภายใน ดูลำดับ รออนุมัติ → รอจัด → กำลังจัด → พร้อมรับ → จ่ายแล้ว ใบร่างของหน่วยงานจะขึ้นคำว่า รออนุมัติ")
    callout(
        doc,
        "คำว่า รออนุมัติ บนแดชบอร์ด (5.1)",
        "ระบบยังไม่มีขั้นอนุมัติใบขอเบิกแยกต่างหาก ใบร่างที่หน่วยงานส่งมาถูกเรียกว่า รออนุมัติ เพื่อให้คลังเห็นคิว คลังรับรายการต่อได้ในบทที่ 5",
    )
    heading(doc, "1.2 ดูตารางการส่งจากผู้ขายก่อนวันรับ (5.1)", 2)
    body(doc, "ใช้จัดคนและพื้นที่รอรับ วันเลยกำหนดแสดงเป็นสีแดง")
    step(doc, 1, "เปิด สินค้าคงคลัง → ตารางการส่งจากผู้ขาย ตัวอย่างวันที่ 30 ก.ย. 2026 มี [00003] จำนวน 4.00 ขวด จาก บ.ดีเคเอ็มเอส จก. เข้า WH/Stock อ้าง P00003 และใบรับ WH/IN/00004 สถานะพร้อม วันเลยกำหนดเป็นตัวแดง", "Screenshot_inv_vendor_schedule.png", "ตารางการส่งจากผู้ขาย WH/IN/00004 ของยา [00003] จำนวน 4.00 ขวด เลยกำหนดและยังไม่รับเข้า")
    step(doc, 2, "กดมุมมองปฏิทินเพื่อจัดคนรอรับ ในเดือนกันยายน 2569 วันที่ 25 คือใบของ P00002 และวันที่ 30 คือใบของ P00003 อย่าลากจุดบนปฏิทิน เพราะวันนัดส่งในใบรับจะเปลี่ยนตาม", "Screenshot_inv_vendor_calendar.png", "ปฏิทินกันยายน 2569 วันที่ 25 และ 30 มีของนัดส่งจากผู้ขาย")
    step(doc, 3, "เมื่อของมาถึง กดเปิดใบรับจากแถวนั้น คิวรับของคลังกลางแสดงใบสถานะพร้อม แล้วไปตรวจคุณภาพตามบทที่ 2", "Screenshot_inv_wh_in_list.png", "คิวรับของสถานะพร้อม วันที่แดงคือเลยวันนัดส่ง")

    heading(doc, "บทที่ 2 ตรวจคุณภาพขาเข้า (5.2)")
    scope_table(
        doc,
        "ตรวจคุณภาพขาเข้า (QC) (5.2)",
        "นับจำนวนของที่มาส่ง แล้วตรวจคุณภาพหรืออุณหภูมิก่อนโอนเข้าคลังพร้อมใช้",
        "ใบตรวจคุณภาพขาเข้า (Stock QC)",
        "เมนู: ใบรับ → ปุ่มตรวจคุณภาพ หรือ สินค้าคงคลัง → ตรวจคุณภาพสินค้า  |  ผู้ปฏิบัติ: เจ้าหน้าที่คลัง และผู้ตรวจคุณภาพ",
        "A3 นับจำนวนที่พื้นที่รับของ · A4 ทำ QC",
    )
    body(
        doc,
        "ของขั้นนี้ยังอยู่พื้นที่รับของ ยอดคงคลังยังไม่เพิ่ม "
        "ลำดับรับของมีสามขั้น ทำข้ามไม่ได้ คือ QC ผ่าน แล้วกรรมการตรวจรับ แล้วจึงรับของเข้าคลัง",
    )
    heading(doc, "2.1 นับของที่มาส่ง (5.2)", 2)
    step(doc, 1, "เปิดใบ WH/IN/00004 ตรวจรับจาก บ.ดีเคเอ็มเอส จก. ประเภทคลังกลาง: Receipts ปลายทาง WH/Stock เอกสารอ้างอิง P00003 รายการ [00003] CARMINATIVE MIXTURE 180 ML GPO", "Screenshot_inv_wh_in_form.png", "ใบรับ WH/IN/00004 สถานะพร้อม ยา [00003] จำนวน 4.00 ขวด อ้างใบสั่งซื้อ P00003")
    step(doc, 2, "ของมาครบ ให้ช่องปริมาณเท่าช่องต้องการ คือ 4.00 ขวด ถ้ามาไม่ครบให้แก้เฉพาะช่องปริมาณ เช่น รับจริง 2.00 ขวด อย่าแก้ช่องต้องการ", "Screenshot_inv_qty_full.png", "รับเต็มจำนวน ต้องการ 4.00 เท่ากับปริมาณ 4.00 ขวด")
    figure(doc, "Screenshot_inv_qty_partial.png", "ตัวอย่างรับบางส่วน ต้องการ 4.00 แต่ปริมาณที่รับจริงเป็น 2.00 ขวด")
    step(doc, 3, "บันทึกใบรับไว้ ของยังอยู่พื้นที่รับของ ขั้นต่อไปคือให้ QC ผ่าน ยังไม่ส่งกรรมการและยังไม่กดตรวจสอบ")
    heading(doc, "2.2 บันทึกผลตรวจคุณภาพ (5.2)", 2)
    step(doc, 1, "ที่ใบ WH/IN/00004 กดตรวจคุณภาพ แถบเหลืองบอกว่าต้องตรวจให้ผ่านก่อนรับเข้า ระบบเปิดใบตรวจและใส่จุดตรวจของคลังกลางกับยานี้", "Screenshot_inv_qc_receipt.png", "ใบรับมีย่านสีเหลืองและปุ่มตรวจคุณภาพก่อนกดตรวจสอบ")
    figure(doc, "Screenshot_inv_qc_form.png", "ใบตรวจคุณภาพ จุดที่ต้องตรวจอยู่ในตาราง แล้วกดตรวจจุดควบคุม")
    step(doc, 2, "ผู้ตรวจบันทึกทีละจุด ข้อผ่านหรือไม่ผ่านกดปุ่มตามผล ของ Cold Chain ให้พิมพ์อุณหภูมิแล้วกดยืนยันค่า ช่วงที่ยอมรับคือ 2 ถึง 8 องศาเซลเซียส", "Screenshot_inv_qc_passfail.png", "ปุ่มผ่านและไม่ผ่านของข้อที่ไม่ได้วัดค่า")
    figure(doc, "Screenshot_inv_qc_measure.png", "พิมพ์อุณหภูมิแล้วกดยืนยันค่า ช่วงที่ยอมรับอยู่ที่ค่าต่ำสุดและค่าสูงสุด")
    step(doc, 3, "เมื่อทุกข้อเป็นผ่าน ให้กดบันทึกผลตรวจ แถบเหลืองบนใบรับจะหาย นี่คือขั้น QC ผ่าน ยังไม่กดตรวจสอบใบรับ", "Screenshot_inv_qc_result.png", "ทุกข้อเป็นผ่านแล้ว จึงกดบันทึกผลตรวจ")
    figure(doc, "Screenshot_inv_qc_cleared.png", "QC ผ่านแล้ว แถบเหลืองหาย ใบ WH/IN/00004 ยังเป็นพร้อม รอกรรมการตรวจรับ")
    step(doc, 4, "ถ้ามีข้อไม่ผ่าน ให้หยุดไว้ แจ้งผู้ขายหรือส่งคืน และอย่ากดตรวจสอบใบรับ ของค้างที่พื้นที่รับของ ค่านอกช่วงให้กดแก้ค่าหรือยืนยันไม่ผ่าน", "Screenshot_inv_qc_measure_fail.png", "ค่านอกช่วง กดแก้ค่าเพื่อใส่ใหม่ หรือยืนยันไม่ผ่านถ้าของรับไม่ได้")
    callout(
        doc,
        "QC ไม่ผ่าน รับเข้าคลังไม่ได้ (5.2)",
        "ใบที่ผลตรวจไม่ผ่านจะไปขั้นกรรมการตรวจรับไม่ได้ และรับเข้าคลังไม่ได้ ของค้างที่พื้นที่รับของจนกว่าจะส่งของใหม่หรือปิดรายการตามที่ตกลงกับผู้ขาย",
    )

    heading(doc, "บทที่ 3 รับสินค้าเข้าคลัง (5.3)")
    scope_table(
        doc,
        "รับสินค้าเข้าคลัง (5.3)",
        "ทำสามขั้นตามลำดับ QC ผ่าน กรรมการตรวจรับ แล้วรับของเข้าคลัง พร้อมบันทึกล็อตตอนรับเข้า",
        "ใบรับสินค้าเข้าคลัง (Incoming GRN), ใบตรวจรับพัสดุ (WA)",
        "เมนู: ใบรับสินค้า และ จัดซื้อ → ตรวจรับมอบงาน  |  ผู้ปฏิบัติ: ผู้ตรวจคุณภาพ, คณะกรรมการตรวจรับ, เจ้าหน้าที่คลังผู้มีสิทธิรับสินค้า",
        "A4 QC ผ่าน · A6 กรรมการตรวจรับ · A5 และ A7 บันทึกล็อตแล้วรับเข้าคลัง",
    )
    body(
        doc,
        "ใบ WH/IN/00004 ของยา [00003] จะรับเข้าคลังได้เมื่อครบสามขั้นนี้เท่านั้น "
        "ขั้นที่ 1 QC ผ่านตามบทที่ 2 "
        "ขั้นที่ 2 กรรมการตรวจรับยืนยันใบตรวจรับ "
        "ขั้นที่ 3 คลังบันทึกล็อตแล้วกดตรวจสอบ ของจึงเข้า WH/Stock "
        "การใส่จำนวนหรือบันทึกล็อตก่อนกดตรวจสอบ ยังไม่ทำให้ยอดคงคลังเพิ่ม",
    )
    heading(doc, "3.1 ขั้นที่ 1 QC ผ่าน (5.2)", 2)
    body(doc, "ใช้ผลจากบทที่ 2 ถ้า QC ยังไม่ผ่าน ห้ามส่งกรรมการตรวจรับและห้ามกดตรวจสอบใบรับ")
    step(doc, 1, "เปิดใบ WH/IN/00004 ตรวจว่าแถบเหลืองเรื่องตรวจคุณภาพหายไป และผลตรวจเป็นผ่าน", "Screenshot_inv_qc_cleared.png", "QC ของใบ WH/IN/00004 ผ่านแล้ว ใบยังเป็นสถานะพร้อม")
    step(doc, 2, "ของยังอยู่พื้นที่รับของ ยังไม่บันทึกให้เข้าคลัง ส่งงานต่อให้กรรมการตรวจรับ")
    heading(doc, "3.2 ขั้นที่ 2 กรรมการตรวจรับ (4.2)", 2)
    body(
        doc,
        "ทำหลัง QC ผ่าน และก่อนรับของเข้าคลัง "
        "พัสดุสร้างใบตรวจรับจากใบสั่งซื้อ P00003 ตามคู่มือกลุ่มงานพัสดุบทที่ 5 "
        "คณะกรรมการบันทึกผลตามผังข้อ 4.2 ผลไม่ผ่านจะตรวจรับไม่ได้ และคลังรับของเข้าคลังไม่ได้",
    )
    step(doc, 1, "เปิด จัดซื้อ → ตรวจรับมอบงาน ของใบสั่งซื้อ P00003 ตรวจรายการยา [00003] ให้ตรงปริมาณบนใบรับ", "Screenshot_ch10_form.png", "บันทึกรับมอบงานที่กรรมการใช้ตรวจรับหลัง QC ผ่าน")
    step(doc, 2, "ตรวจรายชื่อคณะกรรมการที่ดึงจากคำสั่งแต่งตั้ง แล้วบันทึกผลว่าครบถ้วนหรือบางส่วน จากนั้นกดตรวจรับและลงวันที่ตรวจรับ", "Screenshot_ch10_committee.png", "แท็บคณะกรรมการตรวจรับบนใบตรวจรับ")
    step(doc, 3, "เมื่อใบตรวจรับเป็นยืนยันตรวจรับ และปริมาณตรงกับใบ WH/IN/00004 คลังจึงไปขั้นรับของเข้าคลัง ถ้าผลไม่ผ่าน ให้หยุดไว้ที่พื้นที่รับของ")
    callout(
        doc,
        "ยังไม่กดตรวจสอบใบรับในขั้นนี้ (4.2)",
        "กรรมการตรวจรับเป็นการยืนยันผลบนใบตรวจรับ ยังไม่ใช่การรับของเข้าคลัง ยอดคงคลังยังไม่เพิ่มจนกว่าคลังจะทำขั้นที่ 3",
    )
    heading(doc, "3.3 ขั้นที่ 3 รับของเข้าคลัง (5.3)", 2)
    body(doc, "ทำเมื่อ QC ผ่านและใบตรวจรับยืนยันแล้วเท่านั้น ผู้กดต้องเป็นผู้มีสิทธิรับสินค้า")
    step(doc, 1, "เปิดแท็บรายละเอียดการปฏิบัติการของใบ WH/IN/00004 ใส่ล็อต L26001 หมดอายุ 31/12/2027 จำนวนในแท็บล็อตต้องเท่าปริมาณที่รับ ถ้ารับครบคือ 4.00 ขวด", "Screenshot_inv_lot.png", "บันทึกล็อต L26001 ก่อนกดตรวจสอบรับเข้าคลัง")
    step(doc, 2, "ถ้าอายุคงเหลือต่ำกว่าเกณฑ์ ให้แนบใบรับรองเปลี่ยนยา แล้วบันทึกใบรับ ยังไม่กดตรวจสอบจนกว่าล็อตจะครบ")
    step(doc, 3, "ผู้มีสิทธิรับสินค้ากดตรวจสอบ ถ้ารับไม่ครบ เช่น ต้องการ 4.00 แต่รับ 2.00 ให้เลือกเปิดใบรับค้างสำหรับส่วนที่เหลือ", "Screenshot_inv_backorder.png", "ถ้าของมาไม่ครบ ระบบถามว่าจะเปิดใบรับส่วนที่เหลือหรือไม่")
    step(doc, 4, "เมื่อรับครบ ใบเป็นเสร็จสิ้น ยา [00003] 4.00 ขวดเข้า WH/Stock ต้นทุน 580.00 บาทต่อขวด มูลค่า 2,320.00 บาท", "Screenshot_inv_done.png", "หลังกรรมการตรวจรับและกดตรวจสอบ ของ 4.00 ขวดเข้าคลัง")
    figure(doc, "Screenshot_inv_product_cost.png", "หน้าสินค้า [00003] มียอด 4.00 ขวด และต้นทุน 580.00 บาทต่อขวด")
    figure(doc, "Screenshot_inv_onhand.png", "ของเข้า WH/Stock ล็อต L26001 จำนวน 4.00 ขวด")

    heading(doc, "บทที่ 4 จัดเก็บ (5.4)")
    scope_table(
        doc,
        "จัดเก็บตามตำแหน่ง (5.4)",
        "จัดเก็บตามเส้นทางที่กำหนดไว้ตามกลุ่มสินค้า ไม่ต้องเลือกชั้นเก็บทีละชิ้นถ้ากฎจัดเก็บตั้งไว้แล้ว",
        "กฎจัดเก็บ (putaway)",
        "เมนู: แดชบอร์ดการรับ สถานะจัดเก็บ และใบอัปเดตปลายทางตอนโอน  |  ผู้ปฏิบัติ: เจ้าหน้าที่คลัง",
        "สถานะจัดเก็บบนแดชบอร์ดรับ · C3 วางของตามกฎชั้นเก็บของปลายทาง",
    )
    body(
        doc,
        "ข้อ 5.4 ไม่ใช่ใบใหม่ ของจากผู้ขายเข้าตำแหน่งเมื่อรับของเข้าคลังในขั้นที่ 3 ของบทที่ 3 แล้ว "
        "คือหลัง QC ผ่านและกรรมการตรวจรับยืนยัน ของโอนระหว่างคลังเข้าตำแหน่งเมื่อกดตรวจสอบใบอัปเดตปลายทางในบทที่ 5",
    )
    heading(doc, "4.1 จัดเก็บของที่รับจากผู้ขาย (5.4)", 2)
    step(doc, 1, "หลังรับของเข้าคลังในบทที่ 3 ขั้นที่ 3 แดชบอร์ดการรับของใบ WH/IN/00004 เป็นจัดเก็บแล้ว")
    step(doc, 2, "ยา [00003] ล็อต L26001 จำนวน 4.00 ขวดอยู่ที่ WH/Stock ตามกฎจัดเก็บของคลังกลาง", "Screenshot_inv_onhand.png", "จัดเก็บแล้วที่ WH/Stock ล็อต L26001 จำนวน 4.00 ขวด")
    step(doc, 3, "ถ้าของไปผิดตำแหน่ง ให้ตรวจกฎจัดเก็บของกลุ่มสินค้าก่อน อย่าแก้ที่ยอดคงคลังเป็นอย่างแรก")
    heading(doc, "4.2 จัดเก็บเมื่อของถึงคลังปลายทาง (5.4)", 2)
    step(doc, 1, "เมื่อโอนยา [00003] ถึงคลังยา การกดตรวจสอบใบอัปเดตปลายทางจะวางล็อต L26001 ที่ชั้น PHAR/Stock/G ตามกฎชั้นเก็บ", "Screenshot_inv_int_package.png", "กล่อง PACK0000002 อยู่ที่ PHAR/Stock/G ล็อต L26001 จำนวน 1.00 ขวด")
    step(doc, 2, "ยอดรวมทั้งโรงพยาบาลไม่เพิ่ม เปลี่ยนเฉพาะคลังที่ถือของ ตัวอย่างหลังแกะกล่องแล้วยังอยู่ชั้น PHAR/Stock/G", "Screenshot_inv_int_unpack_qty.png", "ของพร้อมใช้ที่ PHAR/Stock/G ล็อต L26001 ไม่ได้อยู่ในกล่อง")

    heading(doc, "บทที่ 5 เบิกจ่ายและขอโอน (5.5)")
    scope_table(
        doc,
        "เบิกจ่าย/ขอโอน ตามคำขอ (5.5)",
        "รับใบเบิกจากหน่วยงาน หยิบ แพ็คลงกล่อง แล้วให้ปลายทางรับ หรือจ่ายออกจากคลังโดยไม่โอนไปเก็บต่อ",
        "ใบเบิกพัสดุ (Internal Transfer), ใบหยิบ, ฉลากติดกล่องพัสดุ, ใบจ่ายออก",
        "เมนู: สินค้าคงคลัง → การปฏิบัติการ → โอน → ขอโอนสินค้า และ ใบจ่ายออก  |  ผู้ปฏิบัติ: หน่วยงานผู้ขอ และเจ้าหน้าที่คลัง",
        "B1 หน่วยงานขอเอง · B4 คลังรับรายการ · C1–C4 หยิบ แพ็ค ปลายทาง · D1 จ่ายออก",
    )
    body(
        doc,
        "ฝั่งหน่วยงานคือข้อ 2.3 ขอเบิกพัสดุจากคลัง งานของหน่วยงานจบเมื่อส่งใบร่าง "
        "การหยิบ แพ็ค และอัปเดตปลายทางเป็นงานคลัง ของย้ายจริงทีละขั้นเมื่อกดตรวจสอบ "
        "ล็อตถูกจองตามวันหมดอายุก่อน",
    )
    heading(doc, "5.1 หน่วยงานสร้างใบขอเบิก (2.3)", 2)
    step(doc, 1, "เปิด สินค้าคงคลัง → การปฏิบัติการ → โอน → ขอโอนสินค้า แล้วกดใหม่ ตัวอย่างต้นทาง WH/Stock ปลายทาง PHAR/Stock เอกสารอ้างอิง เติมคลังยา", "Screenshot_inv_51_step1.png", "ใบขอโอนใหม่ สถานะร่าง จาก WH/Stock ไป PHAR/Stock")
    step(doc, 2, "ใส่ยา [00003] จำนวน 1.00 ขวด ซึ่งไม่เกินยอด 4.00 ขวดที่รับเข้าไว้ ใบยังเป็นร่าง", "Screenshot_inv_51_step2.png", "เพิ่มยา [00003] จำนวน 1.00 ขวด ใบยังเป็นร่าง รอคลังรับรายการ")
    step(doc, 3, "บันทึกแล้วส่งใบร่างให้คลัง ใบจะไปอยู่กลุ่มรออนุมัติบนแดชบอร์ด")
    heading(doc, "5.2 คลังรับรายการและจองของ (5.5)", 2)
    step(doc, 1, "เปิดใบขอเบิกสถานะร่างของยา [00003] จำนวน 1.00 ขวด ตรวจปลายทาง PHAR/Stock")
    step(doc, 2, "กดตั้งเป็นสิ่งที่ต้องทำ ตัวอย่างเปลี่ยนเป็นใบหยิบ WH/PICK/00007 จาก WH/Stock ไป WH/Packing Zone สถานะพร้อม และระบบเปิดใบแพ็คกับใบอัปเดตปลายทางไว้รอ", "Screenshot_inv_51_step3.png", "หลังรับรายการ ได้ใบหยิบ WH/PICK/00007 สถานะพร้อม")
    step(doc, 3, "ของพอ ระบบจองล็อต L26001 ให้ครบ 1.00 ขวด ถ้าพอแค่บางส่วนจะจองเท่าที่มี และเปิดใบค้างตอนตรวจสอบใบหยิบ", "Screenshot_inv_51_step4.png", "แท็บรายละเอียดการปฏิบัติการของใบหยิบ ระบบจองล็อต L26001")
    step(doc, 4, "ถ้าต้นทางไม่มีของ ระบบไม่จอง และงานเติมสต็อกจะเปิดใบขอซื้อตามบทที่ 6")
    heading(doc, "5.3 หยิบ แพ็ค และให้ปลายทางรับ (5.5)", 2)
    step(doc, 1, "ที่ใบหยิบ WH/PICK/00007 กดพิมพ์ใบหยิบของ ไปหยิบล็อต L26001 ที่จุดเก็บ แล้วกดตรวจสอบ ของเข้าจุดแพ็ค", "Screenshot_inv_51_step5.png", "ปุ่มพิมพ์ใบหยิบของและปุ่มตรวจสอบบนใบหยิบ")
    step(doc, 2, "เปิดใบแพ็ค WH/PACK/00008 กดใส่ในแพ็ค ได้กล่อง PACK0000002 แล้วกดตรวจสอบ ของไป WH/Output", "Screenshot_inv_51_step6.png", "ใบแพ็ค WH/PACK/00008 กดใส่ในแพ็คแล้วตรวจสอบ")
    figure(doc, "Screenshot_inv_int_label.png", "ฉลากกล่อง PACK0000002 ยา [00003] ล็อต L26001 จำนวน 1.00 ขวด")
    step(doc, 3, "เปิดใบอัปเดตปลายทาง WH/INT/00035 จาก WH/Output ไป PHAR/Stock แล้วกดตรวจสอบ ของ 1.00 ขวดเข้าคลังยา", "Screenshot_inv_51_step7.png", "ใบอัปเดตปลายทาง WH/INT/00035 กดตรวจสอบเพื่อให้ของเข้า PHAR/Stock")
    figure(doc, "Screenshot_inv_int_handover.png", "หลังตรวจสอบ ใบโอนเสร็จสิ้น ส่งมอบ 1.00 ขวดไป PHAR/Stock")
    step(doc, 4, "ถ้าใช้แอปสแกนบาร์โค้ด ให้สแกนยา [00003] หรือล็อต L26001 เข้าบรรทัด ใส่ในแพ็ค แล้วตรวจสอบจากแอปได้")
    callout(
        doc,
        "ทำตามลำดับใบ ข้ามขั้นไม่ได้ (5.5)",
        "ใบแพ็คจะพร้อมเมื่อตรวจใบหยิบแล้ว และใบอัปเดตปลายทางจะพร้อมเมื่อตรวจใบแพ็คแล้ว ก่อนปลายทางกดตรวจสอบ ของอยู่ระหว่างทาง ยอดรวมโรงพยาบาลยังไม่เปลี่ยนคลัง",
    )
    heading(doc, "5.4 จ่ายออกให้หน่วยงานใช้เลย (5.5)", 2)
    body(doc, "ใช้เมื่อเบิกใช้จากคลังโดยไม่โอนไปเก็บที่คลังปลายทาง ยังไม่ยืนยันจะจ่ายของไม่ได้")
    step(doc, 1, "เปิด การปฏิบัติการ → ใบจ่ายออก ใส่หน่วยงานผู้ขอและรายการ ใบร่างอยู่บนแดชบอร์ดเป็นรออนุมัติ")
    step(doc, 2, "กดยืนยัน สถานะเป็นรอจัด จากนั้นระบบจองล็อตที่หมดอายุก่อน สถานะเป็นกำลังจัด")
    step(doc, 3, "เมื่อสถานะเป็นพร้อมรับ ให้กดตรวจสอบที่คลัง สถานะเป็นจ่ายแล้ว และตัดสต็อกตามล็อต")

    heading(doc, "บทที่ 6 การเติมสินค้า (5.6)")
    scope_table(
        doc,
        "การเติมสินค้า (5.6)",
        "เติมสินค้าอัตโนมัติจากกฎขั้นต่ำ-สูงสุด ตามรอบเวลาที่กำหนด และเปิดใบขอซื้อเมื่อคลังหลักไม่มีของ",
        "ใบโอนอัตโนมัติ, ใบขอซื้อ",
        "เมนู: สินค้าคงคลัง → การปฏิบัติการ → การเติมสินค้า  |  ผู้ปฏิบัติ: ระบบตามรอบ และเจ้าหน้าที่คลังรับรายการ",
        "B2 ใบขอเบิกอัตโนมัติเวลา 23:30 น. · B5 เปิดใบขอซื้อเมื่อของไม่พอ",
    )
    body(
        doc,
        "ข้อ 5.6 ไม่ต้องให้หน่วยงานคีย์ใบเบิกทุกครั้ง "
        "ระบบเติมจากคลังหลักก่อน ของไม่พอจึงเปิดใบขอซื้อเข้าชุดจัดซื้อ ของที่ซื้อมาเข้าทางบทที่ 3",
    )
    heading(doc, "6.1 รับใบโอนที่ระบบสร้างให้ (5.6)", 2)
    step(doc, 1, "ตัวอย่างกฎของคลังยา ยา [00003] ที่ PHAR/Stock มีอยู่ 1.00 ขั้นต่ำ 2.00 สูงสุด 3.00 ระบบจึงสั่งเติม 2.00 ขวด ทุกวันเวลา 23:30 น. ถ้ายอดต่ำกว่าขั้นต่ำ", "Screenshot_inv_replenish_list.png", "การเติมสินค้า ยา [00003] ที่ PHAR/Stock ต่ำกว่าขั้นต่ำ ระบบคำนวณจำนวนที่ต้องเติม")
    figure(doc, "Screenshot_inv_minmax_rule.png", "แบบฟอร์มกฎขั้นต่ำ-สูงสุดของยา [00003]")
    step(doc, 2, "เปิดใบโอนร่างที่ระบบสร้าง ตัวอย่าง WH/INT/00006 จาก WH/Stock ไป PHAR/Stock จำนวน 2.00 ขวด วันเดียวกันและเส้นทางเดิมจะไม่สร้างซ้ำ", "Screenshot_inv_auto_draft.png", "ใบ WH/INT/00006 สถานะร่าง เติมยา [00003] จำนวน 2.00 ขวด")
    step(doc, 3, "คลังรับรายการ ระบบจองล็อต L26001 จำนวน 2.00 ขวด แล้วหยิบ แพ็ค และอัปเดตปลายทางเหมือนบทที่ 5", "Screenshot_inv_auto_lot.png", "ใบพร้อมแล้ว จองล็อต L26001 จำนวน 2.00 ขวด")
    figure(doc, "Screenshot_inv_auto_done.png", "หลังตรวจสอบ ใบเติมสินค้าเสร็จสิ้น ของเข้าคลังยา")
    heading(doc, "6.2 เมื่อคลังหลักไม่มีของพอ (5.6)", 2)
    step(doc, 1, "ถ้าคลังเติมหลักไม่มีของ ระบบเปิดใบขอซื้ออัตโนมัติ ไม่จองของบนใบโอน")
    step(doc, 2, "ใบขอซื้อไปที่กลุ่มงานพัสดุ เพื่อทำ e-GP และใบสั่งซื้อ ตามคู่มือ UM-ERP-VPK-G02")
    step(doc, 3, "เมื่อของมาส่ง ให้รับเข้าคลังตามบทที่ 2 และบทที่ 3")

    heading(doc, "บทที่ 7 การผลิตสินค้าภายใน (5.7)")
    scope_table(
        doc,
        "การผลิตสินค้าภายใน (5.7)",
        "ตั้งสูตรผลิต สั่งผลิต เบิกวัตถุดิบ ทำการผลิต แล้วรับสินค้าสำเร็จรูปเข้าคลัง",
        "ใบสั่งผลิต",
        "เมนู: การผลิต → บิลวัสดุ และ การผลิต → ใบสั่งผลิต  |  ผู้ปฏิบัติ: เภสัชกรและผู้ผลิตที่อยู่ในกลุ่มการผลิต",
        "E1 สูตรผลิต · E2–E4 เปิดใบ ยืนยัน และบันทึกล็อต · E5–E6 คำสั่งงานและผลิตทั้งหมด",
    )
    body(
        doc,
        "เมนูการผลิตขึ้นเมื่อผู้ใช้อยู่ในกลุ่มการผลิต "
        "วัตถุดิบต้องรับเข้าคลังมาก่อนตามบทที่ 3 ยาที่ผลิตแล้วเบิก โอน และตัดจ่ายต่อได้เหมือนสินค้าอื่น",
    )
    heading(doc, "7.1 ตรวจสูตรผลิตก่อนเปิดใบ (5.7)", 2)
    step(doc, 1, "เปิด การผลิต → สินค้า → บิลวัสดุ ตัวอย่างสูตร BOM-PARA500-TAB-B100K-V1 ผลิตยาพาราเซตามอล 500 มก. จำนวน 100,000.00 เม็ด", "Screenshot_inv_mrp_bom.png", "สูตร BOM-PARA500-TAB-B100K-V1 ผลิตยาพาราเซตามอล 100,000.00 เม็ด")
    step(doc, 2, "เปิดแท็บการปฏิบัติการ ตรวจ 6 ห้องผลิต รวม 870 นาที ตั้งแต่ชั่งวัตถุดิบจนถึงตรวจคุณภาพและปล่อยผ่านรุ่น", "Screenshot_inv_mrp_ops.png", "ลำดับห้องผลิตในสูตร ตั้งแต่ห้องชั่งจนถึงห้องควบคุมคุณภาพ")
    heading(doc, "7.2 เปิดใบสั่งผลิตและจองวัตถุดิบ (5.7)", 2)
    step(doc, 1, "เปิด การผลิต → ใบสั่งผลิต → ใหม่ เลือกยาพาราเซตามอล ระบบใส่สูตรและจำนวน 100,000.00 ให้เอง", "Screenshot_inv_mrp_draft.png", "ใบสั่งผลิตใหม่ของคลังยา ตำแหน่ง PHAR/Stock")
    step(doc, 2, "รอบนี้ผลิต 1,000.00 เม็ด จึงแก้ปริมาณ เลือกประเภทคลังยา: Manufacturing ตำแหน่งวัตถุดิบและยาสำเร็จรูปเป็น PHAR/Stock ระบบคำนวณ Paracetamol API เป็น 0.50 กก.", "Screenshot_inv_mrp_comp.png", "วัตถุดิบที่ระบบคำนวณสำหรับผลิต 1,000.00 เม็ด")
    step(doc, 3, "กดยืนยัน ได้เลข PHAR/MO/00001 จองวัตถุดิบ และเปิดคำสั่งงาน ถ้าวัตถุดิบไม่ครบจะยืนยันเต็มจำนวนไม่ได้")
    step(doc, 4, "ใส่ล็อต FG-PARA-261002 แล้วบันทึก ต้องมีล็อตก่อนกดผลิตทั้งหมด", "Screenshot_inv_mrp_lot.png", "ใบ PHAR/MO/00001 หลังยืนยัน บันทึกล็อต FG-PARA-261002")
    heading(doc, "7.3 ผลิตและรับยาเข้าคลัง (5.7)", 2)
    step(doc, 1, "เปิดแท็บคำสั่งงานของ PHAR/MO/00001 จะเห็น 6 ขั้นสถานะรอทำ", "Screenshot_inv_mrp_wo.png", "คำสั่งงานของใบ PHAR/MO/00001 รอทำ และวัตถุดิบพร้อม")
    step(doc, 2, "กดผลิตทั้งหมด ระบบตัดวัตถุดิบ รับยา 1,000.00 เม็ด ล็อต FG-PARA-261002 เข้า PHAR/Stock และปิดคำสั่งงาน", "Screenshot_inv_mrp_done.png", "หลังผลิตทั้งหมด ได้ยา 1,000.00 เม็ด ล็อต FG-PARA-261002")

    heading(doc, "บทที่ 8 รับของยืมด่วน (5.8)")
    scope_table(
        doc,
        "รับของยืมด่วน (ฉุกเฉิน) (5.8)",
        "รับพัสดุยืมจากผู้ขายมาก่อน แล้วหักล้างเมื่อรับตามใบสั่งซื้อจริง",
        "ใบยืมพัสดุจากผู้ขาย (Vendor Loan)",
        "เมนู: สินค้าคงคลัง → ยืมของจากผู้ขาย  |  ผู้ปฏิบัติ: เจ้าหน้าที่คลัง และจัดซื้อที่เปิดใบขอซื้อตามหลัง",
        "A8 ยืมของจากผู้ขาย",
    )
    body(doc, "ใช้เมื่อต้องได้ของก่อนที่ใบขอซื้อและ e-GP จะเสร็จ ของที่ยืมถูกตัดใช้ก่อน ของตามใบสั่งซื้อจริงมาหักล้างทีหลัง")
    heading(doc, "8.1 รับของยืมและเปิดขอซื้อตามหลัง (5.8)", 2)
    step(doc, 1, "เปิด ยืมของจากผู้ขาย แล้วสร้างรายการใหม่ ตัวอย่างผู้ขาย AmRhine Medical Company Limited คลังกลาง คลังยืม WH/คลังยืมผู้ขาย ยา [00002] MILK OF MAGNESIA 240 ML จำนวน 1.00 ขวด ล็อต LoT0001 ต้นทุนที่จะซื้อภายหลัง 563.00 บาท ได้เลข VL/2026/0004 สถานะร่าง", "Screenshot_inv_loan_form.png", "ใบยืม VL/2026/0004 ยา [00002] จำนวน 1.00 ขวด ต้นทุน 563.00 บาท")
    step(doc, 2, "กดรับของ ระบบสร้างใบรับเข้าคลังยืม สถานะเป็นรับของแล้ว ก่อนรับ ของที่คลังปกติไม่ถูกนับเพิ่ม", "Screenshot_inv_loan_received.png", "ใบยืมสถานะรับของแล้ว ของเข้าคลังยืมผู้ขาย")
    step(doc, 3, "เปิดใบขอซื้อตามหลังจากใบยืม สถานะไปที่จัดซื้อ จากนั้นเดิน e-GP ตามคู่มือกลุ่มงานพัสดุ", "Screenshot_inv_loan_pr.png", "ใบขอซื้อที่เปิดตามหลังจากใบยืม VL/2026/0004")
    step(doc, 4, "เมื่อรับของตามใบสั่งซื้อจริงเข้าคลังยืมเดียวกัน ระบบหักยอดยืมจนครบ สถานะเป็นเคลียร์ครบ", "Screenshot_inv_loan_cleared.png", "ใบยืมสถานะเคลียร์ครบ หลังรับของที่ซื้อตามหลังมาหักล้าง")

    heading(doc, "บทที่ 9 การจัดการข้อมูลสินค้าและคลัง (5.9)")
    scope_table(
        doc,
        "การจัดการข้อมูลสินค้าและคลัง (5.9)",
        "สร้างและปรับปรุงข้อมูลวัสดุและโครงสร้างคลัง ที่ทุกสายงานใช้ร่วมกัน",
        "ข้อมูลสินค้า, ข้อมูลคลังและตำแหน่ง",
        "เมนู: สินค้าคงคลัง → คลังและตำแหน่ง และข้อมูลสินค้า  |  ผู้ปฏิบัติ: ผู้ดูแลข้อมูลคลัง",
        "ข้อมูลหลักที่สาย A–E อ้างอิง ทั้งกฎขั้นต่ำ-สูงสุดและกฎจัดเก็บ",
    )
    body(
        doc,
        "ข้อ 5.9 ไม่ใช่ใบรับหรือใบเบิก ถ้าไม่มีรหัสสินค้า หน่วยนับ หรือการติดตามล็อต "
        "จะรับของ เบิก หรือให้ HIS อ้างรหัสไม่ได้ "
        "การขึ้นทะเบียนบัตรสินทรัพย์อยู่ที่กลุ่มงานทรัพย์สินข้อ 7.1 ไม่ได้ทำซ้ำในใบรับคลัง",
    )
    heading(doc, "9.1 ดูและปรับโครงสร้างคลัง (5.9)", 2)
    step(doc, 1, "เปิด สินค้าคงคลัง → คลังและตำแหน่ง ตัวอย่างคลังใหม่ชื่อ คลังตัวอย่างคู่มือ รหัส EX เติมสต็อกจากคลังยา", "Screenshot_inv_wh_new.png", "คลังตัวอย่างคู่มือ รหัส EX")
    step(doc, 2, "สร้างจุดเก็บใต้คลัง ตัวอย่างชั้น A1 ได้ชื่อเต็ม EX/Stock/A1 กฎจัดเก็บของกลุ่มสินค้าใช้ตอนจัดเก็บในบทที่ 4", "Screenshot_inv_loc_new.png", "ตำแหน่ง EX/Stock/A1 ของคลังตัวอย่าง")
    step(doc, 3, "ตรวจกฎขั้นต่ำ-สูงสุดของตำแหน่ง ตัวอย่างยา [00003] ที่ PHAR/Stock ขั้นต่ำ 2.00 สูงสุด 3.00 ใช้ตอนเติมสินค้าในบทที่ 6", "Screenshot_inv_minmax_rule.png", "กฎขั้นต่ำ-สูงสุดที่ใช้ให้ระบบสร้างใบเติมสินค้า")
    heading(doc, "9.2 ตรวจข้อมูลสินค้าก่อนเปิดใช้ (5.9)", 2)
    step(doc, 1, "เปิดข้อมูลสินค้า ตัวอย่างสร้างสำลีแผ่น 2x2 นิ้ว อ้างอิง DEMO-COTTON-2X2 ตรวจรหัส ชื่อ หน่วยนับ และการติดตามล็อต", "Screenshot_inv_product_new.png", "ข้อมูลสินค้าตัวอย่าง สำลีแผ่น 2x2 นิ้ว")
    step(doc, 2, "ยา [00003] ติดตามตามล็อต จึงรับเข้าและตัดจ่ายโดยระบุล็อต ถ้า HIS ไม่ส่งล็อต ระบบตัดล็อตที่หมดอายุก่อน")
    step(doc, 3, "เปิดหน้าสินค้าแล้วกดที่มีอยู่ เพื่อดูยอดหลังรับ WH/IN/00004 ตัวอย่างคือ 4.00 ขวดที่ WH/Stock ล็อต L26001", "Screenshot_inv_onhand.png", "ยอดคงเหลือของยา [00003] หลังรับเข้าคลัง")

    heading(doc, "บทที่ 10 การรับส่งข้อมูลกับระบบ HIS (5.10)")
    scope_table(
        doc,
        "การรับส่งข้อมูลกับระบบ HIS (5.10)",
        "รับคำขอเบิกและข้อมูลตัดใช้จาก HIS ตรวจชุดให้ผ่าน แล้วให้เภสัชกรกด Post จึงตัดหรือโอนสต็อก",
        "คิว HIS เบิกเติมคลัง, คิว HIS ตัดจ่ายสินค้า",
        "เมนู: สินค้าคงคลัง → การปฏิบัติการ → HIS เบิกเติมคลัง และ HIS ตัดจ่ายสินค้า  |  ผู้ปฏิบัติ: เจ้าหน้าที่คลังตรวจชุด และเภสัชกรกด Post",
        "B3 เบิกเติมคลัง · D2–D5 ตัดจ่ายและ Reversal · W5 รับชุด · W6 ส่งสถานะกลับ HIS",
    )
    body(
        doc,
        "ผังข้อ 5.10 ครอบคลุมสี่เรื่อง คือให้รหัสสินค้าที่ HIS อ้างได้ตรงกับข้อ 5.9 "
        "รับคำขอเบิกแล้วอัปเดตเมื่อรับของ "
        "รับการตัดใช้จากการให้บริการ "
        "และอัปเดตยอดเมื่อเติมของตามบทที่ 6 "
        "ชุดที่ยังเป็น Draft ยังไม่ตัดสต็อก",
    )
    heading(doc, "10.1 รับคำขอเบิกเติมคลัง (5.10)", 2)
    step(doc, 1, "เปิด HIS เบิกเติมคลัง ตัวอย่างชุด HIS/2026/00298 วันที่ 2 ตุลาคม 2569 รหัสภายนอก HIS-REQ-DEMO-OPD-00003", "Screenshot_inv_his_req.png", "ชุดเบิกเติมคลัง HIS/2026/00298 ของยา [00003]")
    step(doc, 2, "กด Validate ตรวจยา [00003] จำนวน 1.00 ขวด และยอดรวม ผ่านแล้วสถานะเป็น Ready ไม่ผ่านเป็น Error")
    step(doc, 3, "ถ้าเป็น Error ให้อ่านข้อความ แก้ข้อมูล แล้วกด Validate อีกครั้ง")
    step(doc, 4, "เภสัชกรกด Post ได้ใบโอน PHAR/INT/00005 จ่ายล็อต L26001 จำนวน 1.00 ขวดจาก PHAR/Stock/G ชุดเป็น Posted เมื่อโอนครบ", "Screenshot_inv_his_req_posted.png", "ชุด HIS เบิกเติมคลังสถานะ Posted")
    figure(doc, "Screenshot_inv_his_req_pick.png", "ใบ PHAR/INT/00005 เสร็จสิ้น จ่ายล็อต L26001 จำนวน 1.00 ขวด")
    heading(doc, "10.2 รับชุดตัดจ่าย (5.10)", 2)
    step(doc, 1, "เปิด HIS ตัดจ่ายสินค้า ตัวอย่างชุด HIS/2026/00222 วันที่ 25 สิงหาคม 2569 รวม 26 หน่วย", "Screenshot_inv_his_issue.png", "ชุดตัดจ่าย HIS/2026/00222")
    step(doc, 2, "กด Validate ตรวจรหัสสินค้า จำนวน ล็อต คลัง และยอดรวมให้ตรงยอดควบคุมของชุด")
    step(doc, 3, "เภสัชกรกด Post ระบบสร้างใบตัดจ่ายและตัดล็อตตามที่ HIS ส่ง ถ้าไม่ระบุล็อตจะตัดล็อตที่หมดอายุก่อน", "Screenshot_inv_hisout.png", "ใบตัดจ่ายที่สร้างจากชุด HIS หลังกด Post")
    figure(doc, "Screenshot_inv_hisout_lot.png", "ล็อตที่ถูกตัดในใบจ่ายจาก HIS")
    heading(doc, "10.3 ยกเลิกชุดที่ Post แล้ว (5.10)", 2)
    step(doc, 1, "อย่ายกเลิกบนใบที่เสร็จแล้วโดยตรง ชุดที่ Posted ต้องมีชุดยกเลิกจาก HIS ที่อ้างเลขชุดเดิม")
    step(doc, 2, "เมื่อชุดยกเลิกถูก Post ระบบสร้างใบรับคืนของใบตัดจ่ายเดิมและตรวจให้ สต็อกจึงกลับเข้าคลัง")
    callout(
        doc,
        "ใครกด Post ได้ (5.10)",
        "ผู้เปิดคิวอยู่กลุ่ม HIS Interface ผู้กด Post ต้องเป็นเภสัชกร ถ้าชุดค้างที่ Ready แปลว่ายังไม่มีเภสัชกรกด Post สต็อกจึงยังไม่ขยับ",
    )

    heading(doc, "บทที่ 11 นับสต็อกและพิมพ์บัญชีคุมวัสดุ")
    scope_table(
        doc,
        "รายงานจากความเคลื่อนไหวของข้อ 5.1–5.10",
        "พิมพ์บัญชีคุมวัสดุจากใบที่ตรวจสอบแล้ว และปรับยอดเมื่อนับของจริงแล้วไม่ตรงระบบ",
        "บัญชีคุมวัสดุ, ใบนับสต็อก",
        "เมนู: สินค้าคงคลัง → การรายงาน → บัญชีคุมวัสดุ และเมนูนับสต็อก  |  ผู้ปฏิบัติ: เจ้าหน้าที่คลัง",
        "W8 บัญชีคุมวัสดุ · D6 ปรับยอดจากการนับ",
    )
    body(
        doc,
        "บทนี้ไม่มีเลขข้อใหม่บนผังภาพรวม เป็นรายงานของงานคลังทั้งคอลัมน์ "
        "ใบที่ยังเป็นร่างหรือยังไม่กดตรวจสอบจะไม่ไปเพิ่มหรือลดในบัญชีคุม",
    )
    heading(doc, "11.1 พิมพ์บัญชีคุมวัสดุ", 2)
    step(doc, 1, "เปิด สินค้าคงคลัง → การรายงาน → บัญชีคุมวัสดุ")
    step(doc, 2, "เลือกช่วงวันที่ครอบคลุมใบ WH/IN/00004 และยา [00003] แล้วพิมพ์รายงาน แถวรับต้องเป็น 4.00 ขวดที่เข้า WH/Stock")
    step(doc, 3, "การรับจาก P00003 เพิ่ม 4.00 ขวด การโอน 1.00 ขวดไป PHAR/Stock ไม่เพิ่มยอดรวมโรงพยาบาล การตัดจ่าย HIS ลดยอดต้นทาง ดูยอดตำแหน่งได้จากปุ่มที่มีอยู่", "Screenshot_inv_onhand.png", "ยอดคงเหลือรายล็อตที่ใช้เทียบกับบัญชีคุมวัสดุ")
    heading(doc, "11.2 ปรับยอดเมื่อนับแล้วไม่ตรง", 2)
    step(doc, 1, "เปิดใบนับที่ตำแหน่งที่จะนับ ตัวอย่างนับสำลีแผ่น 2x2 นิ้ว อ้างอิง DEMO-COTTON-2X2 ที่ชั้น EX/Stock/A1", "Screenshot_inv_adj_count.png", "ใบนับสำลีแผ่นตัวอย่างที่ชั้น EX/Stock/A1")
    step(doc, 2, "ใส่จำนวนที่นับได้ ถ้ายอดตรงกับระบบไม่ต้องปรับ")
    step(doc, 3, "ถ้ายอดต่าง ให้ระบุเหตุผล เช่น นับสำลีแผ่นตัวอย่าง แล้วกดอัปเดตปริมาณ", "Screenshot_inv_adj_reason.png", "ใส่เหตุผลการปรับ แล้วยืนยันอัปเดตปริมาณ")
    figure(doc, "Screenshot_inv_adj_done.png", "หลังอัปเดตปริมาณ ยอดสำลีแผ่นตัวอย่างตรงตามที่นับ")

    heading(doc, "ภาคผนวก ก  Workflow และ Dataflow งานคลังสินค้า")
    body(
        doc,
        "ภาคผนวกนี้ย่อจากไฟล์ Workflow-Dataflow-งานคลังสินค้า.pptx "
        "งานคลังแบ่งห้าสาย A ถึง E และมีจุดเชื่อม W1 ถึง W8 กับกลุ่มงานอื่น "
        "ลำดับรับของใช้ตามบทที่ 3 คือ QC ผ่าน แล้วกรรมการตรวจรับ แล้วจึงรับของเข้าคลัง",
    )
    heading(doc, "ก.1 สายงาน", 2)
    figure(doc, "dataflow/df_overview.png", "ผังภาพรวมห้าสายงานคลัง สายรับของเรียง QC ผ่าน กรรมการตรวจรับ แล้วรับของเข้าคลัง")
    make_table(
        doc,
        ["สาย", "ชื่องาน", "ลำดับในสาย"],
        [
            [
                code,
                name,
                "ของมาส่ง → QC ผ่าน → กรรมการตรวจรับ → รับของเข้าคลัง"
                if code == "A"
                else flow,
            ]
            for code, name, flow in PHASES
        ],
        [1.6, 3.6, 11.2],
    )
    by_code = {row["code"]: row for row in FUNCTIONS}
    phase_order = {
        "A": ["A1", "A2", "A3", "A4", "A6", "A5", "A7", "A8"],
    }
    text_fix = {
        "A4": {
            "outputs": [
                "ผ่าน → ส่งให้กรรมการตรวจรับ",
                "ไม่ผ่าน → ไปกรรมการตรวจรับและรับเข้าคลังไม่ได้",
            ],
        },
        "A5": {
            "process": [
                "ทำในขั้นรับของเข้าคลัง หลังกรรมการตรวจรับยืนยันแล้ว",
                "ใส่ล็อตและวันหมดอายุ ระบบคำนวณอายุคงเหลือ ยังไม่กดตรวจสอบ",
            ],
            "outputs": ["ใบรับมีล็อตและวันหมดอายุครบ พร้อมกดตรวจสอบ"],
        },
        "A6": {
            "process": [
                "พัสดุสร้างใบตรวจรับจากใบสั่งซื้อหลัง QC ผ่าน",
                "กรรมการบันทึกผล ครบถ้วน บางส่วน หรือไม่ผ่าน",
                "กดตรวจรับ แล้วลงวันที่ตรวจรับ",
            ],
            "outputs": [
                "ใบตรวจรับสถานะยืนยันตรวจรับ",
                "ผลไม่ผ่าน คลังรับของเข้าคลังไม่ได้",
            ],
        },
    }
    diagrams = {
        "A": [("dataflow/df_receive.png", "ผังการรับสินค้า ลำดับ QC ผ่าน กรรมการตรวจรับ บันทึกล็อต แล้วรับของเข้าคลัง")],
        "B": [("dataflow/df_request.png", "ผังการขอเบิกสินค้า จากหน่วยงาน ระบบ Min-Max และ HIS")],
        "C": [("dataflow/df_transfer.png", "ผังการโอนสินค้า ตั้งแต่ใบหยิบ แพ็คลงกล่อง จนของถึงปลายทาง")],
        "D": [
            ("dataflow/df_issue_his.png", "ผังการตัดจ่ายจาก HIS จนถึงการคืนสต็อกด้วย Reversal"),
            ("dataflow/df_issue_out.png", "ผังการจ่ายออกให้หน่วยงาน และการปรับยอดจากการนับสต็อก"),
        ],
        "E": [("dataflow/df_produce.png", "ผังการผลิตยา ตั้งแต่สูตรผลิตจนยาสำเร็จรูปเข้าคลัง")],
    }
    section_no = 1
    for phase, name, _flow in PHASES:
        section_no += 1
        heading(doc, f"ก.{section_no} สาย {phase} {name}", 2)
        for image, caption in diagrams[phase]:
            figure(doc, image, caption)
        codes = phase_order.get(phase, [row["code"] for row in FUNCTIONS if row["phase"] == phase])
        rows = []
        for code in codes:
            row = by_code[code]
            fix = text_fix.get(code, {})
            rows.append(
                [
                    code,
                    f"{row['name']} ({row['actor']})",
                    " · ".join(fix.get("inputs", row["inputs"])),
                    " · ".join(fix.get("process", row["process"])),
                    " · ".join(fix.get("outputs", row["outputs"])),
                ]
            )
        make_table(
            doc,
            ["รหัส", "งาน", "ข้อมูลเข้า", "การทำงาน", "ผลที่ได้"],
            rows,
            [1.3, 3.3, 4.0, 4.0, 3.8],
        )
    heading(doc, "ก.7 จุดเชื่อมกับกลุ่มงานอื่น", 2)
    body(doc, "จุดเชื่อม W1 ถึง W8 บอกว่าคลังรับงานจากกลุ่มใด และส่งผลต่อไปที่ใด")
    make_table(
        doc,
        ["รหัส", "จาก → ไป", "เกิดเมื่อ", "ผลที่ได้"],
        [
            [
                row["code"],
                f"{row['frm']} → {row['to']}",
                row["trigger"],
                " · ".join(row["outputs"]),
            ]
            for row in INTEGRATION
        ],
        [1.4, 4.2, 4.2, 6.6],
    )
    body(doc, "งานที่คลังไม่ทำแทนกลุ่มงานอื่น")
    bullets(
        doc,
        [
            "ไม่ออกใบขอซื้อ e-GP หรือใบสั่งซื้อ งานนั้นอยู่คู่มือกลุ่มงานพัสดุข้อ 3.1 ถึง 3.3",
            "ไม่สร้างและไม่ลงนามใบตรวจรับ งานนั้นอยู่คู่มือกลุ่มงานพัสดุบทที่ 5 และคณะกรรมการข้อ 4.2 คลังรับของเข้าคลังหลังใบตรวจรับยืนยันแล้ว",
            "ไม่ตั้งเจ้าหนี้ งานนั้นอยู่เจ้าหนี้ข้อ 8.1 หลังมีใบรับและใบตรวจรับครบ",
            "ไม่แก้ข้อมูลใน HIS โดยตรง คลังรับชุดที่ส่งมา ตรวจ แล้วให้เภสัชกรกด Post",
            "กลุ่มงานซ่อมบำรุงเบิกอะไหล่ตามข้อ 6.2 ด้วยใบเบิกจากคลัง วิธีรับรายการเหมือนบทที่ 5",
        ],
    )

    heading(doc, "ภาคผนวก ข  คำศัพท์ในระบบ")
    make_table(
        doc,
        ["คำในระบบ", "พูดกับผู้ใช้", "หมายเหตุ"],
        [
            ["ใบรับ WH/IN", "ใบรับสินค้าจากผู้ขาย", "สร้างเองเมื่อยืนยันใบสั่งซื้อ ของเข้าเมื่อกดตรวจสอบ"],
            ["QC", "ตรวจคุณภาพขาเข้า", "ไม่ผ่านจะรับเข้าคลังไม่ได้"],
            ["ใบตรวจรับ WA", "ใบตรวจรับพัสดุของกรรมการ", "ทำหลัง QC ผ่าน และก่อนคลังกดรับของเข้าคลัง"],
            ["ขอโอนสินค้า", "ใบเบิกพัสดุของหน่วยงาน", "ผังข้อ 2.3 ต้นทางเป็นคลังกลาง"],
            ["ตั้งเป็นสิ่งที่ต้องทำ", "คลังรับรายการ", "ระบบจึงเปิดใบหยิบ ใบแพ็ค และใบปลายทาง"],
            ["FEFO", "จ่ายล็อตที่หมดอายุก่อน", "ใช้ทั้งตอนโอน จ่ายออก และตัดจ่ายที่ HIS ไม่ระบุล็อต"],
            ["Post", "เภสัชกรยืนยันชุด HIS", "ก่อนกด สต็อกยังไม่ขยับ"],
            ["Reversal", "ชุดยกเลิกการตัดจ่าย", "ใช้เมื่อชุดถูก Post ไปแล้ว"],
        ],
        [3.2, 5.6, 7.6],
    )
    end = doc.add_paragraph()
    end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    end.paragraph_format.space_before = Pt(12)
    add_text(end, "— จบคู่มือการใช้งาน : กลุ่มงานคลัง (5.1 – 5.10) —", 12, True, GREEN)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(OUT)


if __name__ == "__main__":
    build()
