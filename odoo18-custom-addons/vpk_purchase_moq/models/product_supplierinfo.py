from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    moq_qty = fields.Float(
        string="จำนวนสั่งซื้อขั้นต่ำ (MOQ)",
        digits="Product Unit of Measure",
        help="จำนวนขั้นต่ำที่ผู้จำหน่ายรับสั่งซื้อต่อครั้ง "
             "(Minimum Order Quantity)",
    )
    moq_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วยนับ MOQ",
        help="หน่วยนับสำหรับจำนวนสั่งซื้อขั้นต่ำ "
             "(ถ้าไม่ระบุจะใช้หน่วยนับเดียวกับสินค้า)",
    )
    order_multiple = fields.Float(
        string="จำนวนทวีคูณ (Order Multiple)",
        digits="Product Unit of Measure",
        help="จำนวนที่ต้องสั่งเป็นทวีคูณ เช่น ทวีคูณ 100 "
             "ต้องสั่ง 100, 200, 300 ...",
    )

    @api.constrains("moq_qty")
    def _check_moq_qty(self):
        for rec in self:
            if rec.moq_qty < 0:
                raise ValidationError(
                    _("จำนวนสั่งซื้อขั้นต่ำ (MOQ) ต้องไม่ติดลบ")
                )

    @api.constrains("order_multiple")
    def _check_order_multiple(self):
        for rec in self:
            if rec.order_multiple < 0:
                raise ValidationError(
                    _("จำนวนทวีคูณ (Order Multiple) ต้องไม่ติดลบ")
                )
