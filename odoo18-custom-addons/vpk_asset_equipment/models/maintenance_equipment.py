# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    _rec_names_search = ["name", "serial_no", "asset_number"]

    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="ทรัพย์สิน",
        copy=False,
        index=True,
        check_company=True,
        ondelete="set null",
    )
    asset_number = fields.Char(
        string="หมายเลขทรัพย์สิน",
        copy=False,
        index=True,
        help="เลขที่สินทรัพย์คงที่ (Fixed Asset Number)",
    )

    @api.depends(
        "name",
        "serial_no",
        "asset_id",
        "asset_number",
        "asset_id.number",
        "asset_id.name",
    )
    def _compute_display_name(self):
        """แสดงเลขที่ asset และชื่อ เมื่อ equipment ลิงก์กับทรัพย์สิน (ใช้ตอนเลือกในคำขอซ่อม)"""
        linked = self.filtered("asset_id")
        for record in linked:
            number = (record.asset_number or record.asset_id.number or "").strip()
            name = (record.name or record.asset_id.name or "").strip()
            if number and name:
                record.display_name = f"{number} - {name}"
            elif number:
                record.display_name = number
            else:
                record.display_name = name or record.name
        remaining = self - linked
        if remaining:
            super(MaintenanceEquipment, remaining)._compute_display_name()

    def action_open_fixed_asset(self):
        self.ensure_one()
        if not self.asset_id:
            return True
        return {
            "type": "ir.actions.act_window",
            "name": _("ทรัพย์สิน"),
            "res_model": "account.asset",
            "view_mode": "form",
            "res_id": self.asset_id.id,
            "target": "current",
        }
