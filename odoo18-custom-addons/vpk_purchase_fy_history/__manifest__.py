{
    "name": "VPK Purchase FY History - ราคา/ปริมาณที่เคยซื้อในปีงบประมาณ",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "summary": "ตรวจสอบราคาและปริมาณที่เคยซื้อในปีงบประมาณ บน PR/PO และสินค้า",
    "depends": [
        "purchase",
        "purchase_request",
        "vpk_vendor_history",
    ],
    "data": [
        "views/purchase_order_line_views.xml",
        "views/purchase_request_line_views.xml",
        "views/product_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
