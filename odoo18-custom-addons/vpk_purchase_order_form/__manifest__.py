{
    "name": "VPK Purchase Order Form (ใบสั่งซื้อ/สั่งจ้าง)",
    "version": "18.0.1.0.4",
    "category": "Purchases",
    "summary": "QWeb ใบสั่งซื้อ/สั่งจ้าง ตามแบบใบ_PO_VPK",
    "description": """
พิมพ์ใบสั่งซื้อ/สั่งจ้าง ตามรูปแบบเอกสารราชการโรงพยาบาลวชิระภูเก็ต
(ต้นแบบ docs/ใบ_PO_VPK.png)
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        "purchase_request",
        "vpk_official_document",
        "l10n_th_base_utils",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "data/report_paperformat.xml",
        "report/purchase_order_form_report.xml",
        "report/purchase_order_form_templates.xml",
        "views/purchase_order_views.xml",
        "views/purchase_request_views.xml",
        "views/res_company_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "vpk_purchase_order_form/static/src/css/po_form_layout.css",
        ],
    },
    "installable": True,
    "application": False,
}
