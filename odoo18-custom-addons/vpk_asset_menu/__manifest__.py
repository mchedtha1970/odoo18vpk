# -*- coding: utf-8 -*-
{
    "name": "VPK Asset Menu",
    "version": "18.0.1.1.0",
    "category": "Accounting/Localizations",
    "summary": "แยกเมนูสินทรัพย์เป็น Root และรองรับพิมพ์ป้ายภาษาไทย",
    "author": "VPK",
    "depends": [
        "account_asset_management",
        "account_asset_number",
        "l10n_th_base_utils",
    ],
    "data": [
        "views/menuitem.xml",
        "data/menu_labels.xml",
        "report/account_asset_number_report.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
