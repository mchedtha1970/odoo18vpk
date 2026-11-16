#!/usr/bin/env python3
"""จบ UAT บทที่ 4: ผู้ชนะ + สัญญาเช่าคอมพิวเตอร์ แบ่ง 12 งวด + PO/WA"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import sys
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_medicine_purchase_request import save_form  # noqa: E402
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/rental_lease_installment")
META = OUT / "meta.json"
EGP_ID = 86
PR_NAME = "PR6911020"
PROC_OWNER = "uat.material"
AMOUNT = 295320.0
PRICE = 24610.0
QTY = 12.0


async def shot(page, name: str):
    path = OUT / name
    await page.wait_for_timeout(400)
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


async def resolve_vendor(page):
    found = await rpc(
        page,
        "res.partner",
        "search_read",
        [[["name", "ilike", "Vendor DEMO"]]],
        {"fields": ["id", "name"], "limit": 1},
    )
    rows = found.get("result") or []
    if not rows:
        raise RuntimeError("ไม่พบ Vendor DEMO")
    return rows[0]["id"], rows[0]["name"]


async def ensure_winner(page, vendor_id: int):
    bids = await rpc(
        page,
        "purchase.requisition.egp.bid",
        "search_read",
        [[["requisition_id", "=", EGP_ID]]],
        {"fields": ["id", "partner_id", "is_winner", "amount_total", "line_ids"]},
    )
    print("bids", bids.get("result"))
    if not (bids.get("result") or []):
        lines = await rpc(
            page,
            "purchase.requisition.line",
            "search_read",
            [[["requisition_id", "=", EGP_ID]]],
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
        if not req_line:
            raise RuntimeError("ไม่พบบรรทัดสินค้าใน e-GP")
        created = await rpc(
            page,
            "purchase.requisition.egp.bid.line",
            "create",
            [
                {
                    "requisition_id": EGP_ID,
                    "partner_id": vendor_id,
                    "requisition_line_id": req_line["id"],
                    "product_id": req_line["product_id"][0],
                    "name": req_line.get("product_description_variants")
                    or "เช่า Fuji Xerox WorkCentre",
                    "product_qty": req_line.get("product_qty") or QTY,
                    "product_uom_id": req_line["product_uom_id"][0]
                    if req_line.get("product_uom_id")
                    else False,
                    "price_unit": PRICE,
                    "is_winner": True,
                }
            ],
        )
        print("created bid line", created)
        if created.get("error"):
            raise RuntimeError(str(created["error"]))
        # mark parent bid winner if created separately
        bids2 = await rpc(
            page,
            "purchase.requisition.egp.bid",
            "search_read",
            [[["requisition_id", "=", EGP_ID]]],
            {"fields": ["id"], "limit": 5},
        )
        for bid in bids2.get("result") or []:
            await rpc(
                page,
                "purchase.requisition.egp.bid",
                "write",
                [[bid["id"]], {"is_winner": True, "amount_total": AMOUNT}],
            )
    else:
        bid = bids["result"][0]
        await rpc(
            page,
            "purchase.requisition.egp.bid",
            "write",
            [[bid["id"]], {"is_winner": True, "amount_total": AMOUNT}],
        )
        if bid.get("line_ids"):
            await rpc(
                page,
                "purchase.requisition.egp.bid.line",
                "write",
                [bid["line_ids"], {"is_winner": True, "price_unit": PRICE}],
            )


async def attach_winner_docs(page):
    types = await rpc(
        page,
        "purchase.requisition.egp.document.type",
        "search_read",
        [[["code", "in", ["consider_procurement", "winner_announcement", "award_approval"]]]],
        {"fields": ["id", "code", "name"]},
    )
    type_by_code = {t["code"]: t for t in (types.get("result") or [])}
    pdf_b64 = base64.b64encode(
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    ).decode()
    for code in ("consider_procurement", "winner_announcement"):
        tinfo = type_by_code.get(code)
        if not tinfo:
            continue
        existing = await rpc(
            page,
            "purchase.requisition.egp.document",
            "search_read",
            [[["requisition_id", "=", EGP_ID], ["document_type_id", "=", tinfo["id"]]]],
            {"fields": ["id"], "limit": 1},
        )
        vals = {
            "requisition_id": EGP_ID,
            "document_type_id": tinfo["id"],
            "document_file": pdf_b64,
            "document_filename": f"uat_rental_{code}.pdf",
        }
        if existing.get("result"):
            await rpc(
                page,
                "purchase.requisition.egp.document",
                "write",
                [[existing["result"][0]["id"]], vals],
            )
        else:
            await rpc(page, "purchase.requisition.egp.document", "create", [vals])

    reports = await rpc(
        page,
        "purchase.requisition.award.report",
        "search_read",
        [[["requisition_id", "=", EGP_ID]]],
        {"fields": ["id", "state"], "limit": 1},
    )
    if not (reports.get("result") or []):
        created = await rpc(
            page,
            "purchase.requisition.award.report",
            "create",
            [{"requisition_id": EGP_ID}],
        )
        print("award report", created)
        rid = (created.get("result") or 0) if isinstance(created.get("result"), int) else None
        if rid:
            for meth in (
                "action_generate_lines",
                "action_submit",
                "action_approve",
                "button_approve",
            ):
                try:
                    await rpc(page, "purchase.requisition.award.report", meth, [[rid]])
                except Exception as error:
                    print("award meth skip", meth, error)
    else:
        rid = reports["result"][0]["id"]
        for meth in ("action_approve", "button_approve"):
            try:
                await rpc(page, "purchase.requisition.award.report", meth, [[rid]])
            except Exception as error:
                print("award meth skip", meth, error)


async def setup_contract_installments(page, contract_id: int):
    ctype = await rpc(
        page,
        "purchase.contract.type",
        "search_read",
        [[["name", "=", "สัญญาเช่าคอมพิวเตอร์"]]],
        {"fields": ["id"], "limit": 1},
    )
    ctype_id = (ctype.get("result") or [{}])[0].get("id")
    vals = {
        "payment_type": "installment",
        "egp_contract_control_no": "P444444444",
    }
    if ctype_id:
        vals["contract_type_id"] = ctype_id
    # contract_kind if exists
    fields = await rpc(page, "purchase.contract", "fields_get", [], {"attributes": ["type"]})
    if fields.get("result") and "contract_kind" in fields["result"]:
        vals["contract_kind"] = "lease"
    written = await rpc(page, "purchase.contract", "write", [[contract_id], vals])
    print("contract write", written)

    # generate installments via wizard model
    wiz = await rpc(
        page,
        "purchase.contract.generate.installments",
        "create",
        [
            {
                "contract_id": contract_id,
                "installment_count": 12,
                "clear_existing": True,
            }
        ],
    )
    print("wiz", wiz)
    wid = wiz.get("result")
    if wid:
        # discover action method
        for meth in ("action_generate", "action_confirm", "action_apply"):
            res = await rpc(
                page, "purchase.contract.generate.installments", meth, [[wid]]
            )
            print("gen", meth, res)
            if not res.get("error"):
                break

    ctr = await rpc(
        page,
        "purchase.contract",
        "read",
        [[contract_id], ["name", "state", "payment_type", "amount_total", "installment_ids"]],
    )
    print("contract after gen", ctr.get("result"))
    return ctr.get("result")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta.update({"egp_id": EGP_ID, "pr_name": PR_NAME, "budget": "DBR/2570/0043"})
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        try:
            await login_as(page, PROC_OWNER)
            vendor_id, vendor_name = await resolve_vendor(page)
            meta["vendor"] = vendor_name
            await ensure_winner(page, vendor_id)
            await attach_winner_docs(page)

            await page.goto(
                f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            await close_modals(page)
            tab = page.get_by_role("tab", name=re.compile("ผู้เสนอราคา|การพิจารณา"))
            if await tab.count():
                await tab.first.click()
                await page.wait_for_timeout(500)
            await shot(page, "21_winner.png")

            # สร้างสัญญา
            contract_btn = page.locator(
                'button[name="action_create_purchase_contract"], '
                'button:has-text("สร้างสัญญา")'
            )
            await contract_btn.first.wait_for(state="visible", timeout=20000)
            await shot(page, "22_contract_btn.png")
            await contract_btn.first.click()
            await page.wait_for_timeout(2000)
            await close_modals(page)
            await page.wait_for_timeout(1000)
            await shot(page, "23_contract_form.png")

            # หา contract id จาก URL หรือ search
            m = re.search(r"purchase\.contract/(\d+)", page.url)
            contract_id = int(m.group(1)) if m else None
            if not contract_id:
                found = await rpc(
                    page,
                    "purchase.contract",
                    "search_read",
                    [[["requisition_id", "=", EGP_ID]]],
                    {"fields": ["id", "name"], "limit": 1, "order": "id desc"},
                )
                if found.get("result"):
                    contract_id = found["result"][0]["id"]
                    await page.goto(
                        f"{BASE_URL}/odoo/purchase.contract/{contract_id}",
                        wait_until="domcontentloaded",
                    )
                    await page.locator(".o_form_view").first.wait_for()
            if not contract_id:
                raise RuntimeError("ไม่พบสัญญาที่สร้างจาก e-GP")

            info = await setup_contract_installments(page, contract_id)
            await page.reload(wait_until="domcontentloaded")
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "24_contract_type.png")

            # UI: แท็บงวด
            inst_tab = page.get_by_role("tab", name=re.compile("เงื่อนไขแบ่งงวด|แบ่งงวด"))
            if await inst_tab.count():
                await inst_tab.first.click()
                await page.wait_for_timeout(600)
            await shot(page, "27_installments.png")

            # ยืนยันสัญญา
            conf = page.locator(
                'button[name="action_confirm"], button:has-text("ยืนยันสัญญา"), '
                'button:has-text("ยืนยัน")'
            )
            if await conf.count() and await conf.first.is_visible():
                await conf.first.click()
                await page.wait_for_timeout(1500)
                await close_modals(page)
            await shot(page, "28_contract_confirmed.png")
            contract_name = (
                await page.locator('.o_field_widget[name="name"]').first.inner_text()
            ).strip()
            meta["contract_id"] = contract_id
            meta["contract_name"] = contract_name
            meta["contract_info"] = info

            # สร้าง PO จาก e-GP
            await page.goto(
                f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            await close_modals(page)
            po_btn = page.locator(
                'button[name="action_open_create_rfq_wizard"], button:has-text("สร้าง PO")'
            )
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
                # fallback: search PO
                await shot(page, "29_no_po_btn.png")
                pos = await rpc(
                    page,
                    "purchase.order",
                    "search_read",
                    [[["origin", "ilike", PR_NAME]]],
                    {
                        "fields": ["name", "state", "amount_total", "id"],
                        "limit": 3,
                        "order": "id desc",
                    },
                )
                meta["pos"] = pos.get("result")
                if pos.get("result"):
                    po_id = pos["result"][0]["id"]
                    await page.goto(
                        f"{BASE_URL}/odoo/purchase/{po_id}",
                        wait_until="domcontentloaded",
                    )
                    await page.locator(".o_form_view").first.wait_for()
                    await shot(page, "31_po_form.png")
                    wa = page.locator(
                        'button[name="action_create_work_acceptance"], '
                        'button:has-text("ใบตรวจรับ"), button:has-text("ตรวจรับ")'
                    )
                    if await wa.count() and await wa.first.is_visible():
                        await shot(page, "32_wa_btn.png")
                        await wa.first.click()
                        await page.wait_for_timeout(1500)
                        await shot(page, "33_wa_form.png")

            pos = await rpc(
                page,
                "purchase.order",
                "search_read",
                [[["origin", "ilike", PR_NAME]]],
                {
                    "fields": ["name", "state", "amount_total", "partner_id"],
                    "limit": 3,
                    "order": "id desc",
                },
            )
            meta["pos"] = pos.get("result")
            inst = await rpc(
                page,
                "purchase.contract.installment",
                "search_read",
                [[["contract_id", "=", contract_id]]],
                {"fields": ["name", "amount", "date_planned"], "order": "id asc"},
            )
            meta["installments"] = inst.get("result")
            print("META", json.dumps(meta, ensure_ascii=False, indent=2, default=str))
            META.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error_finish.png"), full_page=True)
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
