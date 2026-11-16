# -*- coding: utf-8 -*-
from odoo import fields, models


class VpkDataCleanerLog(models.Model):
    _name = "vpk.data.cleaner.log"
    _description = "ประวัติการล้างข้อมูลโมเดล"
    _order = "executed_at desc, id desc"

    name = fields.Char(string="รายการดำเนินการ", required=True, readonly=True)
    executed_at = fields.Datetime(
        string="วันเวลาที่ล้างข้อมูล",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="ผู้ดำเนินการ",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )
    database_name = fields.Char(
        string="ฐานข้อมูล",
        default=lambda self: self.env.cr.dbname,
        readonly=True,
    )
    module_names = fields.Char(string="โมดูลที่เกี่ยวข้อง", readonly=True)
    model_count = fields.Integer(string="จำนวนโมเดลที่ล้าง", readonly=True)
    deleted_row_count = fields.Integer(string="จำนวนแถวที่ลบทั้งหมด", readonly=True)
    included_master = fields.Boolean(string="มีการล้าง Master Data", readonly=True)
    reset_sequences = fields.Boolean(string="รีเซ็ตเลขรันเอกสาร", readonly=True)
    detail_log = fields.Text(string="รายละเอียดผลการลบรายโมเดล", readonly=True)
