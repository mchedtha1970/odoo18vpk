{
    "name": "VPK Committee Appointment - แต่งตั้งคณะกรรมการซื้อจ้าง",
    "version": "18.0.1.1.3",
    "category": "Purchases",
    "summary": "เอกสารขออนุมัติแต่งตั้งคณะกรรมการกำหนดราคากลาง / จัดซื้อจัดจ้าง / ตรวจรับ + อีเมลแจ้งเมื่ออนุมัติ",
    "depends": [
        "purchase_request",
        "l10n_th_gov_purchase_request",
        "mail",
        "hr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/mail_template_data.xml",
        "views/committee_appointment_views.xml",
        "views/purchase_request_views.xml",
        "views/menu_views.xml",
        "report/committee_appointment_report.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
