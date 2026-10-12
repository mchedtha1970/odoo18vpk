# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import http
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request, root

_logger = logging.getLogger(__name__)

CORS = "*"
DEFAULT_DB = "VPK-S1"
BASE = "/vpk/api/v1/maintenance"


def _sync_session_cookie():
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


class MaintenanceMobileApi(http.Controller):
    def _json(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _error(self, message, status=400):
        return self._json({"ok": False, "error": message}, status=status)

    def _body(self):
        raw = request.httprequest.get_data(as_text=True) or ""
        if not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as err:
            raise UserError("รูปแบบข้อมูลไม่ถูกต้อง") from err
        if not isinstance(payload, dict):
            raise UserError("รูปแบบข้อมูลไม่ถูกต้อง")
        return payload

    def _bearer(self):
        header = request.httprequest.headers.get("Authorization") or ""
        match = re.match(r"^bearer\s+(.+)$", header, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _bind_session(self, sid):
        if not sid or not root.session_store.is_valid_key(sid):
            return False
        if request.session.sid == sid and request.session.uid:
            request.update_env(user=request.session.uid)
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
        headers = request.httprequest.headers
        candidates = [
            self._bearer(),
            headers.get("X-Openerp-Session-Id"),
            headers.get("X-Session-Id"),
            request.httprequest.args.get("session_id"),
        ]
        for sid in candidates:
            if sid and self._bind_session(sid.strip()):
                return None
        uid = request.session.uid
        public_ids = request.env["ir.http"]._get_public_users()
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
        except UserError as err:
            return self._error(str(err), 400)
        except Exception:
            _logger.exception("maintenance mobile API failed")
            return self._error("เกิดข้อผิดพลาดภายในระบบ", 500)

    def _user_payload(self):
        user = request.env.user
        return {
            "id": user.id,
            "login": user.login,
            "name": user.name,
        }

    @http.route(BASE + "/health", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS, save_session=False)
    def health(self, **kwargs):
        return self._json({"ok": True, "service": "vpk_maintenance"})

    @http.route(BASE + "/auth/login", type="http", auth="none", methods=["POST"], csrf=False, cors=CORS)
    def login(self, **kwargs):
        def _run():
            payload = self._body()
            login = (payload.get("login") or "").strip()
            password = payload.get("password") or ""
            if not login or not password:
                raise UserError("กรุณาระบุชื่อผู้ใช้และรหัสผ่าน")
            dbname = (payload.get("db") or request.db or DEFAULT_DB or "").strip()
            if not dbname or not http.db_filter([dbname]):
                raise UserError("ไม่พบฐานข้อมูล")
            request.session.authenticate(dbname, {"login": login, "password": password, "type": "password"})
            if not request.session.uid:
                raise AccessDenied()
            return self._json({
                "ok": True,
                "session_id": _sync_session_cookie(),
                "user": self._user_payload(),
            })

        return self._handle(_run, auth=False)

    @http.route(BASE + "/auth/logout", type="http", auth="none", methods=["POST"], csrf=False, cors=CORS)
    def logout(self, **kwargs):
        denied = self._require_user()
        if denied:
            return self._json({"ok": True})
        request.session.logout(keep_db=True)
        return self._json({"ok": True})

    @http.route(BASE + "/me", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def me(self, **kwargs):
        def _run():
            return self._json({"ok": True, "user": self._user_payload()})

        return self._handle(_run)

    @http.route(BASE + "/home", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def home(self, period="today", **kwargs):
        def _run():
            data = request.env["maintenance.request"].get_maintenance_mobile_home(period or "today")
            return self._json({"ok": True, **data})

        return self._handle(_run)

    @http.route(BASE + "/form-options", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def form_options(self, **kwargs):
        def _run():
            return self._json({
                "ok": True,
                **request.env["maintenance.request"].mobile_form_options(),
            })

        return self._handle(_run)

    @http.route(BASE + "/assets", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def assets_search(self, q="", **kwargs):
        def _run():
            assets = request.env["maintenance.request"].mobile_search_assets(q or "")
            return self._json({"ok": True, "assets": assets})

        return self._handle(_run)

    @http.route(BASE + "/assets/lookup", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def assets_lookup(self, code="", **kwargs):
        def _run():
            asset = request.env["maintenance.request"].mobile_lookup_asset(code or "")
            return self._json({"ok": True, "asset": asset})

        return self._handle(_run)

    @http.route(BASE + "/requests", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def requests_list(self, state="open", q="", limit="40", offset="0", **kwargs):
        def _run():
            try:
                limit_value = min(int(limit or 40), 80)
                offset_value = max(int(offset or 0), 0)
            except ValueError as err:
                raise UserError("ค่าหน้าไม่ถูกต้อง") from err
            data = request.env["maintenance.request"].mobile_search(
                state or "open", q or "", limit_value, offset_value
            )
            return self._json({"ok": True, **data})

        return self._handle(_run)

    @http.route(BASE + "/requests", type="http", auth="none", methods=["POST"], csrf=False, cors=CORS)
    def request_create(self, **kwargs):
        def _run():
            detail = request.env["maintenance.request"].mobile_create(self._body())
            return self._json({"ok": True, "request": detail})

        return self._handle(_run)

    @http.route(BASE + "/requests/<int:request_id>", type="http", auth="none", methods=["GET"], csrf=False, cors=CORS)
    def request_detail(self, request_id, **kwargs):
        def _run():
            record = request.env["maintenance.request"].browse(request_id).exists()
            if not record:
                raise UserError("ไม่พบใบงาน")
            return self._json({"ok": True, "request": record.mobile_detail()})

        return self._handle(_run)

    @http.route(
        BASE + "/requests/<int:request_id>",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
    )
    def request_update(self, request_id, **kwargs):
        def _run():
            record = request.env["maintenance.request"].browse(request_id).exists()
            if not record:
                raise UserError("ไม่พบใบงาน")
            payload = self._body()
            detail = record.mobile_update(
                sub_state=payload.get("sub_state") or None,
                repair_detail=payload.get("repair_detail") if "repair_detail" in payload else None,
            )
            return self._json({"ok": True, "request": detail})

        return self._handle(_run)
