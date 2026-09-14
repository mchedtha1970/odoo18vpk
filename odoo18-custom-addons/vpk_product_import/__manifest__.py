{
    "name": "VPK Product Import",
    "version": "18.0.1.3.0",
    "category": "Inventory",
    "summary": "นำเข้า master สินค้าจาก Excel สำหรับ data migration",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "product",
        "stock",
        "purchase_stock",
        "product_expiry",
    ],
    "external_dependencies": {
        "python": ["openpyxl", "xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/product_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
