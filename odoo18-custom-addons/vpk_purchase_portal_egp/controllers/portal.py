# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import binascii

from odoo import _, http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request

from odoo.addons.portal.controllers.web import Home as PortalHome
from odoo.addons.purchase.controllers.portal import CustomerPortal
from odoo.addons.web.controllers.utils import is_user_internal


class VendorPortalHome(PortalHome):
    """Redirect portal vendors to Vendor Portal after login."""

    def _login_redirect(self, uid, redirect=None):
        if not redirect and not is_user_internal(uid):
            redirect = "/my/vendor"
        return super()._login_redirect(uid, redirect=redirect)


class PurchaseVendorPortal(CustomerPortal):
    def _vendor_po_domain(self):
        return []

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        PurchaseOrder = request.env["purchase.order"]
        if PurchaseOrder.has_access("read"):
            if "vendor_waiting_count" in counters:
                values["vendor_waiting_count"] = PurchaseOrder.search_count(
                    [("state", "=", "sent")]
                )
            if "vendor_po_count" in counters:
                values["vendor_po_count"] = PurchaseOrder.search_count(
                    [("state", "in", ["sent", "purchase", "done", "cancel"])]
                )
            # Keep rfq list useful: include sent docs awaiting confirm
            if "rfq_count" in counters:
                values["rfq_count"] = PurchaseOrder.search_count(
                    [("state", "in", ["sent"])]
                )
        else:
            values.setdefault("vendor_waiting_count", 0)
            values.setdefault("vendor_po_count", 0)
        return values

    @http.route(["/vendor", "/vendor/home"], type="http", auth="public", website=True)
    def vendor_landing(self, **kw):
        """Vendor Portal entry: login page or vendor home."""
        if not request.env.user._is_public():
            return request.redirect("/my/vendor")
        return request.render(
            "vpk_purchase_portal_egp.vendor_portal_login",
            {
                "page_name": "vendor_login",
                "redirect": "/my/vendor",
            },
        )

    @http.route(["/vendor/login"], type="http", auth="public", website=True)
    def vendor_login_redirect(self, **kw):
        if not request.env.user._is_public():
            return request.redirect("/my/vendor")
        return request.redirect("/web/login?redirect=/my/vendor")

    @http.route(["/my/vendor", "/my/vendor/home"], type="http", auth="user", website=True)
    def portal_my_vendor_home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(
            self._prepare_home_portal_values(
                ["vendor_waiting_count", "vendor_po_count", "rfq_count", "purchase_count"]
            )
        )
        values["page_name"] = "vendor_home"
        return request.render("vpk_purchase_portal_egp.portal_my_vendor_home", values)

    @http.route(
        ["/my/vendor/orders", "/my/vendor/orders/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_vendor_orders(
        self,
        page=1,
        date_begin=None,
        date_end=None,
        sortby=None,
        filterby=None,
        **kw,
    ):
        return self._render_portal(
            "vpk_purchase_portal_egp.portal_my_vendor_orders",
            page,
            date_begin,
            date_end,
            sortby,
            filterby,
            [],
            {
                "waiting": {
                    "label": _("รอการยืนยัน"),
                    "domain": [("state", "=", "sent")],
                },
                "purchase": {
                    "label": _("ยืนยันแล้ว"),
                    "domain": [("state", "in", ["purchase", "done"])],
                },
                "cancel": {
                    "label": _("ยกเลิก"),
                    "domain": [("state", "=", "cancel")],
                },
                "all": {
                    "label": _("ทั้งหมด"),
                    "domain": [
                        ("state", "in", ["sent", "purchase", "done", "cancel"])
                    ],
                },
            },
            "waiting",
            "/my/vendor/orders",
            "my_vendor_orders_history",
            "vendor_orders",
            "orders",
        )

    # Override standard purchase list labels to Thai vendor wording via domain expand
    @http.route(
        ["/my/rfq", "/my/rfq/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_requests_for_quotation(
        self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw
    ):
        # Redirect vendors to unified vendor order list
        return request.redirect("/my/vendor/orders?filterby=waiting")

    @http.route(
        ["/my/purchase", "/my/purchase/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_purchase_orders(
        self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw
    ):
        return request.redirect("/my/vendor/orders?filterby=all")

    @http.route(
        ["/my/purchase/<int:order_id>/confirm"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_purchase_confirm_http(
        self, order_id, access_token=None, name=None, **kwargs
    ):
        """Simple Confirm for logged-in (or token) vendors."""
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my/vendor")

        if not order_sudo._can_vendor_confirm():
            return request.redirect(
                order_sudo.get_portal_url(query_string="&message=confirm_error")
            )

        signer = name or (
            request.env.user.name
            if not request.env.user._is_public()
            else order_sudo.partner_id.name
        )
        try:
            order_sudo.action_portal_vendor_confirm(name=signer, signature=False)
        except UserError:
            return request.redirect(
                order_sudo.get_portal_url(query_string="&message=confirm_error")
            )

        order_sudo.message_post(
            body=_("ผู้จำหน่าย %(name)s ยืนยันเอกสารบน Vendor Portal", name=signer),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=(
                order_sudo.partner_id.id
                if request.env.user._is_public()
                else request.env.user.partner_id.id
            ),
        )
        return request.redirect(
            order_sudo.get_portal_url(query_string="&message=sign_ok")
        )

    @http.route(
        ["/my/purchase/<int:order_id>/accept"],
        type="json",
        auth="public",
        website=True,
    )
    def portal_purchase_accept(
        self, order_id, access_token=None, name=None, signature=None
    ):
        access_token = access_token or request.httprequest.args.get("access_token")
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return {"error": _("เอกสารไม่ถูกต้อง")}

        if not order_sudo._can_vendor_confirm():
            return {
                "error": _(
                    "เอกสารนี้ไม่ได้อยู่ในสถานะที่ต้องให้ผู้จำหน่ายยืนยัน"
                )
            }
        if order_sudo.require_vendor_signature and not signature:
            return {"error": _("กรุณาลงนามก่อนยืนยัน")}

        try:
            order_sudo.action_portal_vendor_confirm(name=name, signature=signature)
            request.env.cr.flush()
        except (TypeError, binascii.Error):
            return {"error": _("ข้อมูลลายเซ็นไม่ถูกต้อง")}
        except UserError as err:
            return {"error": err.args[0]}

        if signature:
            pdf = (
                request.env["ir.actions.report"]
                .sudo()
                .with_context(purchase_include_signature=True)
                ._render_qweb_pdf(
                    "purchase.action_report_purchase_order", [order_sudo.id]
                )[0]
            )
            order_sudo.message_post(
                attachments=[("%s.pdf" % order_sudo.name, pdf)],
                author_id=(
                    order_sudo.partner_id.id
                    if request.env.user._is_public()
                    else request.env.user.partner_id.id
                ),
                body=_("ผู้จำหน่าย %(name)s ลงนามยืนยันเอกสารบนพอร์ทัล", name=name),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        else:
            order_sudo.message_post(
                author_id=(
                    order_sudo.partner_id.id
                    if request.env.user._is_public()
                    else request.env.user.partner_id.id
                ),
                body=_("ผู้จำหน่าย %(name)s ยืนยันเอกสารบนพอร์ทัล", name=name),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

        return {
            "force_refresh": True,
            "redirect_url": order_sudo.get_portal_url(query_string="&message=sign_ok"),
        }

    @http.route(
        ["/my/purchase/<int:order_id>/decline"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_purchase_decline(
        self, order_id, access_token=None, decline_message=None, **kwargs
    ):
        try:
            order_sudo = self._document_check_access(
                "purchase.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my/vendor")

        if order_sudo._can_vendor_confirm() and decline_message:
            order_sudo.action_portal_vendor_decline(decline_message=decline_message)
        return request.redirect(
            order_sudo.get_portal_url(query_string="&message=decline_ok")
        )

    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        values = super()._purchase_order_get_page_view_values(
            order, access_token, **kwargs
        )
        message = kwargs.get("message") or request.params.get("message")
        if message == "sign_ok":
            values["vendor_sign_message"] = _(
                "ขอบคุณที่ยืนยันเอกสาร ระบบได้ Confirm ใบสั่งซื้อแล้ว"
            )
        elif message == "decline_ok":
            values["vendor_sign_message"] = _("ระบบได้รับแจ้งการปฏิเสธเอกสารแล้ว")
        elif message == "confirm_error":
            values["vendor_sign_message"] = _(
                "ไม่สามารถยืนยันเอกสารได้ กรุณาติดต่อผู้ซื้อ"
            )
        values["can_vendor_confirm"] = order._can_vendor_confirm()
        return values
