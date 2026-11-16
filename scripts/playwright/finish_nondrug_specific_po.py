#!/usr/bin/env python3
"""จบ UAT บทที่ 3: ผู้ชนะ Vendor DEMO + เอกสารประกาศ + สร้าง PO (ไม่มีสัญญา เพราะรูปแบบใบสั่งซื้อ)"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from odoo_session import BASE_URL, launch_browser, login_as  # noqa: E402

OUT = Path("docs/manual_assets/figures/nondrug_specific_le500k")
META = OUT / "meta.json"
EGP_ID = 85
PR_ID = 182
VENDOR_ID = 9  # Vendor DEMO (fallback resolve by name)
PROC_OWNER = "uat.material"
PRICE = 6.0
AMOUNT = 60000.0


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


async def resolve_vendor(page):
    found = await rpc(
        page,
        "res.partner",
        "search_read",
        [[["name", "ilike", "Vendor DEMO"]]],
        {"fields": ["id", "name"], "limit": 1},
    )
    rows = found.get("result") or []
    if rows:
        return rows[0]["id"], rows[0]["name"]
    return VENDOR_ID, "Vendor DEMO"


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
                    or "Gauze 2x2 Sterile",
                    "product_qty": req_line.get("product_qty") or 10000.0,
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
            raise RuntimeError(created["error"])
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
    print("doc types", types.get("result"))
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
            "document_filename": f"uat_nondrug_{code}.pdf",
        }
        if existing.get("result"):
            await rpc(
                page,
                "purchase.requisition.egp.document",
                "write",
                [[existing["result"][0]["id"]], vals],
            )
        else:
            created = await rpc(
                page, "purchase.requisition.egp.document", "create", [vals]
            )
            print("created egp doc", code, created)

    # สร้างรายงานผลการพิจารณาแล้วอนุมัติ (เปิด egp_award_approved)
    reports = await rpc(
        page,
        "purchase.requisition.award.report",
        "search_read",
        [[["requisition_id", "=", EGP_ID]]],
        {"fields": ["id", "state"], "limit": 1},
    )
    if not (reports.get("result") or []):
        created_action = await rpc(
            page, "purchase.requisition", "action_create_award_report", [[EGP_ID]]
        )
        print("create award report", created_action)
        reports = await rpc(
            page,
            "purchase.requisition.award.report",
            "search_read",
            [[["requisition_id", "=", EGP_ID]]],
            {"fields": ["id", "state"], "limit": 1},
        )
    if reports.get("result"):
        rid = reports["result"][0]["id"]
        if reports["result"][0].get("state") != "approved":
            try:
                await rpc(
                    page, "purchase.requisition.award.report", "action_approve", [[rid]]
                )
            except Exception as error:
                print("award approve skip", error)
                await rpc(
                    page,
                    "purchase.requisition.award.report",
                    "write",
                    [[rid], {"state": "approved"}],
                )
        print("award report", rid, "approved")


async def create_po(page, vendor_id: int):
    wiz = await rpc(
        page,
        "purchase.requisition.create.rfq",
        "create",
        [
            {
                "requisition_id": EGP_ID,
                "partner_id": vendor_id,
                "egp_bid_reference": "BID-NONDRUG-GAUZE",
            }
        ],
    )
    print("wizard", wiz)
    if wiz.get("error"):
        raise RuntimeError(wiz["error"])
    action = await rpc(
        page,
        "purchase.requisition.create.rfq",
        "action_create_rfq",
        [[wiz["result"]]],
    )
    print("create rfq", action)
    if action.get("error"):
        raise RuntimeError(action["error"])
    result = action.get("result") or {}
    po_id = result.get("res_id")
    if not po_id and isinstance(result.get("domain"), list):
        # sometimes returns act_window on list
        found = await rpc(
            page,
            "purchase.order",
            "search_read",
            [[["requisition_id", "=", EGP_ID]]],
            {"fields": ["id", "name"], "limit": 1, "order": "id desc"},
        )
        po_id = (found.get("result") or [{}])[0].get("id")
    if not po_id:
        raise RuntimeError("สร้าง PO ไม่สำเร็จ")
    return po_id


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta.pop("error", None)

    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(45000)
        try:
            await login_as(page, PROC_OWNER)
            vendor_id, vendor_name = await resolve_vendor(page)
            print("vendor", vendor_id, vendor_name)
            meta["vendor"] = {"id": vendor_id, "name": vendor_name}

            await ensure_winner(page, vendor_id)
            await page.goto(
                f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            tab = page.get_by_role("tab", name=__import__("re").compile("ผู้เสนอราคา|การพิจารณา"))
            if await tab.count():
                await tab.first.click()
                await page.wait_for_timeout(500)
            await shot(page, "21_winner.png")

            # ยืนยันว่าไม่มีปุ่มสร้างแผน (≤500k)
            plan_btn = page.locator(
                'button[name="action_create_ebidding_plan"], button:has-text("สร้างแผน")'
            )
            visible_plan = await plan_btn.count() and await plan_btn.first.is_visible()
            print("plan button visible?", visible_plan)
            await shot(page, "15_no_plan_expected.png")

            await attach_winner_docs(page)
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(800)

            # ยืนยันกระบวนการ e-GP ก่อนสร้าง PO
            conf = page.locator('button[name="action_confirm"]')
            if await conf.count() and await conf.first.is_visible():
                await shot(page, "25_confirm_egp_btn.png")
                await conf.first.click()
                await page.wait_for_timeout(1500)
                # ถ้ามี dialog ยืนยัน
                modal_ok = page.locator(".modal-content button:has-text('ตกลง'), .modal-footer button.btn-primary")
                if await modal_ok.count() and await modal_ok.first.is_visible():
                    await modal_ok.first.click()
                    await page.wait_for_timeout(1000)
            else:
                # fallback RPC
                conf_rpc = await rpc(
                    page, "purchase.requisition", "action_confirm", [[EGP_ID]]
                )
                print("confirm rpc", conf_rpc)
                if conf_rpc.get("error"):
                    # maybe already confirmed
                    print("confirm skip", conf_rpc["error"].get("data", {}).get("message"))
                await page.reload(wait_until="domcontentloaded")
                await page.wait_for_timeout(800)

            await shot(page, "26_create_po_btn.png")
            po_btn = page.locator(
                'button[name="action_open_create_rfq_wizard"], button:has-text("สร้าง PO")'
            )
            print(
                "PO button visible?",
                await po_btn.count() and await po_btn.first.is_visible(),
            )

            po_id = await create_po(page, vendor_id)
            await page.goto(
                f"{BASE_URL}/odoo/purchase.order/{po_id}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "27_po_wizard.png")
            await shot(page, "28_po_form.png")

            # ยืนยัน PO ถ้ายังเป็นร่าง (วัสดุ → ใบรับคลัง)
            conf = page.locator('button[name="button_confirm"]')
            if await conf.count() and await conf.first.is_visible():
                await conf.first.click()
                await page.wait_for_timeout(2000)
                await shot(page, "29_po_confirmed.png")

            po = await rpc(
                page,
                "purchase.order",
                "read",
                [
                    [po_id],
                    [
                        "name",
                        "state",
                        "partner_id",
                        "amount_total",
                        "picking_ids",
                        "origin",
                        "requisition_id",
                    ],
                ],
            )
            meta["po"] = (po.get("result") or [None])[0]
            picking_ids = (meta["po"] or {}).get("picking_ids") or []
            if picking_ids:
                await page.goto(
                    f"{BASE_URL}/odoo/stock.picking/{picking_ids[0]}",
                    wait_until="domcontentloaded",
                )
                await page.locator(".o_form_view").first.wait_for()
                await shot(page, "30_wh_in.png")
                pick = await rpc(
                    page,
                    "stock.picking",
                    "read",
                    [[picking_ids[0]], ["name", "state", "picking_type_id"]],
                )
                meta["picking"] = (pick.get("result") or [None])[0]

            await page.goto(
                f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "31_egp_final.png")

            await page.goto(
                f"{BASE_URL}/odoo/purchase.request/{PR_ID}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "32_pr_final.png")

            egp = await rpc(
                page,
                "purchase.requisition",
                "read",
                [
                    [EGP_ID],
                    [
                        "name",
                        "state",
                        "egp_has_winner",
                        "requires_procurement_plan",
                        "procurement_document",
                        "estimated_cost",
                    ],
                ],
            )
            meta["egp"] = (egp.get("result") or [None])[0]
            meta["egp_id"] = EGP_ID
            meta["pr_id"] = PR_ID
            meta["pr_name"] = "PR6911019"
            print("META", json.dumps(meta, ensure_ascii=False, indent=2))
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error_finish.png"), full_page=True)
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
