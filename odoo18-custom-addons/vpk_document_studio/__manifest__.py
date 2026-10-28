# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Document Studio",
    "version": "18.0.1.18.0",
    "category": "Productivity",
    "summary": "สร้างแบบฟอร์มเอง กำหนดฟิลด์ อัปโหลด Word แล้วพิมพ์เป็น Word/PDF",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["mail", "web", "l10n_th_amount_to_text"],
    "external_dependencies": {"python": ["docx"]},
    "data": [
        "security/studio_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/studio_document_type_views.xml",
        "views/studio_template_views.xml",
        "views/studio_document_views.xml",
        "views/studio_create_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_document_studio/static/src/js/studio_dynamic_form.js",
            "vpk_document_studio/static/src/xml/studio_dynamic_form.xml",
            "vpk_document_studio/static/src/js/word_editor_field.js",
            "vpk_document_studio/static/src/xml/word_editor_field.xml",
            "vpk_document_studio/static/src/js/pdf_viewer_field.js",
            "vpk_document_studio/static/src/xml/pdf_viewer_field.xml",
            "vpk_document_studio/static/src/scss/studio_dynamic_form.scss",
        ],
    },
    "installable": True,
    "application": True,
}
