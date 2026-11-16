#!/usr/bin/env python3
"""ต่อ UAT จาก EGP ของ CCTV-16: ผู้ชนะ → สัญญาซื้อขาย → สร้าง PO + จับภาพ"""
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
    open_record,
    save_form,
)
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/cctv16_specific")
META = OUT / "meta.json"
EGP_ID = int(os.environ.get("EGP_ID", "83"))
PR_ID = int(os.environ.get("PR_ID", "178"))
PROC_OWNER = "uat.equipment"
VENDOR_QUERY = os.environ.get("VENDOR_QUERY", "ซิลลิค")
HEADLESS = os.environ.get("HEADLESS", "1") == "1"


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


async def dismiss_error(page):
    dialog = page.locator(".o_error_dialog, .modal-content .o_dialog_error, .o_technical_modal")
    if await dialog.count() and await dialog.first.is_visible():
        print("dismiss error:", (await dialog.first.inner_text())[:200])
        close = dialog.locator("button:has-text('Close'), button:has-text('ปิด'), .btn-primary, .btn-secondary").first
        if await close.count():
            await close.click()
            await page.wait_for_timeout(500)


async def open_egp(page):
    await page.goto(
        f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
        wait_until="domcontentloaded",
    )
    await page.locator(".o_form_view").first.wait_for(state="visible", timeout=25000)
    await dismiss_error(page)


async def ensure_consideration(page):
    cons = page.locator('.o_field_widget[name="egp_consideration_type"] select')
    if await cons.count():
        current = await cons.input_value()
        if not current:
            try:
                await cons.select_option(label="ราคาต่อรายการ")
            except Exception:
                await cons.select_option(index=1)
            await save_form(page)


async def add_bidder_ui(page):
    tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา|เปรียบเทียบ"))
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(500)

    # already have bids?
    info = await rpc(
        page,
        "purchase.requisition",
        "read",
        [[EGP_ID], ["egp_bid_ids", "egp_bid_line_ids", "egp_consideration_type"]],
    )
    result = (info.get("result") or [{}])[0]
    if result.get("egp_bid_ids"):
        print("already has bids", result.get("egp_bid_ids"))
        return

    add = page.locator(
        'button[name="action_open_egp_bid_import_wizard"], button:has-text("เพิ่มผู้เสนอราคา")'
    )
    await add.first.wait_for(state="visible", timeout=15000)
    await add.first.click()
    modal = page.locator(".modal-content").last
    await modal.wait_for(state="visible", timeout=15000)

    partner = modal.locator('.o_field_widget[name="partner_id"] input').first
    await partner.click()
    await partner.fill("")
    await partner.press_sequentially(VENDOR_QUERY, delay=40)
    menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
    await menu.wait_for(state="visible", timeout=10000)
    await menu.locator(".dropdown-item, a").first.click()
    await page.wait_for_timeout(1000)

    # ensure at least one product line selected
    checks = modal.locator('.o_field_widget[name="selected"] input[type="checkbox"], input[type="checkbox"]')
    count = await checks.count()
    print("wizard checkboxes", count)
    for i in range(count):
        box = checks.nth(i)
        if not await box.is_checked():
            await box.check()

    await shot(page, "19_bid_wizard.png")
    confirm = modal.locator('button[name="action_confirm"], button:has-text("ยืนยัน"), button:has-text("บันทึก")')
    await confirm.first.click()
    try:
        await modal.wait_for(state="hidden", timeout=20000)
    except PlaywrightTimeout:
        text = (await modal.inner_text())[:600]
        print("bid wizard still open", text)
        await dismiss_error(page)
        raise RuntimeError(f"เพิ่มผู้เสนอราคาไม่สำเร็จ: {text}")


async def set_prices_and_winner(page):
    await open_egp(page)
    tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา|เปรียบเทียบ"))
    if await tab.count():
        await tab.first.click()
        await page.wait_for_timeout(400)

    # fill price on bid lines via UI if editable
    price_inputs = page.locator(
        '.o_field_widget[name="egp_bid_line_ids"] [name="price_unit"] input, '
        '.o_list_table [name="price_unit"] input'
    )
    if await price_inputs.count():
        await price_inputs.first.click()
        await price_inputs.first.fill("600000")
        await price_inputs.first.press("Tab")
        await save_form(page)

    # mark winner via RPC for reliability then refresh for screenshot
    bids = await rpc(
        page,
        "purchase.requisition.egp.bid",
        "search_read",
        [[["requisition_id", "=", EGP_ID]]],
        {"fields": ["id", "partner_id", "is_winner", "amount_total", "line_ids"]},
    )
    print("bids", bids.get("result"))
    bid_rows = bids.get("result") or []
    if not bid_rows:
        # create bid+line via RPC fallback
        partners = await rpc(
            page,
            "res.partner",
            "search_read",
            [[["name", "ilike", VENDOR_QUERY], ["supplier_rank", ">", 0]]],
            {"fields": ["id", "name"], "limit": 1},
        )
        partner = (partners.get("result") or [None])[0]
        if not partner:
            raise RuntimeError("ไม่พบผู้ขายสำหรับเสนอราคา")
        lines = await rpc(
            page,
            "purchase.requisition.line",
            "search_read",
            [[["requisition_id", "=", EGP_ID]]],
            {"fields": ["id", "product_id", "product_qty", "product_uom_id", "product_description_variants"]},
        )
        req_line = (lines.get("result") or [None])[0]
        if not req_line:
            raise RuntimeError("ไม่พบบรรทัดสินค้าใน e-GP")
        created = await rpc(
            page,
            "purchase.requisition.egp.bid.line",
            "create",
            [
                {
                    "requisition_id": EGP_ID,
                    "partner_id": partner["id"],
                    "requisition_line_id": req_line["id"],
                    "product_id": req_line["product_id"][0],
                    "name": req_line.get("product_description_variants") or "CCTV-16",
                    "product_qty": req_line.get("product_qty") or 1.0,
                    "product_uom_id": req_line["product_uom_id"][0]
                    if req_line.get("product_uom_id")
                    else False,
                    "price_unit": 600000.0,
                    "is_winner": True,
                }
            ],
        )
        print("created bid line", created)
        if created.get("error"):
            raise RuntimeError(created["error"])
    else:
        bid_id = bid_rows[0]["id"]
        # set amount / winner
        write_bid = await rpc(
            page,
            "purchase.requisition.egp.bid",
            "write",
            [[bid_id], {"is_winner": True, "amount_total": 600000.0}],
        )
        print("write bid winner", write_bid)
        # also mark bid lines
        line_ids = bid_rows[0].get("line_ids") or []
        if line_ids:
            write_lines = await rpc(
                page,
                "purchase.requisition.egp.bid.line",
                "write",
                [line_ids, {"is_winner": True, "price_unit": 600000.0}],
            )
            print("write bid lines", write_lines)

    await open_egp(page)
    tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา|เปรียบเทียบ"))
    if await tab.count():
        await tab.first.click()
    await page.wait_for_timeout(500)
    await shot(page, "20_bids.png")
    await shot(page, "21_winner.png")


async def create_and_confirm_contract(page):
    await open_egp(page)
    # try header/compare button
    contract_btn = page.locator(
        'button[name="action_create_purchase_contract"]'
    )
    if not await contract_btn.count() or not await contract_btn.first.is_visible():
        tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา|เปรียบเทียบ"))
        if await tab.count():
            await tab.first.click()
            await page.wait_for_timeout(400)
    await contract_btn.first.wait_for(state="visible", timeout=15000)
    await shot(page, "22_contract_btn.png")
    await contract_btn.first.click()
    await page.wait_for_timeout(2000)
    await dismiss_error(page)

    # may open list or form
    if "purchase.contract" not in page.url:
        # open latest contract for this egp via RPC
        found = await rpc(
            page,
            "purchase.contract",
            "search_read",
            [[["requisition_id", "=", EGP_ID]]],
            {"fields": ["id", "name", "state"], "limit": 1, "order": "id desc"},
        )
        rows = found.get("result") or []
        if not rows:
            raise RuntimeError("สร้างสัญญาไม่สำเร็จ — ไม่พบทะเบียนสัญญา")
        await page.goto(
            f"{BASE_URL}/odoo/purchase.contract/{rows[0]['id']}",
            wait_until="domcontentloaded",
        )
        await page.locator(".o_form_view").first.wait_for()

    await shot(page, "23_contract_form.png")

    # set type สัญญาซื้อขาย (fixed)
    ctype = page.locator('.o_field_widget[name="contract_type_id"] input')
    if await ctype.count() and await ctype.is_editable():
        await ctype.click()
        await ctype.fill("")
        await ctype.press_sequentially("สัญญาซื้อขาย", delay=40)
        menu = page.locator(".o-autocomplete--dropdown-menu").locator("visible=true").last
        await menu.wait_for(state="visible", timeout=10000)
        await menu.get_by_text("สัญญาซื้อขาย", exact=True).first.click()
        await page.wait_for_timeout(500)

    # ensure amount
    amount = page.locator('.o_field_widget[name="amount_total"] input')
    if await amount.count():
        val = await amount.input_value()
        if not val or val in ("0", "0.00"):
            await amount.fill("600000")

    # single delivery note / installment: leave empty = งวดเดียว unless required
    for field, value in (
        ("egp_contract_control_no", "P-CCTV16-TEST"),
        ("contract_po_number", "CTR-CCTV-16"),
        ("egp_reference", "P-CCTV16-TEST"),
    ):
        box = page.locator(f'.o_field_widget[name="{field}"] input')
        if await box.count() and await box.first.is_editable():
            await box.first.fill(value)

    await save_form(page)
    await shot(page, "24_contract_type.png")

    # quantity_policy should be fixed from type
    policy = page.locator('.o_field_widget[name="quantity_policy"]')
    if await policy.count():
        print("quantity_policy UI:", (await policy.inner_text()).strip())

    conf = page.locator('button[name="action_confirm"]')
    if await conf.count() and await conf.first.is_visible():
        await conf.first.click()
        await page.wait_for_timeout(1500)
        await dismiss_error(page)
        await shot(page, "25_contract_confirmed.png")

    match = re.search(r"purchase\.contract/(\d+)", page.url)
    contract_id = int(match.group(1)) if match else None
    name = (await page.locator('.o_field_widget[name="name"]').first.inner_text()).strip()
    return contract_id, name, page.url


async def attach_winner_docs_for_po(page):
    """แนบเอกสารผลพิจารณา + ประกาศผู้ชนะแบบทดสอบ เพื่อเปิดปุ่มสร้าง PO"""
    await open_egp(page)
    # try create award report if available
    award_btn = page.locator(
        'button[name="action_create_award_report"], button:has-text("รายงานผล")'
    )
    if await award_btn.count() and await award_btn.first.is_visible():
        await award_btn.first.click()
        await page.wait_for_timeout(1500)

    # Attach via RPC: create egp documents with dummy attachment
    Doc = "purchase.requisition.egp.document"
    # find type codes
    types = await rpc(
        page,
        "purchase.requisition.egp.document.type",
        "search_read",
        [[["code", "in", ["consider_procurement", "winner_announcement", "award_approval"]]]],
        {"fields": ["id", "code", "name"]},
    )
    print("doc types", types.get("result"))
    type_by_code = {t["code"]: t for t in (types.get("result") or [])}

    # create attachment
    import base64

    pdf_b64 = base64.b64encode(
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    ).decode()
    att = await rpc(
        page,
        "ir.attachment",
        "create",
        [
            {
                "name": "uat_cctv16_winner.pdf",
                "datas": pdf_b64,
                "res_model": "purchase.requisition",
                "res_id": EGP_ID,
                "mimetype": "application/pdf",
            }
        ],
    )
    print("attachment", att)
    att_id = att.get("result")
    if not att_id:
        return False

    for code in ("consider_procurement", "winner_announcement"):
        tinfo = type_by_code.get(code)
        if not tinfo:
            continue
        existing = await rpc(
            page,
            Doc,
            "search_read",
            [[["requisition_id", "=", EGP_ID], ["document_type_id", "=", tinfo["id"]]]],
            {"fields": ["id"], "limit": 1},
        )
        vals = {
            "requisition_id": EGP_ID,
            "document_type_id": tinfo["id"],
            "attachment_id": att_id,
            "document_filename": f"uat_{code}.pdf",
        }
        if existing.get("result"):
            await rpc(page, Doc, "write", [[existing["result"][0]["id"]], vals])
        else:
            created = await rpc(page, Doc, "create", [vals])
            print("created egp doc", code, created)

    # also try approve award report if exists
    reports = await rpc(
        page,
        "purchase.requisition.award.report",
        "search_read",
        [[["requisition_id", "=", EGP_ID]]],
        {"fields": ["id", "state"], "limit": 1},
    )
    if reports.get("result"):
        rid = reports["result"][0]["id"]
        # try button_approve if exists
        try:
            await rpc(page, "purchase.requisition.award.report", "action_approve", [[rid]])
        except Exception as error:
            print("award approve skip", error)
            await rpc(
                page,
                "purchase.requisition.award.report",
                "write",
                [[rid], {"state": "approved"}],
            )
    return True


async def create_po(page):
    await open_egp(page)
    # confirm egp if needed
    conf = page.locator('button[name="action_confirm"], button:has-text("ยืนยัน")')
    # careful: many confirm buttons; prefer state draft confirm
    state = page.locator('.o_field_widget[name="state"]')
    print("egp header text sample")

    po_btn = page.locator('button[name="action_open_create_rfq_wizard"]')
    if not await po_btn.count() or not await po_btn.first.is_visible():
        # try from PR
        await page.goto(
            f"{BASE_URL}/odoo/purchase.request/{PR_ID}", wait_until="domcontentloaded"
        )
        await page.locator(".o_form_view").first.wait_for()
        await shot(page, "26_pr_before_po.png")
        po_btn = page.locator('button[name="action_open_create_rfq_wizard"], button:has-text("สร้าง PO")')

    if not await po_btn.count() or not await po_btn.first.is_visible():
        await shot(page, "26_no_po_btn.png")
        # inspect award flags
        flags = await rpc(
            page,
            "purchase.requisition",
            "read",
            [[EGP_ID], ["egp_award_approved", "egp_has_winner", "state", "name"]],
        )
        print("egp flags", flags)
        return None

    await shot(page, "26_create_po_btn.png")
    await po_btn.first.click()
    modal = page.locator(".modal-content").last
    await modal.wait_for(state="visible", timeout=15000)
    await shot(page, "27_po_wizard.png")
    create = modal.locator(
        'button[name="action_create_rfq"], button:has-text("สร้าง PO"), button:has-text("สร้าง")'
    )
    await create.first.click()
    try:
        await modal.wait_for(state="hidden", timeout=30000)
    except PlaywrightTimeout:
        print("po wizard", (await modal.inner_text())[:600])
        await dismiss_error(page)
    await page.wait_for_timeout(2000)
    await shot(page, "28_po_form.png")
    await shot(page, "29_po_header_actions.png")

    # QC / WA buttons
    for label in ("QC", "ตรวจรับ", "Work Acceptance", "ใบตรวจรับ", "WA"):
        btn = page.get_by_role("button", name=re.compile(label, re.I))
        if await btn.count():
            print("found button", label, await btn.first.inner_text())
    # pickings
    picking_stat = page.locator('button[name="action_view_picking"], .o_stat_button:has-text("Receipt")')
    print("picking stat visible", await picking_stat.count())
    return page.url


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    if META.exists():
        try:
            meta = json.loads(META.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    meta.pop("error", None)
    meta["egp_id"] = EGP_ID
    meta["pr_id"] = PR_ID

    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=HEADLESS)
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1100}, device_scale_factor=2
        )
        page.set_default_timeout(30000)
        try:
            await login_as(page, PROC_OWNER)
            await open_egp(page)
            await ensure_consideration(page)
            await add_bidder_ui(page)
            await set_prices_and_winner(page)
            contract_id, contract_name, contract_url = await create_and_confirm_contract(page)
            meta["contract_id"] = contract_id
            meta["contract_name"] = contract_name
            meta["contract_url"] = contract_url
            await attach_winner_docs_for_po(page)
            po_url = await create_po(page)
            meta["po_url"] = po_url
            found = await rpc(
                page,
                "purchase.order",
                "search_read",
                [[["origin", "ilike", meta.get("pr_name") or "PR6911015"]]],
                {
                    "fields": [
                        "name",
                        "state",
                        "partner_id",
                        "amount_total",
                        "picking_ids",
                        "contract_id",
                    ],
                    "limit": 5,
                    "order": "id desc",
                },
            )
            meta["pos"] = found.get("result")
            # also contract-linked
            if contract_id:
                cpos = await rpc(
                    page,
                    "purchase.order",
                    "search_read",
                    [[["contract_id", "=", contract_id]]],
                    {
                        "fields": ["name", "state", "picking_ids", "amount_total"],
                        "limit": 5,
                    },
                )
                meta["contract_pos"] = cpos.get("result")
            # product type note
            prod = await rpc(
                page,
                "product.product",
                "search_read",
                [[["default_code", "=", "CCTV-16"]]],
                {"fields": ["type", "is_storable", "name"], "limit": 1},
            )
            meta["product"] = (prod.get("result") or [None])[0]
            print("META", json.dumps(meta, ensure_ascii=False, indent=2))
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error_resume.png"), full_page=True)
            meta["error"] = str(error)
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
