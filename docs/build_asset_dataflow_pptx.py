#!/usr/bin/env python3
"""Workflow / Dataflow งานบริหารทรัพย์สิน (VPK Odoo 18)
สาย: ขึ้นทะเบียน · ค่าเสื่อมและรายงาน · โอน · จำหน่าย · ตรวจนับประจำปี · เชื่อมซ่อมบำรุง

รัน: python3 docs/build_asset_dataflow_pptx.py
ผลลัพธ์: docs/Workflow-Dataflow-งานบริหารทรัพย์สิน.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dataflow_lib import *  # noqa: E402,F401,F403
from build_warehouse_dataflow_pptx import (  # noqa: E402
    GREY_SOFT, PINK, PINK_SOFT, paginate_int, slide_int_table, slide_swim,
)
from asset_dataflow_data import FUNCTIONS, INTEGRATION, PHASES  # noqa: E402

OUT = Path(__file__).parent / "Workflow-Dataflow-งานบริหารทรัพย์สิน.pptx"
PHASE_COLOR = {
    "A": (BLUE, BLUE_SOFT),
    "B": (AMBER, AMBER_SOFT),
    "C": (TEAL, TEAL_SOFT),
    "D": (RED, RED_SOFT),
    "E": (GREEN, GREEN_SOFT),
    "F": (PINK, PINK_SOFT),
}


def slide_title(prs):
    s = blank(prs)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SLIDE_W), Inches(SLIDE_H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False
    tb(s, 0.9, 1.9, 11.5, 1.0, "Workflow & Dataflow งานบริหารทรัพย์สิน", size=38, color=WHITE, bold=True)
    tb(s, 0.9, 2.95, 11.5, 0.6, "Input / Process / Output ของแต่ละ function", size=20,
       color=RGBColor(0xBF, 0xD6, 0xE6))
    box(s, 0.9, 3.85, 11.5, 0.75,
        [("วงจรทรัพย์สิน: ขึ้นทะเบียน → ค่าเสื่อม → โอน → ซ่อม → จำหน่าย และตรวจนับประจำปี",
          {"bold": True, "size": 13, "color": GREEN}),
         ("ใบแจ้งหนี้ครุภัณฑ์สร้างบัตรสินทรัพย์ · โอนและจำหน่ายอนุมัติตามลำดับ · ตรวจนับผ่าน Portal/QR",
          {"size": 11, "color": SLATE})],
        fill=GREEN_SOFT, line=GREEN, lw=1.5, align=PP_ALIGN.LEFT, margin=0.2)
    tb(s, 0.9, 4.8, 11.5, 0.6, [
        "โรงพยาบาลวชิระภูเก็ต · VPK ERP (Odoo 18) · module vpk_asset_* · account_asset_management",
        "เชื่อมกับจัดซื้อจัดจ้าง (ใบแจ้งหนี้ครุภัณฑ์) บัญชี (ค่าเสื่อม/ตัดจำหน่าย) และงานซ่อมบำรุง",
    ], size=13, color=RGBColor(0xDD, 0xE8, 0xF0))
    x = 0.9
    for code, name, _ in PHASES:
        col, soft = PHASE_COLOR[code]
        box(s, x, 5.85, 1.85, 0.7, f"{code}  {name}", fill=soft, line=None, size=9, color=col, bold=True)
        x += 1.92


OVERVIEW = [
    ("A", "ขึ้นทะเบียน",
     ["ใบแจ้งหนี้ผู้ขาย (ครุภัณฑ์)", "บรรทัดที่เลือกหมวดสินทรัพย์"],
     ["สร้างบัตร (ร่าง)", "บันทึกทะเบียน", "ยืนยัน ออกเลข", "พิมพ์ป้าย / QR"],
     ["บัตร Running + เลขสินทรัพย์", "ถือครองที่ คลังสินค้า"]),
    ("B", "ค่าเสื่อมและรายงาน",
     ["บัตร Running", "วันที่สิ้นงวดบัญชี"],
     ["Compute Assets", "รายการบัญชีค่าเสื่อม", "รายงานสินทรัพย์"],
     ["มูลค่าคงเหลือลดลง", "ครบอายุ → Close"]),
    ("C", "โอนทรัพย์สิน",
     ["หน่วยงานต้นทาง ขอโอนบัตร"],
     ["สร้างใบโอน AT", "ขอโอน", "อนุมัติตามลำดับ", "รับโอน"],
     ["หน่วยงานถือครองเปลี่ยน", "(เมื่ออนุมัติครบ)"]),
    ("D", "จำหน่ายทรัพย์สิน",
     ["บัตรชำรุด / หมดอายุ", "หรือซ่อมไม่คุ้ม"],
     ["รอจำหน่าย", "ใบจำหน่าย AD", "อนุมัติตามลำดับ", "ตัดจากทะเบียน"],
     ["บัตร Removed", "ลงบัญชีกำไร / ขาดทุน"]),
    ("E", "ตรวจนับประจำปี",
     ["รอบตรวจนับ INV", "ทุกบัตรที่ยังไม่ Removed"],
     ["สร้าง Sheet", "เปิดนับ", "นับ Portal / QR", "ปิดนับ"],
     ["ผลนับและผลต่างรายหน่วยงาน"]),
    ("F", "เชื่อมซ่อมบำรุง",
     ["บัตร Running"],
     ["สร้าง Equipment", "คำขอซ่อม", "ประวัติบนบัตร", "ซ่อมไม่คุ้ม แทงจำหน่าย"],
     ["Sub-Status รอจำหน่าย", "ไปสาย D"]),
]


def slide_overview(prs, page, total):
    s = blank(prs)
    header(s, "ภาพรวมงานบริหารทรัพย์สิน: 6 สาย",
           "ที่มา (Trigger) → ขั้นตอนหลัก → ผลต่อทะเบียนสินทรัพย์ · สาย F ส่งต่อสาย D เมื่อซ่อมไม่คุ้ม")
    y0, bh, gap = 0.98, 0.84, 0.07
    for i, (code, name, src, stages, res) in enumerate(OVERVIEW):
        y = y0 + i * (bh + gap)
        col, soft = PHASE_COLOR[code]
        box(s, 0.35, y, 1.7, bh, [(code, {"size": 15, "bold": True, "color": WHITE}),
                                  (name, {"size": 10, "bold": True, "color": WHITE})],
            fill=col, line=col, radius=0.1)
        box(s, 2.2, y, 2.3, bh,
            [("ที่มา", {"size": 8, "bold": True, "color": col})] + [("• " + t, {"size": 8.5}) for t in src],
            fill=soft, line=col, align=PP_ALIGN.LEFT, radius=0.08, margin=0.08)
        seg(s, 2.05, y + bh / 2, 2.2, y + bh / 2, color=SLATE, w=1.75)
        seg(s, 4.5, y + bh / 2, 4.65, y + bh / 2, color=SLATE, w=1.75)
        n = len(stages)
        cx0, cw_total, ar = 4.65, 5.9, 0.14
        cw = (cw_total - ar * (n - 1)) / n
        for k, st in enumerate(stages):
            x = cx0 + k * (cw + ar)
            box(s, x, y + 0.14, cw, bh - 0.28, st, fill=WHITE, line=col, lw=1.5, size=8.5, bold=True,
                color=SLATE, radius=0.15, margin=0.03)
            if k < n - 1:
                seg(s, x + cw, y + bh / 2, x + cw + ar, y + bh / 2, color=col, w=1.5)
        seg(s, cx0 + cw_total, y + bh / 2, 10.7, y + bh / 2, color=SLATE, w=1.75)
        box(s, 10.7, y, 2.3, bh,
            [("ผลลัพธ์", {"size": 8, "bold": True, "color": GREEN})] + [("• " + t, {"size": 8.5}) for t in res],
            fill=GREEN_SOFT, line=GREEN, align=PP_ALIGN.LEFT, radius=0.08, margin=0.08)
    yb = y0 + 6 * (bh + gap) + 0.02
    box(s, 0.35, yb, 12.65, 0.55,
        [("สถานะบัตรสินทรัพย์", {"size": 8.5, "bold": True, "color": NAVY}),
         ("ร่าง (Draft) → ใช้งาน (Running) → ครบอายุ (Close) → ตัดจากทะเบียน (Removed)  ·  "
          "Sub-Status ขณะใช้งาน: ปกติ / ชำรุด / รอจำหน่าย / หมดอายุ", {"size": 8.5})],
        fill=GREY_SOFT, line=LINE, align=PP_ALIGN.LEFT, radius=0.08, margin=0.12)
    footer(s, page, total)


# ------------------------------------------------------------------ Workflow
L_REG = ["จัดซื้อ / ผู้ขาย", "บัญชี", "ทรัพย์สิน", "ระบบ"]
S_REG = {
    "po": (0, 0, "PO ครุภัณฑ์", "ส่งมอบ ตรวจรับ (WA)", "W1", "p"),
    "st": (1, 0, "ตั้งค่าหมวดสินทรัพย์", "อายุ · บัญชี · ลำดับเลข", "A1", "p"),
    "bl": (1, 1, "ใบแจ้งหนี้ผู้ขาย", "บรรทัดเลือกหมวดสินทรัพย์", "A2", "p"),
    "sy": (3, 2, "ระบบสร้างบัตร (ร่าง)", "ถือครอง = คลังสินค้า", "A2", "s"),
    "rg": (2, 3, "บันทึกทะเบียน", "PO · GFMIS · VCR · หน่วยงาน", "A4", "w"),
    "cf": (2, 4, "ยืนยันบัตร", "ออกเลข + ตารางค่าเสื่อม", "A3", "w"),
    "rn": (3, 4, "สถานะ Running", "ใช้งาน · มีเลขสินทรัพย์", "A3", "ok"),
    "dp": (1, 5, "Compute Assets", "รายการบัญชีค่าเสื่อม", "B1", "p"),
    "rp": (1, 6, "รายงานสินทรัพย์", "Assets analysis · Financial", "B2", "p"),
}
E_REG = [
    ("po", "bl", None, None), ("st", "bl", None, "dash"), ("bl", "sy", None, None), ("sy", "rg", None, None),
    ("rg", "cf", None, None), ("cf", "rn", None, "ok"), ("rn", "dp", None, None), ("dp", "rp", None, None),
]
N_REG = [
    (0, 2, 6, [("ที่มาของบัตร", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ครุภัณฑ์ที่ซื้อ: จัดซื้อ → ตรวจรับ → ใบแจ้งหนี้ลงบัญชี → ระบบสร้างบัตร · "
                "ต้องใส่ชื่อสินทรัพย์ในช่องรายละเอียดของบรรทัด", {"size": 8})]),
    (2, 6, 8, [("พิมพ์ป้าย / ชุดสินทรัพย์ (A5-A6)", {"size": 8.5, "bold": True, "color": NAVY}),
               ("พิมพ์ป้ายเลขสินทรัพย์ (QR) ใช้ตอนตรวจนับ · ผูกบัตรย่อยเป็นชุดได้", {"size": 8})]),
    (3, 6, 8, [("ค่าเสื่อม", {"size": 8.5, "bold": True, "color": NAVY}),
               ("คำนวณที่ Compute Assets เท่านั้น เฉพาะบัตร Running · ใช้หลังปิดงวด", {"size": 8})]),
]

L_TRF = ["หน่วยงานต้นทาง", "ผู้อนุมัติ (ตามลำดับ)", "ระบบ", "หน่วยงานปลายทาง"]
S_TRF = {
    "t1": (0, 0, "สร้างใบโอน AT", "ต้นทาง/ปลายทาง + เลือกบัตร", "C1", "u"),
    "t2": (0, 1, "ขอโอน", "ต้องตั้งลำดับอนุมัติไว้ก่อน", "C1", "u"),
    "t3": (1, 2, "อนุมัติทีละลำดับ", "สถานะ ดำเนินการ", "C2", "p"),
    "t4": (1, 3, "ครบลำดับ?", "", "C2", "p:d"),
    "t6": (2, 3, "ยกเลิก", "ผู้อนุมัติปฏิเสธ", "C2", "e"),
    "t5": (2, 4, "เปลี่ยนหน่วยงานถือครอง", "ทันทีที่อนุมัติครบ", "C2", "s"),
    "t7": (3, 5, "รับโอน", "ผู้รับโอน / ผู้จัดการการโอน", "C3", "u"),
    "t8": (3, 6, "สถานะรับโอน", "บันทึกผู้รับ + เวลา · ยกเลิกไม่ได้", "C3", "ok"),
}
E_TRF = [
    ("t1", "t2", None, None), ("t2", "t3", None, None), ("t3", "t4", None, None),
    ("t4", "t5", "ครบ", "ok", {"lp": (0.04, -0.22)}), ("t4", "t6", "ปฏิเสธ", "bad", {"lp": (0.06, 0.02)}),
    ("t5", "t7", None, None), ("t7", "t8", None, "ok"),
]
N_TRF = [
    (0, 3, 8, [("เงื่อนไข", {"size": 8.5, "bold": True, "color": NAVY}),
               ("หน่วยงานต้นทางและปลายทางต้องต่างกัน · ทรัพย์สินห้ามซ้ำในใบ · "
                "ต้นทางต้องตรงกับหน่วยงานถือครองปัจจุบันของบัตร", {"size": 8})]),
    (1, 5, 8, [("หมายเหตุ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("หน่วยงานถือครองเปลี่ยนตอนอนุมัติครบ ไม่ต้องรอกดรับโอน · ปุ่มรับโอนคือยืนยันว่าปลายทางรับของแล้ว",
                {"size": 8})]),
    (2, 6, 8, [("ประวัติ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ใบโอนทุกใบเก็บเป็นประวัติบนบัตรสินทรัพย์", {"size": 8})]),
]

L_DSP = ["หน่วยงาน / ทรัพย์สิน", "ผู้อนุมัติ (ตามลำดับ)", "บัญชี / ระบบ", "ซ่อมบำรุง"]
S_DSP = {
    "d0": (3, 0, "ซ่อมไม่คุ้ม", "ผลประเมิน → แทงจำหน่าย", "F3", "w"),
    "d1": (0, 1, "ตั้ง Sub-Status", "รอจำหน่าย (ชำรุด / หมดอายุ)", "D1", "u"),
    "d2": (0, 2, "สร้างใบจำหน่าย AD", "วิธีตัด · เหตุผล · มติ + ไฟล์", "D2", "u"),
    "d3": (0, 3, "ดึงรายการรอจำหน่าย", "ตรวจมูลค่าคงเหลือ / ที่ได้รับ", "D2", "u"),
    "d4": (0, 4, "ขออนุมัติ", "สถานะ ขออนุมัติ", "D2", "u"),
    "d5": (1, 5, "อนุมัติทีละลำดับ", "ครบ → อนุมัติ · ปฏิเสธ → ยกเลิก", "D3", "p"),
    "d6": (2, 6, "ตัดจำหน่ายจากทะเบียน", "ลงบัญชีกำไร / ขาดทุน", "D4", "s"),
    "d7": (2, 7, "บัตร Removed", "ใบจำหน่ายเสร็จสิ้น", "D4", "ok"),
}
E_DSP = [
    ("d0", "d1", None, "dash"), ("d1", "d2", None, None), ("d2", "d3", None, None), ("d3", "d4", None, None),
    ("d4", "d5", None, None), ("d5", "d6", None, None), ("d6", "d7", None, "ok"),
]
N_DSP = [
    (1, 2, 4, [("ก่อนตัดจำหน่าย", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ใส่เลขหนังสือ/มติ และแนบไฟล์ที่แท็บเอกสารประกอบ", {"size": 8})]),
    (3, 2, 7, [("เงื่อนไขตอนกดตัดจำหน่าย", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ต้องอนุมัติครบลำดับ · ระบุบัญชีกำไรและขาดทุน (มีมูลค่าที่ได้รับ ต้องระบุบัญชีรับเงินด้วย) · "
                "บัตรต้อง Running หรือ Close · วันที่ตัดต้องหลังวันลงบัญชีค่าเสื่อมล่าสุด", {"size": 8})]),
    (0, 6, 8, [("ผู้ดึงรายการ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ดึงได้เฉพาะใบสถานะร่าง และเฉพาะบัตรที่ยังไม่ถูกตัด", {"size": 8})]),
]

L_CNT = ["ทรัพย์สิน (ผู้จัดรอบ)", "ระบบ", "หน่วยงาน (ผู้แทน)", "ผู้บริหาร / ผู้ตรวจ"]
S_CNT = {
    "c1": (0, 0, "เปิดรอบตรวจนับ INV", "ปีงบ · วันเริ่ม–สิ้นสุด", "E1", "w"),
    "c2": (1, 1, "สร้าง Sheet", "ตามหน่วยงานถือครอง · ระบบ = 1", "E1", "s"),
    "c3": (0, 2, "เปิดนับ", "ออกลิงก์ Portal / QR", "E2", "w"),
    "c4": (2, 3, "นับจริง + บันทึก", "Portal / สแกน QR ป้าย", "E3", "u"),
    "c5": (1, 4, "คิดผลต่าง", "นับ − ระบบ · ผู้นับ + เวลา", "E3", "s"),
    "c6": (3, 5, "ดูผลออนไลน์", "รอนับ · นับแล้ว · ผลต่าง", "E4", "p"),
    "c7": (0, 6, "ปิดนับ", "เมื่อนับครบตามกำหนด", "E4", "w"),
    "c8": (0, 7, "ผลนับเป็นหลักฐาน", "ปรับทะเบียนแยกด้วยโอน/จำหน่าย", "E4", "ok"),
}
E_CNT = [
    ("c1", "c2", None, None), ("c2", "c3", None, None), ("c3", "c4", None, None), ("c4", "c5", None, None),
    ("c5", "c6", None, None), ("c6", "c7", None, None), ("c7", "c8", None, "ok"),
]
N_CNT = [
    (2, 7, 8, [("ข้อกำหนด", {"size": 8.5, "bold": True, "color": NAVY}),
               ("บันทึกจำนวนได้เฉพาะช่วงเปิดนับ · สร้าง Sheet ได้เฉพาะสถานะร่าง · รอบที่ปิดนับแล้วยกเลิกไม่ได้",
                {"size": 8})]),
    (3, 0, 3, [("ขอบเขตการนับ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ทุกบัตรที่ยังไม่ Removed แยกตามหน่วยงานถือครอง · ไม่มีหน่วยงาน = Sheet คลังกลาง", {"size": 8})]),
    (1, 7, 8, [("หมายเหตุ ERP", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ปิดนับเปลี่ยนเฉพาะสถานะรอบ ยังไม่ปรับทะเบียนอัตโนมัติจากผลต่าง", {"size": 8})]),
]

L_MNT = ["ทรัพย์สิน", "ช่าง / ซ่อมบำรุง", "ระบบ"]
S_MNT = {
    "m1": (0, 0, "บัตร Running", "ทรัพย์สินที่ใช้งาน", "A3", "w"),
    "m2": (0, 1, "สร้าง Equipment", "โมเดล · ซีเรียล · พิกัด", "F1", "w"),
    "m3": (2, 2, "ผูก Equipment ↔ บัตร", "ปุ่ม Equipment บนบัตร", "F1", "s"),
    "m4": (1, 3, "แจ้งซ่อม / ซ่อม", "คำขอซ่อมของ Equipment", "F2", "w"),
    "m9": (0, 3, "ประวัติซ่อม + สัญญา", "แสดงบนบัตร", "F2", "w"),
    "m5": (1, 4, "ซ่อมคุ้ม?", "", "F3", "w:d"),
    "m6": (1, 5, "ซ่อมเสร็จ", "กลับใช้งานต่อ", "F2", "ok"),
    "m7": (2, 5, "แทงจำหน่าย", "ผลประเมินซ่อมไม่คุ้ม", "F3", "w"),
    "m8": (0, 6, "Sub-Status รอจำหน่าย", "ไปใบจำหน่าย (สาย D)", "F3", "ok"),
}
E_MNT = [
    ("m1", "m2", None, None), ("m2", "m3", None, None), ("m3", "m4", None, None), ("m4", "m5", None, None),
    ("m4", "m9", None, "dash"), ("m5", "m6", "คุ้ม", "ok", {"lp": (0.02, -0.22)}),
    ("m5", "m7", "ไม่คุ้ม", "bad", {"mode": "vh", "lp": (0.05, 0.05)}), ("m7", "m8", None, None),
]
N_MNT = [
    (2, 0, 1, [("สิทธิ์", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ปุ่มสร้าง Equipment เห็นเฉพาะผู้จัดการครุภัณฑ์ / บัญชี", {"size": 8})]),
    (0, 7, 8, [("เงื่อนไขแทงจำหน่าย", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ผลประเมิน = ซ่อมไม่คุ้มแทงจำหน่าย · Equipment ต้องเชื่อมบัตร", {"size": 8})]),
]


# ------------------------------------------------------------------ DFD
DFD_ROWS = [
    ("A", "ขึ้นทะเบียนสินทรัพย์",
     ("ใบแจ้งหนี้ผู้ขาย / ทรัพย์สิน", ["บรรทัดที่เลือกหมวดสินทรัพย์ + มูลค่า", "PO · GFMIS · โครงการ"]),
     ["สร้างบัตร (ร่าง)", "บันทึกทะเบียน → ยืนยัน ออกเลข"],
     (["account.asset · account.asset.profile"], ["บัตร Running + เลขสินทรัพย์", "ตารางค่าเสื่อม"])),
    ("B", "ค่าเสื่อมและรายงาน",
     ("บัญชี", ["วันที่สิ้นงวด", "บัตร Running"]),
     ["Compute Assets", "สร้างรายการบัญชีค่าเสื่อม"],
     (["account.asset.line · account.move"], ["รายการบัญชีค่าเสื่อม", "มูลค่าคงเหลือลดลง"])),
    ("C", "การโอนทรัพย์สิน",
     ("หน่วยงานต้นทาง / ผู้อนุมัติ", ["ต้นทาง · ปลายทาง · บัตร", "ลำดับผู้อนุมัติ"]),
     ["ขอโอน → อนุมัติตามลำดับ", "เปลี่ยนหน่วยงาน → รับโอน"],
     (["vpk.asset.transfer (+ line)"], ["หน่วยงานถือครองใหม่บนบัตร", "ประวัติใบโอน"])),
    ("D", "การจำหน่ายทรัพย์สิน",
     ("หน่วยงาน / ช่าง", ["Sub-Status รอจำหน่าย", "วิธีตัด · มติ · บัญชี"]),
     ["ใบจำหน่าย → อนุมัติ", "ตัดจากทะเบียน ลงบัญชี"],
     (["vpk.asset.disposal (+ line)", "account.asset.remove"], ["บัตร Removed", "รายการบัญชีตัดจำหน่าย"])),
    ("E", "ตรวจนับประจำปี",
     ("ผู้แทนหน่วยงาน (Portal / QR)", ["จำนวนที่นับจริง", "ป้ายเลขสินทรัพย์"]),
     ["สร้าง Sheet → เปิดนับ", "บันทึกผล → ปิดนับ"],
     (["vpk.asset.inventory.count / .sheet / .line"], ["ผลนับและผลต่างรายหน่วยงาน"])),
    ("F", "เชื่อมซ่อมบำรุง",
     ("ช่าง / ผู้จัดการครุภัณฑ์", ["โมเดล · ซีเรียล · พิกัด", "ผลประเมินคำขอซ่อม"]),
     ["สร้าง Equipment", "ประวัติซ่อม · แทงจำหน่าย"],
     (["maintenance.equipment · maintenance.request"], ["ประวัติซ่อมบนบัตร", "Sub-Status รอจำหน่าย"])),
]


def slide_dfd(prs, page, total):
    s = blank(prs)
    header(s, "Dataflow ภาพรวม: ข้อมูลเข้า → การประมวลผล → ที่เก็บข้อมูล / ผลลัพธ์",
           "ทุกสายอ้างบัตรสินทรัพย์ (account.asset) ใบเดียวกัน · หน่วยงานถือครองเปลี่ยนที่สาย C · สถานะ Removed ที่สาย D")
    y0, bh, gap = 1.0, 0.8, 0.07
    for x, w, t, c in [(0.35, 3.3, "ข้อมูลเข้า / ผู้ส่ง", BLUE), (4.2, 4.2, "การประมวลผล", NAVY),
                       (8.95, 4.05, "ที่เก็บข้อมูล และผลลัพธ์", GREEN)]:
        box(s, x, y0, w, 0.3, t, fill=c, line=c, size=10.5, color=WHITE, bold=True, radius=0.2)
    y0 += 0.36
    for i, (code, name, (src, src_items), proc, (stores, results)) in enumerate(DFD_ROWS):
        y = y0 + i * (bh + gap)
        col, soft = PHASE_COLOR[code]
        box(s, 0.35, y, 3.3, bh,
            [(src, {"size": 9.5, "bold": True, "color": BLUE})] + [("• " + t, {"size": 8}) for t in src_items],
            fill=BLUE_SOFT, line=BLUE, align=PP_ALIGN.LEFT, radius=0.08, margin=0.08)
        box(s, 4.2, y, 4.2, bh,
            [(f"{code}  {name}", {"size": 10.5, "bold": True, "color": col})] + [("› " + t, {"size": 8.5}) for t in proc],
            fill=WHITE, line=col, lw=2, align=PP_ALIGN.LEFT, radius=0.1, margin=0.1)
        box(s, 8.95, y, 4.05, bh,
            [(t, {"size": 8, "color": MUTED}) for t in stores]
            + [("• " + t, {"size": 8.5}) for t in results],
            fill=GREEN_SOFT, line=GREEN, align=PP_ALIGN.LEFT, radius=0.08, margin=0.08)
        seg(s, 3.65, y + bh / 2, 4.2, y + bh / 2, color=SLATE, w=2)
        seg(s, 8.4, y + bh / 2, 8.95, y + bh / 2, color=SLATE, w=2)
    footer(s, page, total)


def main():
    configure("งานบริหารทรัพย์สิน · VPK ERP",
              "ที่มา: คู่มือระบบจัดการสินทรัพย์ + odoo18-custom-addons (vpk_asset_*, account_asset_management, vpk_maintenance)")
    prs = new_prs()
    pages = io_pages(FUNCTIONS, PHASES)
    int_pages = paginate_int(INTEGRATION)
    plan = [
        lambda p, t: slide_title(prs),
        lambda p, t: slide_overview(prs, p, t),
        lambda p, t: slide_swim(
            prs, "A–B. Workflow ขึ้นทะเบียน และค่าเสื่อม: ใบแจ้งหนี้ → บัตร → ยืนยัน → ค่าเสื่อม",
            "ใบแจ้งหนี้ครุภัณฑ์สร้างบัตรสถานะร่าง · ยืนยันแล้วออกเลขและตารางค่าเสื่อม · รหัส A1–A6, B1–B2",
            L_REG, S_REG, E_REG, N_REG, p, t),
        lambda p, t: slide_swim(
            prs, "C. Workflow การโอนทรัพย์สิน: ขอโอน → อนุมัติตามลำดับ → รับโอน",
            "ย้ายหน่วยงานถือครองเมื่ออนุมัติครบ · รับโอนคือยืนยันว่าปลายทางรับของแล้ว · รหัส C1–C3",
            L_TRF, S_TRF, E_TRF, N_TRF, p, t),
        lambda p, t: slide_swim(
            prs, "D. Workflow การจำหน่าย: รอจำหน่าย → ใบจำหน่าย → อนุมัติ → ตัดทะเบียน",
            "ตัดบัตรเป็น Removed พร้อมลงบัญชีกำไร/ขาดทุน · รหัส D1–D4",
            L_DSP, S_DSP, E_DSP, N_DSP, p, t),
        lambda p, t: slide_swim(
            prs, "E. Workflow ตรวจนับทรัพย์สินประจำปี: สร้าง Sheet → นับ Portal/QR → ปิดนับ",
            "นับตามหน่วยงานถือครอง ติดตามผลออนไลน์ · รหัส E1–E4",
            L_CNT, S_CNT, E_CNT, N_CNT, p, t),
        lambda p, t: slide_swim(
            prs, "F. Workflow เชื่อมงานซ่อมบำรุง: Equipment → ซ่อม → ซ่อมไม่คุ้ม → รอจำหน่าย",
            "บัตรสินทรัพย์ผูก Equipment · ซ่อมไม่คุ้มส่งต่อใบจำหน่าย · รหัส F1–F3",
            L_MNT, S_MNT, E_MNT, N_MNT, p, t),
        lambda p, t: slide_dfd(prs, p, t),
    ]
    for k, rows in enumerate(int_pages):
        plan.append(lambda p, t, r=rows, k=k: slide_int_table(
            prs, r, k + 1, len(int_pages), p, t,
            title="จุดเชื่อมงานทรัพย์สินกับระบบอื่น: Input / Output",
            sub="จัดซื้อ/บัญชี · GFMIS · ซ่อมบำรุง · การอนุมัติ · Portal (W1–W6)"))
    for code, ch, i, n in pages:
        plan.append(lambda p, t, code=code, ch=ch, i=i, n=n: slide_io(prs, ch, PHASES, PHASE_COLOR, code, i, n, p, t))
    total = len(plan)
    for idx, fn in enumerate(plan, 1):
        fn(idx, total)
    prs.save(OUT)
    print("saved", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    main()
