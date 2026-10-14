# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Document - เอกสารแนบไฟล์",
    "version": "18.0.1.7.1",
    "category": "Productivity",
    "summary": "แนบไฟล์ PDF, Excel, Word และรูปภาพ พร้อมหมวดหมู่และเปิดดูไฟล์",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["mail"],
    "external_dependencies": {"python": ["openpyxl", "python-docx"]},
    "data": [
        "security/ir.model.access.csv",
        "security/vpk_document_security.xml",
        "data/document_category_data.xml",
        "views/document_category_views.xml",
        "views/document_views.xml",
        "views/google_drive_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_document/static/src/xml/document_file_field.xml",
            "vpk_document/static/src/js/document_file_field.js",
        ],
    },
    "installable": True,
    "application": True,
}
