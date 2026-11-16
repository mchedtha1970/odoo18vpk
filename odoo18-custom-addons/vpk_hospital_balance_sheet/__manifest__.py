# -*- coding: utf-8 -*-
{
    "name": "งบแสดงฐานะการเงิน โรงพยาบาลวชิระภูเก็ต",
    "version": "18.0.1.3.1",
    "category": "Accounting/Localizations",
    "summary": "เทมเพลตงบการเงินของฝ่ายบัญชีตามไฟล์งบการเงิน",
    "description": """
เทมเพลตงบแสดงฐานะการเงิน งบกระแสเงินสด
งบแสดงผลการดำเนินงานทางการเงิน หมายเหตุประกอบงบการเงิน
เงินฝากธนาคารจัดกลุ่มตามรหัสบัญชี
และรายงานเงินฝากธนาคารตามเลขที่บัญชีธนาคาร
รูปแบบตามไฟล์งบการเงิน และผูกเฉพาะรหัสบัญชีที่มีในไฟล์

รวม Dashboard ผลการดำเนินงาน: เทียบปี / รายเดือน / แยกหน่วยงาน
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["account_reports", "analytic", "vpk_bank_subledger"],
    "data": [
        "data/balance_sheet.xml",
        "data/cash_flow.xml",
        "data/profit_and_loss.xml",
        "data/financial_notes.xml",
        "data/cash_equivalent.xml",
        "data/bank_by_number.xml",
        "views/pl_performance_dashboard.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_hospital_balance_sheet/static/src/bank_number_header.xml",
            "vpk_hospital_balance_sheet/static/src/scss/pl_performance_dashboard.scss",
            "vpk_hospital_balance_sheet/static/src/dashboard/pl_chart.js",
            "vpk_hospital_balance_sheet/static/src/dashboard/pl_chart.xml",
            "vpk_hospital_balance_sheet/static/src/dashboard/pl_performance_dashboard.js",
            "vpk_hospital_balance_sheet/static/src/dashboard/pl_performance_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
}
