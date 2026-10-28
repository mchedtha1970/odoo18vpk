from odoo import _, models
from odoo.exceptions import UserError

RESET_CONTEXT = {
    "skip_validation_check": True,
    "skip_check_state_condition": True,
    "skip_budget_check_reset": True,
    "skip_budget_refresh": True,
    "vpk_in_auto_confirm": True,
    "mail_notrack": True,
    "tracking_disable": True,
}


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def action_vpk_test_reset(self):
        """ทดสอบ: กลับเป็นฉบับร่าง และลบเอกสารที่เกิดจากใบขอซื้อนี้."""
        self.ensure_one()
        self._vpk_test_reset_to_draft()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("รีเซ็ตแล้ว"),
                "message": _("ใบขอซื้อกลับเป็นฉบับร่าง และลบเอกสารที่เกี่ยวข้องแล้ว"),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                    "target": "current",
                },
            },
        }

    def _vpk_test_reset_to_draft(self):
        for request in self:
            orders = request._vpk_test_related_orders()
            requisitions = request._vpk_test_related_requisitions()
            acceptances = request._vpk_test_related_acceptances(orders)
            request._vpk_test_assert_can_reset(orders, acceptances)
            request._vpk_test_unlink_records(
                request._vpk_test_related_documents(requisitions, orders, acceptances)
            )
            for model_name in ("procurement.committee.appointment", "purchase.product.specification"):
                request._vpk_test_unlink_optional(model_name, [("request_id", "=", request.id)])
            request._vpk_test_cancel_acceptances(acceptances)
            request._vpk_test_unlink_records(acceptances)
            request._vpk_test_cancel_orders(orders)
            request._vpk_test_unlink_records(orders)
            if "saraban.document" in self.env:
                request._vpk_test_unlink_records(
                    self.env["saraban.document"].search(
                        [("purchase_request_id", "=", request.id)]
                    )
                )
            request._vpk_test_unlink_requisitions(requisitions)
            request.with_context(**RESET_CONTEXT)._vpk_test_reset_request_fields()

    def _vpk_test_related_requisitions(self):
        self.ensure_one()
        requisitions = self.env["purchase.requisition"]
        if hasattr(self, "_get_egp_requisitions"):
            requisitions |= self._get_egp_requisitions()
        if "purchase_request_id" in requisitions._fields:
            requisitions |= requisitions.search([("purchase_request_id", "=", self.id)])
        if "requisition_lines" in self.env["purchase.request.line"]._fields:
            requisitions |= self.line_ids.requisition_lines.requisition_id
        return requisitions.exists()

    def _vpk_test_related_orders(self):
        self.ensure_one()
        orders = self.line_ids.purchase_lines.order_id
        requisitions = self._vpk_test_related_requisitions()
        if requisitions and "requisition_id" in self.env["purchase.order"]._fields:
            orders |= self.env["purchase.order"].search(
                [("requisition_id", "in", requisitions.ids)]
            )
        return orders.exists()

    def _vpk_test_related_acceptances(self, orders):
        self.ensure_one()
        if "work.acceptance" not in self.env or not orders:
            return self.env["work.acceptance"].browse()
        return self.env["work.acceptance"].search([("purchase_id", "in", orders.ids)])

    def _vpk_test_related_documents(self, requisitions, orders, acceptances):
        self.ensure_one()
        Document = self.env["vpk.document.studio.document"]
        domain = [("request_id", "=", self.id)]
        extra = []
        if requisitions:
            extra.append(("requisition_id", "in", requisitions.ids))
        if orders:
            extra.append(("purchase_id", "in", orders.ids))
        if acceptances:
            extra.append(("wa_id", "in", acceptances.ids))
        if extra:
            domain = ["|"] * len(extra) + domain + extra
        return Document.search(domain)

    def _vpk_test_assert_can_reset(self, orders, acceptances):
        self.ensure_one()
        pickings = orders.picking_ids
        if acceptances and "wa_id" in self.env["stock.picking"]._fields:
            pickings |= self.env["stock.picking"].search([("wa_id", "in", acceptances.ids)])
        done_pickings = pickings.filtered(lambda picking: picking.state == "done")
        if done_pickings:
            raise UserError(
                _("ไม่สามารถรีเซ็ตได้ เพราะรับสินค้าแล้ว: %s")
                % ", ".join(done_pickings.mapped("name"))
            )
        posted_bills = orders.invoice_ids.filtered(lambda move: move.state == "posted")
        if posted_bills:
            raise UserError(
                _("ไม่สามารถรีเซ็ตได้ เพราะมีใบแจ้งหนี้ที่ลงบัญชีแล้ว: %s")
                % ", ".join(posted_bills.mapped("name"))
            )

    def _vpk_test_unlink_records(self, records):
        records = records.exists()
        if not records:
            return
        reviews = self.env["tier.review"].sudo().search(
            [("model", "=", records._name), ("res_id", "in", records.ids)]
        )
        if reviews:
            reviews.with_context(skip_validation_check=True).unlink()
        activities = self.env["mail.activity"].sudo().search(
            [("res_model", "=", records._name), ("res_id", "in", records.ids)]
        )
        if activities:
            activities.unlink()
        records.sudo().with_context(
            skip_validation_check=True,
            skip_check_state_condition=True,
            mail_notrack=True,
        ).unlink()

    def _vpk_test_unlink_optional(self, model_name, domain):
        if model_name in self.env:
            self._vpk_test_unlink_records(self.env[model_name].search(domain))

    def _vpk_test_cancel_acceptances(self, acceptances):
        for acceptance in acceptances.exists():
            if acceptance.state != "cancel" and hasattr(acceptance, "button_cancel"):
                acceptance.sudo().button_cancel()

    def _vpk_test_cancel_orders(self, orders):
        self._vpk_test_unlink_records(
            orders.invoice_ids.filtered(lambda move: move.state == "draft")
        )
        for picking in orders.picking_ids.filtered(
            lambda picking: picking.state not in ("cancel", "done")
        ):
            picking.sudo().action_cancel()
        for order in orders.exists():
            if order.state not in ("draft", "cancel"):
                order.sudo().button_cancel()

    def _vpk_test_unlink_requisitions(self, requisitions):
        requisitions = requisitions.exists()
        if not requisitions:
            return
        requisitions.sudo().with_context(
            skip_validation_check=True, mail_notrack=True
        ).write({"state": "cancel"})
        self._vpk_test_unlink_records(requisitions)

    def _vpk_test_reset_request_fields(self):
        self.ensure_one()
        if self.review_ids:
            self.review_ids.sudo().with_context(skip_validation_check=True).unlink()
        if (
            "budget_reservation_active" in self._fields
            and self.budget_reservation_active
            and hasattr(self, "_release_budget_reservation")
        ):
            self._release_budget_reservation()
        if "budget_check_line_ids" in self._fields:
            self.budget_check_line_ids.unlink()
        self.line_ids.do_uncancel()
        vals = {"state": "draft"}
        for field_name in (
            "substate_id",
            "sent_to_procurement_date",
            "procurement_owner_id",
            "procurement_claimed_date",
            "procurement_verified",
            "procurement_verified_by",
            "procurement_verified_date",
            "procurement_return_reason",
            "procurement_returned_by",
            "procurement_returned_date",
            "approved_by",
            "date_approved",
            "verified_by",
            "date_verified",
            "budget_check_message",
        ):
            if field_name in self._fields:
                vals[field_name] = False
        if "budget_check_state" in self._fields:
            vals["budget_check_state"] = "unchecked"
        if "budget_available_amount" in self._fields:
            vals["budget_available_amount"] = 0.0
        self.write(vals)
        self.message_post(
            body=_("รีเซ็ตสำหรับทดสอบ: กลับเป็นฉบับร่าง และลบเอกสารที่เกี่ยวข้อง")
        )
