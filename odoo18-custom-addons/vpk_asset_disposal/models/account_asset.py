# -*- coding: utf-8 -*-
from odoo import _, fields, models


class AccountAsset(models.Model):
    _inherit = "account.asset"

    disposal_line_ids = fields.One2many(
        comodel_name="vpk.asset.disposal.line",
        inverse_name="asset_id",
        string="ใบขออนุมัติจำหน่าย",
    )
    disposal_count = fields.Integer(
        string="จำนวนใบจำหน่าย",
        compute="_compute_disposal_count",
    )

    def _compute_disposal_count(self):
        for asset in self:
            asset.disposal_count = len(asset.disposal_line_ids.mapped("disposal_id"))

    def action_view_disposals(self):
        self.ensure_one()
        disposal_ids = self.disposal_line_ids.mapped("disposal_id").ids
        action = {
            "type": "ir.actions.act_window",
            "name": _("ใบขออนุมัติจำหน่าย"),
            "res_model": "vpk.asset.disposal",
            "view_mode": "list,form",
            "domain": [("id", "in", disposal_ids)],
        }
        if len(disposal_ids) == 1:
            action.update({"view_mode": "form", "res_id": disposal_ids[0]})
        return action
