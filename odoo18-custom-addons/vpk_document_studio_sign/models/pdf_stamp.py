# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Stamp a handwritten signature onto a PDF above the approver name."""

import io
import logging
import os

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


def _place_bottom_right(page_size, sig_width, sig_height, index=0):
    page_w, page_h = page_size
    x0 = max(PAGE_MARGIN, page_w - sig_width - PAGE_MARGIN * 3.0)
    y0 = max(PAGE_MARGIN, PAGE_MARGIN * 4.0 + (index * (sig_height + 10.0)))
    return x0, y0


def _place_in_custom_box(page_size, image, custom_box):
    page_w, page_h = page_size
    w_ratio = float(custom_box.get("w_ratio") or 0.24)
    h_ratio = float(custom_box.get("h_ratio") or 0.065)
    x_ratio = float(custom_box.get("x_ratio") or 0.5)
    y_ratio = float(custom_box.get("y_ratio") or 0.5)

    box_w = max(24.0, min(page_w, w_ratio * page_w))
    box_h = max(14.0, min(page_h, h_ratio * page_h))
    box_left = max(0.0, min(page_w - box_w, x_ratio * page_w))
    box_top = max(0.0, min(page_h - box_h, y_ratio * page_h))
    box_bottom = page_h - (box_top + box_h)

    img_ratio = image.width / float(max(image.height, 1))
    sig_width = box_w
    sig_height = sig_width / img_ratio
    if sig_height > box_h:
        sig_height = box_h
        sig_width = sig_height * img_ratio

    x0 = box_left + (box_w - sig_width) / 2.0
    y0 = box_bottom + (box_h - sig_height) / 2.0
    return sig_width, sig_height, x0, y0


def stamp_signature_on_pdf(
    pdf_bytes,
    signature_bytes,
    search_texts,
    fallback_bottom_right=False,
    custom_box=None,
):
    """Return PDF bytes with the signature image placed in custom_box or above the last name match."""
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise SignatureStampError(
            "ไม่สามารถประทับลายเซ็นบน PDF ได้ (ต้องติดตั้ง pypdfium2)"
        ) from error

    image = _decode_image(signature_bytes)
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        if custom_box and isinstance(custom_box, dict):
            raw_page_idx = int(custom_box.get("page_index", len(pdf) - 1))
            page_index = max(0, min(len(pdf) - 1, raw_page_idx))
            page = pdf[page_index]
            sig_width, sig_height, x0, y0 = _place_in_custom_box(
                page.get_size(), image, custom_box
            )
        else:
            hit = find_text_rect(pdf, search_texts)
            if not hit:
                if not fallback_bottom_right:
                    raise SignatureStampError(
                        "ไม่พบชื่อผู้อนุมัติในเอกสาร กรุณาตรวจสอบชื่อผู้ลงนาม หรือกดปุ่มกำหนดกรอบลายเซ็นบนหน้าเอกสาร"
                    )
                page_index = max(len(pdf) - 1, 0)
                page = pdf[page_index]
                sig_width, sig_height = _signature_size(image, 100.0)
                x0, y0 = _place_bottom_right(page.get_size(), sig_width, sig_height)
            else:
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
        _logger.exception("Failed to stamp signature on document PDF")
        raise SignatureStampError("ไม่สามารถประทับลายเซ็นบนเอกสารได้") from error
    finally:
        pdf.close()


def _thai_font_path(bold=True):
    from odoo.addons.vpk_document_studio.models.pdf_converter import thai_font_dirs

    filenames = (
        ("THSarabunNew-Bold.ttf", "THSarabunNew-Regular.ttf")
        if bold
        else ("THSarabunNew-Regular.ttf", "THSarabunNew-Bold.ttf")
    )
    for directory in thai_font_dirs():
        for filename in filenames:
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                return path
    raise SignatureStampError("ไม่พบฟอนต์ภาษาไทยสำหรับประทับเลขที่เอกสาร")


def _render_text_image(text, width_px, height_px):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise SignatureStampError(
            "ไม่สามารถประมวลผลข้อความได้ (ต้องติดตั้ง Pillow)"
        ) from error
    width_px = max(24, int(width_px))
    height_px = max(16, int(height_px))
    image = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font_path = _thai_font_path(bold=True)
    lo, hi = 10, max(height_px, 12)
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        font = ImageFont.truetype(font_path, mid)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= width_px * 0.96 and text_h <= height_px * 0.9:
            best = (font, bbox)
            lo = mid + 1
        else:
            hi = mid - 1
    if best:
        font, bbox = best
    else:
        font = ImageFont.truetype(font_path, 12)
        bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width_px - text_w) / 2.0 - bbox[0]
    y = (height_px - text_h) / 2.0 - bbox[1]
    draw.text((x, y), text, font=font, fill=(20, 20, 20, 255))
    return image


def stamp_text_on_pdf(pdf_bytes, text, custom_box):
    """Return PDF bytes with ``text`` drawn inside ``custom_box`` ratios."""
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise SignatureStampError(
            "ไม่สามารถประทับข้อความบน PDF ได้ (ต้องติดตั้ง pypdfium2)"
        ) from error

    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise SignatureStampError("กรุณาระบุข้อความที่ต้องการประทับบนเอกสาร")
    if not custom_box or not isinstance(custom_box, dict):
        raise SignatureStampError("กรุณากำหนดกรอบตำแหน่งบนหน้าเอกสาร")

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        raw_page_idx = int(custom_box.get("page_index", 0))
        page_index = max(0, min(len(pdf) - 1, raw_page_idx))
        page = pdf[page_index]
        page_w, page_h = page.get_size()
        w_ratio = float(custom_box.get("w_ratio") or 0.28)
        h_ratio = float(custom_box.get("h_ratio") or 0.045)
        x_ratio = float(custom_box.get("x_ratio") or 0.5)
        y_ratio = float(custom_box.get("y_ratio") or 0.08)
        box_w = max(36.0, min(page_w, w_ratio * page_w))
        box_h = max(14.0, min(page_h, h_ratio * page_h))
        box_left = max(0.0, min(page_w - box_w, x_ratio * page_w))
        box_top = max(0.0, min(page_h - box_h, y_ratio * page_h))
        box_bottom = page_h - (box_top + box_h)
        scale = 3.0
        image = _render_text_image(cleaned, box_w * scale, box_h * scale)
        bitmap = pdfium.PdfBitmap.from_pil(image)
        image_obj = pdfium.PdfImage.new(pdf)
        image_obj.set_bitmap(bitmap)
        matrix = pdfium.PdfMatrix().scale(box_w, box_h).translate(box_left, box_bottom)
        image_obj.set_matrix(matrix)
        page.insert_obj(image_obj)
        page.gen_content()
        output = io.BytesIO()
        pdf.save(output)
        return output.getvalue()
    except SignatureStampError:
        raise
    except Exception as error:
        _logger.exception("Failed to stamp document number on PDF")
        raise SignatureStampError("ไม่สามารถประทับข้อความบนไฟล์ได้") from error
    finally:
        pdf.close()
