# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class VpkDocumentCategory(models.Model):
    _name = "vpk.document.category"
    _description = "หมวดหมู่ไฟล์"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "parent_path, sequence, name, id"

    name = fields.Char(string="ชื่อโฟลเดอร์", required=True)
    complete_name = fields.Char(
        string="เส้นทาง",
        compute="_compute_complete_name",
        store=True,
        recursive=True,
    )
    parent_id = fields.Many2one(
        comodel_name="vpk.document.category",
        string="โฟลเดอร์แม่",
        index=True,
        ondelete="restrict",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        comodel_name="vpk.document.category",
        inverse_name="parent_id",
        string="โฟลเดอร์ย่อย",
    )
    code = fields.Char(string="รหัส")
    sequence = fields.Integer(string="ลำดับ", default=10)
    description = fields.Text(string="คำอธิบาย")
    active = fields.Boolean(default=True)
    document_count = fields.Integer(
        string="จำนวนไฟล์",
        compute="_compute_document_count",
    )

    def init(self):
        self.env.cr.execute(
            "ALTER TABLE vpk_document_category "
            "DROP CONSTRAINT IF EXISTS vpk_document_category_name_uniq"
        )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = "%s / %s" % (
                    category.parent_id.complete_name,
                    category.name,
                )
            else:
                category.complete_name = category.name

    @api.depends("complete_name", "name")
    def _compute_display_name(self):
        hierarchical = self.env.context.get("hierarchical_naming", True)
        for category in self:
            if hierarchical:
                category.display_name = category.complete_name or category.name
            else:
                category.display_name = category.name

    def _compute_document_count(self):
        counts = {category.id: 0 for category in self}
        if self:
            folders = self.search([("id", "child_of", self.ids)])
            path_of = {folder.id: folder.parent_path or "" for folder in folders}
            groups = self.env["vpk.document"]._read_group(
                [("category_id", "in", folders.ids)],
                ["category_id"],
                ["__count"],
            )
            for folder, count in groups:
                path = path_of.get(folder.id, "")
                for category in self:
                    prefix = path_of.get(category.id, "")
                    if prefix and path.startswith(prefix):
                        counts[category.id] += count
        for category in self:
            category.document_count = counts[category.id]

    @api.constrains("name", "parent_id")
    def _check_name_under_parent(self):
        for category in self:
            duplicate = self.search(
                [
                    ("id", "!=", category.id),
                    ("name", "=", category.name),
                    ("parent_id", "=", category.parent_id.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("มีโฟลเดอร์ชื่อ %s อยู่ในตำแหน่งนี้แล้ว") % category.name
                )

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if self._has_cycle():
            raise ValidationError(_("โฟลเดอร์ย่อยต้องไม่วนกลับไปหาโฟลเดอร์แม่"))

    @api.constrains("code")
    def _check_code_unique(self):
        for category in self:
            if not category.code:
                continue
            duplicate = self.search(
                [("code", "=", category.code), ("id", "!=", category.id)],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("รหัสหมวดหมู่ %s มีอยู่แล้ว") % category.code
                )
