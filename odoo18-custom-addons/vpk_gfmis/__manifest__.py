# -*- coding: utf-8 -*-
{
    "name": "กระบวนการ GFMIS",
    "version": "18.0.1.1.7",
    "category": "Accounting/Localizations",
    "summary": "เก็บและเชื่อมโยงเอกสารเบิกจ่าย New GFMIS Thai กับรายการใน ERP",
    "description": """
กระบวนการ GFMIS (ระบบเบิกจ่ายส่วนราชการ)
========================================

ขอบเขตสอดคล้องคู่มือระบบเบิกจ่าย (AP) ส่วนราชการ กรมบัญชีกลาง
(คู่มือระบบเบิกจ่าย(AP)_ส่วนราชการ_20230308) ผ่าน New GFMIS Thai:

* แบบฟอร์มขอเบิก ขบ.01 / ขบ.02 / ขบ.03 และแบบที่เกี่ยวข้อง
* จ่ายตรงผู้ขาย (ผ่าน/ไม่ผ่าน PO) และจ่ายผ่านส่วนราชการ
* ขั้นตอนอนุมัติขอเบิก (อม.01) และอนุมัติสั่งจ่าย (อม.02)
* เอกสารขอจ่ายโดยส่วนราชการ (ขจ.05)
* เบิกเกินส่งคืน
* ใบรับรองการหักภาษี ณ ที่จ่าย (แบบ 4235)
* เชื่อมโยงใบแจ้งหนี้ผู้ขาย, ใบสั่งซื้อ, การจ่ายชำระ ใน Odoo
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "purchase",
        "mail",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "security/gfmis_security.xml",
        "security/ir.model.access.csv",
        "data/gfmis_sequence.xml",
        "data/gfmis_wht_cert_sequence.xml",
        "data/gfmis_form_type_data.xml",
        "data/gfmis_test_users.xml",
        "views/gfmis_form_type_views.xml",
        "views/gfmis_document_views.xml",
        "wizard/gfmis_document_approve_wizard_views.xml",
        "views/disbursement_dashboard.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/purchase_order_views.xml",
        "views/account_payment_views.xml",
        "views/menu.xml",
        "report/gfmis_wht_cert_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_gfmis/static/src/scss/disbursement_dashboard.scss",
            "vpk_gfmis/static/src/dashboard/disbursement_dashboard.js",
            "vpk_gfmis/static/src/dashboard/disbursement_dashboard.xml",
        ],
    },
    "installable": True,
    "application": True,
}
