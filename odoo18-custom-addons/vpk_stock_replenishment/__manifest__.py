{
    "name": "VPK Stock Replenishment",
    "version": "18.0.1.1.3",
    "category": "Inventory",
    "summary": "เติมสต็อกคลังหน่วยงานจากคลังใหญ่ก่อน ไม่พอค่อยเปิด PR",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "purchase_stock",
        "purchase_request",
    ],
    "data": [
        "views/stock_warehouse_views.xml",
    ],
    "installable": True,
    "application": False,
}
