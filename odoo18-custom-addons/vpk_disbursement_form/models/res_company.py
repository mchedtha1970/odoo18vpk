# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import file_open


class ResCompany(models.Model):
    _inherit = "res.company"

    vpk_dr_agency_code = fields.Char(string="รหัสหน่วยงาน")
    vpk_dr_agency_name = fields.Char(string="ชื่อหน่วยงาน")
    vpk_dr_province_code = fields.Char(string="รหัสจังหวัด")
    vpk_dr_province_name = fields.Char(string="ชื่อจังหวัด")
    vpk_dr_unit_code = fields.Char(string="รหัสหน่วยเบิกจ่าย")
    vpk_dr_unit_name = fields.Char(string="ชื่อหน่วยเบิกจ่าย")
    vpk_dr_template_kb01 = fields.Binary(
        string="Template ขบ.01",
        attachment=True,
        help="ไฟล์ Excel template ขบ.01 ที่โหลดเข้าไว้ในระบบก่อนสร้างใบขอเบิกเงิน",
    )
    vpk_dr_template_kb01_filename = fields.Char(string="ชื่อไฟล์ template ขบ.01")
    vpk_dr_template_kb11 = fields.Binary(
        string="Template ขบ.11",
        attachment=True,
        help="ไฟล์ Excel template ขบ.11 ที่โหลดเข้าไว้ในระบบก่อนสร้างใบขอเบิกเงิน",
    )
    vpk_dr_template_kb11_filename = fields.Char(string="ชื่อไฟล์ template ขบ.11")

    def _vpk_get_disbursement_template_bytes(self, form_type):
        """คืนไบต์ของ template ที่โหลดไว้ในบริษัท ถ้ายังไม่โหลดใช้ไฟล์ในโมดูลเป็นค่าสำรอง."""
        self.ensure_one()
        field_map = {
            "kb01": ("vpk_dr_template_kb01", "vpk_disbursement_form/data/templates/kb01_template.xls"),
            "kb11": ("vpk_dr_template_kb11", "vpk_disbursement_form/data/templates/kb01_template.xls"),
        }
        if form_type not in field_map:
            raise UserError(_("ยังไม่รองรับแบบฟอร์ม %s") % form_type)
        field_name, fallback_path = field_map[form_type]
        content = getattr(self, field_name)
        if content:
            return base64.b64decode(content)
        with file_open(fallback_path, "rb") as handle:
            return handle.read()

    @api.model
    def _vpk_ensure_default_disbursement_templates(self):
        """โหลด template เริ่มต้นเข้าบริษัทหลักถ้ายังไม่มีไฟล์."""
        company = self.env.company
        updates = {}
        defaults = {
            "vpk_dr_template_kb01": ("kb01_template.xls", "vpk_disbursement_form/data/templates/kb01_template.xls"),
            "vpk_dr_template_kb11": ("kb11_template.xls", "vpk_disbursement_form/data/templates/kb01_template.xls"),
        }
        for field_name, (filename, path) in defaults.items():
            if not getattr(company, field_name):
                with file_open(path, "rb") as handle:
                    updates[field_name] = base64.b64encode(handle.read())
                updates["%s_filename" % field_name] = filename
        if updates:
            company.sudo().write(updates)
