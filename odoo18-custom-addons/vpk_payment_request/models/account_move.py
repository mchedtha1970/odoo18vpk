# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_request_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="ใบขออนุมัติเบิกจ่าย",
        copy=False,
        readonly=True,
        index=True,
        ondelete="set null",
    )

    @api.model
    def get_ap_bill_approval_dashboard(self):
        """Dashboard สำหรับบัญชี: แสดงรายการ Bill ที่ถูกส่งมาขออนุมัติตั้งเจ้าหนี้."""
        Move = self.sudo()
        since = fields.Date.context_today(self) - timedelta(days=30)
        bills = Move.search(
            [
                ("move_type", "in", ["in_invoice", "in_refund"]),
                ("state", "!=", "cancel"),
                ("review_ids", "!=", False),
            ],
            order="id desc",
            limit=500,
        )
        rows = []
        for bill in bills:
            val_status = getattr(bill, "validation_status", "") or ""
            if bill.state == "posted":
                if bill.invoice_date and bill.invoice_date < since and bill.write_date.date() < since:
                    continue
                stage = "posted"
                status_key = "posted"
                state_label = _("อนุมัติ / POST แล้ว")
            elif val_status in ("waiting", "pending"):
                stage = "pending"
                status_key = "wait_acc"
                state_label = _("รอบัญชีอนุมัติ")
            elif val_status == "validated":
                stage = "validated"
                status_key = "acc_approved"
                state_label = _("บัญชีอนุมัติ")
            elif val_status == "rejected":
                stage = "pending"
                status_key = "rejected"
                state_label = _("ไม่อนุมัติ")
            else:
                continue

            req = bill.payment_request_id
            po = req.purchase_id if req and req.purchase_id else self.env["purchase.order"]
            if not po and "purchase_id" in bill._fields and bill.purchase_id:
                po = bill.purchase_id
            if not po and bill.invoice_line_ids:
                po = bill.invoice_line_ids.purchase_line_id.order_id[:1]
            wa = req.wa_id if req and req.wa_id else self.env["work.acceptance"]

            pending_reviews = bill.review_ids.filtered(
                lambda r: r.status in ("pending", "waiting")
            ).sorted("sequence")
            done_reviews = bill.review_ids.filtered(
                lambda r: r.status == "approved"
            ).sorted("sequence")
            if pending_reviews:
                approver_names = ", ".join(
                    r.vpk_approver_user_id.name
                    or ", ".join(r.reviewer_ids.mapped("name"))
                    or r.name
                    for r in pending_reviews
                )
            elif done_reviews:
                approver_names = ", ".join(
                    (r.done_by.name or r.vpk_approver_user_id.name or r.name)
                    for r in done_reviews
                )
            else:
                approver_names = ""

            bill_label = (
                bill.name
                if bill.name and bill.name != "/"
                else _("ฉบับร่าง (#%s)") % bill.id
            )
            rows.append(
                {
                    "id": bill.id,
                    "name": bill_label,
                    "ref": bill.ref or "",
                    "state": stage,
                    "move_state": bill.state,
                    "status_key": status_key,
                    "state_label": state_label,
                    "validation_status": val_status,
                    "vendor": bill.partner_id.name or "",
                    "invoice_date": (
                        fields.Date.to_string(bill.invoice_date)
                        if bill.invoice_date
                        else ""
                    ),
                    "due_date": (
                        fields.Date.to_string(bill.invoice_date_due)
                        if bill.invoice_date_due
                        else ""
                    ),
                    "amount": bill.amount_total or 0.0,
                    "currency": bill.currency_id.name or "",
                    "request_id": req.id if req else False,
                    "request_name": (req.name or req.display_name) if req else "",
                    "po_id": po.id if po else False,
                    "po_name": po.name if po else (bill.invoice_origin or ""),
                    "wa_name": wa.name if wa else "",
                    "is_direct": not bool(req or po),
                    "approver_names": approver_names,
                    "can_approve": bool(
                        bill.state == "draft" and val_status in ("waiting", "pending")
                    ),
                    "can_post": bool(
                        bill.state == "draft" and val_status == "validated"
                    ),
                }
            )

        stage_defs = [
            (
                "pending",
                "รอบัญชีอนุมัติ",
                "ใบเรียกเก็บ (Bill) ที่ส่งมาขออนุมัติตั้งเจ้าหนี้",
                "warn",
            ),
            (
                "validated",
                "บัญชีอนุมัติ",
                "บัญชีอนุมัติแล้ว รอกดยืนยัน POST ลงบัญชี",
                "info",
            ),
            (
                "posted",
                "อนุมัติ / POST แล้ว",
                "อนุมัติและบันทึกลงรายการตั้งเจ้าหนี้แล้ว (30 วันล่าสุด)",
                "ok",
            ),
        ]
        kpis = []
        for key, label, hint, tone in stage_defs:
            items = [r for r in rows if r["state"] == key]
            kpis.append(
                {
                    "key": key,
                    "label": label,
                    "hint": hint,
                    "tone": tone,
                    "count": len(items),
                    "amount": sum(r["amount"] for r in items),
                }
            )
        return {
            "kpis": kpis,
            "rows": rows,
            "currency_symbol": self.env.company.currency_id.symbol or "฿",
        }

    def action_accounting_approve_bill(self):
        """อนุมัติตั้งเจ้าหนี้ (Bill) จาก Dashboard บัญชี."""
        self.ensure_one()
        bill = self.sudo()
        if bill.state != "draft":
            raise UserError(_("อนุมัติได้เฉพาะใบเรียกเก็บฉบับร่าง"))
        val_status = getattr(bill, "validation_status", "") or ""
        if val_status not in ("waiting", "pending"):
            raise UserError(_("ใบเรียกเก็บนี้ไม่ได้อยู่ในสถานะรออนุมัติ"))

        # หากผู้ใช้ปัจจุบันอยู่ในลำดับที่อนุมัติได้ ใช้ผู้ใช้ปัจจุบัน มิฉะนั้นอนุมัติในนามผู้อนุมัติลำดับปัจจุบัน
        if self.can_review:
            self.validate_tier()
        else:
            pending = bill.review_ids.filtered(
                lambda r: r.status in ("pending", "waiting")
            ).sorted("sequence")
            reviewer = (
                pending[:1].vpk_approver_user_id
                or pending[:1].reviewer_ids[:1]
                or self.env.user
            )
            self.with_user(reviewer).sudo().validate_tier()

        bill.invalidate_recordset(["validation_status"])
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("บัญชีอนุมัติแล้ว"),
                "message": _("อนุมัติใบเรียกเก็บ %s เรียบร้อย สถานะเปลี่ยนเป็น บัญชีอนุมัติ")
                % (bill.name if bill.name and bill.name != "/" else bill.display_name),
                "type": "success",
                "sticky": False,
            },
        }

    def action_accounting_reject_bill(self):
        """ไม่อนุมัติตั้งเจ้าหนี้ (Bill) จาก Dashboard บัญชี."""
        self.ensure_one()
        bill = self.sudo()
        if bill.state != "draft":
            raise UserError(_("ทำรายการได้เฉพาะใบเรียกเก็บฉบับร่าง"))
        if self.can_review:
            self.reject_tier()
        else:
            pending = bill.review_ids.filtered(
                lambda r: r.status in ("pending", "waiting")
            ).sorted("sequence")
            reviewer = (
                pending[:1].vpk_approver_user_id
                or pending[:1].reviewer_ids[:1]
                or self.env.user
            )
            self.with_user(reviewer).sudo().reject_tier()
        bill.invalidate_recordset(["validation_status"])
        return True

    def action_accounting_post_bill(self):
        """POST ใบเรียกเก็บที่บัญชีอนุมัติแล้วจาก Dashboard บัญชี."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("POST ได้เฉพาะใบเรียกเก็บฉบับร่าง"))
        val_status = getattr(self, "validation_status", "") or ""
        if val_status != "validated":
            raise UserError(_("ต้องผ่านการอนุมัติตั้งเจ้าหนี้ก่อนจึงจะ POST ได้"))
        self.action_post()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("POST ตั้งเจ้าหนี้แล้ว"),
                "message": _("บันทึกใบเรียกเก็บ %s เข้าบัญชีแยกประเภทเรียบร้อย")
                % (self.name or self.display_name),
                "type": "success",
                "sticky": False,
            },
        }
