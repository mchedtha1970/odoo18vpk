# -*- coding: utf-8 -*-
from odoo import api, fields, models


class VpkApprovalLine(models.Model):
    _name = "vpk.approval.line"
    _description = "ผู้อนุมัติเอกสาร"
    _order = "sequence, id"

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Many2oneReference(
        string="เอกสาร",
        index=True,
        model_field="res_model",
        required=True,
    )
    sequence = fields.Integer(string="ลำดับอนุมัติ", default=1)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        ondelete="restrict",
        domain=[("share", "=", False)],
    )
    position = fields.Char(string="ตำแหน่ง")
    is_check = fields.Boolean(string="ตรวจสอบ")
    is_sign = fields.Boolean(string="ลงนาม", default=True)

    @api.model
    def _position_from_user(self, user):
        employee = user.employee_id if "employee_id" in user._fields else False
        if employee and employee.job_id:
            return employee.job_id.name or ""
        return ""

    def _is_director_secretary(self, user):
        secretary = self.env.ref(
            "vpk_official_document.user_director_secretary",
            raise_if_not_found=False,
        )
        return bool(secretary and user == secretary)

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if self.user_id:
            position = self._position_from_user(self.user_id)
            if position:
                self.position = position
            if self._is_director_secretary(self.user_id):
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

    def _vpk_approval_role(self):
        self.ensure_one()
        if self.is_check and not self.is_sign:
            return "check"
        return "sign"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("res_model"):
                vals["res_model"] = self.env.context.get("default_res_model")
            if vals.get("user_id") and not vals.get("position"):
                user = self.env["res.users"].browse(vals["user_id"])
                position = self._position_from_user(user)
                if position:
                    vals["position"] = position
            if vals.get("is_check") and vals.get("is_sign"):
                vals["is_sign"] = False
            elif "is_check" not in vals and "is_sign" not in vals:
                user = self.env["res.users"].browse(vals.get("user_id"))
                if user and self._is_director_secretary(user):
                    vals["is_check"] = True
                    vals["is_sign"] = False
                else:
                    vals["is_sign"] = True
            if not vals.get("sequence") and vals.get("res_model") and vals.get("res_id"):
                siblings = self.search(
                    [
                        ("res_model", "=", vals["res_model"]),
                        ("res_id", "=", vals["res_id"]),
                    ]
                )
                vals["sequence"] = max(siblings.mapped("sequence") or [0]) + 1
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("user_id") and "position" not in vals:
            user = self.env["res.users"].browse(vals["user_id"])
            position = self._position_from_user(user)
            if position:
                vals = dict(vals, position=position)
        return super().write(vals)
