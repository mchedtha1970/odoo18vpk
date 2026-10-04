{
    "name": "VPK Vendor Loan - ยืมของจากผู้ขาย",
    "version": "18.0.1.2.0",
    "category": "Inventory/Purchase",
    "summary": "รับของยืมด่วนจากผู้ขาย แล้วเปิดขอซื้อ e-GP ตามปกติ และหักล้างตอนยืนยันใบรับ",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "purchase_request",
        "vpk_stock_warehouse",
        "vpk_stock_qc",
        "vpk_purchase_request_urgent",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/vendor_loan_data.xml",
        "views/vendor_loan_views.xml",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "application": False,
}
