# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MaintenanceRequestCostLine(models.Model):
    _name = "maintenance.request.cost.line"
    _description = "สรุปค่าใช้จ่ายการซ่อม"
    _order = "sequence, id"

    request_id = fields.Many2one(
        comodel_name="maintenance.request",
        string="คำขอซ่อม",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    technician_id = fields.Many2one(
        comodel_name="res.users",
        string="ชื่อ - สกุล (ช่างผู้ปฏิบัติงาน)",
        related="request_id.user_id",
        store=True,
    )
    material_cost = fields.Monetary(string="ค่าวัสดุ (บาท)", currency_field="currency_id")
    labor_cost = fields.Monetary(string="ค่าแรง (บาท)", currency_field="currency_id")
    duration_minutes = fields.Integer(string="เวลาที่ใช้ (นาที)")
    total_amount = fields.Monetary(
        string="รวมเงินทั้งสิ้น (บาท)",
        currency_field="currency_id",
        compute="_compute_total_amount",
        store=True,
    )
    currency_id = fields.Many2one(
        related="request_id.company_currency_id",
        string="สกุลเงิน",
    )

    @api.depends("material_cost", "labor_cost")
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = (line.material_cost or 0.0) + (line.labor_cost or 0.0)
