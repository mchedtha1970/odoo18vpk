# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    def _validate_purchase_request_selection(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_model or not active_ids:
            return
        records = self.env[active_model].browse(active_ids)
        purchase_requests = records
        if active_model == "purchase.request.line":
            purchase_requests = records.mapped("request_id")
        if purchase_requests.filtered(lambda rec: rec.state != "approved"):
            raise UserError(
                _(
                    "Only approved document is allowed to "
                    "create purchase agreement"
                )
            )
        if purchase_requests.filtered(lambda rec: rec.to_create != "purchase_agreement"):
            raise UserError(
                _(
                    "Selected document's purchase type is not "
                    "allowed to create purchase agreement"
                )
            )

    @api.model
    def default_get(self, fields_list):
        self._validate_purchase_request_selection()
        return super().default_get(fields_list)
