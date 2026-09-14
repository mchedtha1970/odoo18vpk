from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    duplicate_vat_warning = fields.Text(
        string="Tax ID ซ้ำ",
        compute="_compute_duplicate_warnings",
    )
    duplicate_name_warning = fields.Text(
        string="ชื่อซ้ำ",
        compute="_compute_duplicate_warnings",
    )
    duplicate_phone_warning = fields.Text(
        string="เบอร์โทรซ้ำ",
        compute="_compute_duplicate_warnings",
    )
    duplicate_email_warning = fields.Text(
        string="อีเมลซ้ำ",
        compute="_compute_duplicate_warnings",
    )
    has_duplicate_warning = fields.Boolean(
        compute="_compute_duplicate_warnings",
    )

    @api.depends("vat", "name", "phone", "email")
    def _compute_duplicate_warnings(self):
        for partner in self:
            partner.duplicate_vat_warning = False
            partner.duplicate_name_warning = False
            partner.duplicate_phone_warning = False
            partner.duplicate_email_warning = False
            partner.has_duplicate_warning = False

            if partner.parent_id:
                continue

            if partner.vat:
                dupes = self.search([
                    ("vat", "=", partner.vat),
                    ("id", "!=", partner._origin.id),
                    ("parent_id", "=", False),
                ], limit=5)
                if dupes:
                    names = ", ".join(dupes.mapped("name"))
                    partner.duplicate_vat_warning = _(
                        "Tax ID %s ซ้ำกับ: %s"
                    ) % (partner.vat, names)
                    partner.has_duplicate_warning = True

            if partner.name and len(partner.name) > 3:
                dupes = self.search([
                    ("name", "=ilike", partner.name),
                    ("id", "!=", partner._origin.id),
                    ("parent_id", "=", False),
                ], limit=5)
                if dupes:
                    names = ", ".join(
                        "%s (Tax ID: %s)" % (d.name, d.vat or "-")
                        for d in dupes
                    )
                    partner.duplicate_name_warning = _(
                        "พบชื่อที่คล้ายกัน: %s"
                    ) % names
                    partner.has_duplicate_warning = True

            if partner.phone:
                clean = partner.phone.replace("-", "").replace(" ", "").strip()
                if len(clean) >= 8:
                    dupes = self.search([
                        ("phone", "ilike", clean[-8:]),
                        ("id", "!=", partner._origin.id),
                        ("parent_id", "=", False),
                    ], limit=5)
                    if dupes:
                        names = ", ".join(dupes.mapped("name"))
                        partner.duplicate_phone_warning = _(
                            "เบอร์โทร %s ซ้ำกับ: %s"
                        ) % (partner.phone, names)
                        partner.has_duplicate_warning = True

            if partner.email:
                dupes = self.search([
                    ("email", "=ilike", partner.email),
                    ("id", "!=", partner._origin.id),
                    ("parent_id", "=", False),
                ], limit=5)
                if dupes:
                    names = ", ".join(dupes.mapped("name"))
                    partner.duplicate_email_warning = _(
                        "อีเมล %s ซ้ำกับ: %s"
                    ) % (partner.email, names)
                    partner.has_duplicate_warning = True

    @api.onchange("vat")
    def _onchange_vat_duplicate_check(self):
        if not self.vat or self.parent_id:
            return
        dupes = self.search([
            ("vat", "=", self.vat),
            ("id", "!=", self._origin.id),
            ("parent_id", "=", False),
        ], limit=5)
        if dupes:
            names = ", ".join(dupes.mapped("name"))
            return {
                "warning": {
                    "title": _("Tax ID ซ้ำ!"),
                    "message": _(
                        "Tax ID %s มีอยู่แล้วในระบบ:\n%s\n\n"
                        "กรุณาตรวจสอบก่อนบันทึก หากบันทึกระบบจะบล็อกไม่ให้สร้างซ้ำ"
                    ) % (self.vat, names),
                    "type": "warning",
                }
            }

    @api.onchange("name")
    def _onchange_name_duplicate_check(self):
        if not self.name or len(self.name) <= 3 or self.parent_id:
            return
        dupes = self.search([
            ("name", "=ilike", self.name),
            ("id", "!=", self._origin.id),
            ("parent_id", "=", False),
        ], limit=5)
        if dupes:
            names = "\n".join(
                "- %s (Tax ID: %s)" % (d.name, d.vat or "-")
                for d in dupes
            )
            return {
                "warning": {
                    "title": _("พบชื่อผู้ขาย/ผู้ติดต่อที่คล้ายกัน"),
                    "message": _(
                        "ชื่อ \"%s\" คล้ายกับรายการที่มีอยู่:\n%s\n\n"
                        "กรุณาตรวจสอบว่าไม่ซ้ำซ้อนก่อนบันทึก"
                    ) % (self.name, names),
                    "type": "warning",
                }
            }

    @api.onchange("phone")
    def _onchange_phone_duplicate_check(self):
        if not self.phone or self.parent_id:
            return
        clean = self.phone.replace("-", "").replace(" ", "").strip()
        if len(clean) < 8:
            return
        dupes = self.search([
            ("phone", "ilike", clean[-8:]),
            ("id", "!=", self._origin.id),
            ("parent_id", "=", False),
        ], limit=5)
        if dupes:
            names = ", ".join(dupes.mapped("name"))
            return {
                "warning": {
                    "title": _("เบอร์โทรซ้ำ!"),
                    "message": _(
                        "เบอร์โทร %s ซ้ำกับ: %s"
                    ) % (self.phone, names),
                    "type": "warning",
                }
            }
