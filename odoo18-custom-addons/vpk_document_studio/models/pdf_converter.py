# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Convert a filled Word form to PDF with Thai fonts embedded."""

import base64
import glob
import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path

_logger = logging.getLogger(__name__)

_SOFFICE_LOCK = threading.Lock()

SOFFICE_SEARCH_PATHS = (
    "/opt/odoo18vpk/tools/libreoffice/opt/libreoffice*/program/soffice",
    "/opt/libreoffice*/program/soffice",
    "/usr/lib/libreoffice/program/soffice",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
)


class PdfConversionError(ValueError):
    """Raised when the filled Word file cannot be converted to PDF."""


def _addon_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def thai_font_dirs():
    dirs = []
    try:
        from odoo.tools.misc import file_path

        regular = file_path(
            "l10n_th_base_utils/static/fonts/thai/THSarabunNew/THSarabunNew-Regular.ttf"
        )
        dirs.append(os.path.dirname(regular))
    except Exception:
        fallback = os.path.abspath(
            os.path.join(
                _addon_dir(),
                "..",
                "l10n-thailand-18.0",
                "l10n_th_base_utils",
                "static",
                "fonts",
                "thai",
                "THSarabunNew",
            )
        )
        if os.path.isdir(fallback):
            dirs.append(fallback)
    return [path for path in dirs if os.path.isdir(path)]


def _fontconfig_xml(font_dirs):
    dir_xml = "\n".join(f"  <dir>{path}</dir>" for path in font_dirs)
    return f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
{dir_xml}
  <alias>
    <family>TH SarabunIT๙</family>
    <prefer><family>TH Sarabun New</family></prefer>
    <default><family>TH Sarabun New</family></default>
  </alias>
  <alias>
    <family>TH SarabunIT9</family>
    <prefer><family>TH Sarabun New</family></prefer>
  </alias>
  <alias>
    <family>THSarabunIT๙</family>
    <prefer><family>TH Sarabun New</family></prefer>
  </alias>
  <alias>
    <family>THSarabunNew</family>
    <prefer><family>TH Sarabun New</family></prefer>
  </alias>
</fontconfig>
"""


def find_wkhtmltopdf(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(explicit_path)
    if os.environ.get("WKHTMLTOPDF_PATH"):
        candidates.append(os.environ["WKHTMLTOPDF_PATH"])
    which_bin = _which("wkhtmltopdf")
    if which_bin:
        candidates.append(which_bin)
    candidates.extend(
        (
            "/usr/local/bin/wkhtmltopdf",
            "/usr/bin/wkhtmltopdf",
        )
    )
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def find_soffice(explicit_path=None):
    candidates = []
    if explicit_path:
        candidates.append(explicit_path)
    for key in ("LIBREOFFICE_PATH", "SOFFICE_PATH"):
        if os.environ.get(key):
            candidates.append(os.environ[key])
    for pattern in SOFFICE_SEARCH_PATHS:
        candidates.extend(sorted(glob.glob(pattern)))
    which_soffice = _which("soffice") or _which("libreoffice")
    if which_soffice:
        candidates.append(which_soffice)
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _which(name):
    from shutil import which

    return which(name)


def _soffice_convert(source_bytes, source_ext, convert_to, output_ext,
                     infilter=None, soffice_path=None, label="PDF"):
    soffice = find_soffice(soffice_path)
    if not soffice:
        raise PdfConversionError(
            "ไม่พบ LibreOffice สำหรับแปลงไฟล์ "
            "กรุณาติดตั้ง LibreOffice บนเซิร์ฟเวอร์ หรือตั้งค่าพาธ soffice"
        )

    with tempfile.TemporaryDirectory(prefix="vpk-studio-") as tmp:
        source_path = os.path.join(tmp, "document.%s" % source_ext)
        output_dir = os.path.join(tmp, "out")
        profile_dir = os.path.join(tmp, "lo-profile")
        fonts_conf = os.path.join(tmp, "fonts.conf")
        os.makedirs(output_dir)
        os.makedirs(profile_dir)
        with open(source_path, "wb") as handle:
            handle.write(source_bytes)
        with open(fonts_conf, "w", encoding="utf-8") as handle:
            handle.write(_fontconfig_xml(thai_font_dirs()))

        env = os.environ.copy()
        env["HOME"] = tmp
        env["FONTCONFIG_FILE"] = fonts_conf
        env["SAL_USE_VCLPLUGIN"] = "svp"
        profile_uri = Path(profile_dir).resolve().as_uri()
        command = [
            soffice,
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--norestore",
            "-env:UserInstallation={}".format(profile_uri),
        ]
        if infilter:
            command.append("--infilter={}".format(infilter))
        command += ["--convert-to", convert_to, "--outdir", output_dir, source_path]
        _logger.info(
            "Converting studio %s to %s with %s", source_ext, output_ext, soffice
        )
        try:
            with _SOFFICE_LOCK:
                completed = subprocess.run(
                    command,
                    env=env,
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
        except subprocess.TimeoutExpired as error:
            raise PdfConversionError(
                "แปลงไฟล์เป็น %s ใช้เวลานานเกินไป กรุณาลองใหม่" % label
            ) from error
        except OSError as error:
            raise PdfConversionError(
                "ไม่สามารถเรียก LibreOffice เพื่อแปลงไฟล์เป็น %s ได้" % label
            ) from error

        output_path = os.path.join(output_dir, "document.%s" % output_ext)
        if completed.returncode != 0 or not os.path.isfile(output_path):
            detail = (completed.stderr or completed.stdout or b"").decode(
                "utf-8", errors="ignore"
            )
            _logger.error(
                "LibreOffice %s conversion failed (code=%s): %s",
                label,
                completed.returncode,
                detail,
            )
            raise PdfConversionError(
                "แปลงไฟล์เป็น %s ไม่สำเร็จ กรุณาตรวจสอบ LibreOffice บนเซิร์ฟเวอร์"
                % label
            )
        with open(output_path, "rb") as handle:
            return handle.read()


def convert_docx_bytes_to_pdf(docx_bytes, soffice_path=None):
    """Return PDF bytes converted from a .docx document via LibreOffice."""
    if not docx_bytes:
        raise PdfConversionError("ไม่มีไฟล์ Word สำหรับแปลงเป็น PDF")
    pdf_bytes = _soffice_convert(
        docx_bytes, "docx", "pdf:writer_pdf_Export", "pdf",
        soffice_path=soffice_path, label="PDF",
    )
    if not pdf_bytes.startswith(b"%PDF"):
        raise PdfConversionError("ไฟล์ที่แปลงได้ไม่ใช่ PDF ที่ถูกต้อง")
    return pdf_bytes


def convert_docx_bytes_to_html(docx_bytes, soffice_path=None):
    """Return HTML (UTF-8 text, images embedded) converted from a .docx."""
    if not docx_bytes:
        raise PdfConversionError("ไม่มีไฟล์ Word สำหรับเปิดเป็น layout")
    html_bytes = _soffice_convert(
        docx_bytes, "docx", "html:HTML (StarWriter):EmbedImages", "html",
        soffice_path=soffice_path, label="HTML",
    )
    return html_bytes.decode("utf-8", errors="ignore")


def convert_html_to_docx_bytes(html_text, soffice_path=None):
    """Return .docx bytes built from a full HTML document."""
    if not html_text:
        raise PdfConversionError("ยังไม่มี layout สำหรับสร้างไฟล์ Word")
    return _soffice_convert(
        html_text.encode("utf-8"), "html", "docx:MS Word 2007 XML", "docx",
        infilter="HTML (StarWriter)", soffice_path=soffice_path, label="Word",
    )


def _font_data_uri(path):
    with open(path, "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("ascii")
    return "data:font/ttf;base64,%s" % payload


def thai_font_face_css():
    """@font-face rules so HTML→PDF uses the same Thai fonts as the editor."""
    css = []
    for folder in thai_font_dirs():
        files = {
            "normal": os.path.join(folder, "THSarabunNew-Regular.ttf"),
            "bold": os.path.join(folder, "THSarabunNew-Bold.ttf"),
            "italic": os.path.join(folder, "THSarabunNew-Italic.ttf"),
        }
        uris = {}
        for weight, path in files.items():
            if os.path.isfile(path):
                uris[weight] = _font_data_uri(path)
        if not uris:
            continue
        for family in ("TH Sarabun New", "TH SarabunIT๙"):
            if uris.get("normal"):
                css.append(
                    '@font-face { font-family: "%s"; src: url("%s") format("truetype"); }'
                    % (family, uris["normal"])
                )
            if uris.get("bold"):
                css.append(
                    '@font-face { font-family: "%s"; font-weight: bold; src: url("%s") format("truetype"); }'
                    % (family, uris["bold"])
                )
            if uris.get("italic"):
                css.append(
                    '@font-face { font-family: "%s"; font-style: italic; src: url("%s") format("truetype"); }'
                    % (family, uris["italic"])
                )
        break
    return "\n".join(css)


def _wkhtmltopdf_convert(html_text):
    """Save-as-PDF of the editor HTML using the same engine as Odoo reports."""
    wkhtmltopdf = find_wkhtmltopdf()
    if not wkhtmltopdf:
        raise PdfConversionError("ไม่พบ wkhtmltopdf สำหรับพิมพ์ PDF ให้ตรงกับ Word editor")
    with tempfile.TemporaryDirectory(prefix="vpk-studio-pdf-") as tmp:
        html_path = os.path.join(tmp, "document.html")
        pdf_path = os.path.join(tmp, "document.pdf")
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(html_text)
        command = [
            wkhtmltopdf,
            "--quiet",
            "--page-size",
            "A4",
            "--margin-top",
            "0",
            "--margin-bottom",
            "0",
            "--margin-left",
            "0",
            "--margin-right",
            "0",
            "--disable-smart-shrinking",
            "--print-media-type",
            "--encoding",
            "utf-8",
            "--enable-local-file-access",
            "--no-outline",
            "--dpi",
            "96",
            html_path,
            pdf_path,
        ]
        _logger.info("Printing studio HTML to PDF with %s", wkhtmltopdf)
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired as error:
            raise PdfConversionError("หมดเวลาระหว่างพิมพ์ PDF จาก Word editor") from error
        if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) < 8:
            detail = (completed.stderr or completed.stdout or b"").decode("utf-8", "ignore")
            raise PdfConversionError(
                "ไม่สามารถพิมพ์ PDF จาก Word editor ได้%s"
                % ((":\n%s" % detail.strip()) if detail.strip() else "")
            )
        if completed.returncode not in (0, 1):
            detail = (completed.stderr or b"").decode("utf-8", "ignore")
            raise PdfConversionError(
                "wkhtmltopdf แปลง PDF ไม่สำเร็จ%s"
                % ((":\n%s" % detail.strip()) if detail.strip() else "")
            )
        with open(pdf_path, "rb") as handle:
            pdf_bytes = handle.read()
    if not pdf_bytes.startswith(b"%PDF"):
        raise PdfConversionError("ไฟล์ที่พิมพ์ได้ไม่ใช่ PDF ที่ถูกต้อง")
    return pdf_bytes


def convert_html_to_pdf_bytes(html_text, soffice_path=None):
    """Return PDF bytes that match the Word editor page (Save as PDF)."""
    if not html_text:
        raise PdfConversionError("ยังไม่มีเนื้อหาสำหรับแปลงเป็น PDF")
    try:
        return _wkhtmltopdf_convert(html_text)
    except PdfConversionError as error:
        _logger.warning("wkhtmltopdf save-as-PDF failed, falling back to LibreOffice: %s", error)
    pdf_bytes = _soffice_convert(
        html_text.encode("utf-8"),
        "html",
        "pdf:writer_pdf_Export",
        "pdf",
        infilter="HTML (StarWriter)",
        soffice_path=soffice_path,
        label="PDF",
    )
    if not pdf_bytes.startswith(b"%PDF"):
        raise PdfConversionError("ไฟล์ที่แปลงได้ไม่ใช่ PDF ที่ถูกต้อง")
    return pdf_bytes
