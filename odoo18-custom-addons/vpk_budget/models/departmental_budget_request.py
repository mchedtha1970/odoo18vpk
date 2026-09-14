from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DepartmentalBudgetRequest(models.Model):
    _name = "departmental.budget.request"
    _description = "Departmental Budget Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        default=lambda self: _("New"),
        copy=False,
        tracking=True,
    )
    request_date = fields.Date(
        string="วันที่ขอ",
        default=fields.Date.context_today,
        tracking=True,
    )
    fiscal_year = fields.Char(
        string="ปีงบประมาณ",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year + 543),
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    requester_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ขอ",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน / ศูนย์ต้นทุน",
        required=True,
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="แหล่งเงิน",
        required=True,
        tracking=True,
    )
    annual_budget_id = fields.Many2one(
        comodel_name="budget.budget",
        string="ชื่อแผนงบประมาณประจำปี",
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]",
    )
    form_type_id = fields.Many2one(
        comodel_name="vpk.budget.request.form.type",
        string="แบบฟอร์มคำของบ",
        required=True,
        tracking=True,
    )
    form_type_code = fields.Char(
        related="form_type_id.code",
        store=True,
        readonly=True,
    )
    show_asset_lines = fields.Boolean(compute="_compute_form_line_sections")
    show_material_lines = fields.Boolean(compute="_compute_form_line_sections")
    show_construction_lines = fields.Boolean(compute="_compute_form_line_sections")
    show_project_lines = fields.Boolean(compute="_compute_form_line_sections")
    is_form_type_locked = fields.Boolean(compute="_compute_is_form_type_locked")
    budget_record_id = fields.Many2one(
        comodel_name="budget.budget",
        string="Created Budget",
        readonly=True,
        copy=False,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted to Budget Unit"),
            ("received", "Received by Budget Unit"),
            ("review", "Under Internal Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="สถานะ",
        default="draft",
        tracking=True,
    )
    can_edit_request_content = fields.Boolean(compute="_compute_edit_flags")
    can_edit_allocation = fields.Boolean(compute="_compute_edit_flags")
    submission_date = fields.Datetime(readonly=True, tracking=True)
    request_justification = fields.Text(
        string="เหตุผลประกอบคำขอตั้ง",
        tracking=True,
    )
    review_note = fields.Text(string="Review Note")
    total_amount = fields.Float(
        string="งบประมาณที่ขอ",
        digits=0,
        readonly=False,
        copy=False,
    )
    total_received_budget_amount = fields.Float(
        string="งบประมาณที่ได้รับ",
        digits=0,
        readonly=False,
        copy=False,
    )
    line_ids = fields.One2many(
        comodel_name="departmental.budget.request.line",
        inverse_name="request_id",
        copy=True,
    )
    asset_line_ids = fields.One2many(
        comodel_name="departmental.budget.request.line",
        inverse_name="request_id",
        domain=[("budget_type_id.section_key", "=", "asset")],
        copy=True,
    )
    material_line_ids = fields.One2many(
        comodel_name="departmental.budget.request.line",
        inverse_name="request_id",
        domain=[("budget_type_id.section_key", "=", "material")],
        copy=True,
    )
    material_detail_ids = fields.One2many(
        comodel_name="departmental.budget.request.material.detail",
        inverse_name="request_id",
        string="รายละเอียดสินค้า",
        copy=True,
    )
    has_material_details = fields.Boolean(
        compute="_compute_material_detail_totals",
    )
    material_detail_total = fields.Float(
        string="รวมมูลค่ารายละเอียดสินค้า",
        compute="_compute_material_detail_totals",
        digits=0,
    )
    construction_line_ids = fields.One2many(
        comodel_name="departmental.budget.request.line",
        inverse_name="request_id",
        domain=[("budget_type_id.section_key", "=", "construction")],
        copy=True,
    )
    project_line_ids = fields.One2many(
        comodel_name="departmental.budget.request.line",
        inverse_name="request_id",
        domain=[("budget_type_id.section_key", "=", "project")],
        copy=True,
    )
    material_sub_type_ids = fields.Many2many(
        comodel_name="vpk.budget.material.sub.type",
        relation="departmental_budget_request_material_sub_type_rel",
        column1="request_id",
        column2="material_sub_type_id",
        string="ประเภทวัสดุ",
        compute="_compute_material_sub_type_ids",
        store=True,
        readonly=True,
    )
    budget_group_ids = fields.Many2many(
        comodel_name="vpk.budget.group",
        relation="departmental_budget_request_budget_group_rel",
        column1="request_id",
        column2="budget_group_id",
        string="กลุ่มวัสดุ",
        compute="_compute_budget_group_ids",
        store=True,
        readonly=True,
    )
    asset_type_ids = fields.Many2many(
        comodel_name="vpk.budget.asset.type",
        relation="departmental_budget_request_asset_type_rel",
        column1="request_id",
        column2="asset_type_id",
        string="ประเภทครุภัณฑ์",
        compute="_compute_asset_header_fields",
        store=True,
        readonly=True,
    )
    asset_category_ids = fields.Many2many(
        comodel_name="vpk.budget.asset.category",
        relation="departmental_budget_request_asset_category_rel",
        column1="request_id",
        column2="asset_category_id",
        string="กลุ่มครุภัณฑ์",
        compute="_compute_asset_header_fields",
        store=True,
        readonly=True,
    )
    usage_history_year_y1 = fields.Char(compute="_compute_usage_history_years")
    usage_history_year_y2 = fields.Char(compute="_compute_usage_history_years")
    usage_history_year_y3 = fields.Char(compute="_compute_usage_history_years")
    usage_history_prior_year = fields.Char(compute="_compute_usage_history_years")
    usage_history_be_y1 = fields.Char(
        string="ปี พ.ศ. 1 ปีก่อน",
        compute="_compute_usage_history_years",
    )
    usage_history_be_y2 = fields.Char(
        string="ปี พ.ศ. 2 ปีก่อน",
        compute="_compute_usage_history_years",
    )
    usage_history_be_y3 = fields.Char(
        string="ปี พ.ศ. 3 ปีก่อน",
        compute="_compute_usage_history_years",
    )
    plan_year_be = fields.Char(
        string="ปี พ.ศ. แผนที่ขอ",
        compute="_compute_usage_history_years",
    )

    @api.model
    def get_budget_dashboard_data(self, fiscal_year=None):
        years = [
            year
            for year in self.search([], order="fiscal_year desc").mapped("fiscal_year")
            if year
        ]
        years = list(dict.fromkeys(years))
        fiscal_year = fiscal_year or (years[0] if years else str(fields.Date.context_today(self).year + 543))

        requests = self.search([("fiscal_year", "=", fiscal_year)])
        active_requests = requests.filtered(lambda request: request.state != "rejected")
        lines = active_requests.mapped("line_ids")

        state_labels = {
            "draft": "แบบร่าง",
            "submitted": "ส่งหน่วยงบประมาณ",
            "received": "รับเรื่องแล้ว",
            "review": "อยู่ระหว่างพิจารณา",
            "approved": "อนุมัติแล้ว",
            "rejected": "ไม่อนุมัติ",
        }
        state_colors = {
            "draft": "#3b82f6",
            "submitted": "#f59e0b",
            "received": "#8b5cf6",
            "review": "#06b6d4",
            "approved": "#10b981",
            "rejected": "#ef4444",
        }
        state_totals = {state: 0.0 for state, _label in self._fields["state"].selection}
        state_counts = {state: 0 for state, _label in self._fields["state"].selection}
        for request in requests:
            state_totals[request.state] = state_totals.get(request.state, 0.0) + request.total_amount
            state_counts[request.state] = state_counts.get(request.state, 0) + 1

        total_requested = sum(active_requests.mapped("total_amount"))
        approved_total = state_totals.get("approved", 0.0)
        in_progress_total = (
            state_totals.get("submitted", 0.0)
            + state_totals.get("received", 0.0)
            + state_totals.get("review", 0.0)
        )
        draft_total = state_totals.get("draft", 0.0)

        category_totals = {
            "material": {"label": "วัสดุ", "amount": 0.0, "color": "#22c55e"},
            "asset_above": {"label": "ครุภัณฑ์ 100,000 บาทขึ้นไป", "amount": 0.0, "color": "#3b82f6"},
            "asset_below": {"label": "ครุภัณฑ์ต่ำกว่า 100,000 บาท", "amount": 0.0, "color": "#8b5cf6"},
            "construction": {"label": "สิ่งก่อสร้าง", "amount": 0.0, "color": "#f59e0b"},
            "project": {"label": "โครงการ", "amount": 0.0, "color": "#14b8a6"},
        }
        department_totals = {}
        for line in lines:
            amount = line.total_amount or 0.0
            section = line.section_key
            category_key = section
            if section == "asset":
                form_label = "%s %s" % (
                    line.request_id.form_type_id.name or "",
                    line.request_id.form_type_id.code or "",
                )
                normalized = form_label.replace(",", "").replace(" ", "")
                category_key = (
                    "asset_below"
                    if "ต่ำกว่าแสน" in normalized or "100000" in normalized
                    else "asset_above"
                )
            if category_key in category_totals:
                category_totals[category_key]["amount"] += amount

            department = line.request_id.analytic_account_id
            if department:
                dept_vals = department_totals.setdefault(
                    department.id,
                    {
                        "id": department.id,
                        "name": department.name,
                        "amount": 0.0,
                        "request_count": set(),
                    },
                )
                dept_vals["amount"] += amount
                dept_vals["request_count"].add(line.request_id.id)

        department_rows = []
        for vals in department_totals.values():
            department_rows.append(
                {
                    "id": vals["id"],
                    "name": vals["name"],
                    "amount": vals["amount"],
                    "request_count": len(vals["request_count"]),
                }
            )
        department_rows = sorted(
            department_rows,
            key=lambda item: item["amount"],
            reverse=True,
        )[:8]

        month_labels = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
        monthly_amounts = [0.0] * 12
        for request in active_requests:
            if request.request_date:
                monthly_amounts[request.request_date.month - 1] += request.total_amount or 0.0
        cumulative = []
        running = 0.0
        max_value = 0.0
        for index, amount in enumerate(monthly_amounts):
            running += amount
            max_value = max(max_value, running)
            cumulative.append({"label": month_labels[index], "amount": running})

        recent_requests = []
        for request in requests.sorted(lambda req: (req.request_date or fields.Date.today(), req.id), reverse=True)[:6]:
            recent_requests.append(
                {
                    "id": request.id,
                    "name": request.name,
                    "department": request.analytic_account_id.name or "",
                    "form_type": request.form_type_id.name or "",
                    "amount": request.total_amount,
                    "state": request.state,
                    "state_label": state_labels.get(request.state, request.state),
                }
            )

        state_breakdown = [
            {
                "state": state,
                "label": state_labels.get(state, state),
                "amount": state_totals.get(state, 0.0),
                "count": state_counts.get(state, 0),
                "color": state_colors.get(state, "#64748b"),
            }
            for state, _label in self._fields["state"].selection
            if state_counts.get(state, 0)
        ]
        category_breakdown = [
            {
                "key": key,
                "label": vals["label"],
                "amount": vals["amount"],
                "color": vals["color"],
            }
            for key, vals in category_totals.items()
            if vals["amount"]
        ]

        return {
            "fiscal_year": fiscal_year,
            "year_options": years or [fiscal_year],
            "cards": [
                {"label": "คำของบทั้งหมด", "amount": total_requested, "icon": "fa-folder-open", "color": "#3b82f6"},
                {"label": "อนุมัติแล้ว", "amount": approved_total, "icon": "fa-check-circle", "color": "#10b981"},
                {"label": "อยู่ระหว่างดำเนินการ", "amount": in_progress_total, "icon": "fa-clock-o", "color": "#f59e0b"},
                {"label": "แบบร่าง", "amount": draft_total, "icon": "fa-pencil-square-o", "color": "#8b5cf6"},
            ],
            "state_breakdown": state_breakdown,
            "category_breakdown": category_breakdown,
            "department_rows": department_rows,
            "recent_requests": recent_requests,
            "trend": {
                "points": cumulative,
                "max": max_value or 1.0,
            },
        }

    @api.depends(
        "form_type_id",
        "form_type_id.line_type_ids",
        "form_type_id.line_type_ids.budget_type_id",
        "form_type_id.line_type_ids.section_key",
    )
    def _compute_form_line_sections(self):
        exclusive_by_code = {
            "asset": "asset",
            "material_budget": "material",
            "construction": "construction",
            "project": "project",
        }
        for rec in self:
            form_type = rec.form_type_id
            exclusive = exclusive_by_code.get(form_type.code) if form_type else False
            if exclusive:
                rec.show_asset_lines = exclusive == "asset"
                rec.show_material_lines = exclusive == "material"
                rec.show_construction_lines = exclusive == "construction"
                rec.show_project_lines = exclusive == "project"
                continue
            rec.show_asset_lines = form_type.has_section("asset") if form_type else False
            rec.show_material_lines = (
                form_type.has_section("material") if form_type else False
            )
            rec.show_construction_lines = (
                form_type.has_section("construction") if form_type else False
            )
            rec.show_project_lines = (
                form_type.has_section("project") if form_type else False
            )

    @api.depends_context("default_form_type_id")
    def _compute_is_form_type_locked(self):
        locked = bool(self.env.context.get("default_form_type_id"))
        for rec in self:
            rec.is_form_type_locked = locked and not rec.id

    def _form_has_budget_type_code(self, code):
        self.ensure_one()
        if not self.form_type_id:
            return False
        return code in self.form_type_id.line_type_ids.mapped("line_type")

    def _form_has_line_type(self, *line_types):
        return any(self._form_has_budget_type_code(code) for code in line_types)

    @api.model
    def _fiscal_year_to_be(self, fiscal_year):
        try:
            year = int(fiscal_year)
        except (TypeError, ValueError):
            return 0
        return year + 543 if year < 2400 else year

    @api.model
    def _fiscal_year_to_ce(self, fiscal_year):
        try:
            year = int(fiscal_year)
        except (TypeError, ValueError):
            return 0
        return year if year < 2400 else year - 543

    @api.constrains("fiscal_year")
    def _check_fiscal_year(self):
        for rec in self:
            ce_year = rec._fiscal_year_to_ce(rec.fiscal_year)
            if not ce_year or ce_year < 2000 or ce_year > 2100:
                raise ValidationError(
                    _(
                        "ปีงบประมาณไม่ถูกต้อง กรุณาระบุเป็น ค.ศ. (เช่น 2026) "
                        "หรือ พ.ศ. (เช่น 2569)"
                    )
                )

    @api.depends("fiscal_year")
    def _compute_usage_history_years(self):
        for rec in self:
            ce_current = rec._fiscal_year_to_ce(rec.fiscal_year)
            be_current = rec._fiscal_year_to_be(rec.fiscal_year)
            rec.usage_history_prior_year = str(ce_current - 1) if ce_current else ""
            rec.usage_history_year_y1 = str(ce_current - 1) if ce_current else ""
            rec.usage_history_year_y2 = str(ce_current - 2) if ce_current else ""
            rec.usage_history_year_y3 = str(ce_current - 3) if ce_current else ""
            rec.usage_history_be_y1 = str(be_current - 1) if be_current else ""
            rec.usage_history_be_y2 = str(be_current - 2) if be_current else ""
            rec.usage_history_be_y3 = str(be_current - 3) if be_current else ""
            rec.plan_year_be = str(be_current) if be_current else ""

    @api.model
    def _fiscal_period_from_be_year(self, be_year):
        try:
            be_year = int(be_year)
        except (TypeError, ValueError):
            return False, False
        if be_year < 2400:
            be_year = be_year + 543
        ce_end = be_year - 543
        ce_start = ce_end - 1
        return (
            fields.Date.from_string(f"{ce_start}-10-01"),
            fields.Date.from_string(f"{ce_end}-06-30"),
        )

    @api.model
    def _fiscal_period_from_ce_year(self, ce_year):
        try:
            ce_year = int(ce_year)
        except (TypeError, ValueError):
            return False, False
        ce_start = ce_year - 1
        return (
            fields.Date.from_string(f"{ce_start}-10-01"),
            fields.Date.from_string(f"{ce_year}-06-30"),
        )

    def _get_current_fiscal_period(self):
        self.ensure_one()
        return self._fiscal_period_from_be_year(self.fiscal_year)

    @api.depends("line_ids.material_sub_type_id", "line_ids.line_type")
    def _compute_material_sub_type_ids(self):
        for rec in self:
            material_types = rec.line_ids.filtered(
                lambda line: line.line_type == "supplies_budget"
            ).mapped("material_sub_type_id")
            rec.material_sub_type_ids = material_types

    @api.depends("line_ids.budget_group_id", "line_ids.line_type")
    def _compute_budget_group_ids(self):
        for rec in self:
            budget_groups = rec.line_ids.filtered(
                lambda line: line.line_type == "supplies_budget"
            ).mapped("budget_group_id")
            rec.budget_group_ids = budget_groups

    @api.depends(
        "asset_line_ids.asset_type_ids",
        "asset_line_ids.asset_categ_id",
        "line_ids.asset_type_ids",
        "line_ids.asset_categ_id",
        "line_ids.line_type",
    )
    def _compute_asset_header_fields(self):
        for rec in self:
            asset_lines = rec.line_ids.filtered(
                lambda line: line.section_key == "asset"
                or line.line_type == "asset_budget"
            )
            rec.asset_type_ids = asset_lines.mapped("asset_type_ids")
            rec.asset_category_ids = asset_lines.mapped("asset_categ_id")

    def _get_all_request_lines(self):
        """Collect lines from all section One2many fields (needed during onchange)."""
        self.ensure_one()
        return (
            self.line_ids
            | self.asset_line_ids
            | self.material_line_ids
            | self.construction_line_ids
            | self.project_line_ids
        )

    @api.depends(
        "material_detail_ids",
        "material_detail_ids.total_amount",
        "material_detail_ids.quantity",
        "material_detail_ids.unit_price",
    )
    def _compute_material_detail_totals(self):
        for rec in self:
            details = rec.material_detail_ids
            rec.has_material_details = bool(details)
            rec.material_detail_total = sum(details.mapped("total_amount"))

    def _material_detail_amounts_by_subtype(self):
        self.ensure_one()
        amounts = {}
        for detail in self.material_detail_ids:
            subtype_id = detail.material_sub_type_id.id
            if not subtype_id:
                continue
            amounts[subtype_id] = amounts.get(subtype_id, 0.0) + (
                detail.total_amount or 0.0
            )
        return amounts

    def _apply_material_detail_amounts_in_memory(self):
        """Update material line requested amounts from detail lines (UI onchange)."""
        for rec in self:
            if not rec.material_detail_ids:
                continue
            amounts = rec._material_detail_amounts_by_subtype()
            for line in rec.material_line_ids:
                subtype_id = line.material_sub_type_id.id
                if subtype_id and subtype_id in amounts:
                    line.requested_plan_amount = amounts[subtype_id]
                    line.total_amount = amounts[subtype_id]

    def _sync_material_amounts_from_details(self):
        """Persist material requested amounts from product detail lines."""
        Line = self.env["departmental.budget.request.line"]
        for rec in self:
            if not rec.material_detail_ids:
                rec._sync_header_totals()
                continue
            amounts = rec._material_detail_amounts_by_subtype()
            for line in rec.material_line_ids:
                subtype_id = line.material_sub_type_id.id
                if not subtype_id or subtype_id not in amounts:
                    continue
                amount = amounts[subtype_id]
                if line.requested_plan_amount != amount:
                    Line.browse(line.id).with_context(
                        skip_material_detail_sync=True,
                        skip_budget_request_lock=True,
                    ).write({"requested_plan_amount": amount})
            rec._sync_header_totals()

    def _line_header_requested_amount(self, line):
        if line._is_asset_line():
            qty = line._get_asset_request_quantity() or line.requested_quantity or 0.0
            return qty * (line.unit_price or 0.0)
        if line.section_key == "material" or line.line_type == "supplies_budget":
            return line.requested_plan_amount or line.total_amount or 0.0
        return line.total_amount or 0.0

    def _line_header_received_amount(self, line):
        # ครุภัณฑ์: ไม่ดึงยอดคำขอตั้งงบไปเป็นงบที่ได้รับ — ใช้เฉพาะยอดที่ระบุใน allocated
        return line.allocated_budget_amount or 0.0

    def _calculate_header_totals(self):
        self.ensure_one()
        requested = 0.0
        received = 0.0
        for line in self._get_all_request_lines():
            requested += self._line_header_requested_amount(line)
            received += self._line_header_received_amount(line)
        return requested, received

    def _refresh_header_totals_from_lines(self):
        """Update header totals from in-memory lines (UI onchange)."""
        for rec in self:
            lines = rec._get_all_request_lines()
            requested = 0.0
            received = 0.0
            for line in lines:
                line_requested = rec._line_header_requested_amount(line)
                line_received = rec._line_header_received_amount(line)
                if line._is_asset_line():
                    line.requested_quantity = line._get_asset_request_quantity()
                    line.total_amount = line_requested
                    # ไม่คัดลอกคำขอตั้งงบไปใส่ allocated_budget_amount
                requested += line_requested
                received += line_received
            rec.total_amount = requested
            rec.total_received_budget_amount = received

    def _sync_header_totals(self):
        """Persist header totals from saved lines."""
        for rec in self:
            requested, received = rec._calculate_header_totals()
            if (
                rec.total_amount != requested
                or rec.total_received_budget_amount != received
            ):
                super(DepartmentalBudgetRequest, rec).write(
                    {
                        "total_amount": requested,
                        "total_received_budget_amount": received,
                    }
                )

    @api.onchange(
        "line_ids",
        "asset_line_ids",
        "material_line_ids",
        "construction_line_ids",
        "project_line_ids",
    )
    def _onchange_request_line_totals(self):
        self._refresh_header_totals_from_lines()

    @api.onchange("material_detail_ids")
    def _onchange_material_detail_ids(self):
        self._apply_material_detail_amounts_in_memory()
        self._refresh_header_totals_from_lines()

    def _get_material_print_fiscal_years(self):
        self.ensure_one()
        try:
            current_year = int(self.fiscal_year)
        except (TypeError, ValueError):
            current_year = 0
        prior_year = current_year - 1 if current_year else 0

        def fiscal_period(year):
            if not year:
                return ""
            short_year = year % 100
            return f"ต.ค.{short_year - 1:02d}- มิ.ย.{short_year:02d}"

        return {
            "current_year": current_year,
            "prior_year": prior_year,
            "current_period": fiscal_period(current_year),
            "prior_period": fiscal_period(prior_year),
        }

    def _get_material_print_lines(self):
        self.ensure_one()
        return self.material_line_ids.sorted(
            key=lambda line: (
                line.material_sub_type_id.sequence or 0,
                line.material_sub_type_id.id or 0,
                line.sequence,
                line.id,
            )
        )

    def _get_material_print_type_label(self):
        self.ensure_one()
        names = self.material_sub_type_ids.mapped("name")
        return " ".join(names) if names else "-"

    def action_print_material_budget(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_budget.action_report_departmental_budget_material"
        ).report_action(self)

    def action_apply_usage_history(self):
        self.line_ids.action_apply_usage_history_to_material_line()
        return True

    @api.model
    def _demo_seed_amount(self, seed):
        seed = seed or 1
        return round(800_000 + (seed * 47_500) % 28_000_000, 2)

    def _get_demo_budget_post(self):
        self.ensure_one()
        budget_post = self.line_ids.budget_post_id[:1]
        if not budget_post:
            budget_post = self.env["account.budget.post"].search(
                [
                    ("company_id", "in", [False, self.company_id.id]),
                    ("account_ids", "!=", False),
                ],
                limit=1,
            )
        if not budget_post or not budget_post.account_ids:
            raise ValidationError(_("ไม่พบหมวดงบประมาณที่มีบัญชี GL สำหรับสร้างข้อมูลตัวอย่าง"))
        return budget_post

    def _create_demo_analytic_lines_for_line(self, line, current_be, year_multipliers):
        general_account = line.budget_post_id.account_ids[:1]
        if not general_account:
            return 0

        seed = (
            line.material_sub_type_id.id
            if line.line_type == "supplies_budget" and line.material_sub_type_id
            else line.id
        )
        base_amount = (
            line.prior_year_plan_amount
            or line.disbursed_amount
            or line.requested_plan_amount
            or line.total_amount
            or self._demo_seed_amount(seed)
        )
        base_amount = round(base_amount * (0.85 + (seed % 7) * 0.03), 2)

        analytic_line_model = self.env["account.analytic.line"].sudo()
        created = 0
        for year_offset, multiplier in year_multipliers:
            be_year = current_be - year_offset
            ce_year = be_year - 543
            date_from, date_to = self._fiscal_period_from_be_year(be_year)
            if not date_from or not date_to:
                continue
            demo_date = fields.Date.from_string(f"{ce_year}-03-15")
            amount = round(base_amount * multiplier, 2)
            subtype_id = (
                line.material_sub_type_id.id
                if line.line_type == "supplies_budget" and line.material_sub_type_id
                else False
            )
            ref = (
                f"mst{subtype_id}"
                if subtype_id
                else f"line{line.id}"
            )
            analytic_line_model.create(
                {
                    "name": (
                        f"DEMO_USAGE:{self.name}:{ref}:FY{ce_year}"
                    ),
                    "date": demo_date,
                    "amount": amount,
                    "account_id": self.analytic_account_id.id,
                    "general_account_id": general_account.id,
                    "company_id": self.company_id.id,
                    "material_sub_type_id": subtype_id,
                }
            )
            created += 1
        return created

    def _run_demo_usage_history_seed(self):
        self.ensure_one()
        if not self.analytic_account_id:
            raise ValidationError(_("กรุณาระบุหน่วยงาน / ศูนย์ต้นทุนก่อนสร้างข้อมูลตัวอย่าง"))
        if not self.line_ids:
            raise ValidationError(_("กรุณาเพิ่มรายการคำของบก่อนสร้างข้อมูลตัวอย่าง"))

        current_be = self._fiscal_year_to_be(self.fiscal_year)
        if not current_be:
            raise ValidationError(_("กรุณาระบุปีงบประมาณเป็นตัวเลข"))

        analytic_line_model = self.env["account.analytic.line"].sudo()
        analytic_line_model.search(
            [
                ("account_id", "=", self.analytic_account_id.id),
                ("name", "like", "DEMO_USAGE:%"),
            ]
        ).unlink()

        year_multipliers = (
            (3, 0.65),
            (2, 0.82),
            (1, 1.0),
        )
        created = 0
        for line in self.line_ids:
            created += self._create_demo_analytic_lines_for_line(
                line, current_be, year_multipliers
            )
        return created

    def action_create_demo_usage_history(self):
        created = self._run_demo_usage_history_seed()
        return self._demo_notification(
            _("สร้างข้อมูลตัวอย่างสำเร็จ"),
            _("สร้างรายการบัญชีวิเคราะห์ตัวอย่าง %s รายการ") % created,
        )

    def _prepare_all_material_demo_lines(self):
        self.ensure_one()
        if not self._form_has_line_type("supplies_budget"):
            raise ValidationError(_("ใช้ได้เฉพาะคำของบที่กำหนด Line Type แบบตั้งงบวัสดุ"))
        if self.state != "draft":
            raise ValidationError(_("ใช้ได้เฉพาะคำของบสถานะ Draft"))
        if not self.analytic_account_id:
            raise ValidationError(_("กรุณาระบุหน่วยงาน / ศูนย์ต้นทุนก่อนสร้างข้อมูลตัวอย่าง"))

        budget_post = self._get_demo_budget_post()
        sub_types = self.env["vpk.budget.material.sub.type"].search(
            [("active", "=", True)],
            order="budget_group_id, sequence, id",
        )
        if not sub_types:
            raise ValidationError(_("ไม่พบประเภทวัสดุย่อยในระบบ"))

        self.material_line_ids.unlink()

        line_commands = []
        for index, sub_type in enumerate(sub_types, start=1):
            base_amount = self._demo_seed_amount(sub_type.id)
            line_commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": index * 10,
                        "budget_type_id": self._budget_type_from_code("supplies_budget").id,
                        "budget_post_id": budget_post.id,
                        "budget_group_id": sub_type.budget_group_id.id,
                        "material_sub_type_id": sub_type.id,
                        "prior_year_plan_amount": round(base_amount * 1.1, 2),
                        "disbursed_amount": round(base_amount, 2),
                        "payable_amount": round(base_amount * 0.05, 2),
                        "committed_not_received_amount": round(base_amount * 0.03, 2),
                        "stock_amount": round(base_amount * 0.08, 2),
                        "requested_plan_amount": round(base_amount * 1.15, 2),
                    },
                )
            )
        self.write({"material_line_ids": line_commands})
        return len(sub_types)

    def action_create_demo_all_budget_groups(self):
        line_count = self._prepare_all_material_demo_lines()
        analytic_count = self._run_demo_usage_history_seed()
        return self._demo_notification(
            _("สร้างข้อมูลตัวอย่างครบทุกกลุ่มงบประมาณ"),
            _("สร้างรายการ %s ประเภท และบัญชีวิเคราะห์ %s รายการ") % (line_count, analytic_count),
        )

    @api.model
    def action_create_demo_budget_request_all_groups(self):
        form_type = self.env["vpk.budget.request.form.type"].search(
            [("code", "=", "material_budget")], limit=1
        )
        if not form_type:
            raise ValidationError(_("ไม่พบแบบฟอร์มคำของบแบบตั้งงบวัสดุ"))

        company = self.env.company
        analytic_account = self.env["account.analytic.account"].search(
            [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        annual_budget = self.env["budget.budget"].search(
            [("company_id", "=", company.id)], limit=1
        )
        fund_source = self.env["vpk.budget.fund.source"].search([], limit=1)
        if not analytic_account or not annual_budget or not fund_source:
            raise ValidationError(
                _("กรุณาตั้งค่าหน่วยงาน แผนงบประมาณประจำปี และแหล่งเงินก่อนสร้างข้อมูลตัวอย่าง")
            )

        ce_year = fields.Date.context_today(self).year
        request = self.create(
            {
                "request_date": fields.Date.context_today(self),
                "fiscal_year": str(ce_year),
                "company_id": company.id,
                "requester_id": self.env.user.id,
                "analytic_account_id": analytic_account.id,
                "annual_budget_id": annual_budget.id,
                "form_type_id": form_type.id,
                "fund_source_id": fund_source.id,
                "request_justification": _("ข้อมูลตัวอย่างครบทุกกลุ่มงบประมาณสำหรับทดสอบระบบ"),
            }
        )
        request._prepare_all_material_demo_lines()
        request._run_demo_usage_history_seed()
        return {
            "type": "ir.actions.act_window",
            "res_model": "departmental.budget.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }

    def _demo_notification(self, title, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    @api.depends("state")
    def _compute_edit_flags(self):
        is_budget_unit = self.env.user.has_group(
            "vpk_budget.group_budget_request_budget_unit"
        )
        for rec in self:
            rec.can_edit_request_content = rec.state == "draft"
            rec.can_edit_allocation = bool(
                is_budget_unit and rec.state in ("received", "review")
            )

    def _budget_request_lock_enabled(self):
        return not self.env.su and not self.env.context.get("skip_budget_request_lock")

    def _user_is_budget_unit(self):
        return self.env.user.has_group("vpk_budget.group_budget_request_budget_unit")

    def _check_header_write_allowed(self, vals):
        if not self._budget_request_lock_enabled():
            return
        ignored = {
            "message_ids",
            "message_follower_ids",
            "activity_ids",
            "total_amount",
            "total_received_budget_amount",
        }
        content_vals = {key: value for key, value in vals.items() if key not in ignored}
        if not content_vals:
            return
        is_budget_unit = self._user_is_budget_unit()
        workflow_fields = {"state", "submission_date", "budget_record_id", "review_note"}
        line_command_fields = {
            "line_ids",
            "asset_line_ids",
            "material_line_ids",
            "construction_line_ids",
            "project_line_ids",
            "material_detail_ids",
        }
        for rec in self:
            if rec.state == "draft":
                continue
            if not is_budget_unit:
                raise ValidationError(
                    _("ไม่สามารถแก้ไขคำของบหลังส่งเรื่องได้")
                )
            if rec.state in ("approved", "rejected"):
                if set(content_vals) - workflow_fields:
                    raise ValidationError(
                        _("คำของบที่อนุมัติหรือตีกลับแล้ว ไม่สามารถแก้ไขรายการได้")
                    )
                continue
            allowed = workflow_fields | line_command_fields
            extra = set(content_vals) - allowed
            if extra:
                raise ValidationError(
                    _("หน่วยงบประมาณสามารถระบุยอดจัดสรรและดำเนินการตามสถานะได้เท่านั้น")
                )

    @api.model
    def _check_child_mutation_allowed(self, requests, vals=None, creating=False, unlinking=False):
        if not self._budget_request_lock_enabled():
            return
        is_budget_unit = self._user_is_budget_unit()
        allocation_fields = {"allocated_budget_amount", "allocated_qty"}
        for request in requests:
            if not request or request.state == "draft":
                continue
            if creating or unlinking:
                raise ValidationError(_("ไม่สามารถเพิ่มหรือลบรายการหลังส่งคำของบได้"))
            if request.state in ("approved", "rejected"):
                raise ValidationError(
                    _("คำของบที่อนุมัติหรือตีกลับแล้ว ไม่สามารถแก้ไขรายการได้")
                )
            if not is_budget_unit:
                raise ValidationError(_("ไม่สามารถแก้ไขคำของบหลังส่งเรื่องได้"))
            extra = set(vals or ()) - allocation_fields
            if extra:
                raise ValidationError(_("หน่วยงบประมาณสามารถระบุยอดจัดสรรได้เท่านั้น"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_line_type_commands(vals)
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "departmental.budget.request"
                ) or _("New")
        records = super().create(vals_list)
        records._sync_header_totals()
        return records

    def write(self, vals):
        self._normalize_line_type_commands(vals)
        self._check_header_write_allowed(vals)
        res = super().write(vals)
        if not self.env.context.get("skip_header_total_sync"):
            self._sync_header_totals()
        return res

    def unlink(self):
        if self._budget_request_lock_enabled() and self.filtered(
            lambda rec: rec.state != "draft"
        ):
            raise ValidationError(_("ไม่สามารถลบคำของบที่ไม่ใช่ร่างได้"))
        return super().unlink()

    def action_submit(self):
        for rec in self:
            if not rec.request_justification:
                line_reasons = [
                    reason.strip()
                    for reason in rec.line_ids.mapped("reason")
                    if reason and reason.strip()
                ]
                if line_reasons:
                    rec.request_justification = "\n".join(dict.fromkeys(line_reasons))
                else:
                    raise ValidationError(
                        _("กรุณาระบุเหตุผลประกอบคำขอตั้งงบประมาณ หรือกรอกเหตุผลคำชี้แจงในรายการ")
                    )
            if not rec.line_ids:
                raise ValidationError(_("กรุณาเพิ่มรายการคำของบอย่างน้อย 1 รายการ"))
            rec._validate_material_details_for_submission()
            rec.line_ids._validate_for_submission()
            rec.write(
                {
                    "state": "submitted",
                    "submission_date": fields.Datetime.now(),
                }
            )

    def _validate_material_details_for_submission(self):
        self.ensure_one()
        if not self.show_material_lines or not self.material_detail_ids:
            return
        line_subtypes = self.material_line_ids.mapped("material_sub_type_id")
        missing = self.material_detail_ids.filtered(
            lambda detail: detail.material_sub_type_id
            and detail.material_sub_type_id not in line_subtypes
        )
        if missing:
            names = ", ".join(
                missing.mapped("material_sub_type_id").mapped("name")
            )
            raise ValidationError(
                _(
                    "พบรายละเอียดสินค้าที่ประเภทวัสดุยังไม่มีในแท็บแบบตั้งงบพัสดุ: %(names)s\n"
                    "กรุณาเพิ่มบรรทัดประเภทวัสดุให้ครบก่อนส่งใบคำขอ"
                )
                % {"names": names}
            )
        self._sync_material_amounts_from_details()

    def action_receive(self):
        self.write({"state": "received"})

    def action_start_review(self):
        self.write({"state": "review"})

    def action_approve(self):
        for rec in self:
            rec.line_ids._validate_for_submission()
            budget = rec.annual_budget_id
            if not budget:
                raise ValidationError(_("Please specify annual budget plan."))
            missing_allocated = rec.line_ids.filtered(
                lambda line: not line.allocated_budget_amount
            )
            if missing_allocated:
                raise ValidationError(
                    _("กรุณาระบุงบประมาณที่จัดสรรให้ครบทุกรายการก่อนอนุมัติ")
                )
            rec._sync_budget_lines_to_annual_plan()
            rec.write({"state": "approved", "budget_record_id": budget.id})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_set_draft(self):
        budget_lines = self.env["budget.lines"].sudo().search(
            [("request_id", "in", self.ids)]
        )
        if budget_lines:
            budget_lines.unlink()
        self.write({"state": "draft", "budget_record_id": False})

    @api.model
    def _budget_type_from_code(self, code):
        if not code:
            return self.env["vpk.budget.type"]
        return self.env["vpk.budget.type"].search([("code", "=", code)], limit=1)

    @api.model
    def _normalize_line_type_commands(self, vals):
        line_type_by_field = {
            "asset_line_ids": "asset_budget",
            "material_line_ids": "supplies_budget",
            "construction_line_ids": "construction_budget",
            "project_line_ids": "project_budget",
        }
        for field_name, line_type_code in line_type_by_field.items():
            commands = vals.get(field_name)
            if not commands:
                continue
            normalized = []
            for command in commands:
                if (
                    isinstance(command, (list, tuple))
                    and len(command) >= 3
                    and command[0] == 0
                    and isinstance(command[2], dict)
                ):
                    command_vals = dict(command[2])
                    if not command_vals.get("budget_type_id"):
                        budget_type = self._budget_type_from_code(
                            command_vals.get("line_type") or line_type_code
                        )
                        if budget_type:
                            command_vals["budget_type_id"] = budget_type.id
                    command_vals.pop("line_type", None)
                    normalized.append((0, 0, command_vals))
                else:
                    normalized.append(command)
            vals[field_name] = normalized

    def _prepare_budget_line_vals(self, budget, line, planned_amount, requested_amount):
        """Build vals for one annual-plan budget.lines row."""
        self.ensure_one()
        return {
            "budget_id": budget.id,
            "analytic_account_id": self.analytic_account_id.id,
            "general_budget_id": line.budget_post_id.id,
            "date_from": budget.date_from,
            "date_to": budget.date_to,
            "planned_amount": planned_amount,
            "requested_amount": requested_amount,
            "fund_source_id": self.fund_source_id.id,
            "request_id": self.id,
            "request_line_id": line.id,
            "budget_group_id": line.budget_group_id.id,
            "material_sub_type_id": line.material_sub_type_id.id,
        }

    def _sync_budget_lines_to_annual_plan(self):
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_("Please add at least one budget request line."))
        if not self.annual_budget_id:
            raise ValidationError(_("Please specify annual budget plan."))

        budget = self.annual_budget_id
        budget_line_model = self.env["budget.lines"].sudo()
        existing_lines = budget_line_model.search(
            [("request_id", "=", self.id), ("budget_id", "=", budget.id)]
        )
        if existing_lines:
            existing_lines.unlink()

        missing_allocated = self.line_ids.filtered(
            lambda line: not line.allocated_budget_amount
        )
        if missing_allocated:
            raise ValidationError(
                _("กรุณาระบุงบประมาณที่จัดสรรให้ครบทุกรายการก่อนสร้างรายการงบประมาณ")
            )

        line_vals_list = []
        asset_lines = self.line_ids.filtered(lambda line: line._is_asset_line())
        other_lines = self.line_ids - asset_lines

        # แบบอื่น: สร้างรายการ budgetary ทีละบรรทัดคำขอ
        for line in other_lines:
            line_vals_list.append(
                self._prepare_budget_line_vals(
                    budget,
                    line,
                    line.allocated_budget_amount,
                    line.total_amount,
                )
            )

        # แบบครุภัณฑ์: รวมยอดหลายรายการต่อหมวดงบประมาณ (Budgetary Position) เป็นยอดเดียว
        # ไม่ดึงยอดคำขอตั้งงบ (total_amount) จาก line item มาบันทึกใน requested_amount / request_line_id
        asset_groups = {}
        for line in asset_lines:
            key = line.budget_post_id.id
            group = asset_groups.get(key)
            if not group:
                asset_groups[key] = {
                    "lines": line,
                    "planned_amount": line.allocated_budget_amount or 0.0,
                }
            else:
                group["lines"] |= line
                group["planned_amount"] += line.allocated_budget_amount or 0.0

        for group in asset_groups.values():
            primary_line = group["lines"][:1]
            vals = self._prepare_budget_line_vals(
                budget,
                primary_line,
                group["planned_amount"],
                0.0,
            )
            vals["request_line_id"] = False
            line_vals_list.append(vals)

        budget_line_model.create(line_vals_list)


class DepartmentalBudgetRequestLine(models.Model):
    _name = "departmental.budget.request.line"
    _description = "Departmental Budget Request Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        comodel_name="departmental.budget.request",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="request_id.company_id", store=True, readonly=True)
    budget_type_id = fields.Many2one(
        comodel_name="vpk.budget.type",
        string="ประเภทงบประมาณ",
        required=True,
        ondelete="restrict",
    )
    line_type = fields.Char(
        related="budget_type_id.code",
        store=True,
        readonly=True,
    )
    section_key = fields.Selection(
        related="budget_type_id.section_key",
        store=True,
        readonly=True,
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    item_name = fields.Text(string="รายการ/ชื่อโครงการ")
    item_description = fields.Text(string="รายละเอียดค่าใช้จ่าย")
    unit_name = fields.Char(string="หน่วย")
    quantity = fields.Float(default=1.0)
    unit_price = fields.Float(string="ราคาต่อหน่วย", digits=0)
    total_amount = fields.Float(
        string="รวมเงิน",
        compute="_compute_total_amount",
        store=True,
        digits=0,
    )
    current_quantity = fields.Float(string="จำนวนปัจจุบัน (เครื่อง)")
    current_age_year = fields.Char(string="อายุการใช้งาน (ปี)")
    requested_quantity = fields.Float(
        string="จำนวนที่ขอตั้ง",
        compute="_compute_requested_quantity",
        inverse="_inverse_requested_quantity",
        store=True,
        readonly=False,
        default=1.0,
    )
    usage_area = fields.Char(string="พื้นที่ใช้งาน (ตร.ม.)")
    construction_location = fields.Char(string="สถานที่ก่อสร้าง")
    construction_request_improvement = fields.Boolean(string="ขอปรับปรุง")
    construction_request_expansion = fields.Boolean(
        string="ขอขยาย/ต่อเติม"
    )
    target_group = fields.Char(string="กลุ่มเป้าหมาย")
    duration = fields.Char(string="ระยะเวลาดำเนินการ")
    objective = fields.Char(string="วัตถุประสงค์")
    expected_benefit = fields.Char(string="ประโยชน์ที่คาดว่าจะได้รับ")
    owner_name = fields.Char(string="ผู้รับผิดชอบ")
    request_kind = fields.Selection(
        selection=[
            ("replace", "ทดแทน"),
            ("adequacy", "ให้เพียงพอ"),
            ("expand", "ขยายบริการ"),
            ("new", "จัดใหม่"),
        ],
        string="ประเภทการขอ",
    )
    qty_new_purchase = fields.Float(string="ขอซื้อใหม่")
    qty_replacement = fields.Float(string="ขอทดแทน")
    qty_addition = fields.Float(string="ขอเพิ่ม")
    allowed_asset_categ_ids = fields.Many2many(
        comodel_name="vpk.budget.asset.category",
        compute="_compute_allowed_asset_categ_ids",
    )
    asset_categ_id = fields.Many2one(
        comodel_name="vpk.budget.asset.category",
        string="กลุ่มครุภัณฑ์",
        domain="[('id', 'in', allowed_asset_categ_ids)]",
        help="กลุ่มครุภัณฑ์ของโมดูลงบประมาณ (ผูกหมวดสินค้าได้ที่การกำหนดค่า)",
    )
    allowed_asset_product_ids = fields.Many2many(
        comodel_name="product.template",
        compute="_compute_allowed_asset_product_ids",
    )
    asset_product_id = fields.Many2one(
        comodel_name="product.template",
        string="รายการ",
        domain="[('id', 'in', allowed_asset_product_ids)]",
        help="สินค้าในหมวดครุภัณฑ์เท่านั้น ไม่รวมวัสดุ",
    )
    asset_type_ids = fields.Many2many(
        comodel_name="vpk.budget.asset.type",
        relation="departmental_budget_request_line_asset_type_rel",
        column1="line_id",
        column2="asset_type_id",
        string="ประเภทครุภัณฑ์",
    )
    reason = fields.Text(string="เหตุผลคำชี้แจง")
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        string="กลุ่มงบประมาณ",
    )
    allowed_material_sub_type_ids = fields.Many2many(
        comodel_name="vpk.budget.material.sub.type",
        compute="_compute_allowed_material_sub_type_ids",
    )
    material_sub_type_id = fields.Many2one(
        comodel_name="vpk.budget.material.sub.type",
        string="ประเภทวัสดุ",
        domain="[('id', 'in', allowed_material_sub_type_ids)]",
    )
    prior_year_plan_amount = fields.Float(string="แผนปีงบก่อนหน้า (บาท)", digits=0)
    disbursed_amount = fields.Float(string="เบิกจ่ายแล้ว (บาท)", digits=0)
    payable_amount = fields.Float(string="เจ้าหนี้คงค้าง (บาท)", digits=0)
    committed_not_received_amount = fields.Float(
        string="ก่อหนี้/ยังไม่ได้ตรวจรับ (บาท)", digits=0
    )
    remaining_amount = fields.Float(
        string="ยอดเงินคงเหลือ (บาท)",
        compute="_compute_material_remaining_amount",
        store=True,
        digits=0,
    )
    stock_amount = fields.Float(string="วัสดุคงคลัง (บาท)", digits=0)
    allocated_budget_amount = fields.Float(
        string="งบประมาณที่จัดสรร (บาท)",
        compute="_compute_allocated_budget_amount",
        inverse="_inverse_allocated_budget_amount",
        store=True,
        readonly=False,
        digits=0,
    )
    requested_plan_amount = fields.Float(string="คำขอตั้งแผนปีงบ (บาท)", digits=0)
    material_note = fields.Char(string="หมายเหตุ")
    usage_actual_y1 = fields.Float(
        string="การใช้ย้อนหลัง 1 ปี",
        compute="_compute_usage_history",
        digits=0,
    )
    usage_actual_y2 = fields.Float(
        string="การใช้ย้อนหลัง 2 ปี",
        compute="_compute_usage_history",
        digits=0,
    )
    usage_actual_y3 = fields.Float(
        string="การใช้ย้อนหลัง 3 ปี",
        compute="_compute_usage_history",
        digits=0,
    )
    usage_prior_plan_amount = fields.Float(
        string="แผนงบปีก่อน (บาท)",
        compute="_compute_usage_history",
        digits=0,
    )
    usage_prior_disbursed_amount = fields.Float(
        string="เบิกจ่ายปีก่อน (บาท)",
        compute="_compute_usage_history",
        digits=0,
    )
    usage_prior_remaining_amount = fields.Float(
        string="คงเหลือปีก่อน (บาท)",
        compute="_compute_usage_history",
        digits=0,
    )
    usage_prior_request_name = fields.Char(
        string="อ้างอิงคำของบปีก่อน",
        compute="_compute_usage_history",
    )
    usage_budget_type_name = fields.Char(
        string="ประเภทงบประมาณ",
        compute="_compute_usage_budget_type_name",
    )

    @api.depends("material_sub_type_id", "item_name", "line_type", "asset_categ_id", "asset_product_id")
    def _compute_usage_budget_type_name(self):
        line_type_labels = dict(
            self.env["vpk.budget.request.form.type.line"]._get_line_type_selection()
        )
        for line in self:
            if line.material_sub_type_id:
                line.usage_budget_type_name = line.material_sub_type_id.name
            elif line.asset_product_id:
                line.usage_budget_type_name = line.asset_product_id.display_name
            elif line.item_name:
                line.usage_budget_type_name = line.item_name
            elif line.asset_categ_id:
                line.usage_budget_type_name = line.asset_categ_id.name
            elif line.budget_type_id:
                line.usage_budget_type_name = line.budget_type_id.name
            else:
                line.usage_budget_type_name = line_type_labels.get(line.line_type, "")

    @api.depends()
    def _compute_allowed_asset_categ_ids(self):
        categs = self.env["vpk.budget.asset.category"].search([("active", "=", True)])
        for line in self:
            line.allowed_asset_categ_ids = categs

    @api.depends("asset_categ_id", "asset_categ_id.product_categ_id")
    def _compute_allowed_asset_product_ids(self):
        Product = self.env["product.template"].with_context(active_test=True)
        for line in self:
            linked = line.asset_categ_id.product_categ_id
            if not linked:
                line.allowed_asset_product_ids = Product.browse()
                continue
            line.allowed_asset_product_ids = Product.search(
                [
                    ("purchase_ok", "=", True),
                    ("categ_id", "child_of", linked.id),
                ]
            )

    @api.onchange("asset_categ_id")
    def _onchange_asset_categ_id(self):
        if (
            self.asset_product_id
            and self.allowed_asset_product_ids
            and self.asset_product_id not in self.allowed_asset_product_ids
        ):
            self.asset_product_id = False
            self.item_name = False

    @api.onchange("asset_product_id")
    def _onchange_asset_product_id(self):
        if not self.asset_product_id:
            return
        self.item_name = self.asset_product_id.display_name
        if not self.unit_price:
            self.unit_price = self.asset_product_id.standard_price or 0.0
        if self.asset_product_id.categ_id and not self.asset_categ_id:
            matched = self.env["vpk.budget.asset.category"]._find_for_product_category(
                self.asset_product_id.categ_id
            )
            if matched:
                self.asset_categ_id = matched

    @api.depends("budget_group_id")
    def _compute_allowed_material_sub_type_ids(self):
        material_sub_type_model = self.env["vpk.budget.material.sub.type"]
        for line in self:
            if line.budget_group_id:
                line.allowed_material_sub_type_ids = material_sub_type_model.search(
                    [
                        ("budget_group_id", "=", line.budget_group_id.id),
                        ("active", "=", True),
                    ]
                )
            else:
                line.allowed_material_sub_type_ids = material_sub_type_model.browse()

    @api.onchange("material_sub_type_id")
    def _onchange_material_sub_type_id(self):
        if self.material_sub_type_id:
            self.budget_group_id = self.material_sub_type_id.budget_group_id

    @api.onchange("budget_group_id")
    def _onchange_budget_group_id(self):
        if (
            self.material_sub_type_id
            and self.material_sub_type_id.budget_group_id != self.budget_group_id
        ):
            self.material_sub_type_id = False
        elif self.budget_group_id and not self.material_sub_type_id:
            sub_types = self.env["vpk.budget.material.sub.type"].search(
                [
                    ("budget_group_id", "=", self.budget_group_id.id),
                    ("active", "=", True),
                ],
                limit=2,
            )
            if len(sub_types) == 1:
                self.material_sub_type_id = sub_types

    def _get_asset_request_quantity(self):
        self.ensure_one()
        return (
            (self.qty_new_purchase or 0.0)
            + (self.qty_replacement or 0.0)
            + (self.qty_addition or 0.0)
        )

    def _is_asset_line(self):
        self.ensure_one()
        if self.section_key == "asset":
            return True
        if self.line_type == "asset_budget":
            return True
        if self.budget_type_id and self.budget_type_id.section_key == "asset":
            return True
        return self.env.context.get("default_line_type") == "asset_budget"

    @api.depends(
        "section_key",
        "line_type",
        "budget_type_id",
        "qty_new_purchase",
        "qty_replacement",
        "qty_addition",
    )
    def _compute_requested_quantity(self):
        for rec in self:
            if rec._is_asset_line():
                rec.requested_quantity = rec._get_asset_request_quantity()
            else:
                origin = rec._origin
                rec.requested_quantity = (
                    origin.requested_quantity if origin else (rec.requested_quantity or 0.0)
                )

    def _inverse_requested_quantity(self):
        """Allow manual edit on non-asset lines."""
        return

    @api.onchange(
        "qty_new_purchase",
        "qty_replacement",
        "qty_addition",
        "unit_price",
        "requested_quantity",
    )
    def _onchange_asset_request_quantities(self):
        if self._is_asset_line():
            self.requested_quantity = self._get_asset_request_quantity()
            qty = self.requested_quantity or 0.0
            self.total_amount = qty * (self.unit_price or 0.0)
            # ไม่ดึงยอดคำขอตั้งงบไปใส่ allocated_budget_amount

    @api.depends(
        "budget_type_id",
        "section_key",
        "line_type",
        "quantity",
        "unit_price",
        "requested_quantity",
        "requested_plan_amount",
        "qty_new_purchase",
        "qty_replacement",
        "qty_addition",
    )
    def _compute_total_amount(self):
        for rec in self:
            if rec.section_key == "material":
                rec.total_amount = rec.requested_plan_amount
            elif rec._is_asset_line():
                qty = rec._get_asset_request_quantity() or rec.requested_quantity or 0.0
                rec.total_amount = qty * (rec.unit_price or 0.0)
            else:
                qty = rec.quantity or rec.requested_quantity or 0.0
                rec.total_amount = qty * (rec.unit_price or 0.0)

    @api.depends(
        "section_key",
        "line_type",
        "budget_type_id",
    )
    def _compute_allocated_budget_amount(self):
        """Keep manually entered allocated amount; do not copy from request amount."""
        for rec in self:
            origin = rec._origin
            rec.allocated_budget_amount = (
                origin.allocated_budget_amount if origin else 0.0
            )

    def _inverse_allocated_budget_amount(self):
        """Allow manual edit of allocated amount."""
        return

    @api.constrains("budget_type_id", "request_id", "request_id.form_type_id")
    def _check_line_type_allowed(self):
        for line in self:
            request = line.request_id
            if not request or not request.form_type_id or not line.budget_type_id:
                continue
            allowed = request.form_type_id.line_type_ids.mapped("budget_type_id")
            if allowed and line.budget_type_id not in allowed:
                raise ValidationError(
                    _("ประเภทงบ '%(budget_type)s' ไม่ได้กำหนดไว้ในแบบฟอร์มคำของบ %(form_type)s")
                    % {
                        "budget_type": line.budget_type_id.name,
                        "form_type": request.form_type_id.name,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        Request = self.env["departmental.budget.request"]
        Request._check_child_mutation_allowed(
            Request.browse(
                [vals.get("request_id") for vals in vals_list if vals.get("request_id")]
            ),
            creating=True,
        )
        default_line_type = self.env.context.get("default_line_type")
        budget_type_model = self.env["vpk.budget.type"]
        for vals in vals_list:
            budget_type = budget_type_model.browse()
            if vals.get("budget_type_id"):
                budget_type = budget_type_model.browse(vals["budget_type_id"])
            elif default_line_type:
                budget_type = self.env["departmental.budget.request"]._budget_type_from_code(
                    default_line_type
                )
                if budget_type:
                    vals["budget_type_id"] = budget_type.id
            if budget_type and budget_type.section_key == "asset":
                asset_qty = (
                    (vals.get("qty_new_purchase") or 0.0)
                    + (vals.get("qty_replacement") or 0.0)
                    + (vals.get("qty_addition") or 0.0)
                )
                vals["requested_quantity"] = asset_qty
        lines = super().create(vals_list)
        lines.mapped("request_id")._sync_header_totals()
        return lines

    def write(self, vals):
        self.env["departmental.budget.request"]._check_child_mutation_allowed(
            self.mapped("request_id"), vals=vals
        )
        default_line_type = self.env.context.get("default_line_type")
        if default_line_type and not vals.get("budget_type_id"):
            budget_type = self.env["departmental.budget.request"]._budget_type_from_code(
                default_line_type
            )
            if budget_type:
                missing_type_lines = self.filtered(lambda line: not line.budget_type_id)
                if missing_type_lines:
                    missing_type_lines.with_context(default_line_type=False).write(
                        {"budget_type_id": budget_type.id}
                    )
        asset_qty_fields = {"qty_new_purchase", "qty_replacement", "qty_addition"}
        if asset_qty_fields.intersection(vals):
            result = True
            for line in self:
                line_vals = dict(vals)
                if line.section_key == "asset":
                    qty_new = line_vals.get("qty_new_purchase", line.qty_new_purchase)
                    qty_replace = line_vals.get("qty_replacement", line.qty_replacement)
                    qty_add = line_vals.get("qty_addition", line.qty_addition)
                    line_vals["requested_quantity"] = (
                        (qty_new or 0.0) + (qty_replace or 0.0) + (qty_add or 0.0)
                    )
                result = result and super(DepartmentalBudgetRequestLine, line).write(line_vals)
            self.mapped("request_id")._sync_header_totals()
            return result
        res = super().write(vals)
        amount_fields = {
            "unit_price",
            "quantity",
            "requested_quantity",
            "requested_plan_amount",
            "allocated_budget_amount",
            "total_amount",
            "qty_new_purchase",
            "qty_replacement",
            "qty_addition",
        }
        if amount_fields.intersection(vals):
            self.mapped("request_id")._sync_header_totals()
        return res

    def unlink(self):
        self.env["departmental.budget.request"]._check_child_mutation_allowed(
            self.mapped("request_id"), unlinking=True
        )
        return super().unlink()

    @api.depends(
        "prior_year_plan_amount",
        "disbursed_amount",
        "payable_amount",
        "committed_not_received_amount",
    )
    def _compute_material_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = (
                rec.prior_year_plan_amount
                - rec.disbursed_amount
                - rec.payable_amount
                - rec.committed_not_received_amount
            )

    @api.depends(
        "request_id.fiscal_year",
        "request_id.analytic_account_id",
        "request_id.form_type_code",
        "budget_post_id",
        "budget_post_id.account_ids",
        "material_sub_type_id",
        "item_name",
        "budget_type_id",
        "section_key",
        "prior_year_plan_amount",
        "disbursed_amount",
        "remaining_amount",
    )
    def _compute_usage_history(self):
        request_model = self.env["departmental.budget.request"]
        for line in self:
            line.usage_actual_y1 = 0.0
            line.usage_actual_y2 = 0.0
            line.usage_actual_y3 = 0.0
            line.usage_prior_plan_amount = 0.0
            line.usage_prior_disbursed_amount = 0.0
            line.usage_prior_remaining_amount = 0.0
            line.usage_prior_request_name = False

            request = line.request_id
            if not request or not request.fiscal_year:
                continue

            current_be = request_model._fiscal_year_to_be(request.fiscal_year)
            if not current_be:
                continue

            for offset, field_name in (
                (1, "usage_actual_y1"),
                (2, "usage_actual_y2"),
                (3, "usage_actual_y3"),
            ):
                date_from, date_to = request_model._fiscal_period_from_be_year(
                    current_be - offset
                )
                if date_from and date_to:
                    line[field_name] = line._get_analytic_actual_amount(date_from, date_to)

            prior_line = line._find_prior_approved_request_line(current_be - 1)
            if prior_line:
                line.usage_prior_request_name = prior_line.request_id.name
                if prior_line.line_type == "supplies_budget":
                    line.usage_prior_plan_amount = prior_line.prior_year_plan_amount
                    line.usage_prior_disbursed_amount = prior_line.disbursed_amount
                    line.usage_prior_remaining_amount = prior_line.remaining_amount
                else:
                    line.usage_prior_plan_amount = prior_line.total_amount
                    line.usage_prior_disbursed_amount = line.usage_actual_y1
                    line.usage_prior_remaining_amount = (
                        prior_line.total_amount - line.usage_actual_y1
                    )
            elif line.line_type == "supplies_budget":
                line.usage_prior_plan_amount = line.prior_year_plan_amount
                line.usage_prior_disbursed_amount = line.disbursed_amount
                line.usage_prior_remaining_amount = line.remaining_amount

    def _get_analytic_actual_amount(self, date_from, date_to):
        self.ensure_one()
        analytic_account = self.request_id.analytic_account_id
        account_ids = self.budget_post_id.account_ids.ids
        if not analytic_account or not account_ids:
            return 0.0
        query = """
            SELECT COALESCE(SUM(amount), 0)
            FROM account_analytic_line
            WHERE account_id = %s
              AND date BETWEEN %s AND %s
              AND general_account_id = ANY(%s)
        """
        params = [
            analytic_account.id,
            date_from,
            date_to,
            "{" + ",".join(map(str, account_ids)) + "}",
        ]
        if self.line_type == "supplies_budget" and self.material_sub_type_id:
            query += " AND material_sub_type_id = %s"
            params.append(self.material_sub_type_id.id)
        self.env.cr.execute(query, tuple(params))
        return self.env.cr.fetchone()[0] or 0.0

    def _find_prior_approved_request_line(self, prior_be_year):
        self.ensure_one()
        if not prior_be_year:
            return self.env["departmental.budget.request.line"]
        request_model = self.env["departmental.budget.request"]
        prior_ce_year = request_model._fiscal_year_to_ce(prior_be_year)
        fiscal_years = {str(prior_be_year)}
        if prior_ce_year:
            fiscal_years.add(str(prior_ce_year))
        domain = [
            ("request_id.analytic_account_id", "=", self.request_id.analytic_account_id.id),
            ("request_id.state", "=", "approved"),
            ("request_id.fiscal_year", "in", list(fiscal_years)),
            ("request_id.form_type_id", "=", self.request_id.form_type_id.id),
            ("budget_post_id", "=", self.budget_post_id.id),
            ("id", "!=", self.id),
        ]
        if self.line_type == "supplies_budget" and self.material_sub_type_id:
            domain.append(("material_sub_type_id", "=", self.material_sub_type_id.id))
        elif self.item_name:
            domain.append(("item_name", "=", self.item_name))
        return self.env["departmental.budget.request.line"].search(domain, limit=1)

    def action_apply_usage_history_to_material_line(self):
        for line in self:
            if line.line_type != "supplies_budget":
                continue
            vals = {}
            if line.usage_prior_plan_amount:
                vals["prior_year_plan_amount"] = line.usage_prior_plan_amount
            if line.usage_prior_disbursed_amount:
                vals["disbursed_amount"] = line.usage_prior_disbursed_amount
            if line.usage_actual_y1 and not line.usage_prior_disbursed_amount:
                vals["disbursed_amount"] = abs(line.usage_actual_y1)
            if vals:
                line.write(vals)

    def _validate_for_submission(self):
        for rec in self:
            if not rec.budget_post_id:
                raise ValidationError(_("Please specify budget category."))
            if rec.line_type == "supplies_budget":
                if not rec.budget_group_id:
                    raise ValidationError(
                        _("Please specify budget group for material budget lines.")
                    )
                if not rec.material_sub_type_id:
                    raise ValidationError(
                        _("กรุณาระบุประเภทวัสดุสำหรับรายการแบบตั้งงบวัสดุ")
                    )
                continue
            if not rec.item_name:
                raise ValidationError(_("Please specify item name/project name."))
