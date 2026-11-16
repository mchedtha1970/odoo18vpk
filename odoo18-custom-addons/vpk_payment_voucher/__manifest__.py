# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    "name": "VPK ใบสำคัญจ่าย (กลุ่มงานการเงิน)",
    "version": "18.0.1.0.20",
    "category": "Accounting/Accounting",
    "summary": "ใบสำคัญจ่าย / บันทึกข้อความขออนุมัติเบิกจ่าย จากใบเรียกเก็บที่ POST แล้ว",
    "description": """
ใบสำคัญจ่าย — กลุ่มงานการเงิน
=============================
* สร้างจากใบเรียกเก็บ (Vendor Bill) ที่ POST แล้ว
* ฟอร์มบันทึกข้อความตามแบบราชการ (Garuda)
* พิมพ์เอกสารส่งขออนุมัติเบิกจ่าย
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "l10n_th_amount_to_text",
        "vpk_tier_validation",
        "vpk_payment_request",
        "vpk_finance_flow",
        "vpk_document_studio",
        "vpk_document_studio_procurement",
        "vpk_document_studio_sign",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/paperformat.xml",
        "data/document_type_data.xml",
        "wizard/create_voucher_wizard_views.xml",
        "views/payment_voucher_views.xml",
        "views/studio_document_views.xml",
        "views/account_move_views.xml",
        "views/menu.xml",
        "report/payment_voucher_report.xml",
        "report/payment_voucher_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_payment_voucher/static/src/dashboard/finance_dashboard_patch.js",
            "vpk_payment_voucher/static/src/dashboard/finance_dashboard_patch.xml",
        ],
    },
    "installable": True,
    "application": False,
}
