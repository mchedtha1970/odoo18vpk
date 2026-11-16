#!/usr/bin/env python3
"""จับภาพ flow งานการเงิน: Dashboard รอทำจ่าย → ใบเรียกเก็บ → ใบขอเบิกเงิน"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/fin_dashboard_pay")
USER = "uat.gfmis"
DOC_NAME = "DST/2026/0735"
BILL_ID = 965
FORM_NAME = "KB/2026/0008"


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(500)
    await page.screenshot(path=str(path), full_page=False)
    print("SHOT", path)


async def open_finance_dashboard(page):
    await page.goto(f"{BASE_URL}/odoo/action-1094", wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    head = page.locator("text=งานการเงิน")
    # title may vary - wait for KPI or table
    await page.wait_for_timeout(800)
    kpi = page.locator("text=รอทำจ่าย")
    await kpi.first.wait_for(state="visible", timeout=30000)


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(60000)
        try:
            await login_as(page, USER)
            await shot(page, "01_home_after_login.png")

            # เมนูระบบการเงิน
            await page.goto(f"{BASE_URL}/odoo/accounting", wait_until="domcontentloaded")
            await page.wait_for_timeout(1200)
            await shot(page, "02_accounting_sidebar.png")

            await open_finance_dashboard(page)
            await shot(page, "03_finance_dashboard.png")

            # ค้นหาแถวตัวอย่าง
            search = page.locator('input[placeholder*="ค้นหา"]')
            if await search.count():
                await search.first.fill(DOC_NAME)
                await page.wait_for_timeout(700)
            await shot(page, "04_queue_to_finance.png")

            # เปิดใบเรียกเก็บ
            bill_link = page.locator("a").filter(has_text="BILL/2026/11/0003")
            if await bill_link.count():
                await bill_link.first.click()
            else:
                await page.goto(
                    f"{BASE_URL}/odoo/account.move/{BILL_ID}",
                    wait_until="domcontentloaded",
                )
            await page.locator(".o_form_view").first.wait_for(state="visible", timeout=30000)
            await page.wait_for_timeout(1000)
            await shot(page, "05_bill_from_queue.png")

            # ปุ่มขออนุมัติเบิกจ่าย หรือ smart ใบขอเบิกเงิน
            btn_open = page.locator("button").filter(has_text="ใบขอเบิกเงิน")
            btn_create = page.locator("button").filter(has_text="ขออนุมัติเบิกจ่าย")
            if await btn_open.count() and await btn_open.first.is_visible():
                await btn_open.first.click()
            elif await btn_create.count() and await btn_create.first.is_visible():
                await btn_create.first.click()
            else:
                # เปิดจากเมนู
                await page.goto(
                    f"{BASE_URL}/odoo/action-{env_action_id()}",
                    wait_until="domcontentloaded",
                )
            await page.wait_for_timeout(1500)
            # ถ้ายังไม่ใช่ฟอร์มใบขอเบิก หาจากชื่อ
            if not await page.locator("text=ใบขอเบิกเงิน").count():
                # search form by name via URL from DB later - try list menu
                pass
            form = page.locator(".o_form_view")
            if await form.count():
                await form.first.wait_for(state="visible", timeout=20000)
            await shot(page, "06_disbursement_form.png")

            # เมนูใบขอเบิกเงิน
            act = await page.evaluate(
                """async () => {
                const r = await fetch('/web/dataset/call_kw/ir.model.data/check_object_reference', {
                  method:'POST', headers:{'Content-Type':'application/json'},
                  body: JSON.stringify({jsonrpc:'2.0', method:'call', params:{model:'ir.model.data', method:'check_object_reference', args:['vpk_disbursement_form','action_vpk_disbursement_form'], kwargs:{}}, id:1})
                });
                return r.json();
            }"""
            )
            # fallback: open by searching
            await page.goto(f"{BASE_URL}/odoo", wait_until="domcontentloaded")
            await page.wait_for_timeout(800)
            # direct action search via shell was  - use name URL pattern
            # get action id from previous knowledge / rpc in page
            action_id = await page.evaluate(
                """async () => {
                  const csrf = document.querySelector('meta') ;
                  const res = await odoo.__WOWL_DEBUG__?.services?.orm?.call?.(
                    'ir.model.data','check_object_reference',['vpk_disbursement_form','action_vpk_disbursement_form']
                  ).catch(()=>null);
                  return res;
                }"""
            )
            print("action_id via owl", action_id)

            # open form by name search in backend URL using known form id from DB
            # We'll set FORM_ID after shell lookup - use browse via /web# 
            await page.goto(
                f"{BASE_URL}/web#action=&model=vpk.disbursement.form&view_type=list",
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(1200)
            # better: use odoo 18 path - get from shell after
        finally:
            # always capture menu list via known approach below
            await browser.close()


def env_action_id():
    return 0


if __name__ == "__main__":
    asyncio.run(main())
