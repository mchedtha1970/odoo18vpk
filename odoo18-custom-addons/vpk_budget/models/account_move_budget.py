# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    budget_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานงบประมาณ",
        copy=False,
        tracking=True,
    )
    budget_fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="แหล่งเงิน",
        copy=False,
        tracking=True,
    )

    def _vpk_budget_touch_purchase_lines(self):
        """Recompute PO open commitment after vendor bill post/cancel.

        ตั้งเจ้าหนี้ → qty_invoiced เพิ่ม → งบผูกพัน PO ลด และใช้จริงมาจาก analytic.
        """
        PurchaseLine = self.env["purchase.order.line"]
        po_lines = PurchaseLine.browse()
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                continue
            for line in move.line_ids:
                if line.purchase_line_id:
                    po_lines |= line.purchase_line_id
        if po_lines:
            po_lines._compute_budget_open_committed_amount()
            po_lines.mapped("order_id")._compute_budget_committed_amount()

    def _vpk_sync_budget_from_po(self):
        """Pull budget header fields from the linked PO's PR."""
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                continue
            po_lines = move.line_ids.mapped("purchase_line_id")
            if not po_lines:
                continue
            pr_lines = po_lines.mapped("purchase_request_lines")
            if not pr_lines:
                continue
            pr = pr_lines[:1].request_id
            vals = {}
            if pr.budget_analytic_account_id and not move.budget_analytic_account_id:
                vals["budget_analytic_account_id"] = pr.budget_analytic_account_id.id
            if pr.budget_fund_source_id and not move.budget_fund_source_id:
                vals["budget_fund_source_id"] = pr.budget_fund_source_id.id
            if vals:
                move.write(vals)

    def action_post(self):
        self._vpk_sync_budget_from_po()
        res = super().action_post()
        self._vpk_budget_touch_purchase_lines()
        return res

    def button_draft(self):
        res = super().button_draft()
        self._vpk_budget_touch_purchase_lines()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._vpk_budget_touch_purchase_lines()
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        copy=False,
        index=True,
    )
    budget_line_id = fields.Many2one(
        comodel_name="budget.lines",
        string="รายการงบประมาณ",
        copy=False,
        index=True,
    )

    @api.onchange("budget_post_id")
    def _onchange_budget_post_id_set_account(self):
        for line in self:
            if not line.budget_post_id:
                continue
            accounts = line.budget_post_id.account_ids
            if accounts and line.account_id not in accounts:
                line.account_id = accounts[:1]
