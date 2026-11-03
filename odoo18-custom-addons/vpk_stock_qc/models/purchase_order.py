# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    qc_ids = fields.One2many(
        comodel_name="vpk.stock.qc",
        inverse_name="purchase_id",
        string="ใบตรวจ QC",
    )
    qc_count = fields.Integer(
        compute="_compute_qc_count",
        string="ใบตรวจ QC",
    )

    @api.depends("qc_ids")
    def _compute_qc_count(self):
        for order in self:
            order.qc_count = len(order.qc_ids)

    def action_view_qc(self):
        self.ensure_one()
        qcs = self.qc_ids
        action = {
            "type": "ir.actions.act_window",
            "name": _("ใบตรวจ QC"),
            "res_model": "vpk.stock.qc",
            "domain": [("purchase_id", "=", self.id)],
            "context": {"default_purchase_id": self.id},
        }
        if len(qcs) == 1:
            action.update(
                {
                    "res_id": qcs.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                }
            )
        else:
            action["view_mode"] = "list,form"
        return action
