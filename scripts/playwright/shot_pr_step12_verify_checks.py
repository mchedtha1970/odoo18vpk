"""จับภาพขั้นตอนที่ 12: ผู้รับมอบงานตรวจคณะกรรมการและเอกสารขออนุมัติก่อนยืนยัน"""
import asyncio
from pathlib import Path

from odoo_session import BASE_URL, launch_browser, login_as, wait_for_server

PR_ID = 176
OUT = Path(__file__).resolve().parents[2] / "docs/manual_assets/figures/pr6911013"


async def click_tab(page, name: str):
    tab = page.locator(".o_notebook_headers .nav-link, .o_notebook .nav-link").filter(
        has_text=name
    )
    await tab.first.click()
    await page.wait_for_timeout(800)


async def main():
    wait_for_server()
    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await launch_browser(p, headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1100}, locale="th-TH"
        )
        page = await context.new_page()
        await login_as(page, "uat.material")
        await page.goto(
            f"{BASE_URL}/odoo/purchase.request/{PR_ID}",
            wait_until="domcontentloaded",
        )
        await page.wait_for_selector(".o_form_view", timeout=30000)
        await page.wait_for_timeout(1200)

        # หัวเอกสาร (บริบทก่อนตรวจ)
        header = page.locator(".o_form_view .o_form_statusbar, .o_control_panel").first
        await page.locator(".o_form_view").screenshot(path=str(OUT / "36c_verify_header.png"))

        # แท็บคณะกรรมการ — ตรวจชื่อและสถานะยินยอม
        await click_tab(page, "คณะกรรมการ")
        await page.wait_for_timeout(500)
        committee_block = page.locator(".o_notebook_content, .tab-content").first
        await committee_block.screenshot(path=str(OUT / "36a_verify_committee.png"))

        # แท็บเอกสารที่เกี่ยวข้อง — ตรวจเอกสารขออนุมัติอนุมัติแล้ว
        for label in ("เอกสารที่เกี่ยวข้อง", "เอกสาร", "เอกสารอ้างอิง"):
            tabs = page.locator(".o_notebook_headers .nav-link, .o_notebook .nav-link").filter(
                has_text=label
            )
            if await tabs.count():
                await tabs.first.click()
                await page.wait_for_timeout(800)
                break
        docs_block = page.locator(".o_notebook_content, .tab-content").first
        await docs_block.screenshot(path=str(OUT / "36b_verify_approval_doc.png"))

        # เปิดเอกสาร DST ถ้ามีปุ่มเปิด
        open_btn = page.locator("a,button").filter(has_text="เปิด")
        if await open_btn.count():
            await open_btn.first.click()
            await page.wait_for_timeout(1500)
            # อาจเป็น dialog หรือเปิดฟอร์มเอกสาร
            form = page.locator(".o_dialog .o_form_view, .o_form_view").first
            await form.screenshot(path=str(OUT / "36d_verify_approval_open.png"))
            # ปิด dialog ถ้ามี
            close = page.locator(".o_dialog .btn-close, .modal .btn-close, button:has-text('ปิด')")
            if await close.count():
                await close.first.click()
                await page.wait_for_timeout(400)

        await browser.close()
        print("saved:", sorted(OUT.glob("36*.png")))


if __name__ == "__main__":
    asyncio.run(main())
