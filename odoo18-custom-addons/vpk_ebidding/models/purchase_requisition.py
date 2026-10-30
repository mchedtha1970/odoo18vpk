# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    ebidding_plan_line_id = fields.Many2one(
        comodel_name="ebidding.plan.line",
        string="รายการแผนจาก e-GP",
        copy=False,
        index=True,
        ondelete="set null",
        help="รายการแผนจัดซื้อจัดจ้างที่ใช้สร้างกระบวนการ e-GP นี้",
    )
    ebidding_plan_code = fields.Char(
        related="ebidding_plan_line_id.plan_code",
        string="รหัสแผน",
        readonly=True,
    )
    ebidding_fiscal_year = fields.Char(
        related="ebidding_plan_line_id.fiscal_year",
        string="ปีงบประมาณ",
        readonly=True,
    )
    ebidding_plan_name = fields.Char(
        related="ebidding_plan_line_id.project_name",
        string="ชื่อแผน",
        readonly=True,
    )

    is_ebidding_method = fields.Boolean(
        compute="_compute_is_ebidding_method",
    )

    ebidding_plan_count = fields.Integer(
        compute="_compute_ebidding_plan_count",
    )

    @api.depends("ebidding_plan_line_id")
    def _compute_ebidding_plan_count(self):
        for record in self:
            record.ebidding_plan_count = 1 if record.ebidding_plan_line_id else 0

    @api.depends("procurement_method_id", "procurement_method_id.name")
    def _compute_is_ebidding_method(self):
        bidding = self.env.ref(
            "l10n_th_gov_purchase_request.procurement_bidding",
            raise_if_not_found=False,
        )
        for record in self:
            method = record.procurement_method_id
            record.is_ebidding_method = bool(method) and (
                method == bidding
                or "bidding" in (method.name or "").lower()
            )

    def _ebidding_plan_for_fiscal_year(self):
        self.ensure_one()
        Plan = self.env["ebidding.plan"]
        fiscal_year = Plan._default_fiscal_year()
        plan = Plan.search(
            [
                ("company_id", "=", self.company_id.id),
                ("fiscal_year", "=", fiscal_year),
            ],
            limit=1,
        )
        if not plan:
            plan = Plan.create(
                {"company_id": self.company_id.id, "fiscal_year": fiscal_year}
            )
        return plan

    def action_create_ebidding_plan(self):
        self.ensure_one()
        if self.ebidding_plan_line_id:
            return self.action_open_ebidding_plan_line()
        if not self.is_ebidding_method:
            raise UserError(_("สร้างแผนได้เฉพาะวิธีจัดซื้อจัดจ้าง E-bidding"))
        plan = self._ebidding_plan_for_fiscal_year()
        last_line = self.env["ebidding.plan.line"].search(
            [("company_id", "=", self.company_id.id), ("office_code", "!=", False)],
            order="id desc",
            limit=1,
        )
        today = fields.Date.context_today(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("สร้างแผนจัดซื้อจัดจ้าง (e-bidding)"),
            "res_model": "ebidding.plan.line",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "ebidding_link_requisition_id": self.id,
                "default_plan_id": plan.id,
                "default_project_name": self.egp_project_name
                or self.purchase_request_id.description
                or False,
                "default_extra_budget_amount": self.purchase_request_amount_total,
                "default_office_code": last_line.office_code or False,
                "default_expected_announce_month": fields.Date.to_string(
                    today.replace(day=1)
                ),
            },
        }

    def action_open_ebidding_plan_line(self):
        self.ensure_one()
        if not self.ebidding_plan_line_id:
            raise UserError(_("ยังไม่ได้เชื่อมเอกสารแผน"))
        return {
            "type": "ir.actions.act_window",
            "name": self.ebidding_plan_line_id.display_name,
            "res_model": "ebidding.plan.line",
            "res_id": self.ebidding_plan_line_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def _is_egp_ebidding_method(self):
        self.ensure_one()
        method = self.procurement_method_id
        if not method:
            return bool(self.ebidding_plan_line_id)
        bidding = self.env.ref(
            "l10n_th_gov_purchase_request.procurement_bidding",
            raise_if_not_found=False,
        )
        if bidding and method == bidding:
            return True
        return "bidding" in (method.name or "").lower()

    def _egp_project_budget_amount(self):
        self.ensure_one()
        if self.ebidding_plan_line_id and self._is_egp_ebidding_method():
            return self.ebidding_plan_line_id.amount_total or 0.0
        return super()._egp_project_budget_amount()

    @api.depends(
        "purchase_request_id",
        "purchase_request_id.estimated_cost",
        "ebidding_plan_line_id",
        "ebidding_plan_line_id.amount_total",
        "procurement_method_id",
        "procurement_method_id.name",
    )
    def _compute_purchase_request_amount_total(self):
        for record in self:
            record.purchase_request_amount_total = record._egp_project_budget_amount()
