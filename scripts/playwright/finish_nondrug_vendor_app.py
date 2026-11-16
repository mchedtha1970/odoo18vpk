#!/usr/bin/env python3
"""บทที่ 3 ข้อ 10+: พิมพ์/ส่ง P00049 เข้าแอปผู้ขาย → Vendor DEMO ลงนาม → จับภาพ PO/WH"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/nondrug_specific_le500k")
META = OUT / "meta.json"
PO_ID = 137
PROC_OWNER = "uat.material"
VENDOR_LOGIN = "vdemo@24erp.com"
VENDOR_PASSWORD = "vdemo"


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


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}

    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        try:
            await login_as(page, PROC_OWNER)
            await page.goto(
                f"{BASE_URL}/odoo/purchase.order/{PO_ID}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "33_po_draft_before_send.png")

            # ensure pdf + send (idempotent if already waiting)
            state = await rpc(
                page,
                "purchase.order",
                "read",
                [[PO_ID], ["state", "vpk_vendor_confirm_state", "name", "has_pdf"]],
            )
            print("before", state.get("result"))
            row = (state.get("result") or [{}])[0]
            if row.get("vpk_vendor_confirm_state") == "not_sent":
                await rpc(page, "purchase.order", "action_save_vpk_po_pdf", [[PO_ID]])
                send = await rpc(
                    page, "purchase.order", "action_send_vpk_po_to_winner", [[PO_ID]]
                )
                print("send", send)
                await page.reload(wait_until="domcontentloaded")
                await page.locator(".o_form_view").first.wait_for()

            await shot(page, "34_po_waiting_vendor.png")
            # highlight send button area if still visible
            send_btn = page.locator(
                'button[name="action_send_vpk_po_to_winner"], button:has-text("ส่งเข้าแอป")'
            )
            if await send_btn.count():
                await send_btn.first.scroll_into_view_if_needed()
            await shot(page, "35_po_send_vendor_btn.png")

            # Vendor DEMO signs via API (แอปผู้ขาย)
            tiny_png = base64.b64encode(
                base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
                )
            ).decode()
            login = vendor_api(
                "/vpk/api/v1/vendor/auth/login",
                {"login": VENDOR_LOGIN, "password": VENDOR_PASSWORD, "db": "VPK-S1"},
            )
            print("vendor login ok", login.get("ok"), "waiting", login.get("waiting_count"))
            session_id = login.get("session_id") or login.get("sid")
            if not session_id:
                raise RuntimeError(f"login failed: {login}")

            orders = vendor_api(
                "/vpk/api/v1/vendor/orders?status=waiting",
                session_id=session_id,
                method="GET",
            )
            print("orders", orders if isinstance(orders, dict) else str(orders)[:300])

            signed = vendor_api(
                f"/vpk/api/v1/vendor/orders/{PO_ID}/sign",
                {
                    "signature": tiny_png,
                    "name": "Vendor DEMO",
                },
                session_id=session_id,
            )
            print("signed", signed)

            await page.reload(wait_until="domcontentloaded")
            await page.locator(".o_form_view").first.wait_for()
            await page.wait_for_timeout(1500)
            await shot(page, "36_po_vendor_confirmed.png")

            po = await rpc(
                page,
                "purchase.order",
                "read",
                [
                    [PO_ID],
                    [
                        "name",
                        "state",
                        "vpk_vendor_confirm_state",
                        "partner_id",
                        "amount_total",
                        "picking_ids",
                        "vpk_po_sent_on",
                    ],
                ],
            )
            meta["po_vendor"] = (po.get("result") or [None])[0]
            picking_ids = (meta["po_vendor"] or {}).get("picking_ids") or []
            if picking_ids:
                await page.goto(
                    f"{BASE_URL}/odoo/stock.picking/{picking_ids[-1]}",
                    wait_until="domcontentloaded",
                )
                await page.locator(".o_form_view").first.wait_for()
                await shot(page, "37_wh_in_after_sign.png")
                pick = await rpc(
                    page,
                    "stock.picking",
                    "read",
                    [[picking_ids[-1]], ["name", "state", "picking_type_id", "origin"]],
                )
                meta["picking_after_sign"] = (pick.get("result") or [None])[0]

            # also keep legacy filename for WH
            if picking_ids:
                await page.screenshot(path=str(OUT / "30_wh_in.png"))

            print("META", json.dumps(meta, ensure_ascii=False, indent=2))
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error_vendor_app.png"), full_page=True)
            raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
