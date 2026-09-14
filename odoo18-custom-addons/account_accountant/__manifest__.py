# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
# Community stub of Enterprise account_accountant for account_reports.

{
    "name": "Accounting (Community Bridge)",
    "version": "18.0.1.1.1",
    "category": "Accounting/Accounting",
    "summary": "Minimal account_accountant APIs required by account_reports on Community",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/account_fiscal_year_views.xml",
        "wizard/account_change_lock_date_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_accountant/static/src/components/move_line_list/move_line_list.js",
        ],
    },
    "installable": True,
    "application": False,
}
