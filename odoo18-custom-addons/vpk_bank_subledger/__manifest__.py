# -*- coding: utf-8 -*-
{
    "name": "บัญชีคุมเงินฝากธนาคาร",
    "version": "18.0.1.1.0",
    "category": "Accounting/Localizations",
    "summary": "เก็บยอดรับ จ่าย และคงเหลือของแต่ละบัญชีธนาคารที่ยุบเข้าผังบัญชีเดียวกัน",
    "description": """
บัญชีธนาคารหลายเลขที่ถูกผูกเข้าผังบัญชีเป็นกลุ่ม
โมดูลนี้เก็บยอดของแต่ละเลขที่บัญชีตามส่วนที่จัดสรรเข้าผัง
เพื่อออกรายงานยอดยกมา รับ จ่าย และคงเหลือ
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/bank_subledger_views.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
