# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website


class VpkWebsiteHome(Website):
    """Send the site root to the branded login page instead of the website homepage."""

    @http.route()
    def index(self, **kw):
        if request.session.uid:
            return request.redirect("/odoo")
        return request.redirect("/web/login")
