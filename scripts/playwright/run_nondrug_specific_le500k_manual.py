#!/usr/bin/env python3
"""UAT บทที่ 3: เวชภัณฑ์มิใช่ยา วิธีเฉพาะเจาะจง มูลค่าไม่เกิน 500,000 บาท

user หน่วยงาน (uat.dept) → ส่งจัดซื้อ → มอบหมายกลุ่มวัสดุ → e-GP
(ไม่บังคับสร้างแผนเพราะ ≤500k) → ผู้ชนะ Vendor DEMO → สร้าง PO จากแฟ้มเดิม
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_medicine_purchase_request import (  # noqa: E402
    check_budget,
    complete_document,
    ensure_m2o,
    fill_m2o,
    fill_selection,
    open_record,
    save_form,
)
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/nondrug_specific_le500k")
META = OUT / "meta.json"
USER = "uat.dept"
PROC_BOSS = "uat.procurement"
PROC_OWNER = "uat.material"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
PRODUCT_CODE = "20300057"
BUDGET = "DBR/2570/0027"
VENDOR = "Vendor DEMO"
AMOUNT_QTY = "10000"  # 10,000 x 6 = 60,000 < 500k

DOC_APPROVAL = {
    "label": "บันทึกข้อความอนุมัติขอซื้อ",
    "owner": USER,
    "signers": [
        {"login": "uat.dept", "name": "ผู้ทดสอบหน่วยงาน"},
        {"login": "uat.head_officer", "name": "ผู้ทดสอบหัวหน้าเจ้าหน้าที่"},
        {"login": "uat.director", "name": "ผู้ทดสอบผู้อำนวยการโรงพยาบาล"},
    ],
}
DOC_COMMITTEE = {
    "label": "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ",
    "owner": PROC_OWNER,
    "signers": [{"login": "uat.director", "name": "ผู้ทดสอบผู้อำนวยการโรงพยาบาล"}],
}
DOC_SPECIFIC = {
    "label": "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
    "owner": PROC_OWNER,
    "signers": [
        {"login": "uat.officer", "name": "ผู้ทดสอบเจ้าหน้าที่"},
        {"login": "uat.head_officer", "name": "ผู้ทดสอบหัวหน้าเจ้าหน้าที่"},
        {"login": "uat.director", "name": "ผู้ทดสอบผู้อำนวยการโรงพยาบาล"},
    ],
}


async def shot(page, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    await page.wait_for_timeout(500)
    await page.screenshot(path=str(path))
    print("SHOT", path)
    return path


async def rpc(page, model, method, args, kwargs=None):
    return await page.evaluate(
        """async ({model, method, args, kwargs}) => {
            const res = await fetch('/web/dataset/call_kw/' + model + '/' + method, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    jsonrpc: '2.0', method: 'call',
                    params: {model, method, args, kwargs},
                }),
            });
            return await res.json();
        }""",
        {"model": model, "method": method, "args": args, "kwargs": kwargs or {}},
    )


async def add_wa_committees_via_rpc(page, pr_id: int):
    # ใส่กรรมการตรวจรับ 3 คนผ่าน RPC ให้ครบตามระเบียบ ≤500k
    employees = [
        (19, "chairman"),
        (20, "committee"),
        (21, "secretary"),
    ]
    for emp_id, role in employees:
        emp = await rpc(page, "hr.employee", "read", [[emp_id], ["name"]])
        name = emp["result"][0]["name"] if emp.get("result") else str(emp_id)
        await rpc(
            page,
            "procurement.committee",
            "create",
            [
                {
                    "request_id": pr_id,
                    "employee_id": emp_id,
                    "name": name,
                    "committee_type": "work_acceptance",
                    "approve_role": role,
                }
            ],
        )
    print("committees via rpc ok")


async def create_pr(page):
    await login_as(page, USER)
    await shot(page, "00_login.png")
    await page.goto(f"{BASE_URL}/odoo/action-577", wait_until="domcontentloaded")
    await page.locator(".o_list_button_add, .o_form_button_create, button:has-text('สร้าง')").first.click()
    await page.locator(".o_form_view").wait_for(state="visible")
    await shot(page, "01a_pr_list_new.png")

    await fill_m2o(page, "procurement_type_id", "ซื้อ/จ้าง/เช่า", "ซื้อ/จ้าง/เช่า")
    await fill_m2o(
        page, "purchase_type_id", "จัดซื้อจัดจ้างผ่านพัสดุ", "จัดซื้อจัดจ้างผ่านพัสดุ"
    )
    await fill_m2o(page, "procurement_method_id", "เฉพาะเจาะจง", "เฉพาะเจาะจง")
    await fill_selection(page, "procurement_nature", "ซื้อ")
    await fill_selection(page, "procurement_document", "ใบสั่งซื้อ/ใบสั่งจ้าง")
    await fill_selection(page, "budget_section_key", "วัสดุ")
    await page.locator('.o_field_widget[name="budget_group_id"]').wait_for(
        state="visible", timeout=10000
    )
    await fill_m2o(page, "budget_group_id", "เวชภัณฑ์มิใช่ยา", "เวชภัณฑ์มิใช่ยา")
    await fill_m2o(page, "budget_plan_request_id", BUDGET, BUDGET, exact=False)
    await fill_m2o(page, "budget_analytic_account_id", "UAT-DEPT", "UAT-DEPT", exact=False)
    await fill_m2o(page, "budget_fund_source_id", "เงินบำรุง", "เงินบำรุง")
    # หมวดงบจากสาย DBR (เวชภัณฑ์ทั่วไป)
    post = page.locator('.o_field_widget[name="budget_post_id"]')
    if await post.count() and await post.first.is_visible():
        await fill_m2o(
            page,
            "budget_post_id",
            "เวชภัณฑ์ทั่วไป",
            "หมวดค่าวัสดุ - เวชภัณฑ์มิใช่ยา - เวชภัณฑ์ทั่วไป",
            exact=False,
        )
    await ensure_m2o(page, "picking_type_id", "คลังกลาง", "คลังกลาง: Receipts", exact=False)

    description = page.locator('.o_field_widget[name="description"] textarea').first
    await description.click()
    await description.fill(
        "ขอซื้อเวชภัณฑ์มิใช่ยา (Gauze 2x2 Sterile) ตามงบ DBR/2570/0027 "
        "วิธีเฉพาะเจาะจง มูลค่าไม่เกิน 500,000 บาท รูปแบบใบสั่งซื้อ"
    )
    await save_form(page)
    await shot(page, "01_pr_header.png")

    lines = page.locator('.o_field_widget[name="line_ids"]')
    await lines.locator(".o_field_x2many_list_row_add a").click()
    row = lines.locator("tr.o_selected_row")
    product = row.locator('[name="product_id"] input').first
    await product.click()
    await product.fill("")
    await product.press_sequentially(PRODUCT_CODE, delay=40)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    await menu.get_by_text(PRODUCT_CODE).first.click()
    await page.wait_for_timeout(800)
    qty = row.locator('[name="product_qty"] input').first
    await qty.click()
    await qty.fill(AMOUNT_QTY)
    await qty.press("Tab")
    price = row.locator(
        '[name="budget_unit_price"] input, [name="estimated_cost"] input, '
        '[name="price_unit"] input'
    ).first
    if await price.count():
        val = await price.input_value()
        if not val or val in ("0", "0.00"):
            await price.fill("6")
            await price.press("Tab")
    await save_form(page)
    await shot(page, "03_pr_line.png")

    name = (await page.locator('.o_field_widget[name="name"]').first.inner_text()).strip()
    pr_id = int(re.search(r"/(\d+)(?:\?|$)", page.url).group(1))
    print("PR", name, pr_id)
    await add_wa_committees_via_rpc(page, pr_id)
    await page.reload(wait_until="domcontentloaded")
    await page.wait_for_timeout(800)
    tab = page.locator(".nav-link").filter(has_text="คณะกรรมการ")
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(600)
    await shot(page, "04_committee.png")

    pr_url = page.url
    await complete_document(page, DOC_APPROVAL)
    await login_as(page, USER)
    await open_record(page, pr_url)
    await shot(page, "05_approval_done.png")
    await check_budget(page)
    await shot(page, "06_budget_ok.png")
    closer = page.locator(".o_notification .o_notification_close")
    if await closer.count():
        await closer.first.click()
    await page.locator('button[name="action_send_to_procurement"]').click()
    await page.wait_for_timeout(1500)
    await shot(page, "07_sent_procurement.png")
    return name, page.url, pr_id


async def assign_and_verify(page, pr_name):
    await login_as(page, PROC_BOSS)
    await page.goto(f"{BASE_URL}/odoo/action-979", wait_until="domcontentloaded")
    await page.wait_for_timeout(1200)
    kpi = page.locator(".o_vpk_inbox_kpi", has_text="รอมอบหมาย")
    if await kpi.count():
        await kpi.first.click()
        await page.wait_for_timeout(800)
    card = page.locator(".o_kanban_record, .o_vpk_inbox_card", has_text=pr_name).first
    await card.wait_for(state="visible", timeout=25000)
    await shot(page, "08_inbox_card.png")
    assign_btn = card.get_by_role("button", name="มอบหมายงาน")
    if await assign_btn.count():
        await assign_btn.first.click()
        dialog = page.locator(".modal-content").last
        await dialog.wait_for(state="visible")
        field = dialog.locator(".o_field_widget[name='user_id'] input")
        await field.click()
        await field.fill("กลุ่มวัสดุ")
        await page.wait_for_timeout(500)
        await page.locator(
            ".o-autocomplete--dropdown-menu .dropdown-item, .o-autocomplete--dropdown-item"
        ).filter(has_text="กลุ่มวัสดุ").first.click()
        await shot(page, "09_assign_wizard.png")
        await dialog.get_by_role("button", name="มอบหมายงาน", exact=True).click()
        await dialog.wait_for(state="hidden", timeout=20000)

    await login_as(page, PROC_OWNER)
    await page.goto(f"{BASE_URL}/odoo/action-979", wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)
    for label in ("มอบหมายแล้ว", "งานของฉัน", "ทั้งหมด"):
        kpi = page.locator(".o_vpk_inbox_kpi", has_text=label)
        if await kpi.count():
            await kpi.first.click()
            await page.wait_for_timeout(600)
        card = page.locator(".o_kanban_record, .o_vpk_inbox_card", has_text=pr_name).first
        if await card.count():
            break
    await card.wait_for(state="visible", timeout=25000)
    open_btn = card.locator(
        'button[name="action_open_procurement_work"], button:has-text("เปิดทำรายการ")'
    )
    await open_btn.first.click()
    await page.locator(".o_form_view").first.wait_for(state="visible", timeout=25000)
    pr_url = page.url
    await shot(page, "10_pr_assigned.png")

    for document in (DOC_COMMITTEE, DOC_SPECIFIC):
        try:
            await complete_document(page, document)
        except Exception as error:
            print("DOC skip/fail", document["label"], error)
        await login_as(page, PROC_OWNER)
        await open_record(page, pr_url)

    verify = page.locator('button[name="action_verify_procurement"]')
    if await verify.count() and await verify.first.is_visible():
        await verify.first.click()
        await page.wait_for_timeout(1500)
        await shot(page, "12_verified.png")
    return pr_url


async def send_egp_winner_po(page, pr_url, pr_name):
    await open_record(page, pr_url)
    send = page.locator('button[name="action_send_to_egp"]')
    await send.wait_for(state="visible", timeout=20000)
    await shot(page, "13_send_egp_btn.png")
    await send.click()
    await page.wait_for_timeout(800)
    make = page.locator('button[name="make_purchase_requisition"]')
    if await make.count():
        await make.click()
        await page.locator(".modal").wait_for(state="hidden", timeout=30000)
    await page.wait_for_timeout(1200)

    info = await rpc(
        page,
        "purchase.request",
        "search_read",
        [[["name", "=", pr_name]]],
        {"fields": ["name", "egp_requisition_id", "estimated_cost"], "limit": 1},
    )
    egp_id = info["result"][0]["egp_requisition_id"][0]
    egp_name = None
    await page.goto(f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
    egp_name = (await page.locator('.o_field_widget[name="name"]').first.inner_text()).strip()
    await shot(page, "14_egp_form.png")

    # ≤500k ต้องไม่มีปุ่มสร้างแผน
    plan_btn = page.locator('button[name="action_create_ebidding_plan"], button:has-text("สร้างแผน")')
    visible_plan = await plan_btn.count() and await plan_btn.first.is_visible()
    await shot(page, "15_no_plan_expected.png")
    print("plan button visible?", visible_plan)

    for field, value in (
        ("egp_project_reference", "P555555555"),
        ("egp_project_name", "ซื้อเวชภัณฑ์มิใช่ยา Gauze วิธีเฉพาะเจาะจง ≤500k"),
    ):
        box = page.locator(
            f'.o_field_widget[name="{field}"] input, .o_field_widget[name="{field}"] textarea'
        )
        if await box.count():
            await box.first.fill(value)
    await save_form(page)

    # ผู้เสนอราคา Vendor DEMO
    tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา"))
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(400)
    add = page.locator(
        'button[name="action_open_egp_bid_import_wizard"], button:has-text("เพิ่มผู้เสนอราคา")'
    )
    if await add.count():
        await add.first.click()
        modal = page.locator(".modal-content").last
        await modal.wait_for(state="visible")
        partner = modal.locator(
            '.o_field_widget[name="partner_id"] input, .o_field_widget[name="vendor_id"] input'
        ).first
        await partner.click()
        await partner.fill(VENDOR)
        await page.wait_for_timeout(600)
        await page.locator(".o-autocomplete--dropdown-menu .dropdown-item").filter(
            has_text=VENDOR
        ).first.click()
        confirm = modal.get_by_role("button", name=re.compile("บันทึก|ยืนยัน|เพิ่ม|ตกลง"))
        if await confirm.count():
            await confirm.first.click()
            try:
                await modal.wait_for(state="hidden", timeout=20000)
            except PlaywrightTimeout:
                print("bid wizard open")
    await page.wait_for_timeout(800)
    winner = page.locator(
        'input[type="checkbox"][name="is_winner"], .o_field_boolean[name="is_winner"] input'
    )
    if await winner.count():
        await winner.first.check()
        await save_form(page)
    await shot(page, "21_winner.png")

    # สร้าง PO
    po_btn = page.locator(
        'button[name="action_open_create_rfq_wizard"], button:has-text("สร้าง PO")'
    )
    if await po_btn.count() and await po_btn.first.is_visible():
        await shot(page, "26_create_po_btn.png")
        await po_btn.first.click()
        modal = page.locator(".modal-content").last
        await modal.wait_for(state="visible", timeout=15000)
        await shot(page, "27_po_wizard.png")
        create = modal.get_by_role("button", name=re.compile("สร้าง|ยืนยัน|บันทึก"))
        if await create.count():
            await create.first.click()
            try:
                await modal.wait_for(state="hidden", timeout=30000)
            except PlaywrightTimeout:
                print("po wizard stuck")
        await page.wait_for_timeout(2000)
        await shot(page, "28_po_form.png")
    else:
        print("no PO button yet")
        await shot(page, "26_no_po_btn.png")
    return egp_id, egp_name


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=HEADLESS)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        try:
            pr_name, pr_url, pr_id = await create_pr(page)
            meta.update({"pr_name": pr_name, "pr_url": pr_url, "pr_id": pr_id})
            pr_url = await assign_and_verify(page, pr_name)
            meta["pr_url"] = pr_url
            egp_id, egp_name = await send_egp_winner_po(page, pr_url, pr_name)
            meta.update({"egp_id": egp_id, "egp_name": egp_name})
            found = await rpc(
                page,
                "purchase.order",
                "search_read",
                [[["origin", "ilike", pr_name]]],
                {
                    "fields": ["name", "state", "partner_id", "amount_total"],
                    "limit": 3,
                    "order": "id desc",
                },
            )
            meta["pos"] = found.get("result")
            print("META", json.dumps(meta, ensure_ascii=False, indent=2))
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error.png"), full_page=True)
            META.write_text(
                json.dumps({"error": str(error), **meta}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
