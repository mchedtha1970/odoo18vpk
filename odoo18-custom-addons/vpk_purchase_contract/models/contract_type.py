# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseContractCategory(models.Model):
    _name = "purchase.contract.category"
    _description = "หมวดสัญญา (Master list)"
    _order = "name"

    name = fields.Char(string="ชื่อหมวดสัญญา", required=True, index=True)
    code = fields.Char(string="รหัส", help="รหัสสั้นสำหรับอ้างอิง", index=True)
    description = fields.Text(string="คำอธิบาย")
    active = fields.Boolean(string="ใช้งาน", default=True)
    type_ids = fields.One2many(
        comodel_name="purchase.contract.type",
        inverse_name="category_id",
        string="ประเภทสัญญา",
    )


class PurchaseContractType(models.Model):
    _name = "purchase.contract.type"
    _description = "ประเภทสัญญา (Master list)"
    _order = "name"

    name = fields.Char(string="ชื่อประเภทสัญญา", required=True, index=True)
    code = fields.Char(string="รหัส", help="รหัสสั้นสำหรับอ้างอิง", index=True)
    description = fields.Text(string="คำอธิบาย")
    active = fields.Boolean(string="ใช้งาน", default=True)
    category_id = fields.Many2one(
        comodel_name="purchase.contract.category",
        string="หมวดสัญญา",
        index=True,
        ondelete="restrict",
        help="หมวดสัญญาที่เลือกจากตาราง master",
    )
    quantity_policy = fields.Selection(
        selection=[
            ("fixed", "กำหนดจำนวน"),
            ("unlimited", "จะซื้อจะขายไม่จำกัดจำนวน"),
        ],
        string="ลักษณะปริมาณ",
        default="fixed",
        required=True,
        help="ไม่จำกัดจำนวน: ราคาต่อหน่วยคงที่ เมื่อต้องการสินค้าให้เปิดใบขอซื้อแล้วใส่จำนวนเอง",
    )

    @api.model
    def _vals_for_unlimited_name(self, vals):
        name = vals.get("name") or ""
        if "ไม่จำกัดจำนวน" in name:
            vals["quantity_policy"] = "unlimited"
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared = [self._vals_for_unlimited_name(dict(vals)) for vals in vals_list]
        return super().create(prepared)

    def write(self, vals):
        vals = self._vals_for_unlimited_name(dict(vals))
        return super().write(vals)

