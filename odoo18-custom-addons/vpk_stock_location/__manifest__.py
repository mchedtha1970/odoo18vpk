{
    "name": "VPK Stock Location Management",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Hierarchical Location + Narcotic Access Control + Auto Requisition",
    "depends": ["stock"],
    "data": [
        "security/stock_location_security.xml",
        "security/ir.model.access.csv",
        "data/stock_cron.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
