# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        string="ราคารวมที่เสนอ",
        currency_field="currency_id",
    )
    budget_amount_total = fields.Monetary(
        string="ราคารวมงบประมาณ",
        currency_field="currency_id",
        compute="_compute_budget_amount_total",
        store=True,
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

    @api.depends("line_ids.budget_amount")
    def _compute_budget_amount_total(self):
        for bid in self:
            bid.budget_amount_total = sum(bid.line_ids.mapped("budget_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        bids = super().create(vals_list)
        bids._ensure_lines_from_requisition()
        return bids

    def _ensure_lines_from_requisition(self):
        if self.env.context.get("egp_skip_bid_lines"):
            return
        BidLine = self.env["purchase.requisition.egp.bid.line"]
        for bid in self:
            if bid.line_ids or not bid.requisition_id:
                continue
            if bid.requisition_id.egp_consideration_type in ("line", "unit"):
                continue
            line_vals = []
            for req_line in bid.requisition_id.line_ids:
                line_vals.append(
                    {
                        "bid_id": bid.id,
                        "requisition_id": bid.requisition_id.id,
                        "partner_id": bid.partner_id.id,
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
        string="ใบเสนอราคาเปรียบเทียบ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ eGP",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้เสนอราคา",
        required=True,
        domain="[('supplier_rank', '>', 0)]",
        context={"res_partner_search_mode": "supplier", "default_supplier_rank": 1},
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
        string="ราคาต่อหน่วยที่เสนอ",
        currency_field="currency_id",
    )
    price_subtotal = fields.Monetary(
        string="ราคารวมที่เสนอ",
        currency_field="currency_id",
        compute="_compute_price_subtotal",
        inverse="_inverse_price_subtotal",
        store=True,
        readonly=False,
    )
    is_winner = fields.Boolean(
        string="ผู้ชนะ",
        help="เลือกผู้เสนอราคารายนี้เป็นผู้ชนะของรายการสินค้า",
    )
    budget_unit_price = fields.Monetary(
        string="งบประมาณต่อหน่วย",
        currency_field="currency_id",
        compute="_compute_budget_amounts",
        store=True,
        readonly=True,
    )
    budget_amount = fields.Monetary(
        string="งบประมาณที่ตั้ง",
        currency_field="currency_id",
        compute="_compute_budget_amounts",
        store=True,
        readonly=True,
    )

    @api.depends("product_qty", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit

    def _inverse_price_subtotal(self):
        for line in self:
            line.price_unit = line._unit_from_subtotal(
                line.price_subtotal, line.product_qty
            )

    @api.onchange("price_subtotal")
    def _onchange_price_subtotal(self):
        self._inverse_price_subtotal()

    @api.depends(
        "requisition_line_id",
        "requisition_line_id.budget_amount",
        "requisition_line_id.product_qty",
        "requisition_line_id.purchase_request_lines.estimated_cost",
        "requisition_id",
        "requisition_id.purchase_request_id",
        "requisition_id.purchase_request_id.line_ids.estimated_cost",
        "requisition_id.purchase_request_id.line_ids.product_id",
        "product_id",
        "product_qty",
    )
    def _compute_budget_amounts(self):
        for line in self:
            amount, unit = line._get_source_budget()
            line.budget_amount = amount
            line.budget_unit_price = unit

    def _find_requisition_line(self):
        self.ensure_one()
        if self.requisition_line_id:
            return self.requisition_line_id
        if not self.requisition_id or not self.product_id:
            return self.env["purchase.requisition.line"]
        return self.requisition_id.line_ids.filtered(
            lambda req_line: req_line.product_id == self.product_id
        )[:1]

    def _get_source_budget(self):
        self.ensure_one()
        req_line = self._find_requisition_line()
        qty = self.product_qty or (req_line.product_qty if req_line else 0.0) or 0.0
        if req_line and req_line.budget_amount:
            amount = req_line.budget_amount
            return amount, self._unit_from_subtotal(amount, qty)
        pr_lines = req_line.purchase_request_lines if req_line else self.env[
            "purchase.request.line"
        ]
        if not pr_lines and self.requisition_id.purchase_request_id and self.product_id:
            pr_lines = self.requisition_id.purchase_request_id.line_ids.filtered(
                lambda pr_line: pr_line.product_id == self.product_id
            )
        if pr_lines:
            amount = sum(pr_lines.mapped("estimated_cost")) or 0.0
            unit = 0.0
            if (
                len(pr_lines) == 1
                and "budget_unit_price" in pr_lines._fields
                and pr_lines.budget_unit_price
            ):
                unit = pr_lines.budget_unit_price
            else:
                unit = self._unit_from_subtotal(amount, qty)
            return amount, unit
        return 0.0, 0.0

    @api.model
    def _unit_from_subtotal(self, subtotal, qty):
        subtotal = subtotal or 0.0
        qty = qty or 0.0
        if qty:
            return subtotal / qty
        return subtotal

    def _apply_requisition_line_defaults(self):
        for line in self:
            req_line = line._find_requisition_line()
            if not req_line:
                continue
            updates = {}
            if not line.requisition_line_id:
                updates["requisition_line_id"] = req_line.id
            if not line.name:
                updates["name"] = (
                    req_line.product_description_variants
                    or req_line.product_id.display_name
                )
            if not line.product_qty:
                updates["product_qty"] = req_line.product_qty
            if not line.product_uom_id and req_line.product_uom_id:
                updates["product_uom_id"] = req_line.product_uom_id.id
            if updates:
                super(PurchaseRequisitionEgpBidLine, line).write(updates)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id
            req_line = self._find_requisition_line()
            if req_line:
                self.requisition_line_id = req_line
                self.name = (
                    req_line.product_description_variants
                    or req_line.product_id.display_name
                )
                self.product_qty = req_line.product_qty
                self.product_uom_id = (
                    req_line.product_uom_id or self.product_uom_id
                )
                amount, unit = self._get_source_budget()
                self.budget_amount = amount
                self.budget_unit_price = unit

    @api.onchange("bid_id")
    def _onchange_bid_id(self):
        if self.bid_id:
            self.requisition_id = self.bid_id.requisition_id
            if self.bid_id.partner_id:
                self.partner_id = self.bid_id.partner_id

    @api.model
    def _get_or_create_bid(self, requisition_id, partner_id):
        Bid = self.env["purchase.requisition.egp.bid"]
        bid = Bid.search(
            [
                ("requisition_id", "=", requisition_id),
                ("partner_id", "=", partner_id),
            ],
            limit=1,
        )
        if not bid:
            bid = Bid.with_context(egp_skip_bid_lines=True).create(
                {
                    "requisition_id": requisition_id,
                    "partner_id": partner_id,
                }
            )
        return bid

    def _prepare_bid_link_vals(self, vals):
        vals = dict(vals)
        bid = self.env["purchase.requisition.egp.bid"].browse(vals.get("bid_id") or False)
        if bid:
            vals.setdefault("requisition_id", bid.requisition_id.id)
            vals.setdefault("partner_id", bid.partner_id.id)
        else:
            requisition_id = vals.get("requisition_id") or self.env.context.get(
                "default_requisition_id"
            )
            partner_id = vals.get("partner_id")
            if not requisition_id or not partner_id:
                raise UserError(_("กรุณาเลือกผู้เสนอราคาและรายการสินค้า"))
            bid = self._get_or_create_bid(requisition_id, partner_id)
            vals["bid_id"] = bid.id
            vals["requisition_id"] = bid.requisition_id.id
        if not vals.get("requisition_line_id") and vals.get("product_id"):
            requisition = self.env["purchase.requisition"].browse(
                vals.get("requisition_id")
            )
            req_line = requisition.line_ids.filtered(
                lambda line: line.product_id.id == vals["product_id"]
            )[:1]
            if req_line:
                vals["requisition_line_id"] = req_line.id
                vals.setdefault("product_qty", req_line.product_qty)
                if req_line.product_uom_id:
                    vals.setdefault("product_uom_id", req_line.product_uom_id.id)
                vals.setdefault(
                    "name",
                    req_line.product_description_variants
                    or req_line.product_id.display_name,
                )
        return vals

    def _vals_with_unit_from_subtotal(self, vals):
        vals = dict(vals)
        if "price_subtotal" in vals and "price_unit" not in vals:
            qty = vals.get("product_qty")
            if qty is None:
                qty = 1.0
            vals["price_unit"] = self._unit_from_subtotal(
                vals.get("price_subtotal") or 0.0, qty
            )
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared = [
            self._vals_with_unit_from_subtotal(self._prepare_bid_link_vals(vals))
            for vals in vals_list
        ]
        lines = super().create(prepared)
        lines._apply_requisition_line_defaults()
        lines._sync_bid_amount()
        lines._apply_exclusive_line_winner()
        return lines

    def _same_product_lines(self):
        self.ensure_one()
        lines = self.requisition_id.egp_bid_line_ids - self
        if self.requisition_line_id:
            return lines.filtered(
                lambda line: line.requisition_line_id == self.requisition_line_id
            )
        if self.product_id:
            return lines.filtered(lambda line: line.product_id == self.product_id)
        return self.browse()

    def _apply_exclusive_line_winner(self):
        if self.env.context.get("egp_skip_line_winner"):
            return
        for line in self.filtered("is_winner"):
            others = line._same_product_lines().filtered("is_winner")
            if others:
                others.with_context(egp_skip_line_winner=True).write(
                    {"is_winner": False}
                )

    def write(self, vals):
        if "partner_id" in vals and not self.env.context.get("egp_skip_bid_partner"):
            partner_id = vals["partner_id"]
            if not partner_id:
                raise UserError(_("กรุณาเลือกผู้เสนอราคาและรายการสินค้า"))
            old_bids = self.mapped("bid_id")
            for line in self:
                requisition = line.requisition_id or line.bid_id.requisition_id
                if not requisition:
                    continue
                bid = self._get_or_create_bid(requisition.id, partner_id)
                super(PurchaseRequisitionEgpBidLine, line).write(
                    dict(vals, bid_id=bid.id, requisition_id=requisition.id)
                )
            empty_bids = (old_bids - self.mapped("bid_id")).filtered(
                lambda bid: not bid.line_ids
            )
            empty_bids.unlink()
            (old_bids.exists() | self.mapped("bid_id")).line_ids._sync_bid_amount()
            if vals.get("is_winner"):
                self._apply_exclusive_line_winner()
            return True
        res = super().write(vals)
        if "product_id" in vals and "requisition_line_id" not in vals:
            self._apply_requisition_line_defaults()
        if any(
            key in vals
            for key in ("product_qty", "price_unit", "price_subtotal", "bid_id")
        ):
            self._sync_bid_amount()
        if vals.get("is_winner"):
            self._apply_exclusive_line_winner()
        return res

    def unlink(self):
        bids = self.mapped("bid_id")
        res = super().unlink()
        remaining = bids.exists()
        remaining.line_ids._sync_bid_amount()
        for bid in remaining:
            if not bid.line_ids and bid.requisition_id.egp_consideration_type in (
                "line",
                "unit",
            ):
                bid.amount_total = 0.0
        return res

    def _sync_bid_amount(self):
        for bid in self.mapped("bid_id"):
            if not bid:
                continue
            line_total = sum(bid.line_ids.mapped("price_subtotal"))
            consideration = bid.requisition_id.egp_consideration_type
            if consideration in ("line", "unit") or line_total:
                bid.amount_total = line_total
