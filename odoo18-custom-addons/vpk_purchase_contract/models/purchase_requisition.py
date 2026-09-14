# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    contract_ids = fields.One2many(
        comodel_name="purchase.contract",
        inverse_name="requisition_id",
        string="ทะเบียนสัญญา",
    )
    contract_count = fields.Integer(compute="_compute_contract_count")

    source_contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="อ้างอิงสัญญา",
        tracking=True,
        index=True,
        copy=False,
        help="สัญญาที่ PR อ้างอิงมา (กรณีจัดซื้อตามสัญญา ไม่ต้องเปรียบเทียบราคา)",
    )
    is_contract_procurement = fields.Boolean(
        compute="_compute_is_contract_procurement",
    )
    source_contract_partner = fields.Char(
        related="source_contract_id.partner_id.display_name",
        string="คู่ค้าตามสัญญา",
    )
    source_contract_amount = fields.Monetary(
        related="source_contract_id.amount_total",
        string="วงเงินสัญญา",
        currency_field="currency_id",
    )
    source_contract_remaining = fields.Monetary(
        related="source_contract_id.amount_remaining",
        string="ยอดคงเหลือสัญญา",
        currency_field="currency_id",
    )

    @api.depends("source_contract_id")
    def _compute_is_contract_procurement(self):
        for record in self:
            record.is_contract_procurement = bool(record.source_contract_id)

    def _compute_contract_count(self):
        for requisition in self:
            requisition.contract_count = len(requisition.contract_ids)

    def action_create_purchase_contract(self):
        """ขั้นตอนที่ 1: เปิดทะเบียนสัญญาหลักหลังคัดเลือกผู้ชนะ e-GP."""
        self.ensure_one()
        winner_bid = self.egp_bid_ids.filtered("is_winner")[:1]
        partner = winner_bid.partner_id if winner_bid else self.vendor_id
        amount = 0.0
        if winner_bid and winner_bid.amount_total:
            amount = winner_bid.amount_total
        elif self.purchase_request_amount_total:
            amount = self.purchase_request_amount_total

        contract = self.env["purchase.contract"].create(
            {
                "partner_id": partner.id if partner else False,
                "amount_total": amount,
                "company_id": self.company_id.id,
                "currency_id": self.currency_id.id,
                "requisition_id": self.id,
                "description": self.description,
                "payment_term_note": _(
                    "สร้างจากเอกสาร e-GP %(ref)s"
                )
                % {"ref": self.egp_reference or self.name},
            }
        )
        return {
            "name": _("ทะเบียนสัญญาหลัก"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract",
            "view_mode": "form",
            "res_id": contract.id,
            "target": "current",
        }

    def action_view_purchase_contracts(self):
        self.ensure_one()
        action = {
            "name": _("ทะเบียนสัญญา"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {
                "default_requisition_id": self.id,
                "default_company_id": self.company_id.id,
                "default_currency_id": self.currency_id.id,
            },
        }
        if len(self.contract_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.contract_ids.id
        return action


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    @api.depends(
        "product_id",
        "company_id",
        "requisition_id.date_start",
        "product_qty",
        "product_uom_id",
        "requisition_id.vendor_id",
        "requisition_id.requisition_type",
        "requisition_id.source_contract_id",
        "purchase_request_lines.estimated_cost",
    )
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self.filtered(
            lambda l: l.requisition_id.requisition_type == "egp_procurement"
            and l.requisition_id.source_contract_id
        ):
            pr_lines = line.purchase_request_lines
            if not pr_lines:
                continue
            estimated = sum(l.estimated_cost for l in pr_lines if l.estimated_cost)
            if not estimated:
                continue
            qty = line.product_qty or 1.0
            line.price_unit = line.requisition_id.currency_id.round(estimated / qty)
