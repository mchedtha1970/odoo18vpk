# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    require_vendor_signature = fields.Boolean(
        string="ต้องการลายเซ็นผู้จำหน่าย",
        compute="_compute_require_vendor_signature",
        store=True,
        readonly=False,
        copy=False,
        help="เมื่อเปิด ผู้จำหน่ายต้องลงนามยืนยันบนพอร์ทัลก่อน Confirm PO",
    )
    signature = fields.Image(
        string="ลายเซ็นผู้จำหน่าย",
        copy=False,
        attachment=True,
        max_width=1024,
        max_height=1024,
    )
    signed_by = fields.Char(string="ลงนามโดย", copy=False)
    signed_on = fields.Datetime(string="วันที่ลงนาม", copy=False)
    vendor_signed = fields.Boolean(
        string="ผู้จำหน่ายลงนามแล้ว",
        compute="_compute_vendor_signed",
        store=True,
    )
    vendor_portal_url = fields.Char(
        string="ลิงก์เข้าพอร์ทัลผู้จำหน่าย",
        compute="_compute_vendor_portal_url",
        help="ลิงก์เอกสารพร้อม access token หรือใช้ /vendor สำหรับ login",
    )
    vendor_portal_login_url = fields.Char(
        string="ลิงก์ Login Vendor Portal",
        compute="_compute_vendor_portal_login_url",
    )

    @api.depends("requisition_id", "requisition_id.requisition_type")
    def _compute_require_vendor_signature(self):
        for order in self:
            order.require_vendor_signature = (
                order.requisition_id.requisition_type == "egp_procurement"
            )

    @api.depends("signature", "signed_by", "signed_on")
    def _compute_vendor_signed(self):
        for order in self:
            # Confirmed via portal even without drawn signature image
            order.vendor_signed = bool(order.signed_by and order.signed_on) or bool(
                order.signature
            )

    def _compute_vendor_portal_url(self):
        for order in self:
            if not order.id:
                order.vendor_portal_url = False
                continue
            order.vendor_portal_url = order.get_base_url().rstrip("/") + order.get_portal_url()

    def _compute_vendor_portal_login_url(self):
        for order in self:
            order.vendor_portal_login_url = (
                order.get_base_url().rstrip("/") + "/vendor"
            )

    def _is_egp_vendor_portal_order(self):
        self.ensure_one()
        return self.requisition_id.requisition_type == "egp_procurement"

    def _has_to_be_signed(self):
        """Legacy helper: documents that still need vendor confirmation."""
        return self._can_vendor_confirm()

    def _can_vendor_confirm(self):
        """Whether the vendor can confirm this RFQ/PO on the portal."""
        self.ensure_one()
        return (
            self.state in ("draft", "sent")
            and self.require_vendor_signature
            and bool(self.partner_id)
        )

    def _approval_allowed(self):
        if self.env.context.get("portal_vendor_confirm"):
            return True
        return super()._approval_allowed()

    def action_portal_vendor_confirm(self, name=None, signature=None):
        """Confirm the purchase order from Vendor Portal (signature optional)."""
        self.ensure_one()
        if not self._can_vendor_confirm():
            raise UserError(_("เอกสารนี้ไม่ได้อยู่ในสถานะที่ต้องให้ผู้จำหน่ายยืนยัน"))

        vals = {
            "signed_by": name or self.partner_id.name,
            "signed_on": fields.Datetime.now(),
            "mail_reception_confirmed": True,
            "mail_reception_declined": False,
        }
        if signature:
            vals["signature"] = signature
        if self.state == "draft":
            vals["state"] = "sent"
        self.write(vals)
        self.with_context(portal_vendor_confirm=True).button_confirm()
        return True

    def action_portal_vendor_decline(self, decline_message=None):
        """Vendor declines the RFQ from the portal."""
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            raise UserError(_("ไม่สามารถปฏิเสธเอกสารในสถานะนี้ได้"))
        self.write(
            {
                "mail_reception_declined": True,
                "mail_reception_confirmed": False,
            }
        )
        body = _("ผู้จำหน่ายปฏิเสธการยืนยันเอกสารบนพอร์ทัล")
        if decline_message:
            body = "%s:<br/>%s" % (body, decline_message)
        self.message_post(body=body)
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=self.user_id.id or self.env.user.id,
            note=_(
                "ผู้จำหน่ายปฏิเสธ RFQ/PO %(name)s ผ่านพอร์ทัล หากเห็นชอบให้ยกเลิกเอกสารนี้",
                name=self.name,
            ),
        )
        return True

    def action_invite_vendor_portal(self):
        """Open wizard to set email/login/password for vendor portal user."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("กรุณาระบุผู้จำหน่ายก่อน"))
        return {
            "type": "ir.actions.act_window",
            "name": _("สร้าง User Portal ผู้จำหน่าย"),
            "res_model": "vendor.portal.user.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.partner_id.commercial_partner_id.id,
                "active_id": self.partner_id.commercial_partner_id.id,
            },
        }

    def action_send_vendor_sign_request(self):
        """Send email inviting the vendor to sign/confirm on the portal."""
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(
                _("ผู้จำหน่าย %(vendor)s ยังไม่มีอีเมล", vendor=self.partner_id.display_name)
            )
        if self.state == "draft":
            self.write({"state": "sent"})
        self._portal_ensure_token()
        template = self.env.ref(
            "vpk_purchase_portal_egp.mail_template_purchase_vendor_sign",
            raise_if_not_found=False,
        )
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", raise_if_not_found=False)
        ctx = {
            "default_model": "purchase.order",
            "default_res_ids": self.ids,
            "default_composition_mode": "comment",
            "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
            "force_email": True,
            "mark_rfq_as_sent": True,
        }
        if template:
            ctx["default_template_id"] = template.id
        return {
            "name": _("ส่งคำขอยืนยัน/ลงนามให้ผู้จำหน่าย"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id if compose_form else False, "form")],
            "view_id": compose_form.id if compose_form else False,
            "target": "new",
            "context": ctx,
        }

    def action_preview_vendor_portal(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": self.vendor_portal_url or (
                self.get_base_url().rstrip("/") + self.get_portal_url()
            ),
        }

    def action_share_vendor_portal(self):
        """Open standard portal share wizard with vendor portal link."""
        self.ensure_one()
        self._portal_ensure_token()
        return self.with_context(
            active_id=self.id,
            active_model=self._name,
            default_partner_ids=[(6, 0, self.partner_id.ids)] if self.partner_id else [],
        ).action_share()
