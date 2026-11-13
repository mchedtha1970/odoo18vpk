# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

PAYMENT_REQUEST_CODE = "payment_request"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    payment_request_ids = fields.One2many(
        comodel_name="vpk.document.studio.document",
        inverse_name="purchase_id",
        string="ใบขออนุมัติเบิกจ่าย",
        domain=[("document_type_code", "=", PAYMENT_REQUEST_CODE)],
    )
    payment_request_count = fields.Integer(
        string="จำนวนใบขออนุมัติเบิกจ่าย",
        compute="_compute_payment_request_count",
    )
    can_request_payment = fields.Boolean(
        string="ขออนุมัติเบิกจ่ายได้",
        compute="_compute_can_request_payment",
    )

    can_send_payment_to_ap = fields.Boolean(
        string="ส่งหน่วยงานเจ้าหนี้ได้",
        compute="_compute_can_send_payment_to_ap",
    )

    @api.depends("payment_request_ids.state", "payment_request_ids.payment_ap_forwarded_on")
    def _compute_can_send_payment_to_ap(self):
        for order in self:
            order.can_send_payment_to_ap = bool(order._vpk_payment_to_send())

    def _vpk_payment_to_send(self):
        self.ensure_one()
        return self.sudo().payment_request_ids.filtered(
            lambda doc: doc.state == "approved" and not doc.payment_ap_forwarded_on
        )

    def action_send_payment_to_ap(self):
        """ปุ่ม ส่งหน่วยงานเจ้าหนี้ บนใบสั่งซื้อ: ส่งทุกใบขอที่ลงนามครบแล้วและยังไม่ได้ส่ง."""
        self.ensure_one()
        docs = self._vpk_payment_to_send()
        if not docs:
            raise UserError(
                _("ไม่มีใบขออนุมัติเบิกจ่ายที่ลงนามครบและรอส่งหน่วยงานเจ้าหนี้")
            )
        docs.action_send_to_ap()
        return True

    @api.depends("payment_request_ids")
    def _compute_payment_request_count(self):
        for order in self:
            order.payment_request_count = len(order.sudo().payment_request_ids)

    @api.depends(
        "state",
        "wa_line_ids.wa_id.state",
        "invoice_ids.state",
        "payment_request_ids.state",
        "payment_request_ids.wa_id",
    )
    def _compute_can_request_payment(self):
        for order in self:
            order.can_request_payment = bool(
                order.state in ("purchase", "done") and order._vpk_payment_available_wa()
            )

    def _vpk_payment_available_wa(self):
        """ใบตรวจรับที่ยืนยันแล้ว ยังไม่ถูกใช้ตั้งเจ้าหนี้ และยังไม่มีใบขออนุมัติเบิกจ่าย."""
        self.ensure_one()
        if not self.id:
            return self.env["work.acceptance"]
        accepted = self.env["work.acceptance"].sudo()._get_valid_wa("invoice", self.id)
        covered = self.sudo().payment_request_ids.filtered(
            lambda doc: doc.state != "cancelled"
        ).mapped("wa_id")
        return accepted - covered

    def _vpk_check_can_request_payment(self):
        self.ensure_one()
        if self.state not in ("purchase", "done"):
            raise UserError(_("ขออนุมัติเบิกจ่ายได้เมื่อยืนยันใบสั่งซื้อแล้ว"))
        accepted = self.env["work.acceptance"].sudo().search(
            [("purchase_id", "=", self.id), ("state", "=", "accept")]
        )
        if not accepted:
            raise UserError(
                _(
                    "ยังไม่มีใบตรวจรับที่ยืนยันตรวจรับ "
                    "ขออนุมัติเบิกจ่ายได้หลังตรวจรับมอบงานเสร็จแล้วเท่านั้น"
                )
            )
        if not self._vpk_payment_available_wa():
            raise UserError(
                _(
                    "ใบตรวจรับที่ยืนยันแล้วทุกใบมีใบขออนุมัติเบิกจ่ายหรือถูกใช้ตั้งเจ้าหนี้แล้ว "
                    "ถ้าต้องการขอใหม่ให้ยกเลิกใบเดิมก่อน"
                )
            )
        return True

    def action_request_payment_approval(self):
        """ขออนุมัติเบิกจ่าย: เปิดวิซาร์ดเพิ่มเอกสารหลังตรวจรับเสร็จ."""
        self.ensure_one()
        self._vpk_check_can_request_payment()
        return self.env["vpk.payment.request.wizard"]._open_for(self)

    def action_view_payment_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบขออนุมัติเบิกจ่าย"),
            "res_model": "vpk.document.studio.document",
            "view_mode": "list,form",
            "domain": [
                ("purchase_id", "=", self.id),
                ("document_type_code", "=", PAYMENT_REQUEST_CODE),
            ],
        }
