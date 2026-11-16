#!/usr/bin/env python3
"""จับภาพขั้นสุดท้ายของ flow CCTV-16 จากเอกสารที่มีอยู่แล้ว"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/cctv16_specific")
META = OUT / "meta.json"
PO_ID = 136
CTR_ID = 318
EGP_ID = 83
PR_ID = 178


async def shot(page, name: str, full=False):
    path = OUT / name
    if full:
        await page.screenshot(path=str(path), full_page=True)
    else:
        await page.locator(".o_action, .o_form_view, .o_content").first.screenshot(
            path=str(path)
        )
    print("SHOT", path)


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


async def main():
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta.pop("error", None)

    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1200}, device_scale_factor=2
        )
        await login_as(page, "uat.equipment")

        # Contract confirmed
        await page.goto(
            f"{BASE_URL}/odoo/purchase.contract/{CTR_ID}", wait_until="domcontentloaded"
        )
        await page.locator(".o_form_view").first.wait_for()
        await shot(page, "24_contract_type.png")
        await shot(page, "25_contract_confirmed.png")

        # EGP with winner / no plan
        await page.goto(
            f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}", wait_until="domcontentloaded"
        )
        await page.locator(".o_form_view").first.wait_for()
        await shot(page, "21_winner.png")
        await shot(page, "31_egp_final.png")
        # note no plan
        plan_btn = page.locator('button:has-text("สร้างแผน")')
        print("plan button count", await plan_btn.count())

        # PO
        await page.goto(
            f"{BASE_URL}/odoo/purchase.order/{PO_ID}", wait_until="domcontentloaded"
        )
        await page.locator(".o_form_view").first.wait_for()
        await shot(page, "26_create_po_btn.png")  # PO already created context
        await shot(page, "28_po_form.png")
        await shot(page, "29_po_header_actions.png")

        # smart buttons / WA QC
        box = page.locator(".oe_button_box, .o_button_box")
        if await box.count():
            await box.first.scroll_into_view_if_needed()
            await shot(page, "33_po_smart_buttons.png")

        # try open WA
        wa = page.locator(
            'button[name="action_view_wa"], button:has-text("ตรวจรับ"), '
            'button:has-text("Work Acceptance"), .o_stat_button:has-text("WA")'
        )
        qc = page.locator(
            'button[name="action_view_qc"], button:has-text("QC"), '
            '.o_stat_button:has-text("QC")'
        )
        print("WA btn", await wa.count(), "QC btn", await qc.count())
        if await wa.count() and await wa.first.is_visible():
            await wa.first.click()
            await page.wait_for_timeout(1500)
            await shot(page, "34_wa_view.png")
            await page.goto(
                f"{BASE_URL}/odoo/purchase.order/{PO_ID}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()
        if await qc.count() and await qc.first.is_visible():
            await qc.first.click()
            await page.wait_for_timeout(1500)
            await shot(page, "35_qc_view.png")
            await page.goto(
                f"{BASE_URL}/odoo/purchase.order/{PO_ID}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()

        # picking
        pick = page.locator(
            'button[name="action_view_picking"], .o_stat_button:has-text("Receipt"), '
            '.o_stat_button:has-text("รับ")'
        )
        if await pick.count() and await pick.first.is_visible():
            await pick.first.click()
            await page.wait_for_timeout(1500)
            await shot(page, "36_wh_in.png")
        else:
            # open by id
            picks = await rpc(
                page,
                "stock.picking",
                "search_read",
                [[["purchase_id", "=", PO_ID]]],
                {"fields": ["id", "name", "state"], "limit": 1},
            )
            if picks.get("result"):
                await page.goto(
                    f"{BASE_URL}/odoo/stock.picking/{picks['result'][0]['id']}",
                    wait_until="domcontentloaded",
                )
                await page.locator(".o_form_view").first.wait_for()
                await shot(page, "36_wh_in.png")

        # PR final
        await page.goto(
            f"{BASE_URL}/odoo/purchase.request/{PR_ID}", wait_until="domcontentloaded"
        )
        await page.locator(".o_form_view").first.wait_for()
        await shot(page, "32_pr_final.png")

        # collect meta
        po = await rpc(
            page,
            "purchase.order",
            "read",
            [
                [PO_ID],
                [
                    "name",
                    "state",
                    "partner_id",
                    "amount_total",
                    "picking_ids",
                    "contract_id",
                    "origin",
                    "wa_count",
                    "qc_count",
                    "wa_accepted",
                ],
            ],
        )
        ctr = await rpc(
            page,
            "purchase.contract",
            "read",
            [
                [CTR_ID],
                [
                    "name",
                    "state",
                    "quantity_policy",
                    "contract_type_id",
                    "amount_total",
                    "partner_id",
                ],
            ],
        )
        egp = await rpc(
            page,
            "purchase.requisition",
            "read",
            [
                [EGP_ID],
                ["name", "state", "ebidding_plan_line_id", "egp_award_approved"],
            ],
        )
        prod = await rpc(
            page,
            "product.product",
            "search_read",
            [[["default_code", "=", "CCTV-16"]]],
            {"fields": ["type", "is_storable", "name"], "limit": 1},
        )
        picks = await rpc(
            page,
            "stock.picking",
            "read",
            [
                (po.get("result") or [{}])[0].get("picking_ids") or [],
                ["name", "state", "picking_type_id"],
            ],
        )

        meta.update(
            {
                "pr_name": "PR6911015",
                "pr_id": PR_ID,
                "egp_id": EGP_ID,
                "egp_name": "EGP/2026/0158",
                "plan": None,
                "plan_note": "วิธีเฉพาะเจาะจง — ไม่มีปุ่มสร้างแผน (เฉพาะ e-Bidding)",
                "contract": (ctr.get("result") or [None])[0],
                "po": (po.get("result") or [None])[0],
                "pickings": picks.get("result") or [],
                "product": (prod.get("result") or [None])[0],
                "egp": (egp.get("result") or [None])[0],
            }
        )
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print("META", json.dumps(meta, ensure_ascii=False, indent=2))
        await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
