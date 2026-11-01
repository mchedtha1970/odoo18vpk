# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    def _must_create_egp_before_po(self, request_line):
        """ใบที่ต้องเปิดกระบวนการ e-GP ก่อนสร้างใบสั่งซื้อ"""
        return request_line.request_id.to_create == "purchase_agreement"

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        super()._check_valid_request_line(request_line_ids)
        for line in self.env["purchase.request.line"].browse(request_line_ids):
            if self._must_create_egp_before_po(line):
                raise UserError(
                    _(
                        "Purchase requests configured for Purchase Agreement must create "
                        "an e-GP Purchase Agreement first. Use Create Purchase Agreements "
                        "instead of Create RFQ."
                    )
                )
