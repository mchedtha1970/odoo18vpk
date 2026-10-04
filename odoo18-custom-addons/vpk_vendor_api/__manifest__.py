# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "VPK Vendor Mobile API",
    "version": "18.0.1.0.5",
    "category": "Purchases",
    "summary": "REST API ให้แอปผู้ขายดูใบสั่งซื้อที่ส่งแล้ว เปิด PDF และลงนามยืนยัน",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "vpk_purchase_portal_egp",
        "vpk_purchase_order_form",
    ],
    "data": [
        "security/vendor_trade_document_access.xml",
        "views/vendor_trade_document_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_vendor_api/static/src/js/trade_pdf_button.js",
            "vpk_vendor_api/static/src/xml/trade_pdf_button.xml",
        ],
    },
    "installable": True,
    "application": False,
}
