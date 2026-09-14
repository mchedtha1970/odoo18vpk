# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    budget_commitment_active = fields.Boolean(
        string="ผูกพันงบประมาณแล้ว",
        compute="_compute_budget_commitment_active",
        store=True,
        help="PO ที่ยืนยันแล้วถือเป็นงบผูกพัน (ย้ายจากจอง PR)",
    )
    budget_committed_amount = fields.Monetary(
        string="งบผูกพันคงเหลือ",
        compute="_compute_budget_committed_amount",
        currency_field="currency_id",
        store=True,
    )

    @api.depends("state")
    def _compute_budget_commitment_active(self):
        for order in self:
            order.budget_commitment_active = order.state in ("purchase", "done")

    @api.depends(
        "budget_commitment_active",
        "order_line.budget_open_committed_amount",
        "order_line.price_subtotal",
        "order_line.qty_invoiced",
        "order_line.product_qty",
        "state",
    )
    def _compute_budget_committed_amount(self):
        for order in self:
            if not order.budget_commitment_active:
                order.budget_committed_amount = 0.0
            else:
                order.budget_committed_amount = sum(
                    order.order_line.mapped("budget_open_committed_amount")
                )

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        pr_lines = self.order_line.mapped("purchase_request_lines")
        if pr_lines:
            pr = pr_lines[:1].request_id
            if pr.budget_analytic_account_id:
                vals["budget_analytic_account_id"] = pr.budget_analytic_account_id.id
            if pr.budget_fund_source_id:
                vals["budget_fund_source_id"] = pr.budget_fund_source_id.id
        return vals

    def button_confirm(self):
        self._sync_budget_fields_from_purchase_request()
        self._check_budget_before_po_confirm()
        res = super().button_confirm()
        self._transfer_pr_reservation_to_po_commitment()
        return res

    def button_cancel(self):
        linked_requests = self.mapped(
            "order_line.purchase_request_lines.request_id"
        )
        res = super().button_cancel()
        linked_requests._restore_budget_reservation_after_po_change()
        return res

    def _sync_budget_fields_from_purchase_request(self):
        for order in self:
            for line in order.order_line:
                pr_lines = line.purchase_request_lines
                if not pr_lines:
                    continue
                pr_line = pr_lines[:1]
                vals = {}
                if pr_line.budget_line_id and line.budget_line_id != pr_line.budget_line_id:
                    vals["budget_line_id"] = pr_line.budget_line_id.id
                if pr_line.budget_post_id and line.budget_post_id != pr_line.budget_post_id:
                    vals["budget_post_id"] = pr_line.budget_post_id.id
                if vals:
                    line.with_context(skip_budget_check_reset=True).write(vals)

    def _check_budget_before_po_confirm(self):
        """Ensure budget still covers PO when confirming (PR reserve will move to commit)."""
        for order in self:
            lines = order.order_line.filtered(
                lambda line: line.budget_line_id or line.purchase_request_lines
            )
            if not lines:
                continue
            # Group by budget line
            by_budget = {}
            for line in lines:
                budget_line = line.budget_line_id
                if not budget_line and line.purchase_request_lines:
                    budget_line = line.purchase_request_lines[:1].budget_line_id
                if not budget_line:
                    continue
                by_budget.setdefault(budget_line, 0.0)
                by_budget[budget_line] += line._get_budget_line_amount_company()

            for budget_line, required in by_budget.items():
                # Available without this PO's future commit, but PR reserve of linked PRs
                # will be released — so add back linked PR effective reserve on same budget line
                linked_pr_lines = order.order_line.mapped("purchase_request_lines").filtered(
                    lambda prl, bl=budget_line: prl.budget_line_id == bl
                    and prl.request_id.budget_reservation_active
                )
                pr_release = sum(
                    prl._get_budget_effective_reserved_amount_company()
                    for prl in linked_pr_lines
                )
                available = (budget_line.pr_available_amount or 0.0) + pr_release
                # Also exclude this order from po committed if reconfirming
                other_po = self.env["purchase.order.line"].search(
                    [
                        ("budget_line_id", "=", budget_line.id),
                        ("order_id.budget_commitment_active", "=", True),
                        ("order_id", "!=", order.id),
                        ("state", "in", ("purchase", "done")),
                    ]
                )
                # pr_available already deducts PO commit if we update formula;
                # when confirming first time, add nothing. Re-check with explicit formula:
                planned = budget_line.planned_amount or 0.0
                actual = abs(budget_line.practical_amount or 0.0)
                pr_reserved = budget_line.pr_reserved_amount or 0.0
                # Remove linked PR reserve from reserved (will transfer)
                pr_reserved_adj = max(0.0, pr_reserved - pr_release)
                po_committed = sum(
                    pol._get_budget_open_committed_amount_company() for pol in other_po
                )
                available = planned - actual - pr_reserved_adj - po_committed
                if available + 1e-6 < required:
                    raise ValidationError(
                        _(
                            "งบประมาณไม่เพียงพอสำหรับยืนยันใบสั่งซื้อ %(po)s\n"
                            "รายการงบ: %(budget)s\n"
                            "คงเหลือ (หลังหักจอง/ผูกพันอื่น): %(available)s\n"
                            "ยอด PO ที่จะผูกพัน: %(required)s"
                        )
                        % {
                            "po": order.display_name,
                            "budget": budget_line.display_name,
                            "available": "{:,.2f}".format(available),
                            "required": "{:,.2f}".format(required),
                        }
                    )

    def _transfer_pr_reservation_to_po_commitment(self):
        """After confirm: PR จองของบรรทัดที่ถูกเปิด PO ถูกหัก และงบไปอยู่ที่ PO ผูกพัน."""
        requests = self.mapped("order_line.purchase_request_lines.request_id")
        for request in requests:
            request.message_post(
                body=_(
                    "ย้ายงบประมาณจากจอง PR ไปผูกพันที่ PO: %s"
                )
                % ", ".join(self.mapped("name"))
            )
            # If nothing left to reserve on this PR, clear reservation flag
            remaining = sum(
                line._get_budget_effective_reserved_amount_company()
                for line in request.line_ids.filtered(lambda line: not line.cancelled)
            )
            if request.budget_reservation_active and remaining <= 1e-6:
                request.with_context(skip_budget_check_reset=True).write(
                    {"budget_reservation_active": False}
                )
                request.message_post(
                    body=_("คืนค่าจอง PR ครบแล้ว (ย้ายไปผูกพันที่ใบสั่งซื้อทั้งหมด)")
                )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        copy=False,
        index=True,
    )
    budget_line_id = fields.Many2one(
        comodel_name="budget.lines",
        string="รายการงบประมาณที่ผูกพัน",
        copy=False,
        index=True,
    )
    budget_open_committed_amount = fields.Monetary(
        string="งบผูกพันคงเหลือ",
        compute="_compute_budget_open_committed_amount",
        currency_field="currency_id",
        store=True,
        help="ยอด PO ที่ยังไม่ได้ตั้งเจ้าหนี้ (ผูกพัน) — ลดลงเมื่อตั้งเจ้าหนี้/ใช้จริง",
    )

    @api.depends(
        "price_subtotal",
        "product_qty",
        "qty_invoiced",
        "order_id.state",
        "order_id.budget_commitment_active",
        "currency_id",
        "company_id",
        "date_order",
    )
    def _compute_budget_open_committed_amount(self):
        for line in self:
            if line.order_id.state not in ("purchase", "done"):
                line.budget_open_committed_amount = 0.0
                continue
            line.budget_open_committed_amount = line._get_budget_open_committed_amount_order_currency()

    def _get_budget_line_amount_company(self):
        """Full PO line untaxed amount in company currency (for confirm check)."""
        self.ensure_one()
        company = self.company_id or self.env.company
        currency = self.currency_id or company.currency_id
        return currency._convert(
            self.price_subtotal or 0.0,
            company.currency_id,
            company,
            self.date_order or fields.Date.context_today(self),
        )

    def _get_budget_open_committed_amount_order_currency(self):
        self.ensure_one()
        qty = self.product_qty or 0.0
        if qty <= 0:
            return 0.0
        invoiced = min(max(self.qty_invoiced or 0.0, 0.0), qty)
        open_ratio = (qty - invoiced) / qty
        return (self.price_subtotal or 0.0) * open_ratio

    def _get_budget_open_committed_amount_company(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        currency = self.currency_id or company.currency_id
        return currency._convert(
            self._get_budget_open_committed_amount_order_currency(),
            company.currency_id,
            company,
            self.date_order or fields.Date.context_today(self),
        )

    def _get_budget_confirmed_amount_company(self):
        """Full confirmed PO line amount (used to reduce PR reservation)."""
        self.ensure_one()
        if self.order_id.state not in ("purchase", "done"):
            return 0.0
        return self._get_budget_line_amount_company()

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        if self.budget_post_id:
            res["budget_post_id"] = self.budget_post_id.id
            accounts = self.budget_post_id.account_ids
            if accounts:
                res["account_id"] = accounts[:1].id
        if self.budget_line_id:
            res["budget_line_id"] = self.budget_line_id.id
        return res
