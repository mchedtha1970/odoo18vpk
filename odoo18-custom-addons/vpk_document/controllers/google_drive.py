# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request


class VpkDocumentGoogleController(http.Controller):
    @http.route(
        "/vpk_document/google/open/<int:document_id>",
        type="http",
        auth="user",
    )
    def open_google_sheet(self, document_id, **kwargs):
        service = request.env["vpk.document.google.service"]
        try:
            document = self._document(document_id)
            service._check_google_file(document)
            service._client_config()
            if not service._token_record():
                return self._start_oauth(service, document)
            sheets_url = service.sheets_url_for(document)
        except UserError as error:
            return self._message(error)
        if not sheets_url:
            return self._start_oauth(service, document)
        return request.redirect(sheets_url, local=False)

    @http.route("/vpk_document/google/callback", type="http", auth="user")
    def google_callback(self, code=None, state=None, error=None, **kwargs):
        if error:
            return self._message("ยกเลิกการเชื่อม Google Drive")
        expected = request.session.pop("vpk_google_state", None)
        service = request.env["vpk.document.google.service"]
        try:
            if not code or not state or state != expected:
                raise UserError("การเชื่อม Google Drive ไม่ถูกต้อง กรุณาลองใหม่")
            document_id = service._read_state(state)
            document = self._document(document_id)
            access_token = service.exchange_code(code)
            sheets_url = service.sheets_url_for(document, access_token=access_token)
        except UserError as error:
            return self._message(error)
        if not sheets_url:
            return self._message("อัปโหลดไฟล์ขึ้น Google Drive ไม่สำเร็จ")
        return request.redirect(sheets_url, local=False)

    def _start_oauth(self, service, document):
        url, state = service.authorization_url(document)
        request.session["vpk_google_state"] = state
        return request.redirect(url, local=False)

    def _document(self, document_id):
        document = request.env["vpk.document"].browse(document_id).exists()
        if not document:
            raise UserError("ไม่พบเอกสาร")
        return document

    def _message(self, error):
        text = str(error.args[0] if getattr(error, "args", None) else error)
        return request.make_response(
            "<html><body><p>%s</p></body></html>" % _escape(text),
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )


def _escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
