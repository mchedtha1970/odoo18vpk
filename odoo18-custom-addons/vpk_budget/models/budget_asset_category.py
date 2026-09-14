# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class VpkBudgetAssetCategory(models.Model):
    _name = "vpk.budget.asset.category"
    _description = "กลุ่มครุภัณฑ์"
    _order = "sequence, code, id"

    sequence = fields.Integer(default=10)
    code = fields.Char(string="รหัส", required=True)
    name = fields.Char(string="ชื่อ", required=True)
    active = fields.Boolean(default=True)
    product_categ_id = fields.Many2one(
        comodel_name="product.category",
        string="หมวดสินค้า (Product Category)",
        ondelete="set null",
        index=True,
        help="ผูกกับหมวดสินค้าครุภัณฑ์ เพื่อกรองรายการสินค้าในแบบฟอร์มคำของบ",
    )

    _sql_constraints = [
        (
            "vpk_budget_asset_category_code_uniq",
            "unique(code)",
            "รหัสกลุ่มครุภัณฑ์ต้องไม่ซ้ำ",
        ),
    ]

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            if rec.code and rec.name:
                rec.display_name = f"{rec.code}: {rec.name}"
            else:
                rec.display_name = rec.name or rec.code or ""

    @api.model
    def _equipment_product_root(self):
        return self.env["product.category"].search(
            [("name", "=", "ครุภัณฑ์"), ("parent_id", "=", False)],
            limit=1,
        )

    @api.model
    def _find_for_product_category(self, product_categ):
        """Match a budget group by walking the product category tree."""
        while product_categ:
            rec = self.search([("product_categ_id", "=", product_categ.id)], limit=1)
            if rec:
                return rec
            product_categ = product_categ.parent_id
        return self.browse()

    @api.model
    def action_sync_from_product_categories(self):
        """Create/update budget groups from first-level ครุภัณฑ์ product categories."""
        root = self._equipment_product_root()
        if not root:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("กลุ่มครุภัณฑ์"),
                    "message": _("ไม่พบหมวดสินค้า ครุภัณฑ์ ในระบบคลัง"),
                    "type": "warning",
                },
            }
        type_categs = self.env["product.category"].search(
            [("parent_id", "=", root.id)],
            order="name, id",
        )
        existing = self.with_context(active_test=False).search([])
        used_codes = set(existing.mapped("code"))
        used_ids = set()
        sequence = 10
        for categ in type_categs:
            short_name = categ.name.split(".", 1)[-1].strip() or categ.name
            unused = existing.filtered(lambda r: r.id not in used_ids)
            rec = unused.filtered(lambda r, c=categ: r.product_categ_id == c)[:1]
            if not rec:
                rec = unused.filtered(lambda r, name=short_name: r.name == name)[:1]
            if not rec:
                rec = unused.filtered(lambda r, full=categ.name: r.name == full)[:1]
            if not rec:
                rec = unused.filtered(
                    lambda r, full=categ.name: r.name and full.endswith(r.name)
                )[:1]
            if rec:
                code = rec.code
            else:
                n = 1
                while "EQ%02d" % n in used_codes:
                    n += 1
                code = "EQ%02d" % n
                used_codes.add(code)
            vals = {
                "name": short_name,
                "product_categ_id": categ.id,
                "sequence": sequence,
                "active": True,
                "code": code,
            }
            if rec:
                rec.write(vals)
                used_ids.add(rec.id)
            else:
                created = self.create(vals)
                used_ids.add(created.id)
                existing |= created
            sequence += 10
        leftovers = existing.filtered(
            lambda r: r.id not in used_ids and not r.product_categ_id
        )
        if leftovers:
            leftovers.write({"active": False})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("กลุ่มครุภัณฑ์"),
                "message": _("ซิงก์จากหมวดสินค้าครุภัณฑ์เรียบร้อย"),
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
