# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    vpk_ref_bill_number = fields.Char(string="เลขที่ Bill", copy=False)
    vpk_ref_po_number = fields.Char(string="เลขที่ PO", copy=False)
    vpk_ref_wa_number = fields.Char(string="เลขที่ใบตรวจรับงาน", copy=False)
    vpk_ref_contract_number = fields.Char(
        string="เลขที่สัญญา (GF-ที่อ้างอิง)",
        copy=False,
        help="เลขที่สัญญา/ใบสั่งซื้อจากสัญญาที่ผูกใบเรียกเก็บ หรือค่าการอ้างอิงจากเอกสาร GFMIS/ขบ.",
    )
    vpk_payment_request_id = fields.Many2one(
        comodel_name="vpk.document.studio.document",
        string="ใบขออนุมัติเบิกจ่าย",
        copy=False,
        index=True,
        ondelete="set null",
    )
    vpk_source_bill_ids = fields.Many2many(
        comodel_name="account.move",
        relation="vpk_account_payment_source_bill_rel",
        column1="payment_id",
        column2="move_id",
        string="ใบเรียกเก็บต้นทาง",
        copy=False,
        help="ใบเรียกเก็บที่ดึงมาสร้างใบสำคัญจ่าย (ยังไม่ reconcile จนกว่าจะ POST)",
    )

    @api.model
    def get_payment_accounting_dashboard(self):
        """Dashboard รายการจ่ายชำระ รอบันทึกบัญชี (ภายใต้ระบบบัญชีแยกประเภท)."""
        payments = self.sudo().search(
            [
                ("payment_type", "=", "outbound"),
                ("vpk_payment_request_id", "!=", False),
                ("state", "=", "draft"),
            ],
            order="date asc, id asc",
            limit=500,
        )
        rows = []
        for pay in payments:
            request = pay.vpk_payment_request_id
            rows.append(
                {
                    "id": pay.id,
                    "name": pay.name or pay.display_name or "",
                    "date": fields.Date.to_string(pay.date) if pay.date else "",
                    "vendor": pay.partner_id.name or "",
                    "partner_id": pay.partner_id.id,
                    "amount": pay.amount or 0.0,
                    "currency": pay.currency_id.name or "",
                    "journal": pay.journal_id.display_name or "",
                    "method": pay.payment_method_line_id.name or "",
                    "bill_name": pay.vpk_ref_bill_number or "",
                    "po_name": pay.vpk_ref_po_number or "",
                    "wa_name": pay.vpk_ref_wa_number or "",
                    "contract_name": pay.vpk_ref_contract_number or "",
                    "request_id": request.id if request else False,
                    "request_name": (request.name or request.display_name) if request else "",
                    "validation_status": getattr(pay, "validation_status", "") or "",
                    "can_post": not bool(getattr(pay, "need_validation", False))
                    and (
                        not getattr(pay, "review_ids", False)
                        or not pay.review_ids
                        or (getattr(pay, "validation_status", "") or "") == "validated"
                    ),
                }
            )
        amount_total = sum(row["amount"] for row in rows)
        return {
            "kpis": [
                {
                    "key": "draft",
                    "label": "รอบันทึกบัญชี",
                    "hint": "รายการชำระเงินฉบับร่างจากยืนยันรายการจ่าย — ยังไม่ POST",
                    "tone": "warn",
                    "count": len(rows),
                    "amount": amount_total,
                },
            ],
            "rows": rows,
        }

    def action_accounting_post_payment(self):
        """บันทึกบัญชี (POST) จาก Dashboard รายการจ่ายชำระ รอบันทึกบัญชี."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("บันทึกบัญชีได้เฉพาะรายการชำระเงินที่เป็นร่าง"))
        self.action_post()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("บันทึกบัญชีแล้ว"),
                "message": _("บันทึกรายการชำระเงิน %s เรียบร้อย")
                % (self.name or self.display_name),
                "type": "success",
                "sticky": False,
            },
        }

    def action_post(self):
        """บัญชี POST ได้หลังผ่านการอนุมัติ tier (ถ้ามีการกำหนด)."""
        for payment in self:
            need_validation = bool(getattr(payment, "need_validation", False))
            review_ids = getattr(payment, "review_ids", False)
            validation_status = getattr(payment, "validation_status", "") or ""
            if need_validation or (
                review_ids and review_ids and validation_status != "validated"
            ):
                raise UserError(
                    _(
                        "ใบสำคัญจ่าย %s ต้องขออนุมัติและผ่านการอนุมัติครบก่อน "
                        "แผนกบัญชีจึงจะบันทึก POST ได้"
                    )
                    % (payment.name or payment.display_name)
                )
        res = super(
            AccountPayment,
            self.with_context(skip_validation_check=True),
        ).action_post()
        self._vpk_reconcile_source_bills()
        return res

    def _vpk_reconcile_source_bills(self):
        """หลัง POST ใบสำคัญจ่ายที่ดึงจาก Dashboard — reconcile กับใบเรียกเก็บต้นทาง."""
        for payment in self:
            bills = payment.vpk_source_bill_ids.filtered(
                lambda move: move.state == "posted"
                and move.payment_state not in ("paid", "in_payment")
            )
            if not bills or not payment.move_id:
                continue
            pay_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type
                in payment._get_valid_payment_account_types()
                and not line.reconciled
            )
            bill_lines = bills.line_ids.filtered(
                lambda line: line.account_id.account_type
                in payment._get_valid_payment_account_types()
                and not line.reconciled
                and line.parent_state == "posted"
            )
            for account in (pay_lines + bill_lines).account_id:
                lines = (pay_lines + bill_lines).filtered(
                    lambda line, acc=account: line.account_id == acc
                    and not line.reconciled
                )
                if len(lines) >= 2:
                    lines.reconcile()
            bill_lines.move_id.matched_payment_ids = [
                fields.Command.link(payment.id)
            ]