#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""แผนภาพลำดับการโอนภายใน สำหรับคู่มือสินค้าคงคลัง"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "fig_inv_internal_flow.png"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

NAVY = (18, 58, 86)
NAVY_SOFT = (232, 241, 248)
SLATE = (47, 58, 72)
TEAL = (11, 104, 72)
TEAL_SOFT = (229, 245, 243)
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


def center_lines(draw, box, lines, fills, fonts, gap=6):
    x1, y1, x2, y2 = box
    heights = [text_size(draw, text, fnt)[1] for text, fnt in zip(lines, fonts)]
    total = sum(heights) + gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for text, fill, fnt, h in zip(lines, fills, fonts, heights):
        w, _ = text_size(draw, text, fnt)
        draw.text(((x1 + x2 - w) / 2, y - 2), text, font=fnt, fill=fill)
        y += h + gap


def round_box(draw, box, fill, outline=None, width=2, radius=18):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow_down(draw, x, y1, y2):
    if y2 <= y1 + 8:
        return
    draw.line((x, y1, x, y2 - 10), fill=INK, width=3)
    draw.polygon([(x - 7, y2 - 12), (x + 7, y2 - 12), (x, y2)], fill=INK)


def lane_title(draw, x, y, text, fill):
    fnt = font(26, "medium")
    draw.text((x, y), text, font=fnt, fill=fill)


def main():
    w, h = 1500, 1960
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)
    title_f = font(26, "medium")
    sub_f = font(20, "regular")
    small_f = font(20, "regular")
    cx = w // 2

    # หน่วยงาน
    round_box(draw, (28, 24, 1472, 560), NAVY_SOFT, radius=22)
    lane_title(draw, 52, 40, "หน่วยงาน", NAVY)

    left = (52, 96, 730, 208)
    items = (52, 268, 730, 368)
    right = (770, 96, 1448, 368)
    round_box(draw, left, NAVY)
    center_lines(
        draw, left,
        ["บันทึกขอโอนสินค้า", "สถานะร่าง"],
        [WHITE, WHITE], [title_f, sub_f],
    )
    round_box(draw, items, NAVY)
    center_lines(draw, items, ["ใส่รายการของและจำนวน"], [WHITE], [title_f])
    round_box(draw, right, SLATE)
    center_lines(
        draw, right,
        ["หรือระบบสร้างให้", "เมื่อยอดต่ำกว่าขั้นต่ำ", "สถานะร่าง มีรายการแล้ว"],
        [WHITE, WHITE, WHITE], [title_f, sub_f, sub_f],
    )
    arrow_down(draw, (left[0] + left[2]) // 2, left[3], items[1])

    handoff = (220, 440, 1280, 528)
    round_box(draw, handoff, WHITE, outline=NAVY, width=3)
    center_lines(
        draw, handoff,
        ["จบตรงนี้  ส่งใบร่างให้หน่วยงานคลัง"],
        [NAVY], [title_f],
    )
    join_y = 404
    for box in (items, right):
        bx = (box[0] + box[2]) // 2
        draw.line((bx, box[3], bx, join_y), fill=INK, width=3)
    draw.line(((items[0] + items[2]) // 2, join_y, (right[0] + right[2]) // 2, join_y), fill=INK, width=3)
    arrow_down(draw, cx, join_y, handoff[1])

    # หน่วยงานคลัง
    round_box(draw, (28, 584, 1472, 1936), TEAL_SOFT, radius=22)
    lane_title(draw, 52, 600, "หน่วยงานคลัง", TEAL)
    arrow_down(draw, cx, handoff[3], 668)

    receive = (280, 668, 1220, 776)
    pull = (280, 820, 1220, 928)
    round_box(draw, receive, TEAL)
    center_lines(
        draw, receive,
        ["รับใบขอโอน  กดรับรายการ", "สถานะรับแล้ว  เปิดใบหยิบ"],
        [WHITE, WHITE], [title_f, sub_f],
    )
    arrow_down(draw, cx, receive[3], pull[1])
    round_box(draw, pull, TEAL)
    center_lines(
        draw, pull,
        ["ระบบดึงรายการ", "จองล็อตตาม FEFO"],
        [WHITE, WHITE], [title_f, sub_f],
    )

    split_y = pull[3] + 28
    col_w = 440
    gap = 28
    x0 = (w - (col_w * 3 + gap * 2)) // 2
    cols = [x0, x0 + col_w + gap, x0 + (col_w + gap) * 2]
    branch_y = split_y + 40
    branch_h = 150

    draw.line((cx, pull[3], cx, split_y), fill=INK, width=3)
    draw.line((cols[0] + col_w // 2, split_y, cols[2] + col_w // 2, split_y), fill=INK, width=3)

    branches = [
        (["มีของพอ", "จองครบตามจำนวนที่ขอ"], TEAL, [WHITE, WHITE]),
        (["มีบางส่วน", "จองเท่าที่มี", "ส่วนที่เหลือเปิดใบค้าง"], TEAL, [WHITE, WHITE, WHITE]),
        (["ไม่มีของ", "ยังไม่หยิบ", "ไปสร้างใบขอซื้อ"], AMBER_SOFT, [AMBER, AMBER, AMBER]),
    ]
    for i, (lines, fill, inks) in enumerate(branches):
        x = cols[i]
        bcx = x + col_w // 2
        arrow_down(draw, bcx, split_y, branch_y)
        box = (x, branch_y, x + col_w, branch_y + branch_h)
        outline = AMBER if fill == AMBER_SOFT else None
        round_box(draw, box, fill, outline=outline, width=3)
        fonts = [title_f] + [sub_f] * (len(lines) - 1)
        center_lines(draw, box, lines, inks, fonts)

    cont_y = branch_y + branch_h + 36
    left_mid = cols[0] + col_w // 2
    mid_mid = cols[1] + col_w // 2
    draw.line((left_mid, branch_y + branch_h, left_mid, cont_y), fill=INK, width=3)
    draw.line((mid_mid, branch_y + branch_h, mid_mid, cont_y), fill=INK, width=3)
    draw.line((left_mid, cont_y, mid_mid, cont_y), fill=INK, width=3)
    arrow_down(draw, (left_mid + mid_mid) // 2, cont_y, cont_y + 48)

    follow = (220, cont_y + 48, 1280, cont_y + 132)
    round_box(draw, follow, WHITE, outline=TEAL, width=3)
    center_lines(draw, follow, ["เมื่อมีของ  ทำต่อสามใบนี้"], [TEAL], [title_f])

    steps = [
        (["พิมพ์ใบหยิบของ", "แล้วไปหยิบตามใบ"], TEAL),
        (["แพ็คลงกล่อง", "ที่ใบแพ็ค"], TEAL),
        (["กดตรวจสอบ", "อัปเดตคลังปลายทาง"], TEAL),
    ]
    step_y = follow[3] + 44
    step_h = 150
    step_w = 400
    step_gap = 36
    step_x0 = (w - (step_w * 3 + step_gap * 2)) // 2
    arrow_down(draw, cx, follow[3], step_y)
    for i, (lines, fill) in enumerate(steps):
        x = step_x0 + i * (step_w + step_gap)
        box = (x, step_y, x + step_w, step_y + step_h)
        round_box(draw, box, fill)
        center_lines(
            draw, box, lines, [WHITE, WHITE], [title_f, sub_f],
        )
        if i < len(steps) - 1:
            x_from = box[2] + 4
            x_to = box[2] + step_gap - 4
            y_mid = step_y + step_h // 2
            draw.line((x_from, y_mid, x_to - 8, y_mid), fill=INK, width=3)
            draw.polygon(
                [(x_to - 10, y_mid - 7), (x_to - 10, y_mid + 7), (x_to, y_mid)],
                fill=INK,
            )

    done = (360, step_y + step_h + 48, 1140, step_y + step_h + 168)
    arrow_down(draw, cx, step_y + step_h, done[1])
    round_box(draw, done, GREEN_SOFT, outline=TEAL, width=2)
    center_lines(
        draw, done,
        ["ผลลัพธ์", "ของเข้าคลังปลายทาง"],
        [TEAL, INK],
        [font(22, "medium"), small_f],
    )

    img.save(OUT, "PNG")
    print(OUT, img.size)


if __name__ == "__main__":
    main()
