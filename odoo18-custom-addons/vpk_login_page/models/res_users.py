# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import str2bool

TEST_USERS = [
    ("uat.dept", "หน่วยงาน", "สร้างคำของบ ใบขอซื้อ ส่งพัสดุ"),
    ("uat.budget", "งานงบประมาณ", "รับเรื่อง จัดสรร อนุมัติคำของบ"),
    ("uat.procurement", "พัสดุ / จัดซื้อ", "e-GP คัดเลือกผู้ชนะ เปิด PO"),
    ("uat.officer", "เจ้าหน้าที่", "ลงนามลำดับแรก"),
    ("uat.head_officer", "หัวหน้าเจ้าหน้าที่", "ลงนามลำดับที่สอง"),
    ("uat.secretary", "เลขาผู้อำนวยการ", "กลั่นกรองเอกสารก่อนถึงผู้อำนวยการ ตีกลับหรือส่งต่อ"),
    ("uat.director", "ผู้อำนวยการโรงพยาบาล", "ลงนามคำสั่งและรายงานลำดับสุดท้าย"),
    ("uat.committee1", "ประธานกรรมการตรวจรับ", "ลงนามใบตรวจรับ"),
    ("uat.committee2", "กรรมการตรวจรับ", "ลงนามใบตรวจรับ"),
    ("uat.committee3", "กรรมการและเลขานุการ", "ลงนามใบตรวจรับ"),
    ("uat.warehouse", "คลังสินค้า", "รับเข้า จ่ายออก ตรวจนับ"),
]


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _vpk_login_test_users(self):
        config = self.env["ir.config_parameter"].sudo()
        param = config.get_param("vpk_login_page.test_users_enabled", "False")
        if not str2bool(param, False):
            return []
        password = config.get_param("vpk_login_page.test_users_password") or ""
        logins = [login for login, _role, _desc in TEST_USERS]
        users = self.sudo().search([("login", "in", logins), ("active", "=", True)])
        names = {user.login: user.name for user in users}
        return [
            {"login": login, "role": role, "desc": desc, "name": names[login], "password": password}
            for login, role, desc in TEST_USERS
            if login in names
        ]
