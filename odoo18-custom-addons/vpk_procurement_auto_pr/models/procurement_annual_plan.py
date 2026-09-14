from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProcurementAnnualPlan(models.Model):
    _name = "procurement.annual.plan"
    _description = "แผนจัดซื้อจัดจ้างประจำปีงบประมาณ"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fiscal_year_start desc, id desc"

    name = fields.Char(
        string="ชื่อแผน",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="รหัสแผน",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    fiscal_year_start = fields.Date(
        string="เริ่มปีงบประมาณ",
        required=True,
        tracking=True,
    )
    fiscal_year_end = fields.Date(
        string="สิ้นสุดปีงบประมาณ",
        required=True,
        tracking=True,
    )
    budget_id = fields.Many2one(
        comodel_name="budget.budget",
        string="แผนงบประมาณประจำปี",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("approved", "อนุมัติ"),
            ("closed", "ปิดแผน"),
            ("cancelled", "ยกเลิก"),
        ],
        default="draft",
        tracking=True,
        required=True,
    )
    auto_gen_enabled = fields.Boolean(
        string="เปิดใช้ Gen Auto",
        default=True,
        tracking=True,
        help="ถ้าเปิด ระบบจะสร้างใบขอซื้อ/จ้าง/เช่าอัตโนมัติจากรายการในแผน "
             "เมื่อสินค้าถึงจุดสั่งซื้อ หรือสัญญาใกล้หมดอายุ",
    )
    line_ids = fields.One2many(
        comodel_name="procurement.annual.plan.line",
        inverse_name="plan_id",
        string="รายการแผน",
    )
    amendment_ids = fields.One2many(
        comodel_name="procurement.plan.amendment",
        inverse_name="plan_id",
        string="คำขอเพิ่มแผน",
    )
    line_count = fields.Integer(compute="_compute_counts")
    amendment_count = fields.Integer(compute="_compute_counts")
    pr_count = fields.Integer(compute="_compute_counts")
    notes = fields.Html(string="หมายเหตุ")

    @api.depends("line_ids", "amendment_ids")
    def _compute_counts(self):
        PR = self.env["purchase.request"]
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.amendment_count = len(plan.amendment_ids)
            plan.pr_count = PR.search_count([("procurement_plan_id", "=", plan.id)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", _("New")) == _("New"):
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("procurement.annual.plan")
                    or _("New")
                )
        return super().create(vals_list)

    def action_approve(self):
        self.write({"state": "approved"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_view_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "รายการแผน",
            "res_model": "procurement.annual.plan.line",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id},
        }

    def action_view_amendments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "คำขอเพิ่มแผน",
            "res_model": "procurement.plan.amendment",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id},
        }

    def action_view_prs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "ใบขอซื้อจากแผน",
            "res_model": "purchase.request",
            "view_mode": "list,form",
            "domain": [("procurement_plan_id", "=", self.id)],
        }

    def action_run_auto_gen_now(self):
        """รัน Gen Auto ทันทีสำหรับแผนนี้"""
        self.ensure_one()
        if not self.auto_gen_enabled:
            raise UserError(_("แผนนี้ยังไม่ได้เปิดใช้ Gen Auto"))
        if self.state != "approved":
            raise UserError(_("ต้องอนุมัติแผนก่อนจึงจะ Gen Auto ได้"))
        result = self.env["procurement.annual.plan"]._cron_auto_generate_prs(
            plan_ids=self.ids
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Gen Auto เสร็จสิ้น"),
                "message": result,
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def _get_active_plans(self, company=None):
        company = company or self.env.company
        today = fields.Date.context_today(self)
        return self.search([
            ("company_id", "=", company.id),
            ("state", "=", "approved"),
            ("auto_gen_enabled", "=", True),
            ("fiscal_year_start", "<=", today),
            ("fiscal_year_end", ">=", today),
        ])

    @api.model
    def _is_auto_gen_globally_enabled(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_procurement_auto_pr.auto_gen_enabled", "True")
            == "True"
        )

    @api.model
    def _get_contract_expiry_days(self):
        return int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("vpk_procurement_auto_pr.contract_expiry_days", "60")
        )

    @api.model
    def _cron_auto_generate_prs(self, plan_ids=None):
        """สร้าง PR อัตโนมัติจากจุดสั่งซื้อ + สัญญาใกล้หมดอายุ ตามแผน"""
        if not self._is_auto_gen_globally_enabled() and not plan_ids:
            return _("Gen Auto ถูกปิดใช้งานระดับระบบ")

        domain = [
            ("state", "=", "approved"),
            ("auto_gen_enabled", "=", True),
        ]
        if plan_ids:
            domain.append(("id", "in", plan_ids))
        else:
            today = fields.Date.context_today(self)
            domain += [
                ("fiscal_year_start", "<=", today),
                ("fiscal_year_end", ">=", today),
            ]
        plans = self.search(domain)
        if not plans:
            return _("ไม่พบแผนที่เปิด Gen Auto")

        created_prs = self.env["purchase.request"]
        amendments = self.env["procurement.plan.amendment"]
        for plan in plans:
            prs, amds = plan._auto_gen_from_orderpoints()
            created_prs |= prs
            amendments |= amds
            prs2, amds2 = plan._auto_gen_from_expiring_contracts()
            created_prs |= prs2
            amendments |= amds2

        return _(
            "สร้าง PR อัตโนมัติ %(pr)s ใบ, คำขอเพิ่มแผน %(amd)s ใบ"
        ) % {"pr": len(created_prs), "amd": len(amendments)}

    def _find_plan_line(self, product=None, contract=None, purchase_type=None):
        self.ensure_one()
        domain = [("plan_id", "=", self.id), ("active", "=", True)]
        if product:
            domain.append(("product_id", "=", product.id))
        if contract:
            domain.append(("contract_id", "=", contract.id))
        if purchase_type:
            domain.append(("purchase_type", "=", purchase_type))
        return self.env["procurement.annual.plan.line"].search(domain, limit=1)

    def _prepare_auto_pr_vals(self, origin, description, extra=None):
        self.ensure_one()
        picking_type = self.env["stock.picking.type"].search([
            ("code", "=", "incoming"),
            ("warehouse_id.company_id", "=", self.company_id.id),
        ], limit=1)
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search([
                ("code", "=", "incoming"),
            ], limit=1)
        vals = {
            "origin": origin,
            "description": description,
            "procurement_plan_id": self.id,
            "is_auto_generated": True,
            "company_id": self.company_id.id,
            "requested_by": self.env.user.id,
            "picking_type_id": picking_type.id if picking_type else False,
        }
        if extra:
            vals.update(extra)
        return vals

    def _auto_gen_from_orderpoints(self):
        """สร้าง PR จากสินค้าที่ถึงจุดสั่งซื้อ (ถ้าอยู่ในแผน)"""
        self.ensure_one()
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        PR = self.env["purchase.request"]
        created = PR.browse()
        amendments = self.env["procurement.plan.amendment"].browse()

        plan_products = self.line_ids.filtered(
            lambda l: l.active and l.purchase_type == "buy" and l.product_id
        ).mapped("product_id")
        if not plan_products:
            # Still check outside-plan low stock for amendments
            pass

        orderpoints = Orderpoint.search([
            ("product_id", "in", plan_products.ids),
            ("product_min_qty", ">", 0),
        ]) if plan_products else Orderpoint.browse()

        needs = []
        for op in orderpoints:
            onhand = op.qty_on_hand
            if onhand >= op.product_min_qty:
                continue
            qty = max(op.product_max_qty - onhand, op.product_min_qty - onhand)
            if qty <= 0:
                continue
            existing = PR.search([
                ("procurement_plan_id", "=", self.id),
                ("is_auto_generated", "=", True),
                ("state", "in", ("draft", "to_approve", "approved", "in_progress")),
                ("line_ids.product_id", "=", op.product_id.id),
                ("origin", "ilike", "AUTO-OP"),
            ], limit=1)
            if existing:
                continue
            needs.append((op, qty))

        all_low_ops = Orderpoint.search([("product_min_qty", ">", 0)], limit=200)
        for op in all_low_ops:
            if op.qty_on_hand >= op.product_min_qty:
                continue
            if op.product_id in plan_products:
                continue
            amd = self._ensure_amendment_for_product(op.product_id, "buy", op)
            if amd:
                amendments |= amd

        if needs:
            lines = []
            for op, qty in needs:
                plan_line = self._find_plan_line(
                    product=op.product_id, purchase_type="buy"
                )
                lines.append((0, 0, {
                    "product_id": op.product_id.id,
                    "product_qty": qty,
                    "product_uom_id": op.product_uom.id,
                    "name": op.product_id.display_name,
                    "estimated_cost": (
                        (plan_line.unit_price or 0.0) * qty if plan_line else 0.0
                    ),
                    "procurement_plan_line_id": plan_line.id if plan_line else False,
                }))
            pr_vals = self._prepare_auto_pr_vals(
                origin="AUTO-OP/%s/%s" % (self.code, fields.Date.context_today(self)),
                description=_("สร้างอัตโนมัติจากจุดสั่งซื้อ — แผน %s") % self.name,
                extra={"auto_gen_source": "orderpoint", "line_ids": lines},
            )
            pr = PR.create(pr_vals)
            created |= pr
            for op, _qty in needs:
                plan_line = self._find_plan_line(
                    product=op.product_id, purchase_type="buy"
                )
                if plan_line:
                    plan_line._recompute_consumed()

        return created, amendments

    def _auto_gen_from_expiring_contracts(self):
        """สร้าง PR จากสัญญาจ้าง/เช่าที่ใกล้หมดอายุ (ถ้าอยู่ในแผน)"""
        self.ensure_one()
        Contract = self.env["purchase.contract"]
        PR = self.env["purchase.request"]
        created = PR.browse()
        amendments = self.env["procurement.plan.amendment"].browse()
        days = self._get_contract_expiry_days()
        today = fields.Date.context_today(self)
        limit_date = today + timedelta(days=days)

        contracts = Contract.search([
            ("state", "=", "confirmed"),
            ("date_end", "!=", False),
            ("date_end", ">=", today),
            ("date_end", "<=", limit_date),
            ("company_id", "=", self.company_id.id),
            ("contract_kind", "in", ("hire", "lease")),
        ])
        # Also include contracts without kind set that are linked in plan as hire/lease
        plan_contract_ids = self.line_ids.filtered(
            lambda l: l.active and l.purchase_type in ("hire", "lease") and l.contract_id
        ).mapped("contract_id").ids
        extra_contracts = Contract.search([
            ("id", "in", plan_contract_ids),
            ("state", "=", "confirmed"),
            ("date_end", "!=", False),
            ("date_end", ">=", today),
            ("date_end", "<=", limit_date),
        ])
        contracts |= extra_contracts

        for contract in contracts:
            plan_line = self.line_ids.filtered(
                lambda l: l.active
                and l.contract_id == contract
                and l.purchase_type in ("hire", "lease")
            )[:1]
            if not plan_line:
                amd = self._ensure_amendment_for_contract(contract)
                if amd:
                    amendments |= amd
                continue

            existing = PR.search([
                ("procurement_plan_id", "=", self.id),
                ("is_auto_generated", "=", True),
                ("contract_id", "=", contract.id),
                ("state", "in", ("draft", "to_approve", "approved", "in_progress")),
                ("auto_gen_source", "=", "contract_expiry"),
            ], limit=1)
            if existing:
                continue

            product = plan_line.product_id
            if not product and contract.installment_ids:
                product = contract.installment_ids[:1].product_id
            line_vals = {
                "name": _("ต่ออายุสัญญา %s (หมดอายุ %s)")
                % (contract.name, contract.date_end),
                "product_qty": plan_line.qty_planned or 1.0,
                "estimated_cost": plan_line.amount_planned or contract.amount_total,
                "procurement_plan_line_id": plan_line.id,
            }
            if product:
                line_vals["product_id"] = product.id
                line_vals["product_uom_id"] = product.uom_id.id

            pr_vals = self._prepare_auto_pr_vals(
                origin="AUTO-CTR/%s/%s" % (contract.name, today),
                description=_(
                    "สร้างอัตโนมัติจากสัญญาใกล้หมดอายุ — แผน %s"
                ) % self.name,
                extra={
                    "auto_gen_source": "contract_expiry",
                    "contract_id": contract.id,
                    "line_ids": [(0, 0, line_vals)],
                },
            )
            pr = PR.create(pr_vals)
            created |= pr
            plan_line._recompute_consumed()

        return created, amendments

    def _ensure_amendment_for_product(self, product, purchase_type, orderpoint=None):
        Amendment = self.env["procurement.plan.amendment"]
        existing = Amendment.search([
            ("plan_id", "=", self.id),
            ("state", "in", ("draft", "submitted")),
            ("line_ids.product_id", "=", product.id),
        ], limit=1)
        if existing:
            return existing
        qty = 0.0
        if orderpoint:
            qty = max(
                orderpoint.product_max_qty - orderpoint.qty_on_hand,
                orderpoint.product_min_qty - orderpoint.qty_on_hand,
                0,
            )
        return Amendment.create({
            "plan_id": self.id,
            "reason": _(
                "สินค้า %s ถึงจุดสั่งซื้อ แต่ไม่อยู่ในแผนจัดซื้อจัดจ้างประจำปี — "
                "ต้องขออนุมัติเพิ่มแผนก่อนสร้าง PR"
            ) % product.display_name,
            "source_type": "orderpoint",
            "line_ids": [(0, 0, {
                "product_id": product.id,
                "purchase_type": purchase_type,
                "qty_requested": qty or 1.0,
                "amount_requested": 0.0,
                "name": product.display_name,
            })],
        })

    def _ensure_amendment_for_contract(self, contract):
        Amendment = self.env["procurement.plan.amendment"]
        existing = Amendment.search([
            ("plan_id", "=", self.id),
            ("state", "in", ("draft", "submitted")),
            ("line_ids.contract_id", "=", contract.id),
        ], limit=1)
        if existing:
            return existing
        ctype = getattr(contract, "contract_kind", False) or "hire"
        return Amendment.create({
            "plan_id": self.id,
            "reason": _(
                "สัญญา %s ใกล้หมดอายุ (%s) แต่ไม่อยู่ในแผน — "
                "ต้องขออนุมัติเพิ่มแผนก่อนสร้าง PR ต่ออายุ"
            ) % (contract.name, contract.date_end),
            "source_type": "contract_expiry",
            "line_ids": [(0, 0, {
                "contract_id": contract.id,
                "purchase_type": ctype if ctype in ("hire", "lease") else "hire",
                "qty_requested": 1.0,
                "amount_requested": contract.amount_total,
                "name": _("ต่ออายุ %s") % contract.name,
                "product_id": (
                    contract.installment_ids[:1].product_id.id
                    if contract.installment_ids
                    else False
                ),
            })],
        })


class ProcurementAnnualPlanLine(models.Model):
    _name = "procurement.annual.plan.line"
    _description = "รายการแผนจัดซื้อจัดจ้าง"
    _order = "sequence, id"

    plan_id = fields.Many2one(
        comodel_name="procurement.annual.plan",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="รายละเอียด", required=True)
    purchase_type = fields.Selection(
        selection=[
            ("buy", "ซื้อ"),
            ("hire", "จ้าง"),
            ("lease", "เช่า"),
        ],
        string="ประเภท",
        required=True,
        default="buy",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า/บริการ",
    )
    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญาอ้างอิง",
        help="สำหรับรายการจ้าง/เช่าที่อ้างอิงสัญญาที่มีอยู่",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จำหน่ายที่คาดการณ์",
        domain="[('supplier_rank', '>', 0)]",
    )
    qty_planned = fields.Float(
        string="จำนวนตามแผน",
        digits="Product Unit of Measure",
        default=1.0,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วย",
    )
    unit_price = fields.Float(string="ราคาต่อหน่วยโดยประมาณ")
    amount_planned = fields.Float(
        string="วงเงินตามแผน",
        compute="_compute_amount_planned",
        store=True,
        readonly=False,
    )
    qty_consumed = fields.Float(
        string="จำนวนที่ใช้แล้ว (PR)",
        digits="Product Unit of Measure",
        compute="_compute_consumed",
        store=True,
    )
    amount_consumed = fields.Float(
        string="วงเงินที่ใช้แล้ว",
        compute="_compute_consumed",
        store=True,
    )
    qty_remaining = fields.Float(
        string="จำนวนคงเหลือ",
        compute="_compute_consumed",
        store=True,
    )
    budget_line_id = fields.Many2one(
        comodel_name="budget.lines",
        string="รายการงบประมาณ",
    )
    period_start = fields.Date(string="ช่วงแผน: เริ่ม")
    period_end = fields.Date(string="ช่วงแผน: สิ้นสุด")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related="plan_id.company_id", store=True)

    @api.depends("qty_planned", "unit_price")
    def _compute_amount_planned(self):
        for line in self:
            if line.unit_price:
                line.amount_planned = line.qty_planned * line.unit_price

    @api.depends(
        "plan_id",
        "product_id",
        "qty_planned",
        "amount_planned",
    )
    def _compute_consumed(self):
        for line in self:
            line._recompute_consumed()

    def _recompute_consumed(self):
        PRLine = self.env["purchase.request.line"]
        for line in self:
            pr_lines = PRLine.search([
                ("procurement_plan_line_id", "=", line.id),
                ("request_id.state", "not in", ("rejected", "cancelled")),
                ("cancelled", "=", False),
            ]) if line.id else PRLine.browse()
            line.qty_consumed = sum(pr_lines.mapped("product_qty"))
            line.amount_consumed = sum(pr_lines.mapped("estimated_cost"))
            line.qty_remaining = max(line.qty_planned - line.qty_consumed, 0.0)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.uom_id = self.product_id.uom_po_id or self.product_id.uom_id
