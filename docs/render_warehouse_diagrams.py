#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""วาดผัง Workflow-Dataflow งานคลังเป็นรูปสำหรับคู่มือ"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_warehouse_dataflow_pptx as df  # noqa: E402

OUT = Path(__file__).resolve().parent / "manual_assets" / "figures" / "dataflow"
FONT = "/Users/mchedtha/Library/Fonts/Prompt-Regular.ttf"
FONTB = "/Users/mchedtha/Library/Fonts/Prompt-SemiBold.ttf"

NAVY = (0x12, 0x3A, 0x56)
WHITE = (255, 255, 255)
SLATE = (0x2F, 0x3A, 0x48)
MUTED = (0x5B, 0x68, 0x78)
LINE = (0xD5, 0xDC, 0xE3)
LANE_A = (0xF7, 0xF9, 0xFB)
LANE_B = (0xEE, 0xF3, 0xF7)
GREEN = (0x2C, 0x7A, 0x45)
RED = (0xB4, 0x43, 0x3A)
AMBER = (0xC4, 0x7E, 0x14)

STYLE = {
    "u": ((0xE6, 0xEF, 0xFA), (0x2B, 0x5F, 0x9E)),
    "w": ((0xFD, 0xF3, 0xE0), AMBER),
    "s": ((0xE5, 0xF5, 0xF3), (0x0F, 0x7A, 0x72)),
    "p": ((0xEE, 0xF1, 0xF4), NAVY),
    "x": ((0xF1, 0xEC, 0xFA), (0x6B, 0x4C, 0xA0)),
    "e": ((0xFB, 0xEC, 0xEA), RED),
    "ok": ((0xE5, 0xF5, 0xEA), GREEN),
}
PHASE = {
    "A": ((0xC4, 0x7E, 0x14), (0xFD, 0xF3, 0xE0)),
    "B": ((0x2B, 0x5F, 0x9E), (0xE6, 0xEF, 0xFA)),
    "C": ((0x0F, 0x7A, 0x72), (0xE5, 0xF5, 0xF3)),
    "D": (GREEN, (0xE5, 0xF5, 0xEA)),
    "E": ((0xA8, 0x3A, 0x7A), (0xFA, 0xEA, 0xF3)),
}


def font(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


def wrap(draw, text, fnt, width):
    if not text:
        return []
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def rounded(draw, box, radius, fill, outline, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, pts, color):
    if len(pts) < 2:
        return
    draw.line(pts, fill=color, width=3)
    x1, y1 = pts[-2]
    x2, y2 = pts[-1]
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 11
    left = (x2 - size * math.cos(ang - 0.45), y2 - size * math.sin(ang - 0.45))
    right = (x2 - size * math.cos(ang + 0.45), y2 - size * math.sin(ang + 0.45))
    draw.polygon([(x2, y2), left, right], fill=color)


def draw_swim(title, subtitle, lanes, steps, edges, notes, filename):
    pad, label_w, top = 28, 260, 92
    box_w, box_h, col_w, lane_h = 236, 118, 276, 156
    max_col = 0
    for lane, col, *_rest in steps.values():
        max_col = max(max_col, col)
    for _lane, c0, c1, _text in notes:
        max_col = max(max_col, c1)
    width = pad + label_w + 16 + (max_col + 1) * col_w + pad
    height = top + len(lanes) * lane_h + 28
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, 78), fill=NAVY)
    draw.text((pad, 12), title, font=font(26, True), fill=WHITE)
    draw.text((pad, 46), subtitle, font=font(16), fill=(0xD6, 0xE4, 0xF0))

    x0 = pad + label_w + 16

    def center(sid):
        lane, col = steps[sid][0], steps[sid][1]
        x = x0 + col * col_w + (col_w - box_w) / 2 + box_w / 2
        y = top + lane * lane_h + lane_h / 2
        return x, y

    for i, name in enumerate(lanes):
        y = top + i * lane_h
        draw.rectangle((pad, y, width - pad, y + lane_h - 8), fill=LANE_A if i % 2 == 0 else LANE_B)
        draw.rectangle((pad, y, pad + label_w, y + lane_h - 8), fill=NAVY)
        lines = wrap(draw, name, font(16, True), label_w - 24)
        ty = y + (lane_h - 8 - len(lines) * 22) / 2
        for line in lines:
            draw.text((pad + 12, ty), line, font=font(16, True), fill=WHITE)
            ty += 22

    for lane, c0, c1, text in notes:
        nx = x0 + c0 * col_w + 8
        nw = (c1 - c0 + 1) * col_w - 16
        ny = top + lane * lane_h + 10
        nh = lane_h - 28
        rounded(draw, (nx, ny, nx + nw, ny + nh), 10, (255, 255, 255), MUTED, 1)
        bits = []
        for item, _opt in text:
            bits.append(item)
        body = " ".join(bits)
        lines = wrap(draw, body, font(14), nw - 16)[:4]
        ty = ny + 8
        for line in lines:
            draw.text((nx + 8, ty), line, font=font(14), fill=MUTED)
            ty += 18

    for edge in edges:
        a, b, label, kind = edge[0], edge[1], edge[2], edge[3]
        ax, ay = center(a)
        bx, by = center(b)
        color = {"ok": GREEN, "bad": RED}.get(kind, SLATE)
        hw, hh = box_w / 2 + 4, box_h / 2 + 4
        if abs(ay - by) < 8:
            pts = [(ax + hw, ay), (bx - hw, by)] if bx > ax else [(ax - hw, ay), (bx + hw, by)]
        elif abs(ax - bx) < 8:
            pts = [(ax, ay + hh), (bx, by - hh)] if by > ay else [(ax, ay - hh), (bx, by + hh)]
        else:
            sx = ax + hw if bx > ax else ax - hw
            ey = by - hh if by > ay else by + hh
            pts = [(sx, ay), (bx, ay), (bx, ey)]
        arrow(draw, pts, color)
        if label:
            draw.text((pts[0][0] + 6, pts[0][1] - 20), label, font=font(14, True), fill=color)

    for _sid, (lane, col, title_t, body, tag, style) in steps.items():
        kind, _, shape = style.partition(":")
        fill, outline = STYLE[kind]
        x = x0 + col * col_w + (col_w - box_w) / 2
        y = top + lane * lane_h + (lane_h - box_h) / 2 - 4
        if shape == "d":
            cx, cy = x + box_w / 2, y + box_h / 2
            draw.polygon(
                [(cx, y - 6), (x + box_w + 8, cy), (cx, y + box_h + 6), (x - 8, cy)],
                fill=fill,
                outline=outline,
            )
            tw = draw.textlength(title_t, font=font(15, True))
            draw.text((cx - tw / 2, cy - 22), title_t, font=font(15, True), fill=outline)
            if tag:
                tw = draw.textlength(tag, font=font(13))
                draw.text((cx - tw / 2, cy + 2), tag, font=font(13), fill=MUTED)
            continue
        rounded(draw, (x, y, x + box_w, y + box_h), 12, fill, outline, 2)
        lines = wrap(draw, title_t, font(15, True), box_w - 16)[:2]
        ty = y + 8
        for line in lines:
            draw.text((x + 8, ty), line, font=font(15, True), fill=outline)
            ty += 18
        if body:
            for line in wrap(draw, body, font(13), box_w - 16)[:3]:
                draw.text((x + 8, ty), line, font=font(13), fill=SLATE)
                ty += 16
        if tag:
            draw.text((x + 8, y + box_h - 20), tag, font=font(12, True), fill=MUTED)

    img.save(OUT / filename, "PNG")
    print(filename, img.size)


def draw_overview():
    phases = [
        ("A", "การรับสินค้า", ["ของมาส่ง", "QC ผ่าน", "กรรมการตรวจรับ", "บันทึกล็อต", "รับเข้าคลัง"]),
        ("B", "การขอเบิกสินค้า", ["หน่วยงาน", "Min-Max", "HIS", "คลังรับรายการ", "จอง FEFO"]),
        ("C", "การโอนสินค้า", ["ใบหยิบ", "แพ็คลงกล่อง", "อัปเดตปลายทาง", "ของถึงปลายทาง"]),
        ("D", "การตัดจ่ายสินค้า", ["ชุด HIS", "Validate", "Post", "จ่ายออก", "นับสต็อก"]),
        ("E", "การผลิตยา", ["สูตรผลิต", "ใบสั่งผลิต", "บันทึกล็อต", "ห้องผลิต", "ผลิตทั้งหมด"]),
    ]
    width, row_h, top = 2200, 150, 92
    height = top + len(phases) * row_h + 20
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, 78), fill=NAVY)
    draw.text((28, 14), "ภาพรวมงานคลังสินค้า 5 สาย", font=font(28, True), fill=WHITE)
    draw.text((28, 48), "สายรับของ: QC ผ่าน → กรรมการตรวจรับ → รับของเข้าคลัง", font=font(16), fill=(0xD6, 0xE4, 0xF0))
    for i, (code, name, stages) in enumerate(phases):
        y = top + i * row_h
        col, soft = PHASE[code]
        rounded(draw, (28, y, 320, y + 118), 14, col, col, 1)
        draw.text((48, y + 28), code, font=font(28, True), fill=WHITE)
        draw.text((100, y + 36), name, font=font(22, True), fill=WHITE)
        x = 360
        for k, stage in enumerate(stages):
            rounded(draw, (x, y + 28, x + 250, y + 90), 16, WHITE, col, 2)
            tw = draw.textlength(stage, font=font(18, True))
            draw.text((x + (250 - tw) / 2, y + 46), stage, font=font(18, True), fill=SLATE)
            if k < len(stages) - 1:
                arrow(draw, [(x + 250, y + 59), (x + 300, y + 59)], col)
            x += 310
    img.save(OUT / "df_overview.png", "PNG")
    print("df_overview.png", img.size)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    draw_overview()
    diagrams = [
        ("df_receive.png", "A การรับสินค้า", "QC ผ่าน → กรรมการตรวจรับ → บันทึกล็อต → รับของเข้าคลัง",
         df.L_RECEIVE, df.S_RECEIVE, df.E_RECEIVE, df.N_RECEIVE),
        ("df_request.png", "B การขอเบิกสินค้า", "หน่วยงาน · Min-Max · HIS รวมเป็นใบขอเบิกเดียวกัน",
         df.L_REQUEST, df.S_REQUEST, df.E_REQUEST, df.N_REQUEST),
        ("df_transfer.png", "C การโอนสินค้า", "หยิบ → แพ็ค → อัปเดตปลายทาง ของย้ายเมื่อกดตรวจสอบ",
         df.L_TRANSFER, df.S_TRANSFER, df.E_TRANSFER, df.N_TRANSFER),
        ("df_issue_his.png", "D การตัดจ่ายจาก HIS", "Validate → เภสัชกร Post → ตัดล็อต ยกเลิกด้วย Reversal",
         df.L_ISSUE_HIS, df.S_ISSUE_HIS, df.E_ISSUE_HIS, df.N_ISSUE_HIS),
        ("df_issue_out.png", "D จ่ายออกและนับสต็อก", "ใบจ่ายออกผ่านขั้นจัดของ และปรับยอดเมื่อนับแล้วไม่ตรง",
         df.L_ISSUE_OUT, df.S_ISSUE_OUT, df.E_ISSUE_OUT, df.N_ISSUE_OUT),
        ("df_produce.png", "E การผลิตยา", "สูตร → ใบสั่งผลิต → ล็อต → ห้องผลิต → ยาเข้าคลัง",
         df.L_PROD, df.S_PROD, df.E_PROD, df.N_PROD),
    ]
    for filename, title, subtitle, lanes, steps, edges, notes in diagrams:
        draw_swim(title, subtitle, lanes, steps, edges, notes, filename)


if __name__ == "__main__":
    main()
