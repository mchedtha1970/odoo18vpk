# -*- coding: utf-8 -*-
from odoo import fields, models


class MaintenanceAssessmentResult(models.Model):
    _name = "maintenance.assessment.result"
    _description = "ผลการประเมินคำขอซ่อม"
    _order = "sequence, id"

    name = fields.Char(string="ผลการประเมิน", required=True, translate=True)
    code = fields.Char(string="รหัส", required=True, copy=False)
    sequence = fields.Integer(string="ลำดับ", default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string="หมายเหตุ")

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "รหัสผลการประเมินต้องไม่ซ้ำ",
        ),
    ]
