# -*- coding: utf-8 -*-
{
    "name": "VPK Asset to Equipment",
    "version": "18.0.1.5.0",
    "category": "Accounting",
    "summary": "สร้าง Equipment ใน Maintenance จากบัตรสินทรัพย์คงที่",
    "author": "VPK",
    "depends": [
        "account_asset_management",
        "account_asset_number",
        "maintenance",
    ],
    "data": [
        "views/account_asset_views.xml",
        "views/maintenance_equipment_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
