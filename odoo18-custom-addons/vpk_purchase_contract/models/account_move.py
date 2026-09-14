# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="รหัสสัญญาอ้างอิง",
        index=True,
        copy=False,
        tracking=True,
        help="ดึงมาจากใบสั่งซื้อ เพื่อรายงานติดตามสัญญา",
    )

    def _get_contract_from_purchase(self):
        self.ensure_one()
        purchases = self.invoice_line_ids.mapped("purchase_line_id.order_id")
        return purchases.mapped("contract_id")[:1]

    def action_post(self):
        for move in self.filtered(
            lambda inv: inv.move_type in ("in_invoice", "in_refund")
            and not inv.contract_id
        ):
            contract = move._get_contract_from_purchase()
            if contract:
                move.contract_id = contract
        return super().action_post()
