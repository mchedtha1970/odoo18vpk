#!/usr/bin/env python3
"""UAT บทที่ 5: ขอซื้อครุภัณฑ์วิธี e-Bidding — BP-19 สัญญาส่งงวดเดียว

ขอบเขต:
  หน่วยงาน (uat.dept) เปิด PR จาก DBR/2570/0033 รายการ BP-19
  → คณะกรรมการ + เอกสารอนุมัติ → ส่งจัดซื้อ
  → พัสดุกลุ่มครุภัณฑ์ → e-GP → สร้างแผน (บังคับเพราะ e-Bidding)
  → ผู้ชนะ → สัญญาซื้อขาย จ่ายครั้งเดียว (ส่งงวดเดียว)

รัน:
  HEADLESS=1 python3 scripts/playwright/run_asset_ebidding_bp19_manual.py
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

OUT = Path("docs/manual_assets/figures/asset_ebidding_bp19")
META = OUT / "meta.json"
USER = "uat.dept"
PROC_BOSS = "uat.procurement"
PROC_OWNER = "uat.equipment"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"
PRODUCT_CODE = "BP-19"
BUDGET = "DBR/2570/0033"
VENDOR = "Vendor DEMO"
QTY = "1"
UNIT_PRICE = "1600000"

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
DOC_EBID = {
    "label": "รายงานขออนุมัติประกวดราคาซื้อ",
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


async def close_modals(page):
    for _ in range(3):
        modal = page.locator(".modal.d-block, .modal.show").last
        if not await modal.count():
            break
        btn = modal.locator(
            "button:has-text('ปิด'), button:has-text('ยกเลิก'), button.btn-secondary"
        )
        if await btn.count() and await btn.first.is_visible():
            await btn.first.click()
            await page.wait_for_timeout(400)
        else:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)


async def add_committees_rpc(page, pr_id: int):
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
    print("committees ok")


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
    await fill_m2o(page, "procurement_method_id", "E-bidding", "E-bidding")
    await fill_selection(page, "procurement_nature", "ซื้อ")
    await fill_selection(page, "procurement_document", "สัญญา")
    await fill_selection(page, "budget_section_key", "ครุภัณฑ์")
    await fill_m2o(page, "budget_plan_request_id", BUDGET, BUDGET, exact=False)
    # analytic มักดึงจากงบ; ถ้ายังว่างให้เลือก
    analytic = page.locator('.o_field_widget[name="budget_analytic_account_id"] input')
    if await analytic.count():
        val = ""
        try:
            val = (await analytic.input_value()).strip()
        except Exception:
            val = ""
        if not val:
            await fill_m2o(
                page,
                "budget_analytic_account_id",
                "กุมาร",
                "กลุ่มงาน กุมารเวชกรรม",
                exact=False,
            )
    await fill_m2o(page, "budget_fund_source_id", "เงินบำรุง", "เงินบำรุง")
    post = page.locator('.o_field_widget[name="budget_post_id"]')
    if await post.count() and await post.first.is_visible():
        inp = post.locator("input").first
        cur = ""
        try:
            cur = (await inp.input_value()).strip()
        except Exception:
            cur = ""
        if not cur:
            await inp.click()
            await inp.fill("ครุภัณฑ์วิทยาศาสตร์")
            await page.wait_for_timeout(600)
            menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
            if await menu.count():
                item = menu.locator(".dropdown-item").first
                if await item.count():
                    await item.click(force=True)
                else:
                    await inp.press("Enter")
    await ensure_m2o(page, "picking_type_id", "คลังกลาง", "คลังกลาง: Receipts", exact=False)

    description = page.locator('.o_field_widget[name="description"] textarea').first
    await description.click()
    await description.fill(
        "ขอซื้อครุภัณฑ์ BP-19 เตียงผู้ป่วย ICU ไฟฟ้า 4 มอเตอร์ "
        "ตามงบ DBR/2570/0033 วิธี e-Bidding รูปแบบสัญญา "
        "ทำสัญญาซื้อขาย ส่งของ/ตรวจรับงวดเดียว"
    )
    await save_form(page)
    await shot(page, "01_pr_header.png")
    await shot(page, "02_method_ebidding_contract.png")

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
    await add_committees_rpc(page, pr_id)
    await page.reload(wait_until="domcontentloaded")
    await page.wait_for_timeout(800)
    tab = page.locator(".nav-link").filter(has_text="คณะกรรมการ")
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(500)
    await shot(page, "04_committee.png")

    pr_url = page.url
    # เอกสารอนุมัติ + ภาพวิซาร์ด
    await page.locator(".nav-link").filter(has_text="เอกสารที่เกี่ยวข้อง").first.click()
    await page.wait_for_timeout(600)
    await shot(page, "05a_docs_tab.png")
    add_btn = page.locator(
        'button[name="action_open_add_studio_document_wizard"], button:has-text("เพิ่มเอกสาร")'
    )
    if await add_btn.count():
        await add_btn.first.click()
        modal = page.locator(".modal").last
        await modal.wait_for(state="visible", timeout=15000)
        await shot(page, "05b_add_doc_wizard.png")
        cancel = modal.locator(
            'button:has-text("ยกเลิก"), button:has-text("ปิด"), button.btn-secondary'
        )
        if await cancel.count():
            await cancel.first.click()
            await page.wait_for_timeout(400)

    await complete_document(page, DOC_APPROVAL)
    await login_as(page, USER)
    await open_record(page, pr_url)
    await page.locator(".nav-link").filter(has_text="เอกสารที่เกี่ยวข้อง").first.click()
    await page.wait_for_timeout(600)
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
        await field.fill("กลุ่มครุภัณฑ์")
        await page.wait_for_timeout(500)
        await page.locator(
            ".o-autocomplete--dropdown-menu .dropdown-item, .o-autocomplete--dropdown-item"
        ).filter(has_text="กลุ่มครุภัณฑ์").first.click()
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

    for document in (DOC_COMMITTEE, DOC_EBID):
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


async def send_egp_plan_contract(page, pr_url, pr_name):
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

    # e-Bidding ต้องมีแผน
    plan_btn = page.locator(
        'button[name="action_create_ebidding_plan"], button:has-text("สร้างแผน")'
    )
    if await plan_btn.count() and await plan_btn.first.is_visible():
        await shot(page, "15_create_plan_btn.png")
        await plan_btn.first.click()
        modal = page.locator(".modal-content").last
        await modal.wait_for(state="visible", timeout=15000)
        await shot(page, "16_plan_wizard.png")
        save = modal.get_by_role("button", name=re.compile("บันทึก|สร้าง|ยืนยัน"))
        if await save.count():
            await save.first.click()
            try:
                await modal.wait_for(state="hidden", timeout=30000)
            except PlaywrightTimeout:
                print("plan modal still open")
        await page.wait_for_timeout(1000)
        await shot(page, "17_plan_created.png")
    else:
        print("ไม่พบปุ่มสร้างแผน")
        await shot(page, "15_no_plan_btn.png")

    for field, value in (
        ("egp_project_reference", "P333333333"),
        ("egp_project_name", "ซื้อครุภัณฑ์ BP-19 ICU bed วิธี e-Bidding"),
    ):
        box = page.locator(
            f'.o_field_widget[name="{field}"] input, .o_field_widget[name="{field}"] textarea'
        )
        if await box.count():
            await box.first.fill(value)
    await save_form(page)
    await shot(page, "18_egp_project.png")

    # ผู้ชนะ
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

    # ใส่ผู้ชนะผ่าน RPC ให้ชัวร์
    vendor = await rpc(
        page,
        "res.partner",
        "search_read",
        [[["name", "ilike", VENDOR]]],
        {"fields": ["id", "name"], "limit": 1},
    )
    vendor_id = (vendor.get("result") or [{}])[0].get("id")
    if vendor_id:
        lines = await rpc(
            page,
            "purchase.requisition.line",
            "search_read",
            [[["requisition_id", "=", egp_id]]],
            {
                "fields": [
                    "id",
                    "product_id",
                    "product_qty",
                    "product_uom_id",
                    "product_description_variants",
                ]
            },
        )
        req_line = (lines.get("result") or [None])[0]
        bids = await rpc(
            page,
            "purchase.requisition.egp.bid",
            "search_read",
            [[["requisition_id", "=", egp_id]]],
            {"fields": ["id", "line_ids"], "limit": 5},
        )
        if not (bids.get("result") or []) and req_line:
            await rpc(
                page,
                "purchase.requisition.egp.bid.line",
                "create",
                [
                    {
                        "requisition_id": egp_id,
                        "partner_id": vendor_id,
                        "requisition_line_id": req_line["id"],
                        "product_id": req_line["product_id"][0],
                        "name": req_line.get("product_description_variants")
                        or "BP-19 ICU bed",
                        "product_qty": req_line.get("product_qty") or 1.0,
                        "product_uom_id": req_line["product_uom_id"][0]
                        if req_line.get("product_uom_id")
                        else False,
                        "price_unit": float(UNIT_PRICE),
                        "is_winner": True,
                    }
                ],
            )
        for bid in bids.get("result") or []:
            await rpc(
                page,
                "purchase.requisition.egp.bid",
                "write",
                [[bid["id"]], {"is_winner": True, "amount_total": float(UNIT_PRICE)}],
            )
            if bid.get("line_ids"):
                await rpc(
                    page,
                    "purchase.requisition.egp.bid.line",
                    "write",
                    [bid["line_ids"], {"is_winner": True, "price_unit": float(UNIT_PRICE)}],
                )
    await page.reload(wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
    tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา"))
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(400)
    await shot(page, "21_winner.png")

    # สร้างสัญญาซื้อขาย จ่ายครั้งเดียว
    contract_btn = page.locator(
        'button[name="action_create_purchase_contract"], '
        'button:has-text("สร้างสัญญา"), button:has-text("เข้าสู่การทำสัญญา")'
    )
    contract_id = None
    contract_name = None
    if await contract_btn.count() and await contract_btn.first.is_visible():
        await shot(page, "22_contract_btn.png")
        await contract_btn.first.click()
        await page.wait_for_timeout(2000)
        await close_modals(page)
        await shot(page, "23_contract_form.png")
        m = re.search(r"purchase\.contract/(\d+)", page.url)
        if m:
            contract_id = int(m.group(1))
        else:
            found = await rpc(
                page,
                "purchase.contract",
                "search_read",
                [[["requisition_id", "=", egp_id]]],
                {"fields": ["id", "name"], "limit": 1, "order": "id desc"},
            )
            if found.get("result"):
                contract_id = found["result"][0]["id"]
                await page.goto(
                    f"{BASE_URL}/odoo/purchase.contract/{contract_id}",
                    wait_until="domcontentloaded",
                )
                await page.locator(".o_form_view").first.wait_for()

        if contract_id:
            ctype = await rpc(
                page,
                "purchase.contract.type",
                "search_read",
                [[["name", "=", "สัญญาซื้อขาย"]]],
                {"fields": ["id"], "limit": 1},
            )
            ctype_id = (ctype.get("result") or [{}])[0].get("id")
            vals = {
                "payment_type": "once",
                "egp_contract_control_no": "P333333333",
                # ตัวอย่างครุภัณฑ์: รับประกันความชำรุดบกพร่อง 1 ปี
                "warranty_period_years": 1,
                "warranty_period_months": 0,
                "warranty_period_days": 0,
                "warranty_fix_days": 15,
            }
            if ctype_id:
                vals["contract_type_id"] = ctype_id
            fields = await rpc(
                page, "purchase.contract", "fields_get", [], {"attributes": ["type"]}
            )
            if fields.get("result") and "contract_kind" in fields["result"]:
                vals["contract_kind"] = "buy"
            await rpc(page, "purchase.contract", "write", [[contract_id], vals])
            # สร้างงวดเดียวเต็มมูลค่า (จ่ายครั้งเดียว)
            await rpc(
                page,
                "purchase.contract",
                "_egp_ensure_single_installment_for_once",
                [[contract_id]],
            )
            await page.reload(wait_until="domcontentloaded")
            await page.locator(".o_form_view").first.wait_for()
            await page.evaluate(
                """() => {
                const el = document.querySelector('.o_vpk_warranty_group, [name=contract_warranty]');
                if (el) el.scrollIntoView({block: 'center'});
            }"""
            )
            await page.wait_for_timeout(400)
            await shot(page, "25_contract_warranty.png")
            await page.evaluate(
                """() => {
                const el = document.querySelector('[name=payment_type], [name=contract_amount]');
                if (el) el.scrollIntoView({block: 'center'});
            }"""
            )
            await page.wait_for_timeout(300)
            await shot(page, "24_contract_once.png")
            tab = page.locator(
                '.o_notebook .nav-link, .o_notebook_headers a',
                has_text="เงื่อนไขแบ่งงวด",
            )
            if await tab.count():
                await tab.first.click()
                await page.wait_for_timeout(600)
                await shot(page, "26_contract_one_installment.png")
            conf = page.locator(
                'button[name="action_confirm"], button:has-text("ยืนยันสัญญา"), '
                'button:has-text("ยืนยัน")'
            )
            if await conf.count() and await conf.first.is_visible():
                await conf.first.click()
                await page.wait_for_timeout(1500)
                await close_modals(page)
            # confirm via rpc if still draft
            await rpc(page, "purchase.contract", "action_confirm", [[contract_id]])
            await page.reload(wait_until="domcontentloaded")
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "28_contract_confirmed.png")
            contract_name = (
                await page.locator('.o_field_widget[name="name"]').first.inner_text()
            ).strip()
    else:
        print("ไม่พบปุ่มสร้างสัญญา — อาจต้องมีผู้ชนะ/เอกสารก่อน")
        await shot(page, "22_no_contract_btn.png")

    return {
        "egp_id": egp_id,
        "egp_name": egp_name,
        "contract_id": contract_id,
        "contract_name": contract_name,
    }


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {
        "budget": BUDGET,
        "product": PRODUCT_CODE,
        "qty": QTY,
        "unit_price": UNIT_PRICE,
        "scenario": "asset_ebidding_bp19_once",
        "method": "E-bidding",
        "payment": "once",
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
                    await page.locator(
                        'button[name="action_send_to_procurement"]'
                    ).click()
                    await page.wait_for_timeout(1500)
                    await shot(page, "07_sent_procurement.png")
            else:
                pr_name, pr_url, pr_id = await create_pr(page)
                meta.update({"pr_name": pr_name, "pr_url": pr_url, "pr_id": pr_id})
            if resume_step not in ("egp",):
                pr_url = await assign_and_verify(page, pr_name)
                meta["pr_url"] = pr_url
            extra = await send_egp_plan_contract(page, pr_url, pr_name)
            meta.update(extra)
            print("META", json.dumps(meta, ensure_ascii=False, indent=2, default=str))
            META.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error.png"), full_page=True)
            meta["error"] = str(error)
            META.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
