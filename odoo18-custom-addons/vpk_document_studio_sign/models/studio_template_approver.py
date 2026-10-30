from odoo import api, fields, models


class DocumentStudioTemplateApprover(models.Model):
    _name = "vpk.document.studio.template.approver"
    _description = "ผู้อนุมัติเริ่มต้นของแบบฟอร์ม Document Studio"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับอนุมัติ", default=10)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        ondelete="restrict",
        domain=[("share", "=", False)],
    )
    position = fields.Char(string="ตำแหน่ง")
    is_check = fields.Boolean(string="ตรวจสอบ")
    is_sign = fields.Boolean(string="ลงนาม", default=True)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        Approval = self.env["vpk.approval.line"]
        if self.user_id:
            position = Approval._position_from_user(self.user_id)
            if position:
                self.position = position
            if Approval._is_director_secretary(self.user_id):
                self.is_check = True
                self.is_sign = False
            elif not self.is_check:
                self.is_sign = True

    @api.onchange("is_check")
    def _onchange_is_check(self):
        if self.is_check:
            self.is_sign = False

    @api.onchange("is_sign")
    def _onchange_is_sign(self):
        if self.is_sign:
            self.is_check = False
