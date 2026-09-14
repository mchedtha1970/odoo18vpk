# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import io
from collections import OrderedDict

from odoo import models

WORD_TEMPLATE_PDF_REPORT = "vpk_official_document.report_wa_committee_order"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report_sudo = self._get_report(report_ref)
        if report_sudo.report_name != WORD_TEMPLATE_PDF_REPORT:
            return super()._render_qweb_pdf_prepare_streams(
                report_ref, data, res_ids=res_ids
            )

        collected_streams = OrderedDict()
        documents = self.env[report_sudo.model].browse(res_ids or [])
        for document in documents:
            collected_streams[document.id] = {
                "stream": io.BytesIO(document._render_pdf_from_docx()),
                "attachment": None,
            }
        return collected_streams
