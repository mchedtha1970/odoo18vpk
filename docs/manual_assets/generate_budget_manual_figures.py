#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Training illustrations for the VPK budget user manual."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("/opt/odoo18vpk/docs/manual_assets/figures")
FONT_DIR = Path("/opt/odoo18vpk/docs/manual_assets/fonts")

NAVY = (18, 58, 86)
TEAL = (15, 122, 114)
AMBER = (196, 126, 20)
RED = (180, 67, 58)
GREEN = (44, 122, 69)
SLATE = (47, 58, 72)
MUTED = (91, 104, 120)
LINE = (215, 222, 230)
WHITE = (255, 255, 255)
BG = (246, 248, 250)
SOFT = (229, 245, 243)
AMBER_SOFT = (253, 243, 224)
RED_SOFT = (251, 236, 234)
GREEN_SOFT = (229, 245, 234)
NAVY_SOFT = (232, 241, 248)
GREEN_SOFT = GREEN_SOFT
RED_SOFT = RED_SOFT
AMBER_SOFT = AMBER_SOFT
SOFT = SOFT


def font(size, weight="regular"):
    name = {
        "regular": "Prompt-Regular.ttf",
        "medium": "Prompt-Medium.ttf",
        "medium": "Prompt-Medium.ttf",
        "semibold": "Prompt-SemiBold.ttf",
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
    lines = text.split("\n")
    for i, line in enumerate(lines):
        center_text(draw, x, y + i * (fnt.size + gap), w, line, fnt, fill)


wrap_center = wrap_center  # alias used by later figures
wrap_center = wrap_center


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print(path)
    return path


def fig_cover():
    img, d = new_canvas(1600, 640, NAVY)
    d.rectangle((0, 0, 14, 640), fill=TEAL)
    d.text((70, 90), "โรงพยาบาลวชิระภูเก็ต  ·  Odoo 18", font=font(22), fill=(159, 201, 196))
    d.text((70, 150), "คู่มือการใช้งาน", font=font(28, "medium"), fill=WHITE)
    d.text((70, 200), "ระบบงบประมาณ", font=font(64, "bold"), fill=WHITE)
    d.text(
        (70, 300),
        "สำหรับฝึกอบรมผู้ใช้  ·  หน่วยงาน  งานงบประมาณ  พัสดุ  การเงิน",
        font=font(24),
        fill=(215, 228, 238),
    )
    boxes = [
        ("1", "ตั้งงบ", TEAL),
        ("2", "ใช้งบ", (28, 78, 110)),
        ("3", "ดูคงเหลือ", (36, 99, 90)),
    ]
    for i, (num, title, col) in enumerate(boxes):
        x = 70 + i * 310
        round_rect(d, (x, 430, x + 280, 540), 16, col)
        d.text((x + 28, 448), num, font=font(18, "bold"), fill=(159, 201, 196))
        d.text((x + 28, 478), title, font=font(28, "semibold"), fill=WHITE)
    d.text((70, 575), "เวอร์ชัน 1.0  ·  สิงหาคม 2569  ·  ใช้ประกอบการอบรมในห้องและทบทวนด้วยตนเอง", font=font(18), fill=(159, 201, 196))
    save(img, "cover.png")


def fig_two_phases():
    img, d = new_canvas(1600, 620)
    d.text((48, 28), "ระบบงบประมาณมี 2 ช่วง  ห้ามสลับลำดับ", font=font(30, "bold"), fill=NAVY)
    d.text((48, 78), "ยังซื้อของไม่ได้ จนกว่าจะมีงบที่อนุมัติเข้าแผนประจำปีแล้ว", font=font(20), fill=MUTED)

    round_rect(d, (48, 140, 770, 560), 20, WHITE, TEAL, 3)
    round_rect(d, (48, 140, 770, 210), 20, TEAL)
    d.rectangle((48, 190, 770, 210), fill=TEAL)
    d.text((80, 156), "ช่วงที่ 1   ตั้งงบประจำปี", font=font(26, "bold"), fill=WHITE)
    steps = ["หน่วยงานสร้างคำของบ", "ส่งให้งานงบประมาณ", "งานงบจัดสรรยอด", "อนุมัติ แล้วเข้าแผนปี"]
    for i, t in enumerate(steps):
        y = 240 + i * 70
        round_rect(d, (80, y, 148, y + 50), 12, TEAL)
        center_text(d, 80, y, 68, str(i + 1), font(22, "bold"), WHITE, 50)
        d.text((172, y + 10), t, font=font(22, "medium"), fill=SLATE)

    round_rect(d, (830, 140, 1552, 560), 20, WHITE, AMBER, 3)
    round_rect(d, (830, 140, 1552, 210), 20, AMBER)
    d.rectangle((830, 190, 1552, 210), fill=AMBER)
    d.text((862, 156), "ช่วงที่ 2   ใช้งบผ่านเอกสารซื้อ", font=font(26, "bold"), fill=WHITE)
    steps2 = ["สร้างใบขอซื้อ (PR)", "กดเช็คงบ แล้วส่งอนุมัติ", "พัสดุยืนยันใบสั่งซื้อ (PO)", "การเงินตั้งเจ้าหนี้"]
    for i, t in enumerate(steps2):
        y = 240 + i * 70
        round_rect(d, (862, y, 930, y + 50), 12, AMBER)
        center_text(d, 862, y, 68, str(i + 1), font(22, "bold"), WHITE, 50)
        d.text((954, y + 10), t, font=font(22, "medium"), fill=SLATE)
    save(img, "fig_two_phases.png")


def fig_cycle():
    img, d = new_canvas(1600, 520)
    d.text((48, 24), "วงจรงานทั้งระบบ  เดินจากซ้ายไปขวา", font=font(28, "bold"), fill=NAVY)
    items = [
        ("1", "ข้อมูลหลัก", "แหล่งเงิน หน่วยงาน\nแบบฟอร์ม หมวด", NAVY),
        ("2", "แผนปี", "เปิดกรอบปีงบ\nและช่วงวันที่", NAVY),
        ("3", "คำของบ", "หน่วยงานกรอก\nแล้วกดส่งใบคำขอ", TEAL),
        ("4", "อนุมัติ", "งานงบจัดสรร\nแล้วยอดเข้าแผน", TEAL),
        ("5", "ใช้งบ", "PR → PO → บิล\nระบบกันเงินให้เอง", AMBER),
        ("6", "ดูคงเหลือ", "Dashboard\nและรายการงบ", GREEN),
    ]
    for i, (num, title, body, col) in enumerate(items):
        x = 36 + i * 260
        round_rect(d, (x, 90, x + 236, 150), 14, col)
        center_text(d, x, 98, 236, f"{num}  {title}", font(20, "bold"), WHITE)
        round_rect(d, (x, 150, x + 236, 330), 14, WHITE, col, 2)
        d.rectangle((x, 150, x + 236, 164), fill=WHITE)
        wrap_center(d, x + 12, 180, 212, body, font(18), SLATE, 8)
        if i < 5:
            d.polygon([(x + 242, 200), (x + 256, 210), (x + 242, 220)], fill=TEAL)
    round_rect(d, (36, 360, 1564, 490), 16, SOFT, TEAL, 2)
    d.text((64, 384), "พูดกับผู้ใช้แบบนี้", font=font(18, "semibold"), fill=TEAL)
    d.text(
        (64, 424),
        "แผนปีเป็นกรอบ  ·  หน่วยงานของบเข้าไปในกรอบนี้  ·  งานงบบอกว่าใช้ได้เท่าไร  ·  การซื้อของต้องมีใบขอซื้อ ระบบจะกันเงินให้เอง",
        font=font(20),
        fill=SLATE,
    )
    save(img, "fig_cycle.png")


def fig_roles():
    img, d = new_canvas(1600, 560)
    d.text((48, 24), "ใครกดอะไรในระบบ", font=font(28, "bold"), fill=NAVY)
    d.text((48, 72), "จำบทบาทตัวเองให้ชัด  ห้ามใช้บัญชีเดียวกดครบทุกขั้นตอนอบรม", font=font(18), fill=MUTED)
    roles = [
        ("หน่วยงาน", TEAL, ["สร้างคำของบ แล้วส่ง", "สร้างใบขอซื้อ", "กดเช็คงบ ส่งอนุมัติ PR"], "uat.dept"),
        ("งานงบประมาณ", AMBER, ["ดูแลข้อมูลหลักและแผนปี", "รับเรื่อง พิจารณา จัดสรร", "อนุมัติ หรือตีกลับ"], "uat.budget"),
        ("พัสดุ / จัดซื้อ", NAVY, ["สร้างใบสั่งซื้อจาก PR", "ยืนยัน PO", "ยอดจองกลายเป็นผูกพัน"], "uat.procurement"),
        ("การเงิน", GREEN, ["ตั้งเจ้าหนี้จากใบแจ้งหนี้", "โพสต์บิล", "ยอดกลายเป็นใช้จริง"], "ผู้ใช้บัญชี"),
    ]
    for i, (title, col, lines, login) in enumerate(roles):
        x = 36 + i * 392
        round_rect(d, (x, 130, x + 372, 520), 18, WHITE, col, 3)
        round_rect(d, (x, 130, x + 372, 210), 18, col)
        d.rectangle((x, 190, x + 372, 210), fill=col)
        center_text(d, x, 148, 372, title, font(24, "bold"), WHITE)
        for j, line in enumerate(lines):
            y = 240 + j * 58
            round_rect(d, (x + 24, y, x + 56, y + 32), 8, col)
            center_text(d, x + 24, y, 32, str(j + 1), font(16, "bold"), WHITE, 32)
            d.text((x + 72, y + 4), line, font=font(18), fill=SLATE)
        d.text((x + 24, 460), f"บัญชีอบรม: {login}", font=font(16, "medium"), fill=MUTED)
    save(img, "fig_roles.png")


def fig_forms():
    img, d = new_canvas(1600, 520)
    d.text((48, 24), "คำของบมีแค่ 4 แบบฟอร์ม  เลือกใบให้ถูก", font=font(28, "bold"), fill=NAVY)
    forms = [
        ("01", "แบบฟอร์มตั้งงบวัสดุ", "ยา เวชภัณฑ์ วัสดุทั่วไป\nต้องมีรายละเอียดสินค้า\nและกลุ่มงบประมาณ-วัสดุ", TEAL),
        ("02", "แบบฟอร์มครุภัณฑ์", "เครื่องมือ เครื่องใช้\nคอมพิวเตอร์ใช้ใบนี้\nไม่ต้องมีกลุ่มวัสดุ", NAVY),
        ("03", "แบบฟอร์ม ก่อสร้าง", "งานซ่อม ต่อเติม\nปรับปรุงอาคาร\nรายการงานก่อสร้าง", AMBER),
        ("04", "แบบฟอร์มโครงการ", "ค่าใช้จ่ายโครงการ\nกิจกรรมต่างๆ\nรายการโครงการ", GREEN),
    ]
    for i, (num, title, body, col) in enumerate(forms):
        x = 36 + i * 392
        round_rect(d, (x, 100, x + 372, 480), 18, WHITE, col, 3)
        round_rect(d, (x + 24, 128, x + 96, 180), 12, col)
        center_text(d, x + 24, 128, 72, num, font(22, "bold"), WHITE, 52)
        wrap_center(d, x + 16, 210, 340, title, font(24, "bold"), NAVY, 6)
        wrap_center(d, x + 16, 310, 340, body, font(18), MUTED, 8)
    save(img, "fig_forms.png")


def fig_request_flow():
    img, d = new_canvas(1600, 620)
    d.text((48, 24), "สถานะคำของบ และปุ่มที่ต้องกด", font=font(28, "bold"), fill=NAVY)
    states = [
        ("ร่าง", "หน่วยงานกรอก", "ส่งใบคำขอ", TEAL),
        ("ส่งงานงบ", "เข้าคิวงานงบ", "รับเรื่อง", AMBER),
        ("รับเรื่อง", "ยืนยันว่าได้เอกสาร", "เริ่มพิจารณา", AMBER),
        ("พิจารณา", "ใส่ยอดจัดสรรให้ครบ", "อนุมัติ", GREEN),
        ("อนุมัติ", "ยอดเข้าแผนปี", "ใช้จ่ายได้", GREEN),
    ]
    for i, (title, who, btn, col) in enumerate(states):
        x = 40 + i * 308
        round_rect(d, (x, 100, x + 284, 340), 16, WHITE, col, 2)
        round_rect(d, (x + 18, 120, x + 266, 176), 10, col)
        center_text(d, x + 18, 120, 248, title, font(22, "bold"), WHITE, 56)
        wrap_center(d, x + 12, 200, 260, who, font(18), SLATE)
        round_rect(d, (x + 40, 270, x + 244, 318), 10, col)
        center_text(d, x + 40, 270, 204, btn, font(16, "semibold"), WHITE, 48)
        if i < 4:
            d.polygon([(x + 288, 210), (x + 304, 222), (x + 288, 234)], fill=TEAL)

    round_rect(d, (40, 380, 780, 580), 16, RED_SOFT, RED, 2)
    d.text((68, 408), "ถ้าไม่ผ่าน  ·  กด ตีกลับ", font=font(22, "bold"), fill=RED)
    d.text((68, 460), "หน่วยงานตั้งเป็นร่าง แก้รายการ\nใส่เหตุผลให้ครบ แล้วส่งใหม่", font=font(20), fill=SLATE)
    round_rect(d, (820, 380, 1560, 580), 16, GREEN_SOFT, GREEN, 2)
    d.text((848, 408), "ถ้าผ่าน  ·  ได้วงเงินใช้จ่าย", font=font(22, "bold"), fill=GREEN)
    d.text((848, 460), "ใช้ได้เท่าที่จัดสรร ไม่ใช่เท่าที่ขอ\nใบที่อนุมัติแล้วหน่วยงานแก้รายการหลักไม่ได้", font=font(20), fill=SLATE)
    save(img, "fig_request_flow.png")


def fig_request_form():
    """Annotated mock of the departmental budget request form."""
    img, d = new_canvas(1600, 900, (236, 240, 244))
    # app chrome
    d.rectangle((0, 0, 1600, 56), fill=NAVY)
    d.text((24, 14), "งบประมาณ  /  บันทึกคำของบ  /  แบบฟอร์มตั้งงบวัสดุ", font=font(18, "medium"), fill=WHITE)
    # header buttons
    round_rect(d, (20, 72, 1580, 140), 8, WHITE)
    buttons = [("พิมพ์แบบตั้งงบวัสดุ", MUTED, WHITE), ("ส่งใบคำขอ", TEAL, WHITE)]
    x = 40
    for label, bg, fg in buttons:
        w = text_w(d, label, font(16, "semibold")) + 36
        round_rect(d, (x, 88, x + w, 124), 8, bg)
        center_text(d, x, 88, w, label, font(16, "semibold"), fg, 36)
        x += w + 12
    # statusbar
    statuses = ["ร่าง", "ส่งงานงบ", "รับเรื่อง", "พิจารณา", "อนุมัติ"]
    sx = 980
    for i, st in enumerate(statuses):
        col = TEAL if i == 0 else LINE
        fg = WHITE if i == 0 else MUTED
        round_rect(d, (sx, 92, sx + 108, 122), 12, col)
        center_text(d, sx, 92, 108, st, font(13, "medium"), fg, 30)
        sx += 112
    # sheet
    round_rect(d, (20, 156, 1580, 880), 8, WHITE)
    d.text((48, 176), "DBR/2026/0001", font=font(28, "bold"), fill=NAVY)

    fields = [
        (48, 240, "วันที่ขอ", "24/08/2569"),
        (430, 240, "ปีงบประมาณ", "2569"),
        (812, 240, "ผู้ขอ", "หน่วยงานทดสอบ"),
        (48, 330, "หน่วยงาน / ศูนย์ต้นทุน", "หน่วยงานทดสอบ"),
        (430, 330, "งบประมาณประจำปี", "งบประมาณรายจ่ายประจำปี พ.ศ. 2569"),
        (812, 330, "แบบฟอร์มคำของบ", "แบบฟอร์มตั้งงบวัสดุ"),
        (1194, 330, "แหล่งเงิน", "เงินบำรุง"),
        (48, 420, "งบประมาณที่ขอ", "10,000.00"),
        (430, 420, "งบประมาณที่ได้รับ", "8,000.00"),
    ]
    for x, y, label, value in fields:
        d.text((x, y), label, font=font(13), fill=MUTED)
        round_rect(d, (x, y + 24, x + 350, y + 64), 6, BG, LINE, 1)
        d.text((x + 12, y + 32), value, font=font(16, "medium"), fill=SLATE)

    # callouts
    def callout(x, y, text, col=TEAL):
        round_rect(d, (x, y, x + 360, y + 44), 8, col)
        d.text((x + 14, y + 10), text, font=font(15, "semibold"), fill=WHITE)

    callout(48, 500, "1  เลือกหน่วยงานและแหล่งเงินให้ตรงแผน")
    callout(430, 500, "2  เลือกแบบฟอร์มก่อน จึงจะมีแท็บรายการ")
    callout(812, 500, "3  ยอดขอระบบคำนวณจากบรรทัด")

    # notebook tabs
    d.rectangle((48, 570, 1532, 618), fill=BG)
    round_rect(d, (48, 570, 280, 618), 8, WHITE, TEAL, 2)
    d.text((68, 582), "แบบตั้งงบภาพรวม", font=font(16, "semibold"), fill=TEAL)
    d.text((300, 582), "รายละเอียดสินค้า", font=font(16), fill=MUTED)

    # table header
    d.rectangle((48, 630, 1532, 674), fill=NAVY)
    headers = [(60, "หมวดงบ"), (280, "กลุ่มวัสดุ"), (520, "ประเภทวัสดุย่อย"), (820, "งบที่ขอ"), (1020, "งบที่ได้รับ"), (1240, "เหตุผล")]
    for x, h in headers:
        d.text((x, 640), h, font=font(14, "semibold"), fill=WHITE)
    d.rectangle((48, 674, 1532, 730), fill=WHITE)
    d.line((48, 730, 1532, 730), fill=LINE, width=1)
    vals = [(60, "หมวดค่าวัสดุ"), (280, "วัสดุการแพทย์"), (520, "การแพทย์ผ่าตัด"), (820, "10,000.00"), (1020, "8,000.00"), (1240, "ใช้ในงานผ่าตัด")]
    for x, v in vals:
        d.text((x, 688), v, font=font(15), fill=SLATE)

    round_rect(d, (48, 760, 1532, 848), 10, AMBER_SOFT, AMBER, 2)
    d.text((72, 778), "จุดที่มักสะดุด", font=font(16, "bold"), fill=AMBER)
    d.text((72, 810), "งบวัสดุต้องมีรายละเอียดสินค้าในแท็บถัดไป และต้องมีเหตุผลประกอบคำขอ ไม่งั้นกดส่งใบคำขอไม่ได้", font=font(16), fill=SLATE)
    save(img, "fig_request_form.png")


def fig_spend_flow():
    img, d = new_canvas(1600, 640)
    d.text((48, 24), "ช่วงใช้งบ  ซื้อของทีละใบ ตามนี้", font=font(28, "bold"), fill=NAVY)
    steps = [
        ("ร่าง PR", "ยังไม่กันเงิน", NAVY, "สร้างใบขอซื้อ\nเลือกมิติงบให้ครบ"),
        ("เช็คงบ", "พอไหม", TEAL, "กดปุ่ม เช็คงบประมาณ\nยังไม่จองวงเงิน"),
        ("ส่ง PR", "จองงบ", AMBER, "ส่งอนุมัติแล้ว\nใบอื่นใช้วงเงินซ้ำไม่ได้"),
        ("ยืนยัน PO", "ผูกพันงบ", AMBER, "พัสดุ Confirm PO\nยอดย้ายจากจองเป็นผูกพัน"),
        ("ตั้งเจ้าหนี้", "ใช้จริง", GREEN, "การเงินโพสต์บิล\nคงเหลือลดลงถาวร"),
    ]
    for i, (title, sub, col, body) in enumerate(steps):
        x = 36 + i * 312
        round_rect(d, (x, 100, x + 292, 430), 16, WHITE, col, 3)
        round_rect(d, (x, 100, x + 292, 210), 16, col)
        d.rectangle((x, 190, x + 292, 210), fill=col)
        center_text(d, x, 118, 292, title, font(24, "bold"), WHITE)
        center_text(d, x, 162, 292, sub, font(16), (255, 255, 255, 200) if False else (220, 236, 234))
        wrap_center(d, x + 16, 250, 260, body, font(18), SLATE, 8)
        if i < 4:
            d.polygon([(x + 296, 250), (x + 310, 264), (x + 296, 278)], fill=TEAL)

    notes = [
        (36, RED_SOFT, RED, "เช็คงบไม่ผ่าน", "ส่งอนุมัติไม่ได้ ต้องลดยอดหรือเลือกงบให้ถูก"),
        (548, AMBER_SOFT, AMBER, "ส่ง PR แล้ว", "เงินถูกกันไว้ ใบอื่นใช้วงเงินซ้ำไม่ได้"),
        (1060, GREEN_SOFT, GREEN, "มีบิลแล้ว", "เงินกลายเป็นใช้จริง คงเหลือลดลงถาวร"),
    ]
    for x, bg, fg, title, body in notes:
        round_rect(d, (x, 470, x + 504, 600), 14, bg, fg, 2)
        d.text((x + 24, 490), title, font=font(18, "bold"), fill=fg)
        d.text((x + 24, 534), body, font=font(16), fill=SLATE)
    save(img, "fig_spend_flow.png")


def fig_pr_check():
    img, d = new_canvas(1600, 860, (236, 240, 244))
    d.rectangle((0, 0, 1600, 56), fill=NAVY)
    d.text((24, 14), "ใบขอซื้อ  /  PR6908001", font=font(18, "medium"), fill=WHITE)
    round_rect(d, (20, 72, 1580, 140), 8, WHITE)
    round_rect(d, (40, 88, 220, 124), 8, TEAL)
    center_text(d, 40, 88, 180, "เช็คงบประมาณ", font(16, "semibold"), WHITE, 36)
    statuses = ["ร่าง", "ส่งแล้ว", "อนุมัติ"]
    sx = 1180
    for i, st in enumerate(statuses):
        col = TEAL if i == 0 else LINE
        fg = WHITE if i == 0 else MUTED
        round_rect(d, (sx, 92, sx + 120, 122), 12, col)
        center_text(d, sx, 92, 120, st, font(13, "medium"), fg, 30)
        sx += 128

    round_rect(d, (20, 156, 1580, 840), 8, WHITE)
    d.text((48, 176), "PR6908001", font=font(28, "bold"), fill=NAVY)
    d.text((48, 220), "แท็บ ตรวจสอบงบประมาณ", font=font(18, "semibold"), fill=TEAL)

    left = [
        ("ประเภทสิ่งที่จะซื้อ", "วัสดุ"),
        ("หน่วยงานงบประมาณ", "หน่วยงานทดสอบ"),
        ("แหล่งเงิน", "เงินบำรุง"),
        ("กลุ่มงบประมาณ", "วัสดุการแพทย์"),
        ("หมวดงบประมาณ", "หมวดค่าวัสดุ - วัสดุการแพทย์ - การแพทย์ผ่าตัด"),
    ]
    for i, (lab, val) in enumerate(left):
        y = 270 + i * 70
        d.text((48, y), lab, font=font(13), fill=MUTED)
        round_rect(d, (48, y + 22, 760, y + 60), 6, BG, LINE, 1)
        d.text((60, y + 30), val, font=font(16, "medium"), fill=SLATE)

    right = [
        ("งบประมาณที่จอง", "3,000.00"),
        ("งบคงเหลือหลังหัก PR นี้", "5,000.00"),
        ("สถานะเช็คงบ", "งบเพียงพอ"),
        ("จองงบประมาณแล้ว", "ยังไม่จอง (ร่าง)"),
    ]
    for i, (lab, val) in enumerate(right):
        y = 270 + i * 70
        d.text((820, y), lab, font=font(13), fill=MUTED)
        bg = GREEN_SOFT if "เพียงพอ" in val else BG
        round_rect(d, (820, y + 22, 1532, y + 60), 6, bg, LINE, 1)
        d.text((834, y + 30), val, font=font(16, "medium"), fill=GREEN if "เพียงพอ" in val else SLATE)

    round_rect(d, (48, 640, 1532, 800), 12, SOFT, TEAL, 2)
    d.text((72, 664), "ผลการเช็คงบ", font=font(18, "bold"), fill=TEAL)
    d.text((72, 708), "งบเพียงพอ   วงเงินจัดสรร 8,000   ใช้ได้ 8,000   คงเหลือหลังใบนี้ 5,000", font=font(20, "medium"), fill=SLATE)
    d.text((72, 748), "ตอนนี้อยู่สถานะร่าง ระบบยังไม่กันเงิน  เมื่อกดส่งอนุมัติ จึงจะจองงบ 3,000 บาท", font=font(18), fill=MUTED)
    save(img, "fig_pr_check.png")


def fig_formula():
    img, d = new_canvas(1600, 620)
    d.text((48, 24), "สูตรที่ต้องจำ  สูตรเดียวทั้งระบบ", font=font(28, "bold"), fill=NAVY)
    round_rect(d, (48, 90, 1552, 190), 16, NAVY)
    center_text(d, 48, 90, 1504, "คงเหลือ  =  งบจัดสรร  −  ใช้จริง  −  จอง PR  −  ผูกพัน PO", font(28, "bold"), WHITE, 100)

    nums = [
        ("8,000", "งบจัดสรร", "ที่อนุมัติในแผน", NAVY),
        ("0", "ใช้จริง", "บิลที่โพสต์แล้ว", GREEN),
        ("3,000", "จอง PR", "ส่งแล้วยังไม่มี PO", AMBER),
        ("0", "ผูกพัน PO", "PO ยังไม่ครบบิล", AMBER),
        ("5,000", "คงเหลือ", "ซื้อเพิ่มได้เท่านั้น", TEAL),
    ]
    for i, (val, label, hint, col) in enumerate(nums):
        x = 48 + i * 310
        round_rect(d, (x, 230, x + 290, 430), 16, WHITE, col, 3)
        center_text(d, x, 250, 290, val, font(32, "bold"), col)
        center_text(d, x, 310, 290, label, font(20, "semibold"), NAVY)
        center_text(d, x, 360, 290, hint, font(15), MUTED)

    round_rect(d, (48, 460, 1552, 580), 16, SOFT, TEAL, 2)
    d.text((72, 484), "ตัวอย่างจากชุดอบรม  จัดสรรวัสดุ 8,000 บาท แล้วส่ง PR 3,000 บาท", font=font(18, "semibold"), fill=TEAL)
    d.text((72, 528), "หลังส่ง PR: คงเหลือ 5,000   ·   หลังยืนยัน PO: จองเป็น 0 ผูกพัน 3,000 คงเหลือยัง 5,000   ·   หลังโพสต์บิล: ใช้จริง 3,000 คงเหลือ 5,000", font=font(16), fill=SLATE)
    save(img, "fig_formula.png")


def fig_match_keys():
    img, d = new_canvas(1600, 620)
    d.text((48, 24), "ถ้าเช็คงบไม่ผ่าน  ดูให้ครบ 4 อย่างนี้ก่อน", font=font(28, "bold"), fill=NAVY)
    keys = [
        ("1", "หน่วยงาน / ศูนย์ต้นทุน", "แผนกที่ขอต้องตรงกับงบในแผน\nเช่น หน่วยงานทดสอบ"),
        ("2", "แหล่งเงิน", "เงินบำรุง / งบประมาณ / เงินบริจาค\nห้ามใช้เงินคนละแหล่ง"),
        ("3", "หมวดงบประมาณ", "วัสดุ ครุภัณฑ์ ก่อสร้าง โครงการ\nต้องตรงบรรทัดที่อนุมัติ"),
        ("4", "กลุ่มวัสดุ", "ใช้เฉพาะตอนซื้อวัสดุ\nเช่น ยา เวชภัณฑ์ วัสดุทั่วไป"),
    ]
    for i, (num, title, body) in enumerate(keys):
        r, c = divmod(i, 2)
        x = 48 + c * 776
        y = 100 + r * 240
        round_rect(d, (x, y, x + 740, y + 216), 18, WHITE, TEAL, 3)
        round_rect(d, (x + 28, y + 36, x + 88, y + 96), 12, TEAL)
        center_text(d, x + 28, y + 36, 60, num, font(26, "bold"), WHITE, 60)
        d.text((x + 112, y + 44), title, font=font(24, "bold"), fill=NAVY)
        wrap_center(d, x + 40, y + 120, 660, body, font(18), MUTED, 8)
    save(img, "fig_match_keys.png")


def fig_dashboard():
    img, d = new_canvas(1600, 820, (236, 240, 244))
    d.rectangle((0, 0, 1600, 56), fill=NAVY)
    d.text((24, 14), "งบประมาณ  /  Dashboard งบประมาณ  /  ภาพรวมงบประมาณรายจ่ายประจำปี", font=font(18, "medium"), fill=WHITE)
    round_rect(d, (20, 76, 1580, 800), 10, WHITE)
    d.text((48, 100), "ภาพรวมงบประมาณรายจ่ายประจำปี", font=font(26, "bold"), fill=NAVY)
    d.text((48, 144), "ประจำปีงบประมาณ พ.ศ. 2569", font=font(16), fill=MUTED)
    round_rect(d, (1280, 108, 1520, 148), 8, GREEN)
    center_text(d, 1280, 108, 240, "เบิกจ่ายงบประมาณ", font(14, "semibold"), WHITE, 40)

    cards = [
        ("งบจัดสรร", "258,000", TEAL),
        ("ใช้จริง", "0", AMBER),
        ("จอง PR + ผูกพัน PO", "3,000", NAVY),
        ("คงเหลือ", "255,000", GREEN),
    ]
    for i, (lab, val, col) in enumerate(cards):
        x = 48 + i * 380
        round_rect(d, (x, 190, x + 360, 310), 14, WHITE, col, 2)
        d.text((x + 24, 210), lab, font=font(14), fill=MUTED)
        d.text((x + 24, 244), f"฿ {val}", font=font(28, "bold"), fill=col)

    d.text((48, 340), "KPI ตามสัดส่วนแบบฟอร์มคำของบ", font=font(20, "semibold"), fill=NAVY)
    d.text((48, 376), "สัดส่วนงบประมาณที่ขอ/ได้รับ แยกตามแบบฟอร์ม", font=font(14), fill=MUTED)
    kpis = [
        ("วัสดุ", "8,000", TEAL, 0.22),
        ("ครุภัณฑ์", "40,000", NAVY, 0.35),
        ("ก่อสร้าง", "150,000", AMBER, 0.85),
        ("โครงการ", "60,000", GREEN, 0.48),
    ]
    for i, (lab, amt, col, pct) in enumerate(kpis):
        x = 48 + i * 380
        round_rect(d, (x, 420, x + 360, 600), 14, BG)
        d.text((x + 20, 440), lab, font=font(16, "semibold"), fill=NAVY)
        d.text((x + 20, 476), f"฿ {amt}", font=font(22, "bold"), fill=col)
        round_rect(d, (x + 20, 540, x + 340, 556), 6, LINE)
        round_rect(d, (x + 20, 540, x + 20 + int(320 * pct), 556), 6, col)

    menus = [
        "สถานะคำของบประมาณ",
        "ภาพรวมงบประมาณรายจ่ายประจำปี",
        "บริการงบประมาณรายแผนก",
        "รายการงบประมาณ",
    ]
    d.text((48, 630), "เมนู Dashboard ที่ผู้ใช้ต้องรู้จัก", font=font(18, "semibold"), fill=NAVY)
    for i, m in enumerate(menus):
        x = 48 + (i % 2) * 760
        y = 676 + (i // 2) * 52
        round_rect(d, (x, y, x + 720, y + 44), 8, SOFT)
        d.text((x + 16, y + 10), f"{i + 1}.  {m}", font=font(16), fill=SLATE)
    save(img, "fig_dashboard.png")


def fig_menus():
    img, d = new_canvas(1600, 720)
    d.text((48, 24), "แผนที่เมนูแอป งบประมาณ", font=font(28, "bold"), fill=NAVY)
    d.text((48, 72), "เข้าจากไอคอน งบประมาณ ที่แถบแอปด้านซ้ายหรือด้านบน", font=font(18), fill=MUTED)

    round_rect(d, (48, 120, 360, 680), 16, NAVY)
    d.text((72, 148), "งบประมาณ", font=font(22, "bold"), fill=WHITE)
    roots = [
        "Dashboard งบประมาณ",
        "บันทึกคำของบ",
        "รวบรวมคำของบ",
        "รายการงบประมาณ",
        "การกำหนดค่า",
    ]
    for i, name in enumerate(roots):
        y = 210 + i * 84
        round_rect(d, (72, y, 336, y + 64), 10, (28, 78, 110))
        d.text((92, y + 18), name, font=font(16, "medium"), fill=WHITE)

    groups = [
        (400, "Dashboard", TEAL, [
            "ภาพรวมงบประมาณรายจ่ายประจำปี",
            "บริการงบประมาณรายแผนก",
            "สถานะคำของบประมาณ",
        ]),
        (400 + 390, "หน่วยงานใช้บ่อย", AMBER, [
            "บันทึกคำของบ → ทั้งหมด",
            "แบบฟอร์มตั้งงบวัสดุ",
            "แบบฟอร์มครุภัณฑ์ / ก่อสร้าง / โครงการ",
        ]),
        (400 + 780, "งานงบใช้บ่อย", GREEN, [
            "รวบรวมคำของบ (หน่วยงบประมาณ)",
            "งบประมาณประจำปี",
            "แหล่งเงิน / หมวดงบ / กลุ่มวัสดุ",
        ]),
    ]
    for x, title, col, items in groups:
        round_rect(d, (x, 120, x + 370, 680), 16, WHITE, col, 3)
        round_rect(d, (x, 120, x + 370, 190), 16, col)
        d.rectangle((x, 170, x + 370, 190), fill=col)
        center_text(d, x, 132, 370, title, font(20, "bold"), WHITE)
        for i, item in enumerate(items):
            y = 220 + i * 120
            round_rect(d, (x + 20, y, x + 350, y + 100), 12, BG)
            d.text((x + 40, y + 32), item, font=font(16), fill=SLATE)
    save(img, "fig_menus.png")


def fig_do_dont():
    img, d = new_canvas(1600, 640)
    d.text((48, 24), "ทำ / อย่าทำ  ตอนอบรมและใช้งานจริง", font=font(28, "bold"), fill=NAVY)
    dos = [
        "เลือกแบบฟอร์มให้ถูกก่อนกรอกรายการ",
        "ใส่เหตุผลประกอบคำขอทุกใบ",
        "งบวัสดุต้องมีรายละเอียดสินค้า",
        "เช็คงบบน PR ก่อนส่งอนุมัติ",
        "ดูคงเหลือจากสูตร จัดสรร − ใช้จริง − จอง − ผูกพัน",
    ]
    donts = [
        "อย่าซื้อของก่อนคำของบได้รับอนุมัติ",
        "อย่าเข้าใจว่ายอดที่ขอคือวงเงินใช้ได้",
        "อย่าเลือกหน่วยงานหรือแหล่งเงินคนละชุดกับแผน",
        "อย่าข้ามปุ่มเช็คงบแล้วส่ง PR เลย",
        "อย่าใช้บัญชี admin กดแทนทุกบทบาทตอนอบรม",
    ]
    round_rect(d, (48, 100, 776, 600), 18, GREEN_SOFT, GREEN, 3)
    d.text((80, 128), "ให้ทำ", font=font(26, "bold"), fill=GREEN)
    for i, t in enumerate(dos):
        y = 190 + i * 74
        round_rect(d, (80, y, 128, y + 44), 10, GREEN)
        center_text(d, 80, y, 48, str(i + 1), font(18, "bold"), WHITE, 44)
        d.text((148, y + 8), t, font=font(18), fill=SLATE)

    round_rect(d, (824, 100, 1552, 600), 18, RED_SOFT, RED, 3)
    d.text((856, 128), "อย่าทำ", font=font(26, "bold"), fill=RED)
    for i, t in enumerate(donts):
        y = 190 + i * 74
        round_rect(d, (856, y, 904, y + 44), 10, RED)
        center_text(d, 856, y, 48, str(i + 1), font(18, "bold"), WHITE, 44)
        d.text((924, y + 8), t, font=font(18), fill=SLATE)
    save(img, "fig_do_dont.png")


def fig_login():
    img, d = new_canvas(1600, 560)
    d.text((48, 24), "เข้าสู่ระบบก่อนเริ่มอบรม", font=font(28, "bold"), fill=NAVY)
    steps = [
        ("1", "เปิดเบราว์เซอร์", "ไปที่ระบบ Odoo ของโรงพยาบาล"),
        ("2", "ใส่บัญชีตามบทบาท", "หน่วยงาน / งานงบ / พัสดุ คนละบัญชี"),
        ("3", "เข้าแอป งบประมาณ", "เลือกไอคอน งบประมาณ จากแถบแอป"),
        ("4", "ตรวจเมนูตามสิทธิ์", "หน่วยงานไม่เห็นเมนูกำหนดค่า"),
    ]
    for i, (num, title, body) in enumerate(steps):
        x = 48 + i * 388
        round_rect(d, (x, 110, x + 368, 360), 18, WHITE, TEAL, 2)
        round_rect(d, (x + 24, 134, x + 88, 198), 12, TEAL)
        center_text(d, x + 24, 134, 64, num, font(24, "bold"), WHITE, 64)
        wrap_center(d, x + 16, 220, 336, title, font(22, "bold"), NAVY)
        wrap_center(d, x + 16, 280, 336, body, font(16), MUTED, 6)

    round_rect(d, (48, 400, 1552, 520), 16, NAVY)
    d.text((80, 424), "บัญชีฝึกอบรม (รหัสผ่านชุดเดียวกัน)", font=font(18, "semibold"), fill=(159, 201, 196))
    d.text((80, 464), "uat.dept   หน่วยงาน     ·     uat.budget   งานงบประมาณ     ·     uat.procurement   พัสดุ     ·     รหัสผ่าน  VpkUat@2569", font=font(20, "medium"), fill=WHITE)
    save(img, "fig_login.png")


def main():
    fig_cover()
    fig_login()
    fig_two_phases()
    fig_cycle()
    fig_roles()
    fig_forms()
    fig_menus()
    fig_request_flow()
    fig_request_form()
    fig_spend_flow()
    fig_pr_check()
    fig_formula()
    fig_match_keys()
    fig_dashboard()
    fig_do_dont()


if __name__ == "__main__":
    main()
