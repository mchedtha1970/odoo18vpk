# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "VPK ใบขอเบิกเงิน (ขบ.01) - กรอกข้อมูลลง template Excel",
    "version": "18.0.1.4.2",
    "category": "Accounting",
    "summary": "ฟอร์มกรอกใบขอเบิกเงิน ขบ.01 บันทึกข้อมูลเข้า template Excel อัตโนมัติ และแนบไฟล์เก็บไว้ในเอกสาร",
    "description": """
ใบขอเบิกเงิน (ขบ.01)
====================
เดิมการเงินใช้ไฟล์ Excel (template ขบ.01) กรอกทีละใบแล้วบันทึกเก็บไว้เพื่ออัปโหลดเข้ากรมบัญชีกลาง

* ฟอร์มกรอกข้อมูลในระบบ และบันทึกข้อมูลไว้
* ปุ่ม "บันทึกข้อมูลเข้า template Excel" สร้างไฟล์ .xls จาก template ให้อัตโนมัติ
  (ชีต Input และชีต Interface สำหรับนำเข้าระบบ)
* แนบไฟล์เก็บไว้ในเอกสาร (ไฟล์ที่ระบบสร้างทุกครั้ง + ไฟล์อื่นที่แนบเพิ่ม)
* ใบเรียกเก็บที่เจ้าหนี้ส่งการเงินแล้ว กด "ขออนุมัติเบิกจ่าย" เพื่อสร้างใบขอเบิกเงิน
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "account",
        "purchase",
        "vpk_finance_flow",
        "vpk_payment_request",
        "vpk_gfmis",
    ],
    "external_dependencies": {"python": ["xlrd", "xlwt"]},
    "data": [
        "security/disbursement_form_security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/company_data.xml",
        "views/res_company_views.xml",
        "views/disbursement_form_views.xml",
        "views/account_move_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_hook",
}
