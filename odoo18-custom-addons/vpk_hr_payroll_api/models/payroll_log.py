# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class VpkHrPayrollApiLog(models.Model):
    _name = "vpk.hr.payroll.api.log"
    _description = "บันทึก API เงินเดือน HR"
    _order = "id desc"

    endpoint = fields.Char()
    http_method = fields.Char()
    remote_addr = fields.Char()
    external_id = fields.Char(index=True)
    source_system = fields.Char()
    state = fields.Selection(
        [("pending", "รอ"), ("success", "สำเร็จ"), ("error", "ผิดพลาด")],
        default="pending",
        required=True,
    )
    http_status = fields.Integer()
    error_message = fields.Text()
    request_body = fields.Text()
    response_body = fields.Text()
    batch_id = fields.Many2one("vpk.hr.payroll.batch", ondelete="set null")
