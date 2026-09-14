# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, models


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    def make_purchase_requisition(self):
        result = super().make_purchase_requisition()
        self._populate_contract_on_requisitions()
        return result

    def _populate_contract_on_requisitions(self):
        """Auto-fill contract info + create winner bid for contract-linked PRs."""
        requisitions = (
            self.env["purchase.requisition.line"]
            .search(
                [
                    (
                        "purchase_request_lines",
                        "in",
                        self.item_ids.mapped("line_id").ids,
                    )
                ]
            )
            .mapped("requisition_id")
        )
        for requisition in requisitions.filtered(
            lambda r: r.requisition_type == "egp_procurement"
            and not r.source_contract_id
        ):
            pr = requisition.purchase_request_id
            if not pr or not pr.contract_id:
                continue
            contract = pr.contract_id
            requisition.write(
                {
                    "source_contract_id": contract.id,
                    "vendor_id": contract.partner_id.id,
                    "egp_reference": contract.name,
                    "egp_project_name": _(
                        "จัดซื้อตามสัญญา %(contract)s"
                    )
                    % {"contract": contract.display_name},
                }
            )
            self._create_contract_winner_bid(requisition, contract, pr)

    def _create_contract_winner_bid(self, requisition, contract, pr):
        """Create a single winner bid from the contract — skips comparison."""
        pr_amount = sum(
            line.estimated_cost
            for line in pr.line_ids
            if not line.cancelled and line.estimated_cost
        )
        self.env["purchase.requisition.egp.bid"].create(
            {
                "requisition_id": requisition.id,
                "partner_id": contract.partner_id.id,
                "amount_total": pr_amount or 0.0,
                "is_winner": True,
                "notes": _(
                    "จัดซื้อตามสัญญา %(contract)s — ไม่ต้องเปรียบเทียบราคา"
                )
                % {"contract": contract.display_name},
            }
        )
