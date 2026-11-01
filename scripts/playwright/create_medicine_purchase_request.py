#!/usr/bin/env python3
"""เปิดหน้าต่างเบราว์เซอร์แล้วทำใบขอซื้อยาตามขั้นตอนใน purchase_flows.md

หัวใบ รายการสินค้า และขั้นตอนอ่านจาก purchase_flows.md
ราคาต่อหน่วยให้ระบบดึงจากคำของบที่อนุมัติ (ไม่พิมพ์ราคาเอง)
ขั้นตอนในไฟล์นั้นต่อเนื่องถึงการสร้างรายการ e-GP และมีการอนุมัติแบบทดสอบ ใช้กับเครื่องทดสอบเท่านั้น

รัน:
    pip install playwright
    playwright install chromium
    python scripts/playwright/create_medicine_purchase_request.py

รหัสผ่านอ่านจากตัวแปร ODOO_PASSWORD ถ้าไม่ตั้งไว้จะใช้รหัสของผู้ใช้ทดสอบในหน้า login
ตั้ง HEADLESS=1 เพื่อไม่แสดงหน้าต่าง และตั้ง SCREENSHOT_PATH เพื่อกำหนดที่เก็บภาพเมื่อพลาด
ปรับความเร็วได้ด้วย SLOW_MO (มิลลิวินาทีต่อการกระทำ) และ PAGE_PAUSE (วินาทีที่พักในแต่ละหน้า)
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from odoo_session import BASE_URL, launch_browser, login_as

FLOW_FILE = Path(__file__).with_name("purchase_flows.md")
USER = os.environ.get("ODOO_USER", "uat.dept")
HEADLESS = os.environ.get("HEADLESS") == "1"
SLOW_MO = int(os.environ.get("SLOW_MO", "0" if HEADLESS else "1000"))
PAGE_PAUSE = float(os.environ.get("PAGE_PAUSE", "0" if HEADLESS else "2"))


def split_kv(text):
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def load_flow(path):
    """อ่านกฎจาก purchase_flows.md แล้วคืนค่าที่อนุญาต หัวใบ และรายการสินค้า."""
    allowed = {}
    order = {}
    products = []
    notes = []
    procurement_notes = []
    documents = []
    section = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            title = line[3:].strip()
            if "ใช้ได้" in title:
                section = "allowed"
            elif "ใบที่จะเปิด" in title:
                section = "order"
            elif "งานจัดซื้อ" in title:
                section = "procurement"
            elif "เอกสารและผู้ลงนาม" in title:
                section = "documents"
            else:
                section = None
            continue
        if section == "documents":
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if line.startswith("|") and cells[0] != "เอกสาร" and set(cells[0]) - set("-: "):
                documents.append(
                    {
                        "label": cells[0],
                        "owner": cells[1],
                        "signers": [
                            dict(zip(("login", "name"), map(str.strip, signer.split("="))))
                            for signer in cells[2].split(",")
                        ],
                    }
                )
            continue
        if section == "procurement":
            if line:
                procurement_notes.append(line.lstrip("- ").strip())
            continue
        if section == "allowed" and line.startswith("- "):
            key, value = split_kv(line[2:])
            allowed[key] = [part.strip() for part in value.split(",") if part.strip()]
            continue
        if section != "order":
            continue
        if line.startswith("- ") or line.startswith("ส่ง"):
            body = line[2:].strip() if line.startswith("- ") else line
            if ":" in body:
                key, value = split_kv(body)
                order[key] = value
            else:
                notes.append(body)
            continue
        if not line.startswith("|"):
            if line:
                notes.append(line)
            continue
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0] in ("รหัสสินค้า", "") or set(cells[0]) <= set("-: "):
            continue
        products.append(
            {
                "code": cells[0],
                "qty": cells[1],
                "expected_price": parse_amount(cells[2]) if len(cells) > 2 else 0.0,
            }
        )
    if not products:
        raise SystemExit("ในไฟล์กฎยังไม่มีรายการสินค้า")
    for key in (
        "ประเภทพัสดุ",
        "ประเภทการจัดซื้อ",
        "วิธีการจัดซื้อจัดจ้าง",
        "ประเภทสิ่งที่จะซื้อ",
    ):
        choices = allowed.get(key) or []
        if order.get(key) not in choices:
            raise SystemExit(
                "%s = %s ไม่อยู่ในวิธีซื้อที่ใช้ได้" % (key, order.get(key) or "-")
            )
    note_text = " ".join(notes)
    steps = {
        "committee": "คณะกรรมการ" in note_text,
        "committee_role": "ประธาน" if "ประธาน" in note_text else "คณะกรรมการ",
        "budget": "ตรวจสอบงบ" in note_text,
        "send": "ส่งพัสดุ" in note_text,
        "to_egp": "e-GP" in " ".join(procurement_notes),
        "procurement_user": "uat.procurement",
        "documents": documents,
    }
    return order, products, steps


def parse_amount(text):
    digits = re.sub(r"[^\d.]", "", text or "")
    return float(digits) if digits else 0.0


async def ensure_m2o(page, field_name, query, option_text, exact=True):
    field = page.locator(f'.o_form_view .o_field_widget[name="{field_name}"]').first
    current = await field.locator("input.o_input").first.input_value()
    if option_text in (current or ""):
        return
    await fill_m2o(page, field_name, query, option_text, exact=exact)


async def fill_m2o(page, field_name, query, option_text, exact=True):
    field = page.locator(f'.o_form_view .o_field_widget[name="{field_name}"]').first
    await field.scroll_into_view_if_needed()
    box = field.locator("input.o_input").first
    await box.click()
    await box.fill("")
    await box.press_sequentially(query, delay=40)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    target = menu.get_by_text(option_text, exact=exact).first
    try:
        await target.wait_for(state="visible", timeout=15000)
    except PlaywrightTimeout as error:
        sample = " ".join((await menu.inner_text()).split())[:300]
        raise RuntimeError(
            f"ไม่พบตัวเลือก {option_text} ในช่อง {field_name}: {sample}"
        ) from error
    await target.click()
    await page.wait_for_timeout(400)


async def fill_selection(page, field_name, label):
    field = page.locator(f'.o_form_view .o_field_widget[name="{field_name}"]').first
    await field.scroll_into_view_if_needed()
    await field.locator("select").select_option(label=label)
    await page.wait_for_timeout(300)


async def save_form(page):
    save = page.locator(".o_form_button_save")
    if await save.is_visible():
        await save.click()
    await page.locator(".o_form_view").wait_for(state="visible")
    await page.wait_for_timeout(800)
    error = page.locator(".o_error_dialog, .o_dialog_error, .modal-content .o_dialog_warning")
    if await error.count() and await error.first.is_visible():
        message = (await error.first.inner_text()).strip()
        raise RuntimeError(message)


async def add_product_line(page, item):
    lines = page.locator('.o_field_widget[name="line_ids"]')
    await lines.locator(".o_field_x2many_list_row_add a").click()
    row = lines.locator("tr.o_selected_row")
    product = row.locator('[name="product_id"] input').first
    await product.click()
    await product.fill("")
    await product.press_sequentially(item["code"], delay=40)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    await menu.get_by_text(item["code"]).first.wait_for(state="visible", timeout=15000)
    await menu.get_by_text(item["code"]).first.click()

    price = row.locator('[name="budget_unit_price"] input').first
    await page.wait_for_timeout(800)
    unit_price = parse_amount(await price.input_value())
    expected = item["expected_price"]
    if expected and abs(unit_price - expected) > 0.01:
        raise RuntimeError(
            "สินค้า %s ราคาต่อหน่วยที่ได้คือ %.2f ไม่ใช่ราคาในงบ %.2f"
            % (item["code"], unit_price, expected)
        )

    qty = row.locator('[name="product_qty"] input').first
    await qty.click()
    await qty.fill(item["qty"])
    await qty.press("Tab")
    budget_post = item.get("budget_post")
    if budget_post:
        post = row.locator('[name="budget_post_id"] input').first
        if budget_post not in (await post.input_value()):
            await post.click()
            await post.fill("")
            await post.press_sequentially("ยาเอกซเรย์", delay=40)
            menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
            await menu.wait_for(state="visible", timeout=10000)
            await menu.get_by_text(budget_post, exact=False).first.click()
    await save_form(page)
    print(
        "สินค้า",
        item["code"],
        "จำนวน",
        item["qty"],
        "ราคาต่อหน่วยจากงบ",
        f"{unit_price:,.2f}",
    )


async def click_tab(page, label):
    tab = page.get_by_role("tab", name=label)
    await tab.click()
    await page.wait_for_timeout(400)


async def add_committee(page, role_label):
    await click_tab(page, "คณะกรรมการ")
    lines = page.locator('.o_field_widget[name="work_acceptance_committee_ids"]')
    await lines.locator(".o_field_x2many_list_row_add a").click()
    row = lines.locator("tr.o_selected_row")
    person = row.locator('[name="employee_id"] input').first
    await person.click()
    await person.fill("")
    await person.press_sequentially("กรรมการตรวจรับ คนที่ 1", delay=40)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    await menu.get_by_text("กรรมการตรวจรับ คนที่ 1").first.wait_for(
        state="visible", timeout=15000
    )
    await menu.get_by_text("กรรมการตรวจรับ คนที่ 1").first.click()
    await row.locator('[name="approve_role"] select').select_option(label=role_label)
    await save_form(page)
    print("ใส่คณะกรรมการตรวจรับ: ผู้ทดสอบกรรมการตรวจรับ คนที่ 1 บทบาท", role_label)


async def check_budget(page):
    await page.locator('button[name="action_check_budget_status"]').click()
    notice = page.locator(".o_notification_content, .o_notification_title").first
    await notice.wait_for(state="visible", timeout=20000)
    text = " ".join((await page.locator(".o_notification").first.inner_text()).split())
    print("ผลตรวจงบ:", text)
    if "ฟิลด์ไม่ถูกต้อง" in text:
        raise RuntimeError(text)
    if "ไม่เพียงพอ" in text or "ไม่พอ" in text:
        raise RuntimeError("งบประมาณไม่พอ จึงไม่ส่งพัสดุ: %s" % text)
    await page.locator(".o_form_view").wait_for(state="visible")
    await page.wait_for_timeout(800)


async def pick_m2o(page, scope, field_name, query, option_text):
    box = scope.locator(f'[name="{field_name}"] input').first
    await box.click()
    await box.fill("")
    await box.press_sequentially(query, delay=30)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    option = menu.get_by_text(option_text, exact=True).first
    await option.wait_for(state="visible", timeout=15000)
    await option.click()
    await page.wait_for_timeout(500)


async def pause(page):
    await page.wait_for_timeout(PAGE_PAUSE * 1000)


async def open_record(page, url):
    await page.goto(url, wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for(state="visible", timeout=20000)
    await pause(page)


async def add_document(page, document):
    """สร้างเอกสารจากแท็บเอกสารที่เกี่ยวข้อง แล้วส่งลงนาม คืนเลขและ URL ของเอกสาร."""
    await click_tab(page, "เอกสารที่เกี่ยวข้อง")
    await page.locator('button[name="action_open_add_studio_document_wizard"]').click()
    modal = page.locator(".modal").last
    await modal.locator('[name="document_type_id"]').wait_for(state="visible")
    await pick_m2o(page, modal, "document_type_id", document["label"], document["label"])
    await page.wait_for_timeout(800)
    for signer in document["signers"]:
        approvers = modal.locator('[name="approver_ids"]')
        await approvers.locator(".o_field_x2many_list_row_add a").click()
        row = approvers.locator("tr.o_selected_row")
        await pick_m2o(page, row, "user_id", signer["name"], signer["name"])
    await modal.locator('button[name="action_confirm"]').click()
    send = page.locator('button[name="action_send_for_signature"]')
    await send.wait_for(state="visible", timeout=60000)
    match = re.search(r"vpk\.document\.studio\.document/(\d+)", page.url)
    url = f"{BASE_URL}/odoo/vpk.document.studio.document/{match.group(1)}"
    name = (await page.locator('.o_field_widget[name="name"]').first.inner_text()).strip()
    await pause(page)
    await send.click()
    # ระบบสร้าง PDF ตอนส่งลงนาม ต้องรอให้จบก่อนเปลี่ยนผู้ใช้
    await send.wait_for(state="hidden", timeout=120000)
    await pause(page)
    print("ส่งลงนามแล้ว:", document["label"], name)
    return name, url


async def draw_signature(page, modal):
    canvas = modal.locator("canvas").first
    await canvas.wait_for(state="visible", timeout=10000)
    box = await canvas.bounding_box()
    await page.mouse.move(box["x"] + 40, box["y"] + 40)
    await page.mouse.down()
    for step in range(1, 6):
        await page.mouse.move(
            box["x"] + 40 + step * 40, box["y"] + 40 + (step % 2) * 40, steps=4
        )
    await page.mouse.up()


async def sign_document(page, url, login):
    await login_as(page, login)
    await open_record(page, url)
    await page.locator('button[name="action_open_sign_viewer"]').click(timeout=20000)
    viewer = page.locator(".o_vpk_sign_pdf_container").first
    await viewer.wait_for(state="visible", timeout=20000)
    pdf = page.frame_locator(".o_vpk_sign_pdf_iframe").locator("#viewerContainer")
    await pdf.locator(".page").first.wait_for(state="visible", timeout=30000)
    await pause(page)
    await pdf.evaluate("(element) => { element.scrollTop = element.scrollHeight; }")
    await page.wait_for_function(
        """() => {
            const button = document.querySelector('.o_vpk_sign_pdf_footer button.btn-success');
            return button && !button.disabled;
        }""",
        timeout=20000,
    )
    await page.locator(".o_vpk_sign_pdf_footer button.btn-success").click()
    modal = page.locator(".modal:has(canvas)").last
    await draw_signature(page, modal)
    async with page.expect_response(
        lambda response: "action_apply_signature" in response.url
    ) as signed:
        await modal.locator(".modal-footer button.btn-primary").click()
    result = await (await signed.value).json()
    if "error" in result:
        data = result["error"].get("data") or {}
        raise RuntimeError(f"ลงนามไม่สำเร็จ ({login}): {data.get('message') or result['error']}")
    await viewer.wait_for(state="hidden", timeout=60000)
    print("ลงนามแล้ว:", login)


async def complete_document(page, document):
    """สร้างเอกสาร ส่งลงนาม แล้วลงนามตามลำดับ."""
    name, url = await add_document(page, document)
    for signer in document["signers"]:
        await sign_document(page, url, signer["login"])
    print(f"เอกสารลงนามครบ {document['label']}: {name}")


async def create_purchase_request(page, order, products, steps):
    await page.goto(f"{BASE_URL}/odoo/action-577", wait_until="domcontentloaded")
    await page.locator(".o_list_button_add, .o_form_button_create").first.click()
    await page.locator(".o_form_view").wait_for(state="visible")

    await fill_m2o(page, "procurement_type_id", order["ประเภทพัสดุ"], order["ประเภทพัสดุ"])
    await fill_m2o(
        page, "purchase_type_id", order["ประเภทการจัดซื้อ"], order["ประเภทการจัดซื้อ"]
    )
    await fill_m2o(
        page,
        "procurement_method_id",
        order["วิธีการจัดซื้อจัดจ้าง"],
        order["วิธีการจัดซื้อจัดจ้าง"],
    )
    await fill_selection(page, "budget_section_key", order["ประเภทสิ่งที่จะซื้อ"])
    if order["ประเภทสิ่งที่จะซื้อ"] == "วัสดุ":
        await page.locator('.o_field_widget[name="budget_group_id"]').wait_for(
            state="visible"
        )
        await fill_m2o(page, "budget_group_id", order["กลุ่มงบประมาณ"], order["กลุ่มงบประมาณ"])
    await fill_m2o(
        page,
        "budget_analytic_account_id",
        order["หน่วยงานงบประมาณ"],
        order["หน่วยงานงบประมาณ"],
        exact=False,
    )
    await fill_m2o(page, "budget_fund_source_id", order["แหล่งเงิน"], order["แหล่งเงิน"])
    if order.get("หมวดงบประมาณ"):
        await fill_m2o(
            page,
            "budget_post_id",
            "ยาเอกซเรย์",
            order["หมวดงบประมาณ"],
            exact=False,
        )
    warehouse = order["รับสินค้าเข้าคลัง"]
    await ensure_m2o(page, "picking_type_id", warehouse.split(":")[0], warehouse, exact=False)

    description = page.locator('.o_field_widget[name="description"] textarea').first
    await description.click()
    await description.fill(order["คำอธิบาย"])
    await save_form(page)
    await pause(page)

    for item in products:
        item["budget_post"] = order.get("หมวดงบประมาณ") or ""
        await add_product_line(page, item)

    name = (await page.locator('.o_field_widget[name="name"]').first.inner_text()).strip()
    print("สร้างใบขอซื้อแล้ว:", name)
    print("วิธีซื้อ:", order["วิธีการจัดซื้อจัดจ้าง"])
    if steps["committee"]:
        await add_committee(page, steps["committee_role"])
    if steps["budget"]:
        await check_budget(page)
        closer = page.locator(".o_notification .o_notification_close")
        if await closer.count():
            await closer.first.click()
    pr_url = page.url
    for document in steps["documents"]:
        if document["owner"] == USER:
            await complete_document(page, document)
            await login_as(page, USER)
            await open_record(page, pr_url)
    if steps["send"]:
        await page.locator('button[name="action_send_to_procurement"]').click()
        await page.wait_for_timeout(1200)
        print("ส่งพัสดุแล้ว")
    return name


async def continue_to_egp(page, pr_name, user, documents):
    await login_as(page, user)
    await page.goto(f"{BASE_URL}/odoo/action-979", wait_until="domcontentloaded")
    card = page.locator(".o_vpk_inbox_card", has_text=pr_name).first
    await card.wait_for(state="visible", timeout=20000)
    claim = card.locator('button[name="action_claim_procurement"]')
    if await claim.count() and await claim.is_visible():
        await claim.click()
        await page.wait_for_timeout(1200)
        print("รับงานแล้ว:", pr_name)
    await card.locator('button[name="action_open_procurement_work"]').click()
    await page.locator(".o_form_view").first.wait_for(state="visible", timeout=20000)
    pr_url = page.url
    for document in documents:
        if document["owner"] == user:
            await complete_document(page, document)
            await login_as(page, user)
            await open_record(page, pr_url)
    verify = page.locator('button[name="action_verify_procurement"]')
    if await verify.count() and await verify.first.is_visible():
        await verify.first.click()
        await page.wait_for_timeout(1200)
        print("พัสดุยืนยันการตรวจสอบแล้ว:", pr_name)
    send = page.locator('button[name="action_send_to_egp"]')
    await send.wait_for(state="visible", timeout=20000)
    await send.click()
    await page.locator('button[name="make_purchase_requisition"]').click()
    await page.locator(".modal").wait_for(state="hidden", timeout=20000)
    egp_row = page.locator(".o_data_row", has_text=pr_name).first
    egp_cell = egp_row.locator('td[name="name"]')
    await egp_cell.wait_for(state="visible", timeout=20000)
    egp_name = (await egp_cell.inner_text()).strip()
    print("สร้างรายการ e-GP แล้ว:", egp_name)
    return egp_name


async def main():
    order, products, steps = load_flow(FLOW_FILE)
    async with async_playwright() as playwright:
        browser = await launch_browser(
            playwright, headless=HEADLESS, slow_mo=SLOW_MO
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 1600})
        page = await context.new_page()
        try:
            resume = os.environ.get("RESUME_PR")
            if resume:
                await continue_to_egp(
                    page, resume, steps["procurement_user"], steps["documents"]
                )
            else:
                await login_as(page, USER)
                pr_name = await create_purchase_request(page, order, products, steps)
                if steps.get("to_egp"):
                    await continue_to_egp(
                        page, pr_name, steps["procurement_user"], steps["documents"]
                    )
            hold = int(os.environ.get("HOLD_SECONDS", "0" if HEADLESS else "20"))
            print(f"เปิดหน้าต่างค้างไว้ {hold} วินาที")
            await page.wait_for_timeout(hold * 1000)
        except Exception as error:
            print("ทำรายการไม่สำเร็จ:", error)
            if page.is_closed():
                print("หน้าต่างเบราว์เซอร์ถูกปิดระหว่างทำรายการ")
                return 1
            shot = Path(os.environ.get("SCREENSHOT_PATH", "/tmp/playwright-pr-error.png"))
            await page.screenshot(path=str(shot), full_page=True)
            print("ภาพหน้าจอ:", shot)
            if not HEADLESS:
                await page.wait_for_timeout(8000)
            return 1
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
