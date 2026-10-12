# -*- coding: utf-8 -*-
from odoo import fields, models


class MaintenanceRequestMaterialLine(models.Model):
    _name = "maintenance.request.material.line"
    _description = "วัสดุที่ใช้ในการซ่อม"
    _order = "sequence, id"

    request_id = fields.Many2one(
        comodel_name="maintenance.request",
        string="คำขอซ่อม",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="รายการ", required=True)
    quantity = fields.Float(string="จำนวน", digits="Product Unit of Measure")
    amount = fields.Monetary(string="เป็นเงิน", currency_field="currency_id")
    currency_id = fields.Many2one(
        related="request_id.company_currency_id",
        string="สกุลเงิน",
    )
