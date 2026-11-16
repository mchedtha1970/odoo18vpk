"""จับภาพบทที่ 2 มุมมองกลุ่มครุภัณฑ์ (uat.equipment) หลังอัปเดต theme"""
import asyncio
from pathlib import Path

from odoo_session import BASE_URL, launch_browser, login_as, wait_for_server

OUT = Path(__file__).resolve().parents[2] / "docs/manual_assets/figures/cctv16_specific"
PR_ID = 178
EGP_ID = 83
CTR_ID = 318
PO_ID = 136
WA_ID = 73
PICK_ID = 225
PLAN_ID = 14


async def shot(page, name: str, full=False):
    path = OUT / name
    await page.wait_for_timeout(800)
    if full:
        await page.screenshot(path=str(path), full_page=False)
    else:
        target = page.locator(".o_form_view, .o_content").first
        if await target.count():
            await target.screenshot(path=str(path))
        else:
            await page.screenshot(path=str(path))
    print("saved", name)


async def goto(page, model_path: str):
    await page.goto(f"{BASE_URL}/odoo/{model_path}", wait_until="domcontentloaded")
    await page.wait_for_selector(".o_form_view, .o_list_view, .o_kanban_view", timeout=30000)
    await page.wait_for_timeout(1000)


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

        # PR ที่มอบหมายแล้ว — ปุ่มยืนยันการตรวจสอบ
        await goto(page, f"purchase.request/{PR_ID}")
        await shot(page, "10_pr_assigned.png", full=True)

        # EGP หลังมีแผน (สถานะปัจจุบัน)
        await goto(page, f"purchase.requisition/{EGP_ID}")
        await shot(page, "14_egp_form.png", full=True)
        await shot(page, "16_egp_with_plan.png", full=True)
        plan_field = page.locator(".o_field_widget[name='ebidding_plan_line_id']")
        if await plan_field.count():
            await plan_field.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
            await plan_field.first.screenshot(path=str(OUT / "16b_egp_plan_field.png"))

        # ผู้ชนะ
        tab = page.locator(".nav-link").filter(has_text="ผู้เสนอราคา")
        if await tab.count():
            await tab.first.click()
            await page.wait_for_timeout(800)
            await shot(page, "21_winner.png", full=True)

        # สัญญา
        await goto(page, f"purchase.contract/{CTR_ID}")
        await shot(page, "25_contract_confirmed.png", full=True)

        # PO
        await goto(page, f"purchase.order/{PO_ID}")
        await shot(page, "34_po_from_same_pr.png", full=True)
        await shot(page, "37_po_confirmed.png", full=True)

        # WA
        await goto(page, f"work.acceptance/{WA_ID}")
        await shot(page, "38_work_acceptance.png", full=True)

        # ใบรับคลัง
        await goto(page, f"stock.picking/{PICK_ID}")
        await shot(page, "36_wh_in.png", full=True)

        # เอกสารแผน
        await goto(page, f"ebidding.plan.line/{PLAN_ID}")
        await shot(page, "17_plan_document.png", full=True)

        await browser.close()
        print("equipment theme shots done")


if __name__ == "__main__":
    asyncio.run(main())
