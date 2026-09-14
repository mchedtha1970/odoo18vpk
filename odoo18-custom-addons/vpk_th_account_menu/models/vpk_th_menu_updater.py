# -*- coding: utf-8 -*-
from odoo import api, models


class VpkThMenuUpdater(models.AbstractModel):
    _name = 'vpk.th.menu.updater'
    _description = 'Update Thai Account Menu Labels'

    @api.model
    def update_labels(self):
        labels = {
            'account.menu_finance': 'ระบบบัญชี',
            'account.menu_finance_receivables': 'ระบบลูกหนี้',
            'account.menu_finance_payables': 'ระบบเจ้าหนี้',
            'account.menu_finance_entries': 'ระบบบัญชีแยกประเภท',
        }
        for xmlid, th_name in labels.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.with_context(lang='th_TH').write({'name': th_name})
