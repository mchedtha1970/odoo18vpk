# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json
import logging

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class VendorApiController(http.Controller):
    """Inbound vendor profile registration for external systems.

    Auth: Header ``X-Api-Key: <key>`` or ``Authorization: Bearer <key>``
    Config: Settings → Purchases → Vendor API Key

    Documents:
    - JSON register with ``documents[].content_base64``
    - multipart/form-data register: field ``payload`` (JSON) + files
    - POST ``/vpk/api/v1/vendors/<external_id>/documents``
    """

    def _api_enabled(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_vendor_api.enabled", "True")
            not in ("False", "0", "false", "")
        )

    def _get_configured_api_key(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_vendor_api.api_key", "")
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
                {"ok": False, "error": "Vendor API is disabled"}, status=503
            )
        configured = self._get_configured_api_key()
        if not configured:
            return self._json_response(
                {
                    "ok": False,
                    "error": "Vendor API key is not configured on the server",
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

    def _is_multipart(self):
        ctype = (request.httprequest.content_type or "").lower()
        return "multipart/form-data" in ctype

    def _parse_multipart_payload(self, require_payload=True):
        """Build payload dict from multipart: JSON field + uploaded files."""
        form = request.httprequest.form
        payload_raw = form.get("payload") or form.get("data") or form.get("json")
        if payload_raw:
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError as err:
                raise UserError("Invalid JSON in 'payload' form field") from err
            if not isinstance(payload, dict):
                raise UserError("'payload' must be a JSON object")
        elif require_payload:
            # Allow profile fields as plain form keys
            payload = {}
            skip = {"payload", "data", "json", "doc_type", "display_name", "replace"}
            for key in form:
                if key in skip or key.startswith("file"):
                    continue
                payload[key] = form.get(key)
            if not payload and not request.httprequest.files:
                raise UserError("Missing 'payload' JSON or form fields")
        else:
            payload = {}

        documents = list(payload.get("documents") or payload.get("files") or [])
        documents.extend(self._files_from_request())
        if documents:
            payload["documents"] = documents
        return payload

    def _files_from_request(self):
        """Read uploaded files from multipart request into document dicts."""
        form = request.httprequest.form
        default_doc_type = form.get("doc_type") or "other"
        default_display = form.get("display_name") or False
        replace_raw = form.get("replace")
        replace = True if replace_raw is None else str(replace_raw).lower() not in (
            "0",
            "false",
            "no",
        )

        documents = []
        files = request.httprequest.files
        # Support files, file, documents, document
        collected = []
        for key in ("files", "file", "documents", "document"):
            collected.extend(files.getlist(key))
        # Any other file fields
        for key in files:
            if key not in ("files", "file", "documents", "document"):
                collected.extend(files.getlist(key))

        seen = set()
        for storage in collected:
            if not storage or not storage.filename:
                continue
            # de-dup same Werkzeug FileStorage object
            obj_id = id(storage)
            if obj_id in seen:
                continue
            seen.add(obj_id)
            content = storage.read()
            # Per-file optional metadata: doc_type_<filename> not practical;
            # use form-level doc_type, or filename prefix "type__name.ext"
            filename = storage.filename
            doc_type = default_doc_type
            display_name = default_display or filename
            if "__" in filename and not form.get("doc_type"):
                prefix, rest = filename.split("__", 1)
                if prefix and rest:
                    doc_type = prefix
                    filename = rest
                    display_name = rest
            documents.append(
                {
                    "filename": filename,
                    "display_name": display_name,
                    "doc_type": doc_type,
                    "mimetype": storage.mimetype or False,
                    "content": content,
                    "replace": replace,
                }
            )
        return documents

    def _request_meta(self, endpoint):
        return {
            "endpoint": endpoint,
            "method": request.httprequest.method,
            "remote_addr": request.httprequest.remote_addr,
        }

    def _find_partner(self, external_id):
        return (
            request.env["res.partner"]
            .sudo()
            .search([("vpk_vendor_external_id", "=", external_id)], limit=1)
        )

    @http.route(
        "/vpk/api/v1/vendors/register",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def vendor_register(self, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        try:
            if self._is_multipart():
                payload = self._parse_multipart_payload(require_payload=True)
            else:
                payload = self._parse_json_body()
            result = (
                request.env["vpk.vendor.api.service"]
                .sudo()
                .register_vendor(
                    payload,
                    request_meta=self._request_meta("/vpk/api/v1/vendors/register"),
                )
            )
            return self._json_response(result, status=200)
        except (UserError, ValidationError) as err:
            return self._json_response({"ok": False, "error": str(err)}, status=400)
        except Exception:  # noqa: BLE001
            _logger.exception("Vendor register endpoint failed")
            return self._json_response(
                {"ok": False, "error": "Internal server error"}, status=500
            )

    @http.route(
        "/vpk/api/v1/vendors/<string:external_id>/documents",
        type="http",
        auth="public",
        methods=["POST", "GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def vendor_documents(self, external_id, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        partner = self._find_partner(external_id)
        if not partner:
            return self._json_response(
                {"ok": False, "error": "Vendor not found"}, status=404
            )
        service = request.env["vpk.vendor.api.service"].sudo()
        if request.httprequest.method == "GET":
            return self._json_response(
                {
                    "ok": True,
                    "partner_id": partner.id,
                    "external_id": partner.vpk_vendor_external_id,
                    "documents": service.list_vendor_documents(partner),
                }
            )
        try:
            if self._is_multipart():
                payload = self._parse_multipart_payload(require_payload=False)
                documents = payload.get("documents") or []
            else:
                body = self._parse_json_body()
                documents = body.get("documents") or body.get("files") or []
            if not documents:
                raise UserError("No documents provided")
            result = service.upload_vendor_documents(
                partner,
                documents,
                request_meta=self._request_meta(
                    "/vpk/api/v1/vendors/%s/documents" % external_id
                ),
            )
            return self._json_response(result, status=200)
        except (UserError, ValidationError) as err:
            return self._json_response({"ok": False, "error": str(err)}, status=400)
        except Exception:  # noqa: BLE001
            _logger.exception("Vendor documents endpoint failed")
            return self._json_response(
                {"ok": False, "error": "Internal server error"}, status=500
            )

    @http.route(
        "/vpk/api/v1/vendors/<string:external_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def vendor_get(self, external_id, **kwargs):
        auth_error = self._authenticate()
        if auth_error:
            return auth_error
        partner = self._find_partner(external_id)
        if not partner:
            return self._json_response(
                {"ok": False, "error": "Vendor not found"}, status=404
            )
        docs = (
            request.env["vpk.vendor.api.service"].sudo().list_vendor_documents(partner)
        )
        return self._json_response(
            {
                "ok": True,
                "partner_id": partner.id,
                "external_id": partner.vpk_vendor_external_id,
                "name": partner.name,
                "name_company": partner.name_company or False,
                "vat": partner.vat or False,
                "company_registry": partner.company_registry or False,
                "email": partner.email or False,
                "phone": partner.phone or False,
                "mobile": partner.mobile or False,
                "supplier_rank": partner.supplier_rank,
                "documents": docs,
            },
            status=200,
        )

    @http.route(
        "/vpk/api/v1/vendors/health",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
        website=False,
    )
    def vendor_health(self, **kwargs):
        """Liveness check (no auth). Does not expose secrets."""
        enabled = self._api_enabled()
        configured = bool(self._get_configured_api_key())
        return self._json_response(
            {
                "ok": True,
                "service": "vpk_vendor_api",
                "enabled": enabled,
                "api_key_configured": configured,
            }
        )
