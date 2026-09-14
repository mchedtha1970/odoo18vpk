# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Allowed after tier approval so PR can continue procurement (RFQ, PO, done).
WORKFLOW_AFTER_VALIDATION_FIELDS = [
    "state",
    "substate_id",
]


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
    _state_from = ["draft", "sent_to_procurement"]

    state = fields.Selection(
        selection_add=[
            ("sent_to_procurement", "ส่งพัสดุแล้ว"),
            ("to_approve",),
        ],
        ondelete={"sent_to_procurement": "set default"},
    )
    tier_approver_names = fields.Char(
        string="Approvers",
        compute="_compute_tier_approver_names",
        help="Approver name for every approved tier, in sequence (duplicates kept).",
    )

    @api.depends(
        "review_ids.status",
        "review_ids.done_by",
        "review_ids.sequence",
    )
    def _compute_tier_approver_names(self):
        for rec in self:
            names = []
            for review in rec.review_ids.sorted("sequence"):
                if review.status == "approved" and review.done_by:
                    names.append(review.done_by.display_name)
            rec.tier_approver_names = " → ".join(names) if names else False

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        return list(set(res + WORKFLOW_AFTER_VALIDATION_FIELDS))

    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers)
        self._vpk_auto_confirm_if_validated()
        return res

    def _vpk_auto_confirm_if_validated(self):
        """Confirm PR automatically once every tier review is approved."""
        self.ensure_one()
        self.invalidate_recordset(["validation_status", "validated"])
        if self.validation_status != "validated":
            return
        if self.state not in ("draft", "to_approve", "sent_to_procurement"):
            return
        # Keep acting user for approved_by; sudo only for ACL on confirm.
        self.sudo().with_user(self.env.user).button_approved()

    def button_approved(self):
        return super(
            PurchaseRequest, self.with_context(skip_validation_check=True)
        ).button_approved()

    def _compute_need_validation(self):
        """ขออนุมัติได้หลังหน่วยงานกดส่งพัสดุแล้วเท่านั้น"""
        super()._compute_need_validation()
        for rec in self:
            if rec.state == "draft":
                rec.need_validation = False

    def action_send_to_procurement(self):
        """หน่วยงานส่งใบขอซื้อให้พัสดุ เปลี่ยนสถานะเป็น ส่งพัสดุแล้ว"""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("ส่งพัสดุได้เฉพาะใบขอซื้อสถานะร่าง"))
            active_lines = rec.line_ids.filtered(
                lambda line: not line.cancelled and line.product_qty
            )
            if not active_lines:
                raise UserError(_("กรุณาเพิ่มรายการสินค้าก่อนส่งพัสดุ"))
            if (
                "budget_check_state" in rec._fields
                and rec.budget_check_state != "enough"
            ):
                raise UserError(_("กรุณาเช็คงบประมาณให้ผ่านก่อนส่งพัสดุ"))
        self.write({"state": "sent_to_procurement"})
        for rec in self:
            rec._vpk_subscribe_procurement_users()
            rec.message_post(body=_("หน่วยงานส่งใบขอซื้อให้พัสดุแล้ว"))
        return True

    def _vpk_subscribe_procurement_users(self):
        """ให้เจ้าหน้าที่พัสดุติดตามใบขอซื้อ เพื่อเห็นรายการและได้รับการแจ้งเตือน"""
        self.ensure_one()
        users = self.env["res.users"]
        for xmlid in (
            "purchase_request.group_purchase_request_manager",
            "vpk_tier_validation.group_vpk_procurement_officer",
        ):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                users |= group.users
        users = users.filtered(lambda user: user.active and not user.share)
        partners = users.mapped("partner_id") - self.env.user.partner_id
        if partners:
            self.message_subscribe(partner_ids=partners.ids)
