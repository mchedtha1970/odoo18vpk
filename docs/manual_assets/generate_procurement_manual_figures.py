#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Training illustrations for the VPK procurement (PR → e-GP → PO) user manual."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("/opt/odoo18vpk/docs/manual_assets/figures")
FONT_DIR = Path("/opt/odoo18vpk/docs/manual_assets/fonts")

NAVY = (18, 58, 86)
TEAL = (11, 104, 72)
AMBER = (196, 126, 20)
RED = (180, 67, 58)
GREEN = (44, 122, 69)
SLATE = (47, 58, 72)
MUTED = (91, 104, 120)
WHITE = (255, 255, 255)
BG = (246, 248, 250)
SOFT = (229, 245, 243)
AMBER_SOFT = (253, 243, 224)
RED_SOFT = (251, 236, 234)
GREEN_SOFT = (229, 245, 234)
NAVY_SOFT = (232, 241, 248)


def font(size, weight="regular"):
    name = {
        "regular": "Prompt-Regular.ttf",
        "medium": "Prompt-Medium.ttf",
        "semibold": "Prompt-SemiBold.ttf",
        "bold": "Prompt-Bold.ttf",
    }[weight]
    return ImageFont.truetype(str(FONT_DIR / name), size)


def new_canvas(w, h, color=BG):
    img = Image.new("RGB", (w, h), color)
    return img, ImageDraw.Draw(img)


def round_rect(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def text_w(draw, text, fnt):
    return draw.textbbox((0, 0), text, font=fnt)[2]


def center_text(draw, x, y, w, text, fnt, fill, h=None):
    tw = text_w(draw, text, fnt)
    th = draw.textbbox((0, 0), text, font=fnt)[3]
    ty = y if h is None else y + (h - th) // 2
    draw.text((x + (w - tw) // 2, ty), text, font=fnt, fill=fill)


def wrap_center(draw, x, y, w, text, fnt, fill, gap=6):
    for i, line in enumerate(text.split("\n")):
        center_text(draw, x, y + i * (fnt.size + gap), w, line, fnt, fill)


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print(path)
    return path


def fig_proc_cover():
    img, d = new_canvas(1600, 640, NAVY)
    d.rectangle((0, 0, 14, 640), fill=TEAL)
    d.text((70, 90), "โรงพยาบาลวชิระภูเก็ต  ·  Odoo 18", font=font(22), fill=(159, 201, 196))
    d.text((70, 150), "คู่มือการใช้งาน", font=font(28, "medium"), fill=WHITE)
    d.text((70, 200), "ระบบจัดซื้อจัดจ้าง", font=font(56, "bold"), fill=WHITE)
    d.text(
        (70, 290),
        "ใบขอซื้อ (PR)  →  กระบวนการ e-GP  →  ใบสั่งซื้อ (PO)",
        font=font(22),
        fill=(215, 228, 238),
    )
    boxes = [
        ("1", "เปิดใบขอซื้อ", TEAL),
        ("2", "เข้า e-GP", (28, 78, 110)),
        ("3", "เปิด PO ผู้ชนะ", (36, 99, 90)),
    ]
    for i, (num, title, col) in enumerate(boxes):
        x = 70 + i * 310
        round_rect(d, (x, 430, x + 280, 540), 16, col)
        d.text((x + 28, 448), num, font=font(18, "bold"), fill=(159, 201, 196))
        d.text((x + 28, 478), title, font=font(24, "semibold"), fill=WHITE)
    d.text(
        (70, 575),
        "เวอร์ชัน 1.0  ·  สิงหาคม 2569  ·  สำหรับหน่วยงาน พัสดุ และผู้เกี่ยวข้องจัดซื้อจัดจ้าง",
        font=font(18),
        fill=(159, 201, 196),
    )
    save(img, "fig_proc_cover.png")


def fig_proc_flow():
    img, d = new_canvas(1600, 720)
    d.text((48, 24), "วงจรงานหลัก  ห้ามข้ามขั้น", font=font(28, "bold"), fill=NAVY)
    d.text(
        (48, 72),
        "ใบขอซื้อที่เลือกประเภท จัดซื้อจัดจ้างผ่านพัสดุ ต้องเข้ากระบวนการ e-GP ก่อน จึงจะเปิด PO ได้",
        font=font(18),
        fill=MUTED,
    )
    items = [
        ("1", "หน่วยงาน", "เปิดใบขอซื้อ", "กรอกของ เช็คงบ\nส่งขออนุมัติ", TEAL),
        ("2", "ผู้อนุมัติ", "อนุมัติ PR", "ตรวจและอนุมัติ\nตามขั้น", NAVY),
        ("3", "พัสดุ", "ส่งเข้า e-GP", "สร้างกระบวนการ\nยืนยันเอกสาร", AMBER),
        ("4", "พัสดุ", "คัดเลือกผู้ชนะ", "เชิญ รับข้อเสนอ\nรายงานผล", AMBER),
        ("5", "พัสดุ", "เปิด PO", "สร้าง RFQ/PO\nให้ผู้ชนะแล้วยืนยัน", GREEN),
    ]
    for i, (num, who, title, body, col) in enumerate(items):
        x = 36 + i * 312
        round_rect(d, (x, 130, x + 288, 190), 14, col)
        center_text(d, x, 138, 288, f"{num}  {title}", font(20, "bold"), WHITE)
        round_rect(d, (x, 190, x + 288, 400), 14, WHITE, col, 2)
        d.rectangle((x, 190, x + 288, 206), fill=WHITE)
        center_text(d, x, 220, 288, who, font(16, "semibold"), col)
        wrap_center(d, x + 16, 270, 256, body, font(18), SLATE, 8)
        if i < 4:
            d.polygon([(x + 294, 250), (x + 310, 262), (x + 294, 274)], fill=TEAL)

    round_rect(d, (36, 440, 1564, 680), 16, SOFT, TEAL, 2)
    d.text((64, 464), "จำประโยคนี้ไว้ก่อนลงมือกดในระบบ", font=font(20, "semibold"), fill=TEAL)
    lines = [
        "หน่วยงานสร้างใบขอซื้อ ไม่สร้างใบสั่งซื้อเอง",
        "เลือกประเภทการจัดซื้อเป็น จัดซื้อจัดจ้างผ่านพัสดุ จึงจะส่งเข้ากระบวนการ e-GP ได้",
        "ห้ามกด สร้างใบขอเสนอราคา จากใบขอซื้อประเภทนี้ ต้องส่งกระบวนการ e-GP ก่อน",
        "เปิด PO ได้เมื่อเลือกผู้ชนะ และอนุมัติรายงานผลการพิจารณาแล้วเท่านั้น",
    ]
    for i, t in enumerate(lines):
        d.text((64, 516 + i * 36), f"•  {t}", font=font(18), fill=SLATE)
    save(img, "fig_proc_flow.png")


def fig_proc_roles():
    img, d = new_canvas(1600, 980)
    d.text((48, 24), "ใครทำอะไรในวงจรนี้", font=font(28, "bold"), fill=NAVY)
    d.text(
        (48, 72),
        "ใช้บัญชีตามบทบาท  กรรมการตรวจรับมี 3 คน ตามกติกาอย่างน้อย 3 คน",
        font=font(18),
        fill=MUTED,
    )
    roles = [
        ("หน่วยงาน", "uat.dept", "สร้างใบขอซื้อ เช็คงบ\nส่งขออนุมัติ ติดตามสถานะ", TEAL),
        ("ผู้อนุมัติ", "uat.director", "ลงนามคำสั่งแต่งตั้ง\nและรายงานขออนุมัติลำดับสุดท้าย", NAVY),
        ("พัสดุ / จัดซื้อ", "uat.procurement", "ส่งเข้า e-GP คัดเลือกผู้ชนะ\nเปิดและยืนยัน PO", AMBER),
        ("งานงบประมาณ", "uat.budget", "ดูวงเงินจอง/คงเหลือ\nเมื่อหน่วยงานเช็คงบ", GREEN),
    ]
    for i, (title, account, body, col) in enumerate(roles):
        x = 48 + i * 388
        y0 = 118
        round_rect(d, (x, y0, x + 364, y0 + 380), 18, WHITE, col, 3)
        round_rect(d, (x, y0, x + 364, y0 + 80), 18, col)
        d.rectangle((x, y0 + 60, x + 364, y0 + 80), fill=col)
        center_text(d, x, y0 + 18, 364, title, font(22, "bold"), WHITE)
        round_rect(d, (x + 28, y0 + 110, x + 336, y0 + 170), 10, col)
        center_text(d, x + 28, y0 + 110, 308, account, font(16, "semibold"), WHITE, 60)
        wrap_center(d, x + 20, y0 + 200, 324, body, font(18), SLATE, 10)
        d.text((x + 28, y0 + 320), "ห้ามใช้บัญชีคนเดียว", font=font(15, "medium"), fill=MUTED)
        d.text((x + 28, y0 + 350), "กดครบทุกขั้น", font=font(15, "medium"), fill=MUTED)

    committee = [
        ("ประธานตรวจรับ", "uat.committee1", "ลงนามแบบแสดงความบริสุทธิ์ใจ\nตามลำดับ แล้วลงนามใบตรวจรับ", TEAL),
        ("กรรมการตรวจรับ", "uat.committee2", "ลงนามแบบแสดงความบริสุทธิ์ใจ\nตามลำดับ แล้วลงนามใบตรวจรับ", NAVY),
        ("เลขาตรวจรับ", "uat.committee3", "ลงนามแบบแสดงความบริสุทธิ์ใจ\nตามลำดับ แล้วลงนามใบตรวจรับ", AMBER),
    ]
    start_x = 242
    for i, (title, account, body, col) in enumerate(committee):
        x = start_x + i * 388
        y0 = 530
        round_rect(d, (x, y0, x + 364, y0 + 400), 18, WHITE, col, 3)
        round_rect(d, (x, y0, x + 364, y0 + 80), 18, col)
        d.rectangle((x, y0 + 60, x + 364, y0 + 80), fill=col)
        center_text(d, x, y0 + 18, 364, title, font(22, "bold"), WHITE)
        round_rect(d, (x + 28, y0 + 110, x + 336, y0 + 170), 10, col)
        center_text(d, x + 28, y0 + 110, 308, account, font(16, "semibold"), WHITE, 60)
        wrap_center(d, x + 20, y0 + 200, 324, body, font(18), SLATE, 10)
        d.text((x + 28, y0 + 330), "รหัสผ่านชุดเดียวกับบัญชีอื่น", font=font(15, "medium"), fill=MUTED)
        d.text((x + 28, y0 + 360), "VpkUat@2569", font=font(15, "medium"), fill=MUTED)
    save(img, "fig_proc_roles.png")


def fig_proc_menus():
    img, d = new_canvas(1600, 640)
    d.text((48, 24), "แผนที่เมนูที่ใช้บ่อย", font=font(28, "bold"), fill=NAVY)
    menus = [
        ("หน่วยงาน", [
            "ใบขอซื้อ / สร้างใบขอซื้อ",
            "เช็คงบประมาณ",
            "แท็บรายชื่อคณะกรรมการ",
            "ส่งพัสดุ",
        ], TEAL),
        ("พัสดุ", [
            "จัดซื้อ / ใบขอซื้อจากหน่วยงาน",
            "สร้างเอกสารแต่งตั้งกรรมการ",
            "สร้างเอกสารอนุมัติขอซื้อ",
            "ส่งอนุมัติ",
        ], AMBER),
        ("ในกระบวนการ e-GP", [
            "แท็บเอกสาร e-GP",
            "แท็บเชิญเสนอราคา",
            "แท็บเปรียบเทียบราคา",
            "รายงานผล / ประกาศผู้ชนะ",
        ], NAVY),
    ]
    for i, (title, items, col) in enumerate(menus):
        x = 48 + i * 516
        round_rect(d, (x, 90, x + 492, 590), 18, WHITE, col, 3)
        round_rect(d, (x, 90, x + 492, 170), 18, col)
        d.rectangle((x, 150, x + 492, 170), fill=col)
        center_text(d, x, 108, 492, title, font(24, "bold"), WHITE)
        for j, t in enumerate(items):
            y = 210 + j * 84
            round_rect(d, (x + 28, y, x + 464, y + 68), 12, SOFT if col == TEAL else (NAVY_SOFT if col == NAVY else AMBER_SOFT))
            d.text((x + 52, y + 18), t, font=font(18, "medium"), fill=SLATE)
    save(img, "fig_proc_menus.png")


def fig_proc_egp_steps():
    img, d = new_canvas(1600, 780)
    d.text((48, 24), "ขั้นตอนในกระบวนการ e-GP", font=font(28, "bold"), fill=NAVY)
    d.text((48, 72), "แถบสถานะบนเอกสารกระบวนการ e-GP จะบอกว่าตอนนี้อยู่ขั้นไหน", font=font(18), fill=MUTED)
    steps = [
        ("1", "ส่ง PR", "หน่วยงานสร้างและส่ง"),
        ("2", "PR อนุมัติ", "ผู้อนุมัติครบขั้น"),
        ("3", "ร่าง e-GP", "พัสดุสร้างเอกสาร"),
        ("4", "ยืนยัน", "เริ่มกระบวนการ"),
        ("5", "เอกสาร e-GP", "ประกาศ TOR สัญญา"),
        ("6", "เชิญ/รับข้อเสนอ", "ใบเชิญและราคา"),
        ("7", "เปรียบเทียบ", "เลือกผู้ชนะ"),
        ("8", "รายงานผล", "ขออนุมัติสั่งซื้อ"),
        ("9", "เปิด PO", "สร้างให้ผู้ชนะ"),
    ]
    for i, (num, title, hint) in enumerate(steps):
        r, c = divmod(i, 3)
        x = 48 + c * 516
        y = 130 + r * 190
        col = TEAL if i < 2 else (AMBER if i < 7 else GREEN)
        round_rect(d, (x, y, x + 492, y + 166), 16, WHITE, col, 3)
        round_rect(d, (x + 24, y + 28, x + 88, y + 92), 12, col)
        center_text(d, x + 24, y + 28, 64, num, font(24, "bold"), WHITE, 64)
        d.text((x + 112, y + 36), title, font=font(22, "bold"), fill=NAVY)
        d.text((x + 112, y + 84), hint, font=font(16), fill=MUTED)
    save(img, "fig_proc_egp_steps.png")


def fig_proc_invite():
    img, d = new_canvas(1600, 680)
    d.text((48, 24), "เชิญเสนอราคา รับข้อเสนอ แล้วเลือกผู้ชนะ", font=font(28, "bold"), fill=NAVY)
    boxes = [
        ("เชิญ", "แท็บเชิญเสนอราคา", "เพิ่มผู้ประกอบการ\nกดบันทึกส่งคำเชิญ", TEAL),
        ("รับข้อเสนอ", "กดรับข้อเสนอ", "บันทึกราคาที่เสนอ\nในแท็บเปรียบเทียบราคา", AMBER),
        ("เลือกผู้ชนะ", "ติ๊ก ผู้ชนะ 1 ราย", "แล้วจัดทำรายงานผล\nขออนุมัติสั่งซื้อ/สั่งจ้าง", GREEN),
    ]
    for i, (num, title, body, col) in enumerate(boxes):
        x = 48 + i * 516
        round_rect(d, (x, 100, x + 492, 380), 18, WHITE, col, 3)
        round_rect(d, (x, 100, x + 492, 176), 18, col)
        d.rectangle((x, 156, x + 492, 176), fill=col)
        center_text(d, x, 118, 492, f"{i + 1}  {num}", font(24, "bold"), WHITE)
        d.text((x + 32, 210), title, font=font(20, "semibold"), fill=NAVY)
        wrap_center(d, x + 24, 264, 444, body, font(18), SLATE, 8)
        if i < 2:
            d.polygon([(x + 500, 230), (x + 516, 242), (x + 500, 254)], fill=TEAL)

    round_rect(d, (48, 420, 1552, 640), 16, AMBER_SOFT, AMBER, 2)
    d.text((72, 448), "กติกาที่ต้องจำ", font=font(20, "semibold"), fill=AMBER)
    rules = [
        "สร้าง RFQ/PO จากใบขอซื้อประเภทนี้ไม่ได้ จนกว่าจะเลือกผู้ชนะและอนุมัติรายงานผลแล้ว",
        "ผู้ชนะได้ทีละ 1 ราย เมื่อติ๊กรายใหม่ ระบบจะเอาเครื่องหมายรายเดิมออก",
        "ราคาใน PO จะดึงจากราคาที่ผู้ชนะเสนอ ไม่ใช่ราคาประมาณการในใบขอซื้อ",
    ]
    for i, t in enumerate(rules):
        d.text((72, 500 + i * 40), f"•  {t}", font=font(17), fill=SLATE)
    save(img, "fig_proc_invite.png")


def fig_proc_po():
    img, d = new_canvas(1600, 700)
    d.text((48, 24), "เปิด PO ได้เมื่อครบเงื่อนไขทั้ง 3 ข้อ", font=font(28, "bold"), fill=NAVY)
    conds = [
        ("1", "มีผู้ชนะ", "ติ๊กผู้ชนะในแท็บเปรียบเทียบราคา"),
        ("2", "รายงานผลอนุมัติ", "รายงานผลการพิจารณาเป็น อนุมัติแล้ว"),
        ("3", "กระบวนการยืนยันแล้ว", "เอกสาร e-GP สถานะ Confirmed"),
    ]
    for i, (num, title, body) in enumerate(conds):
        x = 48 + i * 516
        round_rect(d, (x, 100, x + 492, 280), 16, WHITE, TEAL, 3)
        round_rect(d, (x + 28, 128, x + 92, 192), 12, TEAL)
        center_text(d, x + 28, 128, 64, num, font(24, "bold"), WHITE, 64)
        d.text((x + 116, 140), title, font=font(22, "bold"), fill=NAVY)
        d.text((x + 32, 216), body, font=font(16), fill=MUTED)

    round_rect(d, (48, 320, 1552, 660), 16, WHITE, GREEN, 3)
    round_rect(d, (48, 320, 1552, 390), 16, GREEN)
    d.rectangle((48, 370, 1552, 390), fill=GREEN)
    d.text((80, 338), "ลำดับปุ่มหลังได้ผู้ชนะ", font=font(22, "bold"), fill=WHITE)
    steps = [
        "กด จัดทำรายงานผลและขออนุมัติ  →  ส่งขออนุมัติ  →  ผู้อนุมัติกด อนุมัติ",
        "กด สร้างประกาศผู้ชนะ (ถ้าต้องประกาศ) แล้วเผยแพร่",
        "กด สร้าง RFQ/PO ผู้ชนะ  ตรวจผู้ขายให้เป็นผู้ชนะ แล้วสร้างเอกสาร",
        "เปิดใบสั่งซื้อที่สร้างแล้ว กด ยืนยันใบสั่งซื้อ  สถานะเป็น Purchase Order",
    ]
    for i, t in enumerate(steps):
        d.text((80, 420 + i * 52), f"{i + 1}.  {t}", font=font(18), fill=SLATE)
    save(img, "fig_proc_po.png")


def fig_proc_pr_tabs():
    img, d = new_canvas(1600, 860)
    d.text((48, 24), "แท็บบนใบขอซื้อ  บันทึกจากซ้ายไปขวา", font=font(28, "bold"), fill=NAVY)
    d.text(
        (48, 72),
        "ชื่อแท็บตรงกับแถบบนใบขอซื้อในระบบ   กรอกสินค้าและรายชื่อคณะกรรมการก่อน แล้วออกเอกสารตามแท็บถัดไป",
        font=font(17),
        fill=MUTED,
    )
    tabs = [
        (
            "1",
            "สินค้า",
            "เพิ่มรายการสินค้า\nจำนวน หน่วย และงบประมาณ",
            TEAL,
        ),
        (
            "2",
            "รายชื่อ\nคณะกรรมการ",
            "ใส่กรรมการตรวจรับ\nจัดซื้อจัดจ้าง และราคากลาง",
            NAVY,
        ),
        (
            "3",
            "เอกสารแต่งตั้ง\nคณะกรรมการ",
            "ออกคำสั่งแต่งตั้งจากรายชื่อ\nแล้วส่งให้ ผ.อ ลงนาม",
            AMBER,
        ),
        (
            "4",
            "เอกสารแสดง\nความบริสุทธิ์ใจ",
            "ใช้เมื่อวงเงินมากกว่า 100,000 บาท\nลงนามเจ้าหน้าที่ หัวหน้า กรรมการ",
            NAVY,
        ),
        (
            "5",
            "เอกสารขออนุมัติ\nจัดซื้อจัดจ้าง",
            "ออกรายงานขออนุมัติ\nลงนามเจ้าหน้าที่ หัวหน้า ผ.อ",
            AMBER,
        ),
        (
            "6",
            "เอกสารราชการ\nที่เกี่ยวข้อง",
            "ดูเอกสารราชการทั้งหมด\nที่ออกจากใบขอซื้อนี้",
            NAVY,
        ),
        (
            "7",
            "ตรวจสอบ\nงบประมาณ",
            "ดูผลหลังกดเช็คงบประมาณ\nงบเพียงพอหรือไม่",
            GREEN,
        ),
    ]
    card_w, card_h = 368, 280
    for i, (num, title, body, col) in enumerate(tabs):
        if i < 4:
            x = 36 + i * 392
            y = 118
        else:
            x = 232 + (i - 4) * 392
            y = 430
        round_rect(d, (x, y, x + card_w, y + card_h), 16, WHITE, col, 3)
        round_rect(d, (x + 16, y + 20, x + 76, y + 80), 12, col)
        center_text(d, x + 16, y + 20, 60, num, font(24, "bold"), WHITE, 60)
        wrap_center(d, x + 88, y + 24, 264, title, font(16, "bold"), NAVY, 4)
        wrap_center(d, x + 16, y + 120, 336, body, font(16), SLATE, 8)
    save(img, "fig_proc_pr_tabs.png")


def fig_proc_committee():
    img, d = new_canvas(1600, 980, (236, 240, 244))
    d.rectangle((0, 0, 1600, 52), fill=NAVY)
    d.text((24, 12), "ใบขอซื้อ  /  PR6909001  /  แท็บคณะกรรมการ", font=font(16, "medium"), fill=WHITE)
    round_rect(d, (20, 68, 1580, 960), 10, WHITE)

    tabs = [
        ("สินค้า", False),
        ("รายชื่อคณะกรรมการ", True),
        ("แต่งตั้ง", False),
        ("ความบริสุทธิ์ใจ", False),
        ("ขออนุมัติ", False),
        ("เอกสารที่เกี่ยวข้อง", False),
        ("งบประมาณ", False),
    ]
    x = 36
    for name, active in tabs:
        tw = text_w(d, name, font(14, "semibold" if active else "regular")) + 36
        if active:
            round_rect(d, (x, 88, x + tw, 128), 8, TEAL)
            center_text(d, x, 88, tw, name, font(14, "semibold"), WHITE, 40)
        else:
            d.text((x + 12, 98), name, font=font(14), fill=MUTED)
        x += tw + 8

    d.text((36, 148), "ข้อมูลตัวอย่างชุดอบรม  ซื้อ/จ้าง/เช่า ไม่เกิน 500,000 บาท", font=font(16, "medium"), fill=MUTED)

    def draw_group(y, title, rows):
        d.text((36, y), title, font=font(18, "bold"), fill=NAVY)
        headers = ["ลำดับ", "พนักงาน", "บทบาท", "หน่วยงาน"]
        widths = [90, 420, 220, 420]
        hx = 36
        hy = y + 40
        for h, w in zip(headers, widths):
            round_rect(d, (hx, hy, hx + w - 8, hy + 36), 4, TEAL)
            center_text(d, hx, hy, w - 8, h, font(13, "semibold"), WHITE, 36)
            hx += w
        for i, (emp, role, dept) in enumerate(rows):
            ry = hy + 40 + i * 40
            fill = SOFT if i % 2 == 0 else WHITE
            hx = 36
            vals = [str(i + 1), emp, role, dept]
            for val, w in zip(vals, widths):
                round_rect(d, (hx, ry, hx + w - 8, ry + 36), 4, fill, (215, 222, 230), 1)
                d.text((hx + 12, ry + 8), val, font=font(14, "medium" if val == "ประธาน" else "regular"), fill=TEAL if val == "ประธาน" else SLATE)
                hx += w
        return hy + 40 + len(rows) * 40

    y = draw_group(
        188,
        "คณะกรรมการตรวจรับ  (ต้องอย่างน้อย 3 คน)",
        [
            ("ผู้ทดสอบกรรมการตรวจรับ คนที่ 1", "ประธาน", "หน่วยงานทดสอบ"),
            ("ผู้ทดสอบกรรมการตรวจรับ คนที่ 2", "กรรมการ", "หน่วยงานทดสอบ"),
            ("ผู้ทดสอบกรรมการตรวจรับ คนที่ 3", "กรรมการ", "หน่วยงานทดสอบ"),
        ],
    )
    y = draw_group(
        y + 28,
        "คณะกรรมการจัดซื้อจัดจ้าง",
        [
            ("นิรันดร์ หัวหน้าพัสดุ", "ประธาน", "หน่วยงานพัสดุ"),
            ("สุภาพร รองหัวหน้าพัสดุ", "กรรมการ", "หน่วยงานพัสดุ"),
            ("สมจิต จัดซื้อ", "กรรมการ", "หน่วยงานพัสดุ"),
        ],
    )
    draw_group(
        y + 28,
        "คณะกรรมการกำหนดราคากลาง",
        [
            ("วิชัย พัสดุ", "ประธาน", "หน่วยงานพัสดุ"),
            ("มาลี บัญชี", "กรรมการ", "หน่วยงานบัญชีการเงิน"),
            ("สมหญิง รองหัวหน้า", "กรรมการ", "หน่วยงาน IT"),
        ],
    )
    save(img, "fig_proc_committee.png")


def fig_proc_wa_order():
    img, d = new_canvas(1600, 680)
    d.text((48, 24), "ออกคำสั่งแต่งตั้งคณะกรรมการตรวจรับ แล้วพิมพ์", font=font(28, "bold"), fill=NAVY)
    d.text(
        (48, 72),
        "กดจากแท็บเอกสารแต่งตั้งคณะกรรมการ  รายชื่อดึงจากคณะกรรมการตรวจรับ",
        font=font(18),
        fill=MUTED,
    )
    boxes = [
        ("บันทึกรายชื่อ", "แท็บคณะกรรมการ", "ใส่กรรมการตรวจรับ\nแล้วบันทึกใบขอซื้อ", TEAL),
        ("ออกคำสั่ง", "แท็บเอกสารแต่งตั้ง", "ออกคำสั่งแต่งตั้ง\nคณะกรรมการตรวจรับ", NAVY),
        ("ตรวจข้อความ", "เปิดเอกสารคำสั่ง", "ตรวจรายชื่อ เรื่อง\nเลขที่ และผู้ลงนาม", AMBER),
        ("พิมพ์", "กดพิมพ์ PDF", "หรือสร้างไฟล์ Word\nเพื่อดาวน์โหลด", GREEN),
    ]
    for i, (title, sub, body, col) in enumerate(boxes):
        x = 36 + i * 392
        round_rect(d, (x, 120, x + 368, 430), 18, WHITE, col, 3)
        round_rect(d, (x, 120, x + 368, 196), 18, col)
        d.rectangle((x, 176, x + 368, 196), fill=col)
        center_text(d, x, 138, 368, f"{i + 1}  {title}", font(22, "bold"), WHITE)
        d.text((x + 24, 220), sub, font=font(18, "semibold"), fill=NAVY)
        wrap_center(d, x + 16, 270, 336, body, font(17), SLATE, 8)
        if i < 3:
            d.polygon([(x + 376, 260), (x + 392, 274), (x + 376, 288)], fill=TEAL)

    round_rect(d, (48, 470, 1552, 640), 16, AMBER_SOFT, AMBER, 2)
    d.text((72, 498), "สิ่งที่ต้องจำ", font=font(20, "semibold"), fill=AMBER)
    rules = [
        "ยังไม่มีกรรมการตรวจรับในแท็บนี้ ระบบจะไม่ออกคำสั่ง ให้บันทึกรายชื่อก่อน",
        "ใบเดียวกันออกคำสั่งซ้ำไม่ได้ ปุ่มจะเปลี่ยนเป็น เปิดคำสั่งแต่งตั้งคณะกรรมการตรวจรับ",
        "พิมพ์ PDF ใช้ลงนาม/เก็บสำเนา  สร้างไฟล์ Word ใช้เมื่อต้องแก้ไขแบบฟอร์มก่อนพิมพ์",
    ]
    for i, t in enumerate(rules):
        d.text((72, 542 + i * 30), f"•  {t}", font=font(16), fill=SLATE)
    save(img, "fig_proc_wa_order.png")


def fig_proc_integrity():
    img, d = new_canvas(1600, 680)
    d.text((48, 24), "สร้างเอกสารแสดงความบริสุทธิ์ใจ แล้วลงนามตามลำดับ", font=font(28, "bold"), fill=NAVY)
    d.text(
        (48, 72),
        "แท็บเอกสารแสดงความบริสุทธิ์ใจ   พิมพ์ PDF แล้วส่งเอกสารอนุมัติ   เจ้าหน้าที่ → หัวหน้าเจ้าหน้าที่ → กรรมการตามลำดับ",
        font=font(16),
        fill=MUTED,
    )
    boxes = [
        ("สร้างเอกสาร", "แท็บความบริสุทธิ์ใจ", "ดึงเจ้าหน้าที่ หัวหน้า\nและกรรมการตรวจรับ", TEAL),
        ("พิมพ์ PDF", "สร้างไฟล์ PDF", "เปิดดูแล้วพิมพ์ได้\nสำหรับประทับลายเซ็น", NAVY),
        ("ส่งเอกสารอนุมัติ", "กดส่งเพื่อลงนาม", "ส่งเข้ากล่องงานรออนุมัติ\nตามลำดับผู้ลงนาม", AMBER),
        ("เจ้าหน้าที่ / หัวหน้า", "งานรออนุมัติของฉัน", "เจ้าหน้าที่ลงนามก่อน\nแล้วหัวหน้าเจ้าหน้าที่", NAVY),
        ("กรรมการตามลำดับ", "ประธาน แล้วกรรมการ", "คนถัดไปเห็นเมื่อ\nคนก่อนลงนามแล้ว", GREEN),
    ]
    card_w = 292
    gap = 318
    for i, (title, sub, body, col) in enumerate(boxes):
        x = 20 + i * gap
        round_rect(d, (x, 120, x + card_w, 430), 16, WHITE, col, 3)
        round_rect(d, (x, 120, x + card_w, 196), 16, col)
        d.rectangle((x, 176, x + card_w, 196), fill=col)
        center_text(d, x, 138, card_w, f"{i + 1}  {title}", font(17, "bold"), WHITE)
        d.text((x + 16, 220), sub, font=font(16, "semibold"), fill=NAVY)
        wrap_center(d, x + 10, 270, card_w - 20, body, font(15), SLATE, 8)
        if i < 4:
            ax = x + card_w + 4
            d.polygon([(ax, 262), (ax + 16, 274), (ax, 286)], fill=TEAL)

    round_rect(d, (48, 470, 1552, 640), 16, AMBER_SOFT, AMBER, 2)
    d.text((72, 498), "สิ่งที่ต้องจำ", font=font(20, "semibold"), fill=AMBER)
    rules = [
        "แบบนี้ใช้เมื่อวงเงินมากกว่า 100,000 บาท  กดจากแท็บเอกสารแสดงความบริสุทธิ์ใจ ไม่ใช่แท็บรายชื่อคณะกรรมการ",
        "หลังพิมพ์ PDF ต้องกดส่งเอกสารอนุมัติ จึงจะเข้ากล่องงานรออนุมัติ  ผู้อำนวยการไม่ลงนามชุดนี้",
        "เอกสารถึงลงนามแล้วเมื่อกรรมการคนสุดท้ายลงนามครบ  คนที่ยังไม่ถึงลำดับจะยังไม่เห็นรายการ",
    ]
    for i, t in enumerate(rules):
        d.text((72, 542 + i * 30), f"•  {t}", font=font(16), fill=SLATE)
    save(img, "fig_proc_integrity.png")


def fig_proc_approval():
    img, d = new_canvas(1600, 680)
    d.text((48, 24), "ออกหนังสือขออนุมัติจัดซื้อจัดจ้าง แล้วลงนามตามลำดับ", font=font(28, "bold"), fill=NAVY)
    d.text(
        (48, 72),
        "แท็บเอกสารขออนุมัติ   ลงนามตามลำดับเจ้าหน้าที่ → หัวหน้าเจ้าหน้าที่ → ผู้อำนวยการ",
        font=font(18),
        fill=MUTED,
    )
    boxes = [
        ("บันทึกใบขอซื้อ", "สินค้าและกรรมการ", "กรอกรายการและกรรมการ\nตรวจรับให้ครบก่อน", TEAL),
        ("ออกหนังสือ", "แท็บเอกสารขออนุมัติ", "ออกหนังสือขออนุมัติ\nตามวิธีในใบขอซื้อ", NAVY),
        ("ตรวจเนื้อหา", "เปิดรายงานขออนุมัติ", "ตรวจข้อ ๒ วงเงิน\nแล้วกดส่งเพื่อลงนาม", AMBER),
        ("ลงนามตามลำดับ", "งานรออนุมัติของฉัน", "เจ้าหน้าที่ หัวหน้า\nแล้วผู้อำนวยการ", GREEN),
    ]
    for i, (title, sub, body, col) in enumerate(boxes):
        x = 36 + i * 392
        round_rect(d, (x, 120, x + 368, 430), 18, WHITE, col, 3)
        round_rect(d, (x, 120, x + 368, 196), 18, col)
        d.rectangle((x, 176, x + 368, 196), fill=col)
        center_text(d, x, 138, 368, f"{i + 1}  {title}", font(22, "bold"), WHITE)
        d.text((x + 24, 220), sub, font=font(18, "semibold"), fill=NAVY)
        wrap_center(d, x + 16, 270, 336, body, font(17), SLATE, 8)
        if i < 3:
            d.polygon([(x + 376, 260), (x + 392, 274), (x + 376, 288)], fill=TEAL)

    round_rect(d, (48, 470, 1552, 640), 16, AMBER_SOFT, AMBER, 2)
    d.text((72, 498), "สิ่งที่ต้องจำ", font=font(20, "semibold"), fill=AMBER)
    rules = [
        "กดจากแท็บเอกสารขออนุมัติจัดซื้อจัดจ้าง  วิธีในรายงานตามที่เลือกในใบขอซื้อ",
        "ลงนามตามลำดับเจ้าหน้าที่ หัวหน้าเจ้าหน้าที่ แล้วผู้อำนวยการ  คนถัดไปเห็นเมื่อคนก่อนลงนามแล้ว",
        "เมื่อคำสั่งแต่งตั้งและรายงานนี้ลงนามครบ ระบบอนุมัติใบขอซื้อให้อัตโนมัติ",
    ]
    for i, t in enumerate(rules):
        d.text((72, 542 + i * 30), f"•  {t}", font=font(16), fill=SLATE)
    save(img, "fig_proc_approval.png")


def fig_proc_do_dont():
    img, d = new_canvas(1600, 640)
    d.text((48, 24), "สิ่งที่ควรทำ และไม่ควรทำ", font=font(28, "bold"), fill=NAVY)
    round_rect(d, (48, 90, 776, 600), 18, WHITE, GREEN, 3)
    round_rect(d, (48, 90, 776, 160), 18, GREEN)
    d.rectangle((48, 140, 776, 160), fill=GREEN)
    center_text(d, 48, 106, 728, "ควรทำ", font(24, "bold"), WHITE)
    dos = [
        "เลือกประเภท จัดซื้อจัดจ้างผ่านพัสดุ เมื่อต้องเข้า e-GP",
        "เช็คงบให้ผ่านก่อนส่งขออนุมัติ",
        "ส่งกระบวนการ e-GP จากใบที่อนุมัติแล้ว",
        "บันทึกข้อเสนอครบ แล้วเลือกผู้ชนะ 1 ราย",
        "อนุมัติรายงานผลก่อนเปิด PO",
    ]
    for i, t in enumerate(dos):
        d.text((80, 192 + i * 72), f"✓  {t}", font=font(18), fill=SLATE)

    round_rect(d, (824, 90, 1552, 600), 18, WHITE, RED, 3)
    round_rect(d, (824, 90, 1552, 160), 18, RED)
    d.rectangle((824, 140, 1552, 160), fill=RED)
    center_text(d, 824, 106, 728, "ไม่ควรทำ", font(24, "bold"), WHITE)
    donts = [
        "สร้าง PO ตรงจากใบขอซื้อประเภท e-GP",
        "ส่งขออนุมัติทั้งที่เช็คงบยังไม่ผ่าน",
        "เปิดกระบวนการ e-GP จากใบที่ยังเป็นร่าง",
        "เลือกผู้ชนะหลายราย หรือยังไม่มีราคา",
        "ยืนยัน PO โดยยังไม่ตรวจผู้ขายและจำนวน",
    ]
    for i, t in enumerate(donts):
        d.text((856, 192 + i * 72), f"✗  {t}", font=font(18), fill=SLATE)
    save(img, "fig_proc_do_dont.png")


def main():
    fig_proc_cover()
    fig_proc_flow()
    fig_proc_roles()
    fig_proc_menus()
    fig_proc_egp_steps()
    fig_proc_invite()
    fig_proc_po()
    fig_proc_do_dont()
    fig_proc_pr_tabs()
    fig_proc_committee()
    fig_proc_wa_order()
    fig_proc_integrity()
    fig_proc_approval()


if __name__ == "__main__":
    main()
