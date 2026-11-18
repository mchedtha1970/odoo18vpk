# -*- coding: utf-8 -*-
# VPK customized fork companion for account_reports (technical name unchanged).
{
    'name': 'VPK Cash Basis Accounting Reports',
    'summary': 'VPK cash basis functionality for accounting reports',
    'category': 'Accounting/Accounting',
    'version': '18.0.1.0.2',
    'author': 'VPK',
    'description': """
VPK Cash Basis Accounting Reports
=================================
Customized fork maintained for VPK ERP.
Technical module name remains ``account_reports_cash_basis``.
    """,
    'depends': ['account_reports'],
    'data': [
        'data/account_reports_data.xml',
        'views/account_report_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_reports_cash_basis/static/src/components/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
