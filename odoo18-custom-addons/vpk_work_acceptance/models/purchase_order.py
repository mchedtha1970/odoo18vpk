# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _get_wa_committee_from_pr(self):
        """ดึงคณะกรรมการตรวจรับจาก PR ที่เชื่อมกับ PO."""
        self.ensure_one()
        pr_lines = self.order_line.mapped("purchase_request_lines")
        requests = pr_lines.mapped("request_id")
        committee_vals = []
        seen = set()
        for pr in requests:
            for member in pr.work_acceptance_committee_ids:
                key = member.employee_id.id if member.employee_id else member.name
                if key in seen:
                    continue
                seen.add(key)
                role_map = {
                    "chairman": "chairman",
                    "committee": "member",
                }
                vals = {
                    "name": member.name,
                    "position": member.employee_id.job_title if member.employee_id else "",
                    "role": role_map.get(member.approve_role, "member"),
                    "employee_id": member.employee_id.user_id.id if member.employee_id and member.employee_id.user_id else False,
                    "note": member.note or "",
                }
                committee_vals.append(Command.create(vals))
        return committee_vals

    def action_view_wa(self):
        """Override to include contract/installment defaults and committee."""
        result = super().action_view_wa()
        if not isinstance(result.get("context"), dict):
            return result
        ctx = dict(result["context"])
        if self.contract_id:
            ctx["default_contract_id"] = self.contract_id.id
            pr_lines = self.order_line.mapped("purchase_request_lines")
            installment = pr_lines.mapped("contract_installment_id")[:1]
            if installment:
                ctx["default_contract_installment_id"] = installment.id
            if self.contract_id.date_end:
                ctx["default_due_date_contract"] = str(self.contract_id.date_end)
        committee_vals = self._get_wa_committee_from_pr()
        if committee_vals:
            ctx["default_committee_ids"] = committee_vals
        result["context"] = ctx
        return result
