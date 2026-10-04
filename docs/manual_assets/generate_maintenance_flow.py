#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""แผนภาพวงจรซ่อมบำรุง สำหรับคู่มือระบบซ่อมบำรุง"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "fig_maint_flow.png"
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


def main():
    w, h = 1680, 980
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    title_f = font(24, "medium")
    sub_f = font(18, "regular")

    col_x1, col_x2 = 430, 1250
    cx = (col_x1 + col_x2) // 2
    y = 24
    gap = 36
    steps = [
        (["สร้าง Equipment จากบัตรสินทรัพย์", "ใส่โมเดล หมายเลขซีเรียล และพิกัด"], TEAL, [WHITE, WHITE]),
        (["เปิดคำขอการซ่อมบำรุง", "ใส่หัวข้อ เลือกอุปกรณ์ และประเภทการซ่อม"], TEAL, [WHITE, WHITE]),
        (["บันทึกผลการประเมิน", "แล้วเลือกทางทำตามผล"], TEAL, [WHITE, WHITE]),
    ]
    for index, (lines, fill, inks) in enumerate(steps):
        box = (col_x1, y, col_x2, y + 96)
        round_box(draw, box, fill)
        center_lines(draw, box, lines, inks, [title_f, sub_f])
        y = box[3]
        arrow_down(draw, cx, y, y + gap)
        y += gap

    split_y = y - gap
    join = y + 8
    branches = [
        (["ซ่อมได้มีอะไหล่", "กดเบิกอะไหล่", "ปิดงานที่ขั้นตอนซ่อมแล้ว"], TEAL, [WHITE, WHITE, WHITE]),
        (["ซ่อมได้ไม่มีอะไหล่", "กดเปิด PR", "ใส่ราคาประมาณการ"], NAVY, [WHITE, WHITE, WHITE]),
        (["จ้างซ่อมภายนอก", "กดเปิด PR", "สินค้าบริการจ้างซ่อม"], NAVY, [WHITE, WHITE, WHITE]),
        (["ซ่อมไม่คุ้มแทงจำหน่าย", "กดแทงจำหน่าย", "บัตรสินทรัพย์เป็นรอจำหน่าย"], AMBER_SOFT, [AMBER, AMBER, AMBER]),
    ]
    bw, bh, b_gap = 380, 168, 24
    total_w = bw * 4 + b_gap * 3
    x0 = (w - total_w) // 2
    centers = []
    top = join + 28
    for i, (lines, fill, inks) in enumerate(branches):
        x = x0 + i * (bw + b_gap)
        box = (x, top, x + bw, top + bh)
        centers.append((box[0] + box[2]) // 2)
        outline = AMBER if fill == AMBER_SOFT else None
        round_box(draw, box, fill, outline=outline, width=3)
        center_lines(draw, box, lines, inks, [title_f, sub_f, sub_f], gap=8)

    draw.line((centers[0], join, centers[-1], join), fill=INK, width=3)
    draw.line((cx, split_y + 24, cx, join), fill=INK, width=3)
    for bcx in centers:
        arrow_down(draw, bcx, join, top)

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
    img = img.crop((
        max(0, min_x - pad),
        max(0, min_y - pad),
        min(w, max_x + pad + 1),
        min(h, max_y + pad + 1),
    ))
    img.save(OUT, "PNG")
    print(OUT, img.size)


if __name__ == "__main__":
    main()
