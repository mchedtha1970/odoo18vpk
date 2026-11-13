#!/usr/bin/env python3
"""Workflow / Dataflow งานคลังสินค้า (VPK Odoo 18)
แบ่งเป็น: การรับสินค้า · การขอเบิกสินค้า · การโอนสินค้า · การตัดจ่ายสินค้า

รัน: python3 docs/build_warehouse_dataflow_pptx.py
ผลลัพธ์: docs/Workflow-Dataflow-งานคลังสินค้า.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dataflow_lib import *  # noqa: E402,F401,F403
from warehouse_dataflow_data import FUNCTIONS, INTEGRATION, PHASES  # noqa: E402

OUT = Path(__file__).parent / "Workflow-Dataflow-งานคลังสินค้า.pptx"
GREY_SOFT = RGBColor(0xEE, 0xF1, 0xF4)
PINK = RGBColor(0xA8, 0x3A, 0x7A)
PINK_SOFT = RGBColor(0xFA, 0xEA, 0xF3)
HIS = RGBColor(0x6B, 0x4C, 0xA0)
HIS_SOFT = RGBColor(0xF1, 0xEC, 0xFA)
PHASE_COLOR = {
    "A": (AMBER, AMBER_SOFT),
    "B": (BLUE, BLUE_SOFT),
    "C": (TEAL, TEAL_SOFT),
    "D": (GREEN, GREEN_SOFT),
    "E": (PINK, PINK_SOFT),
}

# สไตล์กล่อง: (fill, line)
STYLE = {
    "u": (BLUE_SOFT, BLUE),      # หน่วยงาน / ผู้ขอ
    "w": (AMBER_SOFT, AMBER),    # คลัง
    "s": (TEAL_SOFT, TEAL),      # ระบบ
    "p": (GREY_SOFT, NAVY),      # จัดซื้อ / บัญชี
    "x": (HIS_SOFT, HIS),        # ภายนอก: ผู้ขาย / HIS
    "e": (RED_SOFT, RED),        # ผิดปกติ
    "ok": (GREEN_SOFT, GREEN),   # ผลลัพธ์
}
LEGEND = [("หน่วยงาน / ผู้ขอ", "u"), ("คลัง", "w"), ("ระบบ", "s"), ("จัดซื้อ / บัญชี", "p"),
          ("ภายนอก (ผู้ขาย / HIS)", "x"), ("ผิดปกติ", "e"), ("ผลลัพธ์", "ok")]


# ------------------------------------------------------------------ หน้าปก
def slide_title(prs):
    s = blank(prs)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SLIDE_W), Inches(SLIDE_H))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False
    tb(s, 0.9, 1.9, 11.5, 1.0, "Workflow & Dataflow งานคลังสินค้า", size=38, color=WHITE, bold=True)
    tb(s, 0.9, 2.95, 11.5, 0.6, "Input / Process / Output ของแต่ละ function", size=20,
       color=RGBColor(0xBF, 0xD6, 0xE6))
    box(s, 0.9, 3.85, 11.5, 0.75,
        [("แบ่ง 5 สาย: รับสินค้า · ขอเบิก · โอน · ตัดจ่าย · การผลิตยา",
          {"bold": True, "size": 13, "color": GREEN}),
         ("รับจากผู้ขายตาม PO → ขอเบิก → โอนถึงปลายทาง → ตัดจ่ายตามล็อต (FEFO) · ผลิตยาจากสูตรเข้าคลัง",
          {"size": 11, "color": SLATE})],
        fill=GREEN_SOFT, line=GREEN, lw=1.5, align=PP_ALIGN.LEFT, margin=0.2)
    tb(s, 0.9, 4.8, 11.5, 0.6, [
        "โรงพยาบาลวชิระภูเก็ต · VPK ERP (Odoo 18) · module vpk_stock_* · vpk_his_api · vpk_mobile_barcode",
        "เชื่อมกับชุดจัดซื้อจัดจ้าง (PO → ใบรับ · สต็อกไม่พอ → PR) และ HIS (ตัดจ่าย / เบิกเติม)",
    ], size=13, color=RGBColor(0xDD, 0xE8, 0xF0))
    x = 0.9
    for code, name, _ in PHASES:
        col, soft = PHASE_COLOR[code]
        box(s, x, 5.85, 2.3, 0.7, f"{code}  {name}", fill=soft, line=None, size=10.5, color=col, bold=True)
        x += 2.4


# ------------------------------------------------------------------ ภาพรวม 4 สาย
OVERVIEW = [
    ("A", "การรับสินค้า",
     ["จัดซื้อยืนยัน PO", "ระบบสร้างใบรับ WH/IN"],
     ["ของมาส่ง", "QC ผ่าน", "กรรมการ ตรวจรับ", "บันทึก ล็อต", "รับเข้าคลัง"],
     ["สต็อกคลังเพิ่ม (ตามล็อต)", "PO อัปเดตปริมาณรับ", "ต้นทุนเฉลี่ยขยับ"]),
    ("B", "การขอเบิกสินค้า",
     ["หน่วยงานขอเอง", "Min-Max อัตโนมัติ 23:30", "คำขอจาก HIS"],
     ["ใบขอเบิก (ร่าง)", "คลังรับรายการ", "ตรวจสต็อกต้นทาง", "จอง FEFO / ใบค้าง", "ไม่มีของ ขอซื้อ"],
     ["ใบหยิบพร้อม (ไปขั้นโอน)", "หรือ PR ไปชุดจัดซื้อ"]),
    ("C", "การโอนสินค้า",
     ["ใบขอเบิกที่คลังรับแล้ว", "(ใบหยิบ + ใบแพ็ค + ใบปลายทาง)"],
     ["หยิบ (PICK)", "แพ็ค (PACK)", "ปลายทาง (INT)", "ของเข้าปลายทาง"],
     ["สต็อกย้ายต้นทาง → ปลายทาง", "ยอดรวมและต้นทุนเท่าเดิม"]),
    ("D", "การตัดจ่ายสินค้า",
     ["HIS ตัดจ่ายรายวัน", "ใบจ่ายออก (เบิกใช้ภายใน)", "ผลนับสต็อก"],
     ["รับชุด / ใบจ่าย", "Validate", "Post / จ่าย", "ตัดล็อต FEFO", "Reversal"],
     ["สต็อกลดตามล็อต", "ชุด HIS เป็น Posted"]),
    ("E", "การผลิตยา",
     ["สูตรผลิต (BoM)", "วัตถุดิบใน PHAR/Stock"],
     ["เปิดใบสั่งผลิต", "ยืนยัน จองวัตถุดิบ", "บันทึกล็อต", "คำสั่งงาน 6 ขั้น", "ผลิตทั้งหมด"],
     ["ยาเข้าคลังตามล็อต", "วัตถุดิบถูกตัดตามสูตร"]),
]


def slide_overview(prs, page, total):
    s = blank(prs)
    header(s, "ภาพรวมงานคลังสินค้า: 5 สาย",
           "ที่มา (Trigger) → ขั้นตอนหลัก → ผลต่อสต็อก · สายขอเบิกต่อเข้าสายโอนเมื่อคลังรับรายการ")
    y0, bh, gap = 0.98, 0.96, 0.08
    for i, (code, name, src, stages, res) in enumerate(OVERVIEW):
        y = y0 + i * (bh + gap)
        col, soft = PHASE_COLOR[code]
        box(s, 0.35, y, 1.55, bh, [(f"{code}", {"size": 18, "bold": True, "color": WHITE}),
                                   (name, {"size": 11.5, "bold": True, "color": WHITE})],
            fill=col, line=col, radius=0.1)
        box(s, 2.1, y, 2.2, bh,
            [("ที่มา", {"size": 8.5, "bold": True, "color": col})] + [("• " + t, {"size": 9}) for t in src],
            fill=soft, line=col, align=PP_ALIGN.LEFT, radius=0.08, margin=0.1)
        seg(s, 1.9, y + bh / 2, 2.1, y + bh / 2, color=SLATE, w=1.75)
        seg(s, 4.3, y + bh / 2, 4.5, y + bh / 2, color=SLATE, w=1.75)
        n = len(stages)
        cx0, cw_total = 4.5, 6.1
        ar = 0.14
        cw = (cw_total - ar * (n - 1)) / n
        for k, st in enumerate(stages):
            x = cx0 + k * (cw + ar)
            box(s, x, y + 0.2, cw, bh - 0.4, st, fill=WHITE, line=col, lw=1.5, size=8.5, bold=True, color=SLATE,
                radius=0.15, margin=0.03)
            if k < n - 1:
                seg(s, x + cw, y + bh / 2, x + cw + ar, y + bh / 2, color=col, w=1.5)
        seg(s, cx0 + cw_total, y + bh / 2, 10.8, y + bh / 2, color=SLATE, w=1.75)
        box(s, 10.8, y, 2.2, bh,
            [("ผลลัพธ์", {"size": 8.5, "bold": True, "color": GREEN})] + [("• " + t, {"size": 9}) for t in res],
            fill=GREEN_SOFT, line=GREEN, align=PP_ALIGN.LEFT, radius=0.08, margin=0.1)
    yb = y0 + 5 * (bh + gap) + 0.02
    box(s, 0.35, yb, 12.65, 0.62,
        [("Dashboard สถานะงานคลัง (ติดตามแต่ละสาย)", {"size": 8.5, "bold": True, "color": NAVY}),
         ("รับ: รอรถมา → ตรวจรับ → QC → จัดเก็บ → เสร็จสิ้น  ·  โอน: สร้างใบโอน → จัดสินค้า → ขนส่ง → รอรับ → รับแล้ว  ·  "
          "จ่ายออก: รออนุมัติ (ใบร่าง) → รอจัด → กำลังจัด → พร้อมรับ → จ่ายแล้ว", {"size": 8.5})],
        fill=GREY_SOFT, line=LINE, align=PP_ALIGN.LEFT, radius=0.08, margin=0.12)
    footer(s, page, total)


# ------------------------------------------------------------------ Swimlane ทั่วไป
def _swim_style_flags(st):
    """แยก style หลักกับ flag: d=เพชร, top/bot=ตำแหน่งในเลน, sm=กล่องเล็กลง."""
    flags = (st or "u").split(":")
    return {
        "style": flags[0],
        "diamond": "d" in flags[1:],
        "top": "top" in flags[1:],
        "bot": "bot" in flags[1:],
        "sm": "sm" in flags[1:],
    }


def slide_swim(prs, title, subtitle, lanes, steps, edges, notes, page, total, gap=0.3):
    """steps: id -> (lane, col, title, text, tag, style)
    style เช่น 'w:d' = เพชร · 'u:top:sm' = อยู่ด้านบนเลนและเล็กลง
    edges: (from, to, label, kind, opts) kind: 'ok'|'bad'|'dash'|None"""
    s = blank(prs)
    header(s, title, subtitle)
    lane_x, lane_w, label_w, top = 0.3, 12.73, 1.25, 1.0
    n = len(lanes)
    lane_h = 5.72 / n
    for i, name in enumerate(lanes):
        y = top + i * lane_h
        box(s, lane_x, y, lane_w, lane_h, "", fill=LANE_A if i % 2 == 0 else LANE_B, line=LINE,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
        box(s, lane_x, y, label_w, lane_h, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE, lw=0.75)
    ncols = max(max(v[1] for v in steps.values()), max((n_[2] for n_ in notes), default=0)) + 1
    x0 = lane_x + label_w + 0.12
    colw = (lane_x + lane_w - x0 - 0.05) / max(ncols, 8)
    bw = min(colw - gap, 1.35)
    bh = min(lane_h - 0.2, 0.98)

    def node_geom(sid):
        lane, col = steps[sid][0], steps[sid][1]
        flags = _swim_style_flags(steps[sid][5])
        cx = x0 + col * colw + colw / 2
        ly = top + lane * lane_h
        if flags["top"] or flags["bot"]:
            nbw = min(colw - gap, 0.87)
            nbh = min((lane_h - 0.34) / 2, 0.54)
            cy = (ly + 0.06 + nbh / 2) if flags["top"] else (ly + lane_h - 0.06 - nbh / 2)
        elif flags["sm"]:
            nbw, nbh = bw * 0.86, bh * 0.82
            cy = ly + lane_h / 2
        else:
            nbw, nbh = bw, bh
            cy = ly + lane_h / 2
        return cx, cy, nbw / 2, nbh / 2, nbw, nbh, flags

    def cxy(sid):
        cx, cy, *_ = node_geom(sid)
        return cx, cy

    # หมายเหตุ (วาดก่อน เพื่อให้อยู่ใต้เส้น)
    for lane, c0, c1, text in notes:
        nx = x0 + c0 * colw + 0.05
        nw = (c1 - c0 + 1) * colw - 0.1
        ny = top + lane * lane_h + 0.12
        box(s, nx, ny, nw, lane_h - 0.24, text if isinstance(text, list) else [(text, {"size": 8.5})],
            fill=None, line=MUTED, dash=True, align=PP_ALIGN.LEFT, margin=0.1, radius=0.08, color=MUTED)

    # เส้น
    for e in edges:
        a, b, label, kind = e[0], e[1], e[2], e[3]
        opt = e[4] if len(e) > 4 else {}
        ax, ay, ahw, ahh, *_ = node_geom(a)
        bx, by, bhw, bhh, *_ = node_geom(b)
        color = {"ok": GREEN, "bad": RED}.get(kind, SLATE)
        dash = kind == "dash"
        if abs(ay - by) < 0.05:
            if bx > ax:
                pts = [(ax + ahw, ay), (bx - bhw, by)]
            else:
                pts = [(ax - ahw, ay), (bx + bhw, by)]
        elif abs(ax - bx) < 0.05:
            pts = [(ax, ay + ahh), (bx, by - bhh)] if by > ay else [(ax, ay - ahh), (bx, by + bhh)]
        elif opt.get("mode") == "vh":
            sy = ay + ahh if by > ay else ay - ahh
            ex = bx - bhw if bx > ax else bx + bhw
            pts = [(ax, sy), (ax, by), (ex, by)]
        elif opt.get("mode") == "hv_side":
            sx = ax + ahw if bx > ax else ax - ahw
            ex = bx - bhw if bx > ax else bx + bhw
            pts = [(sx, ay), (ex, by)]
        else:
            sx = ax + ahw if bx > ax else ax - ahw
            ey = by - bhh if by > ay else by + bhh
            pts = [(sx, ay), (bx, ay), (bx, ey)]
        route(s, pts, color=color, w=1.6, dash=dash)
        if label:
            dx, dy = opt.get("lp", (0.04, -0.2))
            tb(s, pts[0][0] + dx, pts[0][1] + dy, 0.55, 0.18, label, size=7.5, color=color, bold=True)

    # กล่อง
    for sid, (lane, col, ttl, txt, tag, st) in steps.items():
        cx, cy, _hw, _hh, nbw, nbh, flags = node_geom(sid)
        fill, line = STYLE[flags["style"]]
        x = cx - nbw / 2
        y = cy - nbh / 2
        if flags["diamond"]:
            box(s, x - 0.05, y - 0.04, nbw + 0.1, nbh + 0.08,
                [(ttl, {"bold": True, "size": 8, "color": line})] + ([(tag, {"size": 7, "color": MUTED})] if tag else []),
                fill=fill, line=line, lw=1.5, shape=MSO_SHAPE.DIAMOND, margin=0.02)
            continue
        stacked = flags["top"] or flags["bot"]
        title_size = 7.0 if stacked else (8.0 if flags["sm"] else 8.5)
        text_size = 6.2 if stacked else (7.0 if flags["sm"] else 7.5)
        tag_size = 6.0 if stacked else (6.5 if flags["sm"] else 7)
        paras = [(ttl, {"bold": True, "size": title_size, "color": line})]
        if txt:
            paras.append((txt, {"size": text_size}))
        if tag:
            paras.append((tag, {"size": tag_size, "color": MUTED, "bold": True}))
        box(s, x, y, nbw, nbh, paras, fill=fill, line=line, lw=1.5 if flags["style"] == "ok" else 1.25,
            radius=0.1, margin=0.02 if stacked else 0.04)

    # legend
    lx = 0.35
    for name, k in LEGEND:
        f, l = STYLE[k]
        box(s, lx, 6.82, 0.18, 0.18, "", fill=f, line=l, lw=1, shape=MSO_SHAPE.RECTANGLE)
        w = 0.35 + 0.075 * len(name)
        tb(s, lx + 0.2, 6.78, w, 0.26, name, size=8, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)
        lx += 0.25 + w
    footer(s, page, total)


L_RECEIVE = ["จัดซื้อ / ระบบ", "คลัง", "ผู้ตรวจ QC", "กรรมการตรวจรับ", "ผู้ขาย"]
S_RECEIVE = {
    "po": (0, 0, "ยืนยัน PO", "ผู้ขายยืนยัน แล้วจัดซื้อยืนยัน", "W1", "p"),
    "rc": (0, 1, "สร้างใบรับ WH/IN", "สถานะพร้อม + วันคาดส่ง", "A1", "s"),
    "sd": (4, 2, "ของมาส่ง", "ผู้ขายส่งของ + ใบส่งของ", "ขั้น 1", "x"),
    "ck": (1, 3, "รับของ + นับจำนวน", "ที่พื้นที่รับของ ใส่ปริมาณตามจริง", "A3", "w"),
    "qc": (2, 4, "ทำ QC ผ่าน?", "", "ขั้น 1 · A4", "w:d"),
    "rt": (4, 5, "แจ้งผู้ขาย / ส่งคืน", "ของค้างพื้นที่รับของ", "A4", "e"),
    "wa": (3, 5, "กรรมการตรวจรับ", "ใบตรวจรับ (WA) ตรวจรับ + ลงวันที่", "ขั้น 2 · A6", "u"),
    "lt": (1, 6, "บันทึกล็อต", "ล็อต + วันหมดอายุ (ยังไม่ตรวจสอบ)", "A5", "w"),
    "vl": (1, 7, "รับของเข้าคลัง", "กดตรวจสอบใบรับ · ไม่ครบ → ใบรับค้าง", "ขั้น 3 · A7", "w"),
    "up": (0, 7, "อัปเดต PO", "ปริมาณรับ / ค้างรับ", "W2", "p"),
    "in": (1, 8, "สินค้าเข้าคลัง", "ยอดคงคลัง + · ต้นทุนเฉลี่ย", "W3", "ok"),
}
E_RECEIVE = [
    ("po", "rc", None, None), ("rc", "sd", None, None), ("sd", "ck", None, None),
    ("ck", "qc", None, None), ("qc", "wa", "ผ่าน", "ok"), ("qc", "rt", "ไม่ผ่าน", "bad", {"lp": (0.04, 0.02)}),
    ("wa", "lt", None, None), ("lt", "vl", None, None), ("vl", "up", None, None), ("vl", "in", None, "ok"),
    ("rt", "sd", "ส่งใหม่", "dash"),
]
N_RECEIVE = [
    (1, 0, 1, [("ตารางการส่ง (A2)", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ดูแผนรับของล่วงหน้าตามวันคาดส่ง", {"size": 8})]),
    (2, 0, 1, [("สิทธิ์และเงื่อนไข", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ผู้กดตรวจสอบต้องเป็นผู้มีสิทธิรับสินค้า · ทำได้หลัง QC ผ่านและกรรมการตรวจรับยืนยัน", {"size": 8})]),
    (3, 0, 1, [("กรรมการตรวจรับ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ทำหลัง QC ผ่านและก่อนรับเข้าคลัง · ไม่ผ่าน = รับของเข้าคลังไม่ได้", {"size": 8})]),
    (0, 3, 6, [("Dashboard งานรับ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("รอรถมา → ตรวจรับ → QC → จัดเก็บ → เสร็จสิ้น", {"size": 8})]),
    (4, 6, 8, [("ยืมของจากผู้ขาย (A8)", {"size": 8.5, "bold": True, "color": NAVY}),
               ("รับของยืมเข้าคลังยืมก่อน → เปิดใบขอซื้อตามหลัง → เมื่อรับตาม PO ระบบหักล้างยอดยืม", {"size": 8})]),
]

L_REQUEST = ["หน่วยงาน", "ระบบ (อัตโนมัติ)", "HIS / เภสัชกร", "คลัง", "จัดซื้อ"]
S_REQUEST = {
    "q1": (0, 0, "ขอเบิก / ขอโอน", "เลือกปลายทาง + รายการ + จำนวน", "B1", "u"),
    "q2": (1, 0, "Min-Max 23:30", "ยอดต่ำกว่าขั้นต่ำ → เติมถึงสูงสุด", "B2", "s"),
    "q3": (2, 0, "HIS เบิกเติม", "Validate → Ready → Post", "B3", "x"),
    "dr": (3, 2, "ใบขอเบิก (ร่าง)", "ต้นทาง = คลังกลาง", "B1-B3", "u"),
    "rv": (3, 3, "คลังรับรายการ", "ตั้งเป็นสิ่งที่ต้องทำ", "B4", "w"),
    "ck": (3, 4, "สต็อกต้นทาง?", "", "B4", "w:d"),
    "rs": (3, 5, "จองล็อต FEFO", "พอ: จองครบ · บางส่วน: จองเท่าที่มี + ใบค้าง", "B4", "w"),
    "go": (3, 6, "ไปการโอนสินค้า", "ใบหยิบ + แพ็ค + ปลายทาง", "C1-C3", "ok"),
    "pr": (4, 5, "สร้าง PR อัตโนมัติ", "คลังหลักไม่มีของ", "B5", "p"),
    "pq": (4, 6, "ส่งจัดซื้อ", "ไป e-GP → PO → รับสินค้า", "W4", "ok"),
}
E_REQUEST = [
    ("q1", "dr", None, None), ("q2", "dr", None, None), ("q3", "dr", None, None),
    ("dr", "rv", None, None), ("rv", "ck", None, None),
    ("ck", "rs", "มีของ", "ok", {"lp": (-0.42, -0.27)}), ("ck", "pr", "ไม่มีของ", "bad", {"mode": "vh", "lp": (0.05, 0.05)}),
    ("rs", "go", None, "ok"), ("pr", "pq", None, None),
]
N_REQUEST = [
    (0, 3, 8, [("หลักการ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ทุกทางเข้ารวมเป็นใบขอเบิกใบเดียวกัน · คลังเติมสต็อกหลักก่อน ไม่พอจึงเปิด PR · "
                "ใบ HIS Requisition ไม่ค้างเป็นใบร่าง (พร้อมทันที)", {"size": 8})]),
    (1, 3, 8, [("หมายเหตุ ERP", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ระบบยังไม่มีขั้นอนุมัติใบขอเบิก: ใบร่างถูกคลังรับรายการได้เลย (Dashboard เรียกใบร่างว่า 'รออนุมัติ')",
                {"size": 8})]),
]

L_TRANSFER = ["คลังต้นทาง (หยิบ)", "จุดแพ็ค / ขนส่ง", "ปลายทาง / หน่วยงาน", "ระบบ", "HIS (ถ้ามาจาก HIS)"]
S_TRANSFER = {
    "t1": (3, 0, "ใบขอเบิกพร้อม", "ระบบเปิด 3 ใบต่อเนื่อง", "B4", "s"),
    "t2": (3, 1, "จองล็อต FEFO", "บนใบหยิบ WH/PICK", "B4", "s"),
    "t3": (0, 2, "พิมพ์ใบหยิบ + หยิบของ", "จาก WH/Stock ตามล็อตที่จอง", "C1", "w"),
    "t4": (0, 3, "ตรวจสอบใบหยิบ", "ของเข้า Packing Zone", "C1", "w"),
    "t5": (1, 4, "แพ็คลงกล่อง", "กด 'ใส่ในแพ็ค' (WH/PACK)", "C2", "w"),
    "t6": (1, 5, "ตรวจสอบใบแพ็ค", "ของไป WH/Output", "C2", "w"),
    "t7": (2, 6, "อัปเดตปลายทาง", "กดตรวจสอบ WH/INT", "C3", "u"),
    "t8": (2, 7, "ของเข้าคลังปลายทาง", "ตามกฎชั้นเก็บ · ยอดรวมเท่าเดิม", "C3", "ok"),
    "t9": (4, 7, "ชุด HIS = Posted", "เมื่อโอนครบทุกขั้น", "B3", "x"),
}
E_TRANSFER = [
    ("t1", "t2", None, None), ("t2", "t3", None, None), ("t3", "t4", None, None), ("t4", "t5", None, None),
    ("t5", "t6", None, None), ("t6", "t7", None, None), ("t7", "t8", None, "ok"), ("t8", "t9", None, "dash"),
]
N_TRANSFER = [
    (3, 3, 6, [("แอปมือถือสแกนบาร์โค้ด (C4)", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ใช้ได้ทั้งขั้นหยิบ แพ็ค และตรวจสอบ: สแกนสินค้า/ล็อต → ใส่ในแพ็ค → ตรวจสอบ", {"size": 8})]),
    (0, 5, 8, [("Dashboard งานโอน", {"size": 8.5, "bold": True, "color": NAVY}),
               ("สร้างใบโอน → จัดสินค้า → ขนส่ง → รอรับ → รับแล้ว", {"size": 8})]),
    (4, 0, 5, [("ก่อนปลายทางตรวจสอบ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ของที่ตรวจสอบแล้วยังอยู่ระหว่างทาง (WH/Output) ยอดรวมโรงพยาบาลไม่เปลี่ยน", {"size": 8})]),
]

L_ISSUE_HIS = ["HIS (ระบบโรงพยาบาล)", "ระบบ ERP (API / คิว)", "คลัง / เภสัชกร", "สต็อก"]
S_ISSUE_HIS = {
    "h1": (0, 0, "ส่งสรุปตัดจ่ายรายวัน", "API stock-issues + Control Qty", "D2", "x"),
    "h2": (1, 1, "รับเข้าคิว (Draft)", "แมปหน่วยบริการ → คลัง/ตำแหน่ง", "D2", "s"),
    "h3": (2, 2, "ตรวจชุด (Validate)", "สินค้า จำนวน ล็อต ยอดรวม", "D3", "w"),
    "h4": (2, 3, "ผ่านตรวจ?", "", "D3", "w:d"),
    "h5": (1, 3, "Error", "แก้ข้อมูล / ส่งใหม่", "D3", "e"),
    "h6": (2, 4, "Ready → Post", "เฉพาะเภสัชกร", "D4", "w"),
    "h7": (3, 5, "ใบ HIS Consumption", "ตัดล็อตตาม HIS หรือ FEFO", "D4", "s"),
    "h8": (3, 6, "ของออกจากคลัง", "ไป HIS Consumption · ชุด Posted", "D4", "ok"),
    "h9": (0, 7, "HIS ส่ง Reversal", "อ้างชุดที่ Posted แล้ว", "D5", "x"),
    "h10": (3, 8, "คืนสต็อก", "ใบรับคืนของใบตัดจ่ายเดิม", "D5", "ok"),
}
E_ISSUE_HIS = [
    ("h1", "h2", None, None), ("h2", "h3", None, None), ("h3", "h4", None, None),
    ("h4", "h6", "ผ่าน", "ok", {"lp": (-0.4, -0.27)}), ("h4", "h5", "ไม่ผ่าน", "bad", {"lp": (0.08, -0.3)}), ("h5", "h3", None, "dash"),
    ("h6", "h7", None, None), ("h7", "h8", None, "ok"), ("h9", "h10", None, None),
]
N_ISSUE_HIS = [
    (1, 5, 7, [("สิทธิ์และกติกา", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ผู้เปิดคิว: กลุ่ม HIS Interface ผู้ใช้ · ผู้ Post: เภสัชกร · ชุด Posted ยกเลิกตรงไม่ได้ ต้องส่ง Reversal",
                {"size": 8})]),
    (2, 6, 7, [("ผลของ Reversal", {"size": 8.5, "bold": True, "color": NAVY}),
               ("สร้างใบรับคืนจากใบตัดจ่ายที่เสร็จแล้ว สต็อกกลับเข้าคลังต้นทาง", {"size": 8})]),
    (0, 2, 5, [("ตัวอย่างข้อมูลที่ HIS ส่ง", {"size": 8.5, "bold": True, "color": NAVY}),
               ("external_id · วันที่ · รหัสสินค้า · จำนวน · ล็อต · หน่วยบริการ · ยอดรวม (Control Qty Total)",
                {"size": 8})]),
]

L_ISSUE_OUT = ["หน่วยงาน (ผู้ขอ)", "คลัง (จ่ายออก)", "คลัง (นับสต็อก)", "ระบบ (สต็อก)"]
S_ISSUE_OUT = {
    "g1": (0, 0, "ขอเบิกใช้", "สร้างใบจ่ายออก (OUT)", "D1", "u"),
    "g2": (1, 1, "ใบร่าง", "Dashboard: รออนุมัติ", "D1", "w"),
    "g3": (1, 2, "ยืนยัน → รอจัด", "จองของต้นทาง", "D1", "w"),
    "g4": (1, 3, "กำลังจัด", "จองล็อตตาม FEFO", "D1", "w"),
    "g5": (1, 4, "พร้อมรับ", "จัดของครบ", "D1", "w"),
    "g6": (1, 5, "ตรวจสอบ → จ่ายแล้ว", "กดตรวจสอบที่คลัง", "D1", "w"),
    "g7": (0, 6, "หน่วยงานรับของ", "", "D1", "u"),
    "g8": (3, 6, "ยอดลดตามล็อต", "ตัดสต็อกต้นทาง", "D1", "ok"),
    "n1": (2, 0, "เปิดใบนับ / สแกน", "Count Sheet หรือแอปมือถือ", "D6", "w"),
    "n2": (2, 1, "ใส่จำนวนที่นับได้", "ที่ตำแหน่งนั้น", "D6", "w"),
    "n3": (2, 2, "มีส่วนต่าง?", "", "D6", "w:d"),
    "n4": (2, 3, "ระบุเหตุผล", "แล้วอัปเดตปริมาณ", "D6", "w"),
    "n5": (3, 4, "ยอดตรงตามที่นับ", "ส่วนต่างบันทึกเป็นการปรับ", "D6", "ok"),
}
E_ISSUE_OUT = [
    ("g1", "g2", None, None), ("g2", "g3", None, None), ("g3", "g4", None, None), ("g4", "g5", None, None),
    ("g5", "g6", None, None), ("g6", "g7", None, None), ("g6", "g8", None, "ok"),
    ("n1", "n2", None, None), ("n2", "n3", None, None), ("n3", "n4", "ต่าง", "bad", {"lp": (0.04, -0.2)}),
    ("n4", "n5", None, "ok"),
]
N_ISSUE_OUT = [
    (3, 0, 3, [("หมายเหตุ", {"size": 8.5, "bold": True, "color": NAVY}),
               ("ถ้าไม่ต่าง ไม่ต้องปรับ · ใบจ่ายออกต้องยืนยันก่อน จึงจัดและจ่ายของได้", {"size": 8})]),
]


L_PROD = ["เภสัชกร / ผู้วางแผนผลิต", "ห้องผลิต", "ระบบ (สต็อก)"]
S_PROD = {
    "e1": (0, 0, "สูตรผลิต (BoM)", "ส่วนประกอบ + ขั้นผลิต", "E1", "w"),
    "e2": (0, 1, "เปิดใบสั่งผลิต", "เลือกยา · จำนวนรุ่นนี้", "E2", "w"),
    "e3": (2, 1, "ยืนยัน + จองวัตถุดิบ", "ได้เลข PHAR/MO", "E3", "s"),
    "e4": (0, 2, "บันทึกล็อตที่ผลิต", "ก่อนผลิตทั้งหมด", "E4", "w"),
    "w1": (1, 3, "ชั่งวัตถุดิบ", "ห้องชั่ง", "E5", "u"),
    "w2": (1, 4, "ผสม + แกรนูล", "", "E5", "u"),
    "w3": (1, 5, "อบแห้ง", "", "E5", "u"),
    "w4": (1, 6, "ตอกเม็ด", "", "E5", "u"),
    "w5": (1, 7, "บรรจุแผง", "", "E5", "u"),
    "w6": (1, 8, "QC + ปล่อยผ่านรุ่น", "ห้องควบคุมคุณภาพ", "E5", "u"),
    "e6": (2, 8, "ผลิตทั้งหมด", "ยาเข้า PHAR/Stock ตามล็อต · ตัดวัตถุดิบ", "E6", "ok"),
}
E_PROD = [
    ("e1", "e2", None, None), ("e2", "e3", None, None), ("e3", "e4", None, None), ("e4", "w1", None, None),
    ("w1", "w2", None, None), ("w2", "w3", None, None), ("w3", "w4", None, None), ("w4", "w5", None, None),
    ("w5", "w6", None, None), ("w6", "e6", None, "ok"),
]
N_PROD = [
    (0, 4, 8, [("ข้อกำหนด", {"size": 8.5, "bold": True, "color": NAVY}),
               ("เมนูการผลิตขึ้นเมื่ออยู่ในกลุ่มการผลิต · ประเภทการปฏิบัติการ 'คลังยา: Manufacturing' · "
                "ตำแหน่ง PHAR/Stock · ผลิตเต็มรุ่นต้องมีวัตถุดิบครบก่อนยืนยัน", {"size": 8})]),
    (2, 3, 6, [("เชื่อมกับสายอื่น", {"size": 8.5, "bold": True, "color": NAVY}),
               ("วัตถุดิบมาจากสายรับสินค้า (A) · ยาที่ผลิตแล้วใช้ต่อในสายขอเบิก โอน ตัดจ่าย (B–D) · "
                "กด 'ผลิตทั้งหมด' ปิดทุกคำสั่งงานพร้อมกันได้", {"size": 8})]),
]


# ------------------------------------------------------------------ DFD
DFD_ROWS = [
    ("A", "การรับสินค้า",
     ("จัดซื้อ / ผู้ขาย", ["PO ที่ยืนยัน (สินค้า ราคา วันคาดส่ง)", "ของ + ใบส่งของ"]),
     ["ใบรับ WH/IN", "ของมาส่ง → QC ผ่าน → กรรมการตรวจรับ → บันทึกล็อต → ตรวจสอบ"],
     ("เก็บที่", ["stock.picking · stock.move.line (ล็อต/EXP)", "vpk.stock.qc (QC) · work.acceptance (ใบตรวจรับ)"],
      ["ยอดคงคลัง + (ต้นทุนเฉลี่ย)", "ปริมาณรับบน PO · ใบรับค้าง"])),
    ("B", "การขอเบิกสินค้า",
     ("หน่วยงาน / Min-Max / HIS", ["รายการ + จำนวน + ปลายทาง", "กฎขั้นต่ำ-สูงสุด · ชุดคำขอ HIS"]),
     ["ใบขอเบิก (ร่าง)", "คลังรับรายการ → ตรวจสต็อก → จอง FEFO"],
     ("เก็บที่", ["stock.picking (internal) · stock.warehouse.orderpoint", "vpk.his.batch (stock_requisition)"],
      ["ใบหยิบพร้อม · ใบค้าง", "PR (กรณีไม่มีของ)"])),
    ("C", "การโอนสินค้า",
     ("ใบขอเบิกที่คลังรับแล้ว", ["ใบหยิบ / ใบแพ็ค / ใบปลายทาง", "ล็อตที่จองตาม FEFO"]),
     ["หยิบ (PICK)", "แพ็ค (PACK) → อัปเดตปลายทาง (INT)"],
     ("เก็บที่", ["stock.picking (pick · pack · deliver)", "stock.quant (ย้ายตำแหน่ง) · stock.quant.package"],
      ["ยอดย้ายต้นทาง → ปลายทาง ยอดรวมเท่าเดิม", "ชุด HIS เป็น Posted"])),
    ("D", "การตัดจ่ายสินค้า",
     ("HIS / หน่วยงาน / คลัง", ["ชุดตัดจ่ายรายวัน (Control Qty)", "ใบจ่ายออก · ใบนับสต็อก"]),
     ["Validate → Post / จ่าย", "ตัดล็อต FEFO · Reversal คืนยอด"],
     ("เก็บที่", ["vpk.his.batch (stock_issue) · stock.picking (HISOUT / OUT)",
                 "stock.quant · stock.quant.count.sheet"],
      ["ยอดคงคลังลดตามล็อต", "ใบรับคืน (กรณี Reversal)"])),
    ("E", "การผลิตยา",
     ("เภสัชกร / คลัง", ["สูตรผลิต (BoM) · จำนวนรุ่นที่ผลิต", "วัตถุดิบใน PHAR/Stock · ชื่อล็อต"]),
     ["ใบสั่งผลิต (PHAR/MO)", "ยืนยัน จอง → คำสั่งงาน 6 ขั้น → ผลิตทั้งหมด"],
     ("เก็บที่", ["mrp.bom · mrp.production · mrp.workorder", "stock.lot · stock.quant"],
      ["ยาสำเร็จรูปเข้าคลังตามล็อต", "วัตถุดิบลดตามสูตร"])),
]


def slide_dfd(prs, page, total):
    s = blank(prs)
    header(s, "Dataflow ภาพรวม: ข้อมูลเข้า → การประมวลผล → ที่เก็บข้อมูล / ผลลัพธ์",
           "ทุกสายใช้ที่เก็บข้อมูลหลักเดียวกันคือใบเคลื่อนไหวสต็อก (stock.picking) และยอดคงคลังตามล็อต (stock.quant)")
    y0, bh, gap = 1.0, 1.05, 0.08
    for x, w, t, c in [(0.35, 3.3, "ข้อมูลเข้า / ผู้ส่ง", BLUE), (4.2, 4.2, "การประมวลผล", NAVY),
                       (8.95, 4.05, "ที่เก็บข้อมูล และผลลัพธ์", GREEN)]:
        box(s, x, y0, w, 0.32, t, fill=c, line=c, size=10.5, color=WHITE, bold=True, radius=0.2)
    y0 += 0.4
    ys = []
    for i, (code, name, (src, src_items), proc, (_, stores, results)) in enumerate(DFD_ROWS):
        y = y0 + i * (bh + gap)
        ys.append(y)
        col, soft = PHASE_COLOR[code]
        box(s, 0.35, y, 3.3, bh,
            [(src, {"size": 10, "bold": True, "color": BLUE})] + [("• " + t, {"size": 8.5}) for t in src_items],
            fill=BLUE_SOFT, line=BLUE, align=PP_ALIGN.LEFT, radius=0.08, margin=0.1)
        box(s, 4.2, y, 4.2, bh,
            [(f"{code}  {name}", {"size": 11.5, "bold": True, "color": col})] + [("› " + t, {"size": 9}) for t in proc],
            fill=WHITE, line=col, lw=2, align=PP_ALIGN.LEFT, radius=0.1, margin=0.12)
        box(s, 8.95, y, 4.05, bh,
            [("ที่เก็บ", {"size": 8, "bold": True, "color": MUTED})] + [(t, {"size": 8.5, "color": SLATE}) for t in stores]
            + [("ผลลัพธ์", {"size": 8, "bold": True, "color": GREEN})] + [("• " + t, {"size": 8.5}) for t in results],
            fill=GREEN_SOFT, line=GREEN, align=PP_ALIGN.LEFT, radius=0.08, margin=0.1)
        seg(s, 3.65, y + bh / 2, 4.2, y + bh / 2, color=SLATE, w=2)
        seg(s, 8.4, y + bh / 2, 8.95, y + bh / 2, color=SLATE, w=2)
    # ลูกศรเชื่อมระหว่างสาย
    seg(s, 6.3, ys[1] + bh, 6.3, ys[2], color=BLUE, w=2.25)
    footer(s, page, total)


# ------------------------------------------------------------------ ตารางจุดเชื่อม
COLS_INT = [("รหัส", 0.5), ("จุดเชื่อม", 2.55), ("INPUT", 2.85), ("OUTPUT / ผลที่ได้", 3.4), ("ทริกเกอร์", 1.85), ("Module", 1.5)]


def _int_cells(r):
    return [[r["code"]], [r["name"], f"{r['frm']} → {r['to']}"], ["• " + t for t in r["inputs"]],
            ["• " + t for t in r["outputs"]], [r["trigger"]], [r["tech"]]]


def slide_int_table(prs, rows, part, nparts, page, total,
                    title="จุดเชื่อมงานคลังกับระบบอื่น: Input / Output",
                    sub="จัดซื้อ · HIS · บัญชี · การผลิต · รายงาน (W1–W8)"):
    s = blank(prs)
    suffix = f" ({part}/{nparts})" if nparts > 1 else ""
    header(s, f"{title}{suffix}", sub)
    x0, y0 = 0.35, 0.98
    x = x0
    xs = []
    for name, w in COLS_INT:
        xs.append((x, w))
        box(s, x, y0, w - 0.04, 0.32, name, fill=NAVY, line=NAVY, size=10, color=WHITE, bold=True,
            shape=MSO_SHAPE.RECTANGLE)
        x += w
    y = y0 + 0.38
    sizes = [10, 9, 8.5, 8.5, 8.5, 7.5]
    for r in rows:
        cells = _int_cells(r)
        h = rows_h(cells, sizes, [w - 0.04 - 0.16 for _, w in COLS_INT])
        fills = [GREY_SOFT, WHITE, BLUE_SOFT, GREEN_SOFT, WHITE, BG]
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


def paginate_int(rows, avail=7.05 - 1.38):
    cols_w = [w - 0.2 for _, w in COLS_INT]
    pages, cur, used = [], [], 0.0
    for r in rows:
        h = rows_h(_int_cells(r), [10, 9, 8.5, 8.5, 8.5, 7.5], cols_w) + 0.05
        if cur and used + h > avail:
            pages.append(cur)
            cur, used = [], 0.0
        cur.append(r)
        used += h
    if cur:
        pages.append(cur)
    return pages


# ------------------------------------------------------------------ main
def main():
    configure("งานคลังสินค้า · VPK ERP",
              "ที่มา: คู่มือระบบสินค้าคงคลัง + odoo18-custom-addons (vpk_stock_*, vpk_his_api, vpk_mobile_barcode, vpk_vendor_loan)")
    prs = new_prs()
    pages = io_pages(FUNCTIONS, PHASES)
    int_pages = paginate_int(INTEGRATION)
    plan = [
        lambda p, t: slide_title(prs),
        lambda p, t: slide_overview(prs, p, t),
        lambda p, t: slide_swim(
            prs, "A. Workflow การรับสินค้า: ของมาส่ง → QC ผ่าน → กรรมการตรวจรับ → เข้าคลัง",
            "ลำดับ: ของมาส่ง · QC ผ่าน · กรรมการตรวจรับ · บันทึกล็อตแล้วรับของเข้าคลัง · รหัส A1–A8",
            L_RECEIVE, S_RECEIVE, E_RECEIVE, N_RECEIVE, p, t),
        lambda p, t: slide_swim(
            prs, "B. Workflow การขอเบิกสินค้า: ใบขอเบิก → คลังรับรายการ → จองล็อต หรือขอซื้อ",
            "3 ทางเข้า (หน่วยงาน · Min-Max · HIS) รวมเป็นใบขอเบิกเดียวกัน · รหัส B1–B5",
            L_REQUEST, S_REQUEST, E_REQUEST, N_REQUEST, p, t),
        lambda p, t: slide_swim(
            prs, "C. Workflow การโอนสินค้า: หยิบ (PICK) → แพ็ค (PACK) → อัปเดตปลายทาง (INT)",
            "ระบบเปิด 3 ใบต่อเนื่องเมื่อคลังรับรายการ · ของย้ายทีละขั้นเมื่อกดตรวจสอบ · รหัส C1–C4",
            L_TRANSFER, S_TRANSFER, E_TRANSFER, N_TRANSFER, p, t),
        lambda p, t: slide_swim(
            prs, "D. Workflow การตัดจ่ายสินค้า (1/2): ตัดจ่ายจาก HIS",
            "HIS ส่งชุดรายวัน → ตรวจ → เภสัชกร Post → ตัดล็อต · ยกเลิกด้วย Reversal · รหัส D2–D5",
            L_ISSUE_HIS, S_ISSUE_HIS, E_ISSUE_HIS, N_ISSUE_HIS, p, t),
        lambda p, t: slide_swim(
            prs, "D. Workflow การตัดจ่ายสินค้า (2/2): จ่ายออกให้หน่วยงาน และปรับยอดจากการนับ",
            "ใบจ่ายออก (OUT) ผ่านขั้นรอจัด/กำลังจัด/พร้อมรับ · นับสต็อกแล้วปรับยอด · รหัส D1, D6",
            L_ISSUE_OUT, S_ISSUE_OUT, E_ISSUE_OUT, N_ISSUE_OUT, p, t),
        lambda p, t: slide_swim(
            prs, "E. Workflow การผลิตยา: สูตร → ใบสั่งผลิต → ล็อต → ห้องผลิต → ยาเข้าคลัง",
            "แอปการผลิต (mrp) · วัตถุดิบถูกจองเมื่อยืนยัน · ตัดวัตถุดิบและรับยาเมื่อกดผลิตทั้งหมด · รหัส E1–E6",
            L_PROD, S_PROD, E_PROD, N_PROD, p, t),
        lambda p, t: slide_dfd(prs, p, t),
    ]
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
