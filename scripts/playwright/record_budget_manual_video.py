#!/usr/bin/env python3
"""
อัดวิดีโอคู่มือกลุ่มงานงบประมาณ (แบบ Live Screen Recording)
ตาม docs/คู่มือการใช้งาน-ตามผังภาพรวม/01-คู่มือการใช้งาน-กลุ่มงานงบประมาณ-ver.1.docx
ครอบคลุมบทที่ 1–4 (ถึงการอนุมัติแผนงบประมาณ)

รัน:
  python3 scripts/playwright/record_budget_manual_video.py
  ODOO_URL=http://127.0.0.1:8069 DB=VPK-S2 HEADLESS=1 python3 scripts/playwright/record_budget_manual_video.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, submit_login, wait_for_server  # noqa: E402
from video_studio import (  # noqa: E402
    ChapterVideoRecorder,
    concat_mp4_files,
    render_info_diagram_png,
    render_title_card_png,
)

DB = os.environ.get("ODOO_DB", "VPK-S2")
HEADLESS = os.environ.get("HEADLESS", "1") == "1"


async def login_as(page, user, password=None):
    """เข้าสู่ระบบบนฐานข้อมูลที่กำหนด (ค่าเริ่มต้น VPK-S2)"""
    await page.goto(f"{BASE_URL}/web/session/logout?db={DB}", wait_until="domcontentloaded")
    await page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="load")
    await page.locator("#login").wait_for(state="visible")
    await submit_login(page, user, password)
OUT_DIR = Path(
    os.environ.get(
        "BUDGET_VIDEO_OUT",
        "docs/คู่มือการใช้งาน-ตามผังภาพรวม/videos/budget-ver1",
    )
)
WORK_DIR = Path(tempfile.gettempdir()) / "vpk_budget_video_work"

DEPT_USER = "uat.pharmacy"
BUDGET_USER = "uat.budget"

ANNUAL_BUDGET = "งบประมาณรายจ่ายประจำปี พ.ศ. 2569"
DEPT_NAME = "กลุ่มงานเภสัชกรรม"
FUND_NAME = "เงินบำรุง"
MATERIAL_POST = "หมวดค่าวัสดุ - เวชภัณฑ์ ยา - ยา + ยาเอกซเรย์"
ASSET_POST = "หมวดครุภัณฑ์ - ครุภัณฑ์สำนักงาน"
CONSTRUCTION_POST = "หมวดสิ่งก่อสร้าง"
PROJECT_POST = "หมวดค่าใช้สอย (โครงการ)"
PRODUCT_CODE = "00660"
PRODUCT_QTY = 10
PRODUCT_PRICE = 95.0


# --------------------------------------------------------------------------- helpers
async def wait_form(page, timeout=30000):
    await page.locator(".o_form_view").first.wait_for(state="visible", timeout=timeout)


async def wait_list(page, timeout=30000):
    await page.locator(".o_list_view, .o_list_renderer, .o_kanban_view").first.wait_for(
        state="visible", timeout=timeout
    )


async def save_form(page):
    save = page.locator(".o_form_button_save")
    if await save.count() and await save.first.is_visible():
        await save.first.click()
        await page.wait_for_timeout(900)
    await wait_form(page)


async def fill_m2o(page, field_name, query, option_text=None, exact=False):
    option_text = option_text or query
    field = page.locator(f'.o_form_view .o_field_widget[name="{field_name}"]').first
    await field.scroll_into_view_if_needed()
    box = field.locator("input.o_input").first
    await box.click()
    await box.fill("")
    await box.press_sequentially(query, delay=35)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=12000)
    target = menu.get_by_text(option_text, exact=exact).first
    await target.wait_for(state="visible", timeout=12000)
    await target.click()
    await page.wait_for_timeout(400)


async def click_create(page):
    btn = page.locator(".o_list_button_add, .o_control_panel .o_list_button_add, button.o_form_button_create").first
    await btn.wait_for(state="visible", timeout=20000)
    await btn.click()
    await wait_form(page)


async def click_header_button(page, name: str):
    btn = page.locator(f'.o_form_view header button[name="{name}"]').first
    await btn.wait_for(state="visible", timeout=20000)
    await btn.click()
    await page.wait_for_timeout(1200)


async def open_sidebar_app(page, app_name: str):
    app = page.locator(".o_vpk_app_link", has_text=app_name).first
    await app.wait_for(state="visible", timeout=20000)
    await app.click()
    await page.wait_for_timeout(700)


async def open_sidebar_menu(page, menu_text: str):
    link = page.locator(".o_vpk_sub_link, .o_vpk_app_link", has_text=menu_text).first
    await link.wait_for(state="visible", timeout=20000)
    await link.click()
    await page.wait_for_timeout(1000)


async def open_menu_path(page, labels):
    """ขยายเมนูย่อยแล้วคลิกเมนูปลายทางตามลำดับข้อความ"""
    for label in labels[:-1]:
        toggle = page.locator(".o_vpk_sub_link, .o_vpk_app_link", has_text=label).first
        await toggle.wait_for(state="visible", timeout=15000)
        parent = toggle.locator("xpath=ancestor::li[1]")
        cls = (await parent.get_attribute("class")) or ""
        if "expanded" not in cls:
            await toggle.click()
            await page.wait_for_timeout(400)
    await open_sidebar_menu(page, labels[-1])


async def fill_header_common(page, form_locked=True):
    await fill_m2o(page, "analytic_account_id", DEPT_NAME, DEPT_NAME, exact=False)
    await fill_m2o(page, "annual_budget_id", "2569", ANNUAL_BUDGET, exact=False)
    await fill_m2o(page, "fund_source_id", FUND_NAME, FUND_NAME, exact=False)
    if not form_locked:
        # แบบฟอร์มถูก lock จากเมนูย่อยแล้ว
        pass


async def click_tab(page, label: str):
    tab = page.get_by_role("tab", name=label)
    await tab.first.wait_for(state="visible", timeout=10000)
    await tab.first.click()
    await page.wait_for_timeout(500)


async def set_radio_plan_type(page, value_label: str):
    # plan_type radio: ในแผน / นอกแผน
    group = page.locator('.o_field_widget[name="plan_type"]').first
    await group.scroll_into_view_if_needed()
    opt = group.get_by_text(value_label, exact=True).first
    await opt.click()
    await page.wait_for_timeout(300)


async def dismiss_notifications(page):
    closer = page.locator(".o_notification .o_notification_close")
    n = await closer.count()
    for i in range(n):
        try:
            await closer.nth(i).click(timeout=1000)
        except Exception:
            pass


async def add_x2m_row(page, field_name: str):
    lines = page.locator(f'.o_field_widget[name="{field_name}"]')
    await lines.scroll_into_view_if_needed()
    add = lines.locator(".o_field_x2many_list_row_add a, .o_list_button_add").first
    await add.click()
    await page.wait_for_timeout(500)
    row = lines.locator("tr.o_selected_row, tbody tr.o_data_row").last
    await row.wait_for(state="visible", timeout=10000)
    return lines, row


async def fill_list_cell(row, field_name: str, value: str, press_tab: bool = True):
    cell = row.locator(f'[name="{field_name}"]').first
    await cell.click()
    inp = row.locator(
        f'[name="{field_name}"] input, [name="{field_name}"] textarea'
    ).first
    await inp.wait_for(state="visible", timeout=8000)
    await inp.fill("")
    await inp.press_sequentially(str(value), delay=25)
    if press_tab:
        await inp.press("Tab")


async def fill_list_m2o(page, row, field_name: str, query: str, option_text: str):
    await fill_list_cell(row, field_name, query, press_tab=False)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    await menu.get_by_text(option_text, exact=False).first.click()
    await page.wait_for_timeout(300)


# --------------------------------------------------------------------------- chapters
async def chapter1(page, rec: ChapterVideoRecorder):
    cards = WORK_DIR / "cards"
    cards.mkdir(parents=True, exist_ok=True)

    title = cards / "ch1_title.png"
    render_title_card_png(
        title,
        kicker="คู่มือกลุ่มงานงบประมาณ · บทที่ 1",
        title="การทำแผนตั้งของบประมาณประจำปี (4 แบบฟอร์ม)",
        subtitle="ตั้งคำของบวัสดุ ครุภัณฑ์ ก่อสร้าง และโครงการ แล้วส่งให้หน่วยงบประมาณ",
        role_badge="บทบาท: ผู้ใช้งานหน่วยงาน (uat.pharmacy)",
    )
    rec.add_static_card_segment(
        title,
        "ยินดีต้อนรับสู่คู่มือการใช้งานระบบงบประมาณ บทที่หนึ่ง การทำแผนตั้งของบประมาณประจำปี ทั้งสี่แบบฟอร์ม",
        min_sec=5.5,
    )

    diagram = cards / "ch1_forms.png"
    render_info_diagram_png(
        diagram,
        "สรุปแบบฟอร์มคำขอตั้งงบประมาณทั้ง 4 ประเภท",
        [
            ("1) แบบฟอร์มตั้งงบวัสดุ", "โหลดรายการจากระบบหรือ Excel แล้วกรอกปริมาณที่ขอ", (16, 185, 129)),
            ("2) แบบฟอร์มครุภัณฑ์", "โหลดบัญชีครุภัณฑ์ แล้วกรอกจำนวนที่ขอซื้อใหม่/ทดแทน/เพิ่ม", (59, 130, 246)),
            ("3) แบบฟอร์มก่อสร้าง", "ระบุโครงการ พื้นที่ สถานที่ ราคา และลักษณะงาน", (245, 158, 11)),
            ("4) แบบฟอร์มโครงการ", "กรอกชื่อโครงการ กลุ่มเป้าหมาย งบที่ขอ และผู้รับผิดชอบ", (168, 85, 247)),
        ],
        "เลือกเมนู งบประมาณ → บันทึกคำของบ → แล้วเลือกแบบฟอร์มให้ตรงประเภทงบ",
    )
    rec.add_static_card_segment(
        diagram,
        "ระบบแบ่งคำขอตั้งงบเป็นสี่แบบฟอร์ม ได้แก่ วัสดุ ครุภัณฑ์ ก่อสร้าง และโครงการ ให้เลือกเมนูให้ตรงประเภทงบที่จะขอ",
        min_sec=7.0,
    )

    # 1.1 login
    async def step_login():
        await page.goto(f"{BASE_URL}/web/session/logout?db={DB}", wait_until="domcontentloaded")
        await page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="load")
        await page.locator("#login").wait_for(state="visible")
        await asyncio.sleep(0.8)
        select = page.locator("#vpk_test_user")
        if await select.count():
            await rec.point_and_highlight(select, "เลือกผู้ใช้ทดสอบ", pause=0.7)
            await select.select_option(value=DEPT_USER)
            await page.wait_for_timeout(500)
            # JS บนหน้า login จะเติม login/password จาก data-password ให้แล้ว
        else:
            await submit_login(page, DEPT_USER)
            return
        await rec.demo_click(
            page.locator("button.vpk-login-submit"),
            "เข้าสู่ระบบ",
            pause_before=0.9,
            pause_after=0.5,
        )
        await page.wait_for_timeout(2000)
        if "/web/login" in page.url:
            await submit_login(page, DEPT_USER)

    await rec.run_step(
        "1.1",
        "เข้าสู่ระบบด้วยบัญชีผู้ใช้งานหน่วยงาน แล้วคลิกปุ่มเข้าสู่ระบบ",
        "ขั้นตอนที่หนึ่ง เปิดเว็บเบราว์เซอร์เข้าสู่ระบบอีอาร์พีของโรงพยาบาล เลือกบัญชีผู้ใช้งานหน่วยงาน แล้วคลิกปุ่มเข้าสู่ระบบ",
        step_login(),
        hold_after=1.0,
    )

    async def step_open_budget_menu():
        await open_sidebar_app(page, "งบประมาณ")
        await asyncio.sleep(0.6)
        await open_menu_path(page, ["บันทึกคำของบ", "แบบฟอร์มตั้งงบวัสดุ"])
        await wait_list(page)

    await rec.run_step(
        "1.1",
        "คลิกแอป งบประมาณ → บันทึกคำของบ → แบบฟอร์มตั้งงบวัสดุ",
        "ขั้นตอนที่สอง ที่แถบเมนูด้านซ้าย คลิกเลือกแอปพลิเคชันงบประมาณ จากนั้นคลิกเมนูบันทึกคำของบ และเลือกแบบฟอร์มตั้งงบวัสดุ",
        step_open_budget_menu(),
        hold_after=1.2,
    )

    # 1.2 material form create + header
    async def step_create_material():
        await rec.demo_click(page.locator(".o_list_button_add").first, "สร้าง", pause_before=0.9, pause_after=1.0)
        await wait_form(page)
        await fill_header_common(page)
        await set_radio_plan_type(page, "ในแผน")
        await save_form(page)

    await rec.run_step(
        "1.2",
        "กดสร้าง แล้วกรอกหน่วยงาน แผนงบประมาณประจำปี แหล่งเงิน และเลือกประเภท ในแผน",
        "ขั้นตอนถัดไป กดปุ่มสร้าง จากนั้นกรอกหน่วยงาน ชื่อแผนงบประมาณประจำปี และแหล่งเงินเงินบำรุง แล้วเลือกประเภทการตั้งงบประมาณเป็นในแผน",
        step_create_material(),
        hold_after=1.2,
    )

    # Excel load flow
    excel_path = WORK_DIR / "template-รายการวัสดุ.xlsx"

    async def step_excel_import():
        await rec.demo_click(
            page.locator('button[name="action_open_material_detail_import"]').first,
            "โหลดจาก Excel",
            pause_before=0.9,
            pause_after=1.0,
        )
        modal = page.locator(".modal").last
        await modal.wait_for(state="visible", timeout=15000)
        # เลือกหมวดงบ
        tags = modal.locator('.o_field_widget[name="budget_post_ids"] input').first
        await rec.point_and_highlight(tags, "หมวดงบประมาณ", pause=0.7)
        await tags.click()
        await tags.fill("")
        await tags.press_sequentially("ยาเอกซเรย์", delay=35)
        menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
        await menu.wait_for(state="visible", timeout=10000)
        await menu.get_by_text(MATERIAL_POST, exact=False).first.click()
        await page.wait_for_timeout(500)

        # ดาวน์โหลดแบบฟอร์ม
        async with page.expect_download(timeout=30000) as dl_info:
            await rec.demo_click(
                modal.locator('button[name="action_download_template"]'),
                "ดาวน์โหลดแบบฟอร์ม",
                pause_before=0.9,
                pause_after=0.5,
            )
        download = await dl_info.value
        await download.save_as(str(excel_path))

        # กรอกปริมาณใน Excel
        wb = load_workbook(excel_path)
        ws = wb["รายการวัสดุ"] if "รายการวัสดุ" in wb.sheetnames else wb.active
        # หาแถวสินค้า 00660
        found = False
        for row in range(2, ws.max_row + 1):
            code = str(ws.cell(row, 1).value or "").strip()
            if code == PRODUCT_CODE:
                ws.cell(row, 5).value = PRODUCT_QTY
                if not ws.cell(row, 4).value:
                    ws.cell(row, 4).value = PRODUCT_PRICE
                found = True
                break
        if not found and ws.max_row >= 2:
            # fallback: ใส่แถวแรกที่มีรหัส
            for row in range(2, min(ws.max_row, 30) + 1):
                if ws.cell(row, 1).value:
                    ws.cell(row, 5).value = PRODUCT_QTY
                    if not ws.cell(row, 4).value:
                        ws.cell(row, 4).value = PRODUCT_PRICE
                    found = True
                    break
        if not found:
            raise RuntimeError("ไม่พบแถวสินค้าในไฟล์ template Excel")
        wb.save(excel_path)

        # อัปโหลดกลับ
        file_input = modal.locator('input[type="file"]').first
        await file_input.set_input_files(str(excel_path))
        await page.wait_for_timeout(700)
        await rec.demo_click(
            modal.locator('button[name="action_import"]'),
            "นำเข้า",
            pause_before=0.9,
            pause_after=1.5,
        )
        # ปิดผลลัพธ์
        close_btn = page.locator(".modal").last.locator("button:has-text('ปิด'), button:has-text('Cancel'), button:has-text('ยกเลิก')").first
        if await close_btn.count():
            await close_btn.click()
        await page.wait_for_timeout(800)
        await wait_form(page)
        await click_tab(page, "รายการวัสดุ")
        await page.wait_for_timeout(800)

    await rec.run_step(
        "1.2",
        "โหลดจาก Excel: เลือกหมวดงบ → ดาวน์โหลดแบบฟอร์ม → กรอกปริมาณ → นำเข้า",
        "ต่อไปคลิกปุ่มโหลดจากเอ็กเซล เลือกหมวดงบประมาณ ดาวน์โหลดแบบฟอร์ม กรอกปริมาณที่ขอในคอลัมน์ปริมาณที่ขอ แล้วอัปโหลดกลับและกดนำเข้า",
        step_excel_import(),
        hold_after=1.4,
    )

    async def step_overview_and_reason():
        await click_tab(page, "แบบตั้งงบภาพรวม")
        await page.wait_for_timeout(800)
        overview = page.locator('.o_field_widget[name="material_line_ids"]').first
        await overview.scroll_into_view_if_needed()
        await rec.point_and_highlight(overview, "แบบตั้งงบภาพรวม", pause=0.8)
        reason = page.locator('.o_field_widget[name="request_justification"] textarea').first
        await reason.scroll_into_view_if_needed()
        await rec.point_and_highlight(reason, "เหตุผลประกอบคำขอ", pause=0.7)
        await reason.click()
        await reason.fill(
            "ขอตั้งงบเวชภัณฑ์ยา NSS สำหรับปีงบประมาณ 2569 เพื่อสำรองใช้ในกลุ่มงานเภสัชกรรม"
        )
        await save_form(page)

    await rec.run_step(
        "1.2",
        "ตรวจแท็บแบบตั้งงบภาพรวม แล้วระบุเหตุผลประกอบคำขอตั้งงบ",
        "คลิกสลับไปที่แท็บแบบตั้งงบภาพรวม เพื่อตรวจยอดรวม แล้วเลื่อนลงไปพิมพ์เหตุผลประกอบคำขอตั้งงบ และกดบันทึก",
        step_overview_and_reason(),
        hold_after=1.0,
    )

    # Keep material URL for later submit; also create asset/construction/project quickly
    material_url = page.url

    async def step_create_asset():
        await open_menu_path(page, ["บันทึกคำของบ", "แบบฟอร์มครุภัณฑ์"])
        await wait_list(page)
        await rec.demo_click(page.locator(".o_list_button_add").first, "สร้าง", pause_before=0.7, pause_after=0.8)
        await wait_form(page)
        await fill_header_common(page)
        await save_form(page)
        await rec.demo_click(
            page.locator('button[name="action_open_load_wizard"]').first,
            "โหลดรายการ",
            pause_before=0.8,
            pause_after=0.8,
        )
        modal = page.locator(".modal").last
        await modal.wait_for(state="visible")
        tags = modal.locator('.o_field_widget[name="budget_post_ids"] input').first
        await tags.click()
        await tags.press_sequentially("ครุภัณฑ์สำนักงาน", delay=30)
        menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
        await menu.wait_for(state="visible")
        await menu.get_by_text(ASSET_POST, exact=False).first.click()
        await page.wait_for_timeout(400)
        await rec.demo_click(modal.locator('button[name="action_load"]'), "โหลด", pause_before=0.7, pause_after=1.5)
        await wait_form(page)
        await click_tab(page, "แบบตั้งงบครุภัณฑ์")
        # กรอกจำนวนแถวแรก
        row = page.locator('.o_field_widget[name="asset_line_ids"] tbody tr').first
        await row.wait_for(state="visible", timeout=20000)
        for fname, val in (("qty_new_purchase", "1"), ("unit_price", "15700"), ("reason", "ทดแทนเครื่องปรับอากาศชำรุด")):
            cell = row.locator(f'[name="{fname}"] input, [name="{fname}"] textarea').first
            if await cell.count():
                await cell.click()
                await cell.fill(val)
        await save_form(page)

    await rec.run_step(
        "1.3",
        "สร้างแบบฟอร์มครุภัณฑ์ โหลดรายการ แล้วกรอกจำนวน/ราคา/เหตุผล",
        "บทถัดไป สร้างใบคำขอแบบฟอร์มครุภัณฑ์ กรอกส่วนหัว โหลดรายการจากหมวดงบครุภัณฑ์สำนักงาน แล้วกรอกจำนวนที่ขอซื้อใหม่ ราคาต่อหน่วย และเหตุผล",
        step_create_asset(),
        hold_after=1.0,
    )

    async def step_create_construction():
        await open_menu_path(page, ["บันทึกคำของบ", "แบบฟอร์ม ก่อสร้าง"])
        await wait_list(page)
        await rec.demo_click(page.locator(".o_list_button_add").first, "สร้าง", pause_before=0.7, pause_after=0.8)
        await wait_form(page)
        await fill_header_common(page)
        await save_form(page)
        await click_tab(page, "แบบตั้งงบก่อสร้าง")
        lines, row = await add_x2m_row(page, "construction_line_ids")
        await fill_list_m2o(page, row, "budget_post_id", "สิ่งก่อสร้าง", CONSTRUCTION_POST)
        await fill_list_cell(row, "item_name", "ปรับปรุงห้องจ่ายยา")
        await fill_list_cell(row, "usage_area", "48")
        await fill_list_cell(row, "construction_location", "อาคารเภสัชกรรม ชั้น 1")
        await fill_list_cell(row, "requested_quantity", "1")
        await fill_list_cell(row, "unit_price", "250000")
        improve = row.locator('[name="construction_request_improvement"]')
        if await improve.count():
            await improve.first.click()
        await fill_list_cell(row, "reason", "ปรับปรุงพื้นที่ให้บริการผู้ป่วย")
        await save_form(page)

    await rec.run_step(
        "1.4",
        "สร้างแบบฟอร์มก่อสร้าง และกรอกรายละเอียดงานก่อสร้าง",
        "ต่อไปสร้างใบคำขอแบบฟอร์มก่อสร้าง กรอกส่วนหัว แล้วเพิ่มรายการงานก่อสร้าง พร้อมระบุพื้นที่ สถานที่ ราคา และลักษณะงานขอปรับปรุง",
        step_create_construction(),
        hold_after=1.0,
    )

    async def step_create_project():
        await open_menu_path(page, ["บันทึกคำของบ", "แบบฟอร์มโครงการ"])
        await wait_list(page)
        await rec.demo_click(page.locator(".o_list_button_add").first, "สร้าง", pause_before=0.7, pause_after=0.8)
        await wait_form(page)
        await fill_header_common(page)
        await save_form(page)
        await click_tab(page, "แบบตั้งงบโครงการ")
        lines, row = await add_x2m_row(page, "project_line_ids")
        await fill_list_m2o(page, row, "budget_post_id", "โครงการ", PROJECT_POST)
        await fill_list_cell(row, "item_name", "โครงการส่งเสริมการใช้ยาอย่างสมเหตุผล")
        await fill_list_cell(row, "item_description", "จัดอบรมและจัดทำสื่อให้ความรู้บุคลากร")
        await fill_list_cell(row, "duration", "12 เดือน")
        await fill_list_cell(row, "target_group", "เภสัชกรและพยาบาล")
        await fill_list_cell(row, "requested_quantity", "1")
        await fill_list_cell(row, "unit_price", "80000")
        await fill_list_cell(row, "objective", "ลดการใช้ยาที่ไม่จำเป็น")
        await fill_list_cell(row, "expected_benefit", "ลดค่าใช้จ่ายด้านยา")
        await fill_list_cell(row, "owner_name", "หัวหน้ากลุ่มงานเภสัชกรรม")
        await save_form(page)

    await rec.run_step(
        "1.5",
        "สร้างแบบฟอร์มโครงการ และกรอกรายละเอียดโครงการ",
        "ต่อไปสร้างใบคำขอแบบฟอร์มโครงการ กรอกส่วนหัว แล้วเพิ่มรายการโครงการ พร้อมงบที่ขอ วัตถุประสงค์ และผู้รับผิดชอบ",
        step_create_project(),
        hold_after=1.0,
    )

    async def step_submit_material():
        await page.goto(material_url, wait_until="domcontentloaded")
        await wait_form(page)
        await page.wait_for_timeout(800)
        await rec.demo_click(
            page.locator('button[name="action_submit"]').first,
            "ส่งใบคำขอ",
            pause_before=1.0,
            pause_after=1.5,
        )
        await page.wait_for_timeout(1000)
        # ยืนยันสถานะ
        state = page.locator('.o_field_widget[name="state"] .o_statusbar_status, .o_field_widget[name="state"]').first
        await state.scroll_into_view_if_needed()

    await rec.run_step(
        "1.6",
        "เปิดใบคำขอวัสดุ แล้วคลิกปุ่มสีเขียว ส่งใบคำขอ",
        "เมื่อตรวจสอบรายการครบแล้ว กลับไปที่ใบคำขอวัสดุ แล้วคลิกปุ่มส่งใบคำขอ สถานะจะเปลี่ยนจากแบบร่างเป็นส่งหน่วยงบประมาณ",
        step_submit_material(),
        hold_after=1.5,
    )

    return material_url


async def chapter2(page, rec: ChapterVideoRecorder, material_url: str):
    cards = WORK_DIR / "cards"
    title = cards / "ch2_title.png"
    render_title_card_png(
        title,
        kicker="คู่มือกลุ่มงานงบประมาณ · บทที่ 2",
        title="การรับคำขอตั้งแผนจากหน่วยงาน",
        subtitle="หน่วยงบประมาณตรวจสอบใบคำขอ แล้วกดรับเรื่อง หรือตีกลับให้หน่วยงานแก้ไข",
        role_badge="บทบาท: เจ้าหน้าที่งานงบประมาณ (uat.budget)",
    )
    rec.add_static_card_segment(
        title,
        "บทที่สอง การรับคำขอตั้งแผนจากหน่วยงาน โดยเจ้าหน้าที่งานงบประมาณ",
        min_sec=4.5,
    )

    async def step_login_budget():
        await login_as(page, BUDGET_USER)
        await page.wait_for_timeout(1000)

    await rec.run_step(
        "2.1",
        "เข้าสู่ระบบด้วยบัญชีเจ้าหน้าที่งานงบประมาณ",
        "ขั้นตอนที่หนึ่ง เข้าสู่ระบบด้วยบัญชีเจ้าหน้าที่งานงบประมาณ แล้วคลิกไอคอนแอปพลิเคชันงบประมาณ",
        step_login_budget(),
        hold_after=1.0,
    )

    async def step_open_central():
        await open_sidebar_app(page, "งบประมาณ")
        await open_sidebar_menu(page, "รวบรวมคำของบ (หน่วยงบประมาณ)")
        await wait_list(page)
        await page.wait_for_timeout(800)

    await rec.run_step(
        "2.1",
        "เปิดเมนู รวบรวมคำของบ (หน่วยงบประมาณ)",
        "ขั้นตอนที่สอง คลิกเมนูรวบรวมคำของบหน่วยงบประมาณ เพื่อดูรายการคำขอตั้งงบทั้งหมดที่หน่วยงานส่งเข้ามา",
        step_open_central(),
        hold_after=1.2,
    )

    async def step_open_and_receive():
        # แสดงรายการในเมนูรวบรวม แล้วเปิดใบวัสดุที่หน่วยงานเพิ่งส่ง
        await page.wait_for_timeout(600)
        if material_url:
            await page.goto(material_url, wait_until="domcontentloaded")
        else:
            row = page.locator(".o_list_view .o_data_row").first
            await rec.demo_click(row, "เปิดใบคำขอ", pause_before=0.8, pause_after=1.0)
        await wait_form(page)
        await page.wait_for_timeout(700)
        await rec.point_and_highlight(
            page.locator('.o_field_widget[name="state"]').first,
            "สถานะ: ส่งหน่วยงบประมาณ",
            pause=0.9,
        )
        await rec.demo_click(
            page.locator('button[name="action_receive"]').first,
            "รับเรื่อง",
            pause_before=1.0,
            pause_after=1.5,
        )

    await rec.run_step(
        "2.1",
        "เปิดใบคำขอ ตรวจรายละเอียด แล้วกดปุ่ม รับเรื่อง",
        "ขั้นตอนที่สามและสี่ เปิดใบคำขอที่ต้องการ ตรวจสอบส่วนหัวและรายการ แล้วคลิกปุ่มรับเรื่อง สถานะจะเปลี่ยนเป็นรับเรื่องแล้ว",
        step_open_and_receive(),
        hold_after=1.5,
    )


async def chapter3(page, rec: ChapterVideoRecorder):
    cards = WORK_DIR / "cards"
    title = cards / "ch3_title.png"
    render_title_card_png(
        title,
        kicker="คู่มือกลุ่มงานงบประมาณ · บทที่ 3",
        title="การรวบรวมและพิจารณาจัดสรรงบประมาณ",
        subtitle="เริ่มพิจารณา แล้วบันทึกปริมาณที่จัดสรรและมูลค่าที่จัดสรรรายบรรทัด",
        role_badge="บทบาท: เจ้าหน้าที่งานงบประมาณ (uat.budget)",
    )
    rec.add_static_card_segment(
        title,
        "บทที่สาม การรวบรวมและพิจารณาจัดสรรงบประมาณ",
        min_sec=4.0,
    )

    async def step_start_review():
        await rec.demo_click(
            page.locator('button[name="action_start_review"]').first,
            "เริ่มพิจารณา",
            pause_before=1.0,
            pause_after=1.4,
        )

    await rec.run_step(
        "3.1",
        "คลิกปุ่ม เริ่มพิจารณา เพื่อเข้าสู่สถานะอยู่ระหว่างพิจารณา",
        "ขั้นตอนที่หนึ่ง เปิดใบคำขอที่มีสถานะรับเรื่องแล้ว แล้วคลิกปุ่มเริ่มพิจารณา สถานะจะเปลี่ยนเป็นอยู่ระหว่างพิจารณา",
        step_start_review(),
        hold_after=1.2,
    )

    async def step_allocate():
        await click_tab(page, "รายการวัสดุ")
        await page.wait_for_timeout(600)
        await rec.demo_click(
            page.locator('button[name="action_open_material_allocation_wizard"]').first,
            "จัดสรรงบประมาณ",
            pause_before=0.9,
            pause_after=1.0,
        )
        modal = page.locator(".modal").last
        await modal.wait_for(state="visible", timeout=15000)
        # วิธีจัดสรร = เท่ากับที่ขอ (ค่าเริ่มต้น)
        mode = modal.locator('.o_field_widget[name="mode"]')
        if await mode.count():
            await rec.point_and_highlight(mode, "วิธีจัดสรร: เท่ากับที่ขอ", pause=0.9)
        await rec.demo_click(
            modal.locator('button[name="action_apply"]'),
            "จัดสรร",
            pause_before=0.9,
            pause_after=1.5,
        )
        await wait_form(page)
        await click_tab(page, "แบบตั้งงบภาพรวม")
        await page.wait_for_timeout(1000)
        overview = page.locator('.o_field_widget[name="material_line_ids"]').first
        await overview.scroll_into_view_if_needed()
        await rec.point_and_highlight(overview, "งบประมาณที่ได้รับ", pause=1.0)
        await save_form(page)

    await rec.run_step(
        "3.1",
        "กดจัดสรรงบประมาณ เลือกเท่ากับที่ขอ แล้วตรวจยอดในแท็บแบบตั้งงบภาพรวม",
        "ขั้นตอนที่สองและสาม คลิกปุ่มจัดสรรงบประมาณ เลือกวิธีจัดสรรเท่ากับที่ขอ แล้วเปิดแท็บแบบตั้งงบภาพรวมเพื่อตรวจยอดรวมก่อนส่งอนุมัติ",
        step_allocate(),
        hold_after=1.4,
    )


async def chapter4(page, rec: ChapterVideoRecorder):
    cards = WORK_DIR / "cards"
    title = cards / "ch4_title.png"
    render_title_card_png(
        title,
        kicker="คู่มือกลุ่มงานงบประมาณ · บทที่ 4",
        title="การอนุมัติแผนงบประมาณและประกาศแจ้งวงเงิน",
        subtitle="กดอนุมัติ แล้วตรวจสอบการซิงก์วงเงินเข้าแผนงบประมาณประจำปีและหน้าสรุปสถานะ",
        role_badge="บทบาท: เจ้าหน้าที่งานงบประมาณ (uat.budget)",
    )
    rec.add_static_card_segment(
        title,
        "บทที่สี่ การอนุมัติแผนงบประมาณและประกาศแจ้งวงเงิน",
        min_sec=4.5,
    )

    async def step_approve():
        await rec.demo_click(
            page.locator('button[name="action_approve"]').first,
            "อนุมัติ",
            pause_before=1.1,
            pause_after=2.0,
        )
        await page.wait_for_timeout(1000)
        # แสดงยอดงบที่ได้รับ
        received = page.locator('.o_field_widget[name="total_received_budget_amount"]').first
        if await received.count():
            await received.scroll_into_view_if_needed()
            await rec.point_and_highlight(received, "งบประมาณที่ได้รับ", pause=1.0)

    await rec.run_step(
        "4.1",
        "คลิกปุ่ม อนุมัติ สถานะเปลี่ยนเป็นอนุมัติแล้ว และแสดงยอดงบประมาณที่ได้รับ",
        "ขั้นตอนที่หนึ่ง เปิดใบคำขอที่อยู่ระหว่างพิจารณา แล้วคลิกปุ่มอนุมัติ สถานะจะเปลี่ยนเป็นอนุมัติแล้ว พร้อมแสดงยอดงบประมาณที่ได้รับ",
        step_approve(),
        hold_after=1.5,
    )

    async def step_annual_budget():
        await open_menu_path(page, ["การกำหนดค่า", "งบประมาณประจำปี"])
        await wait_list(page)
        await page.wait_for_timeout(800)
        row = page.locator(".o_data_row", has_text="2569").first
        if await row.count():
            await rec.demo_click(row, "เปิดแผนงบประมาณ 2569", pause_before=0.8, pause_after=1.2)
            await wait_form(page)
            await page.wait_for_timeout(1000)

    await rec.run_step(
        "4.1",
        "ไปที่ การกำหนดค่า → งบประมาณประจำปี เพื่อตรวจวงเงินที่ซิงก์เข้าแผน",
        "ขั้นตอนที่สอง ไปที่เมนูการกำหนดค่า งบประมาณประจำปี เพื่อตรวจสอบว่าวงเงินที่อนุมัติถูกซิงก์เข้าสู่แผนงบประมาณประจำปีเรียบร้อยแล้ว",
        step_annual_budget(),
        hold_after=1.5,
    )

    async def step_status_dashboard():
        await open_menu_path(page, ["Dashboard งบประมาณ", "ติดตามสถานะคำของบประมาณ"])
        await page.wait_for_timeout(2000)
        # รอโหลด dashboard
        dash = page.locator(".o_vpk_budget_dashboard, .o_vpk_budget_status_action").first
        try:
            await dash.wait_for(state="visible", timeout=20000)
        except PlaywrightTimeout:
            pass
        await page.wait_for_timeout(1500)

    await rec.run_step(
        "4.1",
        "เปิดเมนู ติดตามสถานะคำของบประมาณ เพื่อดูสรุปแผนงบที่จัดสรรและอนุมัติ",
        "ขั้นตอนที่สาม ไปที่เมนูติดตามสถานะคำของบประมาณ เพื่อดูภาพรวมสรุปแผนงบที่จัดสรรและอนุมัติ สำหรับใช้ประกาศแจ้งวงเงินให้หน่วยงาน",
        step_status_dashboard(),
        hold_after=2.0,
    )

    end = cards / "ch4_end.png"
    render_title_card_png(
        end,
        kicker="จบคลิปบทที่ 1–4",
        title="อนุมัติแผนงบประมาณเรียบร้อย",
        subtitle="หน่วยงานตั้งคำของบ → หน่วยงบประมาณรับเรื่อง พิจารณาจัดสรร และอนุมัติ → วงเงินเข้าแผนประจำปี",
        role_badge="พร้อมใช้งานต่อเนื่องไปยังการติดตาม Dashboard และการตรวจงบ PR",
    )
    rec.add_static_card_segment(
        end,
        "จบคู่มือกลุ่มงานงบประมาณ บทที่หนึ่งถึงบทที่สี่ ขอบคุณที่รับชม",
        min_sec=5.0,
    )


async def main():
    wait_for_server(timeout=120)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=HEADLESS, slow_mo=0)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True,
            locale="th-TH",
        )
        page = await context.new_page()
        page.set_default_timeout(45000)

        chapter_files = []

        # Chapter 1
        rec1 = ChapterVideoRecorder(page, WORK_DIR, "chapter01")
        print("=== Recording Chapter 1 ===")
        material_url = await chapter1(page, rec1)
        out1 = OUT_DIR / "01-ตั้งคำของบประมาณ-4แบบฟอร์ม.mp4"
        rec1.build_mp4(out1)
        chapter_files.append(out1)
        print("DONE", out1)

        # Chapter 2
        rec2 = ChapterVideoRecorder(page, WORK_DIR, "chapter02")
        print("=== Recording Chapter 2 ===")
        await chapter2(page, rec2, material_url)
        out2 = OUT_DIR / "02-รับคำขอตั้งแผนจากหน่วยงาน.mp4"
        rec2.build_mp4(out2)
        chapter_files.append(out2)
        print("DONE", out2)

        # Chapter 3 (ต่อจากใบที่รับเรื่องแล้วบนหน้าจอปัจจุบัน)
        rec3 = ChapterVideoRecorder(page, WORK_DIR, "chapter03")
        print("=== Recording Chapter 3 ===")
        await chapter3(page, rec3)
        out3 = OUT_DIR / "03-พิจารณาจัดสรรงบประมาณ.mp4"
        rec3.build_mp4(out3)
        chapter_files.append(out3)
        print("DONE", out3)

        # Chapter 4
        rec4 = ChapterVideoRecorder(page, WORK_DIR, "chapter04")
        print("=== Recording Chapter 4 ===")
        await chapter4(page, rec4)
        out4 = OUT_DIR / "04-อนุมัติแผนงบประมาณ.mp4"
        rec4.build_mp4(out4)
        chapter_files.append(out4)
        print("DONE", out4)

        full = OUT_DIR / "00-คู่มืองบประมาณ-ver1-บท1ถึง4-ฉบับเต็ม.mp4"
        concat_mp4_files(chapter_files, full)
        print("FULL", full)

        await browser.close()

    print("\nวิดีโอทั้งหมดอยู่ที่:", OUT_DIR.resolve())
    for p in sorted(OUT_DIR.glob("*.mp4")):
        mb = p.stat().st_size / (1024 * 1024)
        print(f"  - {p.name} ({mb:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
