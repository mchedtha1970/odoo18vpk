# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        info = super().session_info()
        # iOS WebView cannot always read HttpOnly Set-Cookie; echo the
        # same value into the JSON-RPC authenticate body.
        info["session_id"] = request.session.sid
        return info
