# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
import re

from odoo import http
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request, root

_logger = logging.getLogger(__name__)

CORS = "*"
DEFAULT_DB = "VPK-S1"


def sync_session_cookie():
    session = request.session
    if session.should_rotate:
        root.session_store.rotate(session, request.env)
        request.future_response.set_cookie(
            "session_id",
            session.sid,
            max_age=http.get_session_max_inactivity(request.env),
            httponly=True,
        )
    return session.sid


class VendorApiController(http.Controller):
    """REST API for the vendor portal mobile app.

    Base: ``/vpk/api/v1/vendor``
    """

    def _json(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _error(self, message, status=400):
        return self._json({"ok": False, "error": message}, status=status)

    def _parse_json_body(self):
        raw = request.httprequest.get_data(as_text=True) or ""
        if not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as err:
            raise UserError("Invalid JSON body") from err
        if not isinstance(payload, dict):
            raise UserError("JSON body must be an object")
        return payload

    def _bearer_token(self):
        header = request.httprequest.headers.get("Authorization") or ""
        match = re.match(r"^bearer\s+(.+)$", header, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _explicit_session_candidates(self):
        httprequest = request.httprequest
        headers = httprequest.headers
        values = [
            self._bearer_token(),
            headers.get("X-Openerp-Session-Id"),
            headers.get("X-Session-Id"),
            httprequest.args.get("session_id"),
        ]
        if httprequest.method in ("POST", "PUT", "PATCH"):
            try:
                payload = self._parse_json_body()
            except UserError:
                payload = {}
            if isinstance(payload, dict):
                values.append(payload.get("session_id"))
        seen = set()
        ordered = []
        for value in values:
            sid = (value or "").strip()
            if sid and sid not in seen:
                seen.add(sid)
                ordered.append(sid)
        return ordered

    def _bind_session(self, sid):
        if not sid or not root.session_store.is_valid_key(sid):
            return False
        if request.session.sid == sid and request.session.uid:
            return True
        session = root.session_store.get(sid)
        if not session or not session.uid:
            return False
        session.sid = sid
        request.session = session
        request.update_env(user=session.uid)
        return True

    def _require_user(self):
        if not request.db:
            return self._error("กรุณาเข้าสู่ระบบ", 401)
        bound = False
        for sid in self._explicit_session_candidates():
            if self._bind_session(sid):
                bound = True
                break
        uid = request.session.uid
        public_ids = request.env["ir.http"]._get_public_users()
        if not bound:
            if not uid or uid in public_ids:
                return self._error("กรุณาเข้าสู่ระบบ", 401)
            if request.env.uid != uid:
                request.update_env(user=uid)
        return None

    def _handle(self, callback, auth=True):
        if auth:
            denied = self._require_user()
            if denied:
                return denied
        try:
            return callback()
        except AccessDenied:
            return self._error("เข้าสู่ระบบไม่สำเร็จ", 401)
        except AccessError as err:
            return self._error(str(err), 403)
        except (UserError, ValidationError) as err:
            return self._error(str(err), 400)
        except Exception:
            _logger.exception("vendor API failed")
            return self._error("เกิดข้อผิดพลาดภายในระบบ", 500)

    def _service(self):
        return request.env["vpk.vendor.api.service"]

    @http.route(
        ["/vpk/api/v1/vendor", "/vpk/api/v1/vendor/"],
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
        save_session=False,
    )
    def index(self, **kwargs):
        return self._json(
            {
                "ok": True,
                "service": "vpk_vendor_api",
                "base": "/vpk/api/v1/vendor",
            }
        )

    @http.route(
        "/vpk/api/v1/vendor/auth/login",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
        readonly=False,
    )
    def login(self, **kwargs):
        def _run():
            payload = self._parse_json_body()
            login = (payload.get("login") or "").strip()
            password = payload.get("password") or ""
            if not login or not password:
                raise UserError("กรุณาระบุ login และ password")
            dbname = (payload.get("db") or request.db or DEFAULT_DB or "").strip()
            if not dbname:
                raise UserError("กรุณาระบุฐานข้อมูล")
            if not http.db_filter([dbname]):
                raise UserError("ไม่พบฐานข้อมูล")
            request.session.authenticate(
                dbname,
                {"login": login, "password": password, "type": "password"},
            )
            if not request.session.uid:
                raise AccessDenied()
            user = request.env.user
            if not user._is_portal():
                request.session.logout(keep_db=True)
                raise AccessError("บัญชีนี้ไม่ใช่ผู้ขาย")
            session_id = sync_session_cookie()
            me = request.env["vpk.vendor.api.service"].me()
            return self._json(
                {
                    "ok": True,
                    "uid": user.id,
                    "session_id": session_id,
                    "sid": session_id,
                    "user": me["user"],
                    "waiting_count": me["waiting_count"],
                    "confirmed_count": me["confirmed_count"],
                }
            )

        return self._handle(_run, auth=False)

    @http.route(
        "/vpk/api/v1/vendor/auth/register",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
        readonly=False,
    )
    def register(self, **kwargs):
        def _run():
            payload = self._parse_json_body()
            dbname = (payload.get("db") or request.db or DEFAULT_DB or "").strip()
            if not dbname:
                raise UserError("กรุณาระบุฐานข้อมูล")
            if not http.db_filter([dbname]):
                raise UserError("ไม่พบฐานข้อมูล")
            if request.session.db != dbname:
                request.session.db = dbname
            result = (
                request.env["vpk.vendor.api.service"]
                .sudo()
                .register_portal_account(payload)
            )
            return self._json(result)

        return self._handle(_run, auth=False)

    @http.route(
        "/vpk/api/v1/vendor/address/zips",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
        save_session=False,
    )
    def address_zips(self, q="", limit=20, **kwargs):
        def _run():
            data = request.env["vpk.vendor.api.service"].sudo().search_zips(q, limit=limit)
            return self._json({"ok": True, **data})

        return self._handle(_run, auth=False)

    @http.route(
        "/vpk/api/v1/vendor/auth/logout",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
    )
    def logout(self, **kwargs):
        request.session.logout(keep_db=True)
        return self._json({"ok": True})

    @http.route(
        "/vpk/api/v1/vendor/me",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def me(self, **kwargs):
        def _run():
            return self._json({"ok": True, **self._service().me()})

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/vendor/profile",
        type="http",
        auth="none",
        methods=["GET", "POST"],
        csrf=False,
        cors=CORS,
    )
    def profile(self, **kwargs):
        def _run():
            service = self._service()
            if request.httprequest.method == "POST":
                payload = self._parse_json_body()
                data = service.update_profile(payload)
            else:
                data = service.get_profile()
            return self._json({"ok": True, **data})

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/vendor/orders",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def orders(self, status="waiting", limit=50, offset=0, **kwargs):
        def _run():
            payload = self._service().search_orders(
                limit=limit, offset=offset, status=status
            )
            payload["ok"] = True
            return self._json(payload)

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/vendor/orders/<int:order_id>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def order_detail(self, order_id, **kwargs):
        def _run():
            return self._json({"ok": True, "item": self._service().get_order(order_id)})

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/vendor/orders/<int:order_id>/pdf",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def order_pdf(self, order_id, **kwargs):
        def _run():
            pdf = self._service().get_pdf(order_id)
            return request.make_response(
                pdf["content"],
                headers=[
                    ("Content-Type", "application/pdf"),
                    ("Content-Disposition", pdf["content_disposition"]),
                    ("Cache-Control", "private, no-store"),
                ],
            )

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/vendor/orders/<int:order_id>/sign",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
    )
    def order_sign(self, order_id, **kwargs):
        def _run():
            payload = self._parse_json_body()
            result = self._service().sign_order(
                order_id,
                signature=payload.get("signature"),
                name=payload.get("name"),
            )
            return self._json(result)

        return self._handle(_run)
