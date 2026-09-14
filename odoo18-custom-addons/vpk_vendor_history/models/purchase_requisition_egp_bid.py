from odoo import models


class PurchaseRequisitionEgpBid(models.Model):
    _inherit = "purchase.requisition.egp.bid"

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_winner"):
            for bid in self.filtered("is_winner"):
                # ผู้ชนะ → ผู้ค้าปกติ
                if bid.partner_id:
                    bid.partner_id._mark_as_regular_vendor()
                # ผู้เสนอราคาอื่นในรอบเดียวกันที่ไม่ได้ชนะ
                losers = bid.requisition_id.egp_bid_ids.filtered(
                    lambda b: not b.is_winner and b.partner_id
                )
                losers.mapped("partner_id")._mark_as_unselected_bidder()
        return res
