# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from urllib.parse import quote

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


def _inline_disposition(filename):
    filename = filename or "file"
    ascii_name = filename.encode("ascii", "ignore").decode() or "file"
    ascii_name = ascii_name.replace("\\", "").replace('"', "")
    return "inline; filename=\"%s\"; filename*=UTF-8''%s" % (
        ascii_name,
        quote(filename),
    )


class VpkDocumentController(http.Controller):
    @http.route(
        "/vpk_document/open/<int:document_id>",
        type="http",
        auth="user",
    )
    def open_document(self, document_id, **kwargs):
        document = request.env["vpk.document"].browse(document_id)
        try:
            document.check_access("read")
            document = document.exists()
        except AccessError:
            document = request.env["vpk.document"]
        if not document:
            return request.not_found()
        body, mimetype = document._open_payload()
        if not body:
            return request.not_found()
        headers = [
            ("Content-Type", mimetype),
            ("Content-Disposition", _inline_disposition(document.file_name)),
            ("Content-Length", str(len(body))),
            ("X-Content-Type-Options", "nosniff"),
            ("Cache-Control", "private, no-store"),
        ]
        if document.file_type == "excel":
            headers.append((
                "Content-Security-Policy",
                "default-src 'none'; style-src 'self'; script-src 'self';",
            ))
        elif mimetype.startswith("text/html"):
            headers.append((
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:;",
            ))
        return request.make_response(body, headers=headers)
