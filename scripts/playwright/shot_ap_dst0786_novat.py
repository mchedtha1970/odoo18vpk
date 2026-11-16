#!/usr/bin/env python3
"""จับภาพใบเรียกเก็บ DST/2026/0786 แบบไม่มี VAT (ภาษีซื้อ)"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/ap_dst0786")
USER = "uat.gfmis"
BILL_ID = 969
DOC_NAME = "DST/2026/0786"


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(500)
    await page.screenshot(path=str(path), full_page=False)
    print("SHOT", path)


async def open_bill(page):
    await page.goto(
        f"{BASE_URL}/odoo/account.move/{BILL_ID}",
        wait_until="domcontentloaded",
    )
    await page.locator(".o_form_view").first.wait_for(state="visible", timeout=30000)
    await page.wait_for_timeout(800)


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
            await open_bill(page)
            await shot(page, "06_bill_draft.png")

            lines = page.locator('[name="invoice_line_ids"], .o_notebook')
            if await lines.count():
                await lines.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
            await shot(page, "07_bill_lines.png")
            await shot(page, "08_bill_wht_1pct.png")

            # แท็บใบกำกับภาษี ถ้ามี
            for label in ("ใบกำกับภาษี", "Tax Invoice"):
                tab = page.get_by_role("tab", name=label)
                if await tab.count():
                    await tab.first.click()
                    await page.wait_for_timeout(700)
                    await shot(page, "08c_tax_invoice_tab.png")
                    break
            else:
                # ไม่มีแท็บเมื่อไม่มี VAT — ใช้ภาพบรรทัดแทนชั่วคราวได้
                print("WARN: no tax invoice tab (expected without VAT)")

            print("DRAFT shots done — post via shell then re-run posted shots")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
