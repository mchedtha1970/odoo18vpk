# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Fill a Word template by replacing {{placeholder}} tokens.

Merge is done surgically inside the .docx ZIP so OnlyOffice styles, theme
fonts, headers and numbering stay intact. A full python-docx round-trip
rewrites styles.xml and makes the printed PDF look different from the editor.
"""

import copy
import io
import logging
import re
import zipfile

from lxml import etree

try:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
except ImportError:  # pragma: no cover
    Document = None
    qn = None
    Paragraph = None

_logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
THAI_PDF_FONT = "TH Sarabun New"
PLACEHOLDER_RE = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}"
)
PLACEHOLDER_ONLY_RE = re.compile(
    r"^\s*\{\{\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\s*\}\}\s*$"
)
DOTTED_PLACEHOLDER_RE = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
)
_ROW_HINT_RE = re.compile(
    r"\{\{\s*(?:no|no_th|line|name|qty|uom|unit_price|amount|spec)\s*\}\}"
)


class DocxMergeError(ValueError):
    """Raised when a Word template cannot be filled."""


def _require_docx():
    if Document is None:
        raise DocxMergeError(
            "ไม่พบไลบรารี python-docx กรุณาติดตั้งในสภาพแวดล้อม Odoo ก่อนพิมพ์แบบฟอร์ม"
        )


def _paragraph_text(paragraph):
    return "".join(run.text or "" for run in paragraph.runs)


def _coalesce_split_placeholders(runs):
    """Join adjacent runs when {{placeholder}} was split (incl. `{` + `{code` + `}}`)."""
    i = 0
    while i < len(runs):
        txt = runs[i].text or ""
        needs_join = False
        if "{{" in txt and "}}" not in txt.split("{{")[-1]:
            needs_join = True
        elif txt.endswith("{") and i + 1 < len(runs):
            # Word/OnlyOffice often splits "{{code}}" into "{", "{code", "}}"
            needs_join = True
        elif "{" in txt and "}}" not in txt and i + 1 < len(runs):
            joined_preview = txt + "".join((runs[j].text or "") for j in range(i + 1, min(i + 6, len(runs))))
            if PLACEHOLDER_RE.search(joined_preview) and (
                "{{" not in txt or "}}" not in txt.split("{{")[-1]
            ):
                needs_join = True
        if needs_join:
            j = i + 1
            while j < len(runs):
                nxt = runs[j].text or ""
                txt += nxt
                runs[j].text = ""
                j += 1
                if PLACEHOLDER_RE.search(txt) and txt.count("{{") <= txt.count("}}"):
                    break
                if j - i > 12:
                    break
            runs[i].text = txt
        i += 1


def _replace_in_paragraph_runs(paragraph, mapping):
    """Replace {{code}} inside runs; coalesce split placeholders first."""
    runs = paragraph.runs
    if not runs:
        return
    full = "".join(run.text or "" for run in runs)
    if "{{" not in full and "{" not in full:
        return
    _coalesce_split_placeholders(runs)
    full = "".join(run.text or "" for run in runs)
    if "{{" not in full:
        return
    for code in PLACEHOLDER_RE.findall(full):
        mapping.setdefault(code, "")
    new_full = _replace_in_text(full, mapping)
    if new_full != full:
        # Reliable path when placeholders spanned many runs
        runs[0].text = new_full
        for run in runs[1:]:
            run.text = ""
        return
    for run in runs:
        r_pr = run._element.find(qn("w:rPr"))
        if r_pr is not None:
            bdr = r_pr.find(qn("w:bdr"))
            if bdr is not None:
                from docx.oxml import OxmlElement

                val = (bdr.get(qn("w:val")) or "dotted").lower()
                u_val = "dotted" if val in ("dotted", "dashed", "dotdash") else "single"
                r_pr.remove(bdr)
                u_el = r_pr.find(qn("w:u"))
                if u_el is None:
                    u_el = OxmlElement("w:u")
                    r_pr.append(u_el)
                u_el.set(qn("w:val"), u_val)
        rtxt = run.text or ""
        if "{{" in rtxt:
            trailing_nbsp = len(rtxt) - len(rtxt.rstrip("\u00a0"))
            core = rtxt[: len(rtxt) - trailing_nbsp] if trailing_nbsp else rtxt
            replaced_core = _replace_in_text(core, mapping)
            if trailing_nbsp:
                placeholder_budget = 10 * len(PLACEHOLDER_RE.findall(core))
                total_budget = trailing_nbsp + placeholder_budget
                new_pad = max(2, total_budget - len(replaced_core.strip()))
                run.text = replaced_core + ("\u00a0" * new_pad)
            else:
                run.text = replaced_core


def _remove_paragraph(paragraph):
    elm = paragraph._element
    parent = elm.getparent()
    if parent is not None:
        parent.remove(elm)


def _set_run_font(run, font_name=THAI_PDF_FONT):
    from docx.oxml import OxmlElement

    run.font.name = font_name
    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        r_fonts.set(qn(attr), font_name)
    # LibreOffice needs complex-script bold/size to embed TH Sarabun Bold.
    sz = r_pr.find(qn("w:sz"))
    if sz is not None and r_pr.find(qn("w:szCs")) is None:
        sz_cs = OxmlElement("w:szCs")
        sz_cs.set(qn("w:val"), sz.get(qn("w:val")))
        sz.addnext(sz_cs)
    if r_pr.find(qn("w:b")) is not None and r_pr.find(qn("w:bCs")) is None:
        r_pr.append(OxmlElement("w:bCs"))
    if r_pr.find(qn("w:i")) is not None and r_pr.find(qn("w:iCs")) is None:
        r_pr.append(OxmlElement("w:iCs"))


def _ensure_complex_script_fonts(document):
    """Mirror Latin ↔ complex-script props so Thai PDF matches the Word template."""
    from .word_layout import _mirror_complex_script_formatting

    parts = [document.element.body]
    for section in document.sections:
        for header_footer in (
            section.header,
            section.footer,
            section.first_page_header,
            section.first_page_footer,
        ):
            if header_footer is None:
                continue
            element = getattr(header_footer, "_element", None)
            if element is not None:
                parts.append(element)
    for part in parts:
        _mirror_complex_script_formatting(part, qn)


def _iter_container_paragraphs(container):
    for paragraph in container.paragraphs:
        yield paragraph
    for table in container.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph


def _iter_story_containers(document):
    yield document
    for section in document.sections:
        for part in (
            section.header,
            section.footer,
            section.first_page_header,
            section.first_page_footer,
        ):
            if part is not None:
                yield part


def _iter_paragraphs(document):
    seen = set()
    for container in _iter_story_containers(document):
        for paragraph in _iter_container_paragraphs(container):
            element = paragraph._element
            if element in seen:
                continue
            seen.add(element)
            yield paragraph


def _apply_thai_font(document, font_name=THAI_PDF_FONT):
    for paragraph in _iter_paragraphs(document):
        for run in paragraph.runs:
            _set_run_font(run, font_name)


def extract_placeholders(template_bytes):
    """Return unique placeholder codes found in the Word file, in order.

    `{{items.product_id}}` contributes the parent field `items`.
    """
    _require_docx()
    document = Document(io.BytesIO(template_bytes))
    found = []
    seen = set()
    for paragraph in _iter_paragraphs(document):
        for token in PLACEHOLDER_RE.findall(_paragraph_text(paragraph)):
            code = token.split(".")[0]
            if code not in seen:
                seen.add(code)
                found.append(code)
    return found


def extract_repeat_tokens(template_bytes):
    """Return {parent_code: [field, ...]} from {{items.product_id}} / {{line.qty}}."""
    _require_docx()
    document = Document(io.BytesIO(template_bytes))
    result = {}
    for paragraph in _iter_paragraphs(document):
        for parent, field in DOTTED_PLACEHOLDER_RE.findall(_paragraph_text(paragraph)):
            fields = result.setdefault(parent, [])
            if field not in fields:
                fields.append(field)
    return result


def _repeat_code_for_text(text, rows):
    if not text or "{{" not in text or not rows:
        return None
    for parent, _field in DOTTED_PLACEHOLDER_RE.findall(text):
        if parent in rows:
            return parent
        if parent == "line" and "items" in rows:
            return "items"
        if parent == "line" and len(rows) == 1:
            return next(iter(rows))
    if _ROW_HINT_RE.search(text):
        if "items" in rows:
            return "items"
        if len(rows) == 1:
            return next(iter(rows))
    return None


def _row_token_mapping(code, item):
    mapping = {}
    prefix = "%s." % code
    for key, value in (item or {}).items():
        if key == "amount_value":
            continue
        text = "" if value is None else str(value)
        mapping[str(key)] = text
        if key.startswith(prefix):
            field = key[len(prefix) :]
            mapping.setdefault(field, text)
            mapping.setdefault("line.%s" % field, text)
        elif "." not in str(key):
            mapping.setdefault("%s.%s" % (code, key), text)
            mapping.setdefault("line.%s" % key, text)
    return mapping


def _fill_element_placeholders(element, mapping):
    for p_el in element.iter(qn("w:p")):
        paragraph = Paragraph(p_el, None)
        if "{{" not in _paragraph_text(paragraph):
            continue
        _replace_in_paragraph_runs(paragraph, mapping)


def _expand_tbl(tbl, rows):
    for tr in list(tbl.findall(qn("w:tr"))):
        text = "".join(tr.itertext())
        code = _repeat_code_for_text(text, rows)
        if not code:
            continue
        items = list(rows.get(code) or []) or [{}]
        parent = tr.getparent()
        index = list(parent).index(tr)
        parent.remove(tr)
        for offset, item in enumerate(items):
            new_tr = copy.deepcopy(tr)
            _fill_element_placeholders(new_tr, _row_token_mapping(code, item))
            parent.insert(index + offset, new_tr)


def _expand_repeat_table_rows(document, rows):
    if not rows:
        return
    roots = [document.element.body]
    for section in document.sections:
        for part in (
            section.header,
            section.footer,
            section.first_page_header,
            section.first_page_footer,
        ):
            if part is not None:
                roots.append(part._element)
    seen = set()
    for root in roots:
        for tbl in root.iter(qn("w:tbl")):
            if tbl in seen:
                continue
            seen.add(tbl)
            _expand_tbl(tbl, rows)


def _replace_in_text(text, mapping):
    def replacer(match):
        code = match.group(1)
        if code not in mapping:
            return match.group(0)
        value = mapping[code]
        return "" if value is None else str(value)

    return PLACEHOLDER_RE.sub(replacer, text)


def _is_mergeable_xml_part(name):
    if not name.startswith("word/") or not name.endswith(".xml"):
        return False
    base = name.rsplit("/", 1)[-1]
    return (
        base == "document.xml"
        or base.startswith("header")
        or base.startswith("footer")
        or base.startswith("footnotes")
        or base.startswith("endnotes")
    )


def _paragraph_w_t_nodes(paragraph):
    nodes = []
    for node in paragraph.iter():
        if node.tag != W + "t":
            continue
        # Skip text inside nested paragraphs/hyperlinks? include all w:t under p
        nodes.append(node)
    return nodes


def _set_paragraph_text_preserve_runs(paragraph, new_text):
    """Put replaced text into the first w:t and clear the rest (keeps rPr)."""
    texts = _paragraph_w_t_nodes(paragraph)
    if not texts:
        # Create a minimal run/text if paragraph had only placeholders as drawings etc.
        run = etree.SubElement(paragraph, W + "r")
        node = etree.SubElement(run, W + "t")
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        node.text = new_text
        return
    first = texts[0]
    first.text = new_text
    first.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for node in texts[1:]:
        node.text = ""


def _fill_paragraph_xml(paragraph, mapping):
    texts = _paragraph_w_t_nodes(paragraph)
    if not texts:
        return
    full = "".join(node.text or "" for node in texts)
    if "{{" not in full and "{" not in full:
        return
    # Coalesce split placeholders already represented as adjacent w:t
    for code in PLACEHOLDER_RE.findall(full):
        mapping.setdefault(code, "")
    new = _replace_in_text(full, mapping)
    if new == full:
        return
    in_table = False
    parent = paragraph.getparent()
    while parent is not None:
        if parent.tag == W + "tc":
            in_table = True
            break
        parent = parent.getparent()
    if PLACEHOLDER_ONLY_RE.match(full) and not (new or "").strip():
        # Keep the paragraph for layout; use NBSP inside tables so cells stay visible.
        _set_paragraph_text_preserve_runs(paragraph, "\u00a0" if in_table else "")
        return
    _set_paragraph_text_preserve_runs(paragraph, new)


def _expand_tbl_xml(tbl, rows):
    for tr in list(tbl.findall(W + "tr")):
        text = "".join(tr.itertext())
        code = _repeat_code_for_text(text, rows)
        if not code:
            continue
        items = list(rows.get(code) or []) or [{}]
        parent = tr.getparent()
        index = list(parent).index(tr)
        parent.remove(tr)
        for offset, item in enumerate(items):
            new_tr = copy.deepcopy(tr)
            row_map = _row_token_mapping(code, item)
            for paragraph in new_tr.iter(W + "p"):
                _fill_paragraph_xml(paragraph, row_map)
            parent.insert(index + offset, new_tr)


def _merge_word_xml(xml_bytes, mapping, rows):
    root = etree.fromstring(xml_bytes)
    if rows:
        seen = set()
        for tbl in root.iter(W + "tbl"):
            if id(tbl) in seen:
                continue
            seen.add(id(tbl))
            _expand_tbl_xml(tbl, rows)
    for paragraph in list(root.iter(W + "p")):
        _fill_paragraph_xml(paragraph, mapping)
    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def merge_docx_bytes(template_bytes, mapping, known_codes=None, rows=None):
    """Replace {{code}} tokens and return filled .docx bytes.

    Preserves the original OnlyOffice/Word package (styles, theme, numbering).
    `rows` clones table rows that contain {{items.*}} / {{line.*}}.
    """
    if not template_bytes:
        raise DocxMergeError("ไม่มีไฟล์ Word สำหรับพิมพ์")
    mapping = {
        str(key): ("" if value is None else value)
        for key, value in (mapping or {}).items()
    }
    if known_codes:
        for code in known_codes:
            mapping.setdefault(code, "")
    rows = rows or {}

    try:
        source = zipfile.ZipFile(io.BytesIO(template_bytes))
    except zipfile.BadZipFile as error:
        raise DocxMergeError("ไฟล์ Word เสียหาย") from error

    output = io.BytesIO()
    with source, zipfile.ZipFile(output, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if _is_mergeable_xml_part(info.filename):
                try:
                    data = _merge_word_xml(data, mapping, rows)
                except Exception:
                    _logger.exception(
                        "ZIP merge failed for %s, leaving part unchanged", info.filename
                    )
            # Preserve compression method/time from the OnlyOffice package.
            target.writestr(info, data)
    return output.getvalue()

def build_placeholder_guide_docx(title, fields):
    """Build a starter Word file listing each {{code}} for the user to rearrange."""
    _require_docx()
    document = Document()
    heading = document.add_paragraph(title or "แบบฟอร์ม")
    heading.runs[0].bold = True
    document.add_paragraph(
        "คัดลอก {{รหัสฟิลด์}} ไปวางในแบบฟอร์มที่ต้องการ แล้วอัปโหลดไฟล์กลับมาที่ระบบ"
    )
    if not fields:
        document.add_paragraph("ยังไม่มีฟิลด์ในแบบฟอร์มนี้")
    for field in fields:
        code = field.get("code") or ""
        label = field.get("name") or code
        field_type = field.get("field_type") or "char"
        document.add_paragraph("%s (%s)" % (label, field_type))
        document.add_paragraph("{{%s}}" % code)
    _apply_thai_font(document)
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()
