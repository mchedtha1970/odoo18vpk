{
    "name": "VPK Purchase Request Tracking - ติดตามสถานะและรายงานขอซื้อ/สั่งซื้อ",
    "version": "18.0.1.2.0",
    "category": "Purchases",
    "summary": "ติดตาม PR ที่ออก/ยังไม่ออกใบสั่งซื้อ และ Export รายงานประจำวัน สัปดาห์ เดือน ปี",
    "depends": [
        "purchase",
        "purchase_request",
        "l10n_th_gov_purchase_request",
        "l10n_th_base_sequence",
        "sequence_reset_period",
    ],
    "external_dependencies": {"python": ["xlsxwriter"]},
    "data": [
        "security/ir.model.access.csv",
        "data/purchase_request_sequence.xml",
        "views/purchase_request_tracking_views.xml",
        "views/purchase_order_tracking_views.xml",
        "wizard/pr_po_report_export_wizard_views.xml",
        "views/menu_views.xml",
        "views/procurement_dashboard.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_purchase_request_tracking/static/src/scss/procurement_dashboard.scss",
            "vpk_purchase_request_tracking/static/src/dashboard/procurement_dashboard.js",
            "vpk_purchase_request_tracking/static/src/dashboard/procurement_dashboard.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
