# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    vpk_po_agency_name = fields.Char(
        string="ส่วนราชการ (ใบสั่งซื้อ)",
        default="จังหวัดภูเก็ต",
        help="ข้อความส่วนราชการมุมขวาบนใบสั่งซื้อ/สั่งจ้าง",
    )
    vpk_po_agency_address = fields.Text(
        string="ที่อยู่ส่วนราชการ (ใบสั่งซื้อ)",
        default="ศาลากลางจังหวัดภูเก็ต ต.ตลาดเหนือ\nอ.เมือง จ.ภูเก็ต",
    )
    vpk_po_delivery_place = fields.Text(
        string="สถานที่ส่งมอบ (ใบสั่งซื้อ)",
        default=(
            "งานพัสดุ โรงพยาบาลวชิระภูเก็ต "
            "๓๕๓ ถนนเยาวราช ตำบลตลาดใหญ่ อำเภอเมือง จังหวัดภูเก็ต ๘๓๐๐๐"
        ),
    )
    vpk_po_delivery_days = fields.Integer(
        string="กำหนดส่งมอบ (วัน)",
        default=90,
    )
    vpk_po_warranty_months = fields.Integer(
        string="ระยะเวลารับประกัน (เดือน)",
        default=3,
    )
    vpk_po_penalty_rate = fields.Float(
        string="อัตราค่าปรับรายวัน (%)",
        default=0.20,
        digits=(16, 2),
    )
    vpk_po_penalty_min = fields.Float(
        string="ค่าปรับขั้นต่ำต่อวัน (บาท)",
        default=100.0,
    )
    vpk_po_signer_name = fields.Char(
        string="ชื่อผู้ลงนามใบสั่งซื้อ",
    )
    vpk_po_signer_position = fields.Char(
        string="ตำแหน่งผู้ลงนามใบสั่งซื้อ",
        default="ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
    )
