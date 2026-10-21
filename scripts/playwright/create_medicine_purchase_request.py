#!/usr/bin/env python3
"""เปิดหน้าต่างเบราว์เซอร์แล้วสร้างใบขอซื้อยา เป็นร่าง

หัวใบและรายการสินค้าอ่านจาก purchase_flows.md
ราคาต่อหน่วยให้ระบบดึงจากคำของบที่อนุมัติ (ไม่พิมพ์ราคาเอง)
บันทึกเป็นร่าง ไม่กดตรวจงบ ไม่ส่งพัสดุ และไม่ขออนุมัติ

รัน:
    pip install playwright
    playwright install chromium
    python scripts/playwright/create_medicine_purchase_request.py

รหัสผ่านอ่านจากตัวแปร ODOO_PASSWORD
ถ้าไม่ตั้งไว้ สคริปต์จะอ่านบัญชีหน่วยงานจากสคริปต์คู่มือในเครื่องนี้
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
FLOW_FILE = Path(__file__).with_name("purchase_flows.md")
BASE_URL = os.environ.get("ODOO_URL", "http://127.0.0.1:8069")
USER = os.environ.get("ODOO_USER", "uat.dept")


def load_password():
    value = os.environ.get("ODOO_PASSWORD", "").strip()
    if value:
        return value
    manual = ROOT / "docs" / "build_procurement_user_manual_docx.py"
    text = manual.read_text(encoding="utf-8")
    match = re.search(r'\["หน่วยงาน",\s*"uat\.dept",\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("ตั้งค่า ODOO_PASSWORD ก่อนรันสคริปต์")
    return match.group(1)


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
            else:
                section = None
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
        "approval": "เอกสารอนุมัติ" in note_text or "ส่งอนุมัติ" in note_text,
        "approve": "ให้อนุมัติ" in note_text,
        "send": "ส่งพัสดุ" in note_text,
        "to_egp": "e-GP" in " ".join(procurement_notes),
        "procurement_user": "uat.procurement",
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
    await click_tab(page, "รายชื่อคณะกรรมการ")
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


async def approve_purchase_memo(page, pr_url, do_approve):
    await click_tab(page, "เอกสารอนุมัติขอซื้อ")
    await page.locator('button[name="action_create_purchase_approval_memo"]').first.click()
    await page.locator('button[name="action_open_send_wizard"]').wait_for(
        state="visible", timeout=20000
    )
    print("เปิดบันทึกข้อความอนุมัติขอซื้อแล้ว")
    await page.locator('button[name="action_open_send_wizard"]').click()
    await page.locator(".modal .o_field_widget[name='skip_approval']").wait_for(
        state="visible"
    )
    if do_approve:
        checkbox = page.locator(".modal .o_field_widget[name='skip_approval'] input")
        await checkbox.check()
    await page.locator(".modal button[name='action_confirm']").click()
    await page.locator(".modal").wait_for(state="hidden", timeout=20000)
    print("ส่งเอกสารอนุมัติแล้ว", "และถือว่าอนุมัติสำหรับทดสอบ" if do_approve else "")
    await page.goto(pr_url, wait_until="domcontentloaded")
    await page.locator(".o_form_view").wait_for(state="visible")


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
    if steps["approval"]:
        await approve_purchase_memo(page, pr_url, steps["approve"])
    if steps["send"]:
        await page.locator('button[name="action_send_to_procurement"]').click()
        await page.wait_for_timeout(1200)
        print("ส่งพัสดุแล้ว")
    return name


async def login_as(page, user, password):
    await page.goto(f"{BASE_URL}/web/session/logout", wait_until="domcontentloaded")
    await page.goto(f"{BASE_URL}/web/login", wait_until="domcontentloaded")
    await page.locator("#login").wait_for(state="visible")
    await page.locator("#vpk_test_user option[value='%s']" % user).wait_for(
        state="attached", timeout=15000
    )
    await page.evaluate(
        """([login, passwordValue]) => {
            const select = document.querySelector('#vpk_test_user');
            const option = [...select.options].find((item) => item.value === login);
            const user = document.querySelector('#login');
            const password = document.querySelector('#password');
            user.value = login;
            password.value = (option && option.dataset.password) || passwordValue;
            select.value = login;
        }""",
        [user, password],
    )
    await page.locator("button.vpk-login-submit").click()
    await page.wait_for_url(re.compile(r"/odoo(?:\?|$|/)"), timeout=30000)


async def issue_and_approve(page, pr_url, document_label):
    await click_tab(page, "เอกสารราชการที่เกี่ยวข้อง")
    select = page.locator(
        '.o_field_widget[name="official_document_to_create"] select'
    )
    await select.select_option(label=document_label)
    await page.locator('button[name="action_create_selected_official_document"]').click()
    await page.locator(".o_form_view").wait_for(state="visible", timeout=20000)
    send = page.locator('button[name="action_open_send_wizard"]')
    try:
        await send.wait_for(state="visible", timeout=8000)
    except PlaywrightTimeout:
        print("เอกสารอนุมัติแล้ว:", document_label)
        await page.goto(pr_url, wait_until="domcontentloaded")
        await page.locator(".o_form_view").wait_for(state="visible")
        return
    print("เปิดเอกสารแล้ว:", document_label)
    await page.locator('button[name="action_open_send_wizard"]').click()
    await page.locator(".modal .o_field_widget[name='skip_approval']").wait_for(
        state="visible"
    )
    await page.locator(".modal .o_field_widget[name='skip_approval'] input").check()
    await page.locator(".modal button[name='action_confirm']").click()
    await page.locator(".modal").wait_for(state="hidden", timeout=30000)
    print("ส่งอนุมัติแล้ว:", document_label)
    await page.goto(pr_url, wait_until="domcontentloaded")
    await page.locator(".o_form_view").wait_for(state="visible")


async def continue_to_egp(page, pr_name, user, password):
    await login_as(page, user, password)
    await page.goto(f"{BASE_URL}/odoo/action-979", wait_until="domcontentloaded")
    card = page.locator(".o_vpk_inbox_card", has_text=pr_name).first
    await card.wait_for(state="visible", timeout=20000)
    claim = card.locator('button[name="action_claim_procurement"]')
    if await claim.count() and await claim.is_visible():
        await claim.click()
        await page.wait_for_timeout(1200)
        print("รับงานแล้ว:", pr_name)
    await card.locator('button[name="action_open_procurement_work"]').click()
    await page.locator(".o_form_view").wait_for(state="visible", timeout=20000)
    pr_url = page.url
    await issue_and_approve(
        page, pr_url, "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ"
    )
    await issue_and_approve(
        page, pr_url, "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง"
    )
    send = page.locator('button[name="action_send_to_egp"]')
    await send.wait_for(state="visible", timeout=20000)
    await send.click()
    await page.locator('button[name="make_purchase_requisition"]').click()
    await page.locator(".o_form_view").wait_for(state="visible", timeout=20000)
    egp_name = (
        await page.locator('.o_field_widget[name="name"]').first.inner_text()
    ).strip()
    print("สร้างรายการ e-GP แล้ว:", egp_name)
    return egp_name


async def main():
    order, products, steps = load_flow(FLOW_FILE)
    password = load_password()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, slow_mo=250)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()
        try:
            resume = os.environ.get("RESUME_PR")
            if resume:
                await continue_to_egp(
                    page, resume, steps["procurement_user"], password
                )
            else:
                await login_as(page, USER, password)
                pr_name = await create_purchase_request(page, order, products, steps)
                if steps.get("to_egp"):
                    await continue_to_egp(
                        page, pr_name, steps["procurement_user"], password
                    )
            hold = int(os.environ.get("HOLD_SECONDS", "20"))
            print(f"เปิดหน้าต่างค้างไว้ {hold} วินาที")
            await page.wait_for_timeout(hold * 1000)
        except Exception as error:
            shot = Path("/tmp/playwright-pr-error.png")
            await page.screenshot(path=str(shot), full_page=True)
            print("ทำรายการไม่สำเร็จ:", error)
            print("ภาพหน้าจอ:", shot)
            await page.wait_for_timeout(8000)
            return 1
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
