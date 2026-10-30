from odoo import api, models


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    @api.model
    def _extra_source_models(self):
        return super()._extra_source_models() + ["ebidding.plan.document"]
