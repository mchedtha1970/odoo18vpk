# -*- coding: utf-8 -*-
{
    "name": "VPK Thai Purchase Menu Labels",
    "version": "18.0.1.4.0",
    "category": "Purchases/Localizations",
    "summary": "ปรับเมนูระบบจัดซื้อจัดจ้าง และหมวดข้อมูลผู้จำหน่าย",
    "description": """
        - Purchase / สั่งซื้อ → ระบบจัดซื้อจัดจ้าง
        - เพิ่มเมนู ข้อมูลผู้จำหน่าย และย้าย ผู้จำหน่าย ไว้ภายใต้หมวดนี้
        - Products / สินค้า → ข้อมูลสินค้า
        - Orders / คำสั่ง → จัดการสั่งซื้อ
        - เพิ่มเมนู ข้อมูลใบขอซื้อ และย้าย ใบขอซื้อ / รายการใบขอซื้อ ไว้ภายใต้หมวดนี้
    """,
    "author": "VPK",
    "depends": ["purchase", "purchase_request"],
    "data": [
        "views/menu_views.xml",
        "data/menu_labels.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
