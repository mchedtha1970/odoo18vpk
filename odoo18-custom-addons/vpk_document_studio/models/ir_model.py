# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, models


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.depends_context("vpk_show_model_name")
    def _compute_display_name(self):
        """Show the technical table name too, so duplicate Thai labels are distinguishable."""
        super()._compute_display_name()
        if self.env.context.get("vpk_show_model_name"):
            for rec in self:
                rec.display_name = "%s (%s)" % (rec.name, rec.model)
