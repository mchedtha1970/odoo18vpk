#!/usr/bin/env python3
"""เดิน UAT วิธีเฉพาะเจาะจง ครุภัณฑ์ CCTV-16 สัญญาซื้อขาย + จับภาพคู่มือ

ขอบเขต: PR จาก DBR/2570/0001 → ส่งจัดซื้อ → พัสดุ (กลุ่มครุภัณฑ์) → e-GP → แผน
→ ผู้ชนะ → สัญญาซื้อขาย → สร้าง PO จากแฟ้มเดิม (ไม่เปิด PR ใหม่)

รัน:
  HEADLESS=1 python3 scripts/playwright/run_cctv16_specific_manual.py
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
    add_committee,
    check_budget,
    complete_document,
    ensure_m2o,
    fill_m2o,
    fill_selection,
    open_record,
    pause,
    save_form,
)
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/cctv16_specific")
META = OUT / "meta.json"
USER = "uat.dept"
PROC_BOSS = "uat.procurement"
PROC_OWNER = "uat.equipment"
HEADLESS = os.environ.get("HEADLESS", "1") == "1"

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
    "signers": [
        {"login": "uat.director", "name": "ผู้ทดสอบผู้อำนวยการโรงพยาบาล"},
    ],
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


async def shot(page, name: str, clip=None):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if clip:
        await page.screenshot(path=str(path), clip=clip)
    else:
        await page.locator(".o_action, .o_form_view, .o_content").first.screenshot(
            path=str(path)
        )
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


async def create_pr(page):
    await login_as(page, USER)
    await page.goto(f"{BASE_URL}/odoo/action-577", wait_until="domcontentloaded")
    await page.locator(".o_list_button_add, .o_form_button_create").first.click()
    await page.locator(".o_form_view").wait_for(state="visible")

    await fill_m2o(page, "procurement_type_id", "ซื้อ/จ้าง/เช่า", "ซื้อ/จ้าง/เช่า")
    await fill_m2o(
        page, "purchase_type_id", "จัดซื้อจัดจ้างผ่านพัสดุ", "จัดซื้อจัดจ้างผ่านพัสดุ"
    )
    await fill_m2o(page, "procurement_method_id", "เฉพาะเจาะจง", "เฉพาะเจาะจง")
    await fill_selection(page, "procurement_nature", "ซื้อ")
    await fill_selection(page, "procurement_document", "สัญญา")
    # procurement_category เป็น computed (จัดซื้อแบบสัญญา) — ห้าม fill
    await fill_selection(page, "budget_section_key", "ครุภัณฑ์")
    await fill_m2o(
        page,
        "budget_plan_request_id",
        "DBR/2570/0001",
        "DBR/2570/0001 - หน่วยงานทดสอบ",
        exact=False,
    )
    await fill_m2o(page, "budget_analytic_account_id", "UAT-DEPT", "UAT-DEPT", exact=False)
    await fill_m2o(page, "budget_fund_source_id", "เงินบำรุง", "เงินบำรุง")
    await ensure_m2o(
        page, "picking_type_id", "คลังกลาง", "คลังกลาง: Receipts", exact=False
    )

    description = page.locator('.o_field_widget[name="description"] textarea').first
    await description.click()
    await description.fill(
        "ขอซื้อครุภัณฑ์กล้อง CCTV-16 ตามงบ DBR/2570/0001 จำนวน 1 เครื่อง "
        "สัญญาซื้อขาย ส่งของงวดเดียว มี QC และตรวจรับงาน"
    )
    await save_form(page)
    await shot(page, "01_pr_header.png")
    await shot(
        page,
        "02_method_contract.png",
        clip={"x": 240, "y": 80, "width": 1160, "height": 420},
    )

    # product line
    lines = page.locator('.o_field_widget[name="line_ids"]')
    await lines.locator(".o_field_x2many_list_row_add a").click()
    row = lines.locator("tr.o_selected_row")
    product = row.locator('[name="product_id"] input').first
    await product.click()
    await product.fill("")
    await product.press_sequentially("CCTV-16", delay=40)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    await menu.get_by_text("CCTV-16").first.click()
    await page.wait_for_timeout(1000)
    qty = row.locator('[name="product_qty"] input').first
    await qty.click()
    await qty.fill("1")
    await qty.press("Tab")
    # price may auto from budget; if empty fill 600000
    price = row.locator(
        '[name="budget_unit_price"] input, [name="estimated_cost"] input, '
        '[name="price_unit"] input'
    ).first
    if await price.count():
        val = await price.input_value()
        if not val or val in ("0", "0.00"):
            await price.fill("600000")
            await price.press("Tab")
    await save_form(page)
    await shot(page, "03_pr_line_cctv.png")

    name = (await page.locator('.o_field_widget[name="name"]').first.inner_text()).strip()
    print("PR", name)
    await add_committee(page, "ประธาน")
    await shot(page, "04_committee.png")

    # ตามคู่มือ: เอกสารขออนุมัติ → ลงนาม → แล้วค่อยตรวจงบ → ส่งจัดซื้อ
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
    return name, page.url


async def assign_and_verify(page, pr_name):
    await login_as(page, PROC_BOSS)
    await page.goto(f"{BASE_URL}/odoo/action-979", wait_until="domcontentloaded")
    await page.locator(".o_vpk_procurement_inbox_dashboard, .o_vpk_inbox_kpi").first.wait_for(
        timeout=25000
    )
    await page.wait_for_timeout(800)
    # unassigned
    kpi = page.locator(".o_vpk_inbox_kpi", has_text="รอมอบหมาย")
    if await kpi.count():
        await kpi.first.click()
        await page.wait_for_timeout(1000)
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
        item = page.locator(
            ".o-autocomplete--dropdown-menu .dropdown-item, "
            ".o-autocomplete--dropdown-item"
        ).filter(has_text="กลุ่มครุภัณฑ์").first
        await item.click()
        await shot(page, "09_assign_wizard.png")
        await dialog.get_by_role("button", name="มอบหมายงาน", exact=True).click()
        await dialog.wait_for(state="hidden", timeout=20000)
    else:
        # claim as equipment later
        print("no assign button, will claim as equipment")

    await login_as(page, PROC_OWNER)
    await page.goto(f"{BASE_URL}/odoo/action-979", wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)
    for label in ("มอบหมายแล้ว", "งานของฉัน", "ทั้งหมด"):
        kpi = page.locator(".o_vpk_inbox_kpi", has_text=label)
        if await kpi.count():
            await kpi.first.click()
            await page.wait_for_timeout(800)
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


async def send_egp_and_plan(page, pr_url):
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
    await page.wait_for_timeout(1500)
    # open linked egp
    egp = page.locator('.o_field_widget[name="egp_requisition_id"] a, a[href*="purchase.requisition"]').first
    if await egp.count():
        await egp.click()
    else:
        # search latest
        data = await rpc(
            page,
            "purchase.requisition",
            "search_read",
            [[["purchase_request_id.name", "ilike", Path(pr_url).name]]],
            {"fields": ["name", "id"], "limit": 1, "order": "id desc"},
        )
        # fallback: from PR read
        pass
    await page.wait_for_timeout(1500)
    # Prefer reading from PR
    await open_record(page, pr_url)
    info = await rpc(
        page,
        "purchase.request",
        "search_read",
        [[["id", "=", int(re.search(r"/(\d+)(?:\?|$)", pr_url).group(1))]]],
        {"fields": ["name", "egp_requisition_id", "estimated_cost"], "limit": 1},
    )
    print("PR info", info)
    egp_id = None
    if info.get("result"):
        egp_m2o = info["result"][0].get("egp_requisition_id")
        if egp_m2o:
            egp_id = egp_m2o[0]
    if not egp_id:
        # try domain by origin
        pr_name = info["result"][0]["name"] if info.get("result") else ""
        found = await rpc(
            page,
            "purchase.requisition",
            "search_read",
            [[["purchase_request_id.name", "=", pr_name]]],
            {"fields": ["name", "id"], "limit": 1, "order": "id desc"},
        )
        print("EGP found", found)
        if found.get("result"):
            egp_id = found["result"][0]["id"]
    if not egp_id:
        raise RuntimeError("ไม่พบเอกสาร e-GP ที่ผูกกับ PR")

    await page.goto(f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
    await shot(page, "14_egp_form.png")
    egp_name = (
        await page.locator('.o_field_widget[name="name"]').first.inner_text()
    ).strip()

    # create plan if button exists
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
                print("plan modal still open", await modal.inner_text())
        await page.wait_for_timeout(1000)
        await shot(page, "17_plan_created.png")
    else:
        print("ไม่มีปุ่มสร้างแผนบนหน้านี้ — บันทึกสถานะไว้")
        await shot(page, "15_no_plan_btn.png")

    # project fields
    for field, value in (
        ("egp_project_reference", "P777777777"),
        ("egp_reference", "P777777777"),
        ("egp_project_name", "ซื้อครุภัณฑ์ CCTV-16 วิธีเฉพาะเจาะจง"),
    ):
        box = page.locator(f'.o_field_widget[name="{field}"] input, .o_field_widget[name="{field}"] textarea')
        if await box.count():
            await box.first.click()
            await box.first.fill(value)
    # payment disbursement if selection
    pay = page.locator('.o_field_widget[name="egp_payment_type"] select, .o_field_widget[name="disbursement_type"] select')
    if await pay.count():
        options = await pay.first.locator("option").all_inner_texts()
        for opt in options:
            if "ไม่ผ่าน" in opt or "GFMIS" in opt or opt.strip():
                try:
                    await pay.first.select_option(label=opt.strip())
                    break
                except Exception:
                    continue
    await save_form(page)
    await shot(page, "18_egp_project.png")
    return egp_id, egp_name


async def winner_contract_po(page, egp_id):
    await page.goto(f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
    # consideration type
    cons = page.locator('.o_field_widget[name="egp_consideration_type"] select')
    if await cons.count():
        try:
            await cons.select_option(label="ราคาต่อรายการ")
        except Exception:
            await cons.select_option(index=1)
        await save_form(page)

    # add bidder
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
        # pick partner
        partner = modal.locator(
            '.o_field_widget[name="partner_id"] input, .o_field_widget[name="vendor_id"] input'
        ).first
        await partner.click()
        await partner.fill("ซิลลิค")
        await page.wait_for_timeout(600)
        item = page.locator(".o-autocomplete--dropdown-menu .dropdown-item").first
        await item.click()
        # select products / confirm
        await shot(page, "19_bid_wizard.png")
        confirm = modal.get_by_role("button", name=re.compile("บันทึก|ยืนยัน|เพิ่ม"))
        if await confirm.count():
            await confirm.first.click()
            try:
                await modal.wait_for(state="hidden", timeout=20000)
            except PlaywrightTimeout:
                print("bid wizard", (await modal.inner_text())[:500])
    await page.wait_for_timeout(800)
    await shot(page, "20_bids.png")

    # mark winner checkbox
    winner = page.locator('input[type="checkbox"][name="is_winner"], .o_field_boolean[name="is_winner"] input')
    if await winner.count():
        await winner.first.check()
        await save_form(page)
        await shot(page, "21_winner.png")

    # create contract
    contract_btn = page.locator(
        'button[name="action_create_purchase_contract"], button:has-text("สร้างสัญญา"), button:has-text("เข้าสู่การทำสัญญา")'
    )
    if await contract_btn.count() and await contract_btn.first.is_visible():
        await shot(page, "22_contract_btn.png")
        await contract_btn.first.click()
        await page.wait_for_timeout(2000)
        await shot(page, "23_contract_form.png")
        # set contract type สัญญาซื้อขาย
        ctype = page.locator('.o_field_widget[name="contract_type_id"] input')
        if await ctype.count():
            await ctype.click()
            await ctype.fill("สัญญาซื้อขาย")
            await page.wait_for_timeout(500)
            await page.locator(".o-autocomplete--dropdown-menu .dropdown-item").filter(
                has_text="สัญญาซื้อขาย"
            ).first.click()
        # egp control no
        for field, value in (
            ("egp_reference", "P88888888"),
            ("egp_control_no", "P88888888"),
            ("po_number", "CTR-CCTV-16"),
        ):
            box = page.locator(f'.o_field_widget[name="{field}"] input')
            if await box.count():
                await box.first.fill(value)
        await save_form(page)
        await shot(page, "24_contract_type.png")
        # confirm contract if button
        conf = page.locator(
            'button[name="action_confirm"], button:has-text("ยืนยันสัญญา"), button:has-text("ยืนยัน")'
        )
        if await conf.count() and await conf.first.is_visible():
            await conf.first.click()
            await page.wait_for_timeout(1500)
            await shot(page, "25_contract_confirmed.png")
        contract_url = page.url
    else:
        print("ไม่พบปุ่มสร้างสัญญา")
        contract_url = page.url

    # create PO from egp
    await page.goto(f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
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
                print("po wizard", (await modal.inner_text())[:600])
        await page.wait_for_timeout(2000)
        # may land on PO
        await shot(page, "28_po_form.png")
        # buttons for WA / QC
        await shot(page, "29_po_header_actions.png")
    else:
        print("ยังไม่มีปุ่มสร้าง PO — อาจต้องแนบประกาศผู้ชนะ/ลงนามก่อน")
        await shot(page, "26_no_po_btn.png")
    return contract_url


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=HEADLESS)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=2)
        page.set_default_timeout(30000)
        try:
            resume = os.environ.get("RESUME_PR_URL")
            if resume:
                pr_url = resume
                pr_name = os.environ.get("RESUME_PR_NAME", "")
            else:
                pr_name, pr_url = await create_pr(page)
            meta["pr_name"] = pr_name
            meta["pr_url"] = pr_url
            pr_url = await assign_and_verify(page, pr_name)
            meta["pr_url"] = pr_url
            egp_id, egp_name = await send_egp_and_plan(page, pr_url)
            meta["egp_id"] = egp_id
            meta["egp_name"] = egp_name
            contract_url = await winner_contract_po(page, egp_id)
            meta["contract_url"] = contract_url
            # final PO search
            found = await rpc(
                page,
                "purchase.order",
                "search_read",
                [[["origin", "ilike", pr_name]]],
                {"fields": ["name", "state", "picking_ids", "amount_total"], "limit": 3, "order": "id desc"},
            )
            meta["pos"] = found.get("result")
            print("META", json.dumps(meta, ensure_ascii=False, indent=2))
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error.png"), full_page=True)
            META.write_text(json.dumps({"error": str(error), **meta}, ensure_ascii=False, indent=2), encoding="utf-8")
            raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
