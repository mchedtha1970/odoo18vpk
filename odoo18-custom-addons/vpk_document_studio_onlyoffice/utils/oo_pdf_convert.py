# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Convert filled Word (.docx) to PDF via ONLYOFFICE Document Server.

Templates are authored in OnlyOffice, so converting with the same engine keeps
fonts and layout identical to what the user sees in the editor.
"""

import base64
import json
import logging
import time
import uuid
from xml.etree import ElementTree as ET

import requests

from odoo.addons.onlyoffice_odoo.utils import config_utils, jwt_utils, url_utils

_logger = logging.getLogger(__name__)

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class OnlyOfficeConvertError(ValueError):
    """Raised when ONLYOFFICE ConvertService cannot produce a PDF."""


_ERROR_MESSAGES = {
    "-1": "Unknown error",
    "-2": "Conversion timeout",
    "-3": "Conversion error",
    "-4": "Error downloading the source document",
    "-5": "Incorrect password",
    "-6": "Error accessing conversion result database",
    "-7": "Input error",
    "-8": "Invalid token",
}


def _encode_token(env, payload, secret=None):
    token = jwt_utils.encode_payload(env, payload, secret)
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def _raise_convert_error(error):
    raise OnlyOfficeConvertError(
        "ONLYOFFICE แปลง PDF ไม่สำเร็จ: %s (%s)"
        % (_ERROR_MESSAGES.get(str(error), "error"), error)
    )


def _parse_convert_response(response):
    """Parse ConvertService JSON or XML body into a downloadable PDF URL."""
    content_type = (response.headers.get("Content-Type") or "").lower()
    text = response.text or ""
    if "json" in content_type or text.lstrip().startswith("{"):
        data = response.json() if "json" in content_type else json.loads(text)
        if data.get("error"):
            _raise_convert_error(data.get("error"))
        file_url = data.get("fileUrl") or data.get("FileUrl")
        end = data.get("endConvert", data.get("EndConvert"))
        percent = data.get("percent", data.get("Percent"))
        if not file_url or end in (False, "false", "False", 0, "0"):
            raise OnlyOfficeConvertError(
                "ONLYOFFICE ยังแปลง PDF ไม่เสร็จ (percent=%s)" % (percent or "?")
            )
        return file_url

    root = ET.fromstring(text)
    error = root.findtext("Error")
    if error:
        _raise_convert_error(error)
    end = (root.findtext("EndConvert") or "").lower() == "true"
    percent = root.findtext("Percent")
    file_url = root.findtext("FileUrl")
    if not end or not file_url:
        raise OnlyOfficeConvertError(
            "ONLYOFFICE ยังแปลง PDF ไม่เสร็จ (percent=%s)" % (percent or "?")
        )
    return file_url.replace("&amp;", "&")

def convert_docx_bytes_to_pdf_onlyoffice(env, docx_bytes, filename="document.docx"):
    """Return PDF bytes converted by ONLYOFFICE ConvertService.ashx."""
    if not docx_bytes:
        raise OnlyOfficeConvertError("ไม่มีไฟล์ Word สำหรับแปลงเป็น PDF")

    doc_server = config_utils.get_doc_server_inner_url(env) or config_utils.get_doc_server_public_url(env)
    if not doc_server:
        raise OnlyOfficeConvertError("ยังไม่ได้ตั้งค่า ONLYOFFICE Document Server")

    odoo_url = config_utils.get_base_or_odoo_url(env)
    if not odoo_url:
        raise OnlyOfficeConvertError("ยังไม่ได้ตั้งค่า URL ของ Odoo สำหรับ ONLYOFFICE")

    Attachment = env["ir.attachment"].sudo()
    attachment = Attachment.create(
        {
            "name": filename or "document.docx",
            "datas": base64.b64encode(docx_bytes),
            "mimetype": DOCX_MIME,
            "type": "binary",
            "description": "vpk_studio_onlyoffice_convert",
        }
    )
    # Commit so OnlyOffice can download the attachment over HTTP.
    env.cr.commit()

    try:
        security_token = _encode_token(
            env,
            {"id": env.user.id},
            config_utils.get_internal_jwt_secret(env),
        )
        file_url = (
            "%sonlyoffice/file/content/%s?oo_security_token=%s&db=%s"
            % (odoo_url, attachment.id, security_token, env.cr.dbname)
        )

        payload = {
            "async": False,
            "filetype": "docx",
            "key": uuid.uuid4().hex,
            "outputtype": "pdf",
            "title": filename or "document.docx",
            "url": file_url,
        }
        now = int(time.time())
        payload["iat"] = now
        payload["exp"] = now + 3600

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body = dict(payload)
        secret = config_utils.get_jwt_secret(env)
        if secret:
            token = _encode_token(env, dict(payload), secret)
            body["token"] = token
            headers[config_utils.get_jwt_header(env)] = "Bearer " + token

        convert_url = doc_server.rstrip("/") + "/ConvertService.ashx"
        _logger.info(
            "Converting studio docx to pdf with ONLYOFFICE %s (attachment %s)",
            convert_url,
            attachment.id,
        )
        response = requests.post(
            convert_url, json=body, headers=headers, timeout=120
        )
        response.raise_for_status()
        pdf_url = _parse_convert_response(response)
        pdf_url = url_utils.replace_public_url_to_internal(env, pdf_url)

        pdf_response = requests.get(pdf_url, timeout=120)
        pdf_response.raise_for_status()
        pdf_bytes = pdf_response.content
        if not pdf_bytes.startswith(b"%PDF"):
            raise OnlyOfficeConvertError("ONLYOFFICE คืนไฟล์ที่ไม่ใช่ PDF")
        return pdf_bytes
    finally:
        try:
            attachment.unlink()
            env.cr.commit()
        except Exception:
            _logger.debug(
                "Could not remove temporary OnlyOffice convert attachment",
                exc_info=True,
            )
