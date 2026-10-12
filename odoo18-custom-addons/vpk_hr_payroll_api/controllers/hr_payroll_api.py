# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class HrPayrollApiController(http.Controller):
    """รับชุดเงินเดือนจากระบบ HR.

    Auth: Header ``X-Api-Key`` หรือ ``Authorization: Bearer``
    """

    def _enabled(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_hr_payroll_api.enabled", "True")
            not in ("False", "0", "false", "")
        )

    def _configured_key(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_hr_payroll_api.api_key", "")
            or ""
        ).strip()

    def _provided_key(self):
        headers = request.httprequest.headers
        key = headers.get("X-Api-Key") or headers.get("x-api-key")
        if key:
            return key.strip()
        auth = headers.get("Authorization") or headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return ""

    def _authenticate(self):
        if not self._enabled():
            return self._json({"ok": False, "error": "HR payroll API is disabled"}, 503)
        configured = self._configured_key()
        if not configured:
            return self._json(
                {"ok": False, "error": "HR payroll API key is not configured"},
                503,
            )
        provided = self._provided_key()
        if not provided or provided != configured:
            return self._json({"ok": False, "error": "Invalid or missing API key"}, 401)
        return None

    def _json(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _body(self):
        raw = request.httprequest.get_data(as_text=True) or ""
        if not raw.strip():
            raise UserError("Empty request body")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as err:
            raise UserError("Invalid JSON body") from err
        if not isinstance(payload, dict):
            raise UserError("JSON body must be an object")
        return payload

    def _service(self):
        return request.env["vpk.hr.payroll.service"].sudo()

    @http.route(
        "/vpk/api/v1/hr/health",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def health(self, **kwargs):
        return self._json(
            {
                "ok": True,
                "service": "vpk_hr_payroll_api",
                "enabled": self._enabled(),
                "api_key_configured": bool(self._configured_key()),
            }
        )

    @http.route(
        "/vpk/api/v1/hr/payroll",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def payroll(self, **kwargs):
        denied = self._authenticate()
        if denied:
            return denied
        try:
            result = self._service().ingest_payroll(
                self._body(),
                request_meta={
                    "endpoint": "/vpk/api/v1/hr/payroll",
                    "method": "POST",
                    "remote_addr": request.httprequest.remote_addr,
                },
            )
        except (UserError, ValidationError) as err:
            return self._json({"ok": False, "error": str(err)}, 400)
        except Exception:
            _logger.exception("HR payroll endpoint failed")
            return self._json({"ok": False, "error": "Internal error"}, 500)
        return self._json(result, result.get("http_status", 202))

    @http.route(
        "/vpk/api/v1/hr/payroll/<string:external_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def payroll_status(self, external_id, source_system=None, **kwargs):
        denied = self._authenticate()
        if denied:
            return denied
        try:
            result = self._service().get_batch(external_id, source_system=source_system)
        except (UserError, ValidationError) as err:
            return self._json({"ok": False, "error": str(err)}, 404)
        return self._json(result)
