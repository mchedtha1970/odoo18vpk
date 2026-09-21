# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    gfmis_agency_code = fields.Char(
        string="รหัสหน่วยงาน GFMIS",
        size=5,
        help="รหัสหน่วยงาน 5 หลัก ตามสิทธิ New GFMIS Thai ตัวอย่าง 03003",
    )
    gfmis_area_code = fields.Char(
        string="รหัสพื้นที่ GFMIS",
        size=4,
        help="รหัสพื้นที่ 4 หลัก ตัวอย่าง 1000",
    )
    gfmis_disbursing_unit_code = fields.Char(
        string="รหัสหน่วยเบิกจ่าย GFMIS",
        size=10,
        help="รหัสหน่วยเบิกจ่าย 10 หลัก ตัวอย่าง 0300300003",
    )
