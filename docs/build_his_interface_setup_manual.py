#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""คู่มือตั้งค่าเชื่อมต่อ HIS Interface — ชุดคู่มือการใช้งานตามผังภาพรวม

อ้างอิงผังภาพรวม:
  9. งานลูกหนี้ (HIS Interface) — 9.1 รับรายได้/มัดจำ · 9.2 ตั้งลูกหนี้ตามสิทธิ์
  5.10 รับส่งข้อมูลกับระบบ HIS (คลัง — ตัดจ่าย / เบิกเติม)
  Data Master 6.3 ลูกหนี้สิทธิ HIS · 7.4 การผูกคู่บัญชี Interface (HIS/HR/คลัง)

รัน: python3 docs/build_his_interface_setup_manual.py
ผลลัพธ์: docs/คู่มือการใช้งาน-ตามผังภาพรวม/10-คู่มือการใช้งาน-การตั้งค่าเชื่อมต่อ-HIS-Interface-ver.N.docx
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_new_manual_g02_procurement import (  # noqa: E402
    LOGO,
    META_FILL,
    MUTED,
    OUT_DIR,
    PRIMARY,
    SLATE,
    TEAL,
    add_text,
    bind_toc_bookmarks,
    body,
    bullets,
    callout,
    cell_text,
    estimate_bookmark_pages,
    fill_toc_page_column,
    heading,
    header_footer,
    make_table,
    make_toc_table,
    page_title,
    picture,
    reset_figure_counter,
    set_narrow_cell_margin,
    setup_styles,
    step_with_pic,
    task_summary_card,
)
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

LATEST_DIR = OUT_DIR / "ล่าสุด"
STEM = "10-คู่มือการใช้งาน-การตั้งค่าเชื่อมต่อ-HIS-Interface"

_THAI_MONTHS = (
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
)


def next_manual_rev(stem: str) -> tuple[int, Path]:
    rev_re = re.compile(rf"^{re.escape(stem)}-ver\.(\d+)\.docx$")
    existing = []
    for path in OUT_DIR.glob(f"{stem}-ver.*.docx"):
        if path.name.startswith("~$"):
            continue
        m = rev_re.match(path.name)
        if m:
            existing.append(int(m.group(1)))
    rev = (max(existing) + 1) if existing else 1
    out = OUT_DIR / f"{stem}-ver.{rev}.docx"
    if out.exists():
        raise FileExistsError(f"ไม่ทับไฟล์ที่มีแล้ว: {out}")
    return rev, out


def thai_date(d: date | None = None) -> str:
    d = d or date.today()
    return f"{d.day} {_THAI_MONTHS[d.month]} พ.ศ. {d.year + 543}"


def new_doc(header_label: str, ver_label: str) -> Document:
    reset_figure_counter(0)
    doc = Document()
    setup_styles(doc)
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    header_footer(doc)
    hp = doc.sections[0].header.paragraphs[0]
    hp.clear()
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_text(hp, f"{header_label} · ระบบ ERP รพ.วชิระภูเก็ต | {ver_label}", 8.5, False, MUTED)
    return doc


def cover(doc, title: str, flow: str, cover_info: list[tuple[str, str]]):
    if LOGO.exists():
        logo_p = doc.add_paragraph()
        logo_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo_p.paragraph_format.space_before = Pt(12)
        logo_p.paragraph_format.space_after = Pt(8)
        logo_p.add_run().add_picture(str(LOGO), width=Cm(3.4))
    for txt, size, bold, color, after in [
        ("โรงพยาบาลวชิระภูเก็ต", 16, True, SLATE, 0),
        ("VACHIRAPHUKET HOSPITAL", 11, True, MUTED, 18),
        ("เอกสารคู่มือการใช้งาน (User Manual)", 13, False, MUTED, 6),
        (title, 24, True, TEAL, 4),
        (flow, 12, True, SLATE, 10),
        ("ระบบบริหารทรัพยากรองค์กร (ERP)", 13, False, MUTED, 22),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(after)
        add_text(p, txt, size, bold, color)
    cover_table = doc.add_table(rows=len(cover_info), cols=2)
    cover_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (k, v) in enumerate(cover_info):
        cell_text(cover_table.rows[i].cells[0], k, 11, True, TEAL, "left", META_FILL)
        cell_text(cover_table.rows[i].cells[1], v, 11, False, SLATE, "left", "FFFFFF")
        cover_table.rows[i].cells[0].width = Cm(4.8)
        cover_table.rows[i].cells[1].width = Cm(11.4)
        set_narrow_cell_margin(cover_table.rows[i].cells[0])
        set_narrow_cell_margin(cover_table.rows[i].cells[1])
    doc.add_page_break()


def toc(doc, intro_callout: tuple[str, str], toc_rows: list[tuple[str, str]]):
    page_title(doc, "สารบัญ")
    callout(doc, intro_callout[0], intro_callout[1], "info")
    toc_entries = [(c, t, f"toc_{i:03d}") for i, (c, t) in enumerate(toc_rows, 1)]
    make_toc_table(
        doc,
        toc_entries,
        [3.2, 11.8, 1.6],
        bold_row=lambda row: str(row[0]).startswith("บทที่"),
    )
    doc.add_page_break()
    return toc_entries


def finish(doc, out: Path, toc_entries, ver_label: str, end_label: str):
    end = doc.add_paragraph()
    end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    end.paragraph_format.space_before = Pt(16)
    add_text(end, f"— จบ{end_label} {ver_label} —", 12, True, PRIMARY)
    bound = bind_toc_bookmarks(doc, toc_entries)
    page_map = estimate_bookmark_pages(doc)
    filled = fill_toc_page_column(doc, page_map)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    latest = LATEST_DIR / out.name
    shutil.copy2(out, latest)
    print(out)
    print(f"copied → {latest}")
    print(f"TOC bookmarks bound: {bound}/{len(toc_entries)}; pages filled: {filled}")
    return out


def build():
    rev, out = next_manual_rev(STEM)
    ver_label = f"ver.{rev}"
    doc = new_doc("ตั้งค่าเชื่อมต่อ HIS", ver_label)

    cover(
        doc,
        "การตั้งค่าเชื่อมต่อระบบ HIS",
        "เปิดรับข้อมูล  →  ให้สิทธิ์คนใช้งาน  →  จับคู่ข้อมูล  →  ทดสอบ  →  เริ่มใช้งานจริง",
        [
            ("รหัสเอกสาร", "UM-ERP-HIS-CFG-001"),
            ("เรื่อง", "เตรียมระบบ ERP ให้รับข้อมูลจาก HIS ได้ (รายได้ มัดจำ ตัดจ่ายยา เบิกเติมคลัง)"),
            ("เวอร์ชันเอกสาร", f"{rev}.0"),
            ("วันที่จัดทำ", thai_date()),
            ("อยู่ในผังภาพรวมข้อ", "ข้อ 9 งานลูกหนี้ (HIS) · ข้อ 5.10 คลังกับ HIS · ข้อมูลหลัก 6.3 และ 7.4"),
            ("ใครควรอ่าน", "ผู้ดูแลระบบ · นักบัญชีลูกหนี้ · เภสัชกร · เจ้าหน้าที่ IT"),
        ],
    )

    toc_entries = toc(
        doc,
        (
            "คู่มือเล่มนี้ใช้ทำอะไร",
            "ใช้ตั้งค่าระบบครั้งแรกก่อนเริ่มรับข้อมูลจาก HIS ทำครั้งเดียว (หรือเมื่อมีการเปลี่ยนแปลง) "
            "ส่วนงานประจำวัน เช่น การกดยืนยันรายการ ให้ดูคู่มือของงานบัญชีและงานคลัง",
        ),
        [
            ("บทที่ 1", "เรื่องนี้คืออะไร และต้องทำอะไรบ้าง"),
            ("บทที่ 2", "เปิดช่องทางรับข้อมูลจาก HIS"),
            ("บทที่ 3", "ให้สิทธิ์คนที่จะใช้งาน"),
            ("บทที่ 4", "จับคู่สิทธิการรักษา (บัตรทอง ประกันสังคม ฯลฯ)"),
            ("บทที่ 5", "จับคู่วิธีรับเงิน (เงินสด โอน บัตร ฯลฯ)"),
            ("บทที่ 6", "เตรียมสมุดบัญชีที่ต้องใช้"),
            ("บทที่ 7", "เตรียมคลังยาสำหรับตัดจ่ายและเบิกเติม"),
            ("บทที่ 8", "ตรวจรหัสยาและเลขล็อตให้ตรงกับ HIS"),
            ("บทที่ 9", "ทดสอบก่อนใช้งานจริง"),
            ("บทที่ 10", "เจอปัญหา แก้อย่างไร"),
        ],
    )

    # ----- 1 -----
    heading(doc, "บทที่ 1 เรื่องนี้คืออะไร และต้องทำอะไรบ้าง", 1)
    body(
        doc,
        "HIS คือระบบของโรงพยาบาลที่ใช้ดูแลคนไข้ เช่น ลงทะเบียน เก็บเงิน และจ่ายยา "
        "ทุกวัน HIS จะส่งข้อมูลสรุปมาที่ระบบ ERP เพื่อให้ฝ่ายบัญชีและคลังไม่ต้องคีย์ซ้ำ",
    )
    make_table(
        doc,
        ["HIS ส่งอะไรมา", "ไปอยู่ที่ไหนใน ERP", "ใครดูแล"],
        [
            ["ยอดรายได้และเงินที่รับในแต่ละวัน", "HIS Revenue Queue", "นักบัญชี"],
            ["เงินมัดจำค่ารักษา (รับ/คืน)", "HIS รับมัดจำค่ารักษา", "นักบัญชี"],
            ["ยาที่จ่ายให้คนไข้", "HIS ตัดจ่ายสินค้า", "เภสัชกร"],
            ["คำขอเบิกยาจากคลังใหญ่ไปเติมห้องยา", "HIS เบิกเติมคลัง", "เภสัชกร / คลัง"],
        ],
        [6.0, 5.5, 4.7],
    )
    callout(
        doc,
        "จำไว้ข้อเดียว",
        "ข้อมูลจาก HIS จะมา \"รอ\" ในคิวก่อนเสมอ ระบบยังไม่ลงบัญชีหรือตัดสต็อกเอง "
        "ต้องมีคนตรวจแล้วกดปุ่ม Post (ยืนยัน) ก่อน",
        "info",
    )
    body(doc, "ก่อนเริ่มรับข้อมูลจริง ต้องเตรียมระบบ 6 เรื่องตามลำดับนี้")
    make_table(
        doc,
        ["ลำดับ", "ต้องทำอะไร", "ใครทำ", "อยู่บทที่"],
        [
            ["1", "เปิดช่องทางรับข้อมูล และตั้งรหัสผ่านให้ HIS", "IT", "2"],
            ["2", "ให้สิทธิ์คนที่จะใช้งาน", "ผู้ดูแลระบบ", "3"],
            ["3", "จับคู่สิทธิการรักษา วิธีรับเงิน และสมุดบัญชี", "นักบัญชี", "4–6"],
            ["4", "เตรียมคลังยา", "เภสัชกร / คลัง", "7"],
            ["5", "ตรวจรหัสยาและเลขล็อต", "เภสัชกร / คลัง", "8"],
            ["6", "ทดสอบส่งข้อมูลจริงจำนวนน้อย ๆ", "ทุกฝ่าย", "9"],
        ],
        [1.8, 7.6, 3.6, 3.2],
    )

    # ----- 2 -----
    heading(doc, "บทที่ 2 เปิดช่องทางรับข้อมูลจาก HIS", 1)
    body(
        doc,
        "ERP มี \"ประตู\" สำหรับให้ HIS ส่งข้อมูลเข้ามา (เรียกว่า API) "
        "ต้องเปิดประตูนี้ และตั้ง \"กุญแจ\" (เรียกว่า API Key) ให้ HIS ใช้ คนที่ไม่มีกุญแจจะส่งข้อมูลเข้ามาไม่ได้",
    )
    step_with_pic(
        doc,
        1,
        "เข้าสู่ระบบด้วยบัญชีผู้ดูแลระบบ แล้วไปที่ การตั้งค่า → บัญชี",
        "his_setup/01_home_account.png",
        cap="ภาพที่ 1 หน้าแรกหลังเข้าสู่ระบบ",
    )
    step_with_pic(
        doc,
        2,
        "เลื่อนหาหัวข้อ HIS Interface API แล้วติ๊กช่อง Enable HIS API (เปิดใช้งาน)",
    )
    step_with_pic(
        doc,
        3,
        "ใส่รหัสในช่อง API Key แล้วกดบันทึก",
        sub_bullets=[
            "ตั้งรหัสใหม่เอง อย่าใช้ค่าเดิมที่ติดมากับระบบ (CHANGE-ME-HIS-API-KEY)",
            "ส่งรหัสนี้ให้ทีม HIS ทางช่องทางที่ปลอดภัยเท่านั้น",
        ],
    )
    callout(
        doc,
        "ข้อควรระวัง",
        "API Key เหมือนรหัสผ่าน ห้ามแชร์ในกลุ่มแชตหรืออีเมลทั่วไป "
        "ถ้าสงสัยว่ารั่ว ให้เปลี่ยนรหัสใหม่แล้วแจ้งทีม HIS",
        "warn",
    )
    callout(
        doc,
        "สำหรับทีม IT",
        "HIS ส่งรหัสใน Header แบบ X-Api-Key หรือ Authorization: Bearer · "
        "ช่องทางที่ใช้: /vpk/api/v1/his/revenue, /deposits, /stock-issues, /stock-requisitions · "
        "ตรวจว่าระบบเปิดอยู่ได้ที่ /vpk/api/v1/his/health · "
        "ดูประวัติการส่งได้ที่ บัญชี → การกำหนดค่า → HIS Interface → API Logs",
        "info",
    )

    # ----- 3 -----
    heading(doc, "บทที่ 3 ให้สิทธิ์คนที่จะใช้งาน", 1)
    body(
        doc,
        "คนที่ยังไม่ได้สิทธิ์จะมองไม่เห็นเมนู HIS เลย แม้จะเป็นนักบัญชีหรือเภสัชกรก็ตาม "
        "ผู้ดูแลระบบต้องเพิ่มสิทธิ์ให้ก่อน",
    )
    make_table(
        doc,
        ["ระดับสิทธิ์", "ทำอะไรได้", "เหมาะกับใคร"],
        [
            ["User", "ดูคิวได้อย่างเดียว", "เจ้าหน้าที่ทั่วไปที่ต้องดูข้อมูล"],
            ["Accountant", "ยืนยันรายได้และมัดจำ · ตั้งค่าจับคู่สิทธิและวิธีรับเงิน", "นักบัญชีลูกหนี้"],
            ["Pharmacist", "ยืนยันตัดจ่ายยาและเบิกเติม · ตั้งค่าหน่วยบริการ", "เภสัชกร"],
            ["Manager", "ทำได้ทุกอย่าง รวมถึงตั้งรหัส API และดูประวัติ", "หัวหน้างาน / IT"],
        ],
        [3.2, 7.8, 5.2],
    )
    step_with_pic(
        doc,
        1,
        "ไปที่ การตั้งค่า → ผู้ใช้ → เลือกชื่อคนที่ต้องการ",
    )
    step_with_pic(
        doc,
        2,
        "ในหัวข้อ HIS Interface เลือกระดับสิทธิ์ตามตารางด้านบน แล้วกดบันทึก",
    )
    step_with_pic(
        doc,
        3,
        "ให้ผู้ใช้คนนั้นออกจากระบบแล้วเข้าใหม่ จึงจะเห็นเมนู HIS",
    )

    # ----- 4 -----
    heading(doc, "บทที่ 4 จับคู่สิทธิการรักษา (บัตรทอง ประกันสังคม ฯลฯ)", 1)
    body(
        doc,
        "HIS จะบอกว่าคนไข้ใช้สิทธิอะไร ERP ต้องรู้ว่าสิทธินั้นเป็นเงินของใคร "
        "และต้องลงบัญชีไหน จึงต้องทำ \"ตารางจับคู่\" ไว้ล่วงหน้า",
    )
    picture(
        doc,
        "his_setup/02_accounting.png",
        15.8,
        "ภาพที่ 2 หน้าระบบบัญชี เมนู HIS อยู่ใต้ระบบลูกหนี้ (เห็นเมื่อได้สิทธิ์แล้ว)",
    )
    step_with_pic(
        doc,
        1,
        "ไปที่ บัญชี → ลูกหนี้ → HIS Entitlements",
    )
    step_with_pic(
        doc,
        2,
        "ตรวจว่ามีครบทุกสิทธิ์ที่ HIS ใช้ ทั้งผู้ป่วยนอก (OP) และผู้ป่วยใน (IP)",
    )
    make_table(
        doc,
        ["รหัสที่ HIS ส่งมา", "หมายถึง", "เงินจะเข้าอย่างไร"],
        [
            ["SELF_PAY", "คนไข้จ่ายเอง", "รับเงินทันทีที่เคาน์เตอร์"],
            ["UC", "บัตรทอง", "ตั้งเป็นลูกหนี้ รอกองทุนโอนเงินมา"],
            ["SSO", "ประกันสังคม", "ตั้งเป็นลูกหนี้ รอกองทุนโอนเงินมา"],
            ["CSMBS", "เบิกจ่ายตรง กรมบัญชีกลาง", "ตั้งเป็นลูกหนี้ รอกองทุนโอนเงินมา"],
        ],
        [3.8, 5.5, 6.9],
    )
    step_with_pic(
        doc,
        3,
        "เปิดแต่ละรายการ ตรวจว่าเลือกผู้จ่ายเงิน บัญชีรายได้ และบัญชีลูกหนี้ถูกต้อง "
        "ถ้าใส่รหัสบัญชีไว้แล้ว กดปุ่ม Bind CoA Accounts ให้ระบบเลือกบัญชีให้อัตโนมัติ",
    )
    callout(
        doc,
        "ถ้าลืมตั้งจะเกิดอะไร",
        "ถ้า HIS ส่งสิทธิที่ไม่มีในตารางนี้ ข้อมูลวันนั้นจะขึ้นสถานะ Error และใช้ไม่ได้ "
        "แก้โดยเพิ่มสิทธิในตาราง แล้วให้ HIS ส่งข้อมูลวันนั้นมาใหม่",
        "warn",
    )

    # ----- 5 -----
    heading(doc, "บทที่ 5 จับคู่วิธีรับเงิน (เงินสด โอน บัตร ฯลฯ)", 1)
    body(
        doc,
        "นอกจากสิทธิ HIS ยังบอกด้วยว่ารับเงินด้วยวิธีไหน ERP ต้องรู้ว่าวิธีนั้นเป็น \"เงินจริง\" "
        "ที่เข้าโรงพยาบาลวันนี้ หรือเป็นแค่ \"ยอดค้างรับ\"",
    )
    step_with_pic(doc, 1, "ไปที่ บัญชี → ลูกหนี้ → HIS Payment Methods")
    make_table(
        doc,
        ["วิธีรับเงิน", "เป็นเงินจริงไหม", "ต้องตั้งอะไร"],
        [
            ["เงินสด", "ใช่", "เลือกสมุดเงินสด"],
            ["โอนเงิน / บัตรเครดิต", "ใช่", "เลือกสมุดธนาคาร"],
            ["รับมัดจำ", "ใช่ แต่ยังไม่ใช่รายได้", "ใช้บัญชีเงินรับล่วงหน้า"],
            ["ใช้เงินมัดจำที่จ่ายไว้แล้ว", "ไม่ใช่เงินใหม่", "เลือกสมุดตัดมัดจำ"],
            ["สิทธิ บัตรทอง / ประกันสังคม / เบิกจ่ายตรง", "ไม่ใช่ (ค้างรับ)", "ไม่ต้องเลือกสมุด"],
        ],
        [6.2, 4.0, 6.0],
    )
    step_with_pic(
        doc,
        2,
        "เปิดรายการที่เป็นเงินจริงทีละรายการ แล้วเลือกสมุดบัญชีให้ถูก จากนั้นกดบันทึก",
    )

    # ----- 6 -----
    heading(doc, "บทที่ 6 เตรียมสมุดบัญชีที่ต้องใช้", 1)
    body(
        doc,
        "เวลายืนยันรายได้ ระบบจะสร้างใบแจ้งหนี้และใบรับเงินลงในสมุดบัญชี "
        "ต้องมีสมุดเหล่านี้ก่อน ถ้ายังไม่มีให้สร้างที่ บัญชี → การกำหนดค่า → สมุดรายวัน",
    )
    make_table(
        doc,
        ["รหัสสมุด", "ใช้ทำอะไร"],
        [
            ["HINV", "เก็บใบแจ้งหนี้รายได้จาก HIS"],
            ["HCSH", "เก็บเงินสดที่รับจากเคาน์เตอร์"],
            ["HADV", "เก็บรายการที่คนไข้ใช้เงินมัดจำจ่าย"],
            ["สมุดธนาคาร", "เก็บเงินโอนและบัตรเครดิต"],
        ],
        [4.0, 12.2],
    )
    callout(
        doc,
        "บัญชีที่ต้องมีในผังบัญชี",
        "บัญชีเงินรับล่วงหน้า (มัดจำ) 2103010103.101 · บัญชีเงินสด 1101010101.101 · "
        "บัญชีรายได้และลูกหนี้ของแต่ละสิทธิ ตามที่ตั้งในบทที่ 4",
        "info",
    )

    # ----- 7 -----
    heading(doc, "บทที่ 7 เตรียมคลังยาสำหรับตัดจ่ายและเบิกเติม", 1)
    body(
        doc,
        "เมื่อห้องยาจ่ายยาให้คนไข้ HIS จะแจ้งให้ ERP ตัดยาออกจากคลัง "
        "และเมื่อห้องยาของหมด HIS จะขอเบิกยาจากคลังใหญ่มาเติม ต้องบอก ERP ว่าหน่วยไหนใช้คลังไหน",
    )
    picture(
        doc,
        "his_setup/08_inventory.png",
        15.8,
        "ภาพที่ 3 หน้าสินค้าคงคลัง เมนู HIS อยู่ใต้การปฏิบัติการ (เห็นเมื่อได้สิทธิ์แล้ว)",
    )
    step_with_pic(
        doc,
        1,
        "ไปที่ สินค้าคงคลัง → การกำหนดค่า → HIS Service Units",
    )
    step_with_pic(
        doc,
        2,
        "จับคู่รหัสหน่วยบริการจาก HIS (เช่น OPD, IPD, ห้องผ่าตัด) กับคลังยาที่หน่วยนั้นใช้",
    )
    step_with_pic(
        doc,
        3,
        "ตรวจว่ามีที่เก็บชื่อ HIS Consumption อยู่ในระบบ (ระบบสร้างให้ตอนติดตั้ง) "
        "ยาที่จ่ายให้คนไข้จะถูกย้ายไปที่นี่ หมายถึงใช้ไปแล้ว",
    )
    picture(
        doc,
        "dataflow/df_issue_his.png",
        15.8,
        "ภาพที่ 4 ขั้นตอนตัดจ่ายยาจาก HIS ตั้งแต่รับข้อมูลจนถึงคืนสต็อก",
    )
    picture(
        doc,
        "Screenshot_inv_his_issue.png",
        15.8,
        "ภาพที่ 5 ตัวอย่างหน้าคิว HIS ตัดจ่ายสินค้า",
    )
    picture(
        doc,
        "Screenshot_inv_his_req.png",
        15.8,
        "ภาพที่ 6 ตัวอย่างหน้าคิว HIS เบิกเติมคลัง",
    )
    callout(
        doc,
        "ความต่างที่ควรรู้",
        "ตัดจ่ายยา: กดยืนยันแล้วสต็อกลดทันที · "
        "เบิกเติม: กดยืนยันแล้วได้ใบโอน คลังต้องหยิบและส่งของให้เสร็จก่อน รายการจึงจะปิด",
        "info",
    )

    # ----- 8 -----
    heading(doc, "บทที่ 8 ตรวจรหัสยาและเลขล็อตให้ตรงกับ HIS", 1)
    body(
        doc,
        "HIS กับ ERP ต้องใช้รหัสยาตัวเดียวกัน ถ้ารหัสไม่ตรง ERP จะไม่รู้ว่าเป็นยาอะไร "
        "และจะไม่สร้างยาใหม่ให้เอง",
    )
    step_with_pic(
        doc,
        1,
        "เทียบรายการยาและเวชภัณฑ์ใน HIS กับ ERP ให้รหัสตรงกันทุกตัว",
    )
    step_with_pic(
        doc,
        2,
        "ยาที่ต้องติดตามเลขล็อต ต้องมีเลขล็อตนั้นใน ERP ก่อน "
        "ถ้า HIS ไม่ส่งเลขล็อตมา ระบบจะตัดล็อตที่ใกล้หมดอายุที่สุดก่อนให้เอง",
    )
    picture(
        doc,
        "Screenshot_inv_hisout_lot.png",
        15.8,
        "ภาพที่ 7 ตัวอย่างเลขล็อตที่ถูกตัดจากข้อมูล HIS",
    )
    callout(
        doc,
        "สำหรับทีม IT",
        "ตรวจได้ว่ายาตัวไหนต้องส่งเลขล็อต โดยเรียก "
        "/vpk/api/v1/his/lookups/products?codes=รหัสยา แล้วดูค่า lot_required",
        "info",
    )

    # ----- 9 -----
    heading(doc, "บทที่ 9 ทดสอบก่อนใช้งานจริง", 1)
    body(doc, "ให้ทีม HIS ลองส่งข้อมูลจำนวนน้อย ๆ ก่อน แล้วทุกฝ่ายช่วยกันตรวจ")
    step_with_pic(doc, 1, "IT ตรวจว่าช่องทางรับข้อมูลเปิดอยู่ และรหัส API ใช้ได้")
    step_with_pic(doc, 2, "HIS ส่งข้อมูลทดสอบ เช่น รายได้ 1 วัน หรือยา 2–3 รายการ")
    step_with_pic(
        doc,
        3,
        "เปิดคิวใน ERP ดูสถานะ: Ready = ข้อมูลถูกต้องพร้อมใช้ · Error = มีปัญหาต้องแก้",
    )
    step_with_pic(
        doc,
        4,
        "ลองกด Post แล้วตรวจว่าใบแจ้งหนี้ ใบรับเงิน หรือสต็อกยาออกมาถูกต้อง",
    )
    heading(doc, "9.1 รายการตรวจก่อนเริ่มใช้จริง", 2)
    make_table(
        doc,
        ["✓", "ตรวจเรื่อง", "ผ่านเมื่อ"],
        [
            [" ", "เปิดรับข้อมูลและเปลี่ยนรหัส API แล้ว", "HIS ส่งข้อมูลเข้ามาได้"],
            [" ", "ให้สิทธิ์ผู้ใช้ครบ", "นักบัญชีและเภสัชกรเห็นเมนู HIS"],
            [" ", "จับคู่สิทธิการรักษาครบ", "ไม่มีข้อมูลติด Error เรื่องสิทธิ"],
            [" ", "จับคู่วิธีรับเงินและสมุดบัญชีครบ", "สร้างใบรับเงินได้"],
            [" ", "จับคู่หน่วยบริการกับคลังแล้ว", "ตัดยาจากคลังที่ถูกต้อง"],
            [" ", "รหัสยาและเลขล็อตตรงกับ HIS", "ไม่มีข้อมูลติด Error เรื่องยา"],
            [" ", "ทดลองกด Post แล้ว", "เอกสารบัญชีและสต็อกถูกต้อง"],
            [" ", "ทีม HIS เข้าใจกติกา", "ข้อมูลรายได้ไม่มีชื่อหรือ HN คนไข้"],
        ],
        [1.2, 8.0, 7.0],
    )

    # ----- 10 -----
    heading(doc, "บทที่ 10 เจอปัญหา แก้อย่างไร", 1)
    make_table(
        doc,
        ["อาการ", "น่าจะเกิดจาก", "แก้อย่างไร"],
        [
            ["มองไม่เห็นเมนู HIS", "ยังไม่ได้สิทธิ์", "ให้ผู้ดูแลระบบเพิ่มสิทธิ์ (บทที่ 3)"],
            ["HIS ส่งข้อมูลไม่เข้า", "รหัส API ผิด หรือยังไม่เปิดรับ", "ตรวจบทที่ 2"],
            ["ข้อมูลขึ้น Error เรื่องยอดเงิน", "ยอดรวมจาก HIS ไม่ตรงกับรายการ", "ให้ HIS แก้แล้วส่งใหม่"],
            ["ข้อมูลขึ้น Error เรื่องสิทธิ", "สิทธินั้นยังไม่ได้จับคู่", "เพิ่มในบทที่ 4 แล้วให้ HIS ส่งใหม่"],
            ["ข้อมูลขึ้น Error เรื่องยา", "รหัสยาหรือเลขล็อตไม่มีใน ERP", "เพิ่มยา/ล็อต หรือให้ HIS แก้รหัส"],
            ["สถานะ Ready แต่สต็อกยังไม่ลด", "ยังไม่มีใครกด Post", "ให้เภสัชกรกด Post"],
            ["กด Post ไปแล้วแต่ข้อมูลผิด", "ข้อมูลยืนยันแล้วแก้ตรง ๆ ไม่ได้", "ให้ HIS ส่งรายการยกเลิกมาแทน"],
            ["เบิกเติมกด Post แล้วยังไม่ปิด", "คลังยังส่งของไม่เสร็จ", "ให้คลังทำใบโอนให้เสร็จ"],
        ],
        [4.8, 5.4, 6.0],
    )
    heading(doc, "10.1 หาเมนูได้ที่ไหน", 2)
    make_table(
        doc,
        ["เมนู", "อยู่ที่"],
        [
            ["รายได้ / มัดจำ / จับคู่สิทธิ / วิธีรับเงิน / ใบนำส่งเงิน", "บัญชี → ลูกหนี้"],
            ["ประวัติการส่งข้อมูล (API Logs)", "บัญชี → การกำหนดค่า → HIS Interface"],
            ["ตัดจ่ายสินค้า / เบิกเติมคลัง", "สินค้าคงคลัง → การปฏิบัติการ"],
            ["จับคู่หน่วยบริการ", "สินค้าคงคลัง → การกำหนดค่า"],
        ],
        [8.5, 7.7],
    )
    heading(doc, "10.2 อ่านต่อ", 2)
    bullets(
        doc,
        [
            "การใช้งานประจำวันของคลัง: คู่มือกลุ่มงานคลัง บทที่ 10",
            "รายละเอียดข้อมูลที่ HIS ต้องส่ง (สำหรับ IT): เอกสารออกแบบ Interface HIS→ERP",
        ],
    )

    return finish(doc, out, toc_entries, ver_label, "คู่มือตั้งค่าเชื่อมต่อระบบ HIS")


if __name__ == "__main__":
    build()
