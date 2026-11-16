#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Excel template for pharmacy opening-stock quantities."""

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent
DRUG_SOURCE = ROOT / "UAT-Data-Migrate" / "คลังสินค้า" / "ข้อมูลยาที่ นำเข้าระบบ.xlsx"
OUT_DIR = ROOT / "UAT-Data-Migrate" / "คลังสินค้า"
OUT = OUT_DIR / "template-ยกยอดสต็อก-ยา.xlsx"
OUT_COPY = ROOT / "template-ยกยอดสต็อก-ยา.xlsx"

NAVY = "1F4E79"
NAVY_FILL = PatternFill("solid", fgColor=NAVY)
HINT_FILL = PatternFill("solid", fgColor="E8F1FA")
YELLOW = PatternFill("solid", fgColor="FFF2CC")
GREEN = PatternFill("solid", fgColor="E2EFDA")
WHITE = PatternFill("solid", fgColor="FFFFFF")
THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
FONT = "Prompt"
FONT_TH = Font(name=FONT, size=9, bold=True, color=NAVY)
FONT_EN = Font(name=FONT, size=10, bold=True, color="FFFFFF")
FONT_EX = Font(name=FONT, size=10, color="7A4E00")
FONT_BODY = Font(name=FONT, size=11, color="1E293B")
FONT_TITLE = Font(name=FONT, size=16, bold=True, color=NAVY)
FONT_SUB = Font(name=FONT, size=11, color="475569")
WRAP = Alignment(wrap_text=True, vertical="center")
LEFT = Alignment(vertical="center")

COLUMNS = [
    ("ลำดับ ใส่เลขรันได้ ระบบไม่ใช้คีย์", "sequence", 10, "optional"),
    ("รหัสสินค้าภายใน ต้องตรง item master ห้ามว่าง", "product_id/default_code", 18, "required"),
    ("ชื่อยา ใส่เพื่อตรวจทาน ไม่ใช้เป็นคีย์นำเข้า", "name", 42, "helper"),
    ("หน่วยนับที่ใช้เก็บสต็อก ตรวจทานให้ตรงสินค้า", "uom", 12, "helper"),
    ("รหัสคลัง PHAR = คลังยา  UNIT = คลังยาหน่วยงาน", "warehouse_code", 14, "helper"),
    ("ตำแหน่งจัดเก็บแบบ path เต็ม เช่น PHAR/Stock หรือ PHAR/Stock/Aa1", "location_id/complete_name", 28, "required"),
    ("จำนวนยกยอด ตามหน่วยนับของสินค้า", "inventory_quantity", 14, "required"),
    ("เลขล็อต ยาต้องระบุล็อต หนึ่งแถวต่อหนึ่งล็อต", "lot_id/name", 18, "required"),
    ("วันหมดอายุ รูปแบบ YYYY-MM-DD", "lot_id/expiration_date", 18, "required"),
    ("วันผลิต ถ้าระบบเดิมมี รูปแบบ YYYY-MM-DD เว้นว่างได้", "lot_id/use_date", 16, "optional"),
    ("วันที่ยกยอด วันที่นับสต็อกเปิดระบบ YYYY-MM-DD", "inventory_date", 16, "optional"),
    ("ต้นทุนต่อหน่วย ถ้ายกยอดมูลค่าสต็อกด้วย เว้นว่างได้", "standard_price", 14, "optional"),
    ("หมายเหตุ", "note", 24, "optional"),
]

EXAMPLE = [
    1,
    "00005",
    "SIMETHICONE 80 MG TAB.",
    "เม็ด",
    "PHAR",
    "PHAR/Stock",
    120,
    "LOT-2025-001",
    "2027-12-31",
    "2025-01-15",
    "2026-10-01",
    0.50,
    "แถวตัวอย่าง ลบก่อนนำเข้า",
]


def style_cell(cell, fill, font, align=WRAP):
    cell.fill = fill
    cell.font = font
    cell.alignment = align
    cell.border = THIN


def load_drugs():
    rows = []
    if not DRUG_SOURCE.exists():
        return rows
    wb = load_workbook(DRUG_SOURCE, read_only=True, data_only=True)
    ws = wb.active
    header = None
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        vals = list(row)
        if i == 0:
            header = [str(v).strip() if v is not None else "" for v in vals]
            continue
        rec = dict(zip(header, vals))
        code = rec.get("รหัสสินค้า")
        name = rec.get("ชื่อ")
        if not code or not name:
            continue
        rows.append(
            {
                "code": str(code).strip(),
                "name": str(name).strip(),
                "uom": str(rec.get("หน่วยนับ") or "").strip(),
                "categ": str(rec.get("หมวดหมู่") or "").strip(),
            }
        )
    wb.close()
    return rows


def build_manual(ws, drug_count):
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 88
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 36
    ws.merge_cells("A1:D1")
    ws["A1"] = "Template ยกยอดสต็อกยา"
    ws["A1"].font = FONT_TITLE
    ws.merge_cells("A2:D2")
    ws["A2"] = (
        "ใช้กรอกจำนวนคงเหลือยาเพื่อเปิดระบบ  ·  หนึ่งแถวต่อหนึ่งรหัสสินค้า + ตำแหน่ง + ล็อต  ·  "
        "สินค้าต้องมีในระบบแล้วและติดตามล็อตพร้อมวันหมดอายุ"
    )
    ws["A2"].font = FONT_SUB
    ws["A2"].alignment = WRAP
    ws.row_dimensions[2].height = 36

    ws["A4"] = "วิธีกรอก"
    ws["A4"].font = Font(name=FONT, size=12, bold=True, color=NAVY)
    steps = [
        "กรอกในชีต ยกยอดสต็อกยา แถวที่ 1 เป็นคำอธิบายภาษาไทย แถวที่ 2 เป็นชื่อฟิลด์สำหรับนำเข้า แถวที่ 3 สีเหลืองเป็นตัวอย่างให้ลบก่อนนำเข้า กรอกข้อมูลจริงตั้งแต่แถวที่ 4 แถวว่างมีถึงแถว 203 ถ้าไม่พอให้แทรกแถวต่อท้าย",
        "คัดลอกรหัสสินค้าจากชีต รหัสยาในระบบ ให้ตรง default_code ที่นำเข้า item master แล้ว ห้ามพิมพ์รหัสใหม่",
        "ยาต้องระบุเลขล็อตและวันหมดอายุทุกแถว ถ้ามียาเดียวกันหลายล็อต ให้แยกคนละแถว",
        "ตำแหน่งใส่ path เต็ม เช่น PHAR/Stock สำหรับยอดรวมคลังยา หรือ PHAR/Stock/Aa1 ถ้าแยกชั้น ดูตัวอย่างในชีตรายการอ้างอิง",
        "จำนวนยกยอดใส่ตามหน่วยนับของสินค้า (คอลัมน์ uom) ไม่ใช่หน่วยซื้อ",
        "วันหมดอายุและวันที่ยกยอดใช้รูปแบบ YYYY-MM-DD เช่น 2027-12-31",
        "นำเข้าที่สินค้าคงคลัง → สต็อก → อัปเดตจำนวน หรือ Import โมเดล stock.quant โดยจับคู่คอลัมน์จากแถวที่ 2 แล้ว Validate ให้ On Hand ตรงไฟล์",
    ]
    for i, text in enumerate(steps, 1):
        row = 4 + i
        ws.cell(row, 1, i).font = Font(name=FONT, size=11, bold=True, color=NAVY)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        cell = ws.cell(row, 2, text)
        cell.font = FONT_BODY
        cell.alignment = WRAP
        ws.row_dimensions[row].height = 32

    start = 13
    ws.cell(start, 1, "ตรวจหลังกรอก").font = Font(name=FONT, size=12, bold=True, color=NAVY)
    checks = [
        "นับแถวที่มีรหัสสินค้าในคอลัมน์ product_id/default_code ต้องตรงจำนวนล็อตที่ต้องการยกยอด",
        "รวมคอลัมน์ inventory_quantity ด้วย AutoSum แล้วเทียบกับยอดนับจากระบบเดิม",
        "กรองแถวที่ lot_id/name ว่าง ยาห้ามมีแถวไร้ล็อต",
        "กรองแถวที่ lot_id/expiration_date ว่าง หรือวันที่หมดอายุก่อนวันที่ยกยอด",
    ]
    for i, text in enumerate(checks, 1):
        row = start + i
        ws.cell(row, 1, i).font = Font(name=FONT, size=11, bold=True, color=NAVY)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        cell = ws.cell(row, 2, text)
        cell.font = FONT_BODY
        cell.alignment = WRAP
        ws.row_dimensions[row].height = 28

    ws.cell(18, 1, "คอลัมน์ที่ต้องกรอก").font = Font(name=FONT, size=12, bold=True, color=NAVY)
    ws.cell(19, 1, "คอลัมน์")
    ws.cell(19, 2, "ชื่อฟิลด์")
    ws.cell(19, 3, "ต้องกรอก")
    ws.cell(19, 4, "หมายเหตุ")
    for col in range(1, 5):
        style_cell(ws.cell(19, col), NAVY_FILL, FONT_EN, LEFT)
    required_map = {
        "required": "ใช่",
        "helper": "แนะนำ",
        "optional": "ไม่บังคับ",
    }
    for i, (th, en, _w, kind) in enumerate(COLUMNS, 1):
        row = 19 + i
        ws.cell(row, 1, en)
        ws.cell(row, 2, th)
        ws.cell(row, 3, required_map[kind])
        ws.cell(row, 4, "จับคู่ตอน Import stock.quant" if kind == "required" else "ช่วยตรวจทาน ไม่ใช้เป็นคีย์")
        fill = GREEN if kind == "required" else WHITE
        for col in range(1, 5):
            style_cell(ws.cell(row, col), fill, FONT_BODY, WRAP)
        ws.row_dimensions[row].height = 28

    legend_row = 34
    ws.cell(legend_row, 1, "สีในชีต").font = Font(name=FONT, size=12, bold=True, color=NAVY)
    legends = [
        (YELLOW, "เหลือง", "แถวตัวอย่าง ลบก่อนนำเข้า"),
        (GREEN, "เขียว", "คอลัมน์ที่ต้องกรอกบนแถวข้อมูล"),
        (WHITE, "ขาว", "ช่องที่กรอกได้ รวมชื่อยาและหน่วยสำหรับตรวจทาน"),
        (HINT_FILL, "ฟ้าอ่อน", "แถวคำอธิบายภาษาไทย"),
        (NAVY_FILL, "กรมท่า", "แถวชื่อฟิลด์สำหรับนำเข้า"),
    ]
    ws.cell(legend_row + 1, 1, "สี")
    ws.cell(legend_row + 1, 2, "ความหมาย")
    style_cell(ws.cell(legend_row + 1, 1), NAVY_FILL, FONT_EN, LEFT)
    style_cell(ws.cell(legend_row + 1, 2), NAVY_FILL, FONT_EN, LEFT)
    for i, (fill, name, meaning) in enumerate(legends, 1):
        row = legend_row + 1 + i
        style_cell(ws.cell(row, 1), fill, FONT_BODY if name != "กรมท่า" else FONT_EN, LEFT)
        ws.cell(row, 1, name)
        style_cell(ws.cell(row, 2), WHITE, FONT_BODY, LEFT)
        ws.cell(row, 2, meaning)

    ws.cell(42, 1, "สมมติฐาน").font = Font(name=FONT, size=12, bold=True, color=NAVY)
    ws.merge_cells("A43:D45")
    ws["A43"] = (
        f"รหัสยาในชีตอ้างอิงดึงจากไฟล์ ข้อมูลยาที่ นำเข้าระบบ.xlsx จำนวน {drug_count:,} รายการ ณ วันที่จัดทำเทมเพลต "
        "คลังยาหลักคือ PHAR ตำแหน่งรับเข้ามาตรฐานคือ PHAR/Stock คลังยาหน่วยงานใช้ UNIT/Stock "
        "แถวตัวอย่างใช้รหัส 00005 และล็อต LOT-2025-001 เป็นค่าสมมติเพื่อแสดงรูปแบบ ไม่ใช่ยอดจริง "
        "วันที่ยกยอดตัวอย่างเป็น 2026-10-01 ให้เปลี่ยนเป็นวันที่นับสต็อกเปิดระบบที่ตกลงกับงานคลัง "
        "สินค้าต้องเป็น Storable และ tracking = lot ก่อนยกยอด ห้ามยกยอดเข้าตำแหน่งที่ยังไม่มีในระบบ"
    )
    ws["A43"].font = FONT_BODY
    ws["A43"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[43].height = 72


def build_stock_sheet(ws):
    ws.freeze_panes = "C3"
    ws.auto_filter.ref = "A2:M203"
    ws.row_dimensions[1].height = 48
    ws.row_dimensions[2].height = 22

    for i, (th, en, width, kind) in enumerate(COLUMNS, 1):
        letter = get_column_letter(i)
        ws.column_dimensions[letter].width = width
        c1 = ws.cell(1, i, th)
        c2 = ws.cell(2, i, en)
        style_cell(c1, HINT_FILL, FONT_TH)
        style_cell(c2, NAVY_FILL, FONT_EN, LEFT)
        ex = ws.cell(3, i, EXAMPLE[i - 1])
        style_cell(ex, YELLOW, FONT_EX, LEFT)
        if i == 7:
            ex.number_format = "#,##0.00"
        if i == 12:
            ex.number_format = "#,##0.00"

    for row in range(4, 204):
        for i, (_th, _en, _w, kind) in enumerate(COLUMNS, 1):
            cell = ws.cell(row, i)
            fill = GREEN if kind == "required" else WHITE
            style_cell(cell, fill, FONT_BODY, LEFT)
            if i == 7:
                cell.number_format = "#,##0.00"
            if i == 12:
                cell.number_format = "#,##0.00"
        ws.row_dimensions[row].height = 18

    dv = DataValidation(type="list", formula1='"PHAR,UNIT"', allow_blank=True)
    dv.error = "ใส่ PHAR หรือ UNIT"
    dv.errorTitle = "รหัสคลังไม่ถูกต้อง"
    dv.prompt = "PHAR = คลังยา, UNIT = คลังยาหน่วยงาน"
    dv.promptTitle = "รหัสคลัง"
    ws.add_data_validation(dv)
    dv.add("E3:E203")


def build_ref_sheet(ws):
    ws["A1"] = "คลังที่ใช้ยกยอดยา"
    ws["A1"].font = FONT_TITLE
    headers = ["รหัสคลัง (warehouse_code)", "ชื่อคลัง", "ตำแหน่งมาตรฐาน (location_id/complete_name)", "ใช้เมื่อ"]
    for i, h in enumerate(headers, 1):
        style_cell(ws.cell(3, i, h), NAVY_FILL, FONT_EN, WRAP)
        ws.column_dimensions[get_column_letter(i)].width = [24, 24, 36, 48][i - 1]
    rows = [
        ["PHAR", "คลังยา", "PHAR/Stock", "ยกยอดคงเหลือคลังยาหลัก ถ้าไม่แยกชั้น"],
        ["PHAR", "คลังยา", "PHAR/Stock/Aa1", "ยกยอดแยกชั้น/ช่องเก็บ ใส่ path เต็มตามที่เปิดในระบบ"],
        ["UNIT", "คลังยาหน่วยงาน", "UNIT/Stock", "ยาที่อยู่ที่หน่วยงาน ไม่ใช่คลังยาหลัก"],
    ]
    for r, vals in enumerate(rows, 4):
        for c, val in enumerate(vals, 1):
            style_cell(ws.cell(r, c, val), WHITE, FONT_BODY, WRAP)

    ws["A8"] = "รูปแบบวันที่"
    ws["A8"].font = Font(name=FONT, size=12, bold=True, color=NAVY)
    ws["A9"] = "ใช้ YYYY-MM-DD เท่านั้น เช่น 2027-12-31 ไม่ใส่เวลา และไม่ใช้ พ.ศ. ในช่องวันที่"
    ws["A9"].font = FONT_BODY
    ws.merge_cells("A9:D9")

    ws["A11"] = "กติกานำเข้า"
    ws["A11"].font = Font(name=FONT, size=12, bold=True, color=NAVY)
    rules = [
        "สินค้าต้องมีในระบบแล้ว รหัสตรง product_id/default_code",
        "ตำแหน่งต้องมีในระบบแล้ว ห้ามพิมพ์ชื่อคลังอย่างเดียว ต้องเป็น path เช่น PHAR/Stock",
        "ยา tracking = lot และเปิดวันหมดอายุ ถ้าไม่มีล็อตหรือวันหมดอายุ นำเข้าไม่ได้",
        "หลัง import ให้กด Validate / Apply ที่ใบปรับสต็อก จึงจะขึ้น On Hand",
        "แถวตัวอย่างสีเหลืองต้องลบก่อนนำเข้า",
    ]
    for i, text in enumerate(rules, 1):
        ws.cell(11 + i, 1, i).font = Font(name=FONT, size=11, bold=True, color=NAVY)
        ws.merge_cells(start_row=11 + i, start_column=2, end_row=11 + i, end_column=4)
        cell = ws.cell(11 + i, 2, text)
        cell.font = FONT_BODY
        cell.alignment = WRAP


def build_drug_lookup(ws, drugs):
    ws.freeze_panes = "A2"
    headers = ["รหัสสินค้า", "ชื่อ", "หน่วยนับ", "หมวดหมู่"]
    widths = [16, 72, 12, 40]
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        style_cell(ws.cell(1, i, h), NAVY_FILL, FONT_EN, LEFT)
        ws.column_dimensions[get_column_letter(i)].width = w
    for r, drug in enumerate(drugs, 2):
        vals = [drug["code"], drug["name"], drug["uom"], drug["categ"]]
        for c, val in enumerate(vals, 1):
            style_cell(ws.cell(r, c, val), WHITE, FONT_BODY, LEFT)
        ws.row_dimensions[r].height = 18
    ws.auto_filter.ref = f"A1:D{max(1, len(drugs) + 1)}"


def build():
    drugs = load_drugs()
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "คู่มือ"
    ws1 = wb.create_sheet("ยกยอดสต็อกยา")
    ws2 = wb.create_sheet("รายการอ้างอิง")
    ws3 = wb.create_sheet("รหัสยาในระบบ")
    build_manual(ws0, len(drugs))
    build_stock_sheet(ws1)
    build_ref_sheet(ws2)
    build_drug_lookup(ws3, drugs)
    wb.properties.title = "Template ยกยอดสต็อกยา"
    wb.properties.subject = "กรอกจำนวนคงเหลือยาเพื่อเปิดระบบ Odoo"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    wb.save(OUT_COPY)
    print("Saved:", OUT)
    print("Saved:", OUT_COPY)
    print("Drugs:", len(drugs))


if __name__ == "__main__":
    build()
