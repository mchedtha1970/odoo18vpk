# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Purchase Contract",
    "version": "18.0.1.1.0",
    "category": "Purchases",
    "summary": "ทะเบียนสัญญาหลัก ผูกสัญญาบน PR/PO ตรวจยอดคงเหลือแบบ Hard Block และตัดลดเรียลไทม์",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "purchase_request",
        "account",
        "vpk_budget",
        "vpk_purchase_agreement_egp",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/purchase_contract_security.xml",
        "data/ir_sequence_data.xml",
        "wizard/generate_installments_wizard_views.xml",
        "views/purchase_contract_views.xml",
        "views/purchase_request_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
        "views/purchase_requisition_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}
