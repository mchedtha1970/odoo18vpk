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
    sibling_product_ids = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_sibling_product_ids",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="รายการ",
        domain="[('purchase_ok', '=', True), ('id', 'not in', sibling_product_ids)]",
    )
    name = fields.Char(string="รายการสินค้า")
    allowed_material_sub_type_ids = fields.Many2many(
        comodel_name="vpk.budget.material.sub.type",
        compute="_compute_allowed_material_sub_type_ids",
    )
    material_sub_type_id = fields.Many2one(
        comodel_name="vpk.budget.material.sub.type",
        string="ประเภทวัสดุ",
        required=True,
        domain="[('id', 'in', allowed_material_sub_type_ids)]",
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

    @api.depends(
        "request_id",
        "request_id.material_detail_ids",
        "request_id.material_detail_ids.product_id",
    )
    def _compute_sibling_product_ids(self):
        for detail in self:
            others = detail.request_id.material_detail_ids - detail
            detail.sibling_product_ids = others.mapped("product_id")

    @api.depends("request_id.material_sub_type_ids")
    def _compute_allowed_material_sub_type_ids(self):
        MaterialSubType = self.env["vpk.budget.material.sub.type"]
        for detail in self:
            request_sub_types = detail.request_id.material_sub_type_ids
            if request_sub_types:
                detail.allowed_material_sub_type_ids = request_sub_types
            else:
                detail.allowed_material_sub_type_ids = MaterialSubType.search(
                    [("active", "=", True)]
                )

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
        siblings = self.request_id.material_detail_ids - self
        if self.product_id:
            return siblings.filtered(lambda line: line.product_id == self.product_id)
        item_name = self._normalize_item_name(self.name)
        if not item_name or item_name == self._normalize_item_name("รายการสินค้า"):
            return self.browse()
        return siblings.filtered(
            lambda line: not line.product_id
            and self._normalize_item_name(line.name) == item_name
        )

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
        if request and len(request.material_sub_type_ids) == 1:
            if "material_sub_type_id" in fields_list or not fields_list:
                res["material_sub_type_id"] = request.material_sub_type_ids.id
        return res

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
        if (
            self.request_id
            and not self.material_sub_type_id
            and len(self.request_id.material_sub_type_ids) == 1
        ):
            self.material_sub_type_id = self.request_id.material_sub_type_ids

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
        for vals in vals_list:
            if not vals.get("name"):
                if vals.get("product_id"):
                    vals["name"] = Product.browse(vals["product_id"]).display_name
                else:
                    vals["name"] = vals.get("note") or "รายการสินค้า"
        details = super().create(vals_list)
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
        if amount_fields.intersection(vals):
            self.mapped("request_id")._sync_material_amounts_from_details()
        return res

    def unlink(self):
        requests = self.mapped("request_id")
        self.env["departmental.budget.request"]._check_child_mutation_allowed(
            requests, unlinking=True
        )
        res = super().unlink()
        requests._sync_material_amounts_from_details()
        return res
