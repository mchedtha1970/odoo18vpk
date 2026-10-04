# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import io
import logging
from collections import OrderedDict

from odoo import models

_logger = logging.getLogger(__name__)

DOCX_PDF_REPORTS = {
    "vpk_purchase_agreement_egp.report_winner_announcement",
    "vpk_purchase_agreement_egp.report_award_approval",
}


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report_sudo = self._get_report(report_ref)
        if report_sudo.report_name not in DOCX_PDF_REPORTS:
            return super()._render_qweb_pdf_prepare_streams(
                report_ref, data, res_ids=res_ids
            )

        try:
            from odoo.addons.vpk_official_document.models.pdf_converter import (
                find_soffice,
            )
        except ImportError:
            find_soffice = None

        if not find_soffice or not find_soffice():
            # No LibreOffice in this environment — use QWeb layout matched to the form.
            return super()._render_qweb_pdf_prepare_streams(
                report_ref, data, res_ids=res_ids
            )

        collected_streams = OrderedDict()
        announcements = self.env[report_sudo.model].browse(res_ids or [])
        for announcement in announcements:
            try:
                pdf_bytes = announcement._render_pdf_from_docx()
                if (
                    report_sudo.report_name
                    == "vpk_purchase_agreement_egp.report_award_approval"
                ):
                    announcement._file_award_egp_document(pdf_bytes)
            except Exception as error:  # noqa: BLE001 — fall back to QWeb
                if report_sudo.report_name == (
                    "vpk_purchase_agreement_egp.report_award_approval"
                ):
                    raise
                _logger.warning(
                    "Word template PDF failed for %s (%s): %s; using QWeb",
                    report_sudo.report_name,
                    announcement.id,
                    error,
                )
                return super()._render_qweb_pdf_prepare_streams(
                    report_ref, data, res_ids=res_ids
                )
            collected_streams[announcement.id] = {
                "stream": io.BytesIO(pdf_bytes),
                "attachment": None,
            }
        return collected_streams
