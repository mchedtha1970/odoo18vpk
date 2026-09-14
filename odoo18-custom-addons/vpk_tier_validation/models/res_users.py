# -*- coding: utf-8 -*-
from odoo import api, models

# กำหนดสิทธิ์ตาม login — ปรับรายชื่อได้ที่นี่
VPK_PR_GROUP_USERS = {
    "vpk_tier_validation.group_vpk_pr_confirm": [
        "niran@vpk.demo",      # หัวหน้าพัสดุ L1
        "supaporn@vpk.demo",   # รองหัวหน้าพัสดุ L2
    ],
    "vpk_tier_validation.group_vpk_pr_verify": [
        "niran@vpk.demo",
        "supaporn@vpk.demo",
        "somjit@vpk.demo",     # เจ้าหน้าที่จัดซื้อ
    ],
    "vpk_tier_validation.group_vpk_procurement_officer": [
        "niran@vpk.demo",
        "supaporn@vpk.demo",
        "somjit@vpk.demo",
        "wichai@vpk.demo",
    ],
}


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _vpk_assign_pr_workflow_groups(self):
        """Assign VPK purchase workflow groups to users by login."""
        for group_xmlid, logins in VPK_PR_GROUP_USERS.items():
            try:
                group = self.env.ref(group_xmlid)
            except ValueError:
                continue
            users = self.sudo().search([("login", "in", logins), ("active", "=", True)])
            if not users:
                continue
            group.sudo().write({"users": [(4, user.id) for user in users]})
