#!/usr/bin/env python3
"""จับภาพสายงานเจ้าหนี้ตาม DST/2026/0786: Dashboard → ดึง Draft → WHT 1% → POST → ส่งการเงิน"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/ap_dst0786")
USER = "uat.gfmis"
DOC_ID = 786  # DST/2026/0786
DOC_NAME = "DST/2026/0786"
PO_ID = 136
WHT_LABEL = "WHT 1% ซื้อสินค้า/บริการทั่วไป"


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(400)
    await page.screenshot(path=str(path), full_page=False)
    print("SHOT", path)
    return path


async def open_ap_dashboard(page):
    # client action tag จาก menu.xml
    await page.goto(
        f"{BASE_URL}/odoo/action-1093",
        wait_until="domcontentloaded",
    )
    await page.wait_for_timeout(1500)
    # fallback: ค้นหาจากเมนูถ้ายังไม่เจอหัว Dashboard
    head = page.locator("text=งานเจ้าหนี้: รายการขอเบิกจ่ายจากจัดซื้อ")
    if not await head.count():
        await page.goto(f"{BASE_URL}/odoo", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        # เปิดแอปบัญชี
        app = page.locator(".o_app").filter(has_text="ระบบบัญชี")
        if await app.count():
            await app.first.click()
            await page.wait_for_timeout(1200)
        menu = page.locator("a, button, .dropdown-item").filter(
            has_text="Dashboard งานเจ้าหนี้"
        )
        if await menu.count():
            await menu.first.click()
            await page.wait_for_timeout(1500)
    await head.first.wait_for(state="visible", timeout=30000)


async def find_row(page):
    # ค้นหาเลขเอกสาร
    search = page.locator('input[placeholder*="ค้นหา"]')
    if await search.count():
        await search.first.fill(DOC_NAME)
        await page.wait_for_timeout(600)
    row = page.locator("tr").filter(has_text=DOC_NAME)
    await row.first.wait_for(state="visible", timeout=20000)
    return row.first


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(60000)
        try:
            await login_as(page, USER)
            await shot(page, "01_home_after_login.png")

            # เมนูระบบเจ้าหนี้
            await page.goto(f"{BASE_URL}/odoo/accounting", wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)
            # ถ้ายังอยู่หน้า home apps
            if "/odoo" in page.url and "accounting" not in page.url:
                app = page.locator(".o_app").filter(has_text="ระบบบัญชี")
                if await app.count():
                    await app.first.click()
                    await page.wait_for_timeout(1500)
            # เปิดเมนูระบบเจ้าหนี้
            payables = page.locator(
                ".o_menu_sections .dropdown-toggle, .o_menu_sections a, .o-dropdown"
            ).filter(has_text="ระบบเจ้าหนี้")
            if await payables.count():
                await payables.first.click()
                await page.wait_for_timeout(700)
                await shot(page, "02_menu_payables.png")
            else:
                await shot(page, "02_menu_payables.png")

            await open_ap_dashboard(page)
            row = await find_row(page)
            await row.scroll_into_view_if_needed()
            await shot(page, "03_dashboard_wait.png")

            # เปิดใบขออนุมัติเบิกจ่าย
            link = row.locator("a").filter(has_text=DOC_NAME)
            if await link.count():
                await link.first.click()
                await page.wait_for_timeout(1500)
                form = page.locator(".o_form_view")
                if await form.count():
                    await form.first.wait_for(state="visible", timeout=15000)
                await shot(page, "04_payment_request_doc.png")
                await page.go_back()
                await page.wait_for_timeout(1000)
                await open_ap_dashboard(page)
                row = await find_row(page)

            # เปิด PO
            po_link = row.locator("a").filter(has_text="P00048")
            if await po_link.count():
                await po_link.first.click()
                await page.wait_for_timeout(1500)
                await page.locator(".o_form_view").first.wait_for(state="visible", timeout=15000)
                await shot(page, "05_po.png")
                await page.go_back()
                await page.wait_for_timeout(1000)
                await open_ap_dashboard(page)
                row = await find_row(page)

            # ดึงรายการตั้งเจ้าหนี้
            pull = row.locator("button").filter(has_text="ดึงรายการตั้งเจ้าหนี้")
            if await pull.count() and await pull.first.is_enabled():
                await pull.first.click()
                await page.wait_for_timeout(2500)
            else:
                # อาจดึงไปแล้ว — เปิดใบเรียกเก็บ
                open_bill = row.locator("button, a").filter(has_text="เปิดใบเรียกเก็บ")
                if await open_bill.count():
                    await open_bill.first.click()
                    await page.wait_for_timeout(2000)

            await page.locator(".o_form_view").first.wait_for(state="visible", timeout=30000)
            await shot(page, "06_bill_draft.png")

            # เลื่อนไปบรรทัด
            lines = page.locator('.o_notebook, .o_field_x2many, [name="invoice_line_ids"]')
            if await lines.count():
                await lines.first.scroll_into_view_if_needed()
            await shot(page, "07_bill_lines.png")

            # ใส่เลขอ้างอิงใบแจ้งหนี้ถ้าว่าง
            ref = page.locator('input[name="ref"], .o_field_widget[name="ref"] input')
            if await ref.count():
                val = await ref.first.input_value()
                if not (val or "").strip():
                    await ref.first.fill("INV-DEMO-0786")
                    await page.wait_for_timeout(300)

            # เลือก WHT 1% บนบรรทัด
            wht_cell = page.locator(
                '.o_field_widget[name="wht_tax_id"], '
                'td[name="wht_tax_id"], '
                '.o_list_table td:has(.o_field_many2one[name="wht_tax_id"])'
            )
            if not await wht_cell.count():
                # ลองคลิกเซลล์หัวคอลัมน์ WHT ในแถวแรกของ invoice lines
                wht_cell = page.locator("td").filter(has_text="WHT").locator("xpath=..")
            # เปิด many2one ในแถวสินค้า
            m2o = page.locator('.o_field_many2one[name="wht_tax_id"] input, input[id*="wht_tax"]')
            if not await m2o.count():
                # คลิกแถวแล้วหา cell
                first_line = page.locator(
                    '.o_field_x2many_list[name="invoice_line_ids"] tbody tr.o_data_row, '
                    '[name="invoice_line_ids"] tbody tr.o_data_row'
                )
                if await first_line.count():
                    # หา cell ตาม column header WHT
                    headers = page.locator(
                        '[name="invoice_line_ids"] thead th, '
                        '.o_list_table thead th'
                    )
                    wht_idx = None
                    count = await headers.count()
                    for i in range(count):
                        txt = (await headers.nth(i).inner_text()).strip()
                        if txt.upper() == "WHT" or "WHT" in txt.upper():
                            wht_idx = i
                            break
                    if wht_idx is not None:
                        cell = first_line.first.locator("td").nth(wht_idx)
                        await cell.click()
                        await page.wait_for_timeout(400)
                        m2o = page.locator(
                            '.o_field_many2one[name="wht_tax_id"] input, '
                            'td.o_selected_row input, '
                            '.o_field_widget[name="wht_tax_id"] input'
                        )

            if await m2o.count():
                await m2o.first.click()
                await m2o.first.fill(WHT_LABEL)
                await page.wait_for_timeout(800)
                opt = page.locator(".o-autocomplete--dropdown-item, .ui-menu-item, a.dropdown-item").filter(
                    has_text="WHT 1% ซื้อสินค้า"
                )
                if await opt.count():
                    await opt.first.click()
                else:
                    await page.keyboard.press("Enter")
                await page.wait_for_timeout(800)
            else:
                print("WARN: wht field not found in UI; will set via RPC after save attempt")

            await shot(page, "08_bill_wht_1pct.png")

            # บันทึกถ้ามีปุ่ม
            save = page.locator("button").filter(has_text="บันทึก")
            if await save.count() and await save.first.is_visible():
                await save.first.click()
                await page.wait_for_timeout(1000)

            # ลงรายการ (POST)
            post = page.locator("button").filter(has_text="ลงรายการ")
            if await post.count() and await post.first.is_visible():
                await post.first.click()
                await page.wait_for_timeout(2500)
                # confirm wizard ถ้ามี
                confirm = page.locator(".modal-footer button.btn-primary, .modal button").filter(
                    has_text="ลงรายการ"
                )
                if await confirm.count():
                    await confirm.first.click()
                    await page.wait_for_timeout(2000)
            await shot(page, "09_bill_posted.png")

            # กลับ Dashboard แล้วส่งการเงิน
            await open_ap_dashboard(page)
            # การ์ดรอส่งการเงิน
            kpi = page.locator("button.o_vpk_ap_kpi, .o_vpk_ap_kpi").filter(has_text="รอส่งการเงิน")
            if await kpi.count():
                await kpi.first.click()
                await page.wait_for_timeout(800)
            row = await find_row(page)
            await shot(page, "10_dashboard_to_finance.png")
            send = row.locator("button").filter(has_text="ส่งการเงิน")
            if await send.count() and await send.first.is_enabled():
                await send.first.click()
                await page.wait_for_timeout(2000)
            # การ์ดส่งการเงินแล้ว
            kpi2 = page.locator("button.o_vpk_ap_kpi, .o_vpk_ap_kpi").filter(has_text="ส่งการเงินแล้ว")
            if await kpi2.count():
                await kpi2.first.click()
                await page.wait_for_timeout(800)
            try:
                row = await find_row(page)
            except Exception:
                pass
            await shot(page, "11_dashboard_sent.png")

            print("DONE")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
