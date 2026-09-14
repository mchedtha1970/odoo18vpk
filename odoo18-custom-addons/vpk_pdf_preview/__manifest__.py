# -*- coding: utf-8 -*-
{
    "name": "VPK PDF Preview",
    "version": "18.0.1.1.1",
    "category": "Productivity",
    "summary": "ดูตัวอย่าง PDF ก่อนพิมพ์หรือดาวน์โหลด",
    "description": """
เปิด viewer สำหรับรายงาน PDF ก่อนตัดสินใจพิมพ์หรือดาวน์โหลด
- รองรับทุก QWeb PDF report
- ปุ่ม พิมพ์ / ดาวน์โหลด / ปิด
    """,
    "author": "VPK",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "vpk_pdf_preview/static/src/js/pdf_report_preview_dialog.js",
            "vpk_pdf_preview/static/src/js/pdf_report_preview_dialog.xml",
            "vpk_pdf_preview/static/src/js/pdf_report_preview_handler.js",
            "vpk_pdf_preview/static/src/scss/pdf_report_preview.scss",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
