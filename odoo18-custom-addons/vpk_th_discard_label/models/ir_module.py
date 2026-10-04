# -*- coding: utf-8 -*-
from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _load_module_terms(self, modules, langs, overwrite=False, imported_module=False):
        res = super()._load_module_terms(
            modules, langs, overwrite=overwrite, imported_module=imported_module
        )
        if any(str(lang).startswith("th") for lang in (langs or ())):
            self.env["vpk.th.discard.label.updater"].update_labels()
        return res
