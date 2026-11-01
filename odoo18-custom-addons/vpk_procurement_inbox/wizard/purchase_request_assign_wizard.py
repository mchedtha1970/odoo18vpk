# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestAssignWizard(models.TransientModel):
    _name = "purchase.request.assign.wizard"
    _description = "มอบหมายงานพัสดุ"

    request_ids = fields.Many2many(
        "purchase.request",
        string="ใบขอซื้อ",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="เจ้าหน้าที่พัสดุผู้รับงาน",
        required=True,
        domain=lambda self: self.env["purchase.request"]._procurement_assignee_domain(),
    )
    note = fields.Text(
        string="หมายเหตุถึงผู้รับงาน",
        help="ข้อความนี้จะแจ้งไปยังเจ้าหน้าที่ที่ได้รับมอบหมาย",
    )
    request_count = fields.Integer(compute="_compute_request_count")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids") or []
        active_id = self.env.context.get("active_id")
        if not active_ids and active_id:
            active_ids = [active_id]
        if "request_ids" in fields_list and active_ids and not res.get("request_ids"):
            res["request_ids"] = [(6, 0, active_ids)]
        return res

    @api.depends("request_ids")
    def _compute_request_count(self):
        for rec in self:
            rec.request_count = len(rec.request_ids)

    def action_confirm_assign(self):
        self.ensure_one()
        if not self.request_ids:
            raise UserError(_("ไม่พบใบขอซื้อที่ต้องการมอบหมาย"))
        if not self.user_id:
            raise UserError(_("กรุณาเลือกเจ้าหน้าที่พัสดุผู้รับงาน"))
        self.request_ids.action_assign_procurement(
            self.user_id, note=(self.note or "").strip() or False
        )
        return {"type": "ir.actions.act_window_close"}
