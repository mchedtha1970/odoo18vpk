{
    "name": "VPK Purchase MOQ - สั่งซื้อขั้นต่ำ",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "รองรับการบันทึกและตรวจสอบจำนวนสั่งซื้อขั้นต่ำ (MOQ) ตามผู้จำหน่าย",
    "depends": ["purchase", "product"],
    "data": [
        "views/product_supplierinfo_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
