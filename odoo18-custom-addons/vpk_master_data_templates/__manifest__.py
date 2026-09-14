{
    "name": "VPK Master Data Templates",
    "version": "18.0.1.6.0",
    "category": "Hidden",
    "summary": "Excel templates สำหรับเตรียม master data / ยกยอด (คลัง, สินค้า, UoM, สินทรัพย์, Analytic, Equipment, Vendor, PR, PO, ผังบัญชี, เจ้าหนี้, การเงิน, สมุดเช็ค, บัญชี)",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "stock",
        "product",
        "uom",
        "account",
        "analytic",
        "maintenance",
        "purchase",
    ],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/master_data_template_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
