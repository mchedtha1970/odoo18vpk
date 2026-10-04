{
    "name": "VPK Stock Location Management",
    "version": "18.0.1.1.1",
    "category": "Inventory/Inventory",
    "summary": "Hierarchical Location + Narcotic Access Control + Auto Requisition",
    "depends": ["stock"],
    "data": [
        "security/stock_location_security.xml",
        "security/ir.model.access.csv",
        "data/stock_cron.xml",
        "views/stock_quant_views.xml",
        "wizard/count_sheet_import_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
