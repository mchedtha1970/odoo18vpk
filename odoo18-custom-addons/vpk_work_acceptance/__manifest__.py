# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Work Acceptance",
    "version": "18.0.1.3.5",
    "category": "Purchases",
    "summary": "ระบบบันทึกการรับมอบงาน เชื่อมกับสัญญาและคณะกรรมการตรวจรับ",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase_work_acceptance",
        "vpk_purchase_contract",
        "vpk_stock_qc",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/wa_sequence.xml",
        "data/mail_template_data.xml",
        "views/work_acceptance_views.xml",
        "views/purchase_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_work_acceptance/static/src/scss/work_acceptance_dashboard.scss",
            "vpk_work_acceptance/static/src/dashboard/work_acceptance_dashboard.js",
            "vpk_work_acceptance/static/src/dashboard/work_acceptance_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
}
