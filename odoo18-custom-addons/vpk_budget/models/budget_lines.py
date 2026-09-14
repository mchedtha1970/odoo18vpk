from odoo import api, fields, models


class BudgetLines(models.Model):
    _inherit = "budget.lines"

    budget_id = fields.Many2one(string="Budget")
    analytic_account_id = fields.Many2one(string="Analytic Account")
    planned_amount = fields.Float(string="Planned Amount")
    practical_amount = fields.Float(
        compute="_compute_practical_amount",
        string="Practical Amount",
        digits=0,
    )
    theoretical_amount = fields.Float(
        compute="_compute_theoretical_amount",
        string="Theoretical Amount",
        digits=0,
    )
    percentage = fields.Float(
        compute="_compute_percentage",
        string="Achievement",
    )
    request_id = fields.Many2one(
        comodel_name="departmental.budget.request",
        string="Budget Request",
        index=True,
        readonly=True,
    )
    request_line_id = fields.Many2one(
        comodel_name="departmental.budget.request.line",
        string="Budget Request Line",
        index=True,
        readonly=True,
    )
    fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="Fund Source",
    )
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        string="กลุ่มงบประมาณ",
        index=True,
    )
    material_sub_type_id = fields.Many2one(
        comodel_name="vpk.budget.material.sub.type",
        string="ประเภทวัสดุ",
        index=True,
    )
    requested_amount = fields.Float(string="Requested Amount", digits=0)
    pr_reserved_amount = fields.Float(
        string="งบ PR ที่จอง",
        compute="_compute_pr_budget_amounts",
        digits=0,
    )
    po_committed_amount = fields.Float(
        string="งบ PO ที่ผูกพัน",
        compute="_compute_pr_budget_amounts",
        digits=0,
        help="ยอดใบสั่งซื้อที่ยืนยันแล้วและยังไม่ได้ตั้งเจ้าหนี้",
    )
    pr_available_amount = fields.Float(
        string="งบคงเหลือหลังจอง/ผูกพัน",
        compute="_compute_pr_budget_amounts",
        digits=0,
    )

    def _compute_pr_budget_amounts(self):
        purchase_request_line = self.env["purchase.request.line"]
        purchase_order_line = self.env["purchase.order.line"]
        for line in self:
            reserved = 0.0
            pr_lines = purchase_request_line.sudo().search(
                [
                    ("budget_line_id", "=", line.id),
                    ("request_id.budget_reservation_active", "=", True),
                    ("cancelled", "=", False),
                ]
            )
            for pr_line in pr_lines:
                reserved += pr_line._get_budget_effective_reserved_amount_company()

            committed = 0.0
            po_lines = purchase_order_line.sudo().search(
                [
                    ("budget_line_id", "=", line.id),
                    ("order_id.state", "in", ("purchase", "done")),
                    ("state", "in", ("purchase", "done")),
                ]
            )
            for po_line in po_lines:
                committed += po_line._get_budget_open_committed_amount_company()

            actual = (
                abs(line.practical_amount or 0.0)
                if line.practical_amount < 0
                else (line.practical_amount or 0.0)
            )
            line.pr_reserved_amount = reserved
            line.po_committed_amount = committed
            line.pr_available_amount = (line.planned_amount or 0.0) - actual - reserved - committed

    @api.depends(
        "analytic_account_id",
        "general_budget_id",
        "general_budget_id.account_ids",
        "date_from",
        "date_to",
    )
    def _get_analytic_column(self, analytic_account):
        """Return the column name in account_analytic_line for this account's plan."""
        if not analytic_account or not analytic_account.plan_id:
            return "account_id"
        return analytic_account.plan_id._column_name()

    def _compute_practical_amount(self):
        for line in self:
            if not line.general_budget_id or not line.date_from or not line.date_to:
                line.practical_amount = 0.0
                continue
            result = 0.0
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = self.env.context.get("wizard_date_to") or line.date_to
            date_from = self.env.context.get("wizard_date_from") or line.date_from
            if line.analytic_account_id and acc_ids:
                col = self._get_analytic_column(line.analytic_account_id)
                query = """
                    SELECT SUM(amount)
                    FROM account_analytic_line
                    WHERE {col} = %s
                        AND date BETWEEN %s AND %s
                        AND general_account_id = ANY(%s)
                """.format(col=col)
                params = (
                    line.analytic_account_id.id,
                    date_from,
                    date_to,
                    "{" + ",".join(map(str, acc_ids)) + "}",
                )
                self.env.cr.execute(query, params)
                result = -(self.env.cr.fetchone()[0] or 0.0)
            line.practical_amount = result

    @api.depends("planned_amount", "date_from", "date_to", "paid_date", "practical_amount")
    def _compute_theoretical_amount(self):
        today = fields.Datetime.now()
        for line in self:
            if not line.date_from or not line.date_to:
                line.theoretical_amount = 0.0
                continue

            if self.env.context.get("wizard_date_from") and self.env.context.get(
                "wizard_date_to"
            ):
                date_from = fields.Datetime.from_string(
                    self.env.context.get("wizard_date_from")
                )
                date_to = fields.Datetime.from_string(
                    self.env.context.get("wizard_date_to")
                )
                if date_from < fields.Datetime.from_string(line.date_from):
                    date_from = fields.Datetime.from_string(line.date_from)
                elif date_from > fields.Datetime.from_string(line.date_to):
                    date_from = False

                if date_to > fields.Datetime.from_string(line.date_to):
                    date_to = fields.Datetime.from_string(line.date_to)
                elif date_to < fields.Datetime.from_string(line.date_from):
                    date_to = False

                theo_amt = 0.0
                if date_from and date_to:
                    line_timedelta = fields.Datetime.from_string(
                        line.date_to
                    ) - fields.Datetime.from_string(line.date_from)
                    elapsed_timedelta = date_to - date_from
                    if elapsed_timedelta.days > 0 and line_timedelta.total_seconds():
                        theo_amt = (
                            elapsed_timedelta.total_seconds()
                            / line_timedelta.total_seconds()
                        ) * line.planned_amount
            elif line.paid_date:
                if fields.Datetime.from_string(line.date_to) <= fields.Datetime.from_string(
                    line.paid_date
                ):
                    theo_amt = 0.0
                else:
                    theo_amt = line.planned_amount
            else:
                line_timedelta = fields.Datetime.from_string(
                    line.date_to
                ) - fields.Datetime.from_string(line.date_from)
                elapsed_timedelta = fields.Datetime.from_string(today) - (
                    fields.Datetime.from_string(line.date_from)
                )
                if elapsed_timedelta.days < 0:
                    theo_amt = 0.0
                elif (
                    line_timedelta.days > 0
                    and fields.Datetime.from_string(today)
                    < fields.Datetime.from_string(line.date_to)
                ):
                    total_days = (line.date_to - line.date_from).days + 1
                    days_over = (fields.Date.today() - line.date_from).days + 1
                    theo_amt = line.planned_amount / total_days * days_over
                else:
                    theo_amt = line.planned_amount
            line.theoretical_amount = theo_amt

    @api.depends("practical_amount", "theoretical_amount")
    def _compute_percentage(self):
        for line in self:
            if line.theoretical_amount:
                line.percentage = (
                    float((line.practical_amount or 0.0) / line.theoretical_amount) * 100
                )
            else:
                line.percentage = 0.0
