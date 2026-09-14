# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
# Community bridge: provides Enterprise module name `accountant` for Odoo 18 CE.

{
    "name": "Accountant (Community Bridge)",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Compatibility shim so Enterprise account_reports can install on Community",
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_accountant",
    ],
    "data": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
