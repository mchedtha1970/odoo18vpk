"""จับภาพปุ่มสร้างแผน / เอกสารแผน บน EGP เฉพาะเจาะจง >500k"""
import asyncio
from pathlib import Path

from odoo_session import BASE_URL, launch_browser, login_as, wait_for_server

EGP_ID = 83
OUT = Path(__file__).resolve().parents[2] / "docs/manual_assets/figures/cctv16_specific"


async def main():
    wait_for_server()
    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await launch_browser(p, headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1200}, locale="th-TH"
        )
        page = await context.new_page()
        await login_as(page, "uat.equipment")
        await page.goto(
            f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
            wait_until="domcontentloaded",
        )
        await page.wait_for_selector(".o_form_view", timeout=30000)
        await page.wait_for_timeout(1500)
        await page.screenshot(path=str(OUT / "16_egp_with_plan.png"), full_page=False)
        # โฟกัสช่องเอกสารแผน
        plan_field = page.locator(".o_field_widget[name='ebidding_plan_line_id'], label:has-text('เอกสารแผน')").first
        if await plan_field.count():
            await plan_field.scroll_into_view_if_needed()
            await page.wait_for_timeout(400)
        sheet = page.locator(".o_form_sheet, .o_form_view").first
        await sheet.screenshot(path=str(OUT / "16b_egp_plan_field.png"))
        # เปิดเอกสารแผน
        open_btn = page.locator("button").filter(has_text="เปิดเอกสารแผน")
        if await open_btn.count():
            await open_btn.first.click()
            await page.wait_for_timeout(1500)
            await page.screenshot(path=str(OUT / "17_plan_document.png"), full_page=False)
        await browser.close()
        print("saved", sorted(OUT.glob("16*.png")), sorted(OUT.glob("17*.png")))


if __name__ == "__main__":
    asyncio.run(main())
