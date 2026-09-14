from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class VendorEvaluationCriteria(models.Model):
    _name = "vendor.evaluation.criteria"
    _description = "เกณฑ์ประเมินผู้จำหน่าย"
    _order = "sequence, id"

    name = fields.Char(string="เกณฑ์ประเมิน", required=True)
    code = fields.Char(string="รหัส", required=True)
    sequence = fields.Integer(default=10)
    weight = fields.Float(
        string="น้ำหนัก (%)",
        required=True,
        default=20.0,
        help="น้ำหนักของเกณฑ์นี้ในการคำนวณคะแนนรวม (ผลรวมทุกเกณฑ์ = 100%)",
    )
    max_score = fields.Float(
        string="คะแนนเต็ม",
        required=True,
        default=5.0,
    )
    description = fields.Text(string="คำอธิบาย")
    active = fields.Boolean(default=True)

    @api.constrains("weight")
    def _check_weight(self):
        for rec in self:
            if rec.weight < 0 or rec.weight > 100:
                raise ValidationError(
                    _("น้ำหนักต้องอยู่ระหว่าง 0 - 100%%")
                )

    @api.constrains("max_score")
    def _check_max_score(self):
        for rec in self:
            if rec.max_score <= 0:
                raise ValidationError(
                    _("คะแนนเต็มต้องมากกว่า 0")
                )
