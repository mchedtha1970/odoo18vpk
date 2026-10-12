from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


# งบจะถูกจองเมื่อเช็คงบผ่าน หรือเมื่อส่งขออนุมัติ (budget_reservation_active=True)
# จนกว่าจะยกเลิก/เสร็จสิ้น


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    budget_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานที่ขอซื้อ",
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    budget_fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="แหล่งเงิน",
        tracking=True,
    )
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        string="กลุ่มงบประมาณ",
        tracking=True,
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        tracking=True,
        domain="[('company_id', '=', company_id)]",
    )
    budget_section_key = fields.Selection(
        selection=[
            ("material", "วัสดุ"),
            ("asset", "ครุภัณฑ์"),
            ("project", "โครงการ"),
            ("construction", "ก่อสร้าง"),
        ],
        string="ประเภทสิ่งที่จะซื้อ",
        tracking=True,
        help="วัสดุ / ครุภัณฑ์ / โครงการ / ก่อสร้าง ตามหมวดงบประมาณ",
    )
    # Deprecated: kept for DB compatibility after switching to budget_section_key
    budget_form_type_id = fields.Many2one(
        comodel_name="vpk.budget.request.form.type",
        string="แบบฟอร์มคำของบ (เดิม)",
        tracking=False,
    )
    budget_check_state = fields.Selection(
        selection=[
            ("unchecked", "ยังไม่ได้เช็ค"),
            ("enough", "งบเพียงพอ"),
            ("insufficient", "งบไม่เพียงพอ"),
        ],
        string="สถานะเช็คงบ",
        default="unchecked",
        copy=False,
        tracking=True,
    )
    budget_check_date = fields.Datetime(
        string="วันที่เช็คงบล่าสุด",
        readonly=True,
        copy=False,
    )
    budget_check_message = fields.Text(
        string="ผลการเช็คงบ",
        readonly=True,
        copy=False,
    )
    budget_check_line_ids = fields.One2many(
        comodel_name="purchase.request.budget.check.line",
        inverse_name="request_id",
        string="ตารางผลการเช็คงบ",
        copy=False,
    )
    budget_check_by_product = fields.Boolean(
        compute="_compute_budget_check_by_product",
    )
    budget_requested_amount = fields.Monetary(
        string="งบประมาณที่จอง",
        compute="_compute_budget_requested_amount",
        currency_field="currency_id",
        store=True,
    )
    budget_available_amount = fields.Monetary(
        string="งบคงเหลือหลังหัก PR นี้",
        currency_field="currency_id",
        readonly=True,
        copy=False,
    )
    budget_reservation_active = fields.Boolean(
        string="จองงบประมาณแล้ว",
        default=False,
        copy=False,
        tracking=True,
        help="เปิดใช้เมื่อส่งขออนุมัติ PR เพื่อกันวงเงินจาก PR อื่นที่อยู่ระหว่างอนุมัติ",
    )

    @api.depends("budget_check_line_ids.check_mode")
    def _compute_budget_check_by_product(self):
        for request in self:
            request.budget_check_by_product = any(
                line.check_mode == "product" for line in request.budget_check_line_ids
            )

    @api.depends("line_ids.budget_reserved_amount", "line_ids.estimated_cost", "line_ids.cancelled")
    def _compute_budget_requested_amount(self):
        for request in self:
            request.budget_requested_amount = sum(
                line.budget_reserved_amount or line.estimated_cost or 0.0
                for line in request.line_ids.filtered(
                    lambda line: not line.cancelled
                )
            )

    def _apply_header_budget_post_to_line(self, line):
        """Copy header หมวดงบประมาณ onto a PR line and rematch the budget line."""
        self.ensure_one()
        if not self.budget_post_id or line.cancelled:
            return
        line.budget_post_id = self.budget_post_id
        matches = self._get_matching_budget_lines(self.budget_post_id)
        if "allowed_budget_line_ids" in line._fields:
            line.allowed_budget_line_ids = matches
        if line.budget_line_id and line.budget_line_id not in matches:
            line.budget_line_id = False
        if not line.budget_line_id and len(matches) == 1:
            line.budget_line_id = matches

    def _sync_line_budget_posts_from_header(self):
        """Overwrite หมวดงบประมาณ on every active line from the saved header."""
        for request in self:
            if not request.budget_post_id:
                continue
            lines = request.line_ids.filtered(lambda line: not line.cancelled)
            for line in lines:
                vals = {}
                if line.budget_post_id != request.budget_post_id:
                    vals["budget_post_id"] = request.budget_post_id.id
                matches = request._get_matching_budget_lines(request.budget_post_id)
                budget_line = line.budget_line_id
                if "budget_post_id" in vals or (
                    budget_line and budget_line not in matches
                ):
                    if budget_line and budget_line not in matches:
                        vals["budget_line_id"] = False
                        budget_line = False
                if not budget_line and not vals.get("budget_line_id") and len(matches) == 1:
                    vals["budget_line_id"] = matches.id
                if vals:
                    line.with_context(skip_budget_line_sync=True).write(vals)

    @api.onchange("budget_post_id")
    def _onchange_budget_post_header_sync_lines(self):
        """Set budget_post_id on every active PR line when header budget post changes."""
        if not self.budget_post_id:
            return
        for line in self.line_ids.filtered(lambda line: not line.cancelled):
            self._apply_header_budget_post_to_line(line)

    @api.onchange("budget_analytic_account_id", "budget_fund_source_id", "budget_group_id")
    def _onchange_budget_header_sync_lines(self):
        """Re-match budget_line_id on every PR line when header budget keys change."""
        for line in self.line_ids.filtered(lambda l: not l.cancelled and l.budget_post_id):
            matches = self._get_matching_budget_lines(line.budget_post_id)
            line.allowed_budget_line_ids = matches
            if line.budget_line_id and line.budget_line_id not in matches:
                line.budget_line_id = False
            if not line.budget_line_id and len(matches) == 1:
                line.budget_line_id = matches

    @api.onchange("budget_section_key")
    def _onchange_budget_section_key(self):
        """Clear material group when not purchasing supplies/material."""
        if self.budget_section_key and self.budget_section_key != "material":
            self.budget_group_id = False

    @api.depends("state", "budget_check_state")
    def _compute_hide_reviews(self):
        super()._compute_hide_reviews()
        for request in self:
            if request.state == "draft" and request.budget_check_state != "enough":
                request.hide_reviews = True

    def write(self, vals):
        reset_fields = {
            "budget_analytic_account_id",
            "budget_fund_source_id",
            "budget_group_id",
            "budget_section_key",
            "budget_post_id",
            "line_ids",
        }
        res = super().write(vals)
        if "budget_check_message" in vals:
            self.budget_check_line_ids.unlink()
        if (
            vals.get("budget_post_id")
            and not self.env.context.get("skip_budget_line_sync")
        ):
            self.filtered(lambda request: request.state == "draft")._sync_line_budget_posts_from_header()
        if reset_fields.intersection(vals) and not self.env.context.get(
            "skip_budget_check_reset"
        ):
            draft_requests = self.filtered(lambda request: request.state == "draft")
            if draft_requests:
                draft_requests.with_context(skip_budget_check_reset=True).write(
                    {
                        "budget_check_state": "unchecked",
                        "budget_check_message": False,
                        "budget_available_amount": 0.0,
                    }
                )
        return res

    def _requires_budget_group(self):
        """กลุ่มงบประมาณ (วัสดุ) ใช้เฉพาะเมื่อประเภทสิ่งที่จะซื้อเป็นวัสดุ."""
        self.ensure_one()
        return self.budget_section_key == "material"

    def _format_budget_amount(self, amount):
        self.ensure_one()
        currency = self.company_id.currency_id or self.currency_id
        amount_text = "{:,.2f}".format(amount or 0.0)
        if currency.symbol:
            if currency.position == "before":
                return "{}{}".format(currency.symbol, amount_text)
            return "{} {}".format(amount_text, currency.symbol)
        return amount_text

    def _get_active_budget_request_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: not line.cancelled)

    def _get_budget_line_domain(self, budget_post):
        self.ensure_one()
        domain = [
            ("analytic_account_id", "=", self.budget_analytic_account_id.id),
            ("general_budget_id", "=", budget_post.id),
            ("fund_source_id", "=", self.budget_fund_source_id.id),
            "|",
            ("budget_id.state", "in", ("validate", "done")),
            ("request_id.state", "=", "approved"),
        ]
        if self._requires_budget_group():
            domain.append(("budget_group_id", "=", self.budget_group_id.id))
        check_date = self.date_start or fields.Date.context_today(self)
        if check_date:
            domain += [("date_from", "<=", check_date), ("date_to", ">=", check_date)]
        return domain

    def _get_matching_budget_lines(self, budget_post):
        self.ensure_one()
        if (
            not self.budget_analytic_account_id
            or not self.budget_fund_source_id
            or not budget_post
        ):
            return self.env["budget.lines"]
        if self._requires_budget_group() and not self.budget_group_id:
            return self.env["budget.lines"]
        return self.env["budget.lines"].search(self._get_budget_line_domain(budget_post))

    def _budget_keys_match_group(self, other_group):
        """Compare budget groups only when this PR is material."""
        self.ensure_one()
        if not self._requires_budget_group():
            return True
        return other_group == self.budget_group_id

    def _get_other_pr_reserved_amount(self, budget_post):
        self.ensure_one()
        current_line_ids = self.line_ids.ids
        domain = [
            ("id", "not in", current_line_ids),
            ("request_id.budget_reservation_active", "=", True),
            ("cancelled", "=", False),
            ("budget_analytic_account_id", "=", self.budget_analytic_account_id.id),
            ("budget_fund_source_id", "=", self.budget_fund_source_id.id),
            ("budget_post_id", "=", budget_post.id),
        ]
        if self._requires_budget_group():
            domain.append(("budget_group_id", "=", self.budget_group_id.id))
        amount = 0.0
        for line in self.env["purchase.request.line"].sudo().search(domain):
            amount += line._get_budget_effective_reserved_amount_company()
        return amount

    def _get_other_po_committed_amount(self, budget_post):
        """Open PO commitment on matching budget keys (exclude nothing by default)."""
        self.ensure_one()
        domain = [
            ("order_id.state", "in", ("purchase", "done")),
            ("budget_post_id", "=", budget_post.id),
            ("state", "in", ("purchase", "done")),
        ]
        # Prefer lines linked to same analytic/fund/group via budget_line
        amount = 0.0
        for po_line in self.env["purchase.order.line"].sudo().search(domain):
            budget_line = po_line.budget_line_id
            if budget_line:
                if (
                    budget_line.analytic_account_id != self.budget_analytic_account_id
                    or budget_line.fund_source_id != self.budget_fund_source_id
                    or not self._budget_keys_match_group(budget_line.budget_group_id)
                ):
                    continue
            else:
                pr_lines = po_line.purchase_request_lines
                if not pr_lines:
                    continue
                if not any(
                    prl.budget_analytic_account_id == self.budget_analytic_account_id
                    and prl.budget_fund_source_id == self.budget_fund_source_id
                    and self._budget_keys_match_group(prl.budget_group_id)
                    for prl in pr_lines
                ):
                    continue
            amount += po_line._get_budget_open_committed_amount_company()
        return amount

    def _restore_budget_reservation_after_po_change(self):
        """Re-activate PR reservation when covering confirmed POs are cancelled."""
        for request in self:
            if request.state not in ("to_approve", "approved", "in_progress"):
                continue
            if request.budget_check_state != "enough":
                continue
            remaining = sum(
                line._get_budget_effective_reserved_amount_company()
                for line in request.line_ids.filtered(lambda line: not line.cancelled)
            )
            if remaining <= 1e-6:
                if request.budget_reservation_active:
                    request.with_context(skip_budget_check_reset=True).write(
                        {"budget_reservation_active": False}
                    )
                continue
            # Still have uncovered reserved amount → keep/reactivate reservation
            line_vals_needed = False
            for line in request.line_ids.filtered(lambda line: not line.cancelled):
                if not line.budget_line_id and line.budget_post_id:
                    matches = request._get_matching_budget_lines(line.budget_post_id)
                    if matches:
                        line.with_context(skip_budget_check_reset=True).write(
                            {"budget_line_id": matches[:1].id}
                        )
                        line_vals_needed = True
            if not request.budget_reservation_active:
                request.with_context(skip_budget_check_reset=True).write(
                    {"budget_reservation_active": True}
                )
                request.message_post(
                    body=_("คืนสถานะจองงบ PR หลังยกเลิก/ลดใบสั่งซื้อที่เกี่ยวข้อง")
                )
            elif line_vals_needed:
                request.message_post(
                    body=_("ปรับรายการงบที่จองของ PR หลังเปลี่ยนแปลงใบสั่งซื้อ")
                )
    def _uses_product_allocation_check(self):
        """วัสดุ/ครุภัณฑ์ เช็คงบจากยอดจัดสรรของสินค้า ไม่ใช้ก้อนหมวดทั้งก้อน."""
        self.ensure_one()
        return self.budget_section_key in ("material", "asset")

    def _allocation_check_date(self):
        self.ensure_one()
        return self.date_start or fields.Date.context_today(self)

    def _get_product_allocated_amount(self, product):
        """ยอดที่จัดสรรให้สินค้านี้ในคำของบที่อนุมัติแล้ว ของหน่วยงาน/แหล่งเงิน/ปีเดียวกัน."""
        self.ensure_one()
        if (
            not product
            or not self.budget_analytic_account_id
            or not self.budget_fund_source_id
        ):
            return 0.0
        check_date = self._allocation_check_date()
        request_domain = [
            ("request_id.state", "=", "approved"),
            ("request_id.analytic_account_id", "=", self.budget_analytic_account_id.id),
            ("request_id.fund_source_id", "=", self.budget_fund_source_id.id),
            ("request_id.annual_budget_id.date_from", "<=", check_date),
            ("request_id.annual_budget_id.date_to", ">=", check_date),
        ]
        if self.budget_section_key == "asset":
            lines = self.env["departmental.budget.request.line"].sudo().search(
                request_domain
                + [("asset_product_id", "=", product.product_tmpl_id.id)]
            )
            return sum(lines.mapped("allocated_budget_amount"))
        domain = request_domain + [("product_id", "=", product.id)]
        if self._requires_budget_group() and self.budget_group_id:
            domain.append(("budget_group_id", "=", self.budget_group_id.id))
        details = (
            self.env["departmental.budget.request.material.detail"].sudo().search(domain)
        )
        return sum(details.mapped("allocated_amount"))

    def _get_other_pr_reserved_amount_for_product(self, product):
        """จอง PR อื่นของสินค้านี้ (ไม่รวมบรรทัดของ PR ปัจจุบัน)."""
        self.ensure_one()
        if not product or not self.budget_analytic_account_id or not self.budget_fund_source_id:
            return 0.0
        domain = [
            ("id", "not in", self.line_ids.ids or [0]),
            ("product_id", "=", product.id),
            ("request_id.budget_reservation_active", "=", True),
            ("cancelled", "=", False),
            ("budget_analytic_account_id", "=", self.budget_analytic_account_id.id),
            ("budget_fund_source_id", "=", self.budget_fund_source_id.id),
        ]
        if self._requires_budget_group():
            domain.append(("budget_group_id", "=", self.budget_group_id.id))
        amount = 0.0
        for line in self.env["purchase.request.line"].sudo().search(domain):
            amount += line._get_budget_effective_reserved_amount_company()
        return amount

    def _po_line_matches_request_budget(self, po_line):
        self.ensure_one()
        budget_line = po_line.budget_line_id
        if budget_line:
            return (
                budget_line.analytic_account_id == self.budget_analytic_account_id
                and budget_line.fund_source_id == self.budget_fund_source_id
                and self._budget_keys_match_group(budget_line.budget_group_id)
            )
        pr_lines = po_line.purchase_request_lines
        return any(
            prl.budget_analytic_account_id == self.budget_analytic_account_id
            and prl.budget_fund_source_id == self.budget_fund_source_id
            and self._budget_keys_match_group(prl.budget_group_id)
            for prl in pr_lines
        )

    def _get_po_committed_amount_for_product(self, product, exclude_order=None):
        self.ensure_one()
        if not product:
            return 0.0
        domain = [
            ("product_id", "=", product.id),
            ("order_id.state", "in", ("purchase", "done")),
            ("state", "in", ("purchase", "done")),
        ]
        if exclude_order:
            domain.append(("order_id", "!=", exclude_order.id))
        amount = 0.0
        for po_line in self.env["purchase.order.line"].sudo().search(domain):
            if self._po_line_matches_request_budget(po_line):
                amount += po_line._get_budget_open_committed_amount_company()
        return amount

    def _get_budget_item_unit_price(self, product):
        """ราคาต่อหน่วยจากรายการคำของบที่อนุมัติ ของสินค้านี้ ถ้ามี."""
        self.ensure_one()
        if not product:
            return 0.0
        check_date = self.date_start or fields.Date.context_today(self)
        if self.budget_section_key != "asset":
            domain = [
                ("product_id", "=", product.id),
                ("request_id.state", "=", "approved"),
                ("unit_price", ">", 0),
            ]
            if self.budget_analytic_account_id:
                domain.append(
                    (
                        "request_id.analytic_account_id",
                        "=",
                        self.budget_analytic_account_id.id,
                    )
                )
            if self.budget_fund_source_id:
                domain.append(
                    ("request_id.fund_source_id", "=", self.budget_fund_source_id.id)
                )
            if self._requires_budget_group() and self.budget_group_id:
                domain.append(("budget_group_id", "=", self.budget_group_id.id))
            if self.budget_analytic_account_id and self.budget_fund_source_id:
                domain += [
                    ("request_id.annual_budget_id.date_from", "<=", check_date),
                    ("request_id.annual_budget_id.date_to", ">=", check_date),
                ]
            detail = (
                self.env["departmental.budget.request.material.detail"]
                .sudo()
                .search(domain, order="request_id desc, id desc", limit=1)
            )
            if detail:
                return detail.unit_price or 0.0
        if self.budget_section_key != "material":
            domain = [
                ("asset_product_id", "=", product.product_tmpl_id.id),
                ("request_id.state", "=", "approved"),
                ("unit_price", ">", 0),
            ]
            if self.budget_analytic_account_id:
                domain.append(
                    (
                        "request_id.analytic_account_id",
                        "=",
                        self.budget_analytic_account_id.id,
                    )
                )
            if self.budget_fund_source_id:
                domain.append(
                    ("request_id.fund_source_id", "=", self.budget_fund_source_id.id)
                )
            if self.budget_analytic_account_id and self.budget_fund_source_id:
                domain += [
                    ("request_id.annual_budget_id.date_from", "<=", check_date),
                    ("request_id.annual_budget_id.date_to", ">=", check_date),
                ]
            asset_line = (
                self.env["departmental.budget.request.line"]
                .sudo()
                .search(domain, order="request_id desc, id desc", limit=1)
            )
            if asset_line:
                return asset_line.unit_price or 0.0
        return 0.0

    def _get_last_purchase_unit_price(self, product):
        """ราคาต่อหน่วยจากใบสั่งซื้อที่ยืนยันล่าสุดของสินค้านี้."""
        self.ensure_one()
        if not product:
            return 0.0
        domain = [
            ("product_id", "=", product.id),
            ("order_id.state", "in", ("purchase", "done")),
            ("price_unit", ">", 0),
        ]
        if self.company_id:
            domain.append(("company_id", "=", self.company_id.id))
        po_line = self.env["purchase.order.line"].sudo().search(
            domain, order="date_order desc, id desc", limit=1
        )
        if not po_line:
            return 0.0
        price = po_line.price_unit or 0.0
        target_uom = product.uom_id
        source_uom = po_line.product_uom
        if source_uom and target_uom and source_uom != target_uom:
            price = source_uom._compute_price(price, target_uom)
        return price

    def _suggest_line_unit_price(self, product):
        """ราคาจากคำของบก่อน ถ้าไม่มีใช้ราคาซื้อครั้งล่าสุด."""
        self.ensure_one()
        price = self._get_budget_item_unit_price(product)
        if price:
            return price
        return self._get_last_purchase_unit_price(product)

    def _get_product_budget_remaining(self, product):
        """คงเหลือของสินค้าหลังหักจอง PR (รวม PR นี้ถ้ายังกันงบอยู่) และผูกพัน PO."""
        self.ensure_one()
        allocated = self._get_product_allocated_amount(product)
        other_reserved = self._get_other_pr_reserved_amount_for_product(product)
        own_reserved = 0.0
        if self.budget_reservation_active:
            own_reserved = sum(
                line._get_budget_effective_reserved_amount_company()
                for line in self.line_ids.filtered(
                    lambda line: not line.cancelled and line.product_id == product
                )
            )
        committed = self._get_po_committed_amount_for_product(product)
        return allocated - other_reserved - own_reserved - committed

    def _map_lines_to_budget_line(self, lines):
        self.ensure_one()
        mapping = {}
        for budget_post in lines.mapped("budget_post_id"):
            post_lines = lines.filtered(lambda line: line.budget_post_id == budget_post)
            budget_lines = self._get_matching_budget_lines(budget_post)
            if not budget_lines:
                continue
            selected = budget_lines.sorted(
                key=lambda budget_line: budget_line.pr_available_amount,
                reverse=True,
            )[:1]
            for line in post_lines:
                mapping[line.id] = selected.id
        return mapping

    def _prepare_product_allocation_check(self, lines):
        """เช็คงบทีละสินค้าจากยอดจัดสรร แล้วคืน (enough, messages, total_remaining, line_budget_map, rows)."""
        self.ensure_one()
        messages = []
        rows = []
        enough = True
        total_remaining = 0.0
        missing_product = lines.filtered(lambda line: not line.product_id)
        if missing_product:
            return (
                False,
                _("กรุณาระบุสินค้าในรายการให้ครบทุกบรรทัด เพื่อเช็คงบตามรายการที่จัดสรร"),
                0.0,
                {},
                [],
            )
        missing_post_lines = lines.filtered(lambda line: not line.budget_post_id)
        if missing_post_lines:
            return (
                False,
                _("กรุณาระบุหมวดงบประมาณในรายการ PR ให้ครบทุกบรรทัด"),
                0.0,
                {},
                [],
            )
        for product in lines.mapped("product_id"):
            product_lines = lines.filtered(lambda line: line.product_id == product)
            required = sum(
                line._get_budget_reserved_amount_company() for line in product_lines
            )
            allocated = self._get_product_allocated_amount(product)
            other_reserved = self._get_other_pr_reserved_amount_for_product(product)
            other_committed = self._get_po_committed_amount_for_product(product)
            available = allocated - other_reserved - other_committed
            remaining = available - required
            total_remaining += remaining
            if allocated <= 1e-6 or remaining < -1e-6:
                enough = False
            messages.append(
                _(
                    "%(product)s: จัดสรร %(allocated)s | จอง PR อื่น %(reserved)s | "
                    "ผูกพัน PO %(committed)s | คงเหลือก่อน PR นี้ %(available)s | "
                    "ขอจอง %(required)s | คงเหลือหลังจอง %(remaining)s"
                )
                % {
                    "product": product.display_name,
                    "allocated": self._format_budget_amount(allocated),
                    "reserved": self._format_budget_amount(other_reserved),
                    "committed": self._format_budget_amount(other_committed),
                    "available": self._format_budget_amount(available),
                    "required": self._format_budget_amount(required),
                    "remaining": self._format_budget_amount(remaining),
                }
            )
            rows.append(
                {
                    "name": product.display_name,
                    "check_mode": "product",
                    "allocated_amount": allocated,
                    "other_reserved_amount": other_reserved,
                    "committed_amount": other_committed,
                    "available_amount": available,
                    "required_amount": required,
                    "remaining_amount": remaining,
                    "is_short": allocated <= 1e-6 or remaining < -1e-6,
                }
            )
        return (
            enough,
            messages,
            total_remaining,
            self._map_lines_to_budget_line(lines),
            rows,
        )

    def _prepare_budget_check(self):
        self.ensure_one()
        lines = self._get_active_budget_request_lines()
        messages = []
        rows = []
        enough = True
        total_remaining = 0.0
        line_budget_map = {}

        if not lines:
            return False, _("กรุณาเพิ่มรายการสินค้า/บริการใน PR ก่อนเช็คงบประมาณ"), 0.0, {}, []
        missing_header = []
        if not self.budget_analytic_account_id:
            missing_header.append(_("หน่วยงานที่ขอซื้อ"))
        if self._requires_budget_group() and not self.budget_group_id:
            missing_header.append(_("กลุ่มงบประมาณ"))
        if not self.budget_fund_source_id:
            missing_header.append(_("แหล่งเงิน"))
        if missing_header:
            return (
                False,
                _("กรุณาระบุข้อมูลสำหรับเช็คงบประมาณ: %s")
                % ", ".join(missing_header),
                0.0,
                {},
                [],
            )

        if self._uses_product_allocation_check():
            enough, messages, total_remaining, line_budget_map, rows = (
                self._prepare_product_allocation_check(lines)
            )
            if isinstance(messages, (list, tuple)):
                messages = "\n".join(messages)
            return enough, messages, total_remaining, line_budget_map, rows

        missing_post_lines = lines.filtered(lambda line: not line.budget_post_id)
        if missing_post_lines:
            return (
                False,
                _("กรุณาระบุหมวดงบประมาณในรายการ PR ให้ครบทุกบรรทัด"),
                0.0,
                {},
                [],
            )

        for budget_post in lines.mapped("budget_post_id"):
            post_lines = lines.filtered(lambda line: line.budget_post_id == budget_post)
            required = sum(line._get_budget_reserved_amount_company() for line in post_lines)
            budget_lines = self._get_matching_budget_lines(budget_post)
            approved = sum(budget_lines.mapped("planned_amount"))
            actual = sum(
                abs(line.practical_amount or 0.0)
                if line.practical_amount < 0
                else (line.practical_amount or 0.0)
                for line in budget_lines
            )
            other_reserved = self._get_other_pr_reserved_amount(budget_post)
            other_committed = self._get_other_po_committed_amount(budget_post)
            available = approved - actual - other_reserved - other_committed
            remaining = available - required
            if not budget_lines:
                enough = False
                if self._requires_budget_group():
                    messages.append(
                        _(
                            "%(post)s: ไม่พบงบประมาณที่อนุมัติสำหรับหน่วยงาน/กลุ่มงบประมาณ/แหล่งเงินนี้"
                        )
                        % {"post": budget_post.display_name}
                    )
                else:
                    messages.append(
                        _(
                            "%(post)s: ไม่พบงบประมาณที่อนุมัติสำหรับหน่วยงาน/แหล่งเงินนี้"
                        )
                        % {"post": budget_post.display_name}
                    )
                continue
            total_remaining += remaining
            if remaining < 0:
                enough = False
            selected_budget_line = budget_lines.sorted(
                key=lambda budget_line: budget_line.pr_available_amount,
                reverse=True,
            )[:1]
            for line in post_lines:
                line_budget_map[line.id] = selected_budget_line.id
            messages.append(
                _(
                    "%(post)s: อนุมัติ %(approved)s | ใช้จริง %(actual)s | "
                    "จอง PR อื่น %(reserved)s | ผูกพัน PO %(committed)s | "
                    "คงเหลือก่อน PR นี้ %(available)s | ขอจอง %(required)s | "
                    "คงเหลือหลังจอง %(remaining)s"
                )
                % {
                    "post": budget_post.display_name,
                    "approved": self._format_budget_amount(approved),
                    "actual": self._format_budget_amount(actual),
                    "reserved": self._format_budget_amount(other_reserved),
                    "committed": self._format_budget_amount(other_committed),
                    "available": self._format_budget_amount(available),
                    "required": self._format_budget_amount(required),
                    "remaining": self._format_budget_amount(remaining),
                }
            )
            rows.append(
                {
                    "name": budget_post.display_name,
                    "check_mode": "post",
                    "approved_amount": approved,
                    "actual_amount": actual,
                    "other_reserved_amount": other_reserved,
                    "committed_amount": other_committed,
                    "available_amount": available,
                    "required_amount": required,
                    "remaining_amount": remaining,
                    "is_short": remaining < -1e-6,
                }
            )

        return enough, "\n".join(messages), total_remaining, line_budget_map, rows

    def _replace_budget_check_lines(self, rows):
        self.ensure_one()
        if not rows:
            return
        self.env["purchase.request.budget.check.line"].create(
            [
                {
                    **row,
                    "request_id": self.id,
                    "sequence": (index + 1) * 10,
                }
                for index, row in enumerate(rows)
            ]
        )

    def _rows_from_budget_check_message(self, message):
        """แปลงข้อความผลการเช็คงบที่บันทึกไว้แล้ว ให้เป็นแถวตาราง."""
        self.ensure_one()
        rows = []
        labeled_fields = (
            ("จอง PR อื่น", "other_reserved_amount"),
            ("ผูกพัน PO", "committed_amount"),
            ("คงเหลือก่อน PR นี้", "available_amount"),
            ("ขอจอง", "required_amount"),
            ("คงเหลือหลังจอง", "remaining_amount"),
            ("ใช้จริง", "actual_amount"),
        )
        for raw_line in (message or "").splitlines():
            line = raw_line.strip()
            if ": จัดสรร " in line:
                name, rest = line.split(": จัดสรร ", 1)
                mode = "product"
                leading_field = "allocated_amount"
            elif ": อนุมัติ " in line:
                name, rest = line.split(": อนุมัติ ", 1)
                mode = "post"
                leading_field = "approved_amount"
            else:
                continue
            parts = [part.strip() for part in rest.split("|")]
            if len(parts) < 6:
                continue
            row = {
                "name": name.strip(),
                "check_mode": mode,
                leading_field: self._parse_budget_amount_text(parts[0]),
            }
            matched = True
            for part in parts[1:]:
                field_name = False
                amount_text = part
                for label, candidate in labeled_fields:
                    prefix = label + " "
                    if part.startswith(prefix):
                        field_name = candidate
                        amount_text = part[len(prefix):]
                        break
                if not field_name:
                    matched = False
                    break
                row[field_name] = self._parse_budget_amount_text(amount_text)
            if not matched:
                continue
            remaining = row.get("remaining_amount") or 0.0
            allocated = row.get("allocated_amount") or 0.0
            row["is_short"] = remaining < -1e-6 or (
                mode == "product" and allocated <= 1e-6
            )
            rows.append(row)
        return rows

    @api.model
    def _parse_budget_amount_text(self, text):
        cleaned = []
        for char in text or "":
            if char.isdigit() or char in ".-":
                cleaned.append(char)
        if not cleaned or cleaned == ["-"] or cleaned == ["."]:
            return 0.0
        try:
            return float("".join(cleaned))
        except ValueError:
            return 0.0

    def _apply_budget_check_result(
        self, enough, message, remaining_total, line_budget_map, activate_reservation=False, rows=None
    ):
        self.ensure_one()
        header_vals = {
            "budget_check_state": "enough" if enough else "insufficient",
            "budget_check_date": fields.Datetime.now(),
            "budget_check_message": message,
            "budget_available_amount": remaining_total,
        }
        if enough and activate_reservation:
            header_vals["budget_reservation_active"] = True
        self.with_context(skip_budget_check_reset=True).write(header_vals)
        self._replace_budget_check_lines(rows or [])

        # Always sync line budget fields on check (not only when activating reservation)
        for line in self._get_active_budget_request_lines():
            line_vals = {}
            budget_line_id = line_budget_map.get(line.id)
            if budget_line_id and line.budget_line_id.id != budget_line_id:
                line_vals["budget_line_id"] = budget_line_id
            # Keep reserved amount in sync with current estimated cost
            new_reserved = line.estimated_cost or 0.0
            if abs((line.budget_reserved_amount or 0.0) - new_reserved) > 1e-6:
                line_vals["budget_reserved_amount"] = new_reserved
            if line_vals:
                line.with_context(
                    skip_budget_check_reset=True,
                    skip_budget_refresh=True,
                ).write(line_vals)

    def _activate_budget_reservation(self):
        for request in self:
            enough, message, available, line_budget_map, rows = request._prepare_budget_check()
            if not enough:
                raise ValidationError(
                    _(
                        "ไม่สามารถจองงบประมาณได้ เนื่องจากงบประมาณไม่เพียงพอหรือข้อมูลงบประมาณไม่ครบ\n\n%s"
                    )
                    % message
                )
            request._apply_budget_check_result(
                enough,
                message,
                available,
                line_budget_map,
                activate_reservation=True,
                rows=rows,
            )

    def _release_budget_reservation(self, clear_budget_lines=True):
        """คืนงบที่กันไว้ — ปิดสถานะจอง และล้างลิงก์รายการงบ (ถ้าต้องการ)."""
        requests = self.filtered("budget_reservation_active")
        if not requests:
            return
        requests.with_context(skip_budget_check_reset=True).write(
            {"budget_reservation_active": False}
        )
        if clear_budget_lines:
            requests.mapped("line_ids").with_context(
                skip_budget_check_reset=True,
                skip_budget_refresh=True,
            ).write({"budget_line_id": False})

    def _refresh_budget_reservation_after_edit(self):
        """เมื่อแก้ไขจำนวน/ราคา: คืนจองเดิม แล้วกันงบใหม่ตามยอดล่าสุด."""
        if self.env.context.get("skip_budget_refresh"):
            return
        old_map = self.env.context.get("budget_refresh_old_amounts") or {}
        for request in self.filtered("budget_reservation_active"):
            old_amount = old_map.get(request.id)
            if old_amount is None:
                # Fallback: sum stored reserved amounts before syncing from estimated_cost
                old_amount = sum(
                    (line.budget_reserved_amount or 0.0)
                    for line in request.line_ids.filtered(lambda line: not line.cancelled)
                )
            # Sync reserved amounts from current estimated_cost first
            for line in request._get_active_budget_request_lines():
                new_amt = line.estimated_cost or 0.0
                if abs((line.budget_reserved_amount or 0.0) - new_amt) > 1e-6:
                    line.with_context(
                        skip_budget_refresh=True,
                        skip_budget_check_reset=True,
                    ).write({"budget_reserved_amount": new_amt})
            # คืนจองเดิม (soft — ไม่ล้าง budget_line_id เพื่อให้ re-link เร็ว)
            request._release_budget_reservation(clear_budget_lines=False)
            try:
                request._activate_budget_reservation()
            except ValidationError as err:
                request.with_context(skip_budget_check_reset=True).write(
                    {
                        "budget_check_state": "insufficient",
                        "budget_check_message": str(err.args[0]) if err.args else str(err),
                        "budget_available_amount": 0.0,
                    }
                )
                raise
            request.invalidate_recordset(["budget_requested_amount"])
            new_amount = request.budget_requested_amount
            if abs((old_amount or 0.0) - (new_amount or 0.0)) < 1e-6:
                # No real change in reserved total — still log briefly
                request.message_post(
                    body=_(
                        "ตรวจการจองงบประมาณหลังแก้ไขรายการ — ยอดจองยังเป็น %(amount)s"
                    )
                    % {"amount": request._format_budget_amount(new_amount)}
                )
            else:
                request.message_post(
                    body=_(
                        "ปรับปรุงการจองงบประมาณหลังแก้ไขจำนวน/ราคา\n"
                        "คืนจองเดิม: %(old)s\n"
                        "กันงบใหม่: %(new)s"
                    )
                    % {
                        "old": request._format_budget_amount(old_amount),
                        "new": request._format_budget_amount(new_amount),
                    }
                )

    def action_refresh_budget_reservation(self):
        """ปุ่มมือ: คืนจองเดิมแล้วกันงบใหม่ตามยอดปัจจุบัน."""
        self.ensure_one()
        if not self.budget_reservation_active:
            raise UserError(
                _("PR นี้ยังไม่ได้จองงบประมาณ — กรุณาเช็คงบ / ส่งอนุมัติก่อน")
            )
        self._refresh_budget_reservation_after_edit()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ปรับปรุงการจองงบแล้ว"),
                "message": _(
                    "คืนจองเดิมและกันงบใหม่ตามยอดที่บันทึก: %(amount)s"
                )
                % {"amount": self._format_budget_amount(self.budget_requested_amount)},
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                    "target": "current",
                },
            },
        }

    def action_check_budget_status(self):
        self.ensure_one()
        enough, message, available, line_budget_map, rows = self._prepare_budget_check()
        if not enough and self.budget_reservation_active:
            self._release_budget_reservation(clear_budget_lines=False)
        self._apply_budget_check_result(
            enough,
            message,
            available,
            line_budget_map,
            activate_reservation=enough,
            rows=rows,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("จองงบประมาณแล้ว")
                if enough
                else _("สถานะงบประมาณ: ไม่เพียงพอ"),
                "message": message,
                "type": "success" if enough else "warning",
                "sticky": True,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                    "target": "current",
                    "context": self.env.context,
                },
            },
        }

    def _check_budget_available_before_submit(self):
        self._activate_budget_reservation()

    def button_to_approve(self):
        self._check_budget_available_before_submit()
        return super().button_to_approve()

    def button_approved(self):
        self._check_budget_available_before_submit()
        return super().button_approved()

    def request_validation(self):
        self._check_budget_available_before_submit()
        return super().request_validation()

    def button_rejected(self):
        self._release_budget_reservation()
        return super().button_rejected()

    def button_draft(self):
        self._release_budget_reservation()
        return super().button_draft()

    def button_done(self):
        # Only release leftover PR reservation; PO commitment stays until invoiced
        self._release_budget_reservation()
        return super().button_done()

    def restart_validation(self):
        self._release_budget_reservation()
        return super().restart_validation()

    def reject_tier(self):
        res = super().reject_tier()
        self._release_budget_reservation()
        return res

    def check_auto_reject(self):
        to_release = self.filtered(
            lambda request: request.budget_reservation_active
            and not request.line_ids.filtered(lambda line: not line.cancelled)
        )
        res = super().check_auto_reject()
        to_release._release_budget_reservation()
        return res


class PurchaseRequestBudgetCheckLine(models.Model):
    _name = "purchase.request.budget.check.line"
    _description = "รายละเอียดผลการเช็คงบประมาณ"
    _order = "sequence, id"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="รายการ", required=True)
    check_mode = fields.Selection(
        selection=[
            ("product", "สินค้า"),
            ("post", "หมวดงบประมาณ"),
        ],
        string="แบบเช็ค",
        required=True,
    )
    allocated_amount = fields.Monetary(
        string="จัดสรร",
        currency_field="currency_id",
    )
    approved_amount = fields.Monetary(
        string="อนุมัติ",
        currency_field="currency_id",
    )
    actual_amount = fields.Monetary(
        string="ใช้จริง",
        currency_field="currency_id",
    )
    other_reserved_amount = fields.Monetary(
        string="จอง PR อื่น",
        currency_field="currency_id",
    )
    committed_amount = fields.Monetary(
        string="ผูกพัน PO",
        currency_field="currency_id",
    )
    available_amount = fields.Monetary(
        string="คงเหลือก่อน PR นี้",
        currency_field="currency_id",
    )
    required_amount = fields.Monetary(
        string="ขอจอง",
        currency_field="currency_id",
    )
    remaining_amount = fields.Monetary(
        string="คงเหลือหลังจอง",
        currency_field="currency_id",
    )
    is_short = fields.Boolean(string="งบไม่พอ")
    currency_id = fields.Many2one(
        related="request_id.currency_id",
    )


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    budget_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="request_id.budget_analytic_account_id",
        store=True,
        readonly=True,
    )
    budget_fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        related="request_id.budget_fund_source_id",
        store=True,
        readonly=True,
    )
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        related="request_id.budget_group_id",
        store=True,
        readonly=True,
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        domain="[('company_id', '=', company_id)]",
        tracking=True,
    )
    allowed_budget_line_ids = fields.Many2many(
        comodel_name="budget.lines",
        compute="_compute_allowed_budget_line_ids",
    )
    budget_line_id = fields.Many2one(
        comodel_name="budget.lines",
        string="รายการงบประมาณที่จอง",
        domain="[('id', 'in', allowed_budget_line_ids)]",
        copy=False,
        tracking=True,
    )
    budget_unit_price = fields.Monetary(
        string="ราคาต่อหน่วย",
        currency_field="currency_id",
        copy=True,
        tracking=True,
    )
    budget_reserved_amount = fields.Monetary(
        string="งบประมาณที่จอง",
        currency_field="currency_id",
        copy=True,
        tracking=True,
    )
    budget_line_available_amount = fields.Float(
        string="งบคงเหลือของสินค้า",
        compute="_compute_budget_line_available_amount",
        digits=0,
    )

    @api.depends(
        "product_id",
        "cancelled",
        "budget_line_id",
        "budget_line_id.pr_available_amount",
        "request_id.budget_section_key",
        "request_id.budget_analytic_account_id",
        "request_id.budget_fund_source_id",
        "request_id.budget_group_id",
        "request_id.date_start",
        "request_id.budget_reservation_active",
        "request_id.line_ids.product_id",
        "request_id.line_ids.budget_reserved_amount",
        "request_id.line_ids.cancelled",
    )
    def _compute_budget_line_available_amount(self):
        for line in self:
            request = line.request_id
            if (
                line.product_id
                and request
                and request._uses_product_allocation_check()
            ):
                line.budget_line_available_amount = request._get_product_budget_remaining(
                    line.product_id
                )
            else:
                line.budget_line_available_amount = (
                    line.budget_line_id.pr_available_amount or 0.0
                )

    @api.depends(
        "request_id.budget_analytic_account_id",
        "request_id.budget_fund_source_id",
        "request_id.budget_group_id",
        "request_id.date_start",
        "budget_post_id",
    )
    def _compute_allowed_budget_line_ids(self):
        for line in self:
            if line.request_id and line.budget_post_id:
                line.allowed_budget_line_ids = line.request_id._get_matching_budget_lines(
                    line.budget_post_id
                )
            else:
                line.allowed_budget_line_ids = self.env["budget.lines"]

    def _apply_unit_price_to_estimated_cost(self):
        self.ensure_one()
        self.estimated_cost = (self.product_qty or 0.0) * (self.budget_unit_price or 0.0)
        self.budget_reserved_amount = self.estimated_cost or 0.0

    @api.onchange("product_id")
    def _onchange_product_id_set_budget_unit_price(self):
        """ดึงราคาต่อหน่วยจากคำของบ ถ้าไม่มีใช้ราคาซื้อครั้งล่าสุด."""
        for line in self:
            if not line.product_id or not line.request_id:
                continue
            line.budget_unit_price = line.request_id._suggest_line_unit_price(
                line.product_id
            )
            line._apply_unit_price_to_estimated_cost()

    @api.onchange("budget_unit_price")
    def _onchange_budget_unit_price_set_estimated_cost(self):
        for line in self:
            if line.budget_unit_price:
                line._apply_unit_price_to_estimated_cost()

    @api.onchange("estimated_cost")
    def _onchange_estimated_cost_set_budget_reserved_amount(self):
        """ราคา/งบประมาณเปลี่ยน → sync ยอดจองทันที."""
        for line in self:
            line.budget_reserved_amount = line.estimated_cost or 0.0

    @api.onchange("product_qty")
    def _onchange_product_qty_scale_estimated_cost(self):
        """จำนวนเปลี่ยน → งบประมาณ = จำนวน x ราคาต่อหน่วย."""
        for line in self:
            if line.budget_unit_price:
                line._apply_unit_price_to_estimated_cost()
                continue
            origin = line._origin
            if not origin or not origin.product_qty or not origin.estimated_cost:
                continue
            if abs(origin.product_qty) < 1e-9:
                continue
            if abs((line.product_qty or 0.0) - origin.product_qty) < 1e-9:
                continue
            line.estimated_cost = origin.estimated_cost * (
                (line.product_qty or 0.0) / origin.product_qty
            )
            line.budget_reserved_amount = line.estimated_cost or 0.0

    @api.onchange("budget_post_id", "allowed_budget_line_ids")
    def _onchange_budget_post_id_set_budget_line(self):
        for line in self:
            if line.budget_line_id and line.budget_line_id not in line.allowed_budget_line_ids:
                line.budget_line_id = False
            if not line.budget_line_id and len(line.allowed_budget_line_ids) == 1:
                line.budget_line_id = line.allowed_budget_line_ids

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "budget_post_id" in fields_list and not res.get("budget_post_id"):
            request = self.env["purchase.request"].browse(
                res.get("request_id") or self.env.context.get("default_request_id")
            )
            if request.budget_post_id:
                res["budget_post_id"] = request.budget_post_id.id
        return res

    def _vals_with_header_budget_post(self, vals):
        vals = dict(vals)
        request_id = vals.get("request_id") or self.env.context.get("default_request_id")
        request = (
            self.env["purchase.request"].browse(request_id)
            if request_id
            else self.env["purchase.request"]
        )
        if request.budget_post_id:
            vals["budget_post_id"] = request.budget_post_id.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._fill_unit_price_vals(vals)
            if "budget_reserved_amount" not in vals:
                vals["budget_reserved_amount"] = vals.get("estimated_cost", 0.0)
            if not self.env.context.get("skip_budget_line_sync"):
                vals.update(self._vals_with_header_budget_post(vals))
        lines = super().create(vals_list)
        if not self.env.context.get("skip_budget_line_sync"):
            for line in lines.filtered(lambda rec: not rec.cancelled):
                header_post = line.request_id.budget_post_id
                if not header_post:
                    continue
                vals = {}
                if line.budget_post_id != header_post:
                    vals["budget_post_id"] = header_post.id
                if not line.budget_line_id or "budget_post_id" in vals:
                    matches = line.request_id._get_matching_budget_lines(header_post)
                    if line.budget_line_id and line.budget_line_id not in matches:
                        vals["budget_line_id"] = False
                    if (
                        (not line.budget_line_id or vals.get("budget_line_id") is False)
                        and len(matches) == 1
                    ):
                        vals["budget_line_id"] = matches.id
                if vals:
                    line.with_context(skip_budget_line_sync=True).write(vals)
        lines._reset_parent_budget_check()
        reserved_parents = lines.mapped("request_id").filtered("budget_reservation_active")
        if reserved_parents:
            reserved_parents._refresh_budget_reservation_after_edit()
        return lines

    def _fill_unit_price_vals(self, vals):
        """เติมราคาต่อหน่วยและงบประมาณตอนสร้างบรรทัด ถ้ายังไม่ได้ระบุ."""
        if vals.get("budget_unit_price") or not vals.get("product_id"):
            return vals
        request_id = vals.get("request_id") or self.env.context.get("default_request_id")
        request = (
            self.env["purchase.request"].browse(request_id) if request_id else self.env["purchase.request"]
        )
        if not request:
            return vals
        product = self.env["product.product"].browse(vals["product_id"])
        price = request._suggest_line_unit_price(product)
        if not price:
            return vals
        vals["budget_unit_price"] = price
        if "estimated_cost" not in vals:
            qty = vals.get("product_qty") or 0.0
            vals["estimated_cost"] = qty * price
        return vals

    def write(self, vals):
        vals = dict(vals)
        # Scale estimated_cost when qty changes without explicit cost
        if (
            "product_qty" in vals
            and "estimated_cost" not in vals
            and not self.env.context.get("skip_budget_refresh")
        ):
            new_qty = vals["product_qty"]
            unit_price = vals.get("budget_unit_price")
            if unit_price is None and len(self) == 1:
                unit_price = self.budget_unit_price
            if len(self) == 1 and unit_price:
                vals["estimated_cost"] = float(unit_price) * float(new_qty)
            elif len(self) == 1 and self.product_qty and abs(self.product_qty) > 1e-9:
                vals["estimated_cost"] = (self.estimated_cost or 0.0) * (
                    float(new_qty) / self.product_qty
                )
            elif len(self) > 1:
                # Multi-record: scale each line individually then refresh once
                parents = self.mapped("request_id")
                old_amounts = {
                    request.id: request.budget_requested_amount
                    for request in parents.filtered("budget_reservation_active")
                }
                for line in self:
                    line_vals = dict(vals)
                    if line.budget_unit_price:
                        line_vals["estimated_cost"] = float(line.budget_unit_price) * float(
                            new_qty
                        )
                    elif line.product_qty and abs(line.product_qty) > 1e-9:
                        line_vals["estimated_cost"] = (line.estimated_cost or 0.0) * (
                            float(new_qty) / line.product_qty
                        )
                    line.with_context(
                        skip_budget_refresh=True,
                        skip_budget_multi_qty=True,
                    ).write(line_vals)
                parents.filtered("budget_reservation_active").with_context(
                    budget_refresh_old_amounts=old_amounts
                )._refresh_budget_reservation_after_edit()
                parents.filtered(
                    lambda r: not r.budget_reservation_active
                ).mapped("line_ids")._reset_parent_budget_check()
                return True

        if (
            "budget_unit_price" in vals
            and "estimated_cost" not in vals
            and "product_qty" not in vals
            and len(self) == 1
        ):
            vals["estimated_cost"] = (self.product_qty or 0.0) * float(
                vals.get("budget_unit_price") or 0.0
            )

        if "estimated_cost" in vals and "budget_reserved_amount" not in vals:
            vals["budget_reserved_amount"] = vals.get("estimated_cost") or 0.0

        reserved_parents = self.mapped("request_id").filtered("budget_reservation_active")
        old_amounts = {
            request.id: request.budget_requested_amount for request in reserved_parents
        }

        res = super().write(vals)
        amount_keys = {
            "budget_post_id",
            "budget_line_id",
            "budget_reserved_amount",
            "estimated_cost",
            "product_qty",
            "cancelled",
        }
        if amount_keys.intersection(vals) and not self.env.context.get("skip_budget_refresh"):
            reserved_parents = self.mapped("request_id").filtered(
                "budget_reservation_active"
            )
            if reserved_parents:
                reserved_parents.with_context(
                    budget_refresh_old_amounts=old_amounts
                )._refresh_budget_reservation_after_edit()
            else:
                self._reset_parent_budget_check()
        return res

    def _reset_parent_budget_check(self):
        if self.env.context.get("skip_budget_check_reset"):
            return
        requests = self.mapped("request_id").filtered(
            lambda request: request.state == "draft" and not request.budget_reservation_active
        )
        if requests:
            requests.with_context(skip_budget_check_reset=True).write(
                {
                    "budget_check_state": "unchecked",
                    "budget_check_message": False,
                    "budget_available_amount": 0.0,
                }
            )

    def _get_budget_reserved_amount_company(self):
        self.ensure_one()
        company = self.company_id or self.env.company
        currency = self.currency_id or company.currency_id
        return currency._convert(
            self.budget_reserved_amount or self.estimated_cost or 0.0,
            company.currency_id,
            company,
            self.date_start or fields.Date.context_today(self),
        )

    def _get_budget_transferred_to_po_amount_company(self):
        """Amount of this PR line already moved to confirmed PO commitment."""
        self.ensure_one()
        amount = 0.0
        po_lines = self.purchase_lines.filtered(
            lambda line: line.order_id.state in ("purchase", "done")
        )
        for po_line in po_lines:
            pr_lines = po_line.purchase_request_lines
            share = 1.0 / len(pr_lines) if pr_lines else 1.0
            amount += po_line._get_budget_confirmed_amount_company() * share
        return amount

    def _get_budget_effective_reserved_amount_company(self):
        """PR reservation still holding budget after deducting confirmed PO amounts."""
        self.ensure_one()
        if self.cancelled or not self.request_id.budget_reservation_active:
            return 0.0
        raw = self._get_budget_reserved_amount_company()
        transferred = self._get_budget_transferred_to_po_amount_company()
        return max(0.0, raw - transferred)
