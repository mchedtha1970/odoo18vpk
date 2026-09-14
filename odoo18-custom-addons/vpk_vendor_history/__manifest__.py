{
    "name": "VPK Vendor History - ประวัติซื้อขายและสินค้ามีปัญหา",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "เก็บประวัติการซื้อขาย และรายละเอียดสินค้าที่มีปัญหาของเจ้าหนี้แต่ละราย",
    "depends": ["purchase", "account", "stock", "vpk_purchase_agreement_egp"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/vendor_trade_category_data.xml",
        "views/vendor_product_issue_views.xml",
        "views/purchase_order_line_views.xml",
        "views/res_partner_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
