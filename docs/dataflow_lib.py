#!/usr/bin/env python3
"""ไลบรารีกลางสำหรับสร้าง PPTX Workflow / Dataflow (ใช้ร่วมกันชุดงบประมาณ และชุดจัดซื้อจัดจ้าง)"""
from __future__ import annotations

import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from PIL import ImageFont


FONT = "Prompt"

NAVY = RGBColor(0x12, 0x3A, 0x56)
TEAL = RGBColor(0x0F, 0x7A, 0x72)
TEAL_SOFT = RGBColor(0xE5, 0xF5, 0xF3)
BLUE = RGBColor(0x2B, 0x5F, 0x9E)
BLUE_SOFT = RGBColor(0xE6, 0xEF, 0xFA)
AMBER = RGBColor(0xC4, 0x7E, 0x14)
AMBER_SOFT = RGBColor(0xFD, 0xF3, 0xE0)
RED = RGBColor(0xB4, 0x43, 0x3A)
RED_SOFT = RGBColor(0xFB, 0xEC, 0xEA)
GREEN = RGBColor(0x2C, 0x7A, 0x45)
GREEN_SOFT = RGBColor(0xE5, 0xF5, 0xEA)
SLATE = RGBColor(0x2F, 0x3A, 0x48)
MUTED = RGBColor(0x5B, 0x68, 0x78)
LINE = RGBColor(0xC5, 0xCE, 0xD8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG = RGBColor(0xF6, 0xF8, 0xFA)
LANE_A = RGBColor(0xF3, 0xF6, 0xF9)
LANE_B = RGBColor(0xFF, 0xFF, 0xFF)

SLIDE_W, SLIDE_H = 13.333, 7.5

# ตั้งค่าต่อไฟล์ (ชื่อระบบบนหัวกระดาษ / ที่มาท้ายกระดาษ)
CFG = {"system": "", "source": ""}


def configure(system, source):
    CFG["system"] = system
    CFG["source"] = source


# ------------------------------------------------------------------ helpers
def set_run(run, size, bold=False, color=SLATE, italic=False):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("latin", "ea", "cs"):
        el = rPr.find(qn(f"a:{tag}"))
        if el is None:
            el = etree.SubElement(rPr, qn(f"a:{tag}"))
        el.set("typeface", FONT)


def apply_theme_font(prs):
    try:
        master = prs.slide_masters[0]
        for rel in master.part.rels.values():
            if "theme" in (rel.reltype or ""):
                root = rel.target_part.element
                ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
                for font_el in root.xpath(".//a:majorFont | .//a:minorFont", namespaces=ns):
                    for tag in ("latin", "ea", "cs"):
                        node = font_el.find(f"a:{tag}", namespaces=ns)
                        if node is not None:
                            node.set("typeface", FONT)
                break
    except Exception:  # pragma: no cover
        pass


def fill_text(tf, paras, size, color=SLATE, bold=False, align=PP_ALIGN.LEFT, spacing=1.0):
    """paras: str | list[str | (str, dict)]"""
    if isinstance(paras, str):
        paras = [paras]
    tf.word_wrap = True
    first = True
    for item in paras:
        opts = {}
        if isinstance(item, tuple):
            item, opts = item
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = opts.get("align", align)
        p.line_spacing = spacing
        r = p.add_run()
        r.text = item
        set_run(r, opts.get("size", size), opts.get("bold", bold), opts.get("color", color),
                opts.get("italic", False))


def tb(slide, x, y, w, h, paras, size=11, color=SLATE, bold=False, align=PP_ALIGN.LEFT,
       anchor=MSO_ANCHOR.TOP, margin=0.04):
    s = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    fill_text(tf, paras, size, color, bold, align)
    return s


def box(slide, x, y, w, h, paras="", fill=WHITE, line=LINE, size=10, color=SLATE, bold=False,
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
        lw=1.0, radius=0.12, margin=0.06, dash=False):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            s.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
        if dash:
            ln = s.line._get_or_add_ln()
            pd = etree.SubElement(ln, qn("a:prstDash"))
            pd.set("val", "dash")
    s.shadow.inherit = False
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = anchor
    if paras:
        fill_text(tf, paras, size, color, bold, align)
    return s


def seg(slide, x1, y1, x2, y2, color=MUTED, w=1.5, arrow=True, both=False, dash=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(w)
    ln = c.line._get_or_add_ln()
    if dash:
        pd = etree.SubElement(ln, qn("a:prstDash"))
        pd.set("val", "dash")
    if both:
        he = etree.SubElement(ln, qn("a:headEnd"))
        he.set("type", "triangle")
        he.set("w", "med")
        he.set("len", "med")
    if arrow:
        te = etree.SubElement(ln, qn("a:tailEnd"))
        te.set("type", "triangle")
        te.set("w", "med")
        te.set("len", "med")
    return c


def route(slide, pts, color=MUTED, w=1.5, dash=False):
    """เส้นหักมุมจากหลายจุด หัวลูกศรที่จุดสุดท้าย"""
    for i in range(len(pts) - 1):
        last = i == len(pts) - 2
        seg(slide, *pts[i], *pts[i + 1], color=color, w=w, arrow=last, dash=dash)


def header(slide, title, subtitle=None, page=None, total=None):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(SLIDE_W), Inches(0.82))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()
    bar.shadow.inherit = False
    tb(slide, 0.4, 0.08, 10.5, 0.45, title, size=20, color=WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    if subtitle:
        tb(slide, 0.4, 0.48, 11.5, 0.3, subtitle, size=10.5, color=RGBColor(0xBF, 0xD6, 0xE6))
    tb(slide, 11.0, 0.2, 2.0, 0.4, CFG["system"], size=10, color=RGBColor(0xBF, 0xD6, 0xE6),
       align=PP_ALIGN.RIGHT)


def footer(slide, page, total):
    tb(slide, 0.4, 7.15, 8, 0.28, CFG["source"], size=8,
       color=MUTED)
    tb(slide, 11.9, 7.15, 1.0, 0.28, f"{page}/{total}", size=8, color=MUTED, align=PP_ALIGN.RIGHT)


def blank(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = WHITE
    return s


METHOD_TXT = {
    "both": ("ทั้งสองวิธี", MUTED),
    "specific": ("เฉพาะเจาะจง", GREEN),
    "ebidding": ("e-bidding", AMBER),
}


def slide_io(prs, funcs, phases, pcolor, phase_code, part, nparts, page, total):
    col, soft = pcolor[phase_code]
    pname, pdesc = next((n, d) for c, n, d in phases if c == phase_code)
    s = blank(prs)
    suffix = f" ({part}/{nparts})" if nparts > 1 else ""
    header(s, f"{phase_code}. {pname}{suffix}", pdesc)

    # คอลัมน์
    mx = 0.35
    in_w, fn_w, out_w, ar = 4.35, 3.45, 4.35, 0.4
    xi = mx
    xf = xi + in_w + ar
    xo = xf + fn_w + ar
    hy = 0.98
    for x, w, t, c, sf in [(xi, in_w, "INPUT  (ข้อมูลเข้า)", BLUE, BLUE_SOFT),
                           (xf, fn_w, "FUNCTION  (การประมวลผล)", col, soft),
                           (xo, out_w, "OUTPUT  (ผลลัพธ์)", GREEN, GREEN_SOFT)]:
        box(s, x, hy, w, 0.34, t, fill=c, line=c, size=10.5, color=WHITE, bold=True, radius=0.2)

    n = len(funcs)
    avail_top = 1.45
    avail_h = 7.05 - avail_top
    gap = 0.12
    rh = (avail_h - gap * (n - 1)) / n
    rh = min(rh, 1.85)
    k = 1.2 if n <= 2 else (1.1 if n == 3 else 1.0)
    for i, f in enumerate(funcs):
        y = avail_top + i * (rh + gap)
        # input
        box(s, xi, y, in_w, rh, [("• " + t, {"size": 9.5 * k}) for t in f["inputs"]], fill=BLUE_SOFT, line=BLUE,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, radius=0.08, margin=0.1)
        # function
        box(s, xf, y, fn_w, rh,
            [(f"{f['code']}  {f['name']}", {"bold": True, "size": 10.5 * k, "color": col}),
             (f"ผู้ใช้: {f['actor']}", {"size": 8.5 * k, "color": MUTED})]
            + ([(f"วิธีจัดซื้อ: {METHOD_TXT[f['method']][0]}",
                 {"bold": True, "size": 8.5 * k, "color": METHOD_TXT[f['method']][1]})] if f.get("method") else [])
            + [("› " + p, {"size": 8.5 * k}) for p in f["process"][:3]]
            + [(f["menu"], {"size": 7.5 * k, "italic": True, "color": MUTED})],
            fill=WHITE, line=col, lw=1.75, anchor=MSO_ANCHOR.MIDDLE, radius=0.08, margin=0.08)
        # output
        box(s, xo, y, out_w, rh, [("• " + t, {"size": 9.5 * k}) for t in f["outputs"]], fill=GREEN_SOFT, line=GREEN,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, radius=0.08, margin=0.1)
        seg(s, xi + in_w, y + rh / 2, xf, y + rh / 2, color=SLATE, w=2)
        seg(s, xf + fn_w, y + rh / 2, xo, y + rh / 2, color=SLATE, w=2)
    footer(s, page, total)


_FONTS = {}


def _text_w(t, size, bold=False):
    key = (round(size * 4), bold)
    if key not in _FONTS:
        f = Path(__file__).parent / "fonts" / "Prompt" / f"Prompt-{'Bold' if bold else 'Regular'}.ttf"
        _FONTS[key] = ImageFont.truetype(str(f), int(size * 10))
    return _FONTS[key].getlength(t) / 10 / 72


def _lines(t, size, w, bold=False):
    n, cur = 1, 0.0
    for ch in t:
        cw = _text_w(ch, size, bold)
        if cur + cw > w:
            n, cur = n + 1, cw
        else:
            cur += cw
    return n


def soft_for(code):
    return RGBColor(0xEE, 0xF1, 0xF4)


def rows_h(cells, sizes, widths):
    best = 0.0
    for cell, sz, w in zip(cells, sizes, widths):
        tot = 0.0
        for k, t in enumerate(cell):
            size = 8 if (len(cell) > 1 and k > 0 and sz == 9) else sz
            tot += _lines(t, size, w * 0.95) * size * 1.4 / 72
        best = max(best, tot)
    return max(0.55, best + 0.14)


def io_pages(funcs, phases, per_page=4):
    pages = []
    for code, _, _ in phases:
        fs = [f for f in funcs if f["phase"] == code]
        if not fs:
            continue
        npages = -(-len(fs) // per_page)
        base, extra = divmod(len(fs), npages)
        chunks, pos = [], 0
        for k in range(npages):
            size = base + (1 if k < extra else 0)
            chunks.append(fs[pos:pos + size])
            pos += size
        for i, ch in enumerate(chunks, 1):
            pages.append((code, ch, i, len(chunks)))
    return pages


def new_prs():
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    apply_theme_font(prs)
    return prs
