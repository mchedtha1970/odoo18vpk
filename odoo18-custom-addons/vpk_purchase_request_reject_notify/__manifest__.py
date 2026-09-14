{
    "name": "VPK Purchase Request Reject Notify - แจ้งเตือนเมื่อ PR ไม่ผ่านอนุมัติ",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "แจ้งเตือนผู้ขอและกลุ่มงานเมื่อใบขอซื้อ/จ้าง/เช่าไม่ได้รับการอนุมัติ",
    "depends": [
        "purchase_request",
        "purchase_request_department",
        "purchase_request_tier_validation",
        "mail",
        "hr",
    ],
    "data": [
        "data/mail_template_data.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
