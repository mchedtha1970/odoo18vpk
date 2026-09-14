# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class HisApiController(http.Controller):
    """Inbound HIS daily summary API.

    Auth: Header ``X-Api-Key: <key>`` or ``Authorization: Bearer <key>``
    Config: Settings → Invoicing → HIS API Key
    """

    def _api_enabled(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_his_api.enabled", "True")
            not in ("False", "0", "false", "")
        )

    def _get_configured_api_key(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_his_api.api_key", "")
            or ""
        ).strip()

    def _extract_api_key(self):
        headers = request.httprequest.headers
        key = headers.get("X-Api-Key") or headers.get("x-api-key")
        if key:
            return key.strip()
        auth = headers.get("Authorization") or headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return ""

    def _authenticate(self):
        if not self._api_enabled():
            return self._json_response(
                {"ok": False, "error": "HIS API is disabled"}, status=503
            )
        configured = self._get_configured_api_key()
        if not configured:
            return self._json_response(
                {
                    "ok": False,
                    "error": "HIS API key is not configured on the server",
                },
                status=503,
            )
        provided = self._extract_api_key()
        if not provided or provided != configured:
            return self._json_response(
                {"ok": False, "error": "Invalid or missing API key"}, status=401
            )
        return None

    def _json_response(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _parse_json_body(self):
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

    def _request_meta(self, endpoint):
        return {
            "endpoint": endpoint,
            "method": request.httprequest.method,
            "remote_addr": request.httprequest.remote_addr,
        }

    def _service(self):
        return request.env["vpk.his.api.service"].sudo()

    @http.route(
        "/vpk/api/v1/his/health",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_health(self, **kwargs):
        enabled = self._api_enabled()
        configured = bool(self._get_configured_api_key())
        return self._json_response(
            {
                "ok": True,
                "service": "vpk_his_api",
                "enabled": enabled,
                "api_key_configured": configured,
            }
        )

    @http.route(
        "/vpk/api/v1/his/revenue",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_revenue(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        try:
            payload = self._parse_json_body()
            result = self._service().ingest_revenue(
                payload,
                request_meta=self._request_meta("/vpk/api/v1/his/revenue"),
            )
            return self._json_response(result, status=result.get("http_status", 202))
        except (UserError, ValidationError) as err:
            return self._json_response({"ok": False, "error": str(err)}, status=400)
        except Exception:  # noqa: BLE001
            _logger.exception("HIS revenue endpoint failed")
            return self._json_response(
                {"ok": False, "error": "Internal server error"}, status=500
            )

    @http.route(
        "/vpk/api/v1/his/stock-issues",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_stock_issues(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        try:
            payload = self._parse_json_body()
            result = self._service().ingest_stock_issues(
                payload,
                request_meta=self._request_meta("/vpk/api/v1/his/stock-issues"),
            )
            return self._json_response(result, status=result.get("http_status", 202))
        except (UserError, ValidationError) as err:
            return self._json_response({"ok": False, "error": str(err)}, status=400)
        except Exception:  # noqa: BLE001
            _logger.exception("HIS stock-issues endpoint failed")
            return self._json_response(
                {"ok": False, "error": "Internal server error"}, status=500
            )

    @http.route(
        "/vpk/api/v1/his/stock-requisitions",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_stock_requisitions(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        try:
            payload = self._parse_json_body()
            result = self._service().ingest_stock_requisitions(
                payload,
                request_meta=self._request_meta("/vpk/api/v1/his/stock-requisitions"),
            )
            return self._json_response(result, status=result.get("http_status", 202))
        except (UserError, ValidationError) as err:
            return self._json_response({"ok": False, "error": str(err)}, status=400)
        except Exception:  # noqa: BLE001
            _logger.exception("HIS stock-requisitions endpoint failed")
            return self._json_response(
                {"ok": False, "error": "Internal server error"}, status=500
            )

    @http.route(
        "/vpk/api/v1/his/batches/<string:external_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_batch_get(self, external_id, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        try:
            source_system = (
                request.httprequest.args.get("source_system")
                or kwargs.get("source_system")
            )
            result = self._service().get_batch(external_id, source_system=source_system)
            status = 200 if result.get("state") == "posted" else 202
            return self._json_response(result, status=status)
        except (UserError, ValidationError) as err:
            msg = str(err)
            code = 404 if "not found" in msg.lower() else 400
            return self._json_response({"ok": False, "error": msg}, status=code)

    @http.route(
        "/vpk/api/v1/his/lookups/entitlements",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_lookup_entitlements(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        return self._json_response(self._service().list_entitlements())

    @http.route(
        "/vpk/api/v1/his/lookups/payment-methods",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_lookup_payment_methods(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        return self._json_response(self._service().list_payment_methods())

    @http.route(
        "/vpk/api/v1/his/lookups/warehouses",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_lookup_warehouses(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        return self._json_response(self._service().list_warehouses())

    @http.route(
        "/vpk/api/v1/his/lookups/products",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def his_lookup_products(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        args = request.httprequest.args
        codes = args.get("codes") or args.get("code") or kwargs.get("codes") or kwargs.get("code")
        code_list = [part.strip() for part in str(codes or "").split(",") if part.strip()]
        tracking = args.get("tracking") or kwargs.get("tracking")
        limit = args.get("limit") or kwargs.get("limit") or 50
        return self._json_response(
            self._service().list_products(
                codes=code_list, tracking=tracking, limit=limit
            )
        )
