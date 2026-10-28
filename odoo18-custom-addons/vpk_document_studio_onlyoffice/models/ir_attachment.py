# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

from odoo import models

_logger = logging.getLogger(__name__)

OO_MARK = "vpk_onlyoffice_template"
OO_MIMETYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("skip_onlyoffice_sync"):
            return result
        if not ({"raw", "datas", "db_datas"} & set(vals)):
            return result
        for attachment in self.filtered(
            lambda rec: rec.description == OO_MARK
            and rec.res_model == "vpk.document.studio.template"
            and rec.res_id
        ):
            template = self.env["vpk.document.studio.template"].browse(attachment.res_id)
            if not template.exists():
                continue
            filename = attachment.name or template.filename or "%s.docx" % (template.code or "template")
            template.with_context(skip_onlyoffice_sync=True).write(
                {"datas": attachment.datas, "filename": filename}
            )
        return result
