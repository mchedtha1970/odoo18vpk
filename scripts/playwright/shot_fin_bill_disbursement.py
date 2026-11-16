#!/usr/bin/env python3
"""จับภาพ: ใบเรียกเก็บรอทำจ่าย → ตรวจรายการบนใบ → กดขออนุมัติเบิกจ่าย → ใบขอเบิกเงิน"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/fin_dashboard_pay")
USER = "uat.gfmis"
BILL_ID = 965


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(400)
    await page.screenshot(path=str(path), full_page=False)
    print("SHOT", path)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(60000)
        try:
            await login_as(page, USER)

            await page.goto(
                f"{BASE_URL}/odoo/action-1094",
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(1500)
            await shot(page, "03_finance_dashboard.png")

            await page.goto(
                f"{BASE_URL}/odoo/account.move/{BILL_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for(state="visible", timeout=30000)
            await page.wait_for_timeout(1200)

            # หัวใบเรียกเก็บ + ปุ่มขออนุมัติเบิกจ่าย
            await shot(page, "05_bill_form.png")
            await shot(page, "05b_bill_header_actions.png")

            # แท็บรายการใบแจ้งหนี้ + ยอดท้ายใบ
            lines_tab = page.locator(".o_notebook_headers a, .nav-link").filter(
                has_text="รายการใบแจ้งหนี้"
            )
            if await lines_tab.count():
                await lines_tab.first.click()
                await page.wait_for_timeout(600)
            # เลื่อนให้เห็นบรรทัดสินค้า + ยอดรวม
            await page.evaluate(
                """() => {
                  const el = document.querySelector('.o_list_table, .o_field_x2many_list, .o_notebook');
                  if (el) el.scrollIntoView({block:'center'});
                }"""
            )
            await page.wait_for_timeout(400)
            await shot(page, "05c_bill_lines.png")

            # กดขออนุมัติเบิกจ่าย → สร้าง/เปิดใบขอเบิกเงิน
            btn_create = page.locator("button").filter(has_text="ขออนุมัติเบิกจ่าย")
            btn_open = page.locator("button.oe_stat_button, button").filter(
                has_text="ใบขอเบิกเงิน"
            )
            if await btn_create.count() and await btn_create.first.is_visible():
                await btn_create.first.click()
            elif await btn_open.count():
                await btn_open.first.click()
            else:
                raise RuntimeError("ไม่พบปุ่มขออนุมัติเบิกจ่าย / ใบขอเบิกเงิน")

            await page.wait_for_timeout(2000)
            await page.locator(".o_form_view").first.wait_for(state="visible", timeout=30000)
            # รอชื่อ KB หรือ ขบ.01
            await page.wait_for_timeout(800)
            await shot(page, "06_disbursement_form.png")

            # เลื่อนไปส่วนจำนวนเงิน
            await page.evaluate(
                """() => {
                  const t = Array.from(document.querySelectorAll('label,span,th,td'))
                    .find(e => (e.textContent||'').includes('จำนวนเงินขอเบิก'));
                  if (t) t.scrollIntoView({block:'center'});
                }"""
            )
            await page.wait_for_timeout(400)
            await shot(page, "07_disbursement_amounts.png")

            # บันทึก template ถ้ายังไม่กด
            excel_btn = page.locator("button").filter(
                has_text="บันทึกข้อมูลเข้า template Excel"
            )
            if await excel_btn.count() and await excel_btn.first.is_visible():
                await excel_btn.first.click()
                await page.wait_for_timeout(2500)
            await shot(page, "08_after_generate_excel.png")

            print("DONE")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
