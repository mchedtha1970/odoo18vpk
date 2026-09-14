# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionCreateRfq(models.TransientModel):
    _name = "purchase.requisition.create.rfq"
    _description = "Create RFQ from Purchase Agreement"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="Purchase Agreement",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        context={"res_partner_search_mode": "supplier"},
    )
    egp_bid_reference = fields.Char(string="e-GP Bid Reference")

    def action_create_rfq(self):
        self.ensure_one()
        requisition = self.requisition_id
        if requisition.requisition_type == "egp_procurement":
            if requisition.state not in ("confirmed", "done"):
                raise UserError(
                    _("Please confirm the e-GP process before creating RFQs.")
                )
            winner = requisition.egp_bid_ids.filtered("is_winner")[:1]
            if not winner:
                raise UserError(
                    _(
                        "ยังไม่สามารถสร้าง RFQ/PO ได้ กรุณารับข้อเสนอ "
                        "เปรียบเทียบราคา และเลือกผู้ชนะในกระบวนการ eGP ก่อน"
                    )
                )
            if not requisition.egp_award_approved:
                raise UserError(
                    _(
                        "กรุณาอนุมัติรายงานผลการพิจารณาและ "
                        "ขออนุมัติสั่งซื้อ/สั่งจ้างก่อนสร้าง RFQ/PO"
                    )
                )
            if self.partner_id != winner.partner_id:
                raise UserError(
                    _(
                        "RFQ/PO สร้างได้เฉพาะผู้ชนะที่เลือกไว้: %(vendor)s"
                    )
                    % {"vendor": winner.partner_id.display_name}
                )
        elif requisition.state != "confirmed":
            raise UserError(_("Please confirm the purchase agreement before creating RFQs."))
        existing = requisition.purchase_ids.filtered(
            lambda po: po.partner_id == self.partner_id
            and po.state in ("draft", "sent", "to approve", "purchase", "done")
        )
        if existing:
            raise UserError(
                _("An RFQ already exists for vendor %(vendor)s on this agreement.")
                % {"vendor": self.partner_id.display_name}
            )

        po_vals = requisition._prepare_rfq_vals(self.partner_id, self.egp_bid_reference)
        if not po_vals.get("order_line"):
            raise UserError(_("No product lines found to create RFQ from the Purchase Request."))
        purchase_order = self.env["purchase.order"].create(po_vals)

        if requisition.purchase_ids and len(requisition.purchase_ids) > 1:
            first_rfq = requisition.purchase_ids.filtered(lambda po: po.id != purchase_order.id)[:1]
            if first_rfq and not purchase_order.purchase_group_id:
                if first_rfq.purchase_group_id:
                    first_rfq.purchase_group_id.order_ids |= purchase_order
                else:
                    self.env["purchase.order.group"].create(
                        {"order_ids": [(6, 0, first_rfq.ids + purchase_order.ids)]}
                    )

        return {
            "name": _("Request for Quotation"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": purchase_order.id,
        }
