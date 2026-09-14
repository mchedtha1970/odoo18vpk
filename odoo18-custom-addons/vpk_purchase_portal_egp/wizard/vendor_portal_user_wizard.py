# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import email_normalize


class VendorPortalUserWizard(models.TransientModel):
    _name = "vendor.portal.user.wizard"
    _description = "สร้าง User Portal สำหรับผู้จำหน่าย"

    partner_id = fields.Many2one(
        "res.partner",
        string="ผู้จำหน่าย",
        required=True,
        readonly=True,
    )
    name = fields.Char(related="partner_id.name", string="ชื่อ", readonly=True)
    email = fields.Char(
        string="อีเมล",
        required=True,
        help="บันทึกลงโปรไฟล์ vendor (ใช้เป็นข้อมูลติดต่อ แม้ระบบอีเมลยังไม่ทำงาน)",
    )
    login = fields.Char(
        string="User ID (Login)",
        required=True,
        help="ใช้เข้าสู่ระบบ Vendor Portal ที่ /vendor",
    )
    password = fields.Char(string="รหัสผ่าน")
    password_confirm = fields.Char(string="ยืนยันรหัสผ่าน")
    user_id = fields.Many2one(
        "res.users",
        string="User ที่มีอยู่",
        compute="_compute_user_id",
        readonly=True,
    )
    is_portal = fields.Boolean(compute="_compute_user_id")
    portal_url = fields.Char(string="ลิงก์ Vendor Portal", readonly=True)
    result_login = fields.Char(string="User ID ที่สร้างแล้ว", readonly=True)
    state = fields.Selection(
        [("draft", "ตั้งค่า"), ("done", "เสร็จสิ้น")],
        default="draft",
        readonly=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        default=lambda self: _(
            "ระบบอีเมลยังไม่ใช้งาน — กรอกอีเมล + User ID + รหัสผ่านแล้วกดสร้าง\n"
            "จากนั้นแจ้ง User/Password ให้ผู้จำหน่ายเข้าที่ /vendor"
        ),
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        partner = self.env["res.partner"].browse(
            self.env.context.get("default_partner_id")
            or self.env.context.get("active_id")
        )
        if partner:
            res.setdefault("partner_id", partner.id)
            email = partner.email or False
            res.setdefault("email", email)
            # Prefer existing portal login, else email, else partner ref/name slug
            existing = partner.with_context(active_test=False).user_ids[:1]
            if existing:
                res.setdefault("login", existing.login)
            elif email:
                res.setdefault("login", email_normalize(email) or email)
            else:
                res.setdefault(
                    "login",
                    (partner.ref or ("vendor%s" % partner.id)).replace(" ", "").lower(),
                )
        res.setdefault(
            "portal_url",
            self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
            + "/vendor",
        )
        return res

    @api.depends("partner_id")
    def _compute_user_id(self):
        for wiz in self:
            user = wiz.partner_id.with_context(active_test=False).user_ids[:1]
            wiz.user_id = user
            wiz.is_portal = bool(user and user.active and user._is_portal())

    @api.onchange("email")
    def _onchange_email(self):
        if self.email and not self.user_id:
            normalized = email_normalize(self.email) or self.email.strip()
            if not self.login or self.login == (self.partner_id.email or ""):
                self.login = normalized

    def action_create_portal_user(self):
        self.ensure_one()
        if not self.password or len(self.password) < 4:
            raise UserError(_("รหัสผ่านต้องมีอย่างน้อย 4 ตัวอักษร"))
        if self.password != self.password_confirm:
            raise UserError(_("รหัสผ่านกับยืนยันรหัสผ่านไม่ตรงกัน"))

        email = (self.email or "").strip()
        login = (self.login or "").strip()
        if not email or not login:
            raise UserError(_("กรุณาระบุอีเมลและ User ID"))

        partner = self.partner_id.sudo()
        partner.write({"email": email})

        group_portal = self.env.ref("base.group_portal")
        group_public = self.env.ref("base.group_public")
        Users = self.env["res.users"].sudo().with_context(no_reset_password=True, active_test=False)

        # Login uniqueness
        conflict = Users.search([("login", "=", login), ("partner_id", "!=", partner.id)], limit=1)
        if conflict:
            raise UserError(
                _("User ID '%(login)s' ถูกใช้แล้วโดย %(name)s", login=login, name=conflict.name)
            )

        user = partner.user_ids[:1]
        if user and user._is_internal():
            raise UserError(
                _("ผู้ติดต่อนี้ผูกกับ Internal User อยู่แล้ว ไม่สามารถสร้างเป็น Portal ได้")
            )

        company = partner.company_id or self.env.company
        if not user:
            user = Users.with_company(company)._create_user_from_template(
                {
                    "name": partner.name,
                    "login": login,
                    "email": email_normalize(email) or email,
                    "partner_id": partner.id,
                    "company_id": company.id,
                    "company_ids": [(6, 0, company.ids)],
                }
            )
        else:
            user.write(
                {
                    "login": login,
                    "email": email_normalize(email) or email,
                    "active": True,
                }
            )

        user.write(
            {
                "active": True,
                "groups_id": [(4, group_portal.id), (3, group_public.id)],
            }
        )
        # Hash password directly — write({'password': ...}) is unreliable on portal users.
        user.sudo()._set_encrypted_password(
            user.id, user._crypt_context().hash(self.password)
        )
        # Password already set: no email signup token needed.
        partner.sudo().signup_type = False

        portal_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
            + "/vendor"
        )
        self.write(
            {
                "state": "done",
                "user_id": user.id,
                "result_login": user.login,
                "portal_url": portal_url,
                "password": False,
                "password_confirm": False,
            }
        )
        partner.message_post(
            body=_(
                "สร้าง/อัปเดต Vendor Portal User: <b>%(login)s</b><br/>"
                "ลิงก์เข้าสู่ระบบ: %(url)s",
                login=user.login,
                url=portal_url,
            )
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
