"""จับภาพเอกสาร e-GP เต็มหน้า สำหรับขั้นตอนที่ 13"""
import asyncio
from pathlib import Path

from odoo_session import BASE_URL, launch_browser, login_as, wait_for_server

EGP_ID = 82
OUT = Path(__file__).resolve().parents[2] / "docs/manual_assets/figures/pr6911013"


async def main():
    wait_for_server()
    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await launch_browser(p, headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1400}, locale="th-TH"
        )
        page = await context.new_page()
        await login_as(page, "uat.material")
        await page.goto(
            f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
            wait_until="domcontentloaded",
        )
        await page.wait_for_selector(".o_form_view", timeout=30000)
        await page.wait_for_timeout(1500)

        # เต็มหน้าจอฟอร์มเอกสาร e-GP
        await page.screenshot(
            path=str(OUT / "40b_egp_full_page.png"), full_page=False
        )
        # เฉพาะพื้นที่ฟอร์ม (ตัดเมนูข้างถ้าเป็นไปได้)
        form = page.locator(".o_content, .o_form_view").first
        await form.screenshot(path=str(OUT / "40c_egp_form_full.png"))

        # scroll ลงดูรายการสินค้าแล้วจับอีกใบ
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(600)
        await page.screenshot(path=str(OUT / "40d_egp_full_scrolled.png"))

        await browser.close()
        print("saved:", list(OUT.glob("40*.png")))


if __name__ == "__main__":
    asyncio.run(main())
