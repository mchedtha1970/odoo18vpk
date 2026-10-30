# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import io
import logging
import re
from collections import OrderedDict
from pathlib import Path

from odoo import api, models

_logger = logging.getLogger(__name__)

DOCX_PDF_REPORTS = {
    "vpk_purchase_agreement_egp.report_winner_announcement",
    "vpk_purchase_agreement_egp.report_award_approval",
}
CONTRACT_ESSENCE_REPORT = "vpk_purchase_agreement_egp.report_contract_essence"
_ESSENCE_FONT_CSS_CACHE = None


def _contract_essence_font_css():
    """Embed official TH Sarabun New so wkhtmltopdf does not fall back."""
    global _ESSENCE_FONT_CSS_CACHE
    if _ESSENCE_FONT_CSS_CACHE is not None:
        return _ESSENCE_FONT_CSS_CACHE
    font_dir = (
        Path(__file__).resolve().parents[2]
        / "l10n-thailand-18.0/l10n_th_base_utils/static/fonts/thai/THSarabunNew"
    )
    faces = []
    for family, filename in (
        ("THSarabunNew", "THSarabunNew-Regular.ttf"),
        ("THSarabunNew-Bold", "THSarabunNew-Bold.ttf"),
        ("TH Sarabun New", "THSarabunNew-Regular.ttf"),
    ):
        path = font_dir / filename
        if not path.exists():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode()
        faces.append(
            "@font-face {"
            f'font-family: "{family}";'
            f'src: url("data:font/truetype;base64,{encoded}") format("truetype");'
            "font-weight: normal;"
            "font-style: normal;"
            "}"
        )
    _ESSENCE_FONT_CSS_CACHE = "\n".join(faces)
    return _ESSENCE_FONT_CSS_CACHE


def _contract_essence_inline_css():
    layout = (
        Path(__file__).resolve().parent.parent
        / "static/src/scss/contract_essence_report.scss"
    )
    layout_css = layout.read_text(encoding="utf-8") if layout.exists() else ""
    return f"{_contract_essence_font_css()}\n{layout_css}"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report_sudo = self._get_report(report_ref)
        if report_sudo.report_name not in DOCX_PDF_REPORTS:
            return super()._render_qweb_pdf_prepare_streams(
                report_ref, data, res_ids=res_ids
            )

        try:
            from odoo.addons.vpk_document_studio.models.pdf_converter import (
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

    @api.model
    def _vpk_is_contract_essence_report(self, report_ref):
        if not report_ref:
            return False
        report = self._get_report(report_ref)
        return report.report_name == CONTRACT_ESSENCE_REPORT

    @api.model
    def _vpk_wrap_contract_essence_for_wkhtmltopdf(self, body, css):
        if not body:
            return body
        body = str(body)
        css = str(css or "")
        if "@font-face" in body and "THSarabunNew" in body:
            return body
        if "</head>" in body:
            return body.replace("</head>", f"<style>{css}</style></head>", 1)
        stripped = body.lstrip()
        if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
            return body
        body_without_style = re.sub(
            r"<style[^>]*>.*?</style>\s*",
            "",
            body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return (
            "<!DOCTYPE html><html><head>"
            '<meta charset="utf-8"/>'
            f"<style>{css}</style>"
            "</head><body>"
            f"{body_without_style}"
            "</body></html>"
        )

    @api.model
    def _run_wkhtmltopdf(
        self,
        bodies,
        report_ref=False,
        header=None,
        footer=None,
        landscape=False,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        if self._vpk_is_contract_essence_report(report_ref):
            css = _contract_essence_inline_css()
            bodies = [
                self._vpk_wrap_contract_essence_for_wkhtmltopdf(body, css)
                for body in bodies
            ]
        return super()._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header,
            footer=footer,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
