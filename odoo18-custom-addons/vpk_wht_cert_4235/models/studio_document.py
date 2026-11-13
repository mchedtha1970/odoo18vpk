# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import api, fields, models

try:
    from odoo.addons.vpk_document_studio_procurement.models.studio_document import (
        LINK_FIELDS,
    )
except ImportError:  # pragma: no cover
    LINK_FIELDS = {}

LINK_FIELDS["vpk.wht.cert.4235"] = "wht_cert_4235_id"


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    wht_cert_4235_id = fields.Many2one(
        comodel_name="vpk.wht.cert.4235",
        string="ใบรับรองหักภาษี (4235)",
        index=True,
        ondelete="set null",
        copy=False,
    )

    @api.model
    def _extra_source_models(self):
        return super()._extra_source_models() + ["vpk.wht.cert.4235"]

    def _vpk_fill_links_from_sources(self):
        res = super()._vpk_fill_links_from_sources()
        for rec in self:
            if rec.wht_cert_4235_id or not rec.source_ref:
                continue
            source = rec._record_from_ref(rec.source_ref)
            if source and source._name == "vpk.wht.cert.4235":
                rec.sudo().write({"wht_cert_4235_id": source.id})
        return res
