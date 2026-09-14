{
    "name": "VPK Vendor Evaluation - ประเมินผู้จำหน่าย",
    "version": "18.0.1.1.0",
    "category": "Purchase",
    "summary": "ประเมินผู้จำหน่าย ให้คะแนน จัดเกรดตามเกณฑ์ (ระยะเวลาจัดส่ง, คุณภาพ ฯลฯ)",
    "depends": ["purchase", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "data/evaluation_criteria_data.xml",
        "views/vendor_evaluation_views.xml",
        "views/vendor_evaluation_report_views.xml",
        "views/res_partner_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
