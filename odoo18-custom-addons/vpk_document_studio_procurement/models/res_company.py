from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    official_doc_agency = fields.Char(
        string="หน่วยงานในหัวคำสั่ง",
        default="โรงพยาบาลวชิระภูเก็ต",
        help="ข้อความต่อจากคำว่า 'คำสั่ง' ในเอกสารจัดซื้อจัดจ้าง",
    )
    official_doc_signer_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ลงนามคำสั่ง",
        domain=[("share", "=", False)],
    )
    official_doc_signer_name = fields.Char(
        string="ชื่อผู้ลงนามคำสั่ง",
        default="นายวีระศักดิ์ หล่อทองคำ",
    )
    official_doc_signer_position = fields.Char(
        string="ตำแหน่งผู้ลงนามคำสั่ง",
        default="ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
    )
    official_doc_head_officer_id = fields.Many2one(
        comodel_name="res.users",
        string="หัวหน้าเจ้าหน้าที่",
        domain=[("share", "=", False)],
    )
    official_doc_head_officer_name = fields.Char(
        string="ชื่อหัวหน้าเจ้าหน้าที่",
        default="นางสาวปรีดา สุดขาว",
    )
    official_doc_head_officer_position = fields.Char(
        string="ตำแหน่งหัวหน้าเจ้าหน้าที่",
        default="หัวหน้าเจ้าหน้าที่",
    )
    official_doc_officer_id = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่",
        domain=[("share", "=", False)],
        help="เจ้าหน้าที่ที่ใช้ในแบบแสดงความบริสุทธิ์ใจและรายงานขออนุมัติจัดซื้อจัดจ้าง",
    )
    official_doc_officer_name = fields.Char(
        string="ชื่อเจ้าหน้าที่",
        help="ชื่อเจ้าหน้าที่ที่ใช้ในแบบแสดงความบริสุทธิ์ใจและรายงานขออนุมัติจัดซื้อจัดจ้าง",
    )
    official_doc_officer_position = fields.Char(
        string="ตำแหน่งเจ้าหน้าที่",
        default="เจ้าหน้าที่",
    )

    def write(self, vals):
        res = super().write(vals)
        person_fields = (
            "official_doc_signer_id",
            "official_doc_head_officer_id",
            "official_doc_officer_id",
        )
        if any(name in vals for name in person_fields) and not self.env.context.get(
            "skip_official_doc_person_sync"
        ):
            self._sync_official_doc_people_from_users()
        return res

    def _sync_official_doc_people_from_users(self):
        Values = self.env["vpk.procurement.document.values"]
        mapping = (
            ("signer", "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"),
            ("head_officer", "หัวหน้าเจ้าหน้าที่"),
            ("officer", "เจ้าหน้าที่"),
        )
        for company in self:
            updates = {}
            for role, default_position in mapping:
                user = company["official_doc_%s_id" % role]
                if not user:
                    continue
                name, position = Values.person_from_user(user)
                name_field = "official_doc_%s_name" % role
                position_field = "official_doc_%s_position" % role
                if name and company[name_field] != name:
                    updates[name_field] = name
                position = position or company[position_field] or default_position
                if position and company[position_field] != position:
                    updates[position_field] = position
            if updates:
                company.with_context(skip_official_doc_person_sync=True).write(updates)
