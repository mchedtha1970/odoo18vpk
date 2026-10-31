# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


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

