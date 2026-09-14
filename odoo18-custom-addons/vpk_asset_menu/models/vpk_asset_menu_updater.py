# -*- coding: utf-8 -*-
from odoo import api, models


class VpkAssetMenuUpdater(models.AbstractModel):
    _name = "vpk.asset.menu.updater"
    _description = "Update Asset Root Menu Labels"

    @api.model
    def update_labels(self):
        labels = {
            "account_asset_management.menu_finance_assets": "ระบบจัดการสินทรัพย์",
            "account_asset_management.menu_finance_config_assets": "การตั้งค่า",
            "account_asset_management.account_asset_report_menu": "รายงาน",
        }
        for xmlid, th_name in labels.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.with_context(lang="th_TH").write({"name": th_name})
                menu.with_context(lang="en_US").write({"name": th_name})
