# -*- coding: utf-8 -*-
from odoo import api, fields, models


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
