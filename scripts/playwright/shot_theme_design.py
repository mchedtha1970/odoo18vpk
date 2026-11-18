"""จับภาพประกอบเอกสารออกแบบธีม (vpk_sidebar_menu / vpk_login_page)

ภาพ Theme Settings ต้องใช้บัญชี System Administrator (ODOO_ADMIN_LOGIN / ODOO_ADMIN_PASSWORD)
เปิด panel เพื่อถ่ายภาพเท่านั้น ไม่กด Apply จึงไม่เปลี่ยนธีมกลาง
"""
import asyncio
import os
from pathlib import Path

from odoo_session import BASE_URL, launch_browser, submit_login, wait_for_server

OUT = Path(__file__).resolve().parents[2] / "docs/manual_assets/figures/theme"
DB = os.environ.get("ODOO_DB", "VPK-S1")
USER = "uat.procurement"
ADMIN_LOGIN = os.environ.get("ODOO_ADMIN_LOGIN", "").strip()
ADMIN_PASSWORD = os.environ.get("ODOO_ADMIN_PASSWORD", "").strip()


async def wait_for_theme_fonts(page):
    try:
        await page.wait_for_function(
            """() => [...document.styleSheets].some(
                (s) => s.href && s.href.includes('fonts.googleapis.com'))""",
            timeout=15000,
        )
        await page.evaluate(
            """() => Promise.all([
                document.fonts.load("13px 'Noto Sans Thai'", 'กขค'),
                document.fonts.load("600 13px 'Noto Sans Thai'", 'กขค'),
                document.fonts.load("13px 'Inter'", 'Abc123'),
                document.fonts.load("600 13px 'Inter'", 'Abc123'),
            ]).then(() => document.fonts.ready)"""
        )
    except Exception:
        print("warn: theme fonts not loaded, screenshot uses fallback font")


async def save(page, name, locator=None):
    await wait_for_theme_fonts(page)
    await page.wait_for_timeout(800)
    path = OUT / name
    if locator is not None and await locator.count():
        await locator.first.screenshot(path=str(path))
    else:
        await page.screenshot(path=str(path))
    print("saved", name)


async def goto(page, path, selector=".o_form_view, .o_list_view, .o_kanban_view"):
    await page.goto(f"{BASE_URL}/odoo/{path}", wait_until="domcontentloaded")
    await page.wait_for_selector(selector, timeout=30000)
    await page.wait_for_timeout(1200)


async def open_theme_tab(page, label):
    await page.locator(".o_vpk_theme_tab", has_text=label).click()
    await page.wait_for_timeout(400)


async def main():
    wait_for_server()
    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await launch_browser(p, headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900}, locale="th-TH"
        )
        page = await context.new_page()

        await page.goto(f"{BASE_URL}/web/session/logout?db={DB}", wait_until="domcontentloaded")
        await page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="load")
        await page.locator(".vpk-login-page").wait_for(state="visible")
        await save(page, "01_login.png")

        await submit_login(page, USER)
        await goto(page, "action-purchase_request.purchase_request_form_action")
        await save(page, "02_sidebar_list.png")
        await save(page, "03_sidebar_detail.png", page.locator(".o_vpk_sidebar_primary"))

        first_row = page.locator(".o_data_row").first
        if await first_row.count():
            await first_row.click()
            await page.wait_for_selector(".o_form_view .o_form_sheet", timeout=30000)
            await page.wait_for_timeout(1500)
            await save(page, "04_form_view.png")

        await page.locator(".o_vpk_collapse_btn").click()
        await page.wait_for_timeout(800)
        await save(page, "05_sidebar_collapsed.png")
        await page.locator(".o_vpk_collapse_btn").click()

        await page.locator(".o_vpk_sidebar_search").click()
        await page.wait_for_selector(".o_command_palette", timeout=15000)
        await page.keyboard.type("ใบ")
        await page.wait_for_timeout(1200)
        await save(page, "09_command_palette.png")
        await page.keyboard.press("Escape")

        if not (ADMIN_LOGIN and ADMIN_PASSWORD):
            print("skip Theme Settings shots: set ODOO_ADMIN_LOGIN and ODOO_ADMIN_PASSWORD")
            await browser.close()
            return

        await page.goto(f"{BASE_URL}/web/session/logout?db={DB}", wait_until="domcontentloaded")
        await page.goto(f"{BASE_URL}/web/login?db={DB}", wait_until="load")
        await submit_login(page, ADMIN_LOGIN, ADMIN_PASSWORD)
        await page.wait_for_selector(".o_vpk_sidebar_primary", timeout=60000)
        await page.locator(".o_vpk_systray_item.theme_selector a").click()
        await page.wait_for_selector(".o_vpk_theme_panel .o_vpk_section_title", timeout=15000)
        panel = page.locator(".o_vpk_theme_panel")
        await save(page, "06_theme_general.png", panel)
        await open_theme_tab(page, "Colors")
        await save(page, "07_theme_colors.png", panel)
        await open_theme_tab(page, "Sidebar Size")
        await save(page, "08_theme_sidebar_size.png", panel)
        await page.locator(".o_vpk_btn_discard").click()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
