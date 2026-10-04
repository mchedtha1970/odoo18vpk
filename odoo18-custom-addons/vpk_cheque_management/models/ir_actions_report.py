# -*- coding: utf-8 -*-

from odoo import models

CHEQUE_REPORTS = {
    "vpk_cheque_management.report_cheque_preview",
    "vpk_cheque_management.report_cheque_print",
}


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _prepare_html(self, html, report_model=False):
        bodies, res_ids, header, footer, specific_paperformat_args = super()._prepare_html(
            html, report_model=report_model
        )
        if self.report_name in CHEQUE_REPORTS:
            bodies = [
                body.replace('class="article"', 'class="" style="margin:0;padding:0"')
                for body in bodies
            ]
        return bodies, res_ids, header, footer, specific_paperformat_args
