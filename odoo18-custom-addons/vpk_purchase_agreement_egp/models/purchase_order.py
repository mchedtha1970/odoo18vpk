# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    egp_bid_reference = fields.Char(
        string="e-GP Bid Reference",
        copy=False,
        help="e-GP bid or quotation reference for this vendor.",
    )
    egp_project_reference = fields.Char(
        string="เลขที่โครงการ (e-GP)",
        related="requisition_id.egp_reference",
        readonly=True,
    )
    egp_project_name = fields.Char(
        string="ชื่อโครงการ",
        related="requisition_id.egp_project_name",
        readonly=True,
    )

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        requisition = self.requisition_id
        if not requisition or requisition.requisition_type != "egp_procurement":
            return super()._onchange_requisition_id()

        if not requisition:
            return

        self = self.with_company(self.company_id)
        partner = self.partner_id or requisition.vendor_id
        if not partner:
            self.company_id = requisition.company_id.id
            self.currency_id = requisition.currency_id.id
            if not self.origin:
                self.origin = requisition._get_rfq_origin()
            self.notes = requisition.description
            return

        payment_term = partner.property_supplier_payment_term_id
        FiscalPosition = self.env["account.fiscal.position"]
        fpos = FiscalPosition.with_company(self.company_id)._get_fiscal_position(partner)

        self.partner_id = partner.id
        self.fiscal_position_id = fpos.id
        self.payment_term_id = payment_term.id
        self.company_id = requisition.company_id.id
        self.currency_id = requisition.currency_id.id
        self.origin = requisition._get_rfq_origin(self.egp_bid_reference)
        self.notes = requisition.description
        self.order_line = requisition._prepare_rfq_order_line_values(partner)

    def button_confirm(self):
        res = super().button_confirm()
        for order in self.filtered(
            lambda po: po.requisition_id.requisition_type == "egp_procurement"
            and po.state == "purchase"
        ):
            requisition = order.requisition_id
            if requisition.state == "confirmed":
                other_open = requisition.purchase_ids.filtered(
                    lambda po: po.state in ("draft", "sent", "to approve") and po.id != order.id
                )
                if not other_open:
                    requisition.action_done()
        return res
