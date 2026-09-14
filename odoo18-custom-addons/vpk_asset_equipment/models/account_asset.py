# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAsset(models.Model):
    _inherit = "account.asset"

    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        string="Equipment",
        copy=False,
        index=True,
        check_company=True,
    )
    equipment_count = fields.Integer(
        string="Equipment Count",
        compute="_compute_equipment_count",
    )
    # ข้อมูลทรัพย์สิน — กรอกก่อนสร้าง Equipment แล้วดึงไป Maintenance
    equipment_model = fields.Char(string="โมเดล")
    equipment_serial_no = fields.Char(string="หมายเลขซีเรียล", copy=False)
    equipment_location = fields.Char(string="พิกัดทรัพย์สิน")

    def _compute_equipment_count(self):
        for asset in self:
            asset.equipment_count = 1 if asset.equipment_id else 0

    def _get_or_create_equipment_category(self):
        """Map asset profile to maintenance.equipment.category (reuse if exists)."""
        self.ensure_one()
        profile = self.profile_id
        if not profile:
            return self.env["maintenance.equipment.category"]

        category_name = (profile.name or "").strip()
        if not category_name:
            return self.env["maintenance.equipment.category"]

        Category = self.env["maintenance.equipment.category"]
        domain = [("name", "=", category_name)]
        if self.company_id:
            domain = [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ] + domain
        category = Category.search(domain, limit=1)
        if category:
            return category

        return Category.create(
            {
                "name": category_name,
                "company_id": self.company_id.id or False,
            }
        )

    def _prepare_maintenance_equipment_vals(self):
        self.ensure_one()
        asset_number = (self.number or "").strip()
        category = self._get_or_create_equipment_category()
        vals = {
            "name": self.name,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id or False,
            "cost": self.purchase_value or 0.0,
            "effective_date": self.date_start or fields.Date.context_today(self),
            "assign_date": self.date_start or False,
            "asset_id": self.id,
            # เอกสารอ้างอิงจากผู้ขาย ← ค่าที่เคยใส่ใน Model (เช่น BILL/...)
            "partner_ref": (self.code or "").strip() or False,
            # หมายเลขทรัพย์สิน — ไม่ส่งไปหมายเลขซีเรียล / คำอธิบาย
            "asset_number": asset_number or False,
            # จากแท็บข้อมูลทรัพย์สิน
            "model": (self.equipment_model or "").strip() or False,
            "serial_no": (self.equipment_serial_no or "").strip() or False,
            "location": (self.equipment_location or "").strip() or False,
        }
        if category:
            vals["category_id"] = category.id
        return vals

    def _sync_equipment_missing_fields(self, equipment, vals):
        """Fill empty equipment fields from asset vals (do not overwrite)."""
        self.ensure_one()
        update_vals = {}
        for field_name in (
            "category_id",
            "asset_number",
            "partner_ref",
            "model",
            "serial_no",
            "location",
        ):
            if vals.get(field_name) and not equipment[field_name]:
                update_vals[field_name] = vals[field_name]
        if update_vals:
            equipment.write(update_vals)

    def action_create_equipment(self):
        self.ensure_one()
        vals = self._prepare_maintenance_equipment_vals()
        if self.equipment_id:
            self._sync_equipment_missing_fields(self.equipment_id, vals)
            return self.action_open_equipment()

        equipment = self.env["maintenance.equipment"].create(vals)
        # Ensure category is selected/saved even if create hooks clear it
        if vals.get("category_id") and equipment.category_id.id != vals["category_id"]:
            equipment.category_id = vals["category_id"]
        self.equipment_id = equipment.id
        self.message_post(
            body=_(
                "สร้าง Equipment <a href=# data-oe-model='maintenance.equipment' "
                "data-oe-id='%(id)s'>%(name)s</a> ในระบบบำรุงรักษาแล้ว"
            )
            % {"id": equipment.id, "name": equipment.display_name}
        )
        return self.action_open_equipment()

    def action_open_equipment(self):
        self.ensure_one()
        if not self.equipment_id:
            raise UserError(_("ยังไม่มี Equipment ที่เชื่อมกับสินทรัพย์นี้"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Equipment"),
            "res_model": "maintenance.equipment",
            "view_mode": "form",
            "res_id": self.equipment_id.id,
            "target": "current",
        }
