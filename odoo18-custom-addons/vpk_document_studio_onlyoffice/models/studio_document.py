# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

from odoo import models

from odoo.addons.vpk_document_studio.models.pdf_converter import (
    PdfConversionError,
    convert_docx_bytes_to_pdf,
)

from ..utils.oo_pdf_convert import OnlyOfficeConvertError, convert_docx_bytes_to_pdf_onlyoffice

_logger = logging.getLogger(__name__)


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    def _render_pdf_bytes(self):
        """Prefer ONLYOFFICE ConvertService so print matches the Word template editor."""
        self.ensure_one()
        # Keep HTML-only documents on the existing LibreOffice HTML path.
        if not self._uses_word_template() and (self.body or "").strip():
            return super()._render_pdf_bytes()

        docx_content = self._render_docx_bytes()
        try:
            return convert_docx_bytes_to_pdf_onlyoffice(
                self.env,
                docx_content,
                filename="%s.docx" % self._safe_basename(),
            )
        except OnlyOfficeConvertError as error:
            _logger.warning(
                "ONLYOFFICE PDF failed for %s (%s), falling back to LibreOffice",
                self.display_name,
                error,
            )
        except Exception:
            _logger.warning(
                "ONLYOFFICE PDF failed for %s, falling back to LibreOffice",
                self.display_name,
                exc_info=True,
            )

        try:
            return convert_docx_bytes_to_pdf(
                docx_content,
                soffice_path=self._soffice_path(),
            )
        except PdfConversionError:
            raise
