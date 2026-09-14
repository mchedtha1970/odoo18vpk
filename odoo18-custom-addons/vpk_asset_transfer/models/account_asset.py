# -*- coding: utf-8 -*-
from odoo import api, fields, models

WAREHOUSE_ANALYTIC_NAME = "คลังสินค้า"


class AccountAsset(models.Model):
    _inherit = "account.asset"
    _rec_names_search = ["number", "name", "code"]

    owning_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานที่ถือครอง",
        tracking=True,
        check_company=True,
        default=lambda self: self._default_owning_analytic_account_id(),
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="หน่วยงานที่รับผิดชอบ/ถือครองทรัพย์สินในปัจจุบัน "
        "(ค่าเริ่มต้นเมื่อรับเข้าใหม่: คลังสินค้า)",
    )
    transfer_line_ids = fields.One2many(
        comodel_name="vpk.asset.transfer.line",
        inverse_name="asset_id",
        string="ประวัติใบโอน",
    )
    transfer_count = fields.Integer(compute="_compute_transfer_count")

    def _compute_transfer_count(self):
        for asset in self:
            asset.transfer_count = len(asset.transfer_line_ids)

    @api.model
    def _get_warehouse_analytic_account(self, company=None):
        """Find or create analytic account คลังสินค้า for default asset custody."""
        company = company or self.env.company
        Analytic = self.env["account.analytic.account"]
        account = Analytic.search(
            [
                ("name", "=", WAREHOUSE_ANALYTIC_NAME),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if account:
            return account

        plan = self.env["account.analytic.plan"].search(
            [("name", "=", "หน่วยงาน")], limit=1
        ) or self.env["account.analytic.plan"].search([], limit=1)
        return Analytic.create(
            {
                "name": WAREHOUSE_ANALYTIC_NAME,
                "plan_id": plan.id,
                "company_id": company.id,
            }
        )

    @api.model
    def _default_owning_analytic_account_id(self):
        return self._get_warehouse_analytic_account()

    @api.model_create_multi
    def create(self, vals_list):
        warehouse = False
        for vals in vals_list:
            if not vals.get("owning_analytic_account_id"):
                company = self.env["res.company"].browse(
                    vals.get("company_id") or self.env.company.id
                )
                if not warehouse or warehouse.company_id != company:
                    warehouse = self._get_warehouse_analytic_account(company)
                vals["owning_analytic_account_id"] = warehouse.id
            # Align Analytic Distribution with owning department on create
            owning_id = vals.get("owning_analytic_account_id")
            if owning_id and not vals.get("analytic_distribution"):
                vals["analytic_distribution"] = {str(owning_id): 100}
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "owning_analytic_account_id" in vals and "analytic_distribution" not in vals:
            for asset in self:
                asset._sync_analytic_distribution_from_owning()
        return res

    def _sync_analytic_distribution_from_owning(self):
        """Set Analytic Distribution 100% to owning department."""
        self.ensure_one()
        if self.owning_analytic_account_id:
            distribution = {str(self.owning_analytic_account_id.id): 100}
        else:
            distribution = self.profile_id.analytic_distribution or False
        if self.analytic_distribution != distribution:
            super(AccountAsset, self).write({"analytic_distribution": distribution})

    @api.depends("profile_id", "owning_analytic_account_id")
    def _compute_analytic_distribution(self):
        for asset in self:
            if asset.owning_analytic_account_id:
                asset.analytic_distribution = {
                    str(asset.owning_analytic_account_id.id): 100
                }
            else:
                asset.analytic_distribution = (
                    asset.profile_id.analytic_distribution or False
                )

    @api.depends("name", "code", "number")
    def _compute_display_name(self):
        for asset in self:
            parts = []
            if asset.number:
                parts.append(asset.number)
            elif asset.code:
                parts.append(asset.code)
            if asset.name:
                parts.append(asset.name)
            asset.display_name = " - ".join(parts) if parts else asset.name or ""

    def action_open_asset_transfers(self):
        self.ensure_one()
        transfer_ids = self.transfer_line_ids.mapped("transfer_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": "ใบโอนทรัพย์สิน",
            "res_model": "vpk.asset.transfer",
            "view_mode": "list,form",
            "domain": [("id", "in", transfer_ids)],
            "context": {"default_line_ids": [(0, 0, {"asset_id": self.id})]},
        }
