# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Place a vendor signature on a saved purchase-order PDF."""

import io
import logging

_logger = logging.getLogger(__name__)


def stamp_signature_bottom_left(pdf_bytes, signature_bytes):
    """Stamp when the form has no 'ลงนามผู้รับจ้าง' anchor yet."""
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        from odoo.addons.vpk_official_document.models.pdf_stamp import (
            SignatureStampError,
        )

        raise SignatureStampError(
            "ไม่สามารถประทับลายเซ็นบน PDF ได้ (ต้องติดตั้ง pypdfium2)"
        ) from error

    from odoo.addons.vpk_official_document.models.pdf_stamp import (
        SignatureStampError,
        _decode_image,
    )

    image = _decode_image(signature_bytes)
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        page_count = len(pdf)
        if page_count < 1:
            raise SignatureStampError("ไฟล์ PDF ว่าง")
        # Negative indexes are not accepted by this pdfium build.
        page = pdf[page_count - 1]
        sig_width = 140.0
        ratio = image.width / float(max(image.height, 1))
        sig_height = sig_width / ratio
        if sig_height > 56.0:
            sig_height = 56.0
            sig_width = sig_height * ratio
        x0, y0 = 48.0, 78.0
        bitmap = pdfium.PdfBitmap.from_pil(image)
        image_obj = pdfium.PdfImage.new(pdf)
        image_obj.set_bitmap(bitmap)
        matrix = pdfium.PdfMatrix().scale(sig_width, sig_height).translate(x0, y0)
        image_obj.set_matrix(matrix)
        page.insert_obj(image_obj)
        page.gen_content()
        output = io.BytesIO()
        pdf.save(output)
        return output.getvalue()
    except SignatureStampError:
        raise
    except Exception as error:
        _logger.exception("Failed to stamp vendor signature on PO PDF")
        raise SignatureStampError("ไม่สามารถประทับลายเซ็นบนใบสั่งซื้อได้") from error
    finally:
        pdf.close()
