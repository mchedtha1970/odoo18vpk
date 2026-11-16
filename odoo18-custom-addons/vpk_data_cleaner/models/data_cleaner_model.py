# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import SQL


class VpkDataCleanerModel(models.Model):
    _name = "vpk.data.cleaner.model"
    _description = "โมเดลข้อมูลแยกประเภท Master / Transaction"
    _order = "cleaner_module_id asc, data_type desc, model_name asc"

    cleaner_module_id = fields.Many2one(
        "vpk.data.cleaner.module",
        string="โมดูล (Module)",
        required=True,
        ondelete="cascade",
        index=True,
    )
    module_technical_name = fields.Char(
        related="cleaner_module_id.technical_name",
        string="รหัสโมดูล",
        store=True,
        index=True,
    )
    module_group = fields.Selection(
        related="cleaner_module_id.module_group",
        string="กลุ่มโมดูล",
        store=True,
        index=True,
    )
    ir_model_id = fields.Many2one(
        "ir.model",
        string="อ้างอิง Ir Model",
        ondelete="cascade",
    )
    name = fields.Char(string="ชื่อโมเดล (ภาษาไทย/อังกฤษ)", required=True, index=True)
    model_name = fields.Char(string="ชื่อเทคนิค (Model)", required=True, index=True)
    table_name = fields.Char(string="ตารางฐานข้อมูล (Table)", readonly=True)
    parent_model_name = fields.Char(string="ตารางหลัก (กรณีตารางลูก)", readonly=True)

    data_type = fields.Selection(
        [
            ("transaction", "Transaction (ข้อมูลรายการ)"),
            ("master", "Master (ข้อมูลหลัก / ตั้งค่า)"),
        ],
        string="ประเภทโมเดล",
        required=True,
        default="transaction",
        index=True,
    )
    is_type_overridden = fields.Boolean(
        string="ปรับประเภทด้วยตนเอง",
        default=False,
        help="หากเปิดไว้ ระบบจะไม่เขียนทับประเภท Master/Transaction ที่คุณเลือกไว้เมื่อกดซิงค์ใหม่",
    )
    classification_reason = fields.Char(string="บทบาท / คำอธิบายข้อมูล")
    record_count = fields.Integer(string="จำนวนข้อมูล (แถว)", default=0, readonly=True)
    protect_note = fields.Char(string="หมายเหตุความปลอดภัย", readonly=True)

    last_cleared_at = fields.Datetime(string="ล้างข้อมูลล่าสุดเมื่อ", readonly=True)
    last_cleared_by = fields.Many2one("res.users", string="ล้างข้อมูลล่าสุดโดย", readonly=True)

    _sql_constraints = [
        (
            "model_name_uniq",
            "unique(model_name)",
            "ชื่อเทคนิคของโมเดลต้องไม่ซ้ำกัน",
        ),
    ]

    def write(self, vals):
        if "data_type" in vals and "is_type_overridden" not in vals and not self.env.context.get("syncing_cleaner"):
            # ถ้าผู้ใช้แก้ประเภทเองจากหน้าจอ ให้ล็อกค่าที่ผู้ใช้กำหนดไว้
            vals = dict(vals, is_type_overridden=True)
        return super().write(vals)

    def _refresh_record_counts(self):
        """นับจำนวนแถวสดจากตารางจริงใน PostgreSQL"""
        cr = self.env.cr
        cr.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        existing_tables = {r[0] for r in cr.fetchall()}
        for rec in self:
            if rec.table_name and rec.table_name in existing_tables:
                cr.execute(SQL("SELECT COUNT(*) FROM %s", SQL.identifier(rec.table_name)))
                rec.record_count = cr.fetchone()[0] or 0
            else:
                rec.record_count = 0

    def action_open_records(self):
        """เปิดดูรายการข้อมูลจริงในโมเดลนั้น"""
        self.ensure_one()
        if self.model_name not in self.env:
            raise UserError(_("ไม่พบโมเดล %s ในระบบปัจจุบัน") % self.model_name)
        return {
            "type": "ir.actions.act_window",
            "name": f"{self.name} ({self.model_name})",
            "res_model": self.model_name,
            "view_mode": "list,form",
            "target": "current",
            "context": {"active_test": False},
        }

    def action_open_clear_wizard(self):
        """เปิดหน้าต่างยืนยันการล้างข้อมูลสำหรับโมเดลที่เลือก (1 หรือหลายโมเดล)"""
        if not self:
            raise UserError(_("กรุณาเลือกอย่างน้อย 1 โมเดลที่ต้องการล้างข้อมูล"))
        self._refresh_record_counts()
        wiz = self.env["vpk.data.cleaner.wizard"].create_from_models(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("ยืนยันการล้างข้อมูล (Clear Model Data)"),
            "res_model": "vpk.data.cleaner.wizard",
            "res_id": wiz.id,
            "view_mode": "form",
            "target": "new",
        }
