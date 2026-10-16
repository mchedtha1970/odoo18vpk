# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.exceptions import UserError


class VendorPortalShareWizard(models.TransientModel):
    _name = "vendor.portal.share.wizard"
    _description = "แชร์ลิงก์พอร์ทัลผู้จำหน่าย"

    portal_url = fields.Char(
        string="ลิงก์ Login Vendor Portal",
        readonly=True,
        default=lambda self: (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url", "") or ""
        ).rstrip("/")
        + "/vendor",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="ผู้จำหน่าย",
        domain="[('supplier_rank', '>', 0)]",
    )

    def action_send(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("กรุณาเลือกผู้จำหน่ายที่จะส่งลิงก์"))
        if not self.partner_id.email:
            raise UserError(
                _(
                    "ผู้จำหน่าย %(vendor)s ยังไม่มีอีเมล",
                    vendor=self.partner_id.display_name,
                )
            )
        compose_form = self.env.ref(
            "mail.email_compose_message_wizard_form", raise_if_not_found=False
        )
        body = _(
            "ลิงก์เข้าพอร์ทัลผู้จำหน่าย: %(url)s",
            url=self.portal_url,
        )
        return {
            "name": _("แชร์ลิงก์พอร์ทัล"),
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(compose_form.id if compose_form else False, "form")],
            "view_id": compose_form.id if compose_form else False,
            "target": "new",
            "context": {
                "default_model": "res.partner",
                "default_res_ids": self.partner_id.ids,
                "default_composition_mode": "comment",
                "default_partner_ids": self.partner_id.ids,
                "default_subject": _("ลิงก์พอร์ทัลผู้จำหน่าย"),
                "default_body": "<p>%s</p>" % body,
                "force_email": True,
            },
        }
