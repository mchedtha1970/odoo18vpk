# -*- coding: utf-8 -*-
{
    "name": "บัญชีคุมวัสดุ",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "รายงานบัญชีคุมวัสดุตามช่วงวันที่ หมวดสินค้า และคลัง",
    "description": """
พิมพ์รายงานบัญชีคุมวัสดุแบบรายสินค้า
แสดงรับ จ่าย และยอดคงเหลือ พร้อมยอดยกไปรายวัน
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["stock", "stock_account"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/stock_card_report_views.xml",
        "report/stock_card_report.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}
