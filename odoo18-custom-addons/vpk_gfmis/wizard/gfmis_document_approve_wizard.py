# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

APPROVE_STATES = ("wait_approve_request", "wait_approve_pay")
STATE_LABELS = {
    "wait_approve_request": "รออนุมัติขอเบิก (อม.01)",
    "wait_approve_pay": "รออนุมัติสั่งจ่าย (อม.02)",
}


class GfmisDocumentApproveWizard(models.TransientModel):
    _name = "gfmis.document.approve.wizard"
    _description = "อนุมัติ / ไม่อนุมัติใบเบิกเงิน"

    document_ids = fields.Many2many(
        "gfmis.document",
        string="รายการที่เลือก",
        required=True,
    )
    document_count = fields.Integer(string="จำนวนรายการ", compute="_compute_approval_info")
    approval_state = fields.Char(compute="_compute_approval_info")
    approval_label = fields.Char(string="ขั้นตอนอนุมัติ", compute="_compute_approval_info")
    amount_total = fields.Monetary(
        string="ยอดสุทธิรวม",
        compute="_compute_approval_info",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_approval_info",
    )
    reject_reason = fields.Text(
        string="เหตุผลไม่อนุมัติ",
        help="จำเป็นเมื่อกดไม่อนุมัติ",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = list(self.env.context.get("active_ids") or [])
        active_id = self.env.context.get("active_id")
        if not active_ids and active_id:
            active_ids = [active_id]
        if "document_ids" in fields_list and active_ids and not res.get("document_ids"):
            docs = self.env["gfmis.document"].browse(active_ids).exists()
            self._vpk_check_same_approvable_state(docs)
            res["document_ids"] = [(6, 0, docs.ids)]
        return res

    @api.depends("document_ids", "document_ids.state", "document_ids.amount_net", "document_ids.currency_id")
    def _compute_approval_info(self):
        for wiz in self:
            docs = wiz.document_ids
            wiz.document_count = len(docs)
            states = set(docs.mapped("state"))
            state = next(iter(states)) if len(states) == 1 else False
            wiz.approval_state = state or False
            wiz.approval_label = STATE_LABELS.get(state, "") if state else ""
            wiz.currency_id = docs[:1].currency_id or self.env.company.currency_id
            wiz.amount_total = sum(docs.mapped("amount_net"))

    @api.model
    def _vpk_check_same_approvable_state(self, docs):
        if not docs:
            raise UserError(_("กรุณาเลือกรายการใบเบิกเงินอย่างน้อย 1 รายการ"))
        states = set(docs.mapped("state"))
        if len(states) != 1:
            labels = [
                dict(docs._fields["state"].selection).get(state, state)
                for state in sorted(states)
            ]
            raise UserError(
                _(
                    "เลือกรายการที่สถานะเดียวกันเท่านั้น\n"
                    "รายการที่เลือกมีสถานะปนกัน: %s"
                )
                % ", ".join(labels)
            )
        state = next(iter(states))
        if state not in APPROVE_STATES:
            raise UserError(
                _(
                    "อนุมัติ / ไม่อนุมัติ ได้เฉพาะรายการที่อยู่ในสถานะ "
                    "รออนุมัติขอเบิก (อม.01) หรือ รออนุมัติสั่งจ่าย (อม.02)\n"
                    "สถานะปัจจุบัน: %s"
                )
                % dict(docs._fields["state"].selection).get(state, state)
            )
        return state

    def action_approve(self):
        self.ensure_one()
        state = self._vpk_check_same_approvable_state(self.document_ids)
        if state == "wait_approve_request":
            self.document_ids.action_approve_request()
        else:
            self.document_ids.action_approve_pay()
        return {"type": "ir.actions.act_window_close"}

    def action_reject(self):
        self.ensure_one()
        state = self._vpk_check_same_approvable_state(self.document_ids)
        reason = (self.reject_reason or "").strip()
        if not reason:
            raise UserError(_("กรุณาระบุเหตุผลไม่อนุมัติ"))
        self.document_ids.action_reject_approval(reason=reason, from_state=state)
        return {"type": "ir.actions.act_window_close"}
