#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""แผนภาพวงจรเจ้าหนี้ การเงิน และบัญชี สำหรับคู่มือการใช้งาน"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FIG = Path(__file__).resolve().parent / "figures"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

TEAL = (11, 104, 72)
NAVY = (18, 58, 86)
AMBER = (146, 64, 14)
AMBER_SOFT = (253, 243, 224)
INK = (42, 51, 58)
WHITE = (255, 255, 255)


def font(size, weight="regular"):
    name = {"regular": "Prompt-Regular.ttf", "medium": "Prompt-Medium.ttf"}[weight]
    return ImageFont.truetype(str(FONT_DIR / name), size)


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def center_lines(draw, box, lines, fills, fonts, gap=6):
    x1, y1, x2, y2 = box
    heights = [text_size(draw, text, fnt)[1] for text, fnt in zip(lines, fonts)]
    total = sum(heights) + gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for text, fill, fnt, h in zip(lines, fills, fonts, heights):
        w, _ = text_size(draw, text, fnt)
        draw.text(((x1 + x2 - w) / 2, y - 2), text, font=fnt, fill=fill)
        y += h + gap


def round_box(draw, box, fill, outline=None, width=2, radius=16):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow_down(draw, x, y1, y2):
    if y2 <= y1 + 8:
        return
    draw.line((x, y1, x, y2 - 11), fill=INK, width=3)
    draw.polygon([(x - 7, y2 - 12), (x + 7, y2 - 12), (x, y2)], fill=INK)


def crop(img):
    w, h = img.size
    pixels = img.load()
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for py in range(h):
        for px in range(w):
            if pixels[px, py] != WHITE:
                min_x = min(min_x, px)
                min_y = min(min_y, py)
                max_x = max(max_x, px)
                max_y = max(max_y, py)
    pad = 28
    return img.crop(
        (
            max(0, min_x - pad),
            max(0, min_y - pad),
            min(w, max_x + pad + 1),
            min(h, max_y + pad + 1),
        )
    )


def vertical(steps, width=1680):
    img = Image.new("RGB", (width, 80 + 130 * len(steps)), WHITE)
    draw = ImageDraw.Draw(img)
    title_f = font(26, "medium")
    sub_f = font(20, "regular")
    x1, x2 = 360, width - 360
    cx = (x1 + x2) // 2
    y = 24
    gap = 40
    for lines, fill, inks in steps:
        box = (x1, y, x2, y + 100)
        outline = AMBER if fill == AMBER_SOFT else None
        round_box(draw, box, fill, outline=outline, width=3)
        center_lines(draw, box, lines, inks, [title_f, sub_f])
        y = box[3]
        if lines != steps[-1][0]:
            arrow_down(draw, cx, y, y + gap)
            y += gap
    return crop(img)


def finance_flow():
    w, h = 1760, 920
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    title_f = font(24, "medium")
    sub_f = font(18, "regular")
    x1, x2 = 480, 1280
    cx = (x1 + x2) // 2
    y = 20
    gap = 32
    steps = [
        (["ใบเรียกเก็บที่ยืนยันแล้ว", "มียอดเจ้าหนี้ค้างจ่าย"], TEAL, [WHITE, WHITE]),
        (["เลือกวิธีจ่าย", "จ่ายตรงผู้ขาย หรือจ่ายผ่านส่วนราชการ"], TEAL, [WHITE, WHITE]),
    ]
    for lines, fill, inks in steps:
        box = (x1, y, x2, y + 92)
        round_box(draw, box, fill)
        center_lines(draw, box, lines, inks, [title_f, sub_f])
        y = box[3]
        arrow_down(draw, cx, y, y + gap)
        y += gap
    split_y = y - gap
    join = y + 4
    branches = [
        (
            ["จ่ายตรง", "ขบ.01 หรือ ขบ.02", "อม.01 แล้ว อม.02", "บันทึกจ่ายแล้ว"],
            TEAL,
            [WHITE, WHITE, WHITE, WHITE],
        ),
        (
            ["จ่ายผ่านหน่วยงาน", "ขบ.03 เงินเข้า รพ.", "ต่อด้วย ขจ.05", "จ่ายผู้มีสิทธิแล้ว"],
            NAVY,
            [WHITE, WHITE, WHITE, WHITE],
        ),
        (
            ["จ่ายใน ERP", "กดจ่ายที่ใบเรียกเก็บ", "เลือกสมุดธนาคาร", "ยอดเจ้าหนี้ลดลง"],
            AMBER_SOFT,
            [AMBER, AMBER, AMBER, AMBER],
        ),
    ]
    bw, bh, b_gap = 500, 210, 28
    total_w = bw * 3 + b_gap * 2
    x0 = (w - total_w) // 2
    centers = []
    top = join + 28
    for i, (lines, fill, inks) in enumerate(branches):
        x = x0 + i * (bw + b_gap)
        box = (x, top, x + bw, top + bh)
        centers.append((box[0] + box[2]) // 2)
        outline = AMBER if fill == AMBER_SOFT else None
        round_box(draw, box, fill, outline=outline, width=3)
        center_lines(draw, box, lines, inks, [title_f, sub_f, sub_f, sub_f], gap=8)
    draw.line((centers[0], join, centers[-1], join), fill=INK, width=3)
    draw.line((cx, split_y + 20, cx, join), fill=INK, width=3)
    for bcx in centers:
        arrow_down(draw, bcx, join, top)
    return crop(img)


def main():
    ap = vertical(
        [
            (["ตรวจรับหรือรับสินค้าแล้ว", "ใช้ใบสั่งซื้อที่ยืนยันแล้ว"], TEAL, [WHITE, WHITE]),
            (["จากใบสั่งซื้อกด สร้างบิล", "ระบบดึงผู้ขายและรายการมาให้"], TEAL, [WHITE, WHITE]),
            (["ใส่เลขใบแจ้งหนี้ผู้ขาย", "ตรวจภาษี บัญชี และงบประมาณ"], TEAL, [WHITE, WHITE]),
            (["กดยืนยัน", "ระบบตั้งยอดเจ้าหนี้"], TEAL, [WHITE, WHITE]),
            (["ส่งต่อการเงิน", "จ่ายในระบบ หรือขอเบิก GFMIS"], NAVY, [WHITE, WHITE]),
        ]
    )
    # ทางเลือกอยู่แยกจากลูกศรหลัก ไม่ให้ดูเหมือนต้องลดหนี้ทุกครั้ง
    canvas = Image.new("RGB", (ap.width, ap.height + 150), WHITE)
    canvas.paste(ap, (0, 0))
    draw = ImageDraw.Draw(canvas)
    label_f = font(18, "medium")
    label = "ทางเลือก เมื่อต้องลดยอด"
    lw, _ = text_size(draw, label, label_f)
    draw.text(((canvas.width - lw) / 2, ap.height + 8), label, font=label_f, fill=AMBER)
    box = (80, ap.height + 40, canvas.width - 80, ap.height + 132)
    round_box(draw, box, AMBER_SOFT, outline=AMBER, width=3)
    center_lines(
        draw,
        box,
        ["ใช้เมนูการคืนเงิน", "สร้างใบลดหนี้อ้างใบเรียกเก็บเดิม"],
        [AMBER, AMBER],
        [font(24, "medium"), font(18, "regular")],
    )
    ap = canvas
    ap_path = FIG / "fig_ap_flow.png"
    ap.save(ap_path, "PNG")
    fin = finance_flow()
    fin_path = FIG / "fig_fin_flow.png"
    fin.save(fin_path, "PNG")
    acc = vertical(
        [
            (["เปิดรายการบันทึกสมุดรายวัน", "เลือกสมุดรายวันให้ตรงประเภทรายการ"], TEAL, [WHITE, WHITE]),
            (["ลงเดบิตและเครดิต", "ยอดสองฝั่งต้องเท่ากัน"], TEAL, [WHITE, WHITE]),
            (["กดยืนยัน", "รายการผ่านเข้าบัญชีแยกประเภท"], TEAL, [WHITE, WHITE]),
            (["ตรวจรายงาน", "งบทดลอง งบดุล และกำไรขาดทุน"], NAVY, [WHITE, WHITE]),
        ]
    )
    acc_path = FIG / "fig_acc_flow.png"
    acc.save(acc_path, "PNG")
    print(ap_path, ap.size)
    print(fin_path, fin.size)
    print(acc_path, acc.size)


if __name__ == "__main__":
    main()
