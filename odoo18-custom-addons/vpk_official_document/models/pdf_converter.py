# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Convert a filled official Word form to PDF with Thai fonts embedded."""

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


def convert_docx_bytes_to_pdf(docx_bytes, soffice_path=None):
    """Return PDF bytes converted from a .docx document via LibreOffice."""
    if not docx_bytes:
        raise PdfConversionError("ไม่มีไฟล์ Word สำหรับแปลงเป็น PDF")
    soffice = find_soffice(soffice_path)
    if not soffice:
        raise PdfConversionError(
            "ไม่พบ LibreOffice สำหรับแปลง Word เป็น PDF "
            "กรุณาติดตั้ง LibreOffice บนเซิร์ฟเวอร์ หรือตั้งค่าพาธ soffice"
        )

    with tempfile.TemporaryDirectory(prefix="vpk-odoc-") as tmp:
        source_path = os.path.join(tmp, "document.docx")
        output_dir = os.path.join(tmp, "out")
        profile_dir = os.path.join(tmp, "lo-profile")
        fonts_conf = os.path.join(tmp, "fonts.conf")
        os.makedirs(output_dir)
        os.makedirs(profile_dir)
        with open(source_path, "wb") as handle:
            handle.write(docx_bytes)
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
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            output_dir,
            source_path,
        ]
        _logger.info("Converting official document DOCX to PDF with %s", soffice)
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
                "แปลง Word เป็น PDF ใช้เวลานานเกินไป กรุณาลองใหม่"
            ) from error
        except OSError as error:
            raise PdfConversionError(
                "ไม่สามารถเรียก LibreOffice เพื่อแปลง Word เป็น PDF ได้"
            ) from error

        pdf_path = os.path.join(output_dir, "document.pdf")
        if completed.returncode != 0 or not os.path.isfile(pdf_path):
            detail = (completed.stderr or completed.stdout or b"").decode(
                "utf-8", errors="ignore"
            )
            _logger.error(
                "LibreOffice PDF conversion failed (code=%s): %s",
                completed.returncode,
                detail,
            )
            raise PdfConversionError(
                "แปลงแบบฟอร์ม Word เป็น PDF ไม่สำเร็จ กรุณาตรวจสอบ LibreOffice บนเซิร์ฟเวอร์"
            )
        with open(pdf_path, "rb") as handle:
            pdf_bytes = handle.read()
    if not pdf_bytes.startswith(b"%PDF"):
        raise PdfConversionError("ไฟล์ที่แปลงได้ไม่ใช่ PDF ที่ถูกต้อง")
    return pdf_bytes
