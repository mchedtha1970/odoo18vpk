# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import fields, models


class DisbursementFormFile(models.Model):
    _name = "vpk.disbursement.form.file"
    _description = "ไฟล์แนบใบขอเบิกเงิน"
    _order = "form_id, sequence, id"

    form_id = fields.Many2one(
        "vpk.disbursement.form",
        string="ใบขอเบิกเงิน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    kind = fields.Selection(
        [
            ("generated", "ไฟล์ที่ระบบสร้างจาก template"),
            ("uploaded", "ไฟล์ที่แนบเพิ่ม"),
        ],
        string="ประเภท",
        default="uploaded",
        required=True,
    )
    version = fields.Integer(string="ครั้งที่", readonly=True)
    name = fields.Char(string="รายละเอียด")
    file = fields.Binary(string="ไฟล์", attachment=True, required=True)
    filename = fields.Char(string="ชื่อไฟล์")
    created_by = fields.Many2one(
        "res.users", string="แนบโดย", default=lambda self: self.env.user, readonly=True
    )
    created_on = fields.Datetime(
        string="แนบเมื่อ", default=fields.Datetime.now, readonly=True
    )
    note = fields.Char(string="หมายเหตุ")

    def action_download(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/file/%s?download=true"
            % (self._name, self.id, self.filename or "file"),
            "target": "self",
        }
