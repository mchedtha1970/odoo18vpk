# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Stamp a handwritten signature onto a PDF above the approver name."""

import io
import logging

_logger = logging.getLogger(__name__)

SIGNATURE_MAX_WIDTH = 150.0
SIGNATURE_MIN_WIDTH = 96.0
SIGNATURE_MAX_HEIGHT = 56.0
SIGNATURE_GAP_ABOVE_NAME = 5.0
PAGE_MARGIN = 18.0


class SignatureStampError(ValueError):
    """Raised when the signature cannot be placed on the PDF."""


def _decode_image(signature_bytes):
    try:
        from PIL import Image
    except ImportError as error:
        raise SignatureStampError(
            "ไม่สามารถประมวลผลลายเซ็นได้ (ต้องติดตั้ง Pillow)"
        ) from error
    try:
        image = Image.open(io.BytesIO(signature_bytes))
        image.load()
    except Exception as error:
        raise SignatureStampError("ไฟล์ลายเซ็นไม่ถูกต้อง") from error
    image = image.convert("RGBA")
    bbox = image.getbbox()
    if not bbox:
        raise SignatureStampError("กรุณาลงลายเซ็น")
    return image.crop(bbox)


def _union_charboxes(textpage, start, count):
    xs = []
    ys = []
    for index in range(start, start + count):
        box = textpage.get_charbox(index)
        xs.extend((box[0], box[2]))
        ys.extend((box[1], box[3]))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def find_text_rect(pdf, search_texts):
    """Return ``(page_index, (x0, y0, x1, y1))`` for the last matching text."""
    last_hit = None
    needles = []
    for text in search_texts:
        cleaned = " ".join((text or "").split())
        if cleaned and cleaned not in needles:
            needles.append(cleaned)
    if not needles:
        return None
    for page_index, page in enumerate(pdf):
        textpage = page.get_textpage()
        try:
            for needle in needles:
                searcher = textpage.search(needle)
                while True:
                    hit = searcher.get_next()
                    if not hit:
                        break
                    start, count = hit
                    rect = _union_charboxes(textpage, start, count)
                    if rect:
                        last_hit = (page_index, rect)
        finally:
            textpage.close()
    return last_hit


def _signature_size(image, name_width):
    width = max(SIGNATURE_MIN_WIDTH, min(SIGNATURE_MAX_WIDTH, name_width * 1.25))
    ratio = image.width / float(max(image.height, 1))
    height = width / ratio
    if height > SIGNATURE_MAX_HEIGHT:
        height = SIGNATURE_MAX_HEIGHT
        width = height * ratio
    return width, height


def _place_above_name(page_size, name_rect, sig_width, sig_height):
    page_w, page_h = page_size
    name_x0, _name_y0, name_x1, name_y1 = name_rect
    x0 = ((name_x0 + name_x1) / 2.0) - (sig_width / 2.0)
    y0 = name_y1 + SIGNATURE_GAP_ABOVE_NAME
    x0 = max(PAGE_MARGIN, min(x0, page_w - sig_width - PAGE_MARGIN))
    y0 = max(PAGE_MARGIN, min(y0, page_h - sig_height - PAGE_MARGIN))
    return x0, y0


def stamp_signature_on_pdf(pdf_bytes, signature_bytes, search_texts):
    """Return PDF bytes with the signature image placed above the last name match."""
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise SignatureStampError(
            "ไม่สามารถประทับลายเซ็นบน PDF ได้ (ต้องติดตั้ง pypdfium2)"
        ) from error

    image = _decode_image(signature_bytes)
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        hit = find_text_rect(pdf, search_texts)
        if not hit:
            raise SignatureStampError(
                "ไม่พบชื่อผู้อนุมัติในเอกสาร กรุณาตรวจสอบชื่อผู้ลงนาม"
            )
        page_index, name_rect = hit
        page = pdf[page_index]
        sig_width, sig_height = _signature_size(
            image, max(name_rect[2] - name_rect[0], 1)
        )
        x0, y0 = _place_above_name(page.get_size(), name_rect, sig_width, sig_height)
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
        _logger.exception("Failed to stamp signature on official document PDF")
        raise SignatureStampError("ไม่สามารถประทับลายเซ็นบนเอกสารได้") from error
    finally:
        pdf.close()
