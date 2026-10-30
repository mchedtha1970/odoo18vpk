# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        """สร้างสัญญาของผู้ขายที่ชนะ พร้อมรายการสินค้าที่ชนะ."""
        self.ensure_one()
        if self.requisition_type != "egp_procurement":
            raise UserError(_("สร้างสัญญาได้เฉพาะกระบวนการ e-GP"))
        groups = self._egp_winner_contract_groups()
        if not groups:
            raise UserError(self._egp_winner_contract_missing_message())
        contracts = self.env["purchase.contract"]
        for group in groups:
            contracts |= self._egp_upsert_winner_contract(group)
        return self._egp_open_created_contracts(contracts)

    def _egp_winner_contract_missing_message(self):
        if self.egp_consideration_type in ("line", "unit"):
            return _("กรุณาเลือกผู้ชนะในแต่ละรายการสินค้าก่อนสร้างสัญญา")
        return _("กรุณาเลือกผู้เสนอราคาผู้ชนะก่อนสร้างสัญญา")

    def _egp_winner_contract_groups(self):
        self.ensure_one()
        if self.egp_consideration_type in ("line", "unit"):
            winning_lines = self.egp_bid_line_ids.filtered(
                lambda line: line.is_winner and line.partner_id and line.product_id
            )
            groups = []
            for partner in winning_lines.mapped("partner_id"):
                lines = winning_lines.filtered(lambda line: line.partner_id == partner)
                groups.append(
                    {
                        "partner": partner,
                        "amount": sum(lines.mapped("price_subtotal")),
                        "line_vals": [
                            self._prepare_contract_line_from_bid_line(line)
                            for line in lines
                        ],
                    }
                )
            return groups
        winner = self.egp_bid_ids.filtered("is_winner")[:1]
        if not winner:
            return []
        bid_lines = winner.line_ids.filtered("product_id")
        if bid_lines:
            line_vals = [
                self._prepare_contract_line_from_bid_line(line) for line in bid_lines
            ]
        else:
            line_vals = [
                self._prepare_contract_line_from_requisition_line(line)
                for line in self.line_ids.filtered("product_id")
            ]
        amount = winner.amount_total or sum(
            vals.get("price_unit", 0.0) * vals.get("product_qty", 0.0)
            for vals in line_vals
        )
        return [
            {
                "partner": winner.partner_id,
                "amount": amount or self.purchase_request_amount_total or 0.0,
                "line_vals": line_vals,
            }
        ]

    def _prepare_contract_line_from_bid_line(self, bid_line):
        return {
            "product_id": bid_line.product_id.id,
            "name": bid_line.name or bid_line.product_id.display_name,
            "product_qty": bid_line.product_qty,
            "product_uom_id": bid_line.product_uom_id.id
            if bid_line.product_uom_id
            else False,
            "price_unit": bid_line.price_unit,
            "egp_bid_line_id": bid_line.id,
        }

    def _prepare_contract_line_from_requisition_line(self, req_line):
        return {
            "product_id": req_line.product_id.id,
            "name": req_line.product_description_variants
            or req_line.product_id.display_name,
            "product_qty": req_line.product_qty,
            "product_uom_id": req_line.product_uom_id.id
            if req_line.product_uom_id
            else False,
            "price_unit": req_line.price_unit or 0.0,
        }

    def _egp_upsert_winner_contract(self, group):
        partner = group["partner"]
        contract = self.contract_ids.filtered(
            lambda rec: rec.partner_id == partner and rec.state == "draft"
        )[:1]
        line_commands = [(0, 0, vals) for vals in group["line_vals"]]
        values = {
            "partner_id": partner.id if partner else False,
            "amount_total": group["amount"] or 0.0,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "requisition_id": self.id,
            "description": self.description,
            "payment_term_note": _("สร้างจากเอกสาร e-GP %(ref)s")
            % {"ref": self.egp_reference or self.name},
        }
        if contract:
            contract.write(dict(values, line_ids=[(5, 0, 0)] + line_commands))
            return contract
        return self.env["purchase.contract"].create(
            dict(values, line_ids=line_commands)
        )

    def _egp_open_created_contracts(self, contracts):
        action = {
            "name": _("ทะเบียนสัญญา"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.contract",
            "view_mode": "list,form",
            "domain": [("id", "in", contracts.ids)],
            "context": {
                "default_requisition_id": self.id,
                "default_company_id": self.company_id.id,
                "default_currency_id": self.currency_id.id,
            },
        }
        if len(contracts) == 1:
            action["view_mode"] = "form"
            action["res_id"] = contracts.id
            action.pop("domain", None)
        return action

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
