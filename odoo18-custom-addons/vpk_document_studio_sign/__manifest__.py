# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Document Studio - ลงนามเอกสาร",
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "summary": "ส่งเอกสาร Document Studio เข้ากล่องอนุมัติ ลงนามบน PDF และขอเลขสารบรรณ",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "vpk_document_studio",
        "vpk_tier_validation",
        "vpk_pr_saraban",
    ],
    "external_dependencies": {"python": ["pypdfium2", "PIL"]},
    "data": [
        "security/ir.model.access.csv",
        "data/tier_definition_data.xml",
        "views/studio_document_views.xml",
        "views/saraban_document_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_document_studio_sign/static/src/js/sign_pdf_viewer_dialog.js",
            "vpk_document_studio_sign/static/src/xml/sign_pdf_viewer_dialog.xml",
            "vpk_document_studio_sign/static/src/scss/sign_pdf_viewer_dialog.scss",
            "vpk_document_studio_sign/static/src/js/sign_pdf_viewer_action.js",
            "vpk_document_studio_sign/static/src/js/pdf_icon_field.js",
            "vpk_document_studio_sign/static/src/xml/pdf_icon_field.xml",
            "vpk_document_studio_sign/static/src/scss/pdf_icon_field.scss",
        ],
    },
    "installable": True,
    "application": False,
}
