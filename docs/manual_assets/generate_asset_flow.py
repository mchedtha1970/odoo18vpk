#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""แผนภาพวงจรสินทรัพย์ สำหรับคู่มือระบบจัดการสินทรัพย์"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "fig_asset_flow.png"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

TEAL = (11, 104, 72)
NAVY = (18, 58, 86)
AMBER = (146, 64, 14)
AMBER_SOFT = (253, 243, 224)
GREEN_SOFT = (229, 245, 234)
INK = (42, 51, 58)
WHITE = (255, 255, 255)


def font(size, weight="regular"):
    name = {"regular": "Prompt-Regular.ttf", "medium": "Prompt-Medium.ttf"}[weight]
    return ImageFont.truetype(str(FONT_DIR / name), size)


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def center_lines(draw, box, lines, fills, fonts, gap=4):
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
    w, h = 1400, 1280
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    title_f = font(26, "medium")
    sub_f = font(20, "regular")

    col_x1, col_x2 = 370, 1030
    cx = (col_x1 + col_x2) // 2
    y = 28
    gap = 42
    steps = [
        (["เปิดบัตรสินทรัพย์", "ใส่เลขสินทรัพย์และประเภท"], TEAL),
        (["บันทึกทะเบียนและแหล่งที่มา", "ผู้ขาย ใบสั่งซื้อ ใบแจ้งหนี้ หน่วยงานเจ้าของ"], TEAL),
        (["ถือครองที่หน่วยงาน", "สร้าง Equipment เมื่อต้องซ่อมบำรุง"], TEAL),
    ]
    for index, (lines, fill) in enumerate(steps):
        box = (col_x1, y, col_x2, y + 108)
        round_box(draw, box, fill)
        center_lines(draw, box, lines, [WHITE, WHITE], [title_f, sub_f])
        y = box[3]
        if index < len(steps) - 1:
            arrow_down(draw, cx, y, y + gap)
            y += gap

    split_y = y
    arrow_down(draw, cx, split_y, split_y + 28)
    join = split_y + 36
    branches = [
        (["โอนหน่วยงาน", "ขอโอน  อนุมัติ  รับโอน"], TEAL, [WHITE, WHITE]),
        (["ตรวจนับประจำปี", "สร้าง Sheet  เปิดนับ  ปิดนับ"], NAVY, [WHITE, WHITE]),
        (["จำหน่ายออกจากทะเบียน", "รอจำหน่าย  ขออนุมัติ  ตัดจำหน่าย"], AMBER_SOFT, [AMBER, AMBER]),
    ]
    bw, bh, b_gap = 400, 130, 28
    total_w = bw * 3 + b_gap * 2
    x0 = (w - total_w) // 2
    centers = []
    top = join + 36
    for i, (lines, fill, inks) in enumerate(branches):
        x = x0 + i * (bw + b_gap)
        box = (x, top, x + bw, top + bh)
        centers.append((box[0] + box[2]) // 2)
        outline = AMBER if fill == AMBER_SOFT else None
        round_box(draw, box, fill, outline=outline, width=3)
        center_lines(draw, box, lines, inks, [title_f, sub_f])
    draw.line((centers[0], join, centers[2], join), fill=INK, width=3)
    draw.line((cx, split_y + 28, cx, join), fill=INK, width=3)
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
