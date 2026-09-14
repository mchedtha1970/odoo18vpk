# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseRequisitionEgpBid(models.Model):
    _name = "purchase.requisition.egp.bid"
    _description = "e-GP Bidder Comparison"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ eGP",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="requisition_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="requisition_id.currency_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้เสนอราคา",
        required=True,
        domain="[('supplier_rank', '>', 0)]",
        context={"res_partner_search_mode": "supplier", "default_supplier_rank": 1},
    )
    vendor_name = fields.Char(
        string="ชื่อผู้เสนอราคา",
        compute="_compute_vendor_name",
        store=True,
    )
    egp_bid_reference = fields.Char(
        string="เลขอ้างอิงใบเสนอราคา e-GP",
    )
    bid_date = fields.Date(
        string="วันที่เสนอราคา",
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.bid.line",
        inverse_name="bid_id",
        string="รายการราคา",
        copy=True,
    )
    amount_total = fields.Monetary(
        string="ราคาที่เสนอ",
        currency_field="currency_id",
    )
    is_winner = fields.Boolean(
        string="ผู้ชนะ",
        help="เลือกผู้เสนอราคารายนี้เป็นผู้ชนะ",
    )
    notes = fields.Text(string="หมายเหตุ")

    @api.depends("partner_id", "partner_id.name")
    def _compute_vendor_name(self):
        for bid in self:
            bid.vendor_name = bid.partner_id.display_name if bid.partner_id else False

    @api.model_create_multi
    def create(self, vals_list):
        bids = super().create(vals_list)
        bids._ensure_lines_from_requisition()
        return bids

    def _ensure_lines_from_requisition(self):
        BidLine = self.env["purchase.requisition.egp.bid.line"]
        for bid in self:
            if bid.line_ids or not bid.requisition_id:
                continue
            line_vals = []
            for req_line in bid.requisition_id.line_ids:
                line_vals.append(
                    {
                        "bid_id": bid.id,
                        "requisition_line_id": req_line.id,
                        "product_id": req_line.product_id.id,
                        "name": req_line.product_description_variants
                        or req_line.product_id.display_name,
                        "product_qty": req_line.product_qty,
                        "product_uom_id": req_line.product_uom_id.id,
                        "price_unit": 0.0,
                    }
                )
            if line_vals:
                BidLine.create(line_vals)

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_winner"):
            winners = self.filtered("is_winner")
            for bid in winners:
                (bid.requisition_id.egp_bid_ids - bid).write({"is_winner": False})
                if bid.partner_id and bid.requisition_id.vendor_id != bid.partner_id:
                    bid.requisition_id.vendor_id = bid.partner_id
        return res


class PurchaseRequisitionEgpBidLine(models.Model):
    _name = "purchase.requisition.egp.bid.line"
    _description = "e-GP Bidder Comparison Line"
    _order = "id"

    bid_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid",
        string="ผู้เสนอราคา",
        required=True,
        ondelete="cascade",
        index=True,
    )
    requisition_id = fields.Many2one(
        related="bid_id.requisition_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="bid_id.currency_id",
        store=True,
        readonly=True,
    )
    requisition_line_id = fields.Many2one(
        comodel_name="purchase.requisition.line",
        string="บรรทัดข้อตกลง",
        ondelete="set null",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า",
        required=True,
    )
    name = fields.Text(string="คำอธิบายรายการซื้อใน e-GP")
    product_qty = fields.Float(
        string="ปริมาณ",
        digits="Product Unit of Measure",
        default=1.0,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วยวัด",
    )
    price_unit = fields.Monetary(
        string="ราคาต่อหน่วย",
        currency_field="currency_id",
    )
    price_subtotal = fields.Monetary(
        string="รวม",
        currency_field="currency_id",
        compute="_compute_price_subtotal",
        store=True,
    )

    @api.depends("product_qty", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id
