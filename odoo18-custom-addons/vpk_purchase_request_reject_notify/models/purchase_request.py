# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _get_reject_notify_partners(self):
        """ผู้รับการแจ้งเตือน: ผู้ขอ + ผู้จัดการกลุ่มงานที่ออก PR."""
        self.ensure_one()
        partners = self.env["res.partner"]
        if self.requested_by and self.requested_by.partner_id:
            partners |= self.requested_by.partner_id
        department = self.department_id
        if department and department.manager_id:
            manager = department.manager_id
            if manager.user_id and manager.user_id.partner_id:
                partners |= manager.user_id.partner_id
        return partners

    def _get_reject_reason_text(self):
        self.ensure_one()
        reviews = self.review_ids.filtered(lambda r: r.status == "rejected")
        comments = [
            (r.comment or "").strip()
            for r in reviews.sorted("sequence")
            if (r.comment or "").strip()
        ]
        if comments:
            return "\n".join(comments)
        return _("ไม่ระบุเหตุผล")

    def _notify_requesting_unit_rejected(self, reject_source="rejected"):
        """แจ้งเตือนกลุ่มงานที่ออกใบขอซื้อเมื่อ PR ไม่ผ่านอนุมัติ."""
        template = self.env.ref(
            "vpk_purchase_request_reject_notify.mail_template_pr_rejected",
            raise_if_not_found=False,
        )
        for request in self:
            partners = request._get_reject_notify_partners()
            if not partners:
                continue
            request.message_subscribe(partner_ids=partners.ids)
            reason = request._get_reject_reason_text()
            body = _(
                "<p><b>ใบขอซื้อ/จ้าง/เช่าไม่ได้รับการอนุมัติ</b></p>"
                "<ul>"
                "<li>เลขที่: %(name)s</li>"
                "<li>กลุ่มงาน/หน่วยงาน: %(dept)s</li>"
                "<li>ผู้ขอ: %(requestor)s</li>"
                "<li>เหตุผล: %(reason)s</li>"
                "</ul>"
                "<p>กรุณาตรวจสอบและแก้ไขรายการ หรือเปิดใบใหม่ตามความเหมาะสม</p>"
            ) % {
                "name": request.display_name,
                "dept": request.department_id.display_name
                if request.department_id
                else "-",
                "requestor": request.requested_by.display_name
                if request.requested_by
                else "-",
                "reason": reason,
            }
            subject = _("ใบขอซื้อ/จ้าง/เช่า %s ไม่ได้รับการอนุมัติ") % request.name
            # Inbox notification to requestor + department manager
            request.message_notify(
                partner_ids=partners.ids,
                body=body,
                subject=subject,
            )
            request.message_post(
                body=body,
                subtype_xmlid="purchase_request.mt_request_rejected",
                message_type="notification",
            )
            # Optional email template (single send to requestor)
            if template and request.requested_by and request.requested_by.email:
                template.send_mail(request.id, force_send=False)
            # กิจกรรมให้ผู้ขอ (ถ้ามี user)
            if request.requested_by:
                request.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=request.requested_by.id,
                    summary=_("PR ไม่ผ่านอนุมัติ — %s") % request.name,
                    note=_(
                        "ใบขอซื้อ/จ้าง/เช่า %(name)s ไม่ได้รับการอนุมัติ\n"
                        "หน่วยงาน: %(dept)s\nเหตุผล: %(reason)s"
                    )
                    % {
                        "name": request.name,
                        "dept": request.department_id.display_name
                        if request.department_id
                        else "-",
                        "reason": reason,
                    },
                )

    def button_rejected(self):
        res = super().button_rejected()
        if not self.env.context.get("skip_reject_notify"):
            self._notify_requesting_unit_rejected(reject_source="button_rejected")
        return res

    def _rejected_tier(self, tiers=False):
        res = super()._rejected_tier(tiers)
        # เมื่อ tier ไม่อนุมัติ → เปลี่ยนสถานะ rejected + แจ้งกลุ่มงานผู้ขอ
        to_reject = self.filtered(
            lambda r: r.validation_status == "rejected" and r.state != "rejected"
        )
        if to_reject:
            to_reject.with_context(skip_validation_check=True).button_rejected()
        return res
