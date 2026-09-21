from odoo import _, api, fields, models


class VpkBudgetGroup(models.Model):
    _name = "vpk.budget.group"
    _description = "Budget Group"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    material_sub_type_ids = fields.One2many(
        comodel_name="vpk.budget.material.sub.type",
        inverse_name="budget_group_id",
        string="ประเภทวัสดุย่อย",
    )
    product_categ_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดสินค้า (Product Category)",
        ondelete="set null",
        index=True,
        help="ผูกกับหมวดใต้ กลุ่มวัสดุ เพื่อกรองรายการสินค้าในแบบฟอร์มคำของบ",
    )

    _sql_constraints = [
        (
            "vpk_budget_group_code_uniq",
            "unique(code)",
            "Budget group code must be unique.",
        ),
    ]

    @api.model
    def _material_product_root(self):
        return self.env["product.category"].search(
            [("name", "=", "กลุ่มวัสดุ"), ("parent_id", "=", False)],
            limit=1,
        )

    @api.model
    def _strip_categ_prefix(self, name):
        text = (name or "").strip()
        if "." in text:
            text = text.split(".", 1)[-1].strip()
        return text

    def _match_main_product_categ(self):
        """Find the first-level product category under กลุ่มวัสดุ for this group."""
        self.ensure_one()
        root = self._material_product_root()
        if not root:
            return self.env["product.category"]
        group_short = self._strip_categ_prefix(self.name)
        aliases = {
            "TECHNICIAN": ["ช่าง", "วัสดุช่าง"],
            "FUEL": ["เชื้อเพลิง"],
        }
        candidates = [group_short]
        candidates.extend(aliases.get(self.code or "", []))
        children = self.env["product.category"].search([("parent_id", "=", root.id)])
        for categ in children:
            short = self._strip_categ_prefix(categ.name)
            for needle in candidates:
                if not needle:
                    continue
                if short == needle or needle in short or short in needle:
                    return categ
        return self.env["product.category"]

    def _get_filter_product_categories(self):
        """Categories used to filter products for this budget group."""
        self.ensure_one()
        Category = self.env["product.category"]
        root = self._material_product_root()
        categs = self.product_categ_id or self._match_main_product_categ()
        if not root:
            return categs
        subtype_needles = []
        for subtype in self.material_sub_type_ids:
            for raw in (subtype.name, subtype.code):
                short = self._strip_categ_prefix(raw)
                if short and len(short) >= 2:
                    subtype_needles.append(short)
        orphans = Category.search([("parent_id", "=", root.id)])
        main_ids = set(categs.ids)
        for categ in orphans:
            if categ.id in main_ids:
                continue
            short = self._strip_categ_prefix(categ.name)
            for needle in subtype_needles:
                if needle in short or short in needle:
                    categs |= categ
                    break
        return categs

    def action_link_product_categories(self):
        groups = self or self.search([])
        linked = 0
        for group in groups:
            if group.product_categ_id:
                continue
            matched = group._match_main_product_categ()
            if matched:
                group.product_categ_id = matched
                linked += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("กลุ่มวัสดุ"),
                "message": _("ผูกหมวดสินค้าแล้ว %s กลุ่ม") % linked,
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
