# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import hashlib
import hmac as hmac_lib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import hmac as hmac_tool

from .file_preview import mimetype_from_name

_logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
GOOGLE_FILE_URL = "https://www.googleapis.com/drive/v3/files/%s"
GOOGLE_RESUMABLE_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
SHEETS_MIME = "application/vnd.google-apps.spreadsheet"
DOCS_MIME = "application/vnd.google-apps.document"
GOOGLE_KIND = {
    "excel": (SHEETS_MIME, "https://docs.google.com/spreadsheets/d/%s/edit"),
    "word": (DOCS_MIME, "https://docs.google.com/document/d/%s/edit"),
}
STATE_TTL = 600
MULTIPART_LIMIT = 5 * 1024 * 1024
RETRY_STATUSES = (429, 500, 502, 503)


def build_auth_url(client_id, redirect_uri, state):
    query = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DRIVE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    return "%s?%s" % (GOOGLE_AUTH_URL, query)


def build_multipart(filename, file_bytes, source_mime, target_mime=SHEETS_MIME):
    boundary = "vpkdocumentboundary"
    metadata = json.dumps({
        "name": filename or "document",
        "mimeType": target_mime,
    }).encode()
    source_mime = source_mime or "application/octet-stream"
    marker = boundary.encode()
    body = b"".join([
        b"--", marker, b"\r\n",
        b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
        metadata, b"\r\n",
        b"--", marker, b"\r\n",
        b"Content-Type: ", source_mime.encode(), b"\r\n\r\n",
        file_bytes, b"\r\n",
        b"--", marker, b"--\r\n",
    ])
    return body, "multipart/related; boundary=%s" % boundary


def google_error_text(payload):
    """Short Google error text, without tokens or response dumps."""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        message = str(error.get("message") or "")
        reasons = [
            str(item.get("reason"))
            for item in (error.get("errors") or [])
            if isinstance(item, dict) and item.get("reason")
        ]
        if reasons:
            message = "%s (%s)" % (message, ", ".join(reasons)) if message else ", ".join(reasons)
    elif isinstance(error, str):
        message = error
    else:
        message = ""
    return " ".join(message.split())[:180]


def raise_upload_error(status, payload):
    detail = google_error_text(payload)
    _logger.warning("Google Drive upload failed status=%s detail=%s", status, detail)
    if detail:
        raise UserError(_("อัปโหลดไฟล์ขึ้น Google Drive ไม่สำเร็จ: %s") % detail)
    raise UserError(_("อัปโหลดไฟล์ขึ้น Google Drive ไม่สำเร็จ"))


class VpkDocumentGoogleToken(models.Model):
    _name = "vpk.document.google.token"
    _description = "โทเคน Google Drive ของผู้ใช้"

    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        index=True,
        ondelete="cascade",
    )
    refresh_token = fields.Char(required=True)

    _sql_constraints = [
        ("user_uniq", "unique(user_id)", "เชื่อม Google Drive ได้หนึ่งบัญชีต่อผู้ใช้"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["user_id"] = self.env.uid
        return super().create(vals_list)


class VpkDocumentGoogleLink(models.Model):
    _name = "vpk.document.google.link"
    _description = "ไฟล์ที่เปิดใน Google Docs หรือ Google Sheets"

    document_id = fields.Many2one(
        comodel_name="vpk.document",
        required=True,
        index=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        index=True,
        ondelete="cascade",
    )
    drive_file_id = fields.Char(required=True)
    sheets_url = fields.Char(required=True)
    file_sha256 = fields.Char(required=True)

    _sql_constraints = [
        (
            "document_user_uniq",
            "unique(document_id, user_id)",
            "ผู้ใช้หนึ่งคนมีไฟล์บน Google Drive ได้หนึ่งไฟล์ต่อเอกสาร",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["user_id"] = self.env.uid
        return super().create(vals_list)


class VpkDocumentGoogleSettings(models.TransientModel):
    _name = "vpk.document.google.settings"
    _description = "ตั้งค่า Google Drive"

    client_id = fields.Char(string="Client ID")
    client_secret = fields.Char(string="Client secret")
    redirect_uri = fields.Char(string="Redirect URI", readonly=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        params = self.env["ir.config_parameter"].sudo()
        values.update({
            "client_id": params.get_param("vpk_document.google_client_id") or "",
            "client_secret": params.get_param("vpk_document.google_client_secret") or "",
            "redirect_uri": self.env["vpk.document.google.service"].redirect_uri(),
        })
        return values

    def action_save(self):
        self.ensure_one()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("vpk_document.google_client_id", (self.client_id or "").strip())
        if self.client_secret:
            params.set_param(
                "vpk_document.google_client_secret",
                self.client_secret.strip(),
            )
        return {"type": "ir.actions.act_window_close"}

    def action_disconnect(self):
        self.env["vpk.document.google.token"].search([
            ("user_id", "=", self.env.uid),
        ]).unlink()
        return {"type": "ir.actions.act_window_close"}


class VpkDocumentGoogleService(models.AbstractModel):
    _name = "vpk.document.google.service"
    _description = "เชื่อม Google Drive"

    def redirect_uri(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        return base.rstrip("/") + "/vpk_document/google/callback"

    def _client_config(self):
        params = self.env["ir.config_parameter"].sudo()
        client_id = (params.get_param("vpk_document.google_client_id") or "").strip()
        client_secret = (params.get_param("vpk_document.google_client_secret") or "").strip()
        if not client_id or not client_secret:
            raise UserError(_(
                "ยังไม่ได้ตั้งค่า Client ID และ Client secret "
                "ไปที่ เอกสาร → การตั้งค่า → Google Drive"
            ))
        return client_id, client_secret

    def _check_google_file(self, document):
        document.ensure_one()
        document.check_access("read")
        if document.file_type not in GOOGLE_KIND:
            raise UserError(_("เปิดใน Google ได้เฉพาะไฟล์ Excel และ Word"))
        if not document.with_context(bin_size=False).file:
            raise UserError(_("ยังไม่มีไฟล์แนบ"))

    def authorization_url(self, document):
        self._check_google_file(document)
        client_id, _secret = self._client_config()
        state = self._make_state(document.id)
        return build_auth_url(client_id, self.redirect_uri(), state), state

    def _make_state(self, document_id):
        payload = "%s:%s:%s" % (self.env.uid, document_id, int(time.time()))
        signature = hmac_tool(self.env(su=True), "vpk_document_google", payload)
        return "%s:%s" % (payload, signature)

    def _read_state(self, state):
        parts = (state or "").split(":")
        if len(parts) != 4:
            raise UserError(_("การเชื่อม Google Drive ไม่ถูกต้อง กรุณาลองใหม่"))
        user_id, document_id, issued_at, signature = parts
        payload = "%s:%s:%s" % (user_id, document_id, issued_at)
        expected = hmac_tool(self.env(su=True), "vpk_document_google", payload)
        if (
            not signature
            or len(signature) != len(expected)
            or not hmac_lib.compare_digest(signature, expected)
            or int(user_id) != self.env.uid
        ):
            raise UserError(_("การเชื่อม Google Drive ไม่ถูกต้อง กรุณาลองใหม่"))
        if int(time.time()) - int(issued_at) > STATE_TTL:
            raise UserError(_("หน้าเข้าสู่ระบบ Google หมดเวลา กรุณากดเปิดไฟล์อีกครั้ง"))
        return int(document_id)

    def _token_record(self):
        return self.env["vpk.document.google.token"].search([
            ("user_id", "=", self.env.uid),
        ], limit=1)

    def _save_refresh_token(self, refresh_token):
        if not refresh_token:
            return
        token = self._token_record()
        if token:
            token.refresh_token = refresh_token
        else:
            self.env["vpk.document.google.token"].create({
                "refresh_token": refresh_token,
            })

    def exchange_code(self, code):
        client_id, client_secret = self._client_config()
        status, payload = _request_json(
            GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": self.redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        if status != 200 or not payload.get("access_token"):
            raise UserError(_("Google ไม่ยืนยันการเข้าสู่ระบบ"))
        if not payload.get("refresh_token"):
            raise UserError(_(
                "Google ไม่ได้ให้สิทธิ์แบบถาวร กรุณากดเปิดไฟล์อีกครั้งแล้วกดอนุญาต"
            ))
        self._save_refresh_token(payload["refresh_token"])
        return payload["access_token"]

    def access_token(self):
        token = self._token_record()
        if not token:
            return False
        client_id, client_secret = self._client_config()
        status, payload = _request_json(
            GOOGLE_TOKEN_URL,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": token.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if status != 200 or not payload.get("access_token"):
            token.unlink()
            return False
        return payload["access_token"]

    def sheets_url_for(self, document, access_token=None):
        self._check_google_file(document)
        target_mime, url_template = GOOGLE_KIND[document.file_type]
        raw = document._file_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        link = self.env["vpk.document.google.link"].search([
            ("document_id", "=", document.id),
            ("user_id", "=", self.env.uid),
        ], limit=1)
        access_token = access_token or self.access_token()
        if not access_token:
            return False
        if (
            link
            and link.file_sha256 == digest
            and self._file_exists(access_token, link.drive_file_id)
        ):
            return link.sheets_url
        if link:
            old_file_id = link.drive_file_id
            link.unlink()
            self._delete_file(access_token, old_file_id)
        uploaded = self._upload(document, raw, access_token, target_mime)
        link = self.env["vpk.document.google.link"].create({
            "document_id": document.id,
            "drive_file_id": uploaded["id"],
            "sheets_url": url_template % uploaded["id"],
            "file_sha256": digest,
        })
        return link.sheets_url

    def _file_exists(self, access_token, file_id):
        status, _payload = _request_json(
            GOOGLE_FILE_URL % urllib.parse.quote(file_id),
            method="GET",
            headers={"Authorization": "Bearer %s" % access_token},
        )
        return status == 200

    def _delete_file(self, access_token, file_id):
        _request_json(
            GOOGLE_FILE_URL % urllib.parse.quote(file_id),
            method="DELETE",
            headers={"Authorization": "Bearer %s" % access_token},
        )

    def _upload(self, document, raw, access_token, target_mime):
        source_mime = mimetype_from_name(document.file_name) or "application/octet-stream"
        filename = document.file_name or document.name
        if len(raw) > MULTIPART_LIMIT:
            return self._upload_resumable(filename, raw, source_mime, target_mime, access_token)
        body, content_type = build_multipart(filename, raw, source_mime, target_mime)
        status, payload = _request_json(
            GOOGLE_UPLOAD_URL,
            body,
            headers={
                "Authorization": "Bearer %s" % access_token,
                "Content-Type": content_type,
            },
        )
        if status in RETRY_STATUSES:
            status, payload = _request_json(
                GOOGLE_UPLOAD_URL,
                body,
                headers={
                    "Authorization": "Bearer %s" % access_token,
                    "Content-Type": content_type,
                },
            )
        if status not in (200, 201) or not payload.get("id"):
            raise_upload_error(status, payload)
        return payload

    def _upload_resumable(self, filename, raw, source_mime, target_mime, access_token):
        metadata = json.dumps({
            "name": filename or "document",
            "mimeType": target_mime,
        }).encode()
        status, headers, _payload = _request(
            GOOGLE_RESUMABLE_URL,
            metadata,
            headers={
                "Authorization": "Bearer %s" % access_token,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": source_mime,
                "X-Upload-Content-Length": str(len(raw)),
            },
        )
        location = headers.get("Location")
        if status in RETRY_STATUSES:
            status, headers, _payload = _request(
                GOOGLE_RESUMABLE_URL,
                metadata,
                headers={
                    "Authorization": "Bearer %s" % access_token,
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": source_mime,
                    "X-Upload-Content-Length": str(len(raw)),
                },
            )
            location = headers.get("Location")
        if status != 200 or not location:
            raise_upload_error(status, _payload)
        status, _headers, payload = _request(
            location,
            raw,
            headers={
                "Authorization": "Bearer %s" % access_token,
                "Content-Type": source_mime,
                "Content-Length": str(len(raw)),
                "Content-Range": "bytes 0-%s/%s" % (len(raw) - 1, len(raw)),
            },
            method="PUT",
        )
        if status in RETRY_STATUSES:
            status, _headers, payload = _request(
                location,
                raw,
                headers={
                    "Authorization": "Bearer %s" % access_token,
                    "Content-Type": source_mime,
                    "Content-Length": str(len(raw)),
                    "Content-Range": "bytes 0-%s/%s" % (len(raw) - 1, len(raw)),
                },
                method="PUT",
            )
        if status not in (200, 201) or not payload.get("id"):
            raise_upload_error(status, payload)
        return payload


def _request_json(url, data=None, headers=None, method=None):
    status, _headers, payload = _request(url, data, headers, method)
    return status, payload


def _request(url, data=None, headers=None, method=None):
    hdrs = dict(headers or {})
    body = data
    if isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode()
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, response.headers, _json_body(response.read())
    except urllib.error.HTTPError as error:
        return error.code, error.headers, _json_body(error.read())


def _json_body(raw):
    text = (raw or b"").decode(errors="replace")
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": text[:200]}
