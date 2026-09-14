# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import http
from odoo.addons.web.controllers.session import Session

from .mobile_approval import sync_session_cookie


class MobileAwareSession(Session):
    @http.route()
    def authenticate(self, db, login, password, base_location=None):
        result = super().authenticate(
            db, login, password, base_location=base_location
        )
        if isinstance(result, dict) and result.get("uid"):
            result["session_id"] = sync_session_cookie()
        return result
