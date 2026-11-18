#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""สร้างเอกสารออกแบบ Interface HIS → ERP (Odoo 18) เป็นไฟล์ Word

ครอบคลุมเมนู/คิว:
  1. HIS Revenue Queue
  2. HIS รับมัดจำค่ารักษา
  3. HIS Entitlements
  4. HIS ตัดจ่ายสินค้า
  5. HIS เบิกเติมสินค้า

รัน: python3 docs/build_his_interface_design_docx.py
ผลลัพธ์: docs/เอกสารออกแบบ-HIS-Interface-ERP-VPK.docx
"""
from __future__ import annotations

import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

DOCS = Path(__file__).resolve().parent
OUT = DOCS / "เอกสารออกแบบ-HIS-Interface-ERP-VPK.docx"
FONT = "Prompt"
FONT_DIR = DOCS / "fonts" / "Prompt"

NAVY = RGBColor(0x0B, 0x3D, 0x5C)
TEAL = RGBColor(0x0E, 0x6B, 0x6B)
HEADER_BG = "0B3D5C"
ALT_ROW = "F4F8FA"
CODE_BG = "F3F4F6"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
ODTTF_CT = "application/vnd.openxmlformats-officedocument.obfuscatedFont"


def _obfuscate_font(ttf_bytes, guid):
    key = guid.bytes_le
    out = bytearray(ttf_bytes)
    for i in range(min(32, len(out))):
        out[i] ^= key[i % 16]
    return bytes(out)


def embed_prompt_fonts(docx_path):
    faces = (
        ("embedRegular", FONT_DIR / "Prompt-Regular.ttf", "promptRegular.odttf"),
        ("embedBold", FONT_DIR / "Prompt-Bold.ttf", "promptBold.odttf"),
    )
    if not all(ttf.is_file() for _t, ttf, _n in faces):
        return

    ET.register_namespace("w", W_NS)
    ET.register_namespace("r", R_NS)
    ET.register_namespace("", CT_NS)

    with zipfile.ZipFile(docx_path, "r") as src:
        parts = {info.filename: src.read(info.filename) for info in src.infolist()}

    font_files = {}
    embed_meta = []
    for i, (tag, ttf, name) in enumerate(faces, 1):
        guid = uuid.uuid4()
        font_key = "{" + str(guid).upper() + "}"
        rid = f"rIdFont{i}"
        font_files[f"word/fonts/{name}"] = _obfuscate_font(ttf.read_bytes(), guid)
        embed_meta.append((tag, rid, font_key, name))

    font_table = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:fonts xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
        f'<w:font w:name="{FONT}">'
        f'<w:charset w:val="00"/>'
        f'<w:family w:val="swiss"/>'
        f'<w:pitch w:val="variable"/>'
    )
    for tag, rid, font_key, _name in embed_meta:
        font_table += f'<w:{tag} r:id="{rid}" w:fontKey="{font_key}"/>'
    font_table += "</w:font></w:fonts>"
    parts["word/fontTable.xml"] = font_table.encode("utf-8")

    rels = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">'
    )
    for _tag, rid, _key, name in embed_meta:
        rels += (
            f'<Relationship Id="{rid}" Type="{FONT_REL_TYPE}" '
            f'Target="fonts/{name}"/>'
        )
    rels += "</Relationships>"
    parts["word/_rels/fontTable.xml.rels"] = rels.encode("utf-8")

    ct_root = ET.fromstring(parts["[Content_Types].xml"])
    if not any(el.get("Extension") == "odttf" for el in ct_root.findall(f"{{{CT_NS}}}Default")):
        default = ET.SubElement(ct_root, f"{{{CT_NS}}}Default")
        default.set("Extension", "odttf")
        default.set("ContentType", ODTTF_CT)
    parts["[Content_Types].xml"] = ET.tostring(
        ct_root, encoding="utf-8", xml_declaration=True
    )

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for name, data in parts.items():
            dst.writestr(name, data)
        for name, data in font_files.items():
            dst.writestr(name, data)
    Path(docx_path).write_bytes(buf.getvalue())


def shade_cell(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_run_font(run, size=16, bold=False, italic=False, color=None, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), font)


def add_page_number(paragraph):
    run = paragraph.add_run()
    set_run_font(run, size=12, color=NAVY)
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


class SpecDoc:
    def __init__(self):
        self.doc = Document()
        self._setup_page()
        self._setup_styles()
        self.sec_no = 0

    def _setup_page(self):
        section = self.doc.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run("โรงพยาบาลวชิระภูเก็ต  ·  HIS → ERP Interface Design")
        set_run_font(r, size=11, color=NAVY)
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("VPK-HIS-IF-DD-001  ·  ร่าง  ·  หน้า ")
        set_run_font(r, size=11, color=NAVY)
        add_page_number(fp)

    def _setup_styles(self):
        styles_el = self.doc.styles.element
        doc_defaults = styles_el.find(qn("w:docDefaults"))
        if doc_defaults is None:
            doc_defaults = OxmlElement("w:docDefaults")
            styles_el.insert(0, doc_defaults)
        rpr_default = doc_defaults.find(qn("w:rPrDefault"))
        if rpr_default is None:
            rpr_default = OxmlElement("w:rPrDefault")
            doc_defaults.append(rpr_default)
        rPr = rpr_default.find(qn("w:rPr"))
        if rPr is None:
            rPr = OxmlElement("w:rPr")
            rpr_default.append(rPr)
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = OxmlElement("w:rFonts")
            rPr.insert(0, rFonts)
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rFonts.set(qn(attr), FONT)
        styles = self.doc.styles
        for name, size, bold, space_before, space_after in (
            ("Normal", 15, False, 0, 6),
            ("Heading 1", 20, True, 16, 8),
            ("Heading 2", 17, True, 12, 6),
            ("Heading 3", 15, True, 10, 4),
        ):
            st = styles[name]
            st.font.name = FONT
            st.font.size = Pt(size)
            st.font.bold = bold
            st.font.color.rgb = NAVY if name != "Normal" else RGBColor(0x22, 0x22, 0x22)
            rPr = st.element.get_or_add_rPr()
            rFonts = rPr.get_or_add_rFonts()
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                rFonts.set(qn(attr), FONT)
            pf = st.paragraph_format
            pf.space_before = Pt(space_before)
            pf.space_after = Pt(space_after)
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE

    def p(self, text, size=15, bold=False, align="left", space_after=6, color=None):
        para = self.doc.add_paragraph()
        if align == "center":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "right":
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif align == "justify":
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.space_after = Pt(space_after)
        para.paragraph_format.space_before = Pt(0)
        run = para.add_run(text)
        set_run_font(run, size=size, bold=bold, color=color)
        return para

    def h1(self, title):
        self.sec_no += 1
        self._h2_no = 0
        para = self.doc.add_heading(f"{self.sec_no}.  {title}", level=1)
        for run in para.runs:
            set_run_font(run, size=20, bold=True, color=NAVY)
        return self.sec_no

    def h2(self, title):
        self._h2_no = getattr(self, "_h2_no", 0) + 1
        self._h3_no = 0
        para = self.doc.add_heading(f"{self.sec_no}.{self._h2_no}  {title}", level=2)
        for run in para.runs:
            set_run_font(run, size=17, bold=True, color=TEAL)
        return f"{self.sec_no}.{self._h2_no}"

    def h3(self, title):
        self._h3_no = getattr(self, "_h3_no", 0) + 1
        para = self.doc.add_heading(
            f"{self.sec_no}.{self._h2_no}.{self._h3_no}  {title}", level=3
        )
        for run in para.runs:
            set_run_font(run, size=15, bold=True, color=NAVY)
        return f"{self.sec_no}.{self._h2_no}.{self._h3_no}"

    def bullets(self, items, numbered=False):
        for i, item in enumerate(items, 1):
            para = self.doc.add_paragraph()
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.left_indent = Cm(0.75)
            prefix = f"{i}.  " if numbered else "•  "
            run = para.add_run(prefix + item)
            set_run_font(run, size=15)

    def table(self, headers, rows, col_widths=None):
        tbl = self.doc.add_table(rows=1 + len(rows), cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = True
        for i, h in enumerate(headers):
            cell = tbl.rows[0].cells[i]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(h)
            set_run_font(run, size=13, bold=True, color=RGBColor(255, 255, 255))
            shade_cell(cell, HEADER_BG)
        for r_i, row in enumerate(rows):
            for c_i, val in enumerate(row):
                cell = tbl.rows[r_i + 1].cells[c_i]
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(str(val) if val is not None else "")
                set_run_font(run, size=13)
                if r_i % 2 == 1:
                    shade_cell(cell, ALT_ROW)
        if col_widths:
            for row in tbl.rows:
                for i, w in enumerate(col_widths):
                    row.cells[i].width = Cm(w)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(6)
        return tbl

    def code(self, text):
        para = self.doc.add_paragraph()
        para.paragraph_format.space_before = Pt(4)
        para.paragraph_format.space_after = Pt(8)
        para.paragraph_format.left_indent = Cm(0.2)
        run = para.add_run(text.strip("\n"))
        set_run_font(run, size=10, font="Consolas")
        pPr = para._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), CODE_BG)
        shd.set(qn("w:val"), "clear")
        pPr.append(shd)
        return para

    def note(self, text, label="หมายเหตุ"):
        para = self.doc.add_paragraph()
        para.paragraph_format.space_after = Pt(8)
        r1 = para.add_run(f"{label}: ")
        set_run_font(r1, size=15, bold=True, color=TEAL)
        r2 = para.add_run(text)
        set_run_font(r2, size=15, italic=True)

    def page_break(self):
        from docx.enum.text import WD_BREAK

        para = self.doc.add_paragraph()
        run = para.add_run()
        run.add_break(WD_BREAK.PAGE)

    def save(self, path):
        self.doc.save(str(path))
        embed_prompt_fonts(path)


def build():
    d = SpecDoc()

    # ----- Cover -----
    d.p("โรงพยาบาลวชิระภูเก็ต", size=20, bold=True, align="center", space_after=4, color=NAVY)
    d.p("ระบบบัญชีและคลัง ERP (Odoo 18)", size=15, align="center", space_after=18, color=TEAL)
    d.p("เอกสารออกแบบ Interface", size=26, bold=True, align="center", space_after=4, color=NAVY)
    d.p("ระบบ HIS → ระบบ ERP", size=22, bold=True, align="center", space_after=6, color=NAVY)
    d.p("HIS Interface Design Document", size=16, align="center", space_after=20, color=TEAL)
    d.p(
        "ครอบคลุม HIS Revenue Queue · รับมัดจำค่ารักษา · Entitlements · ตัดจ่ายสินค้า · เบิกเติมสินค้า",
        size=14,
        align="center",
        space_after=24,
    )

    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["รหัสเอกสาร", "VPK-HIS-IF-DD-001"],
            ["เวอร์ชัน", "1.0 (ร่าง)"],
            ["วันที่", "17 พฤศจิกายน 2569"],
            ["สถานะ", "Draft — สำหรับทบทวนร่วม HIS / บัญชี / คลัง / IT"],
            ["ระบบต้นทาง", "Hospital Information System (Front HIS)"],
            ["ระบบปลายทาง", "Odoo 18 ERP — โรงพยาบาลวชิระภูเก็ต"],
            ["โมดูล", "vpk_his_api"],
            ["ทิศทางข้อมูล", "HIS ส่งเข้า ERP (Inbound) + Lookup / สอบถามสถานะชุดกลับ HIS"],
            ["ผู้ใช้เอกสาร", "ทีม HIS · บัญชีลูกหนี้ · เภสัช/คลัง · IT"],
        ],
        col_widths=[5.0, 12.0],
    )

    # ----- 1 Overview -----
    d.h1("ภาพรวมและหลักการออกแบบ")
    d.h2("วัตถุประสงค์")
    d.p(
        "เอกสารนี้กำหนดการออกแบบ Interface ที่ระบบ HIS ส่งข้อมูลเข้าสู่ ERP เพื่อลงบัญชีรายได้ "
        "รับมัดจำ ตัดสต็อกยา/เวชภัณฑ์ และเบิกเติมคลัง โดยใช้คิว staging ให้เจ้าหน้าที่ตรวจสอบก่อน Post "
        "ไม่ลงบัญชีหรือตัดสต็อกอัตโนมัติทันทีที่รับ API",
        align="justify",
    )

    d.h2("ขอบเขต Interface (5 รายการ)")
    d.table(
        ["ลำดับ", "ชื่อใน ERP (เมนู/คิว)", "ประเภท", "Endpoint หลัก"],
        [
            ["1", "HIS Revenue Queue", "Inbound Queue", "POST /vpk/api/v1/his/revenue"],
            ["2", "HIS รับมัดจำค่ารักษา", "Inbound Queue", "POST /vpk/api/v1/his/deposits"],
            ["3", "HIS Entitlements", "Master Mapping + Lookup", "GET /vpk/api/v1/his/lookups/entitlements"],
            ["4", "HIS ตัดจ่ายสินค้า", "Inbound Queue", "POST /vpk/api/v1/his/stock-issues"],
            ["5", "HIS เบิกเติมสินค้า", "Inbound Queue", "POST /vpk/api/v1/his/stock-requisitions"],
        ],
        col_widths=[1.5, 5.5, 4.5, 5.5],
    )
    d.note(
        "Entitlements ไม่ใช่คิวรับข้อมูลแบบ push จาก HIS แต่เป็นตารางแมปหลักใน ERP "
        "ที่ HIS อ่านผ่าน Lookup และใช้ตอน Post รายได้/มัดจำ"
    )

    d.h2("สถาปัตยกรรมรวม")
    d.code(
        "HIS (JSON + X-Api-Key)\n"
        "  → REST POST /vpk/api/v1/his/{revenue|deposits|stock-issues|stock-requisitions}\n"
        "  → vpk.his.api.service  (ตัด PII · idempotent staging · validate)\n"
        "  → vpk.his.batch (+ line models)   draft → ready|error → posted|cancelled\n"
        "  → Manual Post (บัญชี / เภสัชกร)\n"
        "  → account.move / account.payment / stock.picking / stock.scrap\n"
        "HIS สอบถามสถานะ: GET /vpk/api/v1/his/batches/{external_id}"
    )

    d.h2("หลักการออกแบบสำคัญ")
    d.bullets(
        [
            "Staging ก่อน Post — ไม่ auto-post เข้า GL หรือสต็อก",
            "Idempotency: คีย์ = source_system + external_id (+ company) — ส่งซ้ำก่อน Post จะแทนที่รายการ",
            "ไม่สร้าง Master อัตโนมัติ (สินค้า, Lot, สิทธิ์, คู่ค้า) — รหัสที่ไม่มีแมปทำให้ชุดเป็น error",
            "แก้ไขชุดที่ Post แล้ว: ส่งชุดใหม่ batch_type=reversal + original_external_id",
            "แยก API ตามโดเมนและกฎ PII (รายได้/มัดจำห้าม HN·VN; ตัดจ่ายคนไข้ต้องมี HN·VN)",
            "ไม่มี cron ลงบัญชีจาก HIS — การ retry เป็นหน้าที่ HIS ส่งซ้ำด้วยคีย์เดิม",
        ]
    )

    d.h2("การยืนยันตัวตนและคอนฟิก")
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["Auth Header", "X-Api-Key: <key>  หรือ  Authorization: Bearer <key>"],
            ["พารามิเตอร์คีย์", "ir.config_parameter → vpk_his_api.api_key"],
            ["เปิด/ปิด API", "vpk_his_api.enabled"],
            ["ตั้งค่า UI", "Settings → Invoicing → HIS API"],
            ["Log", "โมเดล vpk.his.api.log (pending / success / error)"],
            ["กลุ่มสิทธิ์", "User / Accountant / Pharmacist / Manager"],
        ],
        col_widths=[5.0, 12.0],
    )

    d.h2("สถานะชุดข้อมูลร่วม (vpk.his.batch)")
    d.table(
        ["สถานะ", "ความหมาย", "การดำเนินการถัดไป"],
        [
            ["draft", "รับเข้า staging แล้ว รอ/กำลัง validate", "ระบบ validate อัตโนมัติ"],
            ["ready", "ผ่านการตรวจยอดควบคุมและแมป", "บัญชีหรือเภสัชกด Post"],
            ["error", "ยอดไม่ตรง / รหัสไม่มีแมป / ข้อมูลไม่ครบ", "แก้ที่ HIS หรือ master แล้วส่งซ้ำ"],
            ["posted", "สร้างเอกสาร ERP แล้ว", "แก้ด้วย reversal เท่านั้น"],
            ["cancelled", "ยกเลิกก่อน Post", "ไม่สร้างเอกสาร"],
        ],
        col_widths=[3.0, 7.0, 7.0],
    )

    d.h2("รหัสตอบกลับ HTTP โดยสรุป")
    d.table(
        ["HTTP", "เมื่อใด"],
        [
            ["202", "รับชุดใหม่/อัปเดตชุดที่ยังไม่ Post (action: created/updated)"],
            ["200", "ส่งคีย์เดิมหลัง Post แล้ว (action: unchanged) หรือ GET สถานะชุดที่ posted"],
            ["400", "payload ไม่ถูกต้อง"],
            ["401", "API key ไม่ถูกต้องหรือไม่มี"],
            ["503", "API ปิด หรือยังไม่ตั้งค่า API key"],
        ],
        col_widths=[3.0, 14.0],
    )

    # ----- 2 Revenue -----
    d.page_break()
    d.h1("Interface 1 — HIS Revenue Queue")
    d.h2("ภาพรวม")
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["ชื่อเมนู", "บัญชี → ลูกหนี้ → HIS Revenue Queue"],
            ["วัตถุประสงค์", "รับสรุปรายได้รายวัน/รายกะ จาก HIS เข้าคิว แล้วลงบัญชีเมื่อนักบัญชี Post"],
            ["ทิศทาง", "HIS → ERP"],
            ["Endpoint", "POST /vpk/api/v1/his/revenue"],
            ["โมเดลคิว", "vpk.his.batch (batch_type=revenue) · vpk.his.sale.line · vpk.his.payment.line"],
            ["ผู้ Post", "กลุ่ม Accountant (group_his_accountant)"],
            ["เอกสาร ERP", "account.move (ใบแจ้งหนี้) · account.payment · รายการมัดจำ (ถ้ามี advance_in)"],
            ["รหัส workflow", "E2 รับสรุป · E3 Post รายได้ · E5 Reversal · E6 ใบนำส่งเงิน"],
        ],
        col_widths=[4.5, 12.5],
    )

    d.h2("ลำดับการทำงาน")
    d.bullets(
        [
            "HIS ปิดยอดรายวัน/กะ แล้ว POST สรุปยอดขาย + ยอดรับเงิน + control_totals",
            "ERP ตัด PII (HN/ชื่อ/CID) เก็บเข้าชุด staging แล้ว validate",
            "ยอดรวมตรงและแมปครบ → ready; ไม่ตรง → error",
            "นักบัญชีเปิด HIS Revenue Queue ตรวจชุด แล้วกด Post",
            "ระบบรวมยอดขายตามผู้จ่าย/สิทธิ์/ประเภทบริการ/ใบ → สร้างใบแจ้งหนี้",
            "เงินสด/โอน/บัตร → ใบรับเงินและกระทบยอด; สิทธิ์กองทุน → พักลูกหนี้ใน aging",
            "HIS ดึงสถานะด้วย GET /batches/{external_id}",
        ],
        numbered=True,
    )

    d.h2("ฟิลด์ Header ของชุด")
    d.table(
        ["ฟิลด์", "ชนิด", "บังคับ", "ความหมาย"],
        [
            ["external_id", "string", "ใช่", "รหัสชุดจาก HIS (idempotency)"],
            ["source_system", "string", "ใช่", "ชื่อระบบต้นทาง เช่น front_his"],
            ["business_date", "date", "ใช่", "วันที่ธุรกิจ YYYY-MM-DD"],
            ["shift", "string", "ไม่", "รหัสกะ เช่น 1"],
            ["currency", "string", "ไม่", "ค่าเงิน (ค่าเริ่มต้นของบริษัท)"],
            ["control_totals.sales_total", "float", "ใช่*", "ยอดควบคุมขาย"],
            ["control_totals.payments_total", "float", "ใช่*", "ยอดควบคุมรับ (รวมสิทธิ์/ar_claim)"],
            ["batch_type", "string", "ไม่", "ใส่ reversal เมื่อกลับรายการ"],
            ["original_external_id", "string", "เมื่อ reversal", "external_id ของชุดที่ Post แล้ว"],
        ],
        col_widths=[5.5, 2.0, 2.5, 7.0],
    )

    d.h2("รายการขาย (sales[])")
    d.table(
        ["ฟิลด์", "ความหมาย / ค่าที่รองรับ"],
        [
            ["line_external_id", "รหัสบรรทัดจาก HIS"],
            ["ticket_external_id", "รหัสใบ/ครั้งรับบริการ — ใช้รวมหลายสิทธิ์ในใบเดียว (ห้ามส่ง HN)"],
            ["entitlement_code", "SELF_PAY | UC | SSO | CSMBS"],
            ["service_type", "op | ip"],
            ["item_type", "service | drug | medical_supply | lab | other"],
            ["department_code", "รหัสหน่วยบริการ (ออปชัน)"],
            ["qty", "จำนวน (ออปชัน)"],
            ["amount_total", "ยอดรวมบรรทัด"],
        ],
        col_widths=[5.0, 12.0],
    )

    d.h2("รายการรับเงิน (payments[])")
    d.table(
        ["payment_method_code", "ผลใน ERP"],
        [
            ["cash / transfer / credit_card", "สร้างใบรับเงินจริง กระทบใบแจ้งหนี้"],
            ["advance_in", "รับมัดจำ — เดบิตเงิน / เครดิตหนี้สินรับล่วงหน้า (ไม่ลงรายได้)"],
            ["advance / prepaid / deposit", "ตัดมัดจำเมื่อมาใช้บริการ (สมุด HADV)"],
            ["sso / uc / csmbs / ar_claim", "ไม่ลงเงิน — พักลูกหนี้สิทธิ์หรือค้างคนไข้"],
        ],
        col_widths=[6.0, 11.0],
    )

    d.h2("ตัวอย่าง Payload สรุปรายวัน")
    d.code(
        'POST /vpk/api/v1/his/revenue\n'
        '{\n'
        '  "external_id": "HIS-REV-2026-08-22",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-08-22",\n'
        '  "shift": "1",\n'
        '  "currency": "THB",\n'
        '  "sales": [\n'
        '    {"line_external_id": "S1", "entitlement_code": "SELF_PAY",\n'
        '     "service_type": "op", "item_type": "service", "amount_total": 150000},\n'
        '    {"line_external_id": "S2", "entitlement_code": "UC",\n'
        '     "service_type": "op", "item_type": "drug", "amount_total": 82000}\n'
        '  ],\n'
        '  "payments": [\n'
        '    {"line_external_id": "P1", "payment_method_code": "cash",\n'
        '     "entitlement_code": "SELF_PAY", "amount": 150000},\n'
        '    {"line_external_id": "P2", "payment_method_code": "ar_claim",\n'
        '     "entitlement_code": "UC", "amount": 82000}\n'
        '  ],\n'
        '  "control_totals": {"sales_total": 232000, "payments_total": 232000}\n'
        '}'
    )

    d.h2("กฎธุรกิจสำคัญ")
    d.bullets(
        [
            "ห้ามส่ง HN / VN / ชื่อผู้ป่วย / CID ใน API รายได้ — ระบบตัดทิ้ง",
            "หลายสิทธิ์ในใบเดียว: ใส่ ticket_external_id ชุดเดียวกันทุกบรรทัดของใบนั้น",
            "control_totals.payments_total รวมเงินจริง + ยอดสิทธิ์ + ar_claim ให้เท่ายอดขาย",
            "สมุดใบแจ้งหนี้แนะนำรหัส HINV; เงินสด/โอน/บัตรตาม payment method map",
            "หลังกองทุนโอนเงิน: เคลียร์ลูกหนี้สิทธิ์ที่ใบแจ้งหนี้ด้วยสมุด Bank (นอก API นี้)",
        ]
    )

    d.h2("ข้อผิดพลาดและการแก้ไข")
    d.table(
        ["อาการ", "สาเหตุทั่วไป", "วิธีแก้"],
        [
            ["ชุดเป็น error", "ยอดควบคุมไม่ตรง / สิทธิ์หรือวิธีรับเงินไม่มีแมป", "แก้ payload หรือตั้ง Entitlements/Payment Methods แล้วส่งซ้ำ"],
            ["ส่งซ้ำได้ผล unchanged", "ชุด Post แล้ว", "ใช้ reversal ด้วย external_id ใหม่"],
            ["ลูกหนี้สิทธิ์ค้าง aging", "ออกแบบตามสิทธิ์กองทุน", "เคลียร์เมื่อกองทุนโอนเข้าบัญชี"],
        ],
        col_widths=[4.0, 6.5, 6.5],
    )

    # ----- 3 Deposit -----
    d.page_break()
    d.h1("Interface 2 — HIS รับมัดจำค่ารักษา")
    d.h2("ภาพรวม")
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["ชื่อเมนู", "บัญชี → ลูกหนี้ → HIS รับมัดจำค่ารักษา"],
            ["วัตถุประสงค์", "รับ/คืนเงินมัดจำค่ารักษาก่อนวันมารักษา — ไม่ลงรายได้"],
            ["ทิศทาง", "HIS → ERP"],
            ["Endpoint", "POST /vpk/api/v1/his/deposits"],
            ["โมเดลคิว", "vpk.his.batch (batch_type=deposit)"],
            ["ผู้ Post", "Accountant"],
            ["เอกสาร ERP", "account.move (รายการบัญชีมัดจำ) ผ่าน _create_advance_receipt"],
            ["บัญชีหนี้สิน", "2103010103.101 (เงินรับล่วงหน้า)"],
            ["รหัส workflow", "E4 มัดจำผู้ป่วย"],
        ],
        col_widths=[4.5, 12.5],
    )

    d.h2("ลำดับการทำงาน")
    d.bullets(
        [
            "เคาน์เตอร์ HIS รับมัดจำ (หรือคืนมัดจำ) → สรุปรายวัน POST /deposits",
            "ERP เก็บชุด deposit (ห้ามมี sales) → validate → ready/error",
            "นักบัญชี Post → เดบิตเงินสด/ธนาคาร เครดิตหนี้สินรับล่วงหน้า (หรือกลับด้านเมื่อ refund)",
            "วันมารักษา: ตัดมัดจำผ่าน Revenue ด้วย payment_method_code=advance",
            "HIS เก็บยอดคงเหลือราย HN เอง — ERP รับเฉพาะยอดสรุปและเลขใบเสร็จ (ticket_external_id)",
        ],
        numbered=True,
    )

    d.h2("ฟิลด์รายการมัดจำ (deposits[] หรือ payments[])")
    d.table(
        ["ฟิลด์", "ความหมาย"],
        [
            ["line_external_id", "รหัสบรรทัด"],
            ["ticket_external_id", "เลขใบเสร็จมัดจำ (ห้ามส่ง HN)"],
            ["payment_method_code", "cash | transfer | credit_card | advance_in"],
            ["service_type", "op | ip"],
            ["amount", "จำนวนเงิน"],
            ["transaction_type", "receive (ค่าเริ่มต้น) | refund"],
            ["control_totals.payments_total", "ยอดควบคุมรวมชุด"],
        ],
        col_widths=[5.5, 11.5],
    )

    d.h2("ตัวอย่าง Payload — รับมัดจำ")
    d.code(
        'POST /vpk/api/v1/his/deposits\n'
        '{\n'
        '  "external_id": "HIS-DEP-2026-09-21-1",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-09-21",\n'
        '  "shift": "1",\n'
        '  "deposits": [\n'
        '    {"line_external_id": "DEP-1", "ticket_external_id": "RCP-DEP-0001",\n'
        '     "payment_method_code": "cash", "service_type": "ip", "amount": 20000},\n'
        '    {"line_external_id": "DEP-2", "ticket_external_id": "RCP-DEP-0002",\n'
        '     "payment_method_code": "transfer", "service_type": "op", "amount": 5000}\n'
        '  ],\n'
        '  "control_totals": {"payments_total": 25000}\n'
        '}'
    )

    d.h2("ตัวอย่าง Payload — คืนมัดจำ")
    d.code(
        '{\n'
        '  "external_id": "HIS-DEP-2026-09-22-REF",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-09-22",\n'
        '  "deposits": [{\n'
        '    "line_external_id": "DEP-REF-1",\n'
        '    "ticket_external_id": "RCP-DEP-0001",\n'
        '    "payment_method_code": "cash",\n'
        '    "service_type": "ip",\n'
        '    "transaction_type": "refund",\n'
        '    "amount": 5000\n'
        '  }],\n'
        '  "control_totals": {"payments_total": 5000}\n'
        '}'
    )

    d.h2("เชื่อมกับวันมารักษา (ตัดมัดจำ)")
    d.p(
        "เมื่อคนไข้มาใช้บริการ ส่งยอดขายส่วนคนไข้ผ่าน POST /revenue แล้วตัดด้วย advance "
        "เท่าที่ใช้จากมัดจำ หากมัดจำไม่พอ ส่ง cash/transfer/credit_card ส่วนต่าง",
        align="justify",
    )
    d.table(
        ["รหัสรับชำระ", "วัน", "ผลบัญชี"],
        [
            ["advance_in (หรือชุด /deposits)", "วันรับมัดจำ", "Dr เงิน / Cr 2103010103.101 — ไม่ลงรายได้"],
            ["advance (+ cash ส่วนต่าง)", "วันมารักษา", "ใบแจ้งหนี้ + ใบรับเงิน HADV/HCSH — ลดหนี้สินรับล่วงหน้า"],
        ],
        col_widths=[5.5, 4.0, 7.5],
    )
    d.note("ชุดมัดจำห้ามมี sales — ถ้ามีจะถูกปฏิเสธ; รหัส entitlement/advance ไม่ใช้บนบรรทัดมัดจำ")

    # ----- 4 Entitlements -----
    d.page_break()
    d.h1("Interface 3 — HIS Entitlements")
    d.h2("ภาพรวม")
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["ชื่อเมนู", "บัญชี → ลูกหนี้ → HIS Entitlements"],
            ["วัตถุประสงค์", "แมปรหัสสิทธิ์จาก HIS → คู่ค้าผู้จ่าย + บัญชีรายได้/ลูกหนี้/เงินสด"],
            ["ทิศทาง", "ตั้งค่าใน ERP; HIS อ่านผ่าน Lookup (ไม่ใช่ push queue)"],
            ["Endpoint Lookup", "GET /vpk/api/v1/his/lookups/entitlements"],
            ["โมเดล", "vpk.his.entitlement.map"],
            ["เกี่ยวข้อง", "HIS Payment Methods (vpk.his.payment.method.map) · ลูกหนี้คงค้าง · Aged Receivable"],
            ["รหัส workflow", "E1 ตั้งแมปสิทธิ์และวิธีรับเงิน"],
        ],
        col_widths=[4.5, 12.5],
    )

    d.h2("บทบาทใน Integration")
    d.bullets(
        [
            "เป็น master ที่ต้องตั้งก่อนรับรายได้ — รหัสที่ไม่มีแมปทำให้ชุด revenue เป็น error",
            "HIS เรียก Lookup เพื่อทราบรหัสสิทธิ์ที่ ERP รองรับ และว่าสิทธิ์นั้นสร้างใบรับเงินหรือพักลูกหนี้",
            "ตอน Post รายได้ ระบบ resolve แมปด้วย find_map(code, service_type, item_type) "
            "fallback: exact → item_type=all → service_type=both",
        ]
    )

    d.h2("ฟิลด์ Master (vpk.his.entitlement.map)")
    d.table(
        ["ฟิลด์", "ความหมาย"],
        [
            ["code", "รหัสสิทธิ์ (normalize เป็นตัวพิมพ์ใหญ่) เช่น SELF_PAY, UC, SSO, CSMBS"],
            ["service_type", "op / ip / both"],
            ["item_type", "all / service / drug / medical_supply / lab / other"],
            ["partner_id", "คู่ค้าผู้จ่าย (กองทุน หรือชำระเอง OP/IP)"],
            ["income_account_id / _code", "บัญชีรายได้"],
            ["receivable_account_id / _code", "บัญชีลูกหนี้"],
            ["cash_account_id / _code", "บัญชีเงินสด"],
            ["receipt_journal_id", "สมุดใบรับเงินของสิทธิ์ (ถ้าใช้)"],
            ["create_payment", "True = ชำระเอง (กระทบเงิน); False = พักลูกหนี้กองทุน"],
            ["remittance_sequence / remittance_label", "ลำดับ/ชื่อในใบนำส่งเงิน"],
        ],
        col_widths=[5.5, 11.5],
    )

    d.h2("แมปเริ่มต้นที่ seed ในระบบ (ตัวอย่างบัญชี)")
    d.table(
        ["รหัส", "บริการ", "ชื่อ", "บัญชีรายได้", "บัญชีลูกหนี้", "create_payment"],
        [
            ["SELF_PAY", "OP", "ชำระเงินเอง OP", "4301020104.106", "1102050102.106", "True"],
            ["SELF_PAY", "IP", "ชำระเงินเอง IP", "4301020104.107", "1102050102.107", "True"],
            ["UC", "OP", "UC / บัตรทอง OP", "4301020105.201", "1102050101.201", "False"],
            ["UC", "IP", "UC / บัตรทอง IP", "4301020105.202", "1102050101.202", "False"],
            ["SSO", "OP", "ประกันสังคม OP", "4301020106.303", "1102050101.301", "False"],
            ["SSO", "IP", "ประกันสังคม IP", "4301020106.306", "1102050101.302", "False"],
            ["CSMBS", "OP", "เบิกจ่ายตรง OP", "4301020104.401", "1102050101.401", "False"],
            ["CSMBS", "IP", "เบิกจ่ายตรง IP", "4301020104.402", "1102050101.402", "False"],
        ],
        col_widths=[2.4, 1.8, 3.8, 3.2, 3.2, 2.6],
    )

    d.h2("Payment Method Map ที่ใช้คู่กับ Entitlements")
    d.table(
        ["กลุ่ม", "รหัส", "พฤติกรรม"],
        [
            ["เงินจริง", "cash, transfer, credit_card", "สร้างใบรับเงิน"],
            ["มัดจำ", "advance_in, advance", "รับ/ตัดหนี้สินรับล่วงหน้า"],
            ["สิทธิ์", "sso, uc, csmbs, ar_claim", "is_entitlement=True — พักลูกหนี้"],
        ],
        col_widths=[3.0, 6.0, 8.0],
    )

    d.h2("Lookup Response (สรุป)")
    d.p(
        "GET /vpk/api/v1/his/lookups/entitlements คืนฟิลด์เช่น code, name, service_type, "
        "item_type, create_payment, parks_receivable สำหรับให้ HIS ตรวจสอบก่อนส่งชุดรายได้",
        align="justify",
    )

    # ----- 5 Stock Issue -----
    d.page_break()
    d.h1("Interface 4 — HIS ตัดจ่ายสินค้า")
    d.h2("ภาพรวม")
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["ชื่อเมนู", "สินค้าคงคลัง → การปฏิบัติการ → HIS ตัดจ่ายสินค้า"],
            ["วัตถุประสงค์", "ตัดสต็อกยา/เวชภัณฑ์ที่จ่ายตามบริการคนไข้ (หรือ ward/expired/adjust)"],
            ["ทิศทาง", "HIS → ERP"],
            ["Endpoint", "POST /vpk/api/v1/his/stock-issues"],
            ["โมเดลคิว", "vpk.his.batch (batch_type=stock_issue) · vpk.his.stock.line"],
            ["ผู้ Post", "Pharmacist (group_his_pharmacist)"],
            ["เอกสาร ERP", "stock.picking ประเภท HISOUT → ตำแหน่ง HIS Consumption; stock.scrap ถ้า reason=expired"],
            ["รหัส workflow", "D2 รับชุด · D3–D5 Post/คืนสต็อก · W5/W6 สถานะกลับ HIS"],
        ],
        col_widths=[4.5, 12.5],
    )

    d.h2("ลำดับการทำงาน")
    d.bullets(
        [
            "HIS ส่งรายการตัดจ่ายรายครั้งต่อคนไข้ หรือรวมเป็นชุดรายวัน (แต่ละบรรทัดระบุคนไข้)",
            "ERP เก็บ HN/VN เฉพาะคิวตัดจ่าย (ยังตัดชื่อ/CID ทิ้ง) → validate ยอด qty และรหัสสินค้า/Lot",
            "เภสัชกรเปิดคิว ตรวจชุด แล้วกด Post",
            "ระบบจัดกลุ่มตามคลัง/ตำแหน่ง → สร้างใบตัดจ่าย HISOUT และ validate ทันที",
            "สินค้าติดตาม Lot แต่ไม่ส่ง Lot → ระบบเลือก FEFO; Lot/สินค้าไม่มีใน ERP → error (ไม่สร้างใหม่อัตโนมัติ)",
            "Reversal สร้างใบรับคืนของใบตัดจ่ายเดิม",
        ],
        numbered=True,
    )

    d.h2("ฟิลด์รายการ (issues[] / items[])")
    d.table(
        ["ฟิลด์", "บังคับ", "ความหมาย"],
        [
            ["line_external_id", "ใช่", "รหัสบรรทัด"],
            ["hn", "เมื่อ patient_use", "รหัสโรงพยาบาลคนไข้"],
            ["vn", "เมื่อ patient_use", "รหัสครั้งรับบริการ"],
            ["product_code", "ใช่", "default_code ใน ERP (ยาตัวเลข pad เป็น 5 หลัก)"],
            ["item_type", "ไม่", "drug | medical_supply | other"],
            ["warehouse_code", "แนะนำ", "เช่น PHAR, UNIT — หรือใช้ department_code + unit map"],
            ["department_code", "ไม่", "รหัสหน่วย → vpk.his.unit.map"],
            ["location_code", "ไม่", "ชั้นวาง"],
            ["qty", "ใช่", "จำนวน; ต้องเท่าผลรวม lots[]"],
            ["lot_name / lots[]", "ถ้าติดตาม Lot", "Lot เดียว หรือหลาย Lot; ห้ามส่งคู่กัน"],
            ["reason", "ไม่", "patient_use (default) | ward_use | expired | adjust"],
            ["control_totals.qty_total", "ใช่*", "ยอดควบคุมจำนวนรวมชุด"],
        ],
        col_widths=[4.5, 3.5, 9.0],
    )

    d.h2("ตัวอย่าง Payload")
    d.code(
        'POST /vpk/api/v1/his/stock-issues\n'
        '{\n'
        '  "external_id": "HIS-STK-2026-08-25",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-08-25",\n'
        '  "issues": [{\n'
        '    "line_external_id": "DRUG-PARA-1",\n'
        '    "hn": "6500123", "vn": "6808250001",\n'
        '    "product_code": "00001", "item_type": "drug",\n'
        '    "warehouse_code": "PHAR", "qty": 10, "reason": "patient_use",\n'
        '    "lots": [{"lot_name": "LOT-A", "qty": 6}, {"lot_name": "LOT-B", "qty": 4}]\n'
        '  }],\n'
        '  "control_totals": {"qty_total": 10}\n'
        '}'
    )

    d.h2("กฎ PII และ Master Data")
    d.bullets(
        [
            "ตัดจ่ายคนไข้ (patient_use) ต้องมี hn และ vn — เก็บในคิวเพื่อไล่รายการจ่ายยา",
            "API รายได้ยังห้ามส่ง HN/VN ตามเดิม",
            "สอบถามว่าสินค้าต้องส่ง Lot หรือไม่: GET /lookups/products?codes=...",
            "ไม่รู้จัก product_code หรือ lot_name → ชุด error จนกว่าจะมีใน ERP",
        ]
    )

    # ----- 6 Requisition -----
    d.page_break()
    d.h1("Interface 5 — HIS เบิกเติมสินค้า")
    d.h2("ภาพรวม")
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["ชื่อเมนู", "สินค้าคงคลัง → การปฏิบัติการ → HIS เบิกเติมคลัง"],
            ["วัตถุประสงค์", "หน่วยบริการขอเบิกยา/เวชภัณฑ์จากคลังหลักไปเติมคลัง front — ไม่ใช่จ่ายคนไข้"],
            ["ทิศทาง", "HIS → ERP"],
            ["Endpoint", "POST /vpk/api/v1/his/stock-requisitions"],
            ["โมเดลคิว", "vpk.his.batch (batch_type=stock_requisition) · vpk.his.requisition.line"],
            ["ผู้ Post", "Pharmacist; คลังปฏิบัติการโอนจนเสร็จ"],
            ["เอกสาร ERP", "Internal Transfer picking type HISINT (ต้นทาง → ปลายทาง)"],
            ["รหัส workflow", "B3 HIS เบิกเติม · W5/W6"],
        ],
        col_widths=[4.5, 12.5],
    )

    d.h2("ลำดับการทำงาน")
    d.bullets(
        [
            "หน่วยบริการใน HIS สร้างคำขอเบิกเติม → POST /stock-requisitions (ไม่มี HN/VN)",
            "ERP เก็บชุด → validate ยอด qty และรหัสสินค้า → ready/error",
            "เภสัชกร Post → สร้างใบโอนภายใน HISINT",
            "คลังหยิบ/แพ็ค/ตรวจสอบตาม flow โอนปกติ",
            "ชุดเปลี่ยนเป็น posted เมื่อใบโอนในสายครบสถานะ done "
            "(ต่างจากตัดจ่ายที่ Post แล้วเสร็จทันที)",
            "ถ้าไม่ส่ง Lot ตอนขอเบิก ระบบเลือก FEFO ตอน Post",
        ],
        numbered=True,
    )

    d.h2("ฟิลด์ชุดและรายการ")
    d.table(
        ["ฟิลด์", "ความหมาย"],
        [
            ["source_warehouse_code", "คลังต้นทาง (ค่าเริ่มต้น PHAR)"],
            ["dest_warehouse_code", "คลังปลายทาง front (ค่าเริ่มต้น UNIT)"],
            ["dest_location_code", "ชั้นวางปลายทาง (ออปชัน)"],
            ["department_code", "หน่วยบริการ — ใช้แมปปลายทางถ้าไม่ส่ง dest_warehouse_code"],
            ["lines[] / items[] / requisitions[]", "รายการขอเบิก: product_code, qty, item_type, lot (ออปชัน)"],
            ["control_totals.qty_total", "ยอดควบคุมจำนวนรวม"],
        ],
        col_widths=[6.0, 11.0],
    )

    d.h2("ตัวอย่าง Payload")
    d.code(
        'POST /vpk/api/v1/his/stock-requisitions\n'
        '{\n'
        '  "external_id": "HIS-REQ-2026-08-26-OPD-1",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-08-26",\n'
        '  "source_warehouse_code": "PHAR",\n'
        '  "dest_warehouse_code": "UNIT",\n'
        '  "dest_location_code": "shelf ห้องยาชั้น 1",\n'
        '  "department_code": "OPD",\n'
        '  "lines": [\n'
        '    {"line_external_id": "R1", "product_code": "00001", "item_type": "drug", "qty": 100},\n'
        '    {"line_external_id": "R2", "product_code": "201001", "item_type": "medical_supply", "qty": 20}\n'
        '  ],\n'
        '  "control_totals": {"qty_total": 120}\n'
        '}'
    )

    d.h2("เปรียบเทียบกับตัดจ่าย")
    d.table(
        ["หัวข้อ", "ตัดจ่ายสินค้า", "เบิกเติมสินค้า"],
        [
            ["จุดประสงค์", "จ่ายออกจากการบริการคนไข้", "เติมสต็อกคลัง front"],
            ["HN/VN", "จำเป็นเมื่อ patient_use", "ห้าม/ไม่ใช้"],
            ["เอกสาร", "HISOUT → Consumption", "HISINT โอนภายใน"],
            ["Lot", "บังคับถ้าติดตาม Lot (หรือ FEFO)", "ออปชันตอนขอ — FEFO ตอน Post"],
            ["เมื่อไหร่ posted", "หลัง Post ตัดจ่ายทันที", "เมื่อโอนครบ done"],
        ],
        col_widths=[3.5, 6.5, 7.0],
    )

    # ----- 7 Cross-cutting -----
    d.page_break()
    d.h1("บริการร่วม — Lookup และสถานะชุด")
    d.h2("Endpoints ที่ HIS เรียกได้")
    d.table(
        ["Method", "Path", "ใช้เมื่อ"],
        [
            ["GET", "/vpk/api/v1/his/health", "ตรวจว่า API เปิดและมีคีย์"],
            ["GET", "/vpk/api/v1/his/lookups/entitlements", "รายการสิทธิ์ที่ ERP รองรับ"],
            ["GET", "/vpk/api/v1/his/lookups/payment-methods", "วิธีรับเงินที่แมปแล้ว"],
            ["GET", "/vpk/api/v1/his/lookups/warehouses", "คลังและหน่วยบริการ"],
            ["GET", "/vpk/api/v1/his/lookups/products?codes=...", "ตรวจรหัสสินค้าและ lot_required"],
            ["GET", "/vpk/api/v1/his/batches/{external_id}?source_system=...", "สถานะชุด + เอกสารที่ผูก + errors"],
        ],
        col_widths=[2.0, 8.5, 6.5],
    )

    d.h2("Idempotency และ Reversal (ใช้ร่วมทุกคิว)")
    d.bullets(
        [
            "คีย์ซ้ำก่อน Post: แทนที่รายการในชุดเดิม (updated)",
            "คีย์ซ้ำหลัง Post: คืนชุดเดิมไม่เปลี่ยน (unchanged, HTTP 200)",
            "แก้ไขหลัง Post: ส่ง external_id ใหม่ พร้อม batch_type=reversal และ original_external_id",
            "ชุดที่ Post แล้วยกเลิกตรงๆ ไม่ได้",
        ]
    )

    d.h2("เมทริกซ์ PII")
    d.table(
        ["Interface", "HN/VN", "ชื่อ/CID", "หมายเหตุ"],
        [
            ["Revenue Queue", "ห้าม", "ห้าม", "ระบบตัดทิ้งถ้าส่งมา"],
            ["รับมัดจำ", "ห้าม", "ห้าม", "ใช้ ticket_external_id เป็นเลขใบเสร็จ"],
            ["Entitlements", "—", "—", "ไม่มีข้อมูลคนไข้"],
            ["ตัดจ่ายสินค้า", "จำเป็น (patient_use)", "ห้าม", "เก็บ HN/VN ในคิวเท่านั้น"],
            ["เบิกเติมสินค้า", "ไม่ใช้", "ห้าม", "เป็นการโอนคลัง"],
        ],
        col_widths=[4.0, 4.0, 3.0, 6.0],
    )

    # ----- 8 Ops -----
    d.h1("บทบาท เมนู และการดำเนินงาน")
    d.table(
        ["บทบาท", "หน้าที่หลัก"],
        [
            ["ทีม HIS", "ส่งสรุปตาม endpoint ที่ถูกต้อง · สอบถามสถานะ · ส่ง reversal เมื่อต้องแก้"],
            ["นักบัญชี HIS", "ดูแล Entitlements / Payment Methods · Post รายได้และมัดจำ · ใบนำส่งเงิน"],
            ["เภสัชกร", "Post ตัดจ่ายและเบิกเติม · ตรวจ Lot / สต็อก"],
            ["เจ้าหน้าที่คลัง", "ปฏิบัติการโอนจากชุดเบิกเติมจนใบโอน done"],
            ["IT", "ตั้ง API key · เปิด/ปิด API · ตรวจ log vpk.his.api.log"],
        ],
        col_widths=[4.0, 13.0],
    )

    d.h2("แผนที่เมนู ERP")
    d.table(
        ["เมนู", "ที่อยู่"],
        [
            ["HIS Revenue Queue", "บัญชี → ลูกหนี้"],
            ["HIS รับมัดจำค่ารักษา", "บัญชี → ลูกหนี้"],
            ["HIS Entitlements / Payment Methods", "บัญชี → ลูกหนี้"],
            ["ใบนำส่งเงิน", "บัญชี → ลูกหนี้ (Wizard)"],
            ["HIS ตัดจ่ายสินค้า", "สินค้าคงคลัง → การปฏิบัติการ"],
            ["HIS เบิกเติมคลัง", "สินค้าคงคลัง → การปฏิบัติการ"],
        ],
        col_widths=[6.5, 10.5],
    )

    # ----- 9 Traceability -----
    d.h1("การอ้างอิงทางเทคนิค")
    d.table(
        ["รายการ", "ที่อยู่ในระบบ"],
        [
            ["โมดูล", "odoo18-custom-addons/vpk_his_api"],
            ["Controller", "controllers/his_api.py"],
            ["Ingest service", "models/his_api_service.py"],
            ["Posting service", "models/his_posting.py"],
            ["Batch / lines", "models/his_batch.py และ line models"],
            ["ตัวอย่าง Payload", "vpk_his_api/doc/payload-examples.md"],
            ["Dataflow การเงิน", "docs/finance_dataflow_data.py (E1–E6)"],
            ["Dataflow คลัง", "docs/warehouse_dataflow_data.py (B3, D2–D5, W5–W6)"],
            ["ทดสอบพฤติกรรม", "vpk_his_api/tests/test_his_api.py"],
        ],
        col_widths=[5.0, 12.0],
    )

    d.h2("เอกสารที่เกี่ยวข้อง")
    d.bullets(
        [
            "ข้อกำหนดรายได้: vpk_his_api/doc/build_revenue_spec.py → VPK-HIS-SPEC-REV-001",
            "ข้อกำหนดตัดจ่าย: build_stock_spec.py",
            "ข้อกำหนดเบิกเติม: build_requisition_spec.py",
            "Presentation สถาปัตยกรรม: build_his_api_presentation.py",
            "เอกสารออกแบบระบบรวม: docs/build_system_design_docx.py",
        ]
    )

    d.h2("ประวัติเอกสาร")
    d.table(
        ["เวอร์ชัน", "วันที่", "รายละเอียด"],
        [
            ["1.0", "17 พ.ย. 2569", "ร่างแรก — รวม 5 interface HIS→ERP เป็นเอกสารออกแบบเดียว"],
        ],
        col_widths=[3.0, 4.0, 10.0],
    )

    d.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
