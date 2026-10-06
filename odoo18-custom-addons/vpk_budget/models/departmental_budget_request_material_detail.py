from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DepartmentalBudgetRequestMaterialDetail(models.Model):
    _name = "departmental.budget.request.material.detail"
    _description = "Departmental Budget Request Material Detail"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        comodel_name="departmental.budget.request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id",
        store=True,
        readonly=True,
    )
    product_categ_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดสินค้า",
        related="budget_group_id.product_categ_id",
        store=True,
        readonly=True,
    )
    filter_product_categ_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดสินค้าที่ใช้กรอง",
        compute="_compute_filter_product_categ_id",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="รายการ",
        domain=(
            "[('purchase_ok', '=', True),"
            " ('categ_id', 'child_of', filter_product_categ_id)]"
        ),
    )
    name = fields.Char(string="รายการสินค้า")
    material_sub_type_id = fields.Many2one(
        comodel_name="vpk.budget.material.sub.type",
        string="ประเภทวัสดุ",
        required=True,
    )
    form_section_key = fields.Char(
        string="กลุ่มแบบฟอร์ม",
        related="request_id.form_section_key",
        store=True,
        readonly=True,
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        domain=(
            "[('company_id', 'in', [False, company_id]),"
            " '|', ('section_key', '=', False), ('section_key', '=', form_section_key)]"
        ),
    )
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        string="กลุ่มวัสดุ",
        related="material_sub_type_id.budget_group_id",
        store=True,
        readonly=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วยนับ",
    )
    opening_qty = fields.Float(
        string="ปริมาณคงเหลือยกมา",
        digits=(16, 2),
    )
    opening_amount = fields.Float(
        string="มูลค่าคงเหลือยกมา",
        digits=0,
    )
    plan_usage_qty = fields.Float(
        string="ปริมาณใช้ในปี",
        digits=(16, 2),
    )
    quantity = fields.Float(string="ปริมาณที่ของบ", default=1.0, required=True)
    unit_price = fields.Float(string="ราคา/หน่วยนับ", digits=0, required=True)
    total_amount = fields.Float(
        string="มูลค่าที่ของบ",
        compute="_compute_total_amount",
        store=True,
        digits=0,
    )
    allocated_qty = fields.Float(
        string="ปริมาณที่จัดสรร",
        digits=(16, 2),
    )
    allocated_amount = fields.Float(
        string="มูลค่าที่จัดสรร",
        compute="_compute_allocated_amount",
        store=True,
        digits=0,
    )
    note = fields.Char(string="หมายเหตุ")
    usage_qty_y3 = fields.Float(
        string="ปริมาณใช้ปี",
        digits=(16, 2),
    )
    usage_qty_y2 = fields.Float(
        string="ปริมาณใช้ปี",
        digits=(16, 2),
    )
    usage_qty_y1 = fields.Float(
        string="ปริมาณใช้ปี",
        digits=(16, 2),
    )
    usage_amount_y1 = fields.Float(
        string="มูลค่า 1 ปีก่อน",
        compute="_compute_usage_history_detail",
        digits=0,
    )
    usage_amount_y2 = fields.Float(
        string="มูลค่า 2 ปีก่อน",
        compute="_compute_usage_history_detail",
        digits=0,
    )
    usage_amount_y3 = fields.Float(
        string="มูลค่า 3 ปีก่อน",
        compute="_compute_usage_history_detail",
        digits=0,
    )
    usage_prior_request_name = fields.Char(
        string="อ้างอิงคำของบปีก่อน",
        compute="_compute_usage_history_detail",
    )

    @api.model
    def _get_usage_qty_year_labels(self, fiscal_year=None):
        """Return BE year labels for y3/y2/y1/current relative to request fiscal year."""
        Request = self.env["departmental.budget.request"]
        fiscal_year = fiscal_year or self.env.context.get("vpk_usage_fiscal_year")
        current_be = Request._fiscal_year_to_be(fiscal_year) if fiscal_year else 0
        if not current_be:
            return {"y3": "", "y2": "", "y1": "", "current": ""}
        return {
            "y3": str(current_be - 3),
            "y2": str(current_be - 2),
            "y1": str(current_be - 1),
            "current": str(current_be),
        }

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        years = self._get_usage_qty_year_labels()
        label_map = {
            "usage_qty_y3": (_("ปริมาณใช้ปี %s"), years["y3"]),
            "usage_qty_y2": (_("ปริมาณใช้ปี %s"), years["y2"]),
            "usage_qty_y1": (_("ปริมาณใช้ปี %s"), years["y1"]),
            "plan_usage_qty": (_("ปริมาณใช้ในปี %s"), years["current"]),
            "quantity": (_("ปริมาณที่ของบในปี %s"), years["current"]),
        }
        for fname, (template, year) in label_map.items():
            if fname in res and year:
                res[fname]["string"] = template % year
        if "unit_price" in res:
            res["unit_price"]["string"] = _("ราคา/หน่วยนับ")
        if "total_amount" in res:
            res["total_amount"]["string"] = _("มูลค่าที่ของบ")
        return res

    @api.depends("quantity", "unit_price")
    def _compute_total_amount(self):
        for detail in self:
            detail.total_amount = (detail.quantity or 0.0) * (detail.unit_price or 0.0)

    @api.depends("allocated_qty", "unit_price")
    def _compute_allocated_amount(self):
        for detail in self:
            detail.allocated_amount = (detail.allocated_qty or 0.0) * (
                detail.unit_price or 0.0
            )

    @api.depends(
        "request_id.fiscal_year",
        "request_id.analytic_account_id",
        "request_id.form_type_id",
        "product_id",
        "name",
        "material_sub_type_id",
        "usage_qty_y1",
        "usage_qty_y2",
        "usage_qty_y3",
    )
    def _compute_usage_history_detail(self):
        Request = self.env["departmental.budget.request"]
        for detail in self:
            detail.usage_amount_y1 = 0.0
            detail.usage_amount_y2 = 0.0
            detail.usage_amount_y3 = 0.0
            detail.usage_prior_request_name = False

            request = detail.request_id
            if not request or not request.fiscal_year:
                continue

            current_be = Request._fiscal_year_to_be(request.fiscal_year)
            if not current_be:
                continue

            for offset, amount_field in (
                (1, "usage_amount_y1"),
                (2, "usage_amount_y2"),
                (3, "usage_amount_y3"),
            ):
                prior = detail._find_prior_approved_detail(current_be - offset)
                if not prior:
                    continue
                detail[amount_field] = sum(prior.mapped("total_amount"))
                if offset == 1:
                    detail.usage_prior_request_name = prior[:1].request_id.name

    def _find_prior_approved_detail(self, prior_be_year):
        self.ensure_one()
        if not prior_be_year or not self.request_id:
            return self.browse()
        Request = self.env["departmental.budget.request"]
        prior_ce_year = Request._fiscal_year_to_ce(prior_be_year)
        fiscal_years = {str(prior_be_year)}
        if prior_ce_year:
            fiscal_years.add(str(prior_ce_year))

        domain = [
            ("request_id.analytic_account_id", "=", self.request_id.analytic_account_id.id),
            ("request_id.state", "=", "approved"),
            ("request_id.fiscal_year", "in", list(fiscal_years)),
            ("request_id.form_type_id", "=", self.request_id.form_type_id.id),
            ("id", "!=", self.id),
        ]
        if self.material_sub_type_id:
            domain.append(("material_sub_type_id", "=", self.material_sub_type_id.id))
        if self.product_id:
            domain.append(("product_id", "=", self.product_id.id))
        elif self.name:
            domain.append(("name", "=", self.name))
        else:
            return self.browse()
        return self.search(domain)

    @staticmethod
    def _normalize_item_name(name):
        return (name or "").strip().casefold()

    def _find_duplicate_details(self):
        self.ensure_one()
        if not self.request_id:
            return self.browse()
        if self.product_id:
            domain = [
                ("request_id", "=", self.request_id.id),
                ("product_id", "=", self.product_id.id),
            ]
            if self.id:
                domain.append(("id", "!=", self.id))
            return self.search(domain, limit=1)
        item_name = self._normalize_item_name(self.name)
        if not item_name or item_name == self._normalize_item_name("รายการสินค้า"):
            return self.browse()
        siblings = self.search(
            [
                ("request_id", "=", self.request_id.id),
                ("product_id", "=", False),
                ("id", "!=", self.id if self.id else 0),
            ]
        )
        return siblings.filtered(
            lambda line: self._normalize_item_name(line.name) == item_name
        )[:1]

    @api.constrains("request_id", "product_id", "name")
    def _check_duplicate_material_detail(self):
        for detail in self:
            duplicates = detail._find_duplicate_details()
            if not duplicates:
                continue
            if detail.product_id:
                raise ValidationError(
                    _("ไม่สามารถบันทึกรายการสินค้าซ้ำได้: %s")
                    % detail.product_id.display_name
                )
            raise ValidationError(
                _("ไม่สามารถบันทึกรายการสินค้าซ้ำได้: %s") % (detail.name or "")
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        request = self.env["departmental.budget.request"].browse(
            self.env.context.get("default_request_id")
            or self.env.context.get("active_id")
        )
        if not request and self.env.context.get("params", {}).get("id"):
            request = self.env["departmental.budget.request"].browse(
                self.env.context["params"]["id"]
            )
        request_id = res.get("request_id")
        if request_id:
            request = self.env["departmental.budget.request"].browse(request_id)
        if request and request.load_material_sub_type_id and not res.get(
            "material_sub_type_id"
        ):
            if "material_sub_type_id" in fields_list or not fields_list:
                res["material_sub_type_id"] = request.load_material_sub_type_id.id
        if request and request.load_budget_post_id and not res.get("budget_post_id"):
            if "budget_post_id" in fields_list or not fields_list:
                res["budget_post_id"] = request.load_budget_post_id.id
        if request and len(request.material_sub_type_ids) == 1:
            if "material_sub_type_id" in fields_list or not fields_list:
                res.setdefault(
                    "material_sub_type_id", request.material_sub_type_ids.id
                )
            if "budget_post_id" in fields_list or not fields_list:
                match = request.material_line_ids.filtered(
                    lambda line: line.material_sub_type_id
                    == request.material_sub_type_ids
                    and line.budget_post_id
                )[:1]
                if match:
                    res.setdefault("budget_post_id", match.budget_post_id.id)
        return res

    def _category_from_subtype(self, subtype):
        if subtype and subtype.budget_group_id:
            return subtype.budget_group_id.product_categ_id
        return self.env["product.category"]

    @api.depends(
        "product_categ_id",
        "material_sub_type_id",
        "material_sub_type_id.budget_group_id.product_categ_id",
        "budget_post_id",
        "request_id.load_material_sub_type_id",
        "request_id.load_material_sub_type_id.budget_group_id.product_categ_id",
        "request_id.load_budget_group_id",
        "request_id.load_budget_group_id.product_categ_id",
    )
    def _compute_filter_product_categ_id(self):
        for detail in self:
            categ = detail.product_categ_id or detail._category_from_subtype(
                detail.material_sub_type_id
            )
            request = detail.request_id
            if not categ and request:
                categ = detail._category_from_subtype(request.load_material_sub_type_id)
            if not categ and request and request.load_budget_group_id:
                categ = request.load_budget_group_id.product_categ_id
            if not categ and request and detail.budget_post_id:
                resolved = request._resolve_material_sub_type_from_budget_post(
                    detail.budget_post_id
                )
                categ = detail._category_from_subtype(resolved)
            detail.filter_product_categ_id = categ

    def _apply_subtype_from_budget_post(self):
        if not self.budget_post_id or not self.request_id or self.material_sub_type_id:
            return
        subtype = self.request_id._resolve_material_sub_type_from_budget_post(
            self.budget_post_id
        )
        if subtype:
            self.material_sub_type_id = subtype

    @api.onchange("budget_post_id")
    def _onchange_budget_post_id_subtype(self):
        self._apply_subtype_from_budget_post()

    def _matching_material_line_budget_post(self):
        self.ensure_one()
        if not self.request_id or not self.material_sub_type_id:
            return self.env["account.budget.post"]
        match = self.request_id.material_line_ids.filtered(
            lambda line: line.material_sub_type_id == self.material_sub_type_id
            and line.budget_post_id
        )[:1]
        return match.budget_post_id

    @api.onchange("material_sub_type_id")
    def _onchange_material_sub_type_id_budget_post(self):
        if not self.material_sub_type_id:
            return
        budget_post = self._matching_material_line_budget_post()
        if budget_post:
            section = self.form_section_key
            post_section = budget_post.section_key
            if not section or not post_section or section == post_section:
                self.budget_post_id = budget_post
        if self.product_id and self.product_categ_id:
            still_valid = self.env["product.product"].search_count(
                [
                    ("id", "=", self.product_id.id),
                    ("categ_id", "child_of", self.product_categ_id.id),
                ]
            )
            if not still_valid:
                self.product_id = False
                self.name = False
                self.product_uom_id = False
                self.unit_price = 0.0

    @api.constrains("budget_post_id", "request_id")
    def _check_budget_post_matches_form_section(self):
        for detail in self:
            if not detail.budget_post_id or not detail.request_id.form_type_id:
                continue
            section = detail.request_id.form_type_id._get_primary_section()
            post_section = detail.budget_post_id.section_key
            if section and post_section and section != post_section:
                raise ValidationError(
                    _(
                        "หมวดงบประมาณ \"%(post)s\" ไม่สอดคล้องกับแบบฟอร์มคำของบ "
                        "(ต้องเป็นกลุ่ม %(section)s)"
                    )
                    % {
                        "post": detail.budget_post_id.display_name,
                        "section": dict(
                            detail.budget_post_id._fields["section_key"].selection
                        ).get(section, section),
                    }
                )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id:
            return
        duplicates = self._find_duplicate_details()
        if duplicates:
            product_name = self.product_id.display_name
            self.product_id = False
            return {
                "warning": {
                    "title": _("รายการสินค้าซ้ำ"),
                    "message": _(
                        "สินค้า \"%s\" มีอยู่ในรายละเอียดแล้ว กรุณาอย่าเลือกรายการซ้ำ"
                    )
                    % product_name,
                }
            }
        self.name = self.product_id.display_name
        self.product_uom_id = self.product_id.uom_id
        self.unit_price = self.product_id.standard_price or self.product_id.lst_price or 0.0

    @api.onchange("name")
    def _onchange_name_duplicate(self):
        if not self.name or self.product_id:
            return
        duplicates = self._find_duplicate_details()
        if duplicates:
            item_name = self.name
            self.name = False
            return {
                "warning": {
                    "title": _("รายการสินค้าซ้ำ"),
                    "message": _(
                        "รายการ \"%s\" มีอยู่ในรายละเอียดแล้ว กรุณาอย่ากรอกชื่อซ้ำ"
                    )
                    % item_name,
                }
            }

    @api.onchange("request_id")
    def _onchange_request_id_default_subtype(self):
        if not self.request_id:
            return
        if not self.material_sub_type_id and self.request_id.load_material_sub_type_id:
            self.material_sub_type_id = self.request_id.load_material_sub_type_id
        elif (
            not self.material_sub_type_id
            and len(self.request_id.material_sub_type_ids) == 1
        ):
            self.material_sub_type_id = self.request_id.material_sub_type_ids
        if not self.budget_post_id and self.request_id.load_budget_post_id:
            self.budget_post_id = self.request_id.load_budget_post_id
        self._apply_subtype_from_budget_post()

    @api.model_create_multi
    def create(self, vals_list):
        Request = self.env["departmental.budget.request"]
        Request._check_child_mutation_allowed(
            Request.browse(
                [vals.get("request_id") for vals in vals_list if vals.get("request_id")]
            ),
            creating=True,
        )
        Product = self.env["product.product"]
        Post = self.env["account.budget.post"]
        for vals in vals_list:
            request = Request.browse(vals.get("request_id"))
            if request and not vals.get("material_sub_type_id"):
                if vals.get("budget_post_id"):
                    subtype = request._resolve_material_sub_type_from_budget_post(
                        Post.browse(vals["budget_post_id"])
                    )
                    if subtype:
                        vals["material_sub_type_id"] = subtype.id
                if not vals.get("material_sub_type_id") and request.load_material_sub_type_id:
                    vals["material_sub_type_id"] = request.load_material_sub_type_id.id
            if request and not vals.get("budget_post_id") and request.load_budget_post_id:
                vals["budget_post_id"] = request.load_budget_post_id.id
            if not vals.get("name"):
                if vals.get("product_id"):
                    vals["name"] = Product.browse(vals["product_id"]).display_name
                else:
                    vals["name"] = vals.get("note") or "รายการสินค้า"
        details = super().create(vals_list)
        if not self.env.context.get("skip_material_amount_sync"):
            details.mapped("request_id")._sync_material_amounts_from_details()
        return details

    def write(self, vals):
        self.env["departmental.budget.request"]._check_child_mutation_allowed(
            self.mapped("request_id"), vals=vals
        )
        res = super().write(vals)
        amount_fields = {
            "quantity",
            "unit_price",
            "total_amount",
            "material_sub_type_id",
            "request_id",
        }
        if (
            amount_fields.intersection(vals)
            and not self.env.context.get("skip_material_amount_sync")
        ):
            self.mapped("request_id")._sync_material_amounts_from_details()
        return res

    def unlink(self):
        requests = self.mapped("request_id")
        self.env["departmental.budget.request"]._check_child_mutation_allowed(
            requests, unlinking=True
        )
        res = super().unlink()
        if not self.env.context.get("skip_material_amount_sync"):
            requests._sync_material_amounts_from_details()
        return res
