# -*- coding: utf-8 -*-
{
    "name": "VPK Login Page",
    "version": "18.0.1.2.0",
    "category": "Tools",
    "summary": "Full screen hospital branded login / signup / reset password page",
    "description": """
Replaces the default Odoo login card with a full screen two-column layout:

* left panel with a full bleed illustration, hospital name and tagline
* right panel with the company logo and a clean login form (username,
  password with show/hide, forgot password link, square fields)

Texts can be changed without touching the code through System Parameters:

* ``vpk_login_page.headline``
* ``vpk_login_page.organisation``
* ``vpk_login_page.tagline``
* ``vpk_login_page.welcome_subtitle``
* ``vpk_login_page.footnote``
    """,
    "author": "VPK",
    "depends": ["web"],
    "data": [
        "views/login_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "vpk_login_page/static/src/scss/login_page.scss",
            "vpk_login_page/static/src/js/login_page.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
