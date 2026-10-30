from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestBudgetProductWizard(models.TransientModel):
    _name = "purchase.request.budget.product.wizard"
    _description = "เลือกรายการจากแผนงบประมาณ"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="request_id.company_id")
    currency_id = fields.Many2one(related="request_id.currency_id")
    budget_section_key = fields.Selection(related="request_id.budget_section_key")
    allowed_budget_post_ids = fields.Many2many(
        comodel_name="account.budget.post",
        compute="_compute_allowed_budget_post_ids",
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบ",
        domain="[('id', 'in', allowed_budget_post_ids)]",
    )
    line_ids = fields.One2many(
        comodel_name="purchase.request.budget.product.wizard.line",
        inverse_name="wizard_id",
        string="รายการสินค้าในงบที่ได้รับอนุมัติ",
    )

    @api.depends(
        "request_id",
        "request_id.budget_plan_request_id",
        "request_id.budget_analytic_account_id",
        "request_id.budget_fund_source_id",
        "request_id.budget_group_id",
        "request_id.budget_section_key",
        "request_id.date_start",
    )
    def _compute_allowed_budget_post_ids(self):
        for wizard in self:
            wizard.allowed_budget_post_ids = wizard._search_approved_budget_posts()

    def _request_allocation_domain(self):
        self.ensure_one()
        request = self.request_id
        check_date = request._allocation_check_date()
        if request.budget_plan_request_id:
            return [
                ("request_id", "=", request.budget_plan_request_id.id),
                ("request_id.state", "=", "approved"),
            ]
        return [
            ("request_id.state", "=", "approved"),
            ("request_id.analytic_account_id", "=", request.budget_analytic_account_id.id),
            ("request_id.fund_source_id", "=", request.budget_fund_source_id.id),
            ("request_id.annual_budget_id.date_from", "<=", check_date),
            ("request_id.annual_budget_id.date_to", ">=", check_date),
        ]

    def _wizard_section_key(self, budget_post=None):
        self.ensure_one()
        post = budget_post if budget_post is not None else self.budget_post_id
        return self.request_id.budget_section_key or (post.section_key if post else False)

    def _include_material(self, budget_post=None):
        section = self._wizard_section_key(budget_post)
        return not section or section == "material"

    def _include_asset(self, budget_post=None):
        section = self._wizard_section_key(budget_post)
        return not section or section == "asset"

    def _search_approved_budget_posts(self):
        self.ensure_one()
        request = self.request_id
        if (
            not request
            or not request.budget_analytic_account_id
            or not request.budget_fund_source_id
        ):
            return self.env["account.budget.post"]
        domain = self._request_allocation_domain()
        post_ids = set()
        if self._include_material():
            material_domain = domain + [
                ("product_id", "!=", False),
                ("allocated_amount", ">", 0),
                ("budget_post_id", "!=", False),
            ]
            if request._requires_budget_group() and request.budget_group_id:
                material_domain.append(("budget_group_id", "=", request.budget_group_id.id))
            details = (
                self.env["departmental.budget.request.material.detail"]
                .sudo()
                .search(material_domain)
            )
            post_ids.update(details.mapped("budget_post_id").ids)
        if self._include_asset():
            asset_domain = domain + [
                ("asset_product_id", "!=", False),
                ("allocated_budget_amount", ">", 0),
                ("budget_post_id", "!=", False),
            ]
            lines = (
                self.env["departmental.budget.request.line"].sudo().search(asset_domain)
            )
            post_ids.update(lines.mapped("budget_post_id").ids)
        posts = self.env["account.budget.post"].browse(list(post_ids))
        if request.budget_post_id:
            posts |= request.budget_post_id
        if posts:
            return posts
        post_domain = [
            ("company_id", "in", [False, request.company_id.id]),
        ]
        section = request.budget_section_key
        if section:
            post_domain += [
                "|",
                ("section_key", "=", False),
                ("section_key", "=", section),
            ]
        return self.env["account.budget.post"].search(post_domain)

    def _product_already_on_pr(self, product):
        self.ensure_one()
        return any(
            line.product_id == product and not line.cancelled
            for line in self.request_id.line_ids
        )

    @api.model
    def _purchase_uom(self, product, plan_uom):
        """Plan quantities and prices are counted in the product purchase UoM."""
        return product.uom_po_id or plan_uom

    def _suggested_qty(self, allocated_qty, unit_price, remaining_amount):
        """Allocated plan quantity, reduced only when the remaining budget can't cover it."""
        if remaining_amount <= 0 or not unit_price or unit_price <= 0:
            return allocated_qty or 1.0
        affordable = remaining_amount / unit_price
        if allocated_qty and allocated_qty <= affordable + 1e-6:
            return allocated_qty
        return affordable

    def _prepare_product_line_vals(self):
        self.ensure_one()
        request = self.request_id
        budget_post = self.budget_post_id
        if not request or not budget_post:
            return []
        grouped = {}
        domain = self._request_allocation_domain() + [
            ("budget_post_id", "=", budget_post.id)
        ]
        if self._include_material():
            material_domain = domain + [
                ("product_id", "!=", False),
                ("allocated_amount", ">", 0),
            ]
            if request._requires_budget_group() and request.budget_group_id:
                material_domain.append(("budget_group_id", "=", request.budget_group_id.id))
            details = (
                self.env["departmental.budget.request.material.detail"]
                .sudo()
                .search(material_domain, order="id")
            )
            for detail in details:
                product = detail.product_id
                row = grouped.setdefault(
                    product.id,
                    {
                        "product": product,
                        "uom": detail.product_uom_id or product.uom_id,
                        "allocated_qty": 0.0,
                        "allocated_amount": 0.0,
                        "unit_price": 0.0,
                    },
                )
                row["allocated_qty"] += detail.allocated_qty or 0.0
                row["allocated_amount"] += detail.allocated_amount or 0.0
                if detail.unit_price:
                    row["unit_price"] = detail.unit_price
                if not row["uom"] and product.uom_id:
                    row["uom"] = product.uom_id
        if self._include_asset():
            asset_domain = domain + [
                ("asset_product_id", "!=", False),
                ("allocated_budget_amount", ">", 0),
            ]
            asset_lines = (
                self.env["departmental.budget.request.line"]
                .sudo()
                .search(asset_domain, order="id")
            )
            for asset_line in asset_lines:
                template = asset_line.asset_product_id
                product = template.product_variant_id
                if not product:
                    continue
                qty = (
                    asset_line.requested_quantity
                    or asset_line._get_asset_request_quantity()
                    or 0.0
                )
                if not qty and asset_line.unit_price:
                    qty = (asset_line.allocated_budget_amount or 0.0) / asset_line.unit_price
                row = grouped.setdefault(
                    product.id,
                    {
                        "product": product,
                        "uom": product.uom_id,
                        "allocated_qty": 0.0,
                        "allocated_amount": 0.0,
                        "unit_price": 0.0,
                    },
                )
                row["allocated_qty"] += qty
                row["allocated_amount"] += asset_line.allocated_budget_amount or 0.0
                if asset_line.unit_price:
                    row["unit_price"] = asset_line.unit_price
        vals_list = []
        for product_id, row in grouped.items():
            product = row["product"]
            remaining = request._get_product_budget_remaining(product)
            already = self._product_already_on_pr(product)
            unit_price = row["unit_price"] or request._suggest_line_unit_price(product)
            if remaining <= 1e-6:
                continue
            qty = self._suggested_qty(row["allocated_qty"], unit_price, remaining)
            plan_uom = row["uom"] or product.uom_id
            purchase_uom = self._purchase_uom(product, plan_uom)
            vals_list.append(
                {
                    "selected": False,
                    "product_id": product_id,
                    "product_uom_id": plan_uom.id if plan_uom else False,
                    "purchase_uom_id": purchase_uom.id if purchase_uom else False,
                    "allocated_qty": row["allocated_qty"],
                    "allocated_amount": row["allocated_amount"],
                    "unit_price": unit_price,
                    "remaining_amount": remaining,
                    "product_qty": qty,
                    "already_on_pr": already,
                }
            )
        vals_list.sort(
            key=lambda vals: (
                not vals["selected"],
                vals["already_on_pr"],
                vals["product_id"],
            )
        )
        return vals_list

    def _reload_product_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        vals_list = self._prepare_product_line_vals()
        if vals_list:
            self.write(
                {"line_ids": [(0, 0, vals) for vals in vals_list]}
            )

    @api.onchange("budget_post_id")
    def _onchange_budget_post_id(self):
        commands = [(5, 0, 0)]
        if self.budget_post_id and self.request_id:
            commands.extend((0, 0, vals) for vals in self._prepare_product_line_vals())
        self.line_ids = commands

    def action_select_all(self):
        self.ensure_one()
        self.line_ids.filtered(
            lambda line: not line.already_on_pr and (line.remaining_amount or 0.0) > 1e-6
        ).write({"selected": True})
        return self._reopen()

    def action_unselect_all(self):
        self.ensure_one()
        self.line_ids.write({"selected": False})
        return self._reopen()

    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เลือกรายการจากแผนงบประมาณ"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": {"dialog_size": "extra-large"},
        }

    def action_load(self):
        self.ensure_one()
        request = self.request_id
        if request.state != "draft":
            raise UserError(_("โหลดรายการได้เฉพาะใบขอซื้อสถานะร่าง"))
        if not self.budget_post_id:
            raise UserError(_("กรุณาเลือกหมวดงบ"))
        selected = self.line_ids.filtered(
            lambda line: line.selected and (line.remaining_amount or 0.0) > 1e-6
        )
        if not selected:
            raise UserError(
                _("กรุณาเลือกรายการสินค้าที่งบยังเหลืออย่างน้อย 1 รายการ")
            )
        header_vals = {"budget_post_id": self.budget_post_id.id}
        if not request.budget_section_key and self.budget_post_id.section_key:
            header_vals["budget_section_key"] = self.budget_post_id.section_key
        request.write(header_vals)

        existing_product_ids = set(
            request.line_ids.filtered(lambda line: not line.cancelled).mapped(
                "product_id"
            ).ids
        )
        Line = self.env["purchase.request.line"]
        created = 0
        skipped = 0
        skipped_no_budget = 0
        date_required = request.date_start or fields.Date.context_today(self)
        for wiz_line in selected:
            product = wiz_line.product_id
            if (wiz_line.remaining_amount or 0.0) <= 1e-6:
                skipped_no_budget += 1
                continue
            if not product or product.id in existing_product_ids:
                skipped += 1
                continue
            qty = wiz_line.product_qty or 0.0
            if qty <= 0:
                raise UserError(
                    _("จำนวนของ %s ต้องมากกว่า 0") % product.display_name
                )
            price = wiz_line.unit_price or 0.0
            name = product.name
            if product.code:
                name = f"[{product.code}] {name}"
            if product.description_purchase:
                name = f"{name}\n{product.description_purchase}"
            Line.create(
                {
                    "request_id": request.id,
                    "product_id": product.id,
                    "name": name,
                    "product_qty": qty,
                    "product_uom_id": self._purchase_uom(
                        product, wiz_line.product_uom_id or product.uom_id
                    ).id,
                    "date_required": date_required,
                    "budget_post_id": self.budget_post_id.id,
                    "budget_unit_price": price,
                    "estimated_cost": qty * price,
                    "budget_reserved_amount": qty * price,
                    "loaded_from_budget_plan": True,
                }
            )
            existing_product_ids.add(product.id)
            created += 1
        if not created:
            raise UserError(
                _("ไม่มีรายการที่งบยังเหลือให้โหลด หรือสินค้าที่เลือกมีอยู่ในใบขอซื้อแล้ว")
            )
        message = _("โหลดรายการจากแผนงบประมาณ %s รายการ") % created
        extras = []
        if skipped:
            extras.append(_("ข้ามสินค้าที่มีอยู่แล้ว %s รายการ") % skipped)
        if skipped_no_budget:
            extras.append(_("ข้ามสินค้าที่งบหมดแล้ว %s รายการ") % skipped_no_budget)
        if extras:
            message += " (%s)" % " / ".join(extras)
        request.message_post(body=message)
        return {"type": "ir.actions.act_window_close"}


class PurchaseRequestBudgetProductWizardLine(models.TransientModel):
    _name = "purchase.request.budget.product.wizard.line"
    _description = "รายการสินค้าจากแผนงบประมาณ"
    _order = "already_on_pr, product_id"

    wizard_id = fields.Many2one(
        comodel_name="purchase.request.budget.product.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(string="เลือก", default=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า",
        required=True,
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วยนับ (เล็กสุด)",
        readonly=True,
    )
    purchase_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วยซื้อ",
        readonly=True,
    )
    allocated_qty = fields.Float(
        string="จำนวนที่จัดสรร (หน่วยซื้อ)",
        digits="Product Unit of Measure",
        readonly=True,
    )
    unit_price = fields.Monetary(
        string="ราคา/หน่วยซื้อ",
        currency_field="currency_id",
        readonly=True,
    )
    allocated_amount = fields.Monetary(
        string="มูลค่าที่จัดสรร",
        currency_field="currency_id",
        readonly=True,
    )
    remaining_amount = fields.Monetary(
        string="งบคงเหลือ",
        currency_field="currency_id",
        readonly=True,
    )
    product_qty = fields.Float(
        string="จำนวนที่ขอซื้อ",
        digits="Product Unit of Measure",
        required=True,
    )
    already_on_pr = fields.Boolean(string="มีใน PR แล้ว", readonly=True)
    currency_id = fields.Many2one(related="wizard_id.currency_id")
