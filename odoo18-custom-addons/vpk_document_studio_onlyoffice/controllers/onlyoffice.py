# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
from mimetypes import guess_type

from odoo.http import request

from odoo.addons.onlyoffice_odoo.controllers.controllers import Onlyoffice_Connector, onlyoffice_urlopen
from odoo.addons.onlyoffice_odoo.utils import config_utils, jwt_utils, url_utils

_logger = logging.getLogger(__name__)


def _with_db(url):
    if not url:
        return url
    dbname = request.env.cr.dbname
    if not dbname or "db=" in url:
        return url
    return "%s%cdb=%s" % (url, "&" if "?" in url else "?", dbname)


def _key_suffix(attachment):
    write_date = attachment.write_date
    if not write_date:
        return "0"
    return str(int(write_date.timestamp() * 1000))


class VpkOnlyofficeConnector(Onlyoffice_Connector):
    def prepare_editor_values(self, attachment, access_token, can_write):
        values = super().prepare_editor_values(attachment, access_token, can_write)
        config = values.get("editorConfig") or {}
        document = config.get("document") or {}
        editor = config.get("editorConfig") or {}
        # Document Server caches by key. A failed first download left an empty
        # document for this attachment; include write_date so a rewritten file
        # always opens a fresh copy.
        if document.get("key"):
            document["key"] = "%s_%s" % (document["key"], _key_suffix(attachment))
        if document.get("url"):
            document["url"] = _with_db(document["url"])
        if editor.get("callbackUrl"):
            editor["callbackUrl"] = _with_db(editor["callbackUrl"])
        editor.setdefault("customization", {})
        editor["customization"]["forcesave"] = True
        if config.get("token"):
            config.pop("token", None)
            config["token"] = jwt_utils.encode_payload(request.env, config)
        return values

    def editor_callback(self, attachment_id, oo_security_token=None, access_token=None, **_kw):
        response = super().editor_callback(
            attachment_id,
            oo_security_token=oo_security_token,
            access_token=access_token,
        )
        try:
            self._save_forcesave(attachment_id, oo_security_token, access_token)
        except Exception as ex:
            _logger.error(
                "POST /onlyoffice/editor/callback/%s - forcesave error: %s",
                attachment_id,
                str(ex),
            )
        return response

    def _callback_body(self):
        body = request.get_json_data()
        if not jwt_utils.is_jwt_enabled(request.env):
            return body
        token = body.get("token")
        if not token:
            token = request.httprequest.headers.get(config_utils.get_jwt_header(request.env))
            if token:
                token = token[len("Bearer ") :]
        if not token:
            return body
        payload = jwt_utils.decode_token(request.env, token)
        if payload.get("payload"):
            return payload["payload"]
        return payload

    def _save_forcesave(self, attachment_id, oo_security_token, access_token):
        body = self._callback_body()
        if body.get("status") != 6:
            return
        user = self.get_user_from_token(oo_security_token)
        attachment = self.get_attachment(attachment_id, user)
        if not attachment:
            raise Exception("attachment not found")
        attachment.validate_access(access_token)
        attachment.has_access("write")
        file_url = url_utils.replace_public_url_to_internal(request.env, body.get("url"))
        datas = onlyoffice_urlopen(file_url).read()
        attachment.write({"raw": datas, "mimetype": guess_type(file_url)[0] or attachment.mimetype})
        _logger.info("POST /onlyoffice/editor/callback/%s - forcesave written", attachment_id)
