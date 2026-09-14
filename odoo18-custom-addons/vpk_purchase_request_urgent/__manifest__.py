{
    "name": "VPK Purchase Request Urgent - ขอซื้อฉุกเฉิน/เร่งด่วน",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "รองรับใบขอซื้อฉุกเฉินและเร่งด่วน พร้อมเหตุผลและเส้นทางอนุมัติเร่งด่วน",
    "depends": [
        "purchase_request",
        "vpk_budget",
        "vpk_purchase_contract",
    ],
    "data": [
        "views/purchase_request_urgent_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
