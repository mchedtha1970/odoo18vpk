#!/usr/bin/env python3
"""จบ UAT CCTV-16: สร้าง PO จาก e-GP ผ่าน RPC แล้วจับภาพ PO/สัญญา/QC"""
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
EGP_ID = 83
PR_ID = 178
CONTRACT_CONFIRMED_ID = 318  # CTR/2026/0040
PROC_OWNER = "uat.equipment"


async def shot(page, name: str):
    path = OUT / name
    await page.locator(".o_action, .o_form_view, .o_content").first.screenshot(path=str(path))
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


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta.pop("error", None)

    async with async_playwright() as pw:
        browser = await launch_browser(pw, headless=True)
        page = await browser.new_page(
            viewport={"width": 1440, "height": 1100}, device_scale_factor=2
        )
        try:
            await login_as(page, PROC_OWNER)

            # cancel duplicate draft contract if still draft
            await rpc(
                page,
                "purchase.contract",
                "write",
                [[319], {"state": "cancel"}],
            )

            # ensure winner announcement attached via document_file binary
            import base64

            pdf_b64 = base64.b64encode(
                b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
            ).decode()
            types = await rpc(
                page,
                "purchase.requisition.egp.document.type",
                "search_read",
                [[["code", "=", "winner_announcement"]]],
                {"fields": ["id"], "limit": 1},
            )
            type_id = types["result"][0]["id"]
            existing = await rpc(
                page,
                "purchase.requisition.egp.document",
                "search_read",
                [[["requisition_id", "=", EGP_ID], ["document_type_id", "=", type_id]]],
                {"fields": ["id"], "limit": 1},
            )
            vals = {
                "requisition_id": EGP_ID,
                "document_type_id": type_id,
                "document_file": pdf_b64,
                "document_filename": "uat_winner_announcement.pdf",
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
                    page,
                    "purchase.requisition.egp.document",
                    "create",
                    [vals],
                )
                print("winner doc", created)

            # create PO via wizard model
            wiz = await rpc(
                page,
                "purchase.requisition.create.rfq",
                "create",
                [
                    {
                        "requisition_id": EGP_ID,
                        "partner_id": 41,
                        "egp_bid_reference": "BID-CCTV-16",
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
            po_id = action["result"]["res_id"]

            await page.goto(
                f"{BASE_URL}/odoo/purchase.order/{po_id}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "27_po_wizard.png")  # replace with PO creation result header
            await shot(page, "28_po_form.png")
            await shot(page, "29_po_header_actions.png")

            # scroll lines
            lines = page.locator('.o_field_widget[name="order_line"]')
            if await lines.count():
                await lines.first.scroll_into_view_if_needed()
                await shot(page, "30_po_lines.png")

            # look for QC / WA / receipt smart buttons
            header_btns = page.locator(".o_control_panel button, .o_statusbar_buttons button, .oe_button_box button")
            texts = []
            for i in range(await header_btns.count()):
                t = " ".join((await header_btns.nth(i).inner_text()).split())
                if t:
                    texts.append(t)
            print("PO buttons:", texts)
            meta["po_buttons"] = texts

            # open contract confirmed
            await page.goto(
                f"{BASE_URL}/odoo/purchase.contract/{CONTRACT_CONFIRMED_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "25_contract_confirmed.png")
            await shot(page, "24_contract_type.png")

            # egp final
            await page.goto(
                f"{BASE_URL}/odoo/purchase.requisition/{EGP_ID}",
                wait_until="domcontentloaded",
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "31_egp_final.png")

            # PR final with create PO gone / linked
            await page.goto(
                f"{BASE_URL}/odoo/purchase.request/{PR_ID}", wait_until="domcontentloaded"
            )
            await page.locator(".o_form_view").first.wait_for()
            await shot(page, "32_pr_final.png")

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
                        "contract_id",
                        "origin",
                        "requisition_id",
                    ],
                ],
            )
            meta["po"] = (po.get("result") or [None])[0]
            meta["contract_id"] = CONTRACT_CONFIRMED_ID
            ctr = await rpc(
                page,
                "purchase.contract",
                "read",
                [
                    [CONTRACT_CONFIRMED_ID],
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
            meta["contract"] = (ctr.get("result") or [None])[0]
            egp = await rpc(
                page,
                "purchase.requisition",
                "read",
                [[EGP_ID], ["name", "state", "ebidding_plan_line_id", "egp_award_approved"]],
            )
            meta["egp"] = (egp.get("result") or [None])[0]
            # pickings detail
            picking_ids = (meta["po"] or {}).get("picking_ids") or []
            if picking_ids:
                picks = await rpc(
                    page,
                    "stock.picking",
                    "read",
                    [picking_ids, ["name", "state", "picking_type_id"]],
                )
                meta["pickings"] = picks.get("result")
            else:
                meta["pickings"] = []

            # QC / WA models linked?
            for model in (
                "work.acceptance",
                "purchase.work.acceptance",
                "qc.inspection",
                "quality.check",
            ):
                try:
                    found = await rpc(
                        page,
                        model,
                        "search_read",
                        [[["purchase_id", "=", po_id]]],
                        {"fields": ["name", "state"], "limit": 5},
                    )
                    if "error" not in found:
                        meta.setdefault("related", {})[model] = found.get("result")
                except Exception:
                    pass

            prod = await rpc(
                page,
                "product.product",
                "search_read",
                [[["default_code", "=", "CCTV-16"]]],
                {"fields": ["type", "is_storable", "name"], "limit": 1},
            )
            meta["product"] = (prod.get("result") or [None])[0]
            meta["pr_name"] = "PR6911015"
            meta["egp_name"] = "EGP/2026/0158"
            meta["plan"] = None
            meta["plan_note"] = (
                "วิธีเฉพาะเจาะจง ไม่มีปุ่มสร้างแผนบน e-GP "
                "(ปุ่มสร้างแผนมีเฉพาะ is_ebidding_method)"
            )

            print("META", json.dumps(meta, ensure_ascii=False, indent=2))
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as error:
            print("FAIL", error)
            await page.screenshot(path=str(OUT / "error_finish.png"), full_page=True)
            meta["error"] = str(error)
            META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            raise
        finally:
            await browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
