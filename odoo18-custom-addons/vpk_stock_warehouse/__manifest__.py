{
    "name": "VPK Stock Warehouse Overview",
    "version": "18.0.1.1.0",
    "category": "Inventory",
    "summary": "Warehouse and bin/location explorer with panel navigation",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "views/stock_location_overview_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "vpk_stock_warehouse/static/src/scss/warehouse_overview.scss",
            "vpk_stock_warehouse/static/src/dashboard/warehouse_overview.js",
            "vpk_stock_warehouse/static/src/dashboard/warehouse_overview.xml",
        ],
    },
    "installable": True,
    "application": False,
}
