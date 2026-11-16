#!/usr/bin/env python3
"""Workflow / Dataflow ชุดจัดซื้อจัดจ้าง (VPK Odoo 18): Input = แผนงบที่อนุมัติ -> ใบขอซื้อ -> e-GP -> PO/สัญญา -> ตรวจรับ -> เจ้าหนี้

รัน: python3 docs/build_procurement_dataflow_pptx.py
ผลลัพธ์: docs/Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dataflow_lib import *  # noqa: E402,F401,F403
from dataflow_lib import _lines  # noqa: E402
from procurement_dataflow_data import (  # noqa: E402
    CONTRACT_COMPARE, CONTRACT_TYPES, FUNCTIONS, INTEGRATION, METHOD_LABEL, PHASES,
)

OUT = Path(__file__).parent / "Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx"
PHASE_COLOR = {
    "A": (AMBER, AMBER_SOFT),
    "B": (BLUE, BLUE_SOFT),
    "C": (TEAL, TEAL_SOFT),
    "D": (AMBER, AMBER_SOFT),
    "E": (GREEN, GREEN_SOFT),
}


def slide_title(prs):
    s = blank(prs)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SLIDE_W), Inches(SLIDE_H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False
    tb(s, 0.9, 1.9, 11.5, 1.0, "Workflow & Dataflow ระบบจัดซื้อจัดจ้าง", size=38, color=WHITE, bold=True)
    tb(s, 0.9, 2.95, 11.5, 0.6, "Input / Process / Output ของแต่ละ function", size=20,
       color=RGBColor(0xBF, 0xD6, 0xE6))
    box(s, 0.9, 3.85, 11.5, 0.75,
        [("INPUT ของชุดนี้ = แผนงบที่อนุมัติ และพร้อมใช้งาน (budget.lines) จากชุดงบประมาณ", {"bold": True, "size": 13, "color": GREEN}),
         ("นำไปทำใบขอซื้อ (PR) โดยเลือกคำของบที่อนุมัติ + รายการงบ", {"size": 11, "color": SLATE})],
        fill=GREEN_SOFT, line=GREEN, lw=1.5, align=PP_ALIGN.LEFT, margin=0.2)
    tb(s, 0.9, 4.8, 11.5, 0.6, [
        "โรงพยาบาลวชิระภูเก็ต · VPK ERP (Odoo 18)",
        "ครอบคลุม: แผนจัดซื้อ → PR (ตรวจ/จองงบ) → พัสดุ/e-GP → PO (ผูกพันงบ) / สัญญา → ตรวจรับ → เจ้าหนี้ (ใช้จริง)",
    ], size=13, color=RGBColor(0xDD, 0xE8, 0xF0))
    x = 0.9
    for code, name, _ in PHASES:
        col, soft = PHASE_COLOR[code]
        box(s, x, 5.85, 2.3, 0.7, f"{code}  {name}", fill=soft, line=None, size=9, color=col, bold=True)
        x += 2.4


def slide_fork(prs, page, total):
    s = blank(prs)
    header(s, "ภาพรวมกระบวนการจัดซื้อ จัดจ้าง",
           "หน่วยงานทำ PR → จัดซื้อรับงาน ส่งเข้า e-GP (ตัดสินใจ/flow อยู่ใน e-GP จบที่ผู้ชนะ/สัญญา) → PO ใน GFMIS → ผู้ขายยืนยัน → ใบรับ / ตรวจรับ")
    G_, GS = GREEN, GREEN_SOFT
    A_, AS = AMBER, AMBER_SOFT
    B_, BS = BLUE, BLUE_SOFT

    TL, TLS = TEAL, TEAL_SOFT

    def card(x, y, w, h, a, b, c, fill, line, dash=False, lw=1.25, sa=8.5, sb=7.5):
        box(s, x, y, w, h, [(a, {"bold": True, "size": sa, "color": line}), (b, {"size": sb}),
                            (c, {"size": 7, "color": MUTED})],
            fill=fill, line=line, lw=lw, margin=0.04, dash=dash)

    # ===== ส่วนบน: หน่วยงานทำ PR ให้ครบ แล้วส่งจัดซื้อ =====
    box(s, 0.3, 0.92, 12.73, 1.2, "", fill=BS, line=B_, lw=1.0, dash=True, shape=MSO_SHAPE.RECTANGLE)
    tb(s, 0.4, 0.94, 12.0, 0.28, "หน่วยงาน: เปิด PR → เลือกแผนงบ → เช็คงบ → เพิ่มกรรมการ → ขออนุมัติขอซื้อ → ส่งจัดซื้อ",
       size=10, bold=True, color=B_)
    unit = [
        ("INPUT: แผนงบที่อนุมัติ", "(budget.lines)", "จากชุดงบประมาณ", GS, G_),
        ("เปิด PR", "ใบขอซื้อ / จ้าง / เช่า", "หน่วยงาน · B1", BS, B_),
        ("เลือกแผนงบประมาณ", "เลือกคำของบที่อนุมัติ + รายการงบ", "หน่วยงาน · B1 [T2]", BS, B_),
        ("เช็คงบประมาณ", "ตรวจ + จองงบ ต้องผ่าน", "ระบบ · B3", GS, G_),
        ("เพิ่มกรรมการ", "รายการสินค้า + รายชื่อกรรมการ", "หน่วยงาน · B2", BS, B_),
        ("ขออนุมัติขอซื้อ", "บันทึกอนุมัติ + ลงนาม", "หน่วยงาน · B4", BS, B_),
        ("ส่งจัดซื้อ", "ส่งได้เมื่อเช็คงบผ่านแล้ว", "หน่วยงาน · B5 [T6]", BS, B_),
    ]
    ux0, ugap = 0.45, 0.2
    ubw = (12.43 - ugap * 6) / 7
    uy, uh = 1.26, 0.78
    ucs = []
    for i, (a, b, c, fill, line) in enumerate(unit):
        x = ux0 + i * (ubw + ugap)
        card(x, uy, ubw, uh, a, b, c, fill, line)
        if i > 0:
            seg(s, x - ugap, uy + uh / 2, x, uy + uh / 2, color=SLATE, w=1.5)
        ucs.append(x + ubw / 2)

    # ===== ส่วนกลาง: จัดซื้อรับงาน -> ส่งเข้า e-GP (จุดตัดสินใจและ flow อยู่ใน e-GP) =====
    c1x, c1y = 1.15, 4.05
    route(s, [(ucs[-1], uy + uh), (ucs[-1], 2.22), (c1x, 2.22), (c1x, c1y - 0.5)], color=B_, w=2)
    card(0.4, c1y - 0.5, 1.5, 1.0, "จัดซื้อรับงาน", "admin ตรวจสอบ + มอบหมายเจ้าหน้าที่", "จัดซื้อ · C1", AS, A_, sa=9)
    box(s, 2.5, 2.3, 10.53, 2.65, "", fill=TLS, line=TL, lw=1.25, dash=True, shape=MSO_SHAPE.RECTANGLE)
    tb(s, 2.6, 2.31, 10.3, 0.28,
       "ระบบ e-GP ของรัฐ: จุดตัดสินใจและ flow อยู่ในนี้ · จบที่ ได้ผู้ชนะ และ ทำสัญญา",
       size=10, bold=True, color=TL)
    dx, dy, dw, dh = 2.75, 3.35, 1.2, 1.4
    dcx = dx + dw / 2
    box(s, dx, dy, dw, dh, [("วิธีจัดซื้อ?", {"bold": True, "size": 10, "color": NAVY})],
        fill=WHITE, line=NAVY, lw=2, shape=MSO_SHAPE.DIAMOND)
    seg(s, 1.9, c1y, dx, c1y, color=SLATE, w=2)
    tb(s, 1.9, c1y - 0.33, dx - 1.9, 0.3, "ส่งเข้า e-GP", size=8, bold=True, color=NAVY,
       align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM)

    gx, gw = 4.7, 1.95
    gy0, gh = 2.62, 0.75
    gy = gy0 + gh / 2
    card(gx, gy0, gw, gh, "มูลค่า > 500,000 บาท?", "ใช่ → ต้องทำแผนใน e-GP ด้วย", "จัดซื้อ · A4", RED_SOFT, RED, dash=True)
    py0, ph = 3.65, 0.8
    pcy = py0 + ph / 2
    box(s, gx, py0, gw, ph,
        [("ทำแผน (ตัวเชื่อม)", {"bold": True, "size": 9, "color": A_}),
         ("e-bidding: แผนจัดซื้อ ทำเสมอ (A1)", {"size": 7.5}),
         ("เฉพาะเจาะจง >500,000: แผน e-GP (A4)", {"size": 7.5})],
        fill=WHITE, line=A_, lw=2, margin=0.04)
    route(s, [(dcx, dy), (dcx, gy), (gx, gy)], color=G_, w=2)
    seg(s, dx + dw, 4.05, gx, 4.05, color=A_, w=2)
    tb(s, dcx + 0.05, gy0 - 0.12, gx - dcx - 0.1, 0.45,
       [("เฉพาะเจาะจง", {"bold": True, "size": 9, "color": G_}),
        ("ไม่ต้องทำแผน", {"size": 7.5, "color": MUTED})],
       align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.BOTTOM)
    tb(s, dx + dw, 3.7, gx - dx - dw, 0.3, "e-bidding", size=8.5, bold=True, color=A_,
       align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM)
    tb(s, dx + dw, 4.08, gx - dx - dw, 0.25, "ทำแผนก่อน", size=7.5, color=MUTED, align=PP_ALIGN.CENTER)
    seg(s, gx + gw / 2, gy0 + gh, gx + gw / 2, py0, color=RED, w=1.75, dash=True)
    tb(s, gx + gw / 2 + 0.05, gy0 + gh + 0.02, 1.0, 0.25, "> 500,000 บาท", size=7.5, bold=True, color=RED)

    ex, ew, ey, eh = 7.0, 1.85, 3.6, 0.9
    card(ex, ey, ew, eh, "แนบไฟล์จากระบบ e-GP", "ขออนุมัติ ลงนาม เปรียบเทียบราคา", "จัดซื้อ · C3-C5", AS, A_)
    wx, ww = 9.15, 1.45
    card(wx, ey, ww, eh, "ได้ผู้ชนะ", "ประกาศผลแล้ว", "จัดซื้อ · C5", GS, G_)
    kx, kw = 10.95, 1.8
    card(kx, ey, kw, eh, "ทำสัญญา", "e-bidding: ทำเสมอ · เฉพาะเจาะจง: ถ้าต้องมีสัญญา", "จัดซื้อ · D4", AS, A_)
    seg(s, gx + gw, pcy, ex, pcy, color=A_, w=1.75)                       # ทำแผน -> e-GP
    route(s, [(gx + gw, gy), (ex + 0.45, gy), (ex + 0.45, ey)], color=G_, w=1.75)  # ไม่เกิน 500,000 -> e-GP
    tb(s, gx + gw + 0.03, gy - 0.27, 0.95, 0.25, "ไม่เกิน 500,000", size=7, bold=True, color=G_)
    seg(s, ex + ew, ey + eh / 2, wx, ey + eh / 2, color=SLATE, w=1.5)
    seg(s, wx + ww, ey + eh / 2, kx, ey + eh / 2, color=SLATE, w=1.75)

    # ออกจาก e-GP ไปสร้าง PO
    hy = 5.06
    po_cx = 1.4
    seg(s, wx + ww / 2, ey + eh, wx + ww / 2, hy, color=G_, w=1.75, arrow=False)
    seg(s, kx + kw / 2, ey + eh, kx + kw / 2, hy, color=A_, w=1.75, arrow=False)
    route(s, [(kx + kw / 2, hy), (po_cx, hy), (po_cx, 5.62)], color=SLATE, w=2)
    tb(s, wx + ww / 2 + 0.05, ey + eh + 0.03, 1.7, 0.25, "เฉพาะเจาะจง ไม่ทำสัญญา → PO", size=7.5, bold=True, color=G_)
    tb(s, kx + kw / 2 + 0.05, ey + eh + 0.03, 1.1, 0.25, "ทำสัญญาแล้ว → PO", size=7, bold=True, color=A_)

    # ===== ส่วนล่าง: PO ตามระบบงานรัฐ (GFMIS) -> ผู้ขายยืนยัน -> จัดซื้อยืนยัน -> ใบรับ / ตรวจรับ =====
    box(s, 0.3, 5.25, 12.73, 1.7, "", fill=WHITE, line=A_, lw=1.0, dash=True, shape=MSO_SHAPE.RECTANGLE)
    tb(s, 2.2, 5.27, 6.2, 0.28, "PO ตามระบบงานรัฐ (GFMIS) → ผู้ขายยืนยัน → จัดซื้อยืนยัน → ใบรับ/ตรวจรับ → เบิกจ่าย",
       size=10, bold=True, color=A_)
    tb(s, 8.4, 5.27, 4.55, 0.28, "เส้นเขียน = เฉพาะเจาะจง · ส้ม = e-bidding · แดงประ = มูลค่า > 500,000 บาท",
       size=7.5, color=MUTED, align=PP_ALIGN.RIGHT)
    ry, rh = 5.62, 1.05
    rc = ry + rh / 2
    card(0.45, ry, 1.9, rh, "สร้าง PO ซื้อ", "ตามระบบงานรัฐ ต้องทำใน GFMIS", "จัดซื้อ · D1", TLS, TL, sa=9)
    card(2.6, ry, 1.8, rh, "ส่ง PO ให้ผู้ขายยืนยัน", "แอป/พอร์ทัลผู้ขาย ลงนาม แล้วส่งกลับจัดซื้อ", "จัดซื้อ / ผู้ขาย · D2", AS, A_, sa=9)
    card(4.65, ry, 1.95, rh, "จัดซื้อยืนยัน PO อีกครั้ง", "ตรวจงบ → ผูกพันงบ → เกิดใบรอรับ", "จัดซื้อ / ระบบ · D3", GS, G_, sa=9)
    mx, mw = 6.85, 1.45
    box(s, mx, ry, mw, rh, [("ประเภท?", {"bold": True, "size": 9.5, "color": NAVY}),
                            ("สินค้า / บริการ-ครุภัณฑ์", {"size": 7, "color": MUTED})],
        fill=WHITE, line=NAVY, lw=2, shape=MSO_SHAPE.DIAMOND, margin=0.02)
    seg(s, 2.35, rc, 2.6, rc, color=SLATE, w=1.5)
    seg(s, 4.4, rc, 4.65, rc, color=SLATE, w=1.5)
    seg(s, 6.6, rc, mx, rc, color=SLATE, w=1.5)
    tx, tw = 8.7, 2.45
    t_top, t_bot = 5.6, 6.2
    card(tx, t_top, tw, 0.55, "สินค้า → ใบรับสินค้า (Receipt)", "ส่งเข้าระบบ Inventory (คลัง)", "คลัง · E2", AS, A_, sa=8.5, sb=7.5)
    card(tx, t_bot, tw, 0.55, "บริการ / ครุภัณฑ์ → ระบบตรวจรับงาน", "คณะกรรมการตรวจรับ", "กรรมการ · E1", AS, A_, sa=8.5, sb=7.5)
    route(s, [(mx + mw, rc), (8.5, rc), (8.5, t_top + 0.275), (tx, t_top + 0.275)], color=SLATE, w=1.5)
    route(s, [(mx + mw, rc), (8.5, rc), (8.5, t_bot + 0.275), (tx, t_bot + 0.275)], color=SLATE, w=1.5)
    dbx, dbw = 11.5, 1.4
    card(dbx, ry + 0.05, dbw, rh - 0.1, "เบิกจ่าย", "ระบบบัญชี: ตั้งเจ้าหนี้ ตัดยอดใช้จริง", "บัญชี · E3", AS, A_, sa=9)
    route(s, [(tx + tw, t_top + 0.275), (11.3, t_top + 0.275), (11.3, rc), (dbx, rc)], color=SLATE, w=1.5)
    route(s, [(tx + tw, t_bot + 0.275), (11.3, t_bot + 0.275), (11.3, rc), (dbx, rc)], color=SLATE, w=1.5)
    footer(s, page, total)


def slide_int_workflow(prs, method, page, total):
    """Swimlane แยกตามวิธีจัดซื้อ: method = "specific" | "ebidding" """
    spec = method == "specific"
    mname = "วิธีเฉพาะเจาะจง" if spec else "วิธี e-bidding"
    s = blank(prs)
    header(s, f"Workflow ชุดจัดซื้อจัดจ้าง ({mname})",
           ("ไม่ต้องทำแผน (มูลค่า > 500,000 บาท ทำแผนใน e-GP) → PR → ตรวจ/จองงบ → e-GP → สร้าง PO → ผู้ขายยืนยัน → ตรวจรับ → เจ้าหนี้"
            if spec else
            "ทำแผนก่อน → PR → ตรวจ/จองงบ → e-GP → ทำสัญญา → ตรวจรับ → เจ้าหนี้") +
           " · [T#] = จุดเชื่อมกับงบ")
    lanes = ["หน่วยงาน", "พัสดุ", "ระบบ: งบประมาณ (อัตโนมัติ)", "ผู้ขาย / ตรวจรับ", "เจ้าหนี้ / การเงิน"]
    lane_x, lane_w, label_w, top, lane_h = 0.3, 12.73, 1.25, 1.0, 1.12
    for i, name in enumerate(lanes):
        y = top + i * lane_h
        box(s, lane_x, y, lane_w, lane_h, "", fill=LANE_A if i % 2 == 0 else LANE_B, line=LINE,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
        box(s, lane_x, y, label_w, lane_h, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
    x0 = lane_x + label_w + 0.12
    colw = (lane_x + lane_w - x0 - 0.05) / 10
    bw, bh = colw - 0.14, 0.82

    def cx(c):
        return x0 + c * colw + colw / 2

    def by(lane):
        return top + lane * lane_h + (lane_h - bh) / 2 + 0.04

    BS, B_ = BLUE_SOFT, BLUE
    TS, T_ = TEAL_SOFT, TEAL
    AS, A_ = AMBER_SOFT, AMBER
    GS, G_ = GREEN_SOFT, GREEN

    def step(lane, col, title, text, tag, fill, line, span=1, dash=False):
        x = cx(col) - bw / 2
        w = bw + (span - 1) * colw
        y = by(lane)
        paras = [(title, {"bold": True, "size": 8.5, "color": line}), (text, {"size": 8})]
        if tag:
            paras.append((tag, {"size": 7.5, "color": MUTED, "bold": True}))
        box(s, x, y, w, bh, paras, fill=fill, line=line, lw=1.25, margin=0.03, dash=dash)
        return dict(l=x, r=x + w, t=y, b=y + bh, cx=x + w / 2, cy=y + bh / 2)

    inp = step(2, 0, "INPUT จากชุดงบประมาณ", "แผนงบที่อนุมัติ (budget.lines)", "", GS, G_)
    pr = step(0, 1, "สร้าง PR", "เลือกแผนงบที่อนุมัติ", "[T2]", BS, B_)
    chk = step(2, 2, "เช็คงบ + จอง", "คงเหลือ ≥ ยอด PR", "[T3]", GS, G_)
    snd = step(0, 3, "ส่งจัดซื้อ", "ต้องเช็คงบผ่าน", "[T6]", BS, B_)
    app = step(1, 4, "จัดซื้อรับงาน", "admin ตรวจสอบ", "[C1]", AS, A_)
    egp = step(1, 6 if spec else 5, "e-GP: แนบไฟล์", "จากระบบรัฐ ถึงได้ผู้ชนะ", "[T7]", AS, A_)
    if spec:
        gate = step(1, 5, "เงื่อนไขมูลค่า", "> 500,000 บาท: ทำแผนใน e-GP", "[A4]", RED_SOFT, RED, dash=True)
        exc = step(2, 3, "ข้อยกเว้น", "PR ฉุกเฉิน: ข้ามจอง (เมื่อตั้งค่า)", "[T5]", AS, A_, span=2)
    else:
        plan = step(1, 0, "แผนจัดซื้อ", "ต้องทำก่อน · ผูกแผนงบ", "[T1]", AS, A_)
        exc = step(2, 3, "ข้อยกเว้น", "PR ผูกสัญญา: ตรวจวงเงินสัญญา แทนการจองซ้ำ", "[T4]", AS, A_, span=2)
        con = step(1, 6, "ทำสัญญา", "ทะเบียนสัญญา · งวดงาน", "[T4]", AS, A_)
    po = step(1, 7, "สร้าง PO", "ตามระบบรัฐ ต้องทำใน GFMIS", "[D1]", TEAL_SOFT, TEAL)
    cf = step(2, 7, "จัดซื้อยืนยัน PO", "ผู้ขายยืนยันแล้ว ตรวจงบ → ผูกพัน", "[T8]", GS, G_)
    vd = step(3, 7, "ใบรับ / ตรวจรับ", "สินค้า → Inventory · บริการ/ครุภัณฑ์ → ตรวจรับงาน", "", AS, A_)
    bill = step(4, 8, "ตั้งเจ้าหนี้", "Post Vendor Bill", "[T9]", AS, A_)
    used = step(2, 8, "ตัดผูกพัน", "→ ยอดใช้จริง", "[T9]", GS, G_)
    pay = step(4, 9, "จ่ายเงิน", "การเงิน / GFMIS", "", AS, A_)
    dash = step(2, 9, "Dashboard", "ติดตามงบ (ผลกลับสู่งบ)", "", TS, T_)

    if spec:
        # เฉพาะเจาะจง: ไม่ผ่านแผน ใช้แผนงบเข้า PR โดยตรง
        route(s, [(inp["cx"], inp["t"]), (inp["cx"], pr["cy"]), (pr["l"], pr["cy"])], color=G_)
        tb(s, cx(0) - bw / 2, by(1) + 0.05, bw + 0.2, 0.7,
           [("ไม่ต้องทำแผน", {"bold": True, "size": 8, "color": G_}),
            ("ใช้แผนงบเข้า PR ได้เลย", {"size": 7.5, "color": G_})])
    else:
        route(s, [(inp["cx"], inp["t"]), (plan["cx"], plan["b"])], color=G_)
        route(s, [(plan["cx"], plan["t"]), (plan["cx"], pr["cy"]), (pr["l"], pr["cy"])])
    route(s, [(inp["r"], inp["cy"]), (chk["l"], inp["cy"])], color=G_, dash=True)
    route(s, [(pr["cx"], pr["b"]), (pr["cx"], chk["cy"]), (chk["l"], chk["cy"])])
    route(s, [(chk["cx"], chk["t"]), (chk["cx"], snd["cy"]), (snd["l"], snd["cy"])])
    route(s, [(chk["r"], chk["cy"]), (exc["l"], exc["cy"])], color=A_, dash=True)
    route(s, [(snd["r"], snd["cy"]), (app["cx"], snd["cy"]), (app["cx"], app["t"])])
    if spec:
        route(s, [(app["r"], app["cy"]), (gate["l"], gate["cy"])])
        route(s, [(gate["r"], gate["cy"]), (egp["l"], egp["cy"])], color=RED, dash=True)
        route(s, [(egp["r"], egp["cy"]), (po["l"], po["cy"])])
    else:
        route(s, [(app["r"], app["cy"]), (egp["l"], egp["cy"])])
        route(s, [(egp["r"], egp["cy"]), (con["l"], con["cy"])])
        route(s, [(con["r"], con["cy"]), (po["l"], po["cy"])])
    route(s, [(po["cx"], po["b"]), (cf["cx"], cf["t"])])
    route(s, [(cf["cx"], cf["b"]), (vd["cx"], vd["t"])])
    route(s, [(vd["r"], vd["cy"]), (bill["cx"] - 0.25, vd["cy"]), (bill["cx"] - 0.25, bill["t"])])
    route(s, [(bill["cx"] + 0.25, bill["t"]), (bill["cx"] + 0.25, used["b"])], color=G_)
    route(s, [(bill["r"], bill["cy"]), (pay["l"], pay["cy"])])
    route(s, [(used["r"], used["cy"]), (dash["l"], dash["cy"])], color=G_)

    red = [("คืนงบอัตโนมัติ", {"bold": True, "size": 8, "color": RED}),
           ("PR ตีกลับ/ยกเลิก/ปิด → คืนยอดจอง", {"size": 7.5, "color": RED})]
    red.append(("PO ยกเลิก → คืนจองให้ PR", {"size": 7.5, "color": RED}))
    red.append(("Bill ตั้งร่าง/ยกเลิก → คืนผูกพัน", {"size": 7.5, "color": RED}))
    tb(s, cx(5) - bw / 2, by(2) - 0.02, 2 * colw, 0.85, red)

    ly = top + 5 * lane_h + 0.08
    x = 0.4
    for name, fillc, linec in [("หน่วยงาน", BS, B_), ("พัสดุ / ผู้ขาย / เจ้าหนี้", AS, A_),
                               ("ระบบงบประมาณ", GS, G_), ("ติดตาม", TS, T_)]:
        box(s, x, ly, 0.28, 0.2, "", fill=fillc, line=linec, lw=1.25)
        tb(s, x + 0.33, ly - 0.03, 2.3, 0.26, name, size=8.5, color=MUTED)
        x += 2.4
    seg(s, 10.2, ly + 0.1, 10.7, ly + 0.1, color=A_, dash=True)
    tb(s, 10.75, ly - 0.03, 2.3, 0.26, "ข้อยกเว้นการตรวจงบ", size=8.5, color=MUTED)
    footer(s, page, total)


def slide_int_dfd(prs, method, page, total):
    """method = "specific" (เฉพาะเจาะจง) | "ebidding" """
    spec = method == "specific"
    mname = "วิธีเฉพาะเจาะจง" if spec else "วิธี e-bidding"
    mcol = GREEN if spec else AMBER
    s = blank(prs)
    header(s, f"Data Flow ชุดจัดซื้อจัดจ้าง ({mname}): รับแผนงบที่อนุมัติ และส่งผลกลับสู่งบ",
           ("ไม่ต้องทำแผนจัดซื้อ (มูลค่า > 500,000 บาท ทำแผนใน e-GP) → PR → e-GP → สร้าง PO" if spec
            else "ต้องทำแผนจัดซื้อก่อน → PR → e-GP → ทำสัญญา") +
           " · ซ้าย = Input จากชุดงบประมาณ · ขวา = เอกสารในชุดจัดซื้อ")

    box(s, 0.3, 1.0, 4.0, 6.0, "", fill=RGBColor(0xF1, 0xF8, 0xF4), line=GREEN, lw=1.25, shape=MSO_SHAPE.RECTANGLE,
        dash=True)
    tb(s, 0.4, 1.02, 3.8, 0.28, "INPUT จากชุดงบประมาณ (vpk_budget)", size=10.5, bold=True, color=GREEN)
    box(s, 8.7, 1.0, 4.35, 6.0, "", fill=RGBColor(0xFF, 0xF8, 0xEC), line=AMBER, lw=1.25, shape=MSO_SHAPE.RECTANGLE,
        dash=True)
    tb(s, 8.8, 1.02, 4.1, 0.28, f"ระบบจัดซื้อจัดจ้าง · {mname}", size=10.5, bold=True, color=mcol)

    def store(x, y, w, h, title, lines, col, fill=WHITE, dash=False):
        paras = [(title, {"bold": True, "size": 10, "color": col})] + [(t, {"size": 8, "color": SLATE}) for t in lines]
        box(s, x, y, w, h, paras, fill=fill, line=col, lw=1.5, shape=MSO_SHAPE.RECTANGLE, dash=dash)
        return dict(l=x, r=x + w, t=y, b=y + h, cx=x + w / 2, cy=y + h / 2)

    d2 = store(0.5, 1.4, 3.6, 0.85, "คำของบที่อนุมัติ (Approved)", ["หน่วยงาน · แหล่งเงิน · กลุ่มงบ · หมวดงบ"], GREEN)
    d3 = store(0.5, 2.5, 3.6, 4.35, "รายการงบประมาณ (budget.lines)",
               ["planned = งบจัดสรร", "pr_reserved_amount = จอง PR", "po_committed_amount = ผูกพัน PO",
                "practical_amount = ใช้จริง", "pr_available_amount = คงเหลือ",
                "คงเหลือ = จัดสรร − ใช้จริง − จอง − ผูกพัน"], GREEN, fill=GREEN_SOFT)
    seg(s, d2["cx"], d2["b"], d2["cx"], d3["t"], color=SLATE)
    tb(s, d2["cx"] + 0.08, d2["b"] + 0.02, 2.0, 0.25, "อนุมัติ → สร้างรายการงบ", size=7.5, color=MUTED)

    px, pw = 8.9, 3.95
    if spec:
        pl = store(px, 2.5, pw, 0.7, "ไม่ต้องทำแผนจัดซื้อ", ["ข้ามขั้นแผน ไปสร้าง PR ได้เลย", "แต่มูลค่า > 500,000 บาท ต้องทำแผนในระบบ e-GP ด้วย"], MUTED,
                   fill=RGBColor(0xF6, 0xF8, 0xFA), dash=True)
    else:
        pl = store(px, 2.5, pw, 0.7, "แผนจัดซื้อประจำปี (ต้องทำก่อน)", ["budget_id · budget_line_id"], AMBER)
    pr_lines = ["budget_plan_request_id · budget_line_id", "budget_check_state · budget_reservation_active"]
    if not spec:
        pr_lines.append("PR อ้างรายการแผน · ผูกสัญญา → ตรวจวงเงินสัญญา")
    else:
        pr_lines.append("ฉุกเฉิน (ตั้งค่า) → ข้ามจอง")
    pr_ = store(px, 3.35, pw, 1.0, "ใบขอซื้อ (PR)", pr_lines, AMBER)
    eg = store(px, 4.5, pw, 0.7, "โครงการ e-GP / เปรียบเทียบราคา", ["วงเงินงบ ← ยอดประเมินบรรทัด PR"], AMBER)
    if spec:
        last = store(px, 5.35, pw, 0.7, "ใบสั่งซื้อ (PO)", ["budget_line_id · budget_committed_amount"], AMBER)
    else:
        last = store(px, 5.35, pw, 0.7, "สัญญา (purchase.contract)", ["วงเงินสัญญา · ยอดคงเหลือสัญญา · งวดงาน"], AMBER)
    bl = store(px, 6.2, pw, 0.65, "ใบเรียกเก็บ (Vendor Bill)", ["budget_analytic_account_id · budget_fund_source_id"], AMBER)
    seg(s, pr_["cx"], pr_["b"], eg["cx"], eg["t"], color=SLATE)
    seg(s, last["cx"], last["b"], bl["cx"], bl["t"], color=SLATE)
    seg(s, eg["cx"], eg["b"], last["cx"], last["t"], color=SLATE)
    if not spec:
        seg(s, pl["cx"], pl["b"], pl["cx"], pr_["t"], color=SLATE)

    def flow(y, label, both=False, tag="", dash=False, color=SLATE):
        seg(s, d3["r"], y, px, y, color=color, w=1.75, both=both, dash=dash)
        tb(s, d3["r"] + 0.1, y - 0.42, px - d3["r"] - 0.2, 0.4, [(label, {"size": 8})], color=color,
           anchor=MSO_ANCHOR.BOTTOM)
        if tag:
            tb(s, px - 0.55, y - 0.25, 0.5, 0.2, tag, size=7.5, bold=True, color=MUTED, align=PP_ALIGN.RIGHT)

    if spec:
        flow(3.95, "เลือกรายการงบ และจองงบ / ตรวจงบคงเหลือ", both=True, tag="T3")
        flow(5.7, "ยืนยัน PO: ตรวจงบ แล้วย้ายจอง PR → ผูกพัน PO", both=True, tag="T8")
    else:
        flow(2.85, "ผูกแผนจัดซื้อกับแผนงบ / รายการงบ", both=True, tag="T1")
        flow(3.95, "เลือกรายการงบ และจองงบ / ตรวจงบคงเหลือ", both=True, tag="T3")
        flow(5.7, "PR/PO ผูกสัญญา: ตรวจวงเงินสัญญา แทนการจองงบซ้ำ", both=True, tag="T4", dash=True, color=AMBER)
    flow(6.55, "Post Bill: ผูกพันลด + ยอดใช้จริง", tag="T9")
    route(s, [(d2["r"], 1.8), (8.55, 1.8), (8.55, 3.6), (pr_["l"], 3.6)], color=SLATE, w=1.75)
    tb(s, 4.3, 1.45, 4.2, 0.35, "คำของบที่อนุมัติ → หน่วยงาน/แหล่งเงิน/กลุ่ม/หมวด (T2)", size=8, color=SLATE)
    footer(s, page, total)


def slide_int_table(prs, rows, part, nparts, page, total):
    s = blank(prs)
    suffix = f" ({part}/{nparts})" if nparts > 1 else ""
    header(s, f"จุดรับ Input จากงบประมาณ และผลกลับสู่งบ: Input / Output{suffix}",
           "ข้อมูลที่ส่งผ่านและผลต่อยอดงบ ในแต่ละจุด (T1–T10)")
    cols = [("รหัส", 0.5), ("วิธีจัดซื้อ", 0.85), ("จุดเชื่อม", 2.0), ("INPUT", 2.65), ("OUTPUT / ผลต่องบ", 3.2), ("ทริกเกอร์", 1.45), ("Field / Method", 1.75)]
    x0, y0 = 0.35, 0.98
    x = x0
    xs = []
    for name, w in cols:
        xs.append((x, w))
        box(s, x, y0, w - 0.04, 0.32, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE)
        x += w
    y = y0 + 0.38
    for r in rows:
        cells = [
            [r["code"]],
            [METHOD_LABEL[r["method"]]],
            [r["name"], f"{r['frm']} → {r['to']}"],
            ["• " + t for t in r["inputs"]],
            ["• " + t for t in r["outputs"]],
            [r["trigger"]],
            [r["tech"]],
        ]
        sizes = [10, 8.5, 9, 8.5, 8.5, 8.5, 7.5]
        h = rows_h(cells, sizes, [w - 0.04 - 0.16 for _, w in cols])
        mfill = {"both": RGBColor(0xEE, 0xF1, 0xF4), "specific": GREEN_SOFT, "ebidding": AMBER_SOFT}[r["method"]]
        fills = [soft_for(r["code"]), mfill, WHITE, BLUE_SOFT, GREEN_SOFT, WHITE, RGBColor(0xF6, 0xF8, 0xFA)]
        for ci, ((cx_, cw), cell, sz) in enumerate(zip(xs, cells, sizes)):
            paras = []
            for k, t in enumerate(cell):
                if ci == 2 and k == 0:
                    paras.append((t, {"size": sz, "bold": True, "color": NAVY}))
                elif ci == 2:
                    paras.append((t, {"size": 8, "color": MUTED}))
                elif ci in (0, 1):
                    paras.append((t, {"size": sz, "bold": True, "color": NAVY}))
                else:
                    paras.append((t, {"size": sz, "color": MUTED if ci == 6 else SLATE}))
            box(s, cx_, y, cw - 0.04, h, paras, fill=fills[ci], line=LINE, lw=0.75, shape=MSO_SHAPE.RECTANGLE,
                align=PP_ALIGN.CENTER if ci in (0, 1) else PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, margin=0.08)
        y += h + 0.05
    footer(s, page, total)


def paginate_integration(rows, avail=7.05 - 1.38):
    cols_w = [w - 0.2 for w in (0.5, 0.85, 2.0, 2.65, 3.2, 1.45, 1.75)]
    pages, cur, used = [], [], 0.0
    for r in rows:
        cells = [[r["code"]], [METHOD_LABEL[r["method"]]], [r["name"], f"{r['frm']} → {r['to']}"], ["• " + t for t in r["inputs"]],
                 ["• " + t for t in r["outputs"]], [r["trigger"]], [r["tech"]]]
        h = rows_h(cells, [10, 8.5, 9, 8.5, 8.5, 8.5, 7.5], cols_w) + 0.05
        if cur and used + h > avail:
            pages.append(cur)
            cur, used = [], 0.0
        cur.append(r)
        used += h
    if cur:
        pages.append(cur)
    return pages



# ------------------------------------------------------------------ ประเภทสัญญา
def slide_contract_compare(prs, page, total):
    s = blank(prs)
    header(s, "เปรียบเทียบประเภทสัญญา: สัญญาซื้อขาย / สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน",
           "ทำหลังได้ผู้ชนะ: e-bidding ทำเสมอ · เฉพาะเจาะจงทำได้ถ้าต้องมีสัญญา · ประเภทสัญญาเป็นข้อมูลหลักที่เพิ่มได้")
    cols = [("หัวข้อ", 2.0), ("สัญญาซื้อขาย", 5.3), ("สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน", 5.3)]
    x0, y = 0.35, 1.0
    xs = []
    x = x0
    for (name, w), col in zip(cols, (NAVY, GREEN, AMBER)):
        xs.append((x, w))
        box(s, x, y, w - 0.05, 0.38, name, fill=col, line=col, size=11, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE)
        x += w
    y += 0.44
    for topic, a, b in CONTRACT_COMPARE:
        h = max(rows_h([[topic], [a], [b]], [10, 9.5, 9.5], [w - 0.05 - 0.16 for _, w in cols]), 0.5)
        for (cx_, cw), txt, fill, bold in zip(xs, (topic, a, b), (RGBColor(0xEE, 0xF1, 0xF4), GREEN_SOFT, AMBER_SOFT),
                                              (True, False, False)):
            box(s, cx_, y, cw - 0.05, h, [(txt, {"size": 10 if bold else 9.5, "bold": bold,
                                                 "color": NAVY if bold else SLATE})],
                fill=fill, line=LINE, lw=0.75, shape=MSO_SHAPE.RECTANGLE, align=PP_ALIGN.LEFT,
                anchor=MSO_ANCHOR.MIDDLE, margin=0.1)
        y += h + 0.05
    tb(s, 0.4, y + 0.05, 12.5, 0.55, [
        ("หมายเหตุ: ระบบตรวจวงเงินสัญญาเป็น 'มูลค่า' (ไม่ใช่จำนวนชิ้น) ความต่างของสองประเภทเกิดจากการมี/ไม่มีงวดงาน "
         "และความหมายของมูลค่ารวมสัญญา · ระบบยังไม่มีช่องกำหนด 'ไม่จำกัดจำนวน' โดยเฉพาะ", {"size": 8.5, "color": MUTED}),
    ])
    footer(s, page, total)


# ตำแหน่งกล่องใน swimlane: id -> (lane, col, หัวข้อ, ข้อความ, ชนิด)  ชนิด: p=พัสดุ u=หน่วยงาน s=ระบบ v=ผู้ขาย/เจ้าหนี้
_CT_LANES = ["พัสดุ", "หน่วยงาน", "ระบบ: สัญญา / งบ", "ผู้ขาย / ตรวจรับ", "เจ้าหนี้ / การเงิน"]
_CT_FLOW = {
    "sale": dict(
        boxes={
            "S1": (0, 0, "S1 เปิดทะเบียน", "จาก e-GP ผู้ชนะ", "p"),
            "S2": (0, 1, "S2 รายการ/เงื่อนไข", "สินค้า ราคา วันส่งมอบ", "p"),
            "S3": (0, 2, "S3 แบ่งงวดงาน", "ผลรวมงวด = มูลค่า", "p"),
            "S4": (0, 3, "S4 แนบเอกสาร", "สัญญา TOR หลักประกัน", "p"),
            "S5": (0, 4, "S5 ยืนยันสัญญา", "ผู้จัดการจัดซื้อ", "p"),
            "Y1": (2, 4, "มีผลบังคับใช้", "ตรวจผลรวมงวด", "s"),
            "S6": (1, 5, "S6 PR ต่องวด", "ดึงงวดถัดไป ผูกสัญญา", "u"),
            "Y2": (2, 6, "ตรวจวงเงินสัญญา", "Hard Block ไม่จองงบซ้ำ", "s"),
            "S7": (0, 7, "S7 สร้าง PO", "ผู้ขายยืนยัน", "p"),
            "Y3": (2, 8, "ตัดวงเงินสัญญา", "ตาม PO ที่ยืนยัน", "s"),
            "S8": (3, 8, "S8 ตรวจรับ", "ส่งมอบตามงวด", "v"),
            "S9": (4, 9, "ตั้งเจ้าหนี้", "Post Bill ต่องวด", "v"),
            "Y4": (2, 9, "ยอดใช้จริง", "คงเหลือสัญญา", "s"),
            "S10": (0, 9, "S9 ปิดสัญญา", "ครบงวด/ครบอายุ", "p"),
        },
        routes=[("S1", "S2", "h"), ("S2", "S3", "h"), ("S3", "S4", "h"), ("S4", "S5", "h"),
                ("S5", "Y1", "v"), ("Y1", "S6", "rt_up"), ("S6", "Y2", "rt_dn"), ("Y2", "S7", "rt_up"),
                ("S7", "Y3", "rt_dn"), ("Y3", "S8", "v"), ("S8", "S9", "rt_dn_l"), ("S9", "Y4", "up_r"),
                ("Y4", "S10", "vu")],
        loop=("S9", "S6", "วนซ้ำทุกงวด: งวดถัดไป → เปิด PR ใหม่ → PO → ตรวจรับ → เจ้าหนี้"),
        note="สัญญาซื้อขาย: รายการและมูลค่าชัดเจน แบ่งงวดจ่ายได้ ผลรวมงวด = มูลค่าสัญญา · PR ต่องวด",
    ),
    "framework": dict(
        boxes={
            "S1": (0, 0, "N1 เปิดทะเบียน", "จาก e-GP ผู้ชนะ", "p"),
            "S2": (0, 1, "N2 วงเงินเพดาน", "ราคาต่อหน่วย อายุสัญญา", "p"),
            "S3": (0, 2, "N3 แนบเอกสาร", "สัญญา TOR หลักประกัน", "p"),
            "S5": (0, 3, "N4 ยืนยันสัญญา", "ไม่มีงวด", "p"),
            "Y1": (2, 3, "มีผลบังคับใช้", "พร้อมให้เรียกใช้", "s"),
            "S6": (1, 4, "N5 PR เรียกใช้", "เพิ่มรายการเอง", "u"),
            "Y2": (2, 5, "ตรวจวงเงินสัญญา", "Hard Block ไม่จองงบซ้ำ", "s"),
            "S7": (0, 6, "N6 สร้าง PO", "ต่อรอบ ผู้ขายยืนยัน", "p"),
            "Y3": (2, 7, "ตัดวงเงินสัญญา", "ตาม PO ที่ยืนยัน", "s"),
            "S8": (3, 7, "N7 ตรวจรับ", "ตามรอบที่เรียกใช้", "v"),
            "S9": (4, 8, "ตั้งเจ้าหนี้", "Post Bill ต่อรอบ", "v"),
            "Y4": (2, 8, "คงเหลือสัญญา", "วงเงิน − ใช้ไป", "s"),
            "S10": (0, 9, "N9 ปิดสัญญา", "วงเงินหมด/หมดอายุ", "p"),
        },
        routes=[("S1", "S2", "h"), ("S2", "S3", "h"), ("S3", "S5", "h"),
                ("S5", "Y1", "v"), ("Y1", "S6", "rt_up"), ("S6", "Y2", "rt_dn"), ("Y2", "S7", "rt_up"),
                ("S7", "Y3", "rt_dn"), ("Y3", "S8", "v"), ("S8", "S9", "rt_dn_l"), ("S9", "Y4", "up_r"),
                ("Y4", "S10", "rt_up")],
        loop=("S9", "S6", "N8 เรียกใช้ซ้ำไม่จำกัดรอบ จนวงเงินหมดหรือหมดอายุ"),
        note="สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน: สัญญากรอบ ไม่แบ่งงวด · มูลค่าสัญญา = วงเงินเพดาน · เปิด PR ได้ทุกครั้งที่ต้องการ",
    ),
}


def slide_contract_flow(prs, ctype, page, total):
    spec = _CT_FLOW[ctype]
    info = CONTRACT_TYPES[ctype]
    s = blank(prs)
    header(s, f"Workflow ประเภทสัญญา: {info['name']}", info["desc"])
    lane_x, lane_w, label_w, top, lane_h = 0.3, 12.73, 1.25, 1.0, 1.12
    for i, name in enumerate(_CT_LANES):
        y = top + i * lane_h
        box(s, lane_x, y, lane_w, lane_h, "", fill=LANE_A if i % 2 == 0 else LANE_B, line=LINE,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
        box(s, lane_x, y, label_w, lane_h, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
    x0 = lane_x + label_w + 0.1
    colw = (lane_x + lane_w - x0 - 0.05) / 10
    bw, bh = colw - 0.1, 0.84
    kind = {"p": (AMBER_SOFT, AMBER), "u": (BLUE_SOFT, BLUE), "s": (GREEN_SOFT, GREEN), "v": (AMBER_SOFT, AMBER)}

    def cx(c):
        return x0 + c * colw + colw / 2

    B = {}
    for key, (lane, col, title, text, k) in spec["boxes"].items():
        fill, line = kind[k]
        x = cx(col) - bw / 2
        y = top + lane * lane_h + (lane_h - bh) / 2 + 0.03
        box(s, x, y, bw, bh, [(title, {"bold": True, "size": 8, "color": line}), (text, {"size": 7.5})],
            fill=fill, line=line, lw=1.25, margin=0.03)
        B[key] = dict(l=x, r=x + bw, t=y, b=y + bh, cx=x + bw / 2, cy=y + bh / 2)

    for a, b, mode in spec["routes"]:
        A, Bx = B[a], B[b]
        col = GREEN if A["t"] > top + 1.5 * lane_h and Bx["t"] > top + 1.5 * lane_h else MUTED
        if mode == "h":
            route(s, [(A["r"], A["cy"]), (Bx["l"], Bx["cy"])])
        elif mode == "v":
            route(s, [(A["cx"], A["b"]), (Bx["cx"], Bx["t"])])
        elif mode == "vu":
            route(s, [(A["cx"], A["t"]), (Bx["cx"], Bx["b"])])
        elif mode == "rt_up":
            route(s, [(A["r"], A["cy"]), (Bx["cx"], A["cy"]), (Bx["cx"], Bx["b"])], color=col)
        elif mode == "rt_dn":
            route(s, [(A["r"], A["cy"]), (Bx["cx"], A["cy"]), (Bx["cx"], Bx["t"])], color=col)
        elif mode == "rt_dn_l":
            route(s, [(A["r"], A["cy"]), (Bx["cx"] - 0.25, A["cy"]), (Bx["cx"] - 0.25, Bx["t"])])
        elif mode == "up_r":
            route(s, [(A["cx"] + 0.25, A["t"]), (A["cx"] + 0.25, Bx["b"])], color=GREEN)

    a, b, label = spec["loop"]
    A, Bx = B[a], B[b]
    route(s, [(A["l"], A["cy"]), (Bx["cx"] + 0.3, A["cy"]), (Bx["cx"] + 0.3, Bx["b"])], color=RED, dash=True, w=1.5)
    tb(s, Bx["cx"] + 0.4, A["cy"] - 0.5, 4.8, 0.45, [(label, {"bold": True, "size": 8.5, "color": RED})])

    # หมายเหตุประเภทสัญญา ในเลนหน่วยงาน (ว่าง)
    box(s, cx(0) - bw / 2, top + lane_h + 0.18, 3 * colw + bw - colw + 0.4, 0.76,
        [("จุดเด่นของสัญญานี้", {"bold": True, "size": 8.5, "color": NAVY}), (spec["note"], {"size": 8})],
        fill=WHITE, line=NAVY, lw=1.0, dash=True, align=PP_ALIGN.LEFT, margin=0.08)

    ly = top + 5 * lane_h + 0.08
    x = 0.4
    for name, fillc, linec in [("พัสดุ / ผู้ขาย / เจ้าหนี้", AMBER_SOFT, AMBER), ("หน่วยงาน", BLUE_SOFT, BLUE),
                               ("ระบบ (ตรวจวงเงิน / ตัดยอด)", GREEN_SOFT, GREEN)]:
        box(s, x, ly, 0.28, 0.2, "", fill=fillc, line=linec, lw=1.25)
        tb(s, x + 0.33, ly - 0.03, 2.8, 0.26, name, size=8.5, color=MUTED)
        x += 2.9
    seg(s, 9.4, ly + 0.1, 9.9, ly + 0.1, color=RED, dash=True)
    tb(s, 9.95, ly - 0.03, 3.0, 0.26, "วนซ้ำ (เรียกใช้สัญญาหลายรอบ)", size=8.5, color=MUTED)
    footer(s, page, total)


def contract_steps_pages(ctype):
    cols_w = [w - 0.2 for w in (0.55, 1.5, 2.8, 3.2, 3.0, 1.6)]
    pages, cur, used, avail = [], [], 0.0, 7.05 - 1.38
    for st in CONTRACT_TYPES[ctype]["steps"]:
        cells = [[st["code"]], [st["name"], st["actor"]], ["• " + t for t in st["inputs"]],
                 ["› " + t for t in st["process"]], ["• " + t for t in st["outputs"]], [st["tech"]]]
        h = rows_h(cells, [10, 9, 8.5, 8.5, 8.5, 7.5], cols_w) + 0.05
        if cur and used + h > avail:
            pages.append(cur)
            cur, used = [], 0.0
        cur.append(st)
        used += h
    if cur:
        pages.append(cur)
    if len(pages) == 2:  # แบ่งให้สมดุล
        allst = pages[0] + pages[1]
        half = -(-len(allst) // 2)
        pages = [allst[:half], allst[half:]]
    return pages


def slide_contract_steps(prs, ctype, rows, part, nparts, page, total):
    info = CONTRACT_TYPES[ctype]
    s = blank(prs)
    suffix = f" ({part}/{nparts})" if nparts > 1 else ""
    header(s, f"{info['name']}: Input / Process / Output ของแต่ละขั้น{suffix}", info["desc"])
    cols = [("ขั้น", 0.55), ("ขั้นตอน / ผู้ทำ", 1.5), ("INPUT", 2.8), ("PROCESS", 3.2), ("OUTPUT", 3.0), ("Field / Method", 1.6)]
    x0, y0 = 0.35, 0.98
    x = x0
    xs = []
    for name, w in cols:
        xs.append((x, w))
        box(s, x, y0, w - 0.04, 0.32, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE)
        x += w
    y = y0 + 0.38
    cols_w = [w - 0.04 - 0.16 for _, w in cols]
    for st in rows:
        cells = [[st["code"]], [st["name"], st["actor"]], ["• " + t for t in st["inputs"]],
                 ["› " + t for t in st["process"]], ["• " + t for t in st["outputs"]], [st["tech"]]]
        sizes = [10, 9, 8.5, 8.5, 8.5, 7.5]
        h = rows_h(cells, sizes, cols_w)
        fills = [RGBColor(0xEE, 0xF1, 0xF4), WHITE, BLUE_SOFT, WHITE, GREEN_SOFT, RGBColor(0xF6, 0xF8, 0xFA)]
        for ci, ((cx_, cw), cell, sz) in enumerate(zip(xs, cells, sizes)):
            paras = []
            for k, t in enumerate(cell):
                if ci == 1 and k == 0:
                    paras.append((t, {"size": sz, "bold": True, "color": NAVY}))
                elif ci == 1:
                    paras.append((t, {"size": 8, "color": MUTED}))
                elif ci == 0:
                    paras.append((t, {"size": sz, "bold": True, "color": NAVY}))
                else:
                    paras.append((t, {"size": sz, "color": MUTED if ci == 5 else SLATE}))
            box(s, cx_, y, cw - 0.04, h, paras, fill=fills[ci], line=LINE, lw=0.75, shape=MSO_SHAPE.RECTANGLE,
                align=PP_ALIGN.CENTER if ci == 0 else PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, margin=0.08)
        y += h + 0.05
    footer(s, page, total)


def main():
    configure("ระบบจัดซื้อจัดจ้าง · VPK ERP",
              "ที่มา: คู่มือระบบจัดซื้อจัดจ้าง + odoo18-custom-addons (vpk_procurement_auto_pr, vpk_purchase_*, vpk_budget)")
    prs = new_prs()
    pages = io_pages(FUNCTIONS, PHASES)
    int_pages = paginate_integration(INTEGRATION)
    sale_pages = contract_steps_pages("sale")
    fw_pages = contract_steps_pages("framework")

    plan = [lambda p, t: slide_title(prs), lambda p, t: slide_fork(prs, p, t),
            lambda p, t: slide_int_workflow(prs, "specific", p, t),
            lambda p, t: slide_int_workflow(prs, "ebidding", p, t),
            lambda p, t: slide_contract_compare(prs, p, t)]
    for ctype, cp in (("sale", sale_pages), ("framework", fw_pages)):
        plan.append(lambda p, t, c=ctype: slide_contract_flow(prs, c, p, t))
        for k, rows in enumerate(cp):
            plan.append(lambda p, t, c=ctype, r=rows, k=k, n=len(cp): slide_contract_steps(prs, c, r, k + 1, n, p, t))
    plan.append(lambda p, t: slide_int_dfd(prs, "specific", p, t))
    plan.append(lambda p, t: slide_int_dfd(prs, "ebidding", p, t))
    for k, rows in enumerate(int_pages):
        plan.append(lambda p, t, r=rows, k=k: slide_int_table(prs, r, k + 1, len(int_pages), p, t))
    for code, ch, i, n in pages:
        plan.append(lambda p, t, code=code, ch=ch, i=i, n=n: slide_io(prs, ch, PHASES, PHASE_COLOR, code, i, n, p, t))
    total = len(plan)
    for idx, fn in enumerate(plan, 1):
        fn(idx, total)
    prs.save(OUT)
    print("saved", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    main()
