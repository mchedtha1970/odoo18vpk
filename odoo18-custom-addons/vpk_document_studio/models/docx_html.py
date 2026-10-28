# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Pure-Python .docx → HTML used when LibreOffice is not available."""

import base64
import io
from html import escape

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
EMU_PER_PX = 9525
TWIP_PER_CM = 567.0

ALIGN = {"center": "center", "right": "right", "end": "right", "both": "justify",
         "distribute": "justify", "left": "left", "start": "left"}


def _w(tag):
    return "{%s}%s" % (W_NS, tag)


def _attr(el, name):
    return None if el is None else el.get(_w(name))


def _twip_cm(value):
    try:
        return round(int(value) / TWIP_PER_CM, 2)
    except (TypeError, ValueError):
        return None


def _run_style(rpr):
    if rpr is None:
        return ""
    style = []
    if rpr.find(_w("b")) is not None and _attr(rpr.find(_w("b")), "val") not in ("0", "false"):
        style.append("font-weight:bold")
    if rpr.find(_w("i")) is not None and _attr(rpr.find(_w("i")), "val") not in ("0", "false"):
        style.append("font-style:italic")
    underline = rpr.find(_w("u"))
    if underline is not None and _attr(underline, "val") not in (None, "none"):
        style.append("text-decoration:underline")
    size = rpr.find(_w("szCs")) if rpr.find(_w("szCs")) is not None else rpr.find(_w("sz"))
    if size is not None and _attr(size, "val"):
        try:
            style.append("font-size:%spt" % (int(_attr(size, "val")) / 2))
        except ValueError:
            pass
    fonts = rpr.find(_w("rFonts"))
    family = _attr(fonts, "cs") or _attr(fonts, "ascii")
    if family:
        style.append("font-family:'%s'" % escape(family, quote=False))
    color = rpr.find(_w("color"))
    if color is not None and _attr(color, "val") not in (None, "auto", "000000"):
        style.append("color:#%s" % _attr(color, "val"))
    return ";".join(style)


class _Converter:
    def __init__(self, document):
        self.document = document
        self.part = document.part

    def image(self, drawing):
        blip = drawing.find(".//{%s}blip" % A_NS)
        if blip is None:
            return ""
        rid = blip.get("{%s}embed" % R_NS)
        try:
            image_part = self.part.related_parts[rid]
        except KeyError:
            return ""
        payload = base64.b64encode(image_part.blob).decode("ascii")
        extent = drawing.find(".//{%s}extent" % WP_NS)
        size = ""
        if extent is not None:
            try:
                width = int(extent.get("cx")) // EMU_PER_PX
                height = int(extent.get("cy")) // EMU_PER_PX
                size = ' width="%s" height="%s"' % (width, height)
            except (TypeError, ValueError):
                pass
        return '<img src="data:%s;base64,%s"%s/>' % (image_part.content_type, payload, size)

    def run(self, run_el):
        parts = []
        for child in run_el:
            tag = child.tag
            if tag == _w("t"):
                parts.append(escape(child.text or ""))
            elif tag == _w("tab"):
                parts.append("&nbsp;" * 8)
            elif tag in (_w("br"), _w("cr")):
                parts.append("<br/>")
            elif tag == _w("drawing"):
                parts.append(self.image(child))
        text = "".join(parts)
        style = _run_style(run_el.find(_w("rPr")))
        if text and style:
            return '<span style="%s">%s</span>' % (style, text)
        return text

    def inline(self, el):
        parts = []
        for child in el:
            if child.tag == _w("r"):
                parts.append(self.run(child))
            elif child.tag in (_w("hyperlink"), _w("ins"), _w("smartTag"), _w("sdt"), _w("sdtContent")):
                parts.append(self.inline(child))
        return "".join(parts)

    def paragraph(self, p_el):
        ppr = p_el.find(_w("pPr"))
        style = ["margin:0"]
        if ppr is not None:
            jc = ppr.find(_w("jc"))
            if jc is not None and ALIGN.get(_attr(jc, "val")):
                style.append("text-align:%s" % ALIGN[_attr(jc, "val")])
            ind = ppr.find(_w("ind"))
            if ind is not None:
                left = _twip_cm(_attr(ind, "left") or _attr(ind, "start"))
                first = _twip_cm(_attr(ind, "firstLine"))
                hanging = _twip_cm(_attr(ind, "hanging"))
                if left:
                    style.append("margin-left:%scm" % left)
                if first:
                    style.append("text-indent:%scm" % first)
                elif hanging:
                    style.append("text-indent:-%scm" % hanging)
            spacing = ppr.find(_w("spacing"))
            if spacing is not None:
                before = _attr(spacing, "before")
                after = _attr(spacing, "after")
                if before and before != "0":
                    style.append("margin-top:%spt" % (int(before) / 20))
                if after and after != "0":
                    style.append("margin-bottom:%spt" % (int(after) / 20))
        content = self.inline(p_el) or "<br/>"
        return '<p style="%s">%s</p>' % (";".join(style), content)

    def table(self, tbl_el):
        tblpr = tbl_el.find(_w("tblPr"))
        bordered = False
        if tblpr is not None:
            borders = tblpr.find(_w("tblBorders"))
            if borders is not None:
                bordered = any(_attr(b, "val") not in (None, "nil", "none") for b in borders)
            style_el = tblpr.find(_w("tblStyle"))
            if not bordered and style_el is not None and "Grid" in (_attr(style_el, "val") or ""):
                bordered = True
        border = "border:1px solid #000;" if bordered else ""
        rows = [tr for tr in tbl_el if tr.tag == _w("tr")]
        grid = []
        for tr in rows:
            cells = []
            col = 0
            for tc in (c for c in tr if c.tag == _w("tc")):
                tcpr = tc.find(_w("tcPr"))
                span = int(_attr(tcpr.find(_w("gridSpan")), "val") or 1) if tcpr is not None and tcpr.find(_w("gridSpan")) is not None else 1
                vmerge = tcpr.find(_w("vMerge")) if tcpr is not None else None
                merge = None
                if vmerge is not None:
                    merge = "restart" if _attr(vmerge, "val") == "restart" else "continue"
                width = None
                if tcpr is not None and tcpr.find(_w("tcW")) is not None:
                    tcw = tcpr.find(_w("tcW"))
                    if _attr(tcw, "type") == "dxa":
                        width = _twip_cm(_attr(tcw, "w"))
                cells.append({"el": tc, "col": col, "span": span, "merge": merge,
                              "width": width, "rowspan": 1})
                col += span
            grid.append(cells)
        for row_index, cells in enumerate(grid):
            for cell in cells:
                if cell["merge"] != "restart":
                    continue
                for below in grid[row_index + 1:]:
                    match = next((c for c in below if c["col"] == cell["col"]), None)
                    if not match or match["merge"] != "continue":
                        break
                    cell["rowspan"] += 1
        html_rows = []
        for cells in grid:
            html_cells = []
            for cell in cells:
                if cell["merge"] == "continue":
                    continue
                attrs = ""
                if cell["span"] > 1:
                    attrs += ' colspan="%s"' % cell["span"]
                if cell["rowspan"] > 1:
                    attrs += ' rowspan="%s"' % cell["rowspan"]
                style = border + "padding:2px 4px;vertical-align:top;"
                if cell["width"]:
                    style += "width:%scm;" % cell["width"]
                html_cells.append('<td%s style="%s">%s</td>' % (attrs, style, self.blocks(cell["el"])))
            html_rows.append("<tr>%s</tr>" % "".join(html_cells))
        return (
            '<table style="border-collapse:collapse;width:100%%;%s">%s</table>'
            % (border, "".join(html_rows))
        )

    def blocks(self, container):
        parts = []
        for child in container:
            if child.tag == _w("p"):
                parts.append(self.paragraph(child))
            elif child.tag == _w("tbl"):
                parts.append(self.table(child))
            elif child.tag in (_w("sdt"), _w("sdtContent")):
                parts.append(self.blocks(child))
        return "".join(parts)


def docx_bytes_to_html(docx_bytes):
    """Return a full HTML document in the same shape as LibreOffice's export."""
    import docx

    document = docx.Document(io.BytesIO(docx_bytes))
    body = _Converter(document).blocks(document.element.body)
    page_css = ""
    if document.sections:
        section = document.sections[0]
        margins = []
        for side in ("top", "bottom", "left", "right"):
            value = getattr(section, "%s_margin" % side)
            if value is not None:
                margins.append("margin-%s: %.2fcm" % (side, value.cm))
        page_css = "@page { %s }" % "; ".join(margins)
    font_css = ""
    normal_rpr = None
    try:
        normal_rpr = document.styles["Normal"].element.find(_w("rPr"))
    except KeyError:
        pass
    defaults = document.styles.element.find(".//%s/%s" % (_w("rPrDefault"), _w("rPr")))
    family = size = None
    for rpr in (normal_rpr, defaults):
        if rpr is None:
            continue
        fonts = rpr.find(_w("rFonts"))
        family = family or _attr(fonts, "cs") or _attr(fonts, "ascii")
        size_el = rpr.find(_w("szCs")) if rpr.find(_w("szCs")) is not None else rpr.find(_w("sz"))
        if not size and size_el is not None and _attr(size_el, "val"):
            size = int(_attr(size_el, "val")) / 2
    rules = []
    if family:
        rules.append('font-family: "%s"' % family)
    if size:
        rules.append("font-size: %spt" % size)
    if rules:
        font_css = "p { %s }" % "; ".join(rules)
    return (
        "<html><head><meta charset=\"utf-8\"/><style>%s %s</style></head>"
        "<body>%s</body></html>" % (page_css, font_css, body)
    )
