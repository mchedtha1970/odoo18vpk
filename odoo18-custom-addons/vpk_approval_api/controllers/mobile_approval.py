# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging
import re

from odoo import http
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request, root

_logger = logging.getLogger(__name__)

CORS = "*"
DEFAULT_DB = "VPK-S1"


def sync_session_cookie():
    """Rotate after login so JSON ``session_id`` matches Set-Cookie.

    Odoo sets ``should_rotate`` in ``session.finalize`` and only writes the
    new sid onto the cookie after the controller returns. iOS cannot read
    HttpOnly cookies, so the JSON body must already contain the final sid.
    """
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


class MobileApprovalApiController(http.Controller):
    """REST API for the hospital approval mobile app.

    Base: ``/vpk/api/v1/mobile``

    Auth:
      * ``POST /auth/login`` with ``{"login","password"}``
      * later calls, any of:
        * cookie ``session_id``
        * header ``X-Openerp-Session-Id`` / ``X-Session-Id``
        * ``Authorization: Bearer <session_id or user API key>``
        * query/JSON ``session_id``
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
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise UserError("JSON body must be an object")
        return payload

    def _service(self):
        return request.env["vpk.approval.api.service"]

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
            headers.get("session_id"),
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

    def _bind_api_key(self, key):
        if not key:
            return False
        uid = (
            request.env["res.users.apikeys"]
            .sudo()
            ._check_credentials(scope="rpc", key=key)
        )
        if not uid:
            return False
        request.update_env(user=uid)
        return True

    def _require_user(self):
        if not request.db:
            return self._error("กรุณาเข้าสู่ระบบ", 401)
        bound = False
        for sid in self._explicit_session_candidates():
            if self._bind_session(sid):
                bound = True
                break
            if self._bind_api_key(sid):
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
        except UserError as err:
            return self._error(str(err), 400)
        except Exception:
            _logger.exception("mobile approval API failed")
            return self._error("เกิดข้อผิดพลาดภายในระบบ", 500)

    @http.route(
        ["/vpk/api/v1/mobile", "/vpk/api/v1/mobile/"],
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
                "service": "vpk_approval_api",
                "base": "/vpk/api/v1/mobile",
                "endpoints": [
                    "GET /health",
                    "POST /auth/login",
                    "POST /auth/logout",
                    "GET /me",
                    "GET /approvals",
                    "GET /approvals?status=pending|approved|rejected|all",
                    "GET /approvals/<id>",
                    "GET /approvals/<id>/pdf",
                    "POST /approvals/<id>/approve",
                    "POST /approvals/<id>/reject",
                ],
            }
        )

    @http.route(
        "/vpk/api/v1/mobile/health",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
        save_session=False,
    )
    def health(self, **kwargs):
        return self._json({"ok": True, "service": "vpk_approval_api"})

    @http.route(
        "/vpk/api/v1/mobile/auth/login",
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
            credential = {
                "login": login,
                "password": password,
                "type": "password",
            }
            request.session.authenticate(dbname, credential)
            if not request.session.uid:
                raise AccessDenied()
            user = request.env.user
            session_id = sync_session_cookie()
            return self._json(
                {
                    "ok": True,
                    "uid": user.id,
                    "session_id": session_id,
                    "sid": session_id,
                    "user": {
                        "id": user.id,
                        "login": user.login,
                        "name": user.name,
                        "job_title": user.partner_id.function or "",
                    },
                }
            )

        return self._handle(_run, auth=False)

    @http.route(
        "/vpk/api/v1/mobile/auth/logout",
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
        "/vpk/api/v1/mobile/me",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def me(self, **kwargs):
        def _run():
            service = self._service()
            pending = service.search_reviews(limit=1, offset=0, status="pending")
            approved = service.search_reviews(limit=1, offset=0, status="approved")
            return self._json(
                {
                    "ok": True,
                    "user": service.user_payload(),
                    "pending_count": pending["count"],
                    "approved_count": approved["count"],
                }
            )

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/mobile/approvals",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def approvals(self, **kwargs):
        def _run():
            result = self._service().search_reviews(
                limit=kwargs.get("limit"),
                offset=kwargs.get("offset"),
                status=kwargs.get("status"),
            )
            result["ok"] = True
            return self._json(result)

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/mobile/approvals/<int:review_id>",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def approval_detail(self, review_id, **kwargs):
        def _run():
            item = self._service().get_review(review_id)
            return self._json({"ok": True, "item": item})

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/mobile/approvals/<int:review_id>/pdf",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
        cors=CORS,
    )
    def approval_pdf(self, review_id, **kwargs):
        def _run():
            pdf = self._service().get_pdf(review_id)
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
        "/vpk/api/v1/mobile/approvals/<int:review_id>/approve",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
    )
    def approve(self, review_id, **kwargs):
        def _run():
            payload = self._parse_json_body()
            result = self._service().approve(
                review_id,
                signature=payload.get("signature"),
                comment=payload.get("comment"),
            )
            result["ok"] = True
            return self._json(result)

        return self._handle(_run)

    @http.route(
        "/vpk/api/v1/mobile/approvals/<int:review_id>/reject",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors=CORS,
    )
    def reject(self, review_id, **kwargs):
        def _run():
            payload = self._parse_json_body()
            result = self._service().reject(
                review_id,
                comment=payload.get("comment"),
            )
            result["ok"] = True
            return self._json(result)

        return self._handle(_run)
