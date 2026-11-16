# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "VPK ขออนุมัติเบิกจ่าย (จัดซื้อ → เจ้าหนี้)",
    "version": "18.0.1.6.19",
    "category": "Purchases",
    "summary": "ขออนุมัติเบิกจ่ายจากใบสั่งซื้อหลังตรวจรับ ลงนามภายใน แล้วส่งต่อเจ้าหนี้ตั้งหนี้",
    "description": """
ขออนุมัติเบิกจ่าย
=================
* ใบสั่งซื้อขออนุมัติเบิกจ่ายได้หลังตรวจรับมอบงานเสร็จแล้ว (ใบตรวจรับยืนยันตรวจรับ)
* สร้างเอกสารขออนุมัติเบิกจ่ายจากแบบฟอร์ม Document Studio หรือแนบไฟล์
  ส่งลงนามตามลำดับผู้อนุมัติภายใน
* เมื่อลงนามครบ จัดซื้อกด "ส่งหน่วยงานเจ้าหนี้"
* Dashboard งานเจ้าหนี้: ดึงรายการไปสร้างใบเรียกเก็บ (ฉบับร่าง) → อนุมัติ/POST
  → กด "ส่งการเงิน"
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "purchase",
        "mail",
        "vpk_work_acceptance",
        "vpk_document_studio_procurement",
        "vpk_gfmis",
        "vpk_finance_flow",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/payment_request_data.xml",
        "data/payment_method_data.xml",
        "wizard/payment_request_wizard_views.xml",
        "views/studio_document_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
        "views/gfmis_document_views.xml",
        "views/account_payment_register_views.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_backend": [
            "vpk_payment_request/static/src/scss/ap_dashboard.scss",
            "vpk_payment_request/static/src/dashboard/ap_dashboard.js",
            "vpk_payment_request/static/src/dashboard/ap_dashboard.xml",
            "vpk_payment_request/static/src/dashboard/finance_dashboard.js",
            "vpk_payment_request/static/src/dashboard/finance_dashboard.xml",
            "vpk_payment_request/static/src/dashboard/accounting_dashboard.js",
            "vpk_payment_request/static/src/dashboard/accounting_dashboard.xml",
            "vpk_payment_request/static/src/dashboard/bill_approval_dashboard.js",
            "vpk_payment_request/static/src/dashboard/bill_approval_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
}
