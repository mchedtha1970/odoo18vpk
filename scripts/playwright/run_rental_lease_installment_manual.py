#!/usr/bin/env python3
"""UAT บทที่ 4: เช่า/จ้าง สัญญาบริการเป็นงวด — เช่าเครื่องถ่ายเอกสาร Fuji Xerox

ขอบเขตตัวอย่าง:
  DBR/2570/0043 (295,320 บาท ≤500k) → PR วิธีเฉพาะเจาะจง ลักษณะเช่า รูปแบบสัญญา
  → พัสดุ → e-GP (ไม่บังคับแผน) → ผู้ชนะ → สัญญาเช่าคอมพิวเตอร์ + แบ่งงวด 12 เดือน
  → สร้าง PO จากแฟ้มเดิม → ใบตรวจรับงานรายงวด (เมื่อมีใบแจ้งหนี้)

รัน:
  HEADLESS=1 python3 scripts/playwright/run_rental_lease_installment_manual.py
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

OUT = Path("docs/manual_assets/figures/rental_lease_installment")
META = OUT / "meta.json"
USER = "uat.dept"
PROC_BOSS = "uat.procurement"
PROC_OWNER = "uat.material"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
PRODUCT_CODE = "RENT-FX-WC"
BUDGET = "DBR/2570/0043"
VENDOR = "Vendor DEMO"
QTY = "12"  # 12 งวดตามปีงบประมาณ
UNIT_PRICE = "24610"  # รวม 295,320 — ค่าเช่า 7 เครื่อง/เดือน

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
    for emp_id, role in ((19, "chairman"), (20, "committee"), (21, "secretary")):
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
    await page.locator(
        ".o_list_button_add, .o_form_button_create, button:has-text('สร้าง')"
    ).first.click()
    await page.locator(".o_form_view").wait_for(state="visible")
    await shot(page, "01a_pr_list_new.png")

    await fill_m2o(page, "procurement_type_id", "ซื้อ/จ้าง/เช่า", "ซื้อ/จ้าง/เช่า")
    await fill_m2o(
        page, "purchase_type_id", "จัดซื้อจัดจ้างผ่านพัสดุ", "จัดซื้อจัดจ้างผ่านพัสดุ"
    )
    await fill_m2o(page, "procurement_method_id", "เฉพาะเจาะจง", "เฉพาะเจาะจง")
    await fill_selection(page, "procurement_nature", "เช่า")
    await fill_selection(page, "procurement_document", "สัญญา")
    await fill_selection(page, "budget_section_key", "วัสดุ")
    await page.locator('.o_field_widget[name="budget_group_id"]').wait_for(
        state="visible", timeout=10000
    )
    await fill_m2o(page, "budget_group_id", "วัสดุทั่วไป", "วัสดุทั่วไป")
    await fill_m2o(page, "budget_plan_request_id", BUDGET, BUDGET, exact=False)
    await fill_m2o(page, "budget_analytic_account_id", "UAT-DEPT", "UAT-DEPT", exact=False)
    await fill_m2o(page, "budget_fund_source_id", "เงินบำรุง", "เงินบำรุง")
    post = page.locator('.o_field_widget[name="budget_post_id"]')
    if await post.count() and await post.first.is_visible():
        # หมวดงบมักดึงจาก DBR อัตโนมัติ — ถ้ายังว่างให้เลือกด้วยคีย์บอร์ด
        # (dropdown มักอยู่นอก viewport ทำให้ click ธรรมดา timeout)
        current = post.locator(".o_input, input").first
        val = ""
        try:
            val = (await current.input_value()).strip()
        except Exception:
            try:
                val = (await post.inner_text()).strip()
            except Exception:
                val = ""
        if not val or val in ("", False):
            inp = post.locator("input").first
            await inp.click()
            await inp.fill("วัสดุทั่วไป")
            await page.wait_for_timeout(600)
            menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
            if await menu.count():
                item = menu.locator(".dropdown-item").filter(has_text="อื่นๆ").first
                if await item.count():
                    await item.click(force=True)
                else:
                    await inp.press("ArrowDown")
                    await inp.press("Enter")
            await page.wait_for_timeout(400)
    await ensure_m2o(page, "picking_type_id", "คลังกลาง", "คลังกลาง: Receipts", exact=False)

    description = page.locator('.o_field_widget[name="description"] textarea').first
    await description.click()
    await description.fill(
        "ขอเช่าเครื่องถ่ายเอกสารยี่ห้อ Fuji Xerox WorkCentre จำนวน 7 เครื่อง "
        "กำหนดระยะเวลาสัญญา 1 ปี ตามปีงบประมาณ ใช้งบ DBR/2570/0043 "
        "รูปแบบสัญญาเช่า จ่ายเป็นงวดรายเดือน (12 งวด) "
        "เมื่อผู้ขายส่งใบแจ้งหนี้เรียกเก็บเป็นงวด จะตรวจรับงานรายงวดตามสัญญา"
    )
    await save_form(page)
    await shot(page, "01_pr_header.png")
    await shot(page, "02_method_lease_contract.png")

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
    await qty.fill(QTY)
    await qty.press("Tab")
    price = row.locator(
        '[name="budget_unit_price"] input, [name="estimated_cost"] input, '
        '[name="price_unit"] input'
    ).first
    if await price.count():
        val = await price.input_value()
        if not val or val in ("0", "0.00"):
            await price.fill(UNIT_PRICE)
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
    claim = card.locator(
        'button[name="action_claim_procurement"], button:has-text("รับงาน")'
    )
    if await claim.count() and await claim.first.is_visible():
        await claim.first.click()
        await page.wait_for_timeout(1000)
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
        await shot(page, "11_verify_btn.png")
        await verify.first.click()
        await page.wait_for_timeout(1500)
        await shot(page, "12_verified.png")
    return pr_url


async def send_egp_contract_installments(page, pr_url, pr_name):
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
    await page.goto(
        f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded"
    )
    await page.locator(".o_form_view").first.wait_for()
    egp_name = (
        await page.locator('.o_field_widget[name="name"]').first.inner_text()
    ).strip()
    await shot(page, "14_egp_form.png")

    plan_btn = page.locator(
        'button[name="action_create_ebidding_plan"], button:has-text("สร้างแผน")'
    )
    visible_plan = await plan_btn.count() and await plan_btn.first.is_visible()
    await shot(page, "15_no_plan_expected.png")
    print("plan button visible?", visible_plan)

    for field, value in (
        ("egp_project_reference", "P444444444"),
        ("egp_project_name", "เช่าเครื่องถ่ายเอกสาร Fuji Xerox WorkCentre 7 เครื่อง 1 ปี"),
    ):
        box = page.locator(
            f'.o_field_widget[name="{field}"] input, .o_field_widget[name="{field}"] textarea'
        )
        if await box.count():
            await box.first.fill(value)
    await save_form(page)
    await shot(page, "16_egp_project.png")

    # ผู้เสนอราคา
    tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา"))
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(400)
    cons = page.locator('.o_field_widget[name="egp_consideration_type"] select')
    if await cons.count():
        try:
            await cons.select_option(label="ราคาต่อรายการ")
        except Exception:
            if await cons.locator("option").count() > 1:
                await cons.select_option(index=1)
        await save_form(page)

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

    # สร้างสัญญาเช่า + แบ่งงวด
    contract_btn = page.locator(
        'button[name="action_create_purchase_contract"], '
        'button:has-text("สร้างสัญญา"), button:has-text("เข้าสู่การทำสัญญา")'
    )
    contract_url = None
    contract_name = None
    if await contract_btn.count() and await contract_btn.first.is_visible():
        await shot(page, "22_contract_btn.png")
        await contract_btn.first.click()
        await page.wait_for_timeout(2000)
        await shot(page, "23_contract_form.png")
        ctype = page.locator('.o_field_widget[name="contract_type_id"] input')
        if await ctype.count():
            await ctype.click()
            await ctype.fill("สัญญาเช่าคอมพิวเตอร์")
            await page.wait_for_timeout(500)
            await page.locator(".o-autocomplete--dropdown-menu .dropdown-item").filter(
                has_text="สัญญาเช่าคอมพิวเตอร์"
            ).first.click()
        kind = page.locator('.o_field_widget[name="contract_kind"] select')
        if await kind.count():
            try:
                await kind.select_option(label="เช่า")
            except Exception:
                await kind.select_option(value="lease")
        pay = page.locator('.o_field_widget[name="payment_type"] select')
        if await pay.count():
            try:
                await pay.select_option(label="จ่ายตามงวดเงินที่กำหนด")
            except Exception:
                await pay.select_option(value="installment")
        for field, value in (
            ("egp_reference", "P444444444"),
            ("egp_control_no", "P444444444"),
        ):
            box = page.locator(f'.o_field_widget[name="{field}"] input')
            if await box.count():
                await box.first.fill(value)
        await save_form(page)
        await shot(page, "24_contract_type.png")

        # แท็บเงื่อนไขแบ่งงวด → สร้างงวดอัตโนมัติ 12 งวด
        inst_tab = page.get_by_role("tab", name=re.compile("เงื่อนไขแบ่งงวด|แบ่งงวด"))
        if await inst_tab.count():
            await inst_tab.first.click()
            await page.wait_for_timeout(500)
        gen = page.locator(
            'button[name="action_open_generate_installments"], '
            'button:has-text("สร้างงวด"), button:has-text("สร้างเงื่อนไขแบ่งงวด")'
        )
        if await gen.count() and await gen.first.is_visible():
            await shot(page, "25_installment_btn.png")
            await gen.first.click()
            modal = page.locator(".modal-content").last
            await modal.wait_for(state="visible", timeout=15000)
            count = modal.locator(
                '.o_field_widget[name="installment_count"] input'
            ).first
            if await count.count():
                await count.fill("12")
            await shot(page, "26_installment_wizard.png")
            ok = modal.get_by_role("button", name=re.compile("สร้าง|ยืนยัน|บันทึก|ตกลง"))
            if await ok.count():
                await ok.first.click()
                try:
                    await modal.wait_for(state="hidden", timeout=30000)
                except PlaywrightTimeout:
                    print("installment wizard stuck")
            await page.wait_for_timeout(1000)
        await shot(page, "27_installments.png")

        conf = page.locator(
            'button[name="action_confirm"], button:has-text("ยืนยันสัญญา"), '
            'button:has-text("ยืนยัน")'
        )
        if await conf.count() and await conf.first.is_visible():
            await conf.first.click()
            await page.wait_for_timeout(1500)
            await shot(page, "28_contract_confirmed.png")
        contract_url = page.url
        try:
            contract_name = (
                await page.locator('.o_field_widget[name="name"]').first.inner_text()
            ).strip()
        except Exception:
            contract_name = None
    else:
        print("ไม่พบปุ่มสร้างสัญญา")
        await shot(page, "22_no_contract_btn.png")

    # สร้าง PO จากแฟ้ม e-GP เดิม
    await page.goto(
        f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded"
    )
    await page.locator(".o_form_view").first.wait_for()
    po_btn = page.locator(
        'button[name="action_open_create_rfq_wizard"], button:has-text("สร้าง PO")'
    )
    po_name = None
    if await po_btn.count() and await po_btn.first.is_visible():
        await shot(page, "29_create_po_btn.png")
        await po_btn.first.click()
        modal = page.locator(".modal-content").last
        await modal.wait_for(state="visible", timeout=15000)
        await shot(page, "30_po_wizard.png")
        create = modal.get_by_role("button", name=re.compile("สร้าง|ยืนยัน|บันทึก"))
        if await create.count():
            await create.first.click()
            try:
                await modal.wait_for(state="hidden", timeout=30000)
            except PlaywrightTimeout:
                print("po wizard stuck")
        await page.wait_for_timeout(2000)
        await shot(page, "31_po_form.png")
        try:
            po_name = (
                await page.locator('.o_field_widget[name="name"]').first.inner_text()
            ).strip()
        except Exception:
            po_name = None
        # ปุ่มตรวจรับงาน
        wa = page.locator(
            'button[name="action_create_work_acceptance"], '
            'button:has-text("ใบตรวจรับ"), button:has-text("ตรวจรับ")'
        )
        if await wa.count() and await wa.first.is_visible():
            await shot(page, "32_wa_btn.png")
            await wa.first.click()
            await page.wait_for_timeout(1500)
            await shot(page, "33_wa_form.png")
        else:
            await shot(page, "32_po_actions.png")
    else:
        print("ยังไม่มีปุ่มสร้าง PO")
        await shot(page, "29_no_po_btn.png")

    return {
        "egp_id": egp_id,
        "egp_name": egp_name,
        "contract_url": contract_url,
        "contract_name": contract_name,
        "po_name": po_name,
        "plan_visible": visible_plan,
    }


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {
        "budget": BUDGET,
        "product": PRODUCT_CODE,
        "qty": QTY,
        "unit_price": UNIT_PRICE,
        "scenario": "rental_lease_installment_fuji_xerox",
    }
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=HEADLESS)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        try:
            resume = os.environ.get("RESUME_PR_URL")
            resume_step = os.environ.get("RESUME_STEP", "")
            if resume:
                pr_url = resume
                pr_name = os.environ.get("RESUME_PR_NAME", "")
                pr_id = int(re.search(r"/(\d+)(?:\?|$)", pr_url).group(1))
                meta.update({"pr_name": pr_name, "pr_url": pr_url, "pr_id": pr_id})
                if resume_step == "budget":
                    await login_as(page, USER)
                    await open_record(page, pr_url)
                    await check_budget(page)
                    await shot(page, "06_budget_ok.png")
                    closer = page.locator(".o_notification .o_notification_close")
                    if await closer.count():
                        await closer.first.click()
                    await page.locator('button[name="action_send_to_procurement"]').click()
                    await page.wait_for_timeout(1500)
                    await shot(page, "07_sent_procurement.png")
                elif resume_step == "assign":
                    pass
                else:
                    # เริ่มจากมอบหมาย
                    pass
            else:
                pr_name, pr_url, pr_id = await create_pr(page)
                meta.update({"pr_name": pr_name, "pr_url": pr_url, "pr_id": pr_id})
            if resume_step not in ("egp",):
                pr_url = await assign_and_verify(page, pr_name)
                meta["pr_url"] = pr_url
            extra = await send_egp_contract_installments(page, pr_url, pr_name)
            meta.update(extra)
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
            ctrs = await rpc(
                page,
                "purchase.contract",
                "search_read",
                [[["origin", "ilike", pr_name]]],
                {
                    "fields": [
                        "name",
                        "state",
                        "payment_type",
                        "amount_total",
                        "contract_type_id",
                    ],
                    "limit": 3,
                    "order": "id desc",
                },
            )
            if not ctrs.get("result"):
                ctrs = await rpc(
                    page,
                    "purchase.contract",
                    "search_read",
                    [[]],
                    {
                        "fields": [
                            "name",
                            "state",
                            "payment_type",
                            "amount_total",
                            "contract_type_id",
                        ],
                        "limit": 5,
                        "order": "id desc",
                    },
                )
            meta["contracts"] = ctrs.get("result")
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
