# -*- coding: utf-8 -*-
import re

from odoo import api, models

PO_FORM_REPORT = "vpk_purchase_order_form.report_purchase_order_vpk_form"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def _vpk_is_po_form_report(self, report_ref):
        if not report_ref:
            return False
        report = self._get_report(report_ref)
        return report.report_name == PO_FORM_REPORT

    @api.model
    def _vpk_wrap_po_form_for_wkhtmltopdf(self, body, css):
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
        if self._vpk_is_po_form_report(report_ref):
            css = self.env["purchase.order"]._get_po_form_inline_css()
            bodies = [
                self._vpk_wrap_po_form_for_wkhtmltopdf(body, css) for body in bodies
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

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, report_type = super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )
        if (
            report_type == "pdf"
            and self._vpk_is_po_form_report(report_ref)
            and res_ids
            and len(set(res_ids)) == 1
        ):
            order = self.env["purchase.order"].browse(res_ids[0]).exists()
            if order:
                order._vpk_upsert_po_pdf(pdf_content)
        return pdf_content, report_type
