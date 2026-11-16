#!/usr/bin/env python3
"""Workflow / Dataflow ชุดงบประมาณ (VPK Odoo 18): ตั้งค่า -> คำของบ -> พิจารณา/อนุมัติ -> แผนงบที่อนุมัติพร้อมใช้งาน (ส่งมอบชุดจัดซื้อ)

รัน: python3 docs/build_budget_dataflow_pptx.py
ผลลัพธ์: docs/Workflow-Dataflow-งบประมาณ.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dataflow_lib import *  # noqa: E402,F401,F403
from budget_dataflow_data import FUNCTIONS, PHASES  # noqa: E402

OUT = Path(__file__).parent / "Workflow-Dataflow-งบประมาณ.pptx"
PHASE_COLOR = {
    "A": (MUTED, RGBColor(0xEE, 0xF1, 0xF4)),
    "B": (BLUE, BLUE_SOFT),
    "C": (TEAL, TEAL_SOFT),
    "D": (GREEN, GREEN_SOFT),
}


def slide_title(prs):
    s = blank(prs)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SLIDE_W), Inches(SLIDE_H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False
    tb(s, 0.9, 1.9, 11.5, 1.0, "Workflow & Dataflow ระบบงบประมาณ", size=38, color=WHITE, bold=True)
    tb(s, 0.9, 2.95, 11.5, 0.6, "Input / Process / Output ของแต่ละ function", size=20,
       color=RGBColor(0xBF, 0xD6, 0xE6))
    box(s, 0.9, 3.85, 11.5, 0.75,
        [("OUTPUT ของชุดนี้ = แผนงบที่อนุมัติ และพร้อมใช้งาน (budget.lines)", {"bold": True, "size": 13, "color": GREEN}),
         ("ส่งมอบให้ชุดจัดซื้อจัดจ้างนำไปทำใบขอซื้อ (PR) — ดูเอกสาร Workflow-Dataflow-จัดซื้อจัดจ้าง", {"size": 11, "color": SLATE})],
        fill=GREEN_SOFT, line=GREEN, lw=1.5, align=PP_ALIGN.LEFT, margin=0.2)
    tb(s, 0.9, 4.8, 11.5, 0.6, [
        "โรงพยาบาลวชิระภูเก็ต · VPK ERP (Odoo 18) · module vpk_budget",
        "ครอบคลุม: ตั้งค่าข้อมูลหลัก → คำของบ → พิจารณา/จัดสรร/อนุมัติ → แผนงบที่อนุมัติพร้อมใช้ + รายงาน",
    ], size=13, color=RGBColor(0xDD, 0xE8, 0xF0))
    x = 0.9
    for code, name, _ in PHASES:
        col, soft = PHASE_COLOR[code]
        box(s, x, 5.85, 2.85, 0.7, f"{code}  {name}", fill=soft, line=None, size=9.5, color=col, bold=True)
        x += 2.95


LANES = ["หน่วยงาน", "งานงบประมาณ", "ระบบ (อัตโนมัติ)", "ปลายทาง: จัดซื้อจัดจ้าง"]


def slide_workflow(prs, page, total):
    s = blank(prs)
    header(s, "Workflow ภาพรวม: จากตั้งค่า → คำของบ → อนุมัติ → แผนงบพร้อมใช้",
           "Swimlane แยกตามผู้รับผิดชอบ · 'ขั้น 0–8' คือลำดับขั้นตอน · สิ้นสุดที่ส่งมอบแผนงบให้ชุดจัดซื้อจัดจ้าง")

    lane_x, lane_w = 0.3, 12.73
    label_w = 1.25
    top = 1.0
    lane_h = 1.4
    for i, name in enumerate(LANES):
        y = top + i * lane_h
        box(s, lane_x, y, lane_w, lane_h, "", fill=LANE_A if i % 2 == 0 else LANE_B, line=LINE,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
        box(s, lane_x, y, label_w, lane_h, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)

    x0 = lane_x + label_w + 0.12
    colw = (lane_x + lane_w - x0 - 0.05) / 10
    bw, bh = colw - 0.14, 0.9

    def cx(c):
        return x0 + c * colw + colw / 2

    def by(lane):
        return top + lane * lane_h + (lane_h - bh) / 2 + 0.06

    def step(lane, col, num, text, fill, line, span=1):
        x = cx(col) - bw / 2
        w = bw + (span - 1) * colw
        y = by(lane)
        box(s, x, y, w, bh, [(num, {"bold": True, "size": 9, "color": line}), (text, {"size": 8.5})],
            fill=fill, line=line, size=8.5, lw=1.25, margin=0.03)
        return dict(l=x, r=x + w, t=y, b=y + bh, cx=x + w / 2, cy=y + bh / 2)

    B_, BS = BLUE, BLUE_SOFT
    T_, TS = TEAL, TEAL_SOFT
    G_, GS = GREEN, GREEN_SOFT
    M_, MS = MUTED, RGBColor(0xEE, 0xF1, 0xF4)

    s0 = step(1, 0, "ขั้น 0", "ตั้งค่าข้อมูลหลัก + แผนประจำปี", MS, M_)
    s1 = step(0, 0, "ขั้น 1", "สร้างใบคำของบ", BS, B_)
    s2 = step(0, 1, "ขั้น 2", "เพิ่มรายการ (โหลด / Import)", BS, B_)
    s3 = step(0, 2, "ขั้น 3", "ส่งใบคำขอ", BS, B_)
    s4 = step(1, 3, "ขั้น 4", "รับเรื่อง / เริ่มพิจารณา", TS, T_)
    s5 = step(1, 4, "ขั้น 5", "จัดสรรยอด", TS, T_)
    s6 = step(1, 5, "ขั้น 6", "อนุมัติ", TS, T_)
    sb = step(2, 5, "ระบบ", "สร้าง budget.lines ในแผนประจำปี", GS, G_)
    s7 = step(2, 6, "ขั้น 7", "แผนงบที่อนุมัติ พร้อมใช้งาน", GS, G_)
    s8 = step(1, 7, "ขั้น 8", "พิมพ์ / Export / Dashboard สถานะ", TS, T_)
    end = step(3, 5, "ส่งมอบ (สิ้นสุดชุดงบประมาณ)",
               "ชุดจัดซื้อจัดจ้างนำแผนงบที่อนุมัติไปทำใบขอซื้อ (PR) เลือกคำของบ + รายการงบ", AMBER_SOFT, AMBER, span=4)

    route(s, [(s0["cx"], s0["t"]), (s1["cx"], s1["b"])])
    route(s, [(s1["r"], s1["cy"]), (s2["l"], s2["cy"])])
    route(s, [(s2["r"], s2["cy"]), (s3["l"], s3["cy"])])
    route(s, [(s3["r"], s3["cy"]), (s4["cx"], s3["cy"]), (s4["cx"], s4["t"])])
    route(s, [(s4["r"], s4["cy"]), (s5["l"], s5["cy"])])
    route(s, [(s5["r"], s5["cy"]), (s6["l"], s6["cy"])])
    route(s, [(s6["cx"], s6["b"]), (sb["cx"], sb["t"])], color=G_)
    route(s, [(sb["r"], sb["cy"]), (s7["l"], s7["cy"])], color=G_)
    route(s, [(s7["cx"] - 0.2, s7["b"]), (s7["cx"] - 0.2, end["t"])], color=AMBER, w=2)
    route(s, [(s7["r"], s7["cy"]), (s8["cx"], s7["cy"]), (s8["cx"], s8["b"])], color=G_, dash=True)

    ry = top + 0.11
    route(s, [(s4["cx"] + 0.3, s4["t"]), (s4["cx"] + 0.3, ry), (s1["cx"] - 0.3, ry),
              (s1["cx"] - 0.3, s1["t"])], color=RED, dash=True, w=1.25)
    tb(s, s4["cx"] + 0.4, ry + 0.2, 3.6, 0.5, ["ตีกลับ / ตั้งเป็นร่าง", "→ หน่วยงานแก้ไขแล้วส่งใหม่"],
       size=8, color=RED)

    ly = top + 4 * lane_h + 0.1
    items = [("ข้อมูลหลัก", MS, M_), ("หน่วยงาน", BS, B_), ("งานงบประมาณ / ผู้บริหาร", TS, T_),
             ("ระบบอัตโนมัติ", GS, G_), ("ส่งมอบชุดจัดซื้อ", AMBER_SOFT, AMBER)]
    x = 0.4
    for name, fillc, linec in items:
        box(s, x, ly, 0.28, 0.2, "", fill=fillc, line=linec, lw=1.25)
        tb(s, x + 0.33, ly - 0.03, 2.3, 0.26, name, size=8.5, color=MUTED)
        x += 2.35 if len(name) > 12 else 1.7
    seg(s, 10.8, ly + 0.1, 11.3, ly + 0.1, color=G_, dash=True)
    tb(s, 11.35, ly - 0.03, 1.7, 0.26, "อ่านข้อมูลงบ", size=8.5, color=MUTED)
    footer(s, page, total)


def slide_state(prs, page, total):
    s = blank(prs)
    header(s, "สถานะใบคำของบ และการส่งมอบแผนงบที่อนุมัติ",
           "ใบคำของบ (departmental.budget.request) จนถึงแผนงบที่อนุมัติ พร้อมใช้งาน")

    tb(s, 0.4, 1.0, 8, 0.3, "1) สถานะใบคำของบ", size=13, bold=True, color=NAVY)
    states = [
        ("Draft", "ร่าง", MUTED, RGBColor(0xEE, 0xF1, 0xF4)),
        ("Submitted", "ส่งให้งานงบแล้ว", BLUE, BLUE_SOFT),
        ("Received", "งานงบรับเรื่อง", TEAL, TEAL_SOFT),
        ("Review", "อยู่ระหว่างพิจารณา", TEAL, TEAL_SOFT),
        ("Approved", "อนุมัติ", GREEN, GREEN_SOFT),
    ]
    x, y, w, h, gap = 0.5, 1.5, 2.0, 0.9, 0.55
    xs = []
    for i, (en, th, col, soft) in enumerate(states):
        xx = x + i * (w + gap)
        xs.append(xx)
        box(s, xx, y, w, h, [(en, {"bold": True, "size": 13, "color": col}), (th, {"size": 10})],
            fill=soft, line=col, lw=1.5)
    labels = [("ส่งใบคำขอ", "หน่วยงาน"), ("รับเรื่อง", "งานงบ"), ("เริ่มพิจารณา", "งานงบ"),
              ("อนุมัติ", "งานงบ")]
    for i, (lb, who) in enumerate(labels):
        x1 = xs[i] + w
        x2 = xs[i + 1]
        seg(s, x1, y + h / 2, x2, y + h / 2, color=SLATE, w=1.75)
        tb(s, x1 - 0.2, y + h / 2 - 0.55, gap + 0.4, 0.5, [(lb, {"size": 8.5, "bold": True}),
                                                          (who, {"size": 7.5, "color": MUTED})],
           align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM)
    # ข้าม Received → Approved
    route(s, [(xs[2] + w / 2, y + h), (xs[2] + w / 2, y + h + 0.35), (xs[4] + w / 2, y + h + 0.35),
              (xs[4] + w / 2, y + h)], color=SLATE, w=1.25, dash=True)
    tb(s, xs[2] + w / 2 + 0.2, y + h + 0.37, 5.0, 0.25, "อนุมัติได้ทันทีจาก Received (ข้ามขั้นพิจารณา)", size=8, color=MUTED)
    # Rejected
    box(s, xs[1] + 0.6, 3.85, 2.4, 0.8, [("Rejected", {"bold": True, "size": 13, "color": RED}),
                                         ("ตีกลับ", {"size": 10})], fill=RED_SOFT, line=RED, lw=1.5)
    route(s, [(xs[3] + 0.5, y + h), (xs[3] + 0.5, 4.25), (xs[1] + 3.0, 4.25)], color=RED, dash=True, w=1.25)
    tb(s, xs[3] - 1.2, 4.3, 3.8, 0.45, "ปุ่ม 'ตีกลับ' (ทุกสถานะที่ไม่ใช่ Draft / Approved / Rejected)", size=8,
       color=RED)
    box(s, xs[0] - 0.1, 3.85, 2.2, 0.8, [("ตั้งเป็นร่าง", {"bold": True, "size": 11, "color": MUTED}),
                                         ("ลบ budget.lines ที่เคยสร้าง", {"size": 8.5})],
        fill=WHITE, line=MUTED, lw=1.0, dash=True)
    route(s, [(xs[1] + 0.6, 4.25), (xs[0] + 2.1, 4.25)], color=MUTED, dash=True, w=1.25)
    route(s, [(xs[0] + 1.0, 3.85), (xs[0] + 1.0, y + h)], color=MUTED, dash=True, w=1.25)

    # ผลตอนอนุมัติ
    box(s, xs[4] - 0.4, 3.0, 2.8, 1.0, [("เมื่ออนุมัติ", {"bold": True, "size": 9.5, "color": GREEN}),
                                        ("• สร้าง budget.lines (planned = ยอดจัดสรร)", {"size": 8.5}),
                                        ("• กำหนด budget_record_id = แผนประจำปี", {"size": 8.5})],
        fill=GREEN_SOFT, line=GREEN, align=PP_ALIGN.LEFT, size=8.5)
    route(s, [(xs[4] + 1.6, y + h), (xs[4] + 1.6, 3.0)], color=GREEN, w=1.25)

    # ส่งมอบแผนงบที่อนุมัติ
    tb(s, 0.4, 5.0, 12, 0.3, "2) เมื่ออนุมัติแล้ว แผนงบพร้อมใช้งาน (ส่งมอบให้ชุดจัดซื้อจัดจ้าง)", size=13, bold=True, color=NAVY)
    items = [
        ("คำของบ Approved", "departmental.budget.request", "สถานะ = approved", GREEN, GREEN_SOFT),
        ("รายการงบ (budget.lines)", "planned_amount", "งบจัดสรร = วงเงินที่ใช้ได้", GREEN, GREEN_SOFT),
        ("พร้อมให้ PR เลือก", "budget_plan_request_id", "เลือกเฉพาะคำของบที่อนุมัติ", BLUE, BLUE_SOFT),
    ]
    sx, sy, sw, sh, sg = 0.5, 5.4, 3.1, 0.95, 0.45
    for k, (nm, field, how, col, soft) in enumerate(items):
        xx = sx + k * (sw + sg)
        box(s, xx, sy, sw, sh, [(nm, {"bold": True, "size": 12, "color": col}),
                                (field, {"size": 8.5, "color": MUTED}),
                                (how, {"size": 8.5})], fill=soft, line=col, lw=1.5)
        if k < 2:
            seg(s, xx + sw, sy + sh / 2, xx + sw + sg, sy + sh / 2, color=SLATE, w=1.75)
    box(s, sx + 3 * (sw + sg) - 0.05, sy, 1.9, sh, [("ไปชุด", {"size": 9, "color": MUTED}),
                                                  ("จัดซื้อจัดจ้าง", {"bold": True, "size": 11, "color": NAVY})],
        fill=WHITE, line=NAVY, lw=1.5, dash=True)
    seg(s, sx + 2 * (sw + sg) + sw, sy + sh / 2, sx + 3 * (sw + sg) - 0.05, sy + sh / 2, color=SLATE, w=1.75)
    tb(s, 0.5, 6.5, 12.3, 0.6, [
        ("ขอบเขตชุดงบประมาณ สิ้นสุดที่ 'แผนงบที่อนุมัติและพร้อมใช้'", {"bold": True, "size": 11, "color": NAVY}),
        ("การจองงบ (PR) · ผูกพัน (PO) · ใช้จริง (Bill) เกิดในชุดจัดซื้อจัดจ้าง และอ่านค่ากลับมาแสดงในรายงาน/Dashboard", {"size": 9, "color": MUTED}),
    ])
    footer(s, page, total)


def slide_dfd(prs, page, total):
    s = blank(prs)
    header(s, "Data Flow Diagram ระดับ 1 ของระบบงบประมาณ",
           "วงกลมมน = กระบวนการ (P) · กล่อง = ที่เก็บข้อมูล (D) · เส้นประ = ผู้ใช้ภายนอก · ลูกศร = ข้อมูลที่ไหล")

    def proc(x, y, code, name, actor, col, soft):
        box(s, x, y, 2.7, 1.0, [(f"{code}  {name}", {"bold": True, "size": 10.5, "color": col}),
                                (f"ผู้ทำ: {actor}", {"size": 8.5, "color": MUTED})],
            fill=soft, line=col, lw=1.75, radius=0.5)
        return dict(l=x, r=x + 2.7, t=y, b=y + 1.0, cx=x + 1.35, cy=y + 0.5)

    def store(x, y, w, code, name, sub):
        box(s, x, y, w, 0.85, [(f"{code}  {name}", {"bold": True, "size": 10, "color": NAVY}),
                               (sub, {"size": 8, "color": MUTED})],
            fill=WHITE, line=NAVY, lw=1.25, shape=MSO_SHAPE.RECTANGLE, align=PP_ALIGN.CENTER)
        return dict(l=x, r=x + w, t=y, b=y + 0.85, cx=x + w / 2, cy=y + 0.425)

    P1 = proc(0.6, 1.15, "P1", "ตั้งค่าข้อมูลหลัก", "งานงบประมาณ", MUTED, RGBColor(0xEE, 0xF1, 0xF4))
    P2 = proc(5.3, 1.15, "P2", "จัดทำและส่งคำของบ", "หน่วยงาน", BLUE, BLUE_SOFT)
    P3 = proc(10.0, 1.15, "P3", "พิจารณา จัดสรร อนุมัติ", "งานงบประมาณ", TEAL, TEAL_SOFT)

    D1 = store(0.6, 3.0, 2.7, "D1", "ข้อมูลหลักงบ", "แหล่งเงิน/ประเภท/กลุ่ม/หมวด/แผน")
    D2 = store(5.3, 3.0, 2.7, "D2", "ใบคำของบ", "departmental.budget.request")
    D3 = store(10.0, 3.0, 2.7, "D3", "รายการงบประมาณ", "budget.lines (แผนประจำปี)")

    P4 = proc(0.6, 5.0, "P4", "รายงานและติดตามสถานะ", "ผู้บริหาร / งานงบ", GREEN, GREEN_SOFT)
    EXT = box(s, 10.0, 5.0, 2.7, 1.0, [("ระบบจัดซื้อจัดจ้าง", {"bold": True, "size": 11, "color": AMBER}),
                                       ("ผู้ใช้แผนงบที่อนุมัติ (ทำ PR)", {"size": 8.5, "color": MUTED})],
              fill=AMBER_SOFT, line=AMBER, lw=1.75, shape=MSO_SHAPE.RECTANGLE, dash=True)
    ext = dict(l=10.0, r=12.7, t=5.0, b=6.0, cx=11.35, cy=5.5)

    def lab(x, y, t, w=2.2, align=PP_ALIGN.LEFT, color=MUTED):
        tb(s, x, y, w, 0.4, t, size=8, color=color, align=align)

    seg(s, P1["cx"], P1["b"], D1["cx"], D1["t"], color=SLATE)
    lab(P1["cx"] + 0.08, 2.35, "ข้อมูลหลัก / Excel import")
    seg(s, D1["r"], D1["t"] + 0.2, P2["l"] + 0.2, P2["b"], color=SLATE)
    lab(3.4, 3.3, "ตัวเลือกแบบฟอร์ม / แหล่งเงิน / แผน", w=1.85)
    seg(s, P2["cx"], P2["b"], D2["cx"], D2["t"], color=SLATE)
    lab(P2["cx"] + 0.08, 2.35, "ใบคำของบ + รายการ", w=1.6)
    seg(s, D2["r"], D2["cy"] - 0.15, P3["l"] + 0.35, P3["b"], color=SLATE, both=True)
    lab(8.15, 3.3, "ใบที่ส่งแล้ว → ยอดจัดสรร / สถานะกลับ", w=1.8)
    seg(s, P3["cx"], P3["b"], D3["cx"], D3["t"], color=SLATE)
    lab(P3["cx"] + 0.08, 2.35, "สร้างรายการงบ (planned)", w=1.8)
    # ส่งมอบ
    seg(s, D3["cx"], D3["b"], ext["cx"], ext["t"], color=AMBER, w=2.25)
    lab(ext["cx"] + 0.1, 4.2, "แผนงบที่อนุมัติ พร้อมใช้ (INPUT ของชุดจัดซื้อ)", w=1.7, color=AMBER)
    # อ่านรายงาน
    seg(s, D2["l"] + 0.2, D2["b"], P4["r"] - 0.2, P4["t"] + 0.05, color=GREEN)
    seg(s, D3["l"] + 0.1, D3["b"], P4["r"], P4["cy"] - 0.35, color=GREEN)
    lab(3.45, 5.5, "อ่านคำของบ / งบ", w=1.7, color=GREEN)
    seg(s, D1["cx"], D1["b"], P4["cx"], P4["t"], color=GREEN, dash=True)
    lab(D1["cx"] + 0.08, 4.3, "ชื่อกลุ่ม / หมวด", w=1.5, color=GREEN)
    footer(s, page, total)



def main():
    configure("ระบบงบประมาณ · VPK ERP", "ที่มา: odoo18-custom-addons/vpk_budget (models, wizard, views)")
    prs = new_prs()
    pages = io_pages(FUNCTIONS, PHASES)
    total = 4 + len(pages)
    slide_title(prs)
    slide_workflow(prs, 2, total)
    slide_state(prs, 3, total)
    slide_dfd(prs, 4, total)
    for k, (code, ch, i, n) in enumerate(pages):
        slide_io(prs, ch, PHASES, PHASE_COLOR, code, i, n, 5 + k, total)
    prs.save(OUT)
    print("saved", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    main()
