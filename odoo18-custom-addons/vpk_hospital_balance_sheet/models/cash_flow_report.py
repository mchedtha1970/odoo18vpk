# -*- coding: utf-8 -*-
from odoo import models


class HospitalCashFlowReportHandler(models.AbstractModel):
    _name = "vpk.hospital.cash.flow.report.handler"
    _inherit = "account.report.custom.handler"
    _description = "รายงานกระแสเงินสด โรงพยาบาลวชิระภูเก็ต"

    def _custom_options_initializer(self, report, options, previous_options):
        """Keep every journal. The standard cash-flow handler would hide purchase journals."""
        return
