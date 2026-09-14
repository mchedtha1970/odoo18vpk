# -*- coding: utf-8 -*-
from odoo import api, models

MENU_LABELS = {
    "purchase.menu_purchase_root": "ระบบจัดซื้อจัดจ้าง",
    "purchase.menu_procurement_management": "จัดการสั่งซื้อ",
    "vpk_th_purchase_menu.menu_purchase_request_data_root": "ข้อมูลใบขอซื้อ",
    "purchase_request.menu_purchase_request_pro_mgt": "ใบขอซื้อ",
    "purchase_request.menu_purchase_request_line": "รายการใบขอซื้อ",
    "purchase.menu_purchase_products": "ข้อมูลสินค้า",
    "vpk_th_purchase_menu.menu_vendor_data_root": "ข้อมูลผู้จำหน่าย",
    "purchase.menu_procurement_management_supplier_name": "ผู้จำหน่าย",
}


class VpkThPurchaseMenuUpdater(models.AbstractModel):
    _name = "vpk.th.purchase.menu.updater"
    _description = "Update Thai Purchase Menu Labels"

    @api.model
    def update_labels(self):
        langs = {"en_US"}
        langs.update(
            code
            for code, _name in self.env["res.lang"].get_installed()
            if code == "en_US" or code.startswith("th")
        )
        for xmlid, th_name in MENU_LABELS.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            for lang in sorted(langs):
                menu.with_context(lang=lang).write({"name": th_name})
