# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Document Studio OnlyOffice",
    "version": "18.0.1.3.0",
    "category": "Productivity",
    "summary": "แก้ไขไฟล์ Word ของ Document Studio ด้วย ONLYOFFICE Docs",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["vpk_document_studio", "onlyoffice_odoo"],
    "data": [
        "data/onlyoffice_config.xml",
        "views/studio_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_document_studio_onlyoffice/static/src/js/onlyoffice_editor_field.js",
            "vpk_document_studio_onlyoffice/static/src/xml/onlyoffice_editor_field.xml",
            "vpk_document_studio_onlyoffice/static/src/scss/onlyoffice_editor.scss",
        ],
    },
    "installable": True,
    "application": False,
}
