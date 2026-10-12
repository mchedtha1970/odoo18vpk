# -*- coding: utf-8 -*-
{
    "name": "ติดตามงานเจ้าหนี้ การเงิน และบัญชี",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "แดชบอร์ดติดตามงานค้างและความเคลื่อนไหวของเจ้าหนี้ การเงิน และบัญชี",
    "description": """
ติดตามงานตั้งแต่ใบแจ้งหนี้ผู้ขาย การจ่ายเงินและเช็ค จนถึงเอกสาร GFMIS และรายการบัญชี
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "vpk_gfmis",
        "vpk_cheque_management",
    ],
    "data": [
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_finance_flow/static/src/scss/finance_flow_dashboard.scss",
            "vpk_finance_flow/static/src/dashboard/finance_flow_dashboard.js",
            "vpk_finance_flow/static/src/dashboard/finance_flow_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
}
