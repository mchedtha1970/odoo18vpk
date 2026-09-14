# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    def _vpk_purchase_requests_from_context(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not active_model or not active_ids:
            return self.env["purchase.request"]
        records = self.env[active_model].browse(active_ids)
        if active_model == "purchase.request.line":
            return records.mapped("request_id")
        return records

    def _validate_purchase_request_selection(self):
        super()._validate_purchase_request_selection()
        for request in self._vpk_purchase_requests_from_context():
            if request._get_egp_requisitions():
                raise UserError(
                    _("ใบขอซื้อ %s มีกระบวนการ e-GP แล้ว") % request.display_name
                )
            if hasattr(request, "_vpk_related_documents_all_approved") and (
                not request._vpk_related_documents_all_approved()
            ):
                raise UserError(
                    _(
                        "กรุณาอนุมัติเอกสารที่เกี่ยวข้องให้ครบทุกฉบับก่อนส่งใบขอซื้อ %s เข้าระบบ e-GP"
                    )
                    % request.display_name
                )

    @api.model
    def _prepare_purchase_requisition(self, picking_type, group_id, company, origin):
        data = super()._prepare_purchase_requisition(picking_type, group_id, company, origin)
        data["requisition_type"] = "egp_procurement"
        return data

    def make_purchase_requisition(self):
        result = super().make_purchase_requisition()
        requisitions = self.env["purchase.requisition.line"].search(
            [("purchase_request_lines", "in", self.item_ids.mapped("line_id").ids)]
        ).mapped("requisition_id")
        for requisition in requisitions.filtered(
            lambda record: record.requisition_type == "egp_procurement"
        ):
            purchase_request = requisition.line_ids.purchase_request_lines.request_id[:1]
            if purchase_request:
                requisition.write(
                    {
                        "purchase_request_id": purchase_request.id,
                        "procurement_type_id": purchase_request.procurement_type_id.id,
                        "purchase_type_id": purchase_request.purchase_type_id.id,
                        "procurement_method_id": purchase_request.procurement_method_id.id,
                        "reference": purchase_request.name,
                    }
                )
        return result
