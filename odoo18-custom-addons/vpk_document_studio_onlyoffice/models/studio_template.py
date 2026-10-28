# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, fields, models
from odoo.exceptions import UserError

from .ir_attachment import OO_MARK, OO_MIMETYPE


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    onlyoffice_host = fields.Boolean(
        string="OnlyOffice",
        compute="_compute_onlyoffice_host",
    )

    def _compute_onlyoffice_host(self):
        for rec in self:
            rec.onlyoffice_host = bool(rec.datas)

    def action_edit_with_onlyoffice(self):
        self.ensure_one()
        if not self.datas:
            raise UserError(_("อัปโหลดไฟล์ Word ก่อน แล้วค่อยเปิดแก้ไขด้วย OnlyOffice"))
        attachment = self._onlyoffice_word_attachment()
        return {
            "type": "ir.actions.client",
            "tag": "onlyoffice_editor",
            "name": self.filename or self.name,
            "target": "current",
            "params": {"attachment_id": attachment.id},
        }

    def onlyoffice_word_attachment_id(self):
        self.ensure_one()
        if not self.datas:
            raise UserError(_("อัปโหลดไฟล์ Word ก่อน แล้วค่อยเปิดแก้ไขด้วย OnlyOffice"))
        return self._onlyoffice_word_attachment().id

    def _onlyoffice_word_attachment(self):
        """Standalone .docx attachment that OnlyOffice can open and save back."""
        self.ensure_one()
        name = (self.filename or "%s.docx" % (self.code or "template")).strip()
        if not name.lower().endswith(".docx"):
            name = "%s.docx" % name
        Attachment = self.env["ir.attachment"].sudo()
        attachment = Attachment.search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("res_field", "=", False),
                ("description", "=", OO_MARK),
            ],
            limit=1,
        )
        values = {
            "name": name,
            "raw": self._template_bytes(),
            "mimetype": OO_MIMETYPE,
            "type": "binary",
            "res_model": self._name,
            "res_id": self.id,
            "description": OO_MARK,
        }
        ctx_attachment = Attachment.with_context(skip_onlyoffice_sync=True)
        if attachment:
            ctx_attachment.browse(attachment.id).write(values)
        else:
            attachment = ctx_attachment.create(values)
        return Attachment.browse(attachment.id)
