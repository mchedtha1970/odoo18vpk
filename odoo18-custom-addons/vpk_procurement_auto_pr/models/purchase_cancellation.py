from markupsafe import Markup, escape

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    cancellation_note = fields.Text(
        string="รายละเอียดเหตุผลการยกเลิก",
        readonly=True,
        copy=False,
        tracking=True,
    )
    cancelled_at = fields.Datetime(
        string="วันที่ยกเลิก",
        readonly=True,
        copy=False,
    )
    cancelled_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ดำเนินการยกเลิก",
        readonly=True,
        copy=False,
    )
    cancellation_department_notified = fields.Boolean(
        string="แจ้งหน่วยงานแล้ว",
        readonly=True,
        copy=False,
    )
    vendor_confirmation_locked = fields.Boolean(
        string="ล็อกการยืนยันของผู้จำหน่าย",
        readonly=True,
        copy=False,
    )
    replacement_required = fields.Boolean(
        string="ต้องออก PO ใหม่",
        copy=False,
    )
    replacement_po_id = fields.Many2one(
        comodel_name="purchase.order",
        string="PO ทดแทน",
        readonly=True,
        copy=False,
    )
    original_cancelled_po_id = fields.Many2one(
        comodel_name="purchase.order",
        string="PO เดิมที่ถูกยกเลิก",
        readonly=True,
        copy=False,
        index=True,
    )

    def _can_vendor_confirm(self):
        self.ensure_one()
        return (
            super()._can_vendor_confirm()
            and not self.vendor_confirmation_locked
            and self.state != "cancel"
        )

    def button_cancel(self):
        orders_to_notify = self.filtered(lambda order: order.state != "cancel")
        result = super().button_cancel()
        for order in orders_to_notify.filtered(
            lambda record: record.state == "cancel"
        ):
            order.write({
                "cancelled_at": fields.Datetime.now(),
                "cancelled_by_id": self.env.user.id,
                "vendor_confirmation_locked": True,
            })
            order._notify_requesting_department_of_cancellation()
        return result

    def _notify_requesting_department_of_cancellation(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for order in self:
            requests = order.order_line.mapped(
                "purchase_request_lines.request_id"
            )
            reason = order.cancel_reason_id.display_name
            details = order.cancellation_note or "-"
            for request in requests:
                request.message_post(
                    body=Markup(
                        "<strong>แจ้งยกเลิก PO %(po)s</strong><br/>"
                        "เหตุผล: %(reason)s<br/>"
                        "รายละเอียด: %(details)s<br/>"
                        "กรุณาตรวจสอบและดำเนินการออก PO ใหม่"
                    )
                    % {
                        "po": escape(order.name),
                        "reason": escape(reason),
                        "details": escape(details),
                    }
                )
                notify_user = request.requested_by or request.assigned_to
                if notify_user:
                    request.activity_schedule(
                        activity_type_id=activity_type.id,
                        user_id=notify_user.id,
                        summary=_("ออก PO ใหม่ทดแทน %s") % order.name,
                        note=details,
                        date_deadline=fields.Date.context_today(request),
                    )
            order.cancellation_department_notified = bool(requests)
            order.message_post(
                body=Markup(
                    "<strong>ยกเลิก PO และล็อก Vendor Portal แล้ว</strong>"
                    "<br/>เหตุผล: %(reason)s"
                    "<br/>แจ้งหน่วยงานต้นเรื่อง: %(notified)s"
                )
                % {
                    "reason": escape(reason),
                    "notified": escape(
                        _("เรียบร้อย") if requests else _("ไม่พบ PR ต้นทาง")
                    ),
                }
            )

    def action_create_replacement_po(self):
        self.ensure_one()
        if self.state != "cancel":
            raise UserError(_("สร้าง PO ทดแทนได้เฉพาะ PO ที่ยกเลิกแล้ว"))
        if self.replacement_po_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "res_id": self.replacement_po_id.id,
                "view_mode": "form",
            }
        replacement = self.copy(default={
            "name": _("New"),
            "state": "draft",
            "cancel_reason_id": False,
            "cancellation_note": False,
            "cancelled_at": False,
            "cancelled_by_id": False,
            "cancellation_department_notified": False,
            "vendor_confirmation_locked": False,
            "replacement_required": False,
            "replacement_po_id": False,
            "original_cancelled_po_id": self.id,
            "origin": _("%(origin)s | ทดแทน %(po)s")
            % {"origin": self.origin or "", "po": self.name},
        })
        original_lines = self.order_line.filtered(
            lambda line: not line.display_type
        )
        replacement_lines = replacement.order_line.filtered(
            lambda line: not line.display_type
        )
        for original_line, replacement_line in zip(
            original_lines, replacement_lines
        ):
            replacement_line.purchase_request_lines = (
                original_line.purchase_request_lines
            )
            for allocation in original_line.purchase_request_allocation_ids:
                self.env["purchase.request.allocation"].create({
                    "requested_product_uom_qty": (
                        allocation.requested_product_uom_qty
                    ),
                    "product_uom_id": allocation.product_uom_id.id,
                    "purchase_request_line_id": (
                        allocation.purchase_request_line_id.id
                    ),
                    "purchase_line_id": replacement_line.id,
                })
        self.write({
            "replacement_po_id": replacement.id,
            "replacement_required": False,
        })
        self.message_post(
            body=_("สร้าง PO ทดแทนแล้ว: %s") % replacement.display_name
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": replacement.id,
            "view_mode": "form",
        }


class PurchaseOrderCancel(models.TransientModel):
    _inherit = "purchase.order.cancel"

    cancellation_note = fields.Text(
        string="รายละเอียดเหตุผลการขอยกเลิก",
        required=True,
    )
    replacement_required = fields.Boolean(
        string="แจ้งหน่วยงานเพื่อออก PO ใหม่",
        default=True,
    )

    def confirm_cancel(self):
        self.ensure_one()
        purchase_orders = self.env["purchase.order"].browse(
            self.env.context.get("active_ids", [])
        )
        purchase_orders.write({
            "cancellation_note": self.cancellation_note,
            "replacement_required": self.replacement_required,
        })
        return super().confirm_cancel()
