#!/usr/bin/env python3
"""จบบทที่ 4–5: สร้าง PO จาก e-GP → พิมพ์/ส่ง Mobile App → ผู้ขายยืนยัน"""
from __future__ import annotations

import asyncio
import base64
import json
import shutil
import sys
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

SCENARIOS = [
    {
        "key": "rental",
        "out": Path("docs/manual_assets/figures/rental_lease_installment"),
        "egp_id": 86,
        "pr_name": "PR6911020",
        "owner": "uat.material",
        "bid_ref": "BID-RENTAL-FX",
        "copy_vendorapp_from": Path("docs/manual_assets/figures/nondrug_specific_le500k"),
    },
    {
        "key": "bp19",
        "out": Path("docs/manual_assets/figures/asset_ebidding_bp19"),
        "egp_id": 87,
        "pr_name": "PR6911021",
        "owner": "uat.equipment",
        "bid_ref": "BID-BP19-ICU",
        "copy_vendorapp_from": Path("docs/manual_assets/figures/nondrug_specific_le500k"),
    },
]
VENDOR_LOGIN = "vdemo@24erp.com"
VENDOR_PASSWORD = "vdemo"


async def shot(page, out: Path, name: str):
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
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


def vendor_api(path, payload=None, session_id=None, method="POST"):
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if session_id:
        headers["Authorization"] = f"Bearer {session_id}"
        headers["Cookie"] = f"session_id={session_id}"
    if payload is not None:
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode()
        return json.loads(body) if body else {}


async def close_modals(page):
    for _ in range(3):
        modal = page.locator(".modal.d-block, .modal.show").last
        if not await modal.count():
            break
        btn = modal.locator(
            "button:has-text('ปิด'), button:has-text('ตกลง'), button:has-text('ยกเลิก')"
        )
        if await btn.count() and await btn.first.is_visible():
            await btn.first.click()
            await page.wait_for_timeout(300)
        else:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)


async def ensure_winner(page, egp_id: int, vendor_id: int):
    bids = await rpc(
        page,
        "purchase.requisition.egp.bid",
        "search_read",
        [[["requisition_id", "=", egp_id]]],
        {"fields": ["id", "line_ids", "is_winner", "amount_total"]},
    )
    if not (bids.get("result") or []):
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
                    "price_unit",
                    "product_description_variants",
                ]
            },
        )
        req = (lines.get("result") or [None])[0]
        if not req:
            raise RuntimeError(f"EGP {egp_id} ไม่มีบรรทัดสินค้า")
        price = req.get("price_unit") or 1.0
        await rpc(
            page,
            "purchase.requisition.egp.bid.line",
            "create",
            [
                {
                    "requisition_id": egp_id,
                    "partner_id": vendor_id,
                    "requisition_line_id": req["id"],
                    "product_id": req["product_id"][0],
                    "name": req.get("product_description_variants") or "item",
                    "product_qty": req.get("product_qty") or 1.0,
                    "product_uom_id": req["product_uom_id"][0]
                    if req.get("product_uom_id")
                    else False,
                    "price_unit": price,
                    "is_winner": True,
                }
            ],
        )
        bids = await rpc(
            page,
            "purchase.requisition.egp.bid",
            "search_read",
            [[["requisition_id", "=", egp_id]]],
            {"fields": ["id", "line_ids"], "limit": 5},
        )
    for bid in bids.get("result") or []:
        await rpc(
            page,
            "purchase.requisition.egp.bid",
            "write",
            [[bid["id"]], {"is_winner": True}],
        )
        if bid.get("line_ids"):
            await rpc(
                page,
                "purchase.requisition.egp.bid.line",
                "write",
                [bid["line_ids"], {"is_winner": True}],
            )


async def attach_award_docs(page, egp_id: int):
    types = await rpc(
        page,
        "purchase.requisition.egp.document.type",
        "search_read",
        [[["code", "in", ["consider_procurement", "winner_announcement"]]]],
        {"fields": ["id", "code"]},
    )
    pdf_b64 = base64.b64encode(
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    ).decode()
    for tinfo in types.get("result") or []:
        existing = await rpc(
            page,
            "purchase.requisition.egp.document",
            "search_read",
            [[["requisition_id", "=", egp_id], ["document_type_id", "=", tinfo["id"]]]],
            {"fields": ["id"], "limit": 1},
        )
        vals = {
            "requisition_id": egp_id,
            "document_type_id": tinfo["id"],
            "document_file": pdf_b64,
            "document_filename": f"uat_{tinfo['code']}.pdf",
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
        [[["requisition_id", "=", egp_id]]],
        {"fields": ["id", "state"], "limit": 1},
    )
    if not (reports.get("result") or []):
        await rpc(page, "purchase.requisition", "action_create_award_report", [[egp_id]])
        reports = await rpc(
            page,
            "purchase.requisition.award.report",
            "search_read",
            [[["requisition_id", "=", egp_id]]],
            {"fields": ["id", "state"], "limit": 1},
        )
    if reports.get("result"):
        rid = reports["result"][0]["id"]
        if reports["result"][0].get("state") != "approved":
            for meth in ("action_generate_lines", "action_submit", "action_approve"):
                try:
                    await rpc(page, "purchase.requisition.award.report", meth, [[rid]])
                except Exception as error:
                    print("award", meth, error)
            await rpc(
                page,
                "purchase.requisition.award.report",
                "write",
                [[rid], {"state": "approved"}],
            )


async def create_po(page, egp_id: int, vendor_id: int, bid_ref: str):
    wiz = await rpc(
        page,
        "purchase.requisition.create.rfq",
        "create",
        [
            {
                "requisition_id": egp_id,
                "partner_id": vendor_id,
                "egp_bid_reference": bid_ref,
            }
        ],
    )
    if wiz.get("error"):
        raise RuntimeError(wiz["error"])
    action = await rpc(
        page, "purchase.requisition.create.rfq", "action_create_rfq", [[wiz["result"]]]
    )
    if action.get("error"):
        raise RuntimeError(action["error"])
    result = action.get("result") or {}
    po_id = result.get("res_id")
    if not po_id:
        found = await rpc(
            page,
            "purchase.order",
            "search_read",
            [[["requisition_id", "=", egp_id]]],
            {"fields": ["id", "name"], "limit": 1, "order": "id desc"},
        )
        po_id = (found.get("result") or [{}])[0].get("id")
    if not po_id:
        raise RuntimeError("สร้าง PO ไม่สำเร็จ")
    return po_id


async def process_scenario(page, sc, vendor_id: int):
    out = sc["out"]
    egp_id = sc["egp_id"]
    meta_path = out / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.pop("error", None)

    await login_as(page, sc["owner"])
    await ensure_winner(page, egp_id, vendor_id)
    await attach_award_docs(page, egp_id)

    await page.goto(
        f"{BASE_URL}/odoo/purchase.requisition/{egp_id}", wait_until="domcontentloaded"
    )
    await page.locator(".o_form_view").first.wait_for()
    await close_modals(page)

    # ยืนยัน e-GP
    conf = page.locator('button[name="action_confirm"]')
    if await conf.count() and await conf.first.is_visible():
        await shot(page, out, "29a_confirm_egp_btn.png")
        await conf.first.click()
        await page.wait_for_timeout(1200)
        await close_modals(page)
    else:
        conf_rpc = await rpc(page, "purchase.requisition", "action_confirm", [[egp_id]])
        print(sc["key"], "confirm rpc", conf_rpc.get("error") or "ok")
        await page.reload(wait_until="domcontentloaded")
        await page.locator(".o_form_view").first.wait_for()

    await shot(page, out, "29_create_po_btn.png")
    po_btn = page.locator(
        'button[name="action_open_create_rfq_wizard"], button:has-text("สร้าง PO")'
    )
    visible = await po_btn.count() and await po_btn.first.is_visible()
    print(sc["key"], "PO btn visible?", visible)

    # UI click if possible else RPC
    if visible:
        await po_btn.first.click()
        modal = page.locator(".modal-content").last
        try:
            await modal.wait_for(state="visible", timeout=10000)
            await shot(page, out, "30_po_wizard.png")
            create = modal.get_by_role("button", name=__import__("re").compile("สร้าง|ยืนยัน|บันทึก"))
            if await create.count():
                await create.first.click()
                await page.wait_for_timeout(2000)
                await close_modals(page)
        except Exception as error:
            print(sc["key"], "wizard ui fail", error)
            await close_modals(page)
            po_id = await create_po(page, egp_id, vendor_id, sc["bid_ref"])
        else:
            # resolve po id from url or search
            import re

            m = re.search(r"purchase(?:\.order)?/(\d+)", page.url)
            if m:
                po_id = int(m.group(1))
            else:
                found = await rpc(
                    page,
                    "purchase.order",
                    "search_read",
                    [[["requisition_id", "=", egp_id]]],
                    {"fields": ["id"], "limit": 1, "order": "id desc"},
                )
                po_id = (found.get("result") or [{}])[0].get("id")
                if not po_id:
                    po_id = await create_po(page, egp_id, vendor_id, sc["bid_ref"])
    else:
        po_id = await create_po(page, egp_id, vendor_id, sc["bid_ref"])

    await page.goto(f"{BASE_URL}/odoo/purchase.order/{po_id}", wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
    await shot(page, out, "31_po_form.png")
    await shot(page, out, "33_po_draft_before_send.png")

    # พิมพ์/ส่งแอป
    state = await rpc(
        page,
        "purchase.order",
        "read",
        [[po_id], ["name", "state", "vpk_vendor_confirm_state", "partner_id", "amount_total"]],
    )
    print(sc["key"], "before send", state.get("result"))
    row = (state.get("result") or [{}])[0]
    if row.get("vpk_vendor_confirm_state") in (False, None, "not_sent"):
        await rpc(page, "purchase.order", "action_save_vpk_po_pdf", [[po_id]])
        send = await rpc(page, "purchase.order", "action_send_vpk_po_to_winner", [[po_id]])
        print(sc["key"], "send", send.get("error") or "ok")
        await page.reload(wait_until="domcontentloaded")
        await page.locator(".o_form_view").first.wait_for()

    await shot(page, out, "34_po_waiting_vendor.png")
    send_btn = page.locator(
        'button[name="action_send_vpk_po_to_winner"], button:has-text("ส่ง"), button:has-text("แอป")'
    )
    if await send_btn.count():
        await send_btn.first.scroll_into_view_if_needed()
    await shot(page, out, "35_po_send_vendor_btn.png")

    # ผู้ขายยืนยันผ่าน API
    tiny_png = base64.b64encode(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
    ).decode()
    login = vendor_api(
        "/vpk/api/v1/vendor/auth/login",
        {"login": VENDOR_LOGIN, "password": VENDOR_PASSWORD, "db": "VPK-S1"},
    )
    session_id = login.get("session_id") or login.get("sid")
    if not session_id:
        raise RuntimeError(f"vendor login failed: {login}")
    signed = vendor_api(
        f"/vpk/api/v1/vendor/orders/{po_id}/sign",
        {"signature": tiny_png, "name": "Vendor DEMO"},
        session_id=session_id,
    )
    print(sc["key"], "signed", signed.get("ok") or signed)

    await page.reload(wait_until="domcontentloaded")
    await page.locator(".o_form_view").first.wait_for()
    await page.wait_for_timeout(1200)
    await shot(page, out, "36_po_vendor_confirmed.png")

    po = await rpc(
        page,
        "purchase.order",
        "read",
        [
            [po_id],
            [
                "name",
                "state",
                "vpk_vendor_confirm_state",
                "partner_id",
                "amount_total",
                "picking_ids",
            ],
        ],
    )
    meta["po"] = (po.get("result") or [None])[0]
    meta["po_id"] = po_id
    meta["po_vendor"] = meta["po"]

    # คัดลอกภาพ Mobile App จากบทที่ 3 (flow เดียวกัน) ถ้ายังไม่มี
    src = sc["copy_vendorapp_from"]
    for name in (
        "42_vendorapp_login.png",
        "43_vendorapp_home.png",
        "44_vendorapp_po_cards.png",
        "46_vendorapp_sign.png",
        "48_vendorapp_done.png",
    ):
        dst = out / name
        if not dst.exists() and (src / name).exists():
            shutil.copy2(src / name, dst)
            print("COPY", dst)

    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(sc["key"], "DONE", meta.get("po"))
    return meta


async def main():
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(60000)
        try:
            # resolve vendor once
            await login_as(page, "uat.material")
            found = await rpc(
                page,
                "res.partner",
                "search_read",
                [[["name", "ilike", "Vendor DEMO"]]],
                {"fields": ["id", "name"], "limit": 1},
            )
            vendor_id = found["result"][0]["id"]
            print("vendor", vendor_id, found["result"][0]["name"])
            for sc in SCENARIOS:
                try:
                    await process_scenario(page, sc, vendor_id)
                except Exception as error:
                    print("FAIL", sc["key"], error)
                    await page.screenshot(
                        path=str(sc["out"] / f"error_po_{sc['key']}.png"), full_page=True
                    )
                    raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
