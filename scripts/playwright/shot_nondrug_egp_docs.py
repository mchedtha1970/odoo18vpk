#!/usr/bin/env python3
"""จับภาพแท็บเอกสาร e-GP + เพิ่มเอกสาร/ส่งลงนาม บน EGP/2026/0162 สำหรับบทที่ 3 ข้อ 7"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/nondrug_specific_le500k")
EGP_ID = 85
USER = "uat.material"


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(500)
    await page.screenshot(path=str(path))
    print("SHOT", path)
    return path


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        try:
            await login_as(page, USER)
            await page.goto(
                f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "16_egp_overview.png")

            # แท็บเอกสาร
            for label in (
                "เอกสารที่เปิดในระบบ e-GP",
                "เอกสาร e-GP",
                "เอกสาร",
            ):
                tab = page.get_by_role("tab", name=label)
                if await tab.count():
                    await tab.first.click()
                    await page.wait_for_timeout(600)
                    print("opened tab", label)
                    break
            else:
                # fallback: click any nav-link containing เอกสาร
                link = page.locator(".nav-link").filter(has_text="เอกสาร")
                if await link.count():
                    await link.first.click()
                    await page.wait_for_timeout(600)

            await shot(page, "17_egp_docs_tab.png")

            # ปุ่มเพิ่มเอกสาร
            add = page.locator(
                'button:has-text("เพิ่มเอกสาร"), .o_field_x2many_list_row_add a'
            )
            if await add.count() and await add.first.is_visible():
                await add.first.click()
                await page.wait_for_timeout(800)
                modal = page.locator(".modal-content").last
                if await modal.count():
                    await modal.wait_for(state="visible", timeout=10000)
                    await shot(page, "18_add_doc_modal.png")
                    # ปิด modal
                    cancel = modal.locator(
                        "button:has-text('ยกเลิก'), button:has-text('ปิด'), button.btn-secondary"
                    )
                    if await cancel.count():
                        await cancel.first.click()
                    else:
                        await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)

            # ปุ่มเพิ่มผู้อนุมัติ / ส่งเพื่อลงนาม ถ้ามี
            for label in ("เพิ่มผู้อนุมัติ", "ส่งเพื่อลงนาม", "ส่งอนุมัติ"):
                btn = page.get_by_role("button", name=label)
                if await btn.count() and await btn.first.is_visible():
                    await btn.first.scroll_into_view_if_needed()
                    await shot(page, "19_send_sign_btn.png")
                    print("found", label)
                    break

            # แถวเอกสารและสถานะลงนาม
            docs = page.locator(
                '.o_field_widget[name="egp_document_ids"], '
                '.o_notebook_content .o_list_table'
            )
            if await docs.count():
                await docs.first.scroll_into_view_if_needed()
                await shot(page, "20_egp_docs_signed.png")

            await shot(page, "17b_egp_docs_full.png")
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
