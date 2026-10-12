# -*- coding: utf-8 -*-
{
    "name": "VPK Buddhist Era Dates",
    "version": "18.0.1.0.0",
    "category": "Localization",
    "summary": "แสดงและกรอกวันที่เป็นปี พ.ศ. ทั้งหน้าจอและรายงาน",
    "description": """
แสดงปีในวันที่เป็น พ.ศ. สำหรับหน่วยงานภาครัฐ

* หน้าจอ: ช่องวันที่ รายการ ตัวกรอง และปฏิทินเลือกวันที่ แสดงปี พ.ศ.
* การกรอก: พิมพ์ปี พ.ศ. (เช่น 08/10/2569) หรือ ค.ศ. ก็ได้
* รายงาน PDF: วันที่จาก widget date / datetime แสดงปี พ.ศ.
* ค่าที่เก็บในฐานข้อมูลยังเป็น ค.ศ. ตามมาตรฐาน Odoo
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "vpk_buddhist_date/static/src/js/buddhist_date.js",
            "vpk_buddhist_date/static/src/js/buddhist_date_picker.js",
        ],
        "web.assets_frontend": [
            "vpk_buddhist_date/static/src/js/buddhist_date.js",
        ],
    },
    "installable": True,
    "application": False,
}
