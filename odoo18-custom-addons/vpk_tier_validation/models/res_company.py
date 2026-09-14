# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    vpk_memo_agency = fields.Char(
        string="ส่วนราชการ (บันทึกข้อความ)",
        default="กลุ่มงานพัสดุ โรงพยาบาลวชิระภูเก็ต",
    )
    vpk_memo_phone = fields.Char(
        string="โทรศัพท์ (บันทึกข้อความ)",
        default="โทร ๐ ๗๖๓๖ ๑๒๓๔ ต่อ ๖๕๕๓-๔",
    )
    vpk_memo_default_to = fields.Char(
        string="เรียน (ค่าเริ่มต้น)",
        default="ผู้ว่าราชการจังหวัดภูเก็ต",
    )
    vpk_memo_proposer_name = fields.Char(
        string="ผู้เสนอ (ชื่อ)",
        default="นางสาวปรีดา สุดขาว",
    )
    vpk_memo_proposer_position = fields.Char(
        string="ผู้เสนอ (ตำแหน่ง)",
        default="หัวหน้าเจ้าหน้าที่",
    )
    vpk_memo_approver_name = fields.Char(
        string="ผู้อนุมัติ (ชื่อ)",
        default="นายวีระศักดิ์ หล่อทองคำ",
    )
    vpk_memo_approver_position = fields.Char(
        string="ผู้อนุมัติ (ตำแหน่ง)",
        default="ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
    )
    vpk_memo_approver_acting = fields.Char(
        string="ผู้อนุมัติ (ปฏิบัติราชการแทน)",
        default="ปฏิบัติราชการแทนผู้ว่าราชการจังหวัดภูเก็ต",
    )
