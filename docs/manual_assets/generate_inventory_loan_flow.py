#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""แผนภาพลำดับการยืมของจากผู้ขาย สำหรับคู่มือสินค้าคงคลัง"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "fig_inv_loan_flow.png"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

TEAL = (11, 104, 72)
AMBER = (146, 64, 14)
AMBER_SOFT = (253, 243, 224)
GREEN_SOFT = (229, 245, 234)
INK = (42, 51, 58)
WHITE = (255, 255, 255)


def font(size, weight="regular"):
    name = {
        "regular": "Prompt-Regular.ttf",
        "medium": "Prompt-Medium.ttf",
    }[weight]
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
    w, h = 1400, 1480
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    title_f = font(28, "medium")
    sub_f = font(22, "regular")
    note_f = font(20, "medium")

    col_x1, col_x2 = 250, 910
    cx = (col_x1 + col_x2) // 2
    y = 28
    gap = 46

    steps = [
        (["บันทึกใบยืม", "ใส่ต้นทุนที่จะซื้อมาหักล้าง"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
        (["รับของยืมเข้าคลังยืมผู้ขาย", "ไม่ตรวจคุณภาพ"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
        (["เปิดขอซื้อระดับเร่งด่วน", "ฝ่ายพัสดุเดินอนุมัติและ e-GP"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
        (["ตัดใช้จากคลังยืมก่อน", "คงค้างยืมยังไม่ลด"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
        (["กรรมการบันทึกตรวจรับ", "ใบตรวจรับไม่เพิ่มยอดคลัง"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
        (["รับของซื้อเข้าคลังยืมเดียวกัน", "ตรวจคุณภาพให้ผ่านก่อน"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
        (["กดตรวจสอบ", "รับเข้าแล้วหักล้างในคลังยืมทันที"], TEAL, [WHITE, WHITE], [title_f, sub_f], 108),
    ]

    use_box = None
    for index, (lines, fill, inks, fonts, bh) in enumerate(steps):
        box = (col_x1, y, col_x2, y + bh)
        round_box(draw, box, fill)
        center_lines(draw, box, lines, inks, fonts)
        if lines[0].startswith("ตัดใช้"):
            use_box = box
        y = box[3]
        if index < len(steps) - 1:
            arrow_down(draw, cx, y, y + gap)
            y += gap

    # ถ้ายังไม่เบิก ข้ามขั้นตัดใช้
    skip = (960, use_box[1], 1348, use_box[3])
    round_box(draw, skip, AMBER_SOFT, outline=AMBER, width=3)
    center_lines(
        draw, skip,
        ["ถ้ายังไม่เบิก", "ข้ามขั้นนี้"],
        [AMBER, AMBER],
        [title_f, sub_f],
    )
    mid_y = (use_box[1] + use_box[3]) // 2
    x = use_box[2] + 8
    while x < skip[0] - 6:
        draw.line((x, mid_y, min(x + 10, skip[0] - 6), mid_y), fill=AMBER, width=3)
        x += 18

    # แยกผลลัพธ์
    split_y = y
    left = (80, split_y + 56, 660, split_y + 220)
    right = (740, split_y + 56, 1320, split_y + 220)
    left_cx = (left[0] + left[2]) // 2
    right_cx = (right[0] + right[2]) // 2
    join = split_y + 8
    draw.line((cx, split_y, cx, join), fill=INK, width=3)
    draw.line((left_cx, join, right_cx, join), fill=INK, width=3)
    arrow_down(draw, left_cx, join, left[1])
    arrow_down(draw, right_cx, join, right[1])

    round_box(draw, left, GREEN_SOFT, outline=TEAL, width=2)
    center_lines(
        draw, left,
        ["ผลลัพธ์  ตัดใช้ไปแล้ว", "คลังยืมจบที่ 0", "คลังปกติไม่ถูกนับเพิ่ม"],
        [TEAL, INK, INK],
        [note_f, title_f, sub_f],
    )
    round_box(draw, right, GREEN_SOFT, outline=TEAL, width=2)
    center_lines(
        draw, right,
        ["ผลลัพธ์  ยังไม่ตัดใช้", "คลังยืมเหลือของที่ยืม", "คลังปกติไม่ถูกนับเพิ่ม"],
        [TEAL, INK, INK],
        [note_f, title_f, sub_f],
    )

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
