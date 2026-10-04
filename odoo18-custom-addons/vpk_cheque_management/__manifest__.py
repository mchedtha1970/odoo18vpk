# -*- coding: utf-8 -*-
{
    "name": "VPK Cheque Management",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "สมุดเช็ค แบบฟอร์มเช็ค และพิมพ์เช็คจากใบเรียกเก็บหรือรายการจ่าย",
    "author": "VPK",
    "depends": [
        "account",
        "l10n_th_amount_to_text",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/cheque_attribute_data.xml",
        "report/cheque_report.xml",
        "views/cheque_layout_templates.xml",
        "wizard/print_bank_cheque_views.xml",
        "views/bank_cheque_views.xml",
        "views/account_move_views.xml",
        "views/menu_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
