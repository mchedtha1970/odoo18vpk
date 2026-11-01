# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    is_unlimited_contract_po = fields.Boolean(
        string="สร้างจากสัญญาไม่จำกัดจำนวน",
    )

    def _must_create_egp_before_po(self, request_line):
        contract = request_line.request_id.contract_id
        if contract and contract.quantity_policy == "unlimited":
            return False
        return super()._must_create_egp_before_po(request_line)

    @api.model
    def _unlimited_contract_partner_from_context(self):
        request_lines = self._contract_request_lines_from_context()
        partners = request_lines.mapped("request_id.contract_id").filtered(
            lambda contract: contract.quantity_policy == "unlimited"
        ).mapped("partner_id")
        return partners if len(partners) == 1 else self.env["res.partner"]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner = self._unlimited_contract_partner_from_context()
        if partner:
            res["supplier_id"] = partner.id
            res["is_unlimited_contract_po"] = True
        return res

    @api.model
    def _contract_request_lines_from_context(self):
        active_model = self.env.context.get("active_model")
        if active_model == "purchase.request.line":
            return self.env["purchase.request.line"].browse(
                self.env.context.get("active_ids", [])
            )
        if active_model == "purchase.request":
            return self.env["purchase.request"].browse(
                self.env.context.get("active_ids", [])
            ).mapped("line_ids")
        return self.env["purchase.request.line"]

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        data = super()._prepare_purchase_order(picking_type, group_id, company, origin)
        contracts = self.item_ids.mapped("request_id.contract_id")
        if len(contracts) == 1:
            data["contract_id"] = contracts.id
            if (
                contracts.quantity_policy == "unlimited"
                and contracts.partner_id
                and not data.get("partner_id")
            ):
                data["partner_id"] = contracts.partner_id.id
        return data

    def _post_process_po_line(self, item, po_line, new_pr_line):
        super()._post_process_po_line(item, po_line, new_pr_line)
        contract_line = item.line_id.contract_line_id
        if (
            not contract_line
            or contract_line.contract_id.quantity_policy != "unlimited"
            or not contract_line.price_unit
        ):
            return
        po_line.price_unit = contract_line.price_unit
