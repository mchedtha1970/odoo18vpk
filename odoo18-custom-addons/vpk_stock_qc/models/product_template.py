# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    cold_chain = fields.Boolean(
        string="Cold Chain",
        help="ยาที่ต้องบันทึกอุณหภูมิรถขนส่งตอนรับ หากอยู่นอกเกณฑ์ รับเข้าคลังไม่ได้",
    )
    show_cold_chain = fields.Boolean(compute="_compute_show_cold_chain")

    @api.depends("hospital_item_type", "categ_id", "categ_id.complete_name")
    def _compute_show_cold_chain(self):
        for product in self:
            category_name = product.categ_id.complete_name or ""
            product.show_cold_chain = (
                product.hospital_item_type == "medicine"
                or "เวชภัณฑ์ ยา" in category_name
            )

    @api.onchange("cold_chain")
    def _onchange_cold_chain_storage_method(self):
        if "storage_method" not in self._fields:
            return
        if self.cold_chain:
            self.storage_method = "cold"
        elif self.storage_method == "cold":
            self.storage_method = "room"


class ProductProduct(models.Model):
    _inherit = "product.product"

    cold_chain = fields.Boolean(
        related="product_tmpl_id.cold_chain",
        string="Cold Chain",
        store=True,
    )
