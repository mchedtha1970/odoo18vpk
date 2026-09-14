# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Work Acceptance",
    "version": "18.0.1.1.0",
    "category": "Purchases",
    "summary": "ระบบบันทึกการรับมอบงาน เชื่อมกับสัญญาและคณะกรรมการตรวจรับ",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase_work_acceptance",
        "vpk_purchase_contract",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/wa_sequence.xml",
        "data/mail_template_data.xml",
        "views/work_acceptance_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
