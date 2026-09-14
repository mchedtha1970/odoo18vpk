# -*- coding: utf-8 -*-
import re

from odoo import api, models

OFFICIAL_MEMO_REPORT = "vpk_tier_validation.report_purchase_request_official_memo"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _vpk_is_official_memo_report(self, report_ref):
        if not report_ref:
            return False
        report = self._get_report(report_ref)
        return report.report_name == OFFICIAL_MEMO_REPORT

    @api.model
    def _vpk_wrap_memo_body_for_wkhtmltopdf(self, body, css):
        """Wrap report fragment in a full HTML document with Thai fonts in head."""
        if not body:
            return body
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
        if self._vpk_is_official_memo_report(report_ref):
            css = self.env["purchase.request"]._get_official_memo_inline_css()
            bodies = [
                self._vpk_wrap_memo_body_for_wkhtmltopdf(body, css) for body in bodies
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
