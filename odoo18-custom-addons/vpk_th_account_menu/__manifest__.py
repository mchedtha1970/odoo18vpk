# -*- coding: utf-8 -*-
{
    'name': 'VPK Thai Account Menu Labels',
    'version': '18.0.1.1.1',
    'category': 'Accounting/Localizations',
    'summary': 'Customize Thai menu labels for Accounting app',
    'description': """
        Override Thai translations for accounting sidebar menus:
        - Invoicing → ระบบบัญชี
        - Customers (section) → ระบบลูกหนี้
        - Vendors (section) → ระบบเจ้าหนี้
        - Accounting (entries section) → ระบบบัญชีแยกประเภท
    """,
    'author': 'VPK',
    'depends': ['account'],
    'data': [
        'data/menu_labels.xml',
        'views/res_partner_bank_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
