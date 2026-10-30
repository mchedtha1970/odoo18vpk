# -*- coding: utf-8 -*-
{
    "name": "VPK e-Bidding",
    "version": "18.0.1.24.0",
    "category": "Purchases",
    "summary": "บันทึกแผนจัดซื้อจัดจ้างที่จัดทำและประกาศแล้วในระบบ e-GP",
    "description": """
ทะเบียนแผนจัดซื้อจัดจ้างจากระบบ e-GP ของกรมบัญชีกลาง
====================================================

ใช้บันทึกแผนที่สร้างและประกาศแล้วบน www.gprocurement.go.th ให้อยู่ใน ERP
ไม่ใช่หน้าจอประกาศแผนขึ้นเว็บไซต์ e-GP

- บันทึกรายการแผนทีละโครงการตามหน้าจอ e-GP
- นำเข้า Excel ตามเทมเพลตของกรมบัญชีกลาง
- แนบไฟล์ประกาศเผยแพร่แผนที่ได้จาก e-GP
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "mail",
        "vpk_buddhist_date",
        "vpk_document_studio_procurement",
        "vpk_purchase_agreement_egp",
    ],
    "external_dependencies": {
        "python": ["openpyxl"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/ebidding_plan_document_type_data.xml",
        "views/ebidding_plan_views.xml",
        "wizard/ebidding_plan_import_views.xml",
        "wizard/ebidding_plan_publish_code_views.xml",
        "views/menu_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_ebidding/static/src/js/month_year_field.js",
            "vpk_ebidding/static/src/xml/month_year_field.xml",
            "vpk_ebidding/static/src/js/x2many_selectable.js",
            "vpk_ebidding/static/src/xml/x2many_selectable.xml",
            "vpk_ebidding/static/src/js/stamp_number_pdf_viewer_dialog.js",
            "vpk_ebidding/static/src/xml/stamp_number_pdf_viewer_dialog.xml",
            "vpk_ebidding/static/src/js/stamp_number_pdf_viewer_action.js",
        ],
    },
    "installable": True,
    "application": False,
}
