# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    egp_purchase_name = fields.Text(
        string="ชื่อสำหรับซื้อใน e-GP",
        help="ชื่อสินค้าที่ใช้ตอนจัดซื้อในระบบ e-GP "
        "จะถูกดึงไปแสดงในรายการใบขอซื้อ (PR) และใบสั่งซื้อ (PO) เมื่อเลือกสินค้า",
        copy=True,
    )

    def action_open_uom_change_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Change Product UoM"),
            "res_model": "vpk.product.uom.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
            },
        }

    def write(self, vals):
        """Allow base UoM change when wizard sets context flag.

        Stock's write() blocks uom_id if any stock.move exists. The wizard
        converts related quantities first, then writes with this flag.
        """
        if self.env.context.get("vpk_allow_uom_change") and "uom_id" in vals:
            uom_id = vals.pop("uom_id")
            res = True
            if vals:
                res = super().write(vals)
            if self.ids:
                self.env.cr.execute(
                    "UPDATE product_template SET uom_id = %s WHERE id IN %s",
                    (uom_id, tuple(self.ids)),
                )
                self.invalidate_recordset(["uom_id", "uom_name", "uom_category_id"])
            return res
        return super().write(vals)
