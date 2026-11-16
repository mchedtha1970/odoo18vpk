#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""สร้างเอกสารออกแบบระบบ (System Design Document) ย้อนหลังจากโค้ด VPK ERP (Odoo 18) เป็นไฟล์ Word

ที่มาข้อมูล:
  - โค้ดใน odoo18-custom-addons/vpk_* (อ่าน __manifest__.py, models, security, controllers, data แบบอัตโนมัติ)
  - ข้อมูล Workflow / Input-Process-Output ใน docs/*_dataflow_data.py
  - ประวัติ git

รัน: python3 docs/build_system_design_docx.py
ผลลัพธ์: docs/เอกสารออกแบบระบบ-VPK-ERP-Odoo18.docx
"""
import ast
import datetime as dt
import glob
import os
import re
import subprocess
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
ADDONS = ROOT / "odoo18-custom-addons"
OUT = DOCS / "เอกสารออกแบบระบบ-VPK-ERP-Odoo18.docx"
sys.path.insert(0, str(DOCS))

import asset_dataflow_data as D_ASSET  # noqa: E402
import budget_dataflow_data as D_BUDGET  # noqa: E402
import finance_dataflow_data as D_FIN  # noqa: E402
import maintenance_dataflow_data as D_MAINT  # noqa: E402
import procurement_dataflow_data as D_PROC  # noqa: E402
import warehouse_dataflow_data as D_WH  # noqa: E402

FONT = "Prompt"
# Prompt ตัวใหญ่กว่า TH Sarabun จึงย่อขนาดทุกจุดตามสัดส่วนนี้ (ค่าในโค้ดคิดเป็นขนาดแบบ Sarabun)
SCALE = 0.7


def fs(size):
    return max(7.0, round(size * SCALE * 2) / 2)
NAVY = RGBColor(0x12, 0x3A, 0x56)
MUTED = RGBColor(0x5B, 0x68, 0x78)
HEAD_FILL = "123A56"
ZEBRA = "F3F6F9"
THAI_MONTH = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม",
              "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]


def thai_date(d):
    return f"{d.day} {THAI_MONTH[d.month]} {d.year + 543}"


# ---------------------------------------------------------------------------
# 1) กลุ่มระบบงาน และการจัดโมดูลเข้ากลุ่ม
# ---------------------------------------------------------------------------
DOMAINS = OrderedDict([
    ("BUD", ("ระบบงบประมาณ", ["vpk_budget"])),
    ("PRO", ("ระบบจัดซื้อจัดจ้าง", [
        "vpk_procurement_auto_pr", "vpk_procurement_action_plan", "vpk_procurement_inbox",
        "vpk_purchase_request_urgent", "vpk_purchase_request_reject_notify", "vpk_purchase_request_tracking",
        "vpk_pr_saraban", "vpk_purchase_fy_history", "vpk_purchase_moq", "vpk_purchase_order_form",
        "vpk_ebidding", "vpk_purchase_agreement_egp", "vpk_purchase_contract", "vpk_purchase_contract_document",
        "vpk_committee_appointment", "vpk_work_acceptance", "vpk_product_specification", "vpk_th_purchase_menu",
    ])),
    ("VEN", ("ระบบผู้จำหน่าย", [
        "vpk_purchase_portal_egp", "vpk_vendor_api", "vpk_vendor_evaluation", "vpk_vendor_history",
        "vpk_vendor_loan", "vpk_vendor_security", "vpk_partner_duplicate_check",
    ])),
    ("WH", ("ระบบคลังสินค้าและเวชภัณฑ์", [
        "vpk_product", "vpk_product_import", "vpk_master_data_templates", "vpk_stock_location", "vpk_stock_qc",
        "vpk_stock_replenishment", "vpk_stock_warehouse", "vpk_stock_card", "vpk_mobile_barcode",
    ])),
    ("AST", ("ระบบบริหารทรัพย์สิน", [
        "vpk_asset_registry", "vpk_asset_menu", "vpk_asset_transfer", "vpk_asset_disposal",
        "vpk_asset_inventory", "vpk_asset_equipment",
    ])),
    ("MNT", ("ระบบซ่อมบำรุง", ["vpk_maintenance"])),
    ("FIN", ("ระบบเจ้าหนี้ การเงิน และบัญชี", [
        "vpk_payment_request", "vpk_payment_voucher", "vpk_disbursement_form", "vpk_gfmis",
        "vpk_cheque_management", "vpk_bank_subledger", "vpk_wht_cert_4235", "vpk_finance_flow",
        "vpk_hospital_balance_sheet", "vpk_th_account_menu", "vpk_his_api", "vpk_hr_payroll_api",
    ])),
    ("DOC", ("ระบบเอกสาร สารบรรณ และการลงนาม", [
        "vpk_document", "vpk_document_studio", "vpk_document_studio_onlyoffice",
        "vpk_document_studio_procurement", "vpk_document_studio_sign", "vpk_official_document", "vpk_pdf_preview",
    ])),
    ("PLT", ("แพลตฟอร์มกลาง การอนุมัติ และส่วนติดต่อผู้ใช้", [
        "vpk_tier_validation", "vpk_approval_api", "vpk_sidebar_menu", "vpk_login_page", "vpk_buddhist_date",
        "vpk_th_company_label", "vpk_th_discard_label", "vpk_data_cleaner",
    ])),
])

DOMAIN_DATA = {
    "BUD": D_BUDGET, "PRO": D_PROC, "WH": D_WH, "AST": D_ASSET, "MNT": D_MAINT, "FIN": D_FIN,
}

DOMAIN_INTRO = {
    "BUD": "รับคำของบประมาณจากหน่วยงาน พิจารณา จัดสรร และอนุมัติเป็นรายการงบ (budget.lines) ในแผนงบประมาณประจำปี "
           "แผนงบที่อนุมัติเป็น Input ของระบบจัดซื้อจัดจ้าง และระบบควบคุมการจองงบ/ใช้จริงจาก PR, PO และใบแจ้งหนี้",
    "PRO": "ครอบคลุมตั้งแต่แผนจัดซื้อประจำปี ใบขอซื้อ (PR) การอนุมัติหลายระดับ งานพัสดุและเอกสารตามระเบียบ "
           "การจัดซื้อผ่านระบบ e-GP (เฉพาะเจาะจง / e-bidding) ใบสั่งซื้อ ทะเบียนสัญญา (รวมสัญญาไม่จำกัดจำนวน/call-off) "
           "คณะกรรมการ และการตรวจรับ ก่อนส่งต่อให้คลังและเจ้าหนี้",
    "VEN": "ฐานข้อมูลผู้จำหน่าย การป้องกันข้อมูลซ้ำ สิทธิ์การแก้ไข Portal และ Mobile API สำหรับผู้ขาย "
           "การประเมินผู้จำหน่าย ประวัติการซื้อขาย และการยืมของจากผู้ขาย",
    "WH": "รับสินค้าพร้อมตรวจคุณภาพ (QC) และกรรมการตรวจรับ การเบิก-จ่าย-โอนระหว่างคลังหลักและคลังหน่วยงาน "
          "ควบคุมยาเสพติด/ยาความเสี่ยงสูง เติมสต็อกอัตโนมัติ บัญชีคุมวัสดุ และแอปสแกนบาร์โค้ดบนมือถือ",
    "AST": "ขึ้นทะเบียนสินทรัพย์จากใบแจ้งหนี้/PO ติดตามแหล่งที่มา (GFMIS) ค่าเสื่อมราคา การโอน การจำหน่าย "
           "การตรวจนับประจำปีผ่าน Portal/QR และการเชื่อมกับงานซ่อมบำรุง",
    "MNT": "รับแจ้งซ่อมจากแอป/ระบบ มอบหมายช่าง ประเมินทางซ่อม เบิกอะไหล่ จ้างซ่อมภายนอกผ่าน PR "
           "และแทงจำหน่ายเมื่อซ่อมไม่คุ้มค่า พร้อม Dashboard ติดตาม",
    "FIN": "ขออนุมัติเบิกจ่ายจากจัดซื้อ ตั้งเจ้าหนี้ ภาษีหัก ณ ที่จ่าย (รวมแบบ 4235) ขบ.01/11 เบิกจ่ายผ่าน GFMIS "
           "ใบสำคัญจ่าย เช็ค บัญชีคุมเงินฝากธนาคาร รับรายได้จาก HIS เงินเดือนจาก HR งบการเงิน และ Dashboard AP/Finance/GL",
    "DOC": "สร้างแบบฟอร์มเอกสารเอง (Document Studio) แก้ไข Word ผ่าน ONLYOFFICE ออกหนังสือราชการ ขอเลขสารบรรณ "
           "ส่งลงนามบน PDF และแนบไฟล์ประกอบเอกสารทุกประเภท",
    "PLT": "เส้นทางอนุมัติตามลำดับ (Tier Validation) ที่ใช้ร่วมทุกระบบ API อนุมัติบนมือถือ เมนูแถบข้าง "
           "หน้า Login ของโรงพยาบาล การแสดงวันที่ พ.ศ. ป้ายภาษาไทย และเครื่องมือล้างข้อมูลสำหรับ UAT",
}

OCA_LAYERS = [
    ("Odoo 18 Community (core)", "odoo18/addons", "โมดูลมาตรฐาน: account, purchase, stock, maintenance, analytic, hr ฯลฯ"),
    ("account-financial-tools-18.0", "OCA", "เครื่องมือบัญชีเสริม (เช่น ล็อกงวด ปีบัญชี)"),
    ("account-invoicing-18.0 / account-payment-18.0", "OCA", "ใบแจ้งหนี้และการชำระเงิน"),
    ("base_accounting_kit-18.0.5.0.9", "Cybrosys", "สินทรัพย์ งบประมาณบัญชี (base_account_budget) รายงานบัญชี"),
    ("account_accountant / account_reports / accountant", "Odoo-compatible", "เมนูนักบัญชีและรายงานการเงิน"),
    ("l10n-thailand-18.0", "OCA", "Localization ไทย: ภาษีหัก ณ ที่จ่าย ฟอนต์ไทย ตัวอักษรจำนวนเงิน"),
    ("purchase-workflow-18.0", "OCA", "purchase_request, purchase_requisition และ workflow จัดซื้อ"),
    ("server-ux-18.0", "OCA", "base_tier_validation และเครื่องมือ UX"),
    ("server-tools-18.0 / reporting-engine-18.0", "OCA", "เครื่องมือเซิร์ฟเวอร์ และ report_xlsx"),
    ("partner-contact-18.0 / hr-expense-18.0", "OCA", "ข้อมูลคู่ค้า และค่าใช้จ่ายพนักงาน"),
    ("stock-logistics-workflow-18.0", "OCA", "workflow คลังสินค้า"),
    ("onlyoffice-odoo-18.0", "ONLYOFFICE", "เชื่อม ONLYOFFICE Docs สำหรับแก้ไขเอกสาร"),
]

EXTERNAL = [
    ("HIS (ระบบสารสนเทศโรงพยาบาล)", "vpk_his_api", "REST API (รับเข้า)",
     "สรุปรายได้/มัดจำรายวัน และการตัดจ่ายยา เข้าคิว staging แล้วลงบัญชีรายได้และตัดสต็อก"),
    ("ระบบ HR / เงินเดือน", "vpk_hr_payroll_api", "REST API (รับเข้า)",
     "รับชุดเงินเดือน ตรวจแล้วกดผ่านเพื่อสร้างสมุดรายวัน"),
    ("ระบบ e-GP กรมบัญชีกลาง", "vpk_ebidding, vpk_purchase_agreement_egp", "บันทึก/แนบไฟล์ (ไม่เชื่อมตรง)",
     "บันทึกแผน เลขโครงการ ผลการพิจารณา ผู้ชนะ และเอกสารที่ได้จาก e-GP"),
    ("New GFMIS Thai", "vpk_gfmis", "บันทึกเอกสารและผูกเลขอ้างอิง",
     "เอกสารขอเบิก อม.01/อม.02 ผลการจ่าย และเลขเอกสาร GFMIS ของสินทรัพย์"),
    ("ONLYOFFICE Docs", "vpk_document_studio_onlyoffice", "Document Server (JWT)",
     "แก้ไขแม่แบบ Word ในหน้า Odoo และแปลงเป็น PDF"),
    ("แอปมือถืออนุมัติ", "vpk_approval_api", "REST API",
     "ดึงงานรออนุมัติ ประวัติ เปิดเอกสาร และอนุมัติ/ตีกลับ"),
    ("แอปผู้ขาย / Vendor Portal", "vpk_vendor_api, vpk_purchase_portal_egp", "REST API / Web Portal",
     "ผู้ขายดู PO เปิด PDF ลงนามยืนยัน และส่งเอกสารการค้า"),
    ("แอปสแกนบาร์โค้ดคลัง", "vpk_mobile_barcode", "JSON-RPC (auth=user)",
     "รับ/จ่าย/โอน/ตรวจนับสต็อกด้วยการสแกน"),
    ("Google Drive", "vpk_document", "OAuth callback", "เก็บ/เปิดไฟล์แนบผ่าน Google"),
]


# ---------------------------------------------------------------------------
# 2) อ่านโค้ด
# ---------------------------------------------------------------------------
def _lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def scan_module(path):
    mod = path.name
    manifest = ast.literal_eval("{" + (path / "__manifest__.py").read_text(encoding="utf-8").split("{", 1)[1])
    new_models, ext_models, routes = [], set(), []
    loc = 0
    for py in sorted(path.rglob("*.py")):
        if "tests" in py.parts or "migrations" in py.parts:
            continue
        src = py.read_text(encoding="utf-8", errors="ignore")
        loc += len(src.splitlines())
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                attrs, nfields = {}, 0
                for st in node.body:
                    if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                        k = st.targets[0].id
                        if k in ("_name", "_inherit", "_description", "_auto"):
                            attrs[k] = _lit(st.value)
                        elif isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Attribute) \
                                and isinstance(st.value.func.value, ast.Name) and st.value.func.value.id == "fields":
                            nfields += 1
                name = attrs.get("_name")
                inh = attrs.get("_inherit")
                inh = [inh] if isinstance(inh, str) else (inh or [])
                if name and name not in inh:
                    kind = "Transient" if any(getattr(b, "attr", "") == "TransientModel" for b in node.bases) else (
                        "Abstract" if any(getattr(b, "attr", "") == "AbstractModel" for b in node.bases) else "Model")
                    new_models.append(dict(name=name, desc=attrs.get("_description") or "", fields=nfields, kind=kind))
                else:
                    ext_models.update(i for i in inh if i)
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "route" and dec.args:
                        r = _lit(dec.args[0])
                        r = r if isinstance(r, list) else [r]
                        auth = next((_lit(k.value) for k in dec.keywords if k.arg == "auth"), "")
                        typ = next((_lit(k.value) for k in dec.keywords if k.arg == "type"), "")
                        methods = next((_lit(k.value) for k in dec.keywords if k.arg == "methods"), None)
                        routes.append(dict(url=", ".join(str(x) for x in r if x), auth=auth or "user",
                                           type=typ or "http", methods=",".join(methods or [])))
    # ลบโมเดลที่ซ้ำ (ประกาศหลายไฟล์)
    seen, uniq = set(), []
    for m in new_models:
        if m["name"] not in seen:
            seen.add(m["name"])
            uniq.append(m)
    ext_models -= seen
    groups, crons, reports, menus = [], [], [], 0
    for xml in path.rglob("*.xml"):
        s = xml.read_text(encoding="utf-8", errors="ignore")
        menus += s.count("<menuitem")
        for rec in re.findall(r'<record[^>]*model="res\.groups"[^>]*>(.*?)</record>', s, re.S):
            g = re.search(r'name="name"[^>]*>([^<]+)<', rec)
            if g:
                groups.append(g.group(1).strip())
        for rec in re.findall(r'<record[^>]*model="ir\.cron"[^>]*>(.*?)</record>', s, re.S):
            g = re.search(r'name="name"[^>]*>([^<]+)<', rec)
            iv = re.search(r'name="interval_number"[^>]*>(\d+)<', rec)
            it = re.search(r'name="interval_type"[^>]*>(\w+)<', rec)
            crons.append((g.group(1).strip() if g else "-",
                          f"ทุก {iv.group(1)} {it.group(1)}" if iv and it else ""))
        for rec in re.findall(r'<record[^>]*model="ir\.actions\.report"[^>]*>(.*?)</record>', s, re.S):
            g = re.search(r'name="name"[^>]*>([^<]+)<', rec)
            mdl = re.search(r'name="model"[^>]*>([^<]+)<', rec)
            typ = re.search(r'name="report_type"[^>]*>([^<]+)<', rec)
            reports.append((g.group(1).strip() if g else "-", mdl.group(1).strip() if mdl else "",
                            typ.group(1).strip() if typ else ""))
    return dict(
        mod=mod, name=manifest.get("name", mod), summary=manifest.get("summary", "") or "",
        version=manifest.get("version", ""), depends=manifest.get("depends", []),
        new=uniq, ext=sorted(ext_models), routes=routes, groups=sorted(set(groups)),
        crons=crons, reports=reports, menus=menus, loc=loc,
    )


def scan_all():
    mods = {}
    for p in sorted(ADDONS.glob("vpk_*")):
        if (p / "__manifest__.py").exists():
            mods[p.name] = scan_module(p)
    return mods


def git_history():
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "--reverse", "--no-merges", "--date=short", "--format=%ad|%s"],
            text=True)
    except Exception:
        return []
    return [ln.split("|", 1) for ln in out.splitlines() if "|" in ln]


# ---------------------------------------------------------------------------
# 3) ตัวช่วยจัดรูปแบบ Word
# ---------------------------------------------------------------------------
def set_cell_bg(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def no_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def set_font(run, size=None, bold=None, color=None, italic=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), FONT)
    if size:
        size = fs(size)
        run.font.size = Pt(size)
        szcs = OxmlElement("w:szCs")
        szcs.set(qn("w:val"), str(int(size * 2)))
        rpr.append(szcs)
    if bold is not None:
        run.font.bold = bold
        if bold:
            rpr.append(OxmlElement("w:bCs"))
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def para(doc_or_cell, text="", size=15, bold=False, color=None, align=None, after=4, before=0, italic=False,
         style=None):
    p = doc_or_cell.add_paragraph(style=style) if style else doc_or_cell.add_paragraph()
    if text:
        r = p.add_run(text)
        set_font(r, size, bold, color, italic)
    pf = p.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(before)
    pf.line_spacing = 1.0
    if align is not None:
        p.alignment = align
    return p


def bullet(doc, text, level=0, size=15):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    r = p.add_run(text)
    set_font(r, size)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    return p


def heading(doc, text, level):
    h = doc.add_heading(level=level)
    r = h.add_run(text)
    set_font(r, {0: 28, 1: 22, 2: 18, 3: 16}[level], True, NAVY)
    h.paragraph_format.keep_with_next = True
    return h


def cell_write(cell, value, size=13, bold=False, color=None):
    cell.text = ""
    lines = value if isinstance(value, (list, tuple)) else str(value).split("\n")
    first = True
    for ln in lines:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(str(ln))
        set_font(r, size, bold, color)


def table(doc, headers, rows, widths_cm, size=13, head_size=13, zebra=True):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    hdr = t.rows[0]
    set_repeat_header(hdr)
    for i, h in enumerate(headers):
        c = hdr.cells[i]
        cell_write(c, h, head_size, True, RGBColor(0xFF, 0xFF, 0xFF))
        set_cell_bg(c, HEAD_FILL)
        for p in c.paragraphs:  # ไม่ให้หัวตารางค้างอยู่ท้ายหน้าโดยไม่มีแถวข้อมูล
            p.paragraph_format.keep_with_next = True
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cell_write(cells[i], v, size)
            if zebra and ri % 2 == 1:
                set_cell_bg(cells[i], ZEBRA)
    for row in t.rows:
        no_split(row)
        for i, w in enumerate(widths_cm):
            row.cells[i].width = Cm(w)
    para(doc, "", after=2)
    return t


def add_toc(doc):
    p = doc.add_paragraph()
    r = p.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = "คลิกขวาแล้วเลือก \"Update Field\" (หรือกด F9) เพื่อแสดงสารบัญ"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (fld, instr, sep, txt, end):
        r._r.append(el)
    set_font(r, 15, color=MUTED)


def add_page_number_footer(section, label):
    p = section.footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"{label}  |  หน้า ")
    set_font(r, 12, color=MUTED)
    r2 = p.add_run()
    for kind, val in (("begin", None), ("instr", "PAGE"), ("end", None)):
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = val
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        r2._r.append(el)
    set_font(r2, 12, color=MUTED)


def new_section(doc, landscape):
    sec = doc.add_section()
    w, h = Cm(21.0), Cm(29.7)
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = h, w
    else:
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width, sec.page_height = w, h
    return sec


def setup_styles(doc):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(fs(15))
    rpr = st.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(a), FONT)
    szcs = OxmlElement("w:szCs")
    szcs.set(qn("w:val"), str(int(fs(15) * 2)))
    rpr.append(szcs)
    for name, size in (("Heading 1", 22), ("Heading 2", 18), ("Heading 3", 16)):
        s = doc.styles[name]
        s.font.name = FONT
        s.font.size = Pt(fs(size))
        s.font.color.rgb = NAVY
        s.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
        s.paragraph_format.space_after = Pt(4)
        s.paragraph_format.keep_with_next = True
        r = s.element.get_or_add_rPr()
        rf = r.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts")
            r.append(rf)
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), FONT)


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------------------
# 4) เนื้อหา
# ---------------------------------------------------------------------------
def build():
    mods = scan_all()
    assigned = {m for _, (_, ms) in DOMAINS.items() for m in ms}
    leftovers = sorted(set(mods) - assigned)
    if leftovers:
        DOMAINS["OTH"] = ("โมดูลอื่น ๆ", leftovers)
    for _, (_, ms) in DOMAINS.items():
        ms[:] = [m for m in ms if m in mods]
    dom_of = {m: k for k, (_, ms) in DOMAINS.items() for m in ms}
    hist = git_history()
    today = dt.date.today()

    tot_models = sum(len(m["new"]) for m in mods.values())
    tot_loc = sum(m["loc"] for m in mods.values())
    tot_routes = sum(len(m["routes"]) for m in mods.values())

    doc = Document()
    setup_styles(doc)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    for s in [sec]:
        s.left_margin = s.right_margin = Cm(2.0)
        s.top_margin = s.bottom_margin = Cm(2.0)

    # ---------- ปก ----------
    for _ in range(5):
        para(doc, "")
    para(doc, "เอกสารออกแบบระบบ", 34, True, NAVY, WD_ALIGN_PARAGRAPH.CENTER, after=2)
    para(doc, "(System Design Document)", 20, False, MUTED, WD_ALIGN_PARAGRAPH.CENTER, after=24)
    para(doc, "ระบบบริหารทรัพยากรองค์กร (ERP)", 24, True, None, WD_ALIGN_PARAGRAPH.CENTER, after=2)
    para(doc, "โรงพยาบาลวชิระภูเก็ต", 24, True, None, WD_ALIGN_PARAGRAPH.CENTER, after=2)
    para(doc, "พัฒนาบน Odoo 18 (VPK ERP)", 18, False, MUTED, WD_ALIGN_PARAGRAPH.CENTER, after=60)
    para(doc, "ฉบับจัดทำย้อนหลังจากระบบที่พัฒนาแล้ว (As-Built) เพื่อใช้เป็นเอกสารอ้างอิง", 16, False, None,
         WD_ALIGN_PARAGRAPH.CENTER, after=2)
    para(doc, f"ข้อมูล ณ วันที่ {thai_date(today)}", 16, False, None, WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)

    # ---------- ประวัติเอกสาร + สารบัญ ----------
    para(doc, "ประวัติการแก้ไขเอกสาร", 20, True, NAVY, after=6)
    table(doc, ["ฉบับที่", "วันที่", "รายละเอียด", "ผู้จัดทำ"],
          [["1.0", thai_date(today),
            "จัดทำเอกสารออกแบบระบบย้อนหลัง (As-Built) จากโค้ดใน repository odoo18vpk "
            f"ครอบคลุม {len(mods)} โมดูล custom", "ทีมพัฒนา VPK ERP"]],
          [2.0, 3.5, 8.0, 3.5])
    para(doc, "หมายเหตุ: ตารางรายชื่อโมดูล แบบจำลองข้อมูล สิทธิ์ API งานอัตโนมัติ และรายงาน ในเอกสารนี้สร้างอัตโนมัติจากโค้ด "
              "ด้วยสคริปต์ docs/build_system_design_docx.py หากระบบมีการเปลี่ยนแปลง ให้รันสคริปต์ใหม่เพื่อปรับปรุงเอกสาร",
         14, color=MUTED, after=12)
    para(doc, "สารบัญ", 20, True, NAVY, after=6)
    add_toc(doc)
    page_break(doc)

    # ---------- 1. บทนำ ----------
    heading(doc, "1. บทนำ", 1)
    heading(doc, "1.1 วัตถุประสงค์ของเอกสาร", 2)
    para(doc, "เอกสารนี้อธิบายการออกแบบระบบ ERP ของโรงพยาบาลวชิระภูเก็ตตามที่พัฒนาและติดตั้งใช้งานจริงบน Odoo 18 "
              "(As-Built) โดยจัดทำย้อนหลังจากซอร์สโค้ด เอกสาร Workflow/Dataflow และประวัติการพัฒนา เพื่อใช้เป็น")
    for t in ["เอกสารอ้างอิงสำหรับทีมพัฒนาและผู้ดูแลระบบในการบำรุงรักษา แก้ไข และต่อยอดระบบ",
              "เอกสารประกอบการตรวจรับงาน การทดสอบ UAT และการส่งมอบระบบ",
              "ข้อมูลตั้งต้นให้ผู้ใช้งานหลักเข้าใจขอบเขต กระบวนการ และความเชื่อมโยงระหว่างระบบงาน"]:
        bullet(doc, t)
    heading(doc, "1.2 ขอบเขต", 2)
    para(doc, f"ครอบคลุมโมดูลที่พัฒนาเพิ่มเติม (custom) จำนวน {len(mods)} โมดูล (ขึ้นต้นด้วย vpk_) "
              f"ซึ่งสร้างแบบจำลองข้อมูลใหม่ {tot_models} โมเดล มี API endpoint {tot_routes} รายการ "
              f"และโค้ด Python ประมาณ {tot_loc:,} บรรทัด จัดเป็น {len(DOMAINS)} กลุ่มระบบงาน รวมถึงโมดูลมาตรฐานของ Odoo "
              "และโมดูล OCA ที่ระบบพึ่งพา (อธิบายในระดับการใช้งานเท่านั้น)")
    heading(doc, "1.3 เอกสารอ้างอิง", 2)
    for t in ["docs/dataflow.md และไฟล์ Workflow-Dataflow-*.pptx (งบประมาณ จัดซื้อ คลัง ทรัพย์สิน ซ่อมบำรุง เจ้าหนี้-การเงิน-บัญชี)",
              "docs/*_dataflow_data.py: ข้อมูล Input / Process / Output ของแต่ละฟังก์ชัน (แหล่งข้อมูลของบทที่ 5)",
              "คู่มือการใช้งานรายระบบ ใน docs/ERP-Vachiraphuket/คู่มือERP-Vachiraphuket",
              "แผนการทดสอบ UAT: docs/UAT-งบประมาณ-แผนการทดสอบ.md, docs/UAT-จัดซื้อคลัง-แผนการทดสอบ.md",
              "DEVELOPMENT.md และ odoo18vpk-docker/docker/README.md (การติดตั้งและการพัฒนา)"]:
        bullet(doc, t)
    heading(doc, "1.4 คำศัพท์และคำย่อ", 2)
    table(doc, ["คำ", "ความหมาย"], [
        ["PR / PO", "ใบขอซื้อ-ขอจ้าง (purchase.request) / ใบสั่งซื้อ-สั่งจ้าง (purchase.order)"],
        ["e-GP", "ระบบการจัดซื้อจัดจ้างภาครัฐของกรมบัญชีกลาง"],
        ["e-bidding / เฉพาะเจาะจง", "วิธีจัดซื้อจัดจ้างตาม พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560"],
        ["สัญญาไม่จำกัดจำนวน (Call-off)", "สัญญาราคาต่อหน่วยที่สั่งซื้อเป็นงวดตามความต้องการ โดยตัดวงเงิน/ปริมาณคงเหลือของสัญญา"],
        ["GFMIS", "ระบบบริหารการเงินการคลังภาครัฐแบบอิเล็กทรอนิกส์ (New GFMIS Thai)"],
        ["ขบ.01 / ขบ.11", "แบบใบขอเบิกเงิน / ใบสำคัญจ่ายตามแบบของกรมบัญชีกลาง"],
        ["WHT / แบบ 4235", "ภาษีหัก ณ ที่จ่าย / หนังสือรับรองการหักภาษี ณ ที่จ่ายสำหรับส่วนราชการ"],
        ["HIS", "Hospital Information System ระบบสารสนเทศโรงพยาบาล"],
        ["Tier Validation", "กลไกอนุมัติหลายระดับตามลำดับ (OCA base_tier_validation + vpk_tier_validation)"],
        ["Document Studio", "เครื่องมือสร้างแบบฟอร์มเอกสาร Word/PDF จากข้อมูลในระบบ (vpk_document_studio)"],
        ["UAT", "User Acceptance Test การทดสอบเพื่อยอมรับระบบโดยผู้ใช้"],
        ["FEFO", "First Expired, First Out จ่ายสินค้าที่หมดอายุก่อนออกก่อน"],
    ], [5.0, 12.0])

    # ---------- 2. ภาพรวม ----------
    page_break(doc)
    heading(doc, "2. ภาพรวมระบบ", 1)
    heading(doc, "2.1 ระบบงานและขอบเขตการทำงาน", 2)
    para(doc, "ระบบแบ่งเป็นกลุ่มระบบงานดังนี้ (จำนวนโมดูล/โมเดลนับจากโค้ด)")
    rows = []
    for k, (title, ms) in DOMAINS.items():
        rows.append([title, DOMAIN_INTRO.get(k, ""), str(len(ms)),
                     str(sum(len(mods[m]["new"]) for m in ms))])
    table(doc, ["ระบบงาน", "ขอบเขตการทำงาน", "โมดูล", "โมเดลใหม่"], rows, [3.8, 10.4, 1.4, 1.4], size=13)

    heading(doc, "2.2 ภาพรวมกระแสงานหลักแบบครบวงจร", 2)
    para(doc, "กระแสงานหลักของระบบเชื่อมต่อกันตั้งแต่การตั้งงบประมาณจนถึงการจ่ายเงินและบันทึกบัญชี ดังนี้")
    flow = [
        ("งบประมาณ", "หน่วยงานส่งคำของบ → งานงบพิจารณา/จัดสรร → อนุมัติสร้าง budget.lines ในแผนประจำปี"),
        ("แผนจัดซื้อ", "พัสดุทำแผนจัดซื้อประจำปีผูกรายการงบ ระบบสร้าง PR อัตโนมัติจากจุดสั่งซื้อ/สัญญาใกล้หมด"),
        ("ใบขอซื้อ (PR)", "หน่วยงานสร้าง PR เลือกแผนงบ → ตรวจและจองงบ → อนุมัติตามลำดับ → ส่งจัดซื้อ"),
        ("งานพัสดุ / e-GP", "หัวหน้าพัสดุมอบหมายงาน → แต่งตั้งกรรมการ → เอกสารรายงานขอซื้อ → บันทึกผล e-GP และผู้ชนะ"),
        ("PO / สัญญา", "สร้าง PO หรือทะเบียนสัญญา (รวม call-off) → ผู้ขายยืนยันผ่าน Portal/แอป → ผูกพันงบ"),
        ("ตรวจรับ / คลัง", "ของมาส่ง → QC → กรรมการตรวจรับ → รับเข้าคลัง (ล็อต/วันหมดอายุ) → เบิกจ่ายให้หน่วยงาน"),
        ("ทรัพย์สิน", "ครุภัณฑ์ขึ้นทะเบียนสินทรัพย์ → ค่าเสื่อม → โอน/จำหน่าย/ตรวจนับ → ซ่อมบำรุง"),
        ("เจ้าหนี้ / การเงิน", "ขออนุมัติเบิกจ่าย → ตั้งเจ้าหนี้ + ภาษีหัก ณ ที่จ่าย → ขบ.01/GFMIS → ใบสำคัญจ่าย → เช็ค/โอน"),
        ("บัญชี", "ลงบัญชีอัตโนมัติ รายได้จาก HIS เงินเดือนจาก HR บัญชีคุมเงินฝาก และงบแสดงฐานะการเงิน"),
    ]
    table(doc, ["ขั้น", "ระบบงาน", "สาระสำคัญ"],
          [[str(i + 1), a, b] for i, (a, b) in enumerate(flow)], [1.2, 3.5, 12.3])

    heading(doc, "2.3 กลุ่มผู้ใช้งาน", 2)
    table(doc, ["กลุ่มผู้ใช้", "บทบาทหลักในระบบ"], [
        ["หน่วยงาน / กลุ่มงาน", "จัดทำคำของบ ใบขอซื้อ ขอเบิกวัสดุ แจ้งซ่อม รับโอนทรัพย์สิน ตรวจนับ"],
        ["หัวหน้ากลุ่มงาน / ผู้อนุมัติ", "อนุมัติเอกสารตามลำดับชั้นผ่าน Tier Validation หรือแอปมือถือ"],
        ["งานงบประมาณ", "ตั้งค่าข้อมูลหลักงบ พิจารณา จัดสรร อนุมัติ และติดตามการใช้งบ"],
        ["งานพัสดุ / จัดซื้อ", "แผนจัดซื้อ รับงาน PR งาน e-GP สัญญา คณะกรรมการ ใบสั่งซื้อ ขออนุมัติเบิกจ่าย"],
        ["คลังสินค้า / เภสัชกรรม", "รับสินค้า QC จ่าย โอน ปรับยอด ควบคุมยาเสพติด ผลิตยา"],
        ["งานทรัพย์สิน", "ทะเบียนสินทรัพย์ โอน จำหน่าย ตรวจนับประจำปี"],
        ["ช่างซ่อมบำรุง", "รับงานซ่อม ประเมิน เบิกอะไหล่ ปิดงาน"],
        ["เจ้าหนี้ / การเงิน / บัญชี", "ตั้งหนี้ ภาษี ทำจ่าย GFMIS เช็ค บัญชีทั่วไป รายงานการเงิน"],
        ["ผู้ขาย (ภายนอก)", "ลงทะเบียน ยืนยัน PO ส่งเอกสารการค้าผ่าน Portal / แอป"],
        ["ผู้บริหาร", "Dashboard งบประมาณ จัดซื้อ การเงิน และความเห็นบนเอกสาร"],
        ["ผู้ดูแลระบบ", "ตั้งค่า สิทธิ์ แม่แบบเอกสาร นำเข้าข้อมูล ล้างข้อมูลทดสอบ"],
    ], [5.0, 12.0])

    heading(doc, "2.4 หลักการออกแบบ", 2)
    for t in [
        "ต่อยอดจากโมดูลมาตรฐาน Odoo และ OCA (purchase_request, base_tier_validation, base_account_budget ฯลฯ) "
        "โดยใช้ _inherit แทนการแก้ไขโค้ดต้นฉบับ เพื่อให้อัปเกรดได้",
        "แยกโมดูลตามความรับผิดชอบ (หนึ่งเรื่องหนึ่งโมดูล) เปิด/ปิดได้อิสระ และระบุ depends ชัดเจน",
        "ใช้เส้นทางอนุมัติกลาง (vpk_tier_validation) ร่วมกันทุกเอกสาร ทั้ง PR, PO, ใบแจ้งหนี้, คลัง, ทรัพย์สิน",
        "รองรับระเบียบราชการไทย: ปีงบประมาณ ต.ค.-ก.ย., วันที่ พ.ศ., เอกสารตามแบบกรมบัญชีกลาง, เลขสารบรรณ, e-GP, GFMIS",
        "ควบคุมงบประมาณแบบเรียลไทม์: ตรวจ/จองงบตั้งแต่ PR, ผูกพันเมื่อ PO/สัญญา, ใช้จริงเมื่อตั้งหนี้",
        "เอกสารราชการสร้างจากแม่แบบ Word ที่ผู้ใช้แก้ไขเองได้ (Document Studio + ONLYOFFICE) แทนการเขียน QWeb ทุกฉบับ",
        "เชื่อมระบบภายนอกผ่าน REST API และคิว staging (HIS, HR) เพื่อให้ตรวจสอบก่อนลงบัญชีได้",
        "ส่วนติดต่อผู้ใช้ภาษาไทยทั้งระบบ เมนูแถบข้าง และแอปมือถือสำหรับงานภาคสนาม (อนุมัติ ผู้ขาย สแกนบาร์โค้ด ซ่อมบำรุง)",
    ]:
        bullet(doc, t)

    # ---------- 3. สถาปัตยกรรม ----------
    page_break(doc)
    heading(doc, "3. สถาปัตยกรรมระบบ", 1)
    heading(doc, "3.1 เทคโนโลยีที่ใช้", 2)
    table(doc, ["องค์ประกอบ", "รายละเอียด"], [
        ["Application Server", "Odoo 18.0 Community (Python 3) รันผ่าน odoo-bin, proxy_mode = True, max_cron_threads = 1"],
        ["ฐานข้อมูล", "PostgreSQL 16 ฐานข้อมูลหลัก VPK-S1"],
        ["Document Server", "ONLYOFFICE Document Server 8.3 (JWT) สำหรับแก้ไข Word และแปลง PDF พร้อมฟอนต์ไทย TH Sarabun"],
        ["Web Client", "Odoo Web (OWL) + Asset JS/SCSS ของโมดูล vpk_* (sidebar, dashboard, barcode, PDF preview)"],
        ["รายงาน", "QWeb PDF (wkhtmltopdf), report_xlsx และแม่แบบ Word/Excel (Document Studio, ขบ.01)"],
        ["การติดตั้ง", "Production: /opt/odoo18vpk + /etc/odoo18vpk.conf | Local/UAT: Docker Compose (db, odoo, onlyoffice)"],
        ["ระบบควบคุมเวอร์ชัน", "Git (GitHub: odoo18vpk) branch main"],
    ], [4.0, 13.0])

    heading(doc, "3.2 สถาปัตยกรรมเชิงชั้น (Layered Architecture)", 2)
    table(doc, ["ชั้น", "องค์ประกอบ"], [
        ["ช่องทางผู้ใช้", "Odoo Web Client · Vendor Portal (/vendor) · แอปมือถืออนุมัติ · แอปผู้ขาย · แอปสแกนบาร์โค้ด · แอปแจ้งซ่อม"],
        ["API / Controller", "REST/JSON endpoint ใน vpk_approval_api, vpk_vendor_api, vpk_his_api, vpk_hr_payroll_api, "
                             "vpk_mobile_barcode, vpk_purchase_portal_egp, vpk_asset_inventory ฯลฯ"],
        ["Business Logic (custom)", f"{len(mods)} โมดูล vpk_* แบ่ง {len(DOMAINS)} กลุ่มระบบงาน (บทที่ 4)"],
        ["Business Logic (OCA/3rd party)", "purchase_request, base_tier_validation, l10n_th_*, base_accounting_kit, report_xlsx ฯลฯ"],
        ["Odoo Framework", "ORM, Security (groups / record rules), Workflow (state/statusbar), Cron, Mail/Activity, QWeb"],
        ["ข้อมูล", "PostgreSQL 16 + Filestore (ไฟล์แนบ เอกสาร PDF/Word)"],
    ], [4.5, 12.5])

    heading(doc, "3.3 ชั้นของโมดูล (addons_path)", 2)
    table(doc, ["ชุดโมดูล", "แหล่งที่มา", "การใช้งานในระบบ"], [list(x) for x in OCA_LAYERS], [6.0, 3.0, 8.0])

    heading(doc, "3.4 การเชื่อมต่อระบบภายนอก", 2)
    table(doc, ["ระบบภายนอก", "โมดูล", "รูปแบบ", "ข้อมูลที่แลกเปลี่ยน"], [list(x) for x in EXTERNAL],
          [3.8, 4.2, 3.2, 5.8])

    heading(doc, "3.5 สภาพแวดล้อมการติดตั้ง", 2)
    table(doc, ["สภาพแวดล้อม", "รายละเอียด"], [
        ["Production / UAT Server", "โค้ดที่ /opt/odoo18vpk, venv ที่ /opt/odoo18vpk/odoo18vpk-venv, config /etc/odoo18vpk.conf, "
                                    "log /var/log/odoo18vpk/odoo18vpk.log, port 8769"],
        ["Local (Docker)", "odoo18vpk-docker/docker-compose.yml: services db (postgres:16), odoo (port 8069), "
                           "onlyoffice (port 8080); mount VPK_S1 สำหรับ restore dump และ filestore"],
        ["การอัปเกรดโมดูล", "odoo-bin -c /etc/odoo18vpk.conf -d VPK-S1 -u <module> --stop-after-init แล้ว restart และ hard refresh"],
    ], [4.0, 13.0])

    # ---------- 4. โครงสร้างโมดูล ----------
    page_break(doc)
    heading(doc, "4. โครงสร้างโมดูล", 1)
    para(doc, "ตารางต่อไปนี้แสดงโมดูล custom แยกตามระบบงาน พร้อมหน้าที่และโมดูลที่ต้องพึ่งพา "
              "(แสดงเฉพาะ depends ที่เป็น vpk_* และโมดูลหลัก) ข้อมูลอ่านจาก __manifest__.py")
    for i, (k, (title, ms)) in enumerate(DOMAINS.items(), 1):
        heading(doc, f"4.{i} {title}", 2)
        rows = []
        for m in ms:
            d = mods[m]
            deps = [x for x in d["depends"] if x.startswith("vpk_")]
            core = [x for x in d["depends"] if not x.startswith("vpk_")]
            dep_txt = ", ".join(deps) if deps else "-"
            rows.append([f"{m}\n{d['name']}", d["summary"] or "-",
                         f"vpk: {dep_txt}\nอื่น: {', '.join(core[:6])}{' …' if len(core) > 6 else ''}"])
        table(doc, ["โมดูล", "หน้าที่", "Depends"], rows, [5.0, 7.0, 5.0], size=12, head_size=13)

    heading(doc, f"4.{len(DOMAINS) + 1} ความสัมพันธ์ระหว่างโมดูล custom", 2)
    para(doc, "รายการด้านล่างแสดงว่าโมดูลใดถูกโมดูล vpk_* อื่นพึ่งพา (เป็นฐานของโมดูลอื่น) เรียงตามจำนวนที่ถูกพึ่งพา "
              "ช่วยประเมินผลกระทบเมื่อแก้ไขหรืออัปเกรดโมดูล")
    rev = defaultdict(list)
    for m, d in mods.items():
        for x in d["depends"]:
            if x in mods:
                rev[x].append(m)
    rows = [[k, str(len(v)), ", ".join(sorted(v))] for k, v in sorted(rev.items(), key=lambda kv: -len(kv[1]))]
    table(doc, ["โมดูลฐาน", "จำนวน", "โมดูลที่พึ่งพา"], rows, [5.0, 1.6, 10.4], size=12)

    # ---------- 5. การออกแบบระบบงาน (landscape) ----------
    sec = new_section(doc, landscape=True)
    sec.left_margin = sec.right_margin = Cm(1.6)
    heading(doc, "5. การออกแบบกระบวนการทำงานรายระบบ", 1)
    para(doc, "บทนี้อธิบายกระบวนการ (Workflow) และฟังก์ชันของแต่ละระบบงานในรูปแบบ Input / Process / Output "
              "พร้อมเมนูและโมเดล/เมธอดที่เกี่ยวข้อง เพื่อใช้อ้างอิงระหว่างเอกสารกับโค้ด")
    sub = 0
    for k, (title, ms) in DOMAINS.items():
        data = DOMAIN_DATA.get(k)
        if not data:
            continue
        sub += 1
        heading(doc, f"5.{sub} {title}", 2)
        para(doc, DOMAIN_INTRO.get(k, ""))
        para(doc, "ขั้นตอนหลัก (Phase)", 15, True, NAVY, after=2)
        table(doc, ["Phase", "ชื่อขั้นตอน", "สาระสำคัญ"], [list(p) for p in data.PHASES], [1.6, 6.0, 18.9])
        phase_name = {p[0]: p[1] for p in data.PHASES}
        cur = None
        for f in data.FUNCTIONS:
            if f["phase"] != cur:
                cur = f["phase"]
                heading(doc, f"Phase {cur}: {phase_name.get(cur, '')}", 3)
                rows = []
            rows.append([
                f["code"], f"{f['name']}\n(ผู้ใช้: {f.get('actor', '')})",
                ["• " + x for x in f.get("inputs", [])],
                ["› " + x for x in f.get("process", [])],
                ["• " + x for x in f.get("outputs", [])],
                f"{f.get('menu', '')}\n{f.get('tech', '')}",
            ])
            nxt = data.FUNCTIONS.index(f) + 1
            if nxt >= len(data.FUNCTIONS) or data.FUNCTIONS[nxt]["phase"] != cur:
                table(doc, ["รหัส", "ฟังก์ชัน", "Input", "Process", "Output", "เมนู / Model · Method"], rows,
                      [1.3, 3.8, 5.3, 4.6, 5.3, 6.2], size=11, head_size=12)
        integ = getattr(data, "INTEGRATION", None)
        if integ:
            heading(doc, "จุดเชื่อมต่อกับระบบอื่น (Integration)", 3)
            rows = [[x["code"], f"{x['name']}\n{x['frm']} → {x['to']}",
                     ["• " + i for i in x.get("inputs", [])], ["• " + o for o in x.get("outputs", [])],
                     x.get("trigger", ""), x.get("tech", "")] for x in integ]
            table(doc, ["รหัส", "การเชื่อมต่อ", "ข้อมูลเข้า", "ผลลัพธ์", "จังหวะที่เกิด", "เทคนิค"], rows,
                  [1.3, 4.6, 5.0, 5.4, 3.7, 6.5], size=11, head_size=12)
        if k == "PRO" and getattr(data, "CONTRACT_COMPARE", None):
            heading(doc, "เปรียบเทียบรูปแบบสัญญา", 3)
            cc = data.CONTRACT_COMPARE
            if cc and isinstance(cc[0], (list, tuple)):
                n = len(cc[0])
                hdr = ["หัวข้อ"] + [f"แบบที่ {i}" for i in range(1, n)]
                if n == 3:
                    hdr = ["หัวข้อ", "สัญญาจำกัดจำนวน", "สัญญาไม่จำกัดจำนวน (call-off)"]
                table(doc, hdr, [list(map(str, r)) for r in cc], [6.0] + [20.5 / (n - 1)] * (n - 1), size=12)

    # ระบบที่ไม่มีไฟล์ dataflow: สรุปจาก manifest
    for k in ("VEN", "DOC", "PLT"):
        title, ms = DOMAINS[k]
        sub += 1
        heading(doc, f"5.{sub} {title}", 2)
        para(doc, DOMAIN_INTRO[k])
        rows = []
        for m in ms:
            d = mods[m]
            rows.append([f"{m}\n{d['name']}", d["summary"] or "-",
                         ", ".join(x["name"] for x in d["new"]) or "-",
                         ", ".join(d["ext"]) or "-"])
        table(doc, ["โมดูล", "ฟังก์ชันหลัก", "โมเดลที่สร้างใหม่", "ต่อยอดโมเดลเดิม"], rows,
              [5.0, 8.0, 7.0, 6.5], size=11, head_size=12)
    heading(doc, "กลไกการอนุมัติตามลำดับ (vpk_tier_validation)", 3)
    for t in [
        "ต่อยอด OCA base_tier_validation ให้อนุมัติเป็นลำดับ (sequential) ผู้อนุมัติคนถัดไปเห็นงานเมื่อคนก่อนหน้าอนุมัติแล้ว",
        "ใช้กับ purchase.request (เพิ่มสถานะและบันทึกข้อความ PR), account.move (ใบแจ้งหนี้), เอกสารคลัง ทรัพย์สิน และเอกสาร Document Studio",
        "ตั้งค่าที่บริษัท (res.company) และผู้ใช้ (res.users) เช่น ผู้อนุมัติแทน ลำดับขั้น และแสดงตารางผู้อนุมัติบนรายงาน PDF (ir.actions.report)",
        "เปิดให้แอปมือถือดึงงานรออนุมัติและอนุมัติ/ตีกลับผ่าน vpk_approval_api",
        "เมื่อ PR ไม่ผ่านอนุมัติ vpk_purchase_request_reject_notify แจ้งผู้ขอและกลุ่มงาน; PR เร่งด่วนใช้เส้นทางอนุมัติเร่งด่วน (vpk_purchase_request_urgent)",
    ]:
        bullet(doc, t)

    # ---------- 6. แบบจำลองข้อมูล ----------
    sec = new_section(doc, landscape=False)
    sec.left_margin = sec.right_margin = Cm(2.0)
    heading(doc, "6. แบบจำลองข้อมูล (Data Model)", 1)
    para(doc, f"ระบบสร้างโมเดลใหม่ {tot_models} โมเดล และต่อยอด (_inherit) โมเดลมาตรฐาน ตารางนี้สร้างจากการอ่านคลาสในโค้ด "
              "(ประเภท: Model = ตารางถาวร, Transient = Wizard/ข้อมูลชั่วคราว, Abstract = Mixin) จำนวนฟิลด์นับเฉพาะฟิลด์ที่ประกาศในคลาสนั้น")
    heading(doc, "6.1 โมเดลมาตรฐานที่ถูกต่อยอดมากที่สุด", 2)
    ext_cnt = defaultdict(list)
    for m, d in mods.items():
        for x in d["ext"]:
            ext_cnt[x].append(m)
    rows = [[x, str(len(v)), ", ".join(sorted(v))]
            for x, v in sorted(ext_cnt.items(), key=lambda kv: -len(kv[1]))[:25]]
    table(doc, ["โมเดล", "จำนวนโมดูล", "โมดูลที่ต่อยอด"], rows, [4.5, 2.0, 10.5], size=12)
    for i, (k, (title, ms)) in enumerate(DOMAINS.items(), 2):
        rows = []
        for m in ms:
            for x in mods[m]["new"]:
                rows.append([x["name"], x["desc"] or "-", x["kind"], str(x["fields"]), m])
        if not rows:
            continue
        heading(doc, f"6.{i} {title}", 2)
        table(doc, ["โมเดล (_name)", "คำอธิบาย", "ประเภท", "ฟิลด์", "โมดูล"], rows,
              [5.2, 5.3, 1.9, 1.2, 3.4], size=11, head_size=12)

    # ---------- 7. ความปลอดภัย ----------
    page_break(doc)
    heading(doc, "7. ความปลอดภัยและสิทธิ์การใช้งาน", 1)
    heading(doc, "7.1 แนวทาง", 2)
    for t in [
        "ควบคุมสิทธิ์ด้วยกลุ่มผู้ใช้ (res.groups) และ Access Rights (ir.model.access.csv) ของแต่ละโมดูล",
        "Record Rules จำกัดการมองเห็นตามหน่วยงาน/ผู้สร้าง (เช่น คำของบของหน่วยงาน ผู้ตรวจนับเฉพาะหน่วยงานตนเอง)",
        "สิทธิ์ข้อมูลผู้จำหน่ายแยก Viewer / Editor / Administrator (vpk_vendor_security) และตรวจข้อมูลซ้ำ (Tax ID ชื่อ เบอร์โทร อีเมล)",
        "พื้นที่จัดเก็บยาเสพติด/ยาความเสี่ยงสูงเข้าถึงได้เฉพาะกลุ่ม Narcotic / High-Alert Location Access (vpk_stock_location)",
        "API ภายนอกใช้ auth แบบ user/token ตาม endpoint; Portal ผู้ขายเห็นเฉพาะ PO ของตนเอง",
        "ONLYOFFICE ใช้ JWT ในการรับส่งเอกสาร",
    ]:
        bullet(doc, t)
    heading(doc, "7.2 กลุ่มผู้ใช้ที่กำหนดในโมดูล custom", 2)
    rows = [[m, ["• " + g for g in d["groups"]]] for m, d in mods.items() if d["groups"]]
    table(doc, ["โมดูล", "กลุ่มผู้ใช้ (res.groups)"], rows, [5.5, 11.5], size=12)

    # ---------- 8. API ----------
    heading(doc, "8. ส่วนเชื่อมต่อโปรแกรม (API / Web Routes)", 1)
    para(doc, "รายการ HTTP/JSON route ที่โมดูล custom เปิดไว้ (อ่านจาก @http.route ใน controllers)")
    rows = []
    for m, d in mods.items():
        for r in d["routes"]:
            rows.append([m, r["url"], r["type"], r["auth"], r["methods"] or "-"])
    table(doc, ["โมดูล", "Route", "ชนิด", "auth", "Method"], rows, [3.8, 8.2, 1.5, 1.7, 1.8], size=11, head_size=12)

    # ---------- 9. งานอัตโนมัติ และรายงาน ----------
    heading(doc, "9. งานอัตโนมัติ รายงาน และแบบพิมพ์", 1)
    heading(doc, "9.1 งานตั้งเวลา (Scheduled Actions)", 2)
    rows = [[m, n, iv] for m, d in mods.items() for (n, iv) in d["crons"]]
    if rows:
        table(doc, ["โมดูล", "ชื่องาน", "รอบการทำงาน"], rows, [5.0, 8.5, 3.5], size=12)
    else:
        para(doc, "-")
    heading(doc, "9.2 รายงานและแบบพิมพ์ (ir.actions.report)", 2)
    rows = [[m, n, mdl, t] for m, d in mods.items() for (n, mdl, t) in d["reports"]]
    table(doc, ["โมดูล", "ชื่อรายงาน", "โมเดล", "ชนิด"], rows, [4.5, 6.0, 4.5, 2.0], size=11, head_size=12)
    heading(doc, "9.3 เอกสารที่สร้างจากแม่แบบ Word/Excel", 2)
    for t in [
        "Document Studio: แบบฟอร์มที่ผู้ใช้กำหนดฟิลด์และ block เอง ผูกกับโมเดลต้นทาง (PR, สัญญา, คณะกรรมการ) พิมพ์เป็น Word/PDF",
        "เอกสารจัดซื้อจัดจ้าง: คำสั่งแต่งตั้งคณะกรรมการ รายงานขอซื้อขอจ้าง รายงานผลการพิจารณา ประกาศผู้ชนะ ใบตรวจรับ",
        "หนังสือราชการ (vpk_official_document) พร้อมเลขสารบรรณ และส่งลงนามบน PDF (vpk_document_studio_sign)",
        "ใบขอเบิกเงิน ขบ.01 / ขบ.11 กรอกลง template Excel อัตโนมัติ (vpk_disbursement_form)",
        "เช็ค: กำหนดตำแหน่งพิมพ์บนแบบฟอร์มเช็คได้เอง (vpk_cheque_management)",
    ]:
        bullet(doc, t)

    # ---------- 10. การทดสอบ ติดตั้ง ----------
    heading(doc, "10. การทดสอบ การนำเข้าข้อมูล และการบำรุงรักษา", 1)
    heading(doc, "10.1 การทดสอบ", 2)
    for t in [
        "UAT รายระบบตามแผนใน docs/UAT-*-แผนการทดสอบ.md และใบบันทึกผล .xlsx (งบประมาณ จัดซื้อ-คลัง นำเข้าข้อมูล)",
        "สคริปต์ทดสอบอัตโนมัติด้วย Playwright ใน scripts/playwright (เช่น flow ใบขอซื้อ e-GP) ใช้ผ่าน agent odoo-tester",
        "ข้อมูลทดสอบและผู้ใช้ทดสอบรายกลุ่ม (จัดซื้อ เภสัชกรรม) และเครื่องมือล้างข้อมูลตามโมดูล (vpk_data_cleaner)",
    ]:
        bullet(doc, t)
    heading(doc, "10.2 การนำเข้าข้อมูล (Data Migration)", 2)
    for t in [
        "แม่แบบ Excel สำหรับข้อมูลหลักและยกยอด: คลัง สินค้า หน่วยนับ ผู้จำหน่าย (vpk_master_data_templates)",
        "นำเข้าสินค้า/ยา-เวชภัณฑ์ (vpk_product_import) และข้อมูลหลักงบประมาณ (Import Budget Master)",
        "นำเข้าเจ้าหนี้คงค้างและตรวจผู้จำหน่ายซ้ำ ตามไฟล์ UAT-นำเข้าข้อมูล-*.xlsx",
    ]:
        bullet(doc, t)
    heading(doc, "10.3 แนวทางการบำรุงรักษาและพัฒนาต่อ", 2)
    for t in [
        "แก้ไขโค้ดในโมดูล vpk_* เท่านั้น ห้ามแก้ odoo18/addons หรือโมดูล OCA โดยตรง",
        "เพิ่ม version ใน __manifest__.py และเขียน migration เมื่อเปลี่ยนโครงสร้างข้อมูล",
        "ตรวจผลกระทบจากตาราง 'ความสัมพันธ์ระหว่างโมดูล' (หัวข้อ 4) ก่อนแก้โมดูลฐาน เช่น vpk_budget, vpk_tier_validation",
        "อัปเดตไฟล์ docs/*_dataflow_data.py เมื่อ workflow เปลี่ยน แล้วรันสคริปต์สร้างเอกสารนี้ใหม่",
    ]:
        bullet(doc, t)

    # ---------- ภาคผนวก ----------
    sec = new_section(doc, landscape=False)
    heading(doc, "ภาคผนวก ก: รายชื่อโมดูล custom ทั้งหมด", 1)
    rows = []
    for m, d in mods.items():
        rows.append([m, d["name"], DOMAINS[dom_of[m]][0], d["version"], str(len(d["new"])),
                     str(len(d["routes"])), f"{d['loc']:,}"])
    table(doc, ["โมดูล", "ชื่อ", "ระบบงาน", "เวอร์ชัน", "โมเดล", "API", "บรรทัด"], rows,
          [4.3, 4.6, 3.3, 1.9, 1.1, 0.9, 1.4], size=11, head_size=12)

    heading(doc, "ภาคผนวก ข: ประวัติการพัฒนา (จาก Git)", 1)
    if hist:
        para(doc, f"ช่วงเวลา: {hist[0][0]} ถึง {hist[-1][0]} รวม {len(hist)} commit")
        table(doc, ["วันที่", "รายละเอียดการเปลี่ยนแปลง"], [[a, b] for a, b in hist], [2.6, 14.4], size=11,
              head_size=12)

    for s in doc.sections:
        add_page_number_footer(s, "เอกสารออกแบบระบบ VPK ERP (Odoo 18)")
        if s.orientation != WD_ORIENT.LANDSCAPE:
            s.left_margin = s.right_margin = Cm(2.0)
        s.top_margin = s.bottom_margin = Cm(1.8)

    doc.core_properties.title = "เอกสารออกแบบระบบ VPK ERP (Odoo 18)"
    doc.core_properties.subject = "System Design Document (As-Built)"
    doc.save(OUT)
    print(f"saved {OUT}  modules={len(mods)} models={tot_models} routes={tot_routes} leftovers={leftovers}")


if __name__ == "__main__":
    build()
