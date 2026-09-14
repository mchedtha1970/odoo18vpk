# -*- coding: utf-8 -*-
from urllib.parse import unquote

from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class AssetInventoryPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        Sheet = request.env["vpk.asset.inventory.sheet"]
        if "asset_inventory_count" in counters:
            values["asset_inventory_count"] = (
                Sheet.search_count([("count_state", "=", "open")])
                if Sheet.has_access("read")
                else 0
            )
        return values

    def _asset_inventory_sheet_domain(self):
        user = request.env.user
        return [
            ("count_state", "=", "open"),
            "|",
            ("user_ids", "in", [user.id]),
            ("analytic_account_id", "in", user.asset_inventory_analytic_ids.ids),
        ]

    def _get_sheet_sudo(self, sheet_id, access_token=None):
        return self._document_check_access(
            "vpk.asset.inventory.sheet", sheet_id, access_token=access_token
        )

    def _get_line_sudo(self, line_id, access_token=None):
        return self._document_check_access(
            "vpk.asset.inventory.line", line_id, access_token=access_token
        )

    def _find_open_line_by_number(self, number, count_id=None):
        """Find open inventory line by asset number (exact then ilike)."""
        number = (number or "").strip()
        if not number:
            return request.env["vpk.asset.inventory.line"]
        Line = request.env["vpk.asset.inventory.line"].sudo()
        domain = [
            ("count_state", "=", "open"),
            ("asset_number", "=", number),
        ]
        if count_id:
            domain.append(("count_id", "=", int(count_id)))
        line = Line.search(domain, limit=1, order="id desc")
        if not line:
            domain_ilike = [
                ("count_state", "=", "open"),
                ("asset_number", "ilike", number),
            ]
            if count_id:
                domain_ilike.append(("count_id", "=", int(count_id)))
            line = Line.search(domain_ilike, limit=1, order="id desc")
        return line

    def _redirect_to_line_count(self, line):
        line._portal_ensure_token()
        url = f"/my/asset-inventory/line/{line.id}?access_token={line.access_token}"
        return request.redirect(url)

    # ---- Mobile camera QR: short public URL ----
    @http.route(
        [
            "/ai/<path:number>",
            "/asset-inventory/qr/<path:number>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def asset_inventory_qr_redirect(self, number, count_id=None, **kw):
        """Phone camera scans URL QR → open count form (tokenized, no login required)."""
        number = unquote(number or "").strip()
        # If sticker somehow embeds full path again, strip prefix
        for prefix in ("ai/", "/ai/", "asset-inventory/qr/"):
            if number.startswith(prefix):
                number = number[len(prefix) :]
        line = self._find_open_line_by_number(number, count_id=count_id)
        if not line:
            return request.render(
                "vpk_asset_inventory.portal_asset_inventory_qr_not_found",
                {
                    "number": number,
                    "page_name": "asset_inventory_scan",
                },
            )
        return self._redirect_to_line_count(line)

    @http.route(
        ["/my/asset-inventory", "/my/asset-inventory/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_asset_inventory_list(self, page=1, **kw):
        Sheet = request.env["vpk.asset.inventory.sheet"]
        domain = self._asset_inventory_sheet_domain()
        total = Sheet.search_count(domain)
        pager = portal_pager(
            url="/my/asset-inventory",
            total=total,
            page=page,
            step=self._items_per_page,
        )
        sheets = Sheet.search(
            domain, limit=self._items_per_page, offset=pager["offset"]
        )
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "sheets": sheets,
                "page_name": "asset_inventory",
                "pager": pager,
                "default_url": "/my/asset-inventory",
            }
        )
        return request.render(
            "vpk_asset_inventory.portal_asset_inventory_list", values
        )

    @http.route(
        ["/my/asset-inventory/sheet/<int:sheet_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_asset_inventory_sheet(self, sheet_id, access_token=None, **kw):
        try:
            sheet_sudo = self._get_sheet_sudo(sheet_id, access_token)
        except (AccessError, MissingError):
            return request.redirect("/my")

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "sheet": sheet_sudo,
                "lines": sheet_sudo.line_ids,
                "page_name": "asset_inventory_sheet",
                "access_token": access_token,
            }
        )
        return request.render(
            "vpk_asset_inventory.portal_asset_inventory_sheet", values
        )

    @http.route(
        ["/my/asset-inventory/line/<int:line_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_asset_inventory_line(self, line_id, access_token=None, **kw):
        try:
            line_sudo = self._get_line_sudo(line_id, access_token)
        except (AccessError, MissingError):
            return request.redirect("/my")

        from urllib.parse import quote_plus

        values = self._prepare_portal_layout_values()
        qr_url = line_sudo.get_portal_qr_url()
        values.update(
            {
                "line": line_sudo,
                "page_name": "asset_inventory_line",
                "access_token": access_token or line_sudo.access_token,
                "qr_url": qr_url,
                "qr_barcode_src": (
                    f"/report/barcode/?barcode_type=QR"
                    f"&value={quote_plus(qr_url)}&width=180&height=180"
                ),
                "error": kw.get("error"),
                "success": kw.get("success"),
            }
        )
        return request.render(
            "vpk_asset_inventory.portal_asset_inventory_line", values
        )

    @http.route(
        ["/my/asset-inventory/line/<int:line_id>/submit"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_asset_inventory_line_submit(self, line_id, access_token=None, **post):
        try:
            line_sudo = self._get_line_sudo(line_id, access_token)
        except (AccessError, MissingError):
            return request.redirect("/my")

        redirect = f"/my/asset-inventory/line/{line_id}"
        if access_token:
            redirect += f"?access_token={access_token}"

        try:
            qty = float(post.get("counted_qty") or 0)
            note = post.get("note") or ""
            if line_sudo.count_id.state != "open":
                raise UserError(_("บันทึกจำนวนได้เฉพาะช่วงเปิดนับ"))
            user = request.env.user
            if user._is_public():
                line_sudo.sudo().write(
                    {
                        "counted_qty": qty,
                        "note": note,
                        "counted_by": False,
                        "counted_date": fields.Datetime.now(),
                    }
                )
            else:
                line_sudo.sudo().action_register_count(qty, note=note, user=user)
        except (UserError, ValueError) as err:
            sep = "&" if "?" in redirect else "?"
            return request.redirect(f"{redirect}{sep}error={err}")

        sep = "&" if "?" in redirect else "?"
        return request.redirect(f"{redirect}{sep}success=1")

    @http.route(
        ["/my/asset-inventory/scan", "/my/asset-inventory/scan/<int:count_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_asset_inventory_scan(self, count_id=None, **kw):
        """Resolve scanned asset number / URL to count line + camera helper."""
        values = self._prepare_portal_layout_values()
        error = kw.get("error")
        number = (kw.get("number") or "").strip()
        Count = request.env["vpk.asset.inventory.count"]

        open_counts = Count.search([("state", "=", "open")])
        if count_id:
            open_counts = open_counts.filtered(lambda c: c.id == count_id)

        # Accept pasted full /ai/URL or portal URL
        if number:
            raw = number
            if "/ai/" in raw:
                number = unquote(raw.split("/ai/", 1)[-1].split("?", 1)[0])
            elif "/asset-inventory/qr/" in raw:
                number = unquote(
                    raw.split("/asset-inventory/qr/", 1)[-1].split("?", 1)[0]
                )

        if number and open_counts:
            # Prefer lines in sheets allowed for this user; fallback any open line
            Line = request.env["vpk.asset.inventory.line"]
            domain = self._asset_inventory_sheet_domain()
            allowed_sheets = request.env["vpk.asset.inventory.sheet"].search(domain)
            line = Line.search(
                [
                    ("count_id", "in", open_counts.ids),
                    ("sheet_id", "in", allowed_sheets.ids),
                    ("asset_number", "=", number),
                ],
                limit=1,
            )
            if not line:
                line = self._find_open_line_by_number(number, count_id=count_id)
                # still restrict if user has sheet ACL and line sheet not allowed
                if line and allowed_sheets and line.sheet_id not in allowed_sheets:
                    # officers see all
                    if not request.env.user.has_group(
                        "vpk_asset_inventory.group_asset_inventory_officer"
                    ):
                        line = Line.browse()
            if line:
                return self._redirect_to_line_count(line)
            error = _(
                "ไม่พบเลขทรัพย์สิน %s ในรอบตรวจนับที่เปิดอยู่"
            ) % number

        base = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        values.update(
            {
                "page_name": "asset_inventory_scan",
                "open_counts": open_counts,
                "count_id": count_id,
                "error": error,
                "number": number,
                "base_url": (base or "").rstrip("/"),
            }
        )
        return request.render(
            "vpk_asset_inventory.portal_asset_inventory_scan", values
        )

    @http.route(
        ["/my/asset-inventory/sheet/<int:sheet_id>/bulk"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_asset_inventory_sheet_bulk(self, sheet_id, access_token=None, **post):
        try:
            sheet_sudo = self._get_sheet_sudo(sheet_id, access_token)
        except (AccessError, MissingError):
            return request.redirect("/my")

        for line in sheet_sudo.line_ids:
            key = f"qty_{line.id}"
            if key not in post:
                continue
            raw = (post.get(key) or "").strip()
            if raw == "":
                continue
            try:
                qty = float(raw)
                note = post.get(f"note_{line.id}") or line.note
                if request.env.user._is_public():
                    if line.count_id.state != "open":
                        continue
                    line.sudo().write(
                        {
                            "counted_qty": qty,
                            "note": note,
                            "counted_date": fields.Datetime.now(),
                        }
                    )
                else:
                    line.sudo().action_register_count(
                        qty, note=note, user=request.env.user
                    )
            except (UserError, ValueError):
                continue

        redirect = f"/my/asset-inventory/sheet/{sheet_id}"
        if access_token:
            redirect += f"?access_token={access_token}&success=1"
        else:
            redirect += "?success=1"
        return request.redirect(redirect)
