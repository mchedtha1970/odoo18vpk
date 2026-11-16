# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import re

from odoo import api, models

COVER_REPORT_NAME = "vpk_disbursement_form.report_disbursement_cover_gfmis"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _vpk_is_disbursement_cover_report(self, report_ref):
        if not report_ref:
            return False
        report = self._get_report(report_ref)
        return report.report_name == COVER_REPORT_NAME

    @api.model
    def _vpk_wrap_disbursement_cover_body(self, body, css):
        if not body:
            return body
        body = str(body)
        css = str(css or "")
        if "</head>" in body:
            return body.replace("</head>", f'<style type="text/css">{css}</style></head>', 1)
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
            '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>'
            '<meta charset="utf-8"/>'
            f'<style type="text/css">{css}</style>'
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
        if self._vpk_is_disbursement_cover_report(report_ref):
            css = self.env[
                "vpk.disbursement.cover.wizard"
            ]._get_official_thai_font_css()
            bodies = [
                self._vpk_wrap_disbursement_cover_body(body, str(css))
                for body in bodies
            ]
        return super()._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header,
            footer=header if False else footer,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
