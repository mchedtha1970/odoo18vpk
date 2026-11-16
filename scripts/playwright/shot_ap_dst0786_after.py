#!/usr/bin/env python3
"""จับภาพหลัง POST/ส่งการเงิน ของ DST/2026/0786"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/ap_dst0786")
USER = "uat.gfmis"
DOC_NAME = "DST/2026/0786"
BILL_ID = 969


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(500)
    await page.screenshot(path=str(path), full_page=False)
    print("SHOT", path)


async def open_ap_dashboard(page):
    await page.goto(f"{BASE_URL}/odoo/action-1093", wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    await page.locator("text=งานเจ้าหนี้: รายการขอเบิกจ่ายจากจัดซื้อ").first.wait_for(
        state="visible", timeout=30000
    )


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(60000)
        try:
            await login_as(page, USER)

            # ใบเรียกเก็บที่ POST แล้ว + WHT
            await page.goto(
                f"{BASE_URL}/odoo/account.move/{BILL_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for(state="visible")
            await page.wait_for_timeout(1000)
            await shot(page, "09_bill_posted.png")

            # เลื่อนดูบรรทัด WHT
            lines = page.locator('[name="invoice_line_ids"], .o_notebook')
            if await lines.count():
                await lines.first.scroll_into_view_if_needed()
            await shot(page, "08b_bill_wht_posted.png")

            # แท็บใบกำกับภาษี ถ้ามี
            for label in ("ใบกำกับภาษี", "Tax Invoice", "ภาษี"):
                tab = page.get_by_role("tab", name=label)
                if await tab.count():
                    await tab.first.click()
                    await page.wait_for_timeout(600)
                    await shot(page, "08c_tax_invoice_tab.png")
                    break

            await open_ap_dashboard(page)
            search = page.locator('input[placeholder*="ค้นหา"]')
            if await search.count():
                await search.first.fill(DOC_NAME)
                await page.wait_for_timeout(600)

            # การ์ดส่งการเงินแล้ว
            kpi = page.locator("button.o_vpk_ap_kpi, .o_vpk_ap_kpi").filter(
                has_text="ส่งการเงินแล้ว"
            )
            if await kpi.count():
                await kpi.first.click()
                await page.wait_for_timeout(800)
            await shot(page, "11_dashboard_sent.png")

            # การ์ดทั้งหมด / draft สำหรับอ้างอิง
            kpi_all = page.locator("button.o_vpk_ap_kpi, .o_vpk_ap_kpi").filter(
                has_text="ตั้งเจ้าหนี้ (Draft)"
            )
            if await kpi_all.count():
                await kpi_all.first.click()
                await page.wait_for_timeout(500)
                await shot(page, "10_dashboard_draft_empty.png")

            print("DONE")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
