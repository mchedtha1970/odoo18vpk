# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    official_doc_agency = fields.Char(
        string="หน่วยงานในหัวคำสั่ง",
        default="โรงพยาบาลวชิระภูเก็ต",
        help="ข้อความต่อจากคำว่า 'คำสั่ง' ในหนังสือราชการ",
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for company in records:
            company._sync_official_doc_defaults_from_memo()
        return records

    def _sync_official_doc_defaults_from_memo(self):
        """Reuse memo signer names when this company already has them."""
        self.ensure_one()
        updates = {}
        if not self.official_doc_signer_name and "vpk_memo_approver_name" in self._fields:
            updates["official_doc_signer_name"] = self.vpk_memo_approver_name
        if (
            not self.official_doc_signer_position
            and "vpk_memo_approver_position" in self._fields
        ):
            updates["official_doc_signer_position"] = self.vpk_memo_approver_position
        if not self.official_doc_agency:
            updates["official_doc_agency"] = self.name or "โรงพยาบาลวชิระภูเก็ต"
        if (
            not self.official_doc_head_officer_name
            and "vpk_memo_proposer_name" in self._fields
        ):
            updates["official_doc_head_officer_name"] = self.vpk_memo_proposer_name
        if (
            not self.official_doc_head_officer_position
            and "vpk_memo_proposer_position" in self._fields
        ):
            updates["official_doc_head_officer_position"] = self.vpk_memo_proposer_position
        if updates:
            self.write(updates)

    def write(self, vals):
        res = super().write(vals)
        person_ids = (
            "official_doc_signer_id",
            "official_doc_head_officer_id",
            "official_doc_officer_id",
        )
        if any(field_name in vals for field_name in person_ids) and not self.env.context.get(
            "skip_official_doc_person_sync"
        ):
            self._sync_official_doc_people_from_users()
        return res

    def _sync_official_doc_people_from_users(self):
        Document = self.env["vpk.official.document"]
        mapping = (
            (
                "official_doc_signer_id",
                "official_doc_signer_name",
                "official_doc_signer_position",
                "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
            ),
            (
                "official_doc_head_officer_id",
                "official_doc_head_officer_name",
                "official_doc_head_officer_position",
                "หัวหน้าเจ้าหน้าที่",
            ),
            (
                "official_doc_officer_id",
                "official_doc_officer_name",
                "official_doc_officer_position",
                "เจ้าหน้าที่",
            ),
        )
        for company in self:
            updates = {}
            for user_field, name_field, position_field, default_position in mapping:
                user = company[user_field]
                if not user:
                    continue
                name, position = Document._person_from_user(user)
                if name and company[name_field] != name:
                    updates[name_field] = name
                position = position or company[position_field] or default_position
                if position and company[position_field] != position:
                    updates[position_field] = position
            if updates:
                company.with_context(skip_official_doc_person_sync=True).write(updates)
