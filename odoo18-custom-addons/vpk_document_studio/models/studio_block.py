# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

"""Standard layout blocks for Document Studio templates.

A template in "blocks" mode is assembled from ready-made blocks (memo header,
paragraph, signature, spacer). Each block renders flow-based HTML, so the PDF
always matches the editor and nothing has to be dragged or pinned by hand.
"""

import re
from html import escape

from lxml import html as lxml_html

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .studio_field import CODE_RE

BLOCK_TYPES = [
    ("memo_header", "หัวบันทึกข้อความ"),
    ("heading", "หัวข้อความทั่วไป"),
    ("paragraph", "ย่อหน้า / เนื้อความ"),
    ("table", "ตาราง"),
    ("signature", "ลงชื่อ"),
    ("spacer", "เว้นบรรทัด"),
]
ALIGNMENTS = [
    ("left", "ชิดซ้าย"),
    ("center", "กึ่งกลาง"),
    ("right", "ชิดขวา"),
    ("justify", "กระจายเต็มบรรทัด"),
]
SIGNATURE_ALIGNMENTS = [
    ("right", "ฝั่งขวา"),
    ("center", "กึ่งกลาง"),
    ("left", "ฝั่งซ้าย"),
]

# Approximate label widths (cm) at 16pt Thai Sarabun, bold.
_LABEL_CM = {
    "ส่วนราชการ": 2.5,
    "ที่": 0.8,
    "วันที่": 1.4,
    "เรื่อง": 1.2,
    "เรียน": 1.2,
}
_LINE_SAFETY_CM = 0.4
SIGNATURE_BOX_CM = 9.0
PARAGRAPH_INDENT_CM = 2.5
LINE_PLACEHOLDER = "&nbsp;"


def fill_line_html(cm, inner=LINE_PLACEHOLDER):
    """Dotted fill-line span compatible with the Word editor and the PDF path."""
    cm = max(1.0, round(float(cm), 1))
    return (
        '<span class="o_vpk_we_fill_line" data-line-cm="%(cm).1f" '
        'data-line-style="dotted" '
        'style="display: inline-block; box-sizing: border-box; '
        'min-width: %(cm).1fcm; width: %(cm).1fcm; '
        "border-bottom: 1px dotted #000000; padding: 0 4px; "
        "line-height: 1.05; text-align: left; vertical-align: baseline; "
        'white-space: normal;">%(inner)s</span>'
    ) % {"cm": cm, "inner": inner}


def _placeholder(code):
    code = (code or "").strip()
    return "{{%s}}" % code if code else LINE_PLACEHOLDER


def _label_html(text, scale=1.0):
    width = round(_LABEL_CM.get(text, 0.25 * len(text) + 0.4) * scale, 2)
    return (
        '<span style="display: inline-block; width: %.2fcm;">'
        "<b>%s</b></span>" % (width, escape(text))
    ), width


def _row(*chunks):
    return (
        '<p style="margin: 0 0 0.1cm 0; white-space: nowrap;">%s</p>'
        % "".join(chunks)
    )


def _style_paragraphs(content, align, indent_cm, bold):
    """Apply alignment/indent to the paragraphs the user typed."""
    content = (content or "").strip()
    if not content:
        return ""
    style = "margin: 0; text-align: %s;" % align
    if indent_cm:
        style += " text-indent: %.1fcm;" % indent_cm
    try:
        nodes = lxml_html.fragments_fromstring(content)
    except Exception:
        return '<p style="%s">%s</p>' % (style, escape(content))
    out = []
    for node in nodes:
        if isinstance(node, str):
            text = node.strip()
            if text:
                out.append('<p style="%s">%s</p>' % (style, escape(text)))
            continue
        if node.tag in ("p", "div", "h1", "h2", "h3", "h4"):
            old = node.get("style") or ""
            old = re.sub(r"(text-align|text-indent)\s*:\s*[^;]+;?", "", old).strip()
            node.set("style", (old + "; " + style).strip("; "))
            node.set("align", align)
        out.append(lxml_html.tostring(node, encoding="unicode", method="html"))
    html = "".join(out)
    if bold:
        html = "<b>%s</b>" % html
    return html


class DocumentStudioBlock(models.Model):
    _name = "vpk.document.studio.block"
    _description = "บล็อกเอกสาร Document Studio"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    block_type = fields.Selection(
        selection=BLOCK_TYPES,
        string="ชนิดบล็อก",
        required=True,
        default="paragraph",
    )
    summary = fields.Char(string="สรุป", compute="_compute_summary")

    # memo header
    title = fields.Char(string="หัวเรื่อง", default="บันทึกข้อความ")
    code_agency = fields.Char(string="รหัสฟิลด์ ส่วนราชการ", default="agency")
    code_number = fields.Char(string="รหัสฟิลด์ ที่", default="memo_number")
    code_date = fields.Char(string="รหัสฟิลด์ วันที่", default="memo_date")
    code_subject = fields.Char(string="รหัสฟิลด์ เรื่อง", default="subject")
    code_recipient = fields.Char(string="รหัสฟิลด์ เรียน", default="recipient")
    show_recipient = fields.Boolean(string="แสดงบรรทัด เรียน", default=True)

    # heading
    heading_text = fields.Char(
        string="ข้อความหัวข้อ",
        help="พิมพ์หัวข้อ เช่น ความเห็นของคณะกรรมการ ใส่ {{รหัสฟิลด์}} ได้",
    )
    heading_align = fields.Selection(
        selection=[("left", "ชิดซ้าย"), ("center", "กึ่งกลาง"), ("right", "ชิดขวา")],
        string="การจัดชิดหัวข้อ",
        default="left",
    )
    heading_bold = fields.Boolean(string="ตัวหนา (หัวข้อ)", default=True)
    heading_underline = fields.Boolean(string="ขีดเส้นใต้")
    heading_size = fields.Integer(
        string="ขนาดตัวอักษร (pt)",
        default=16,
        help="ขนาดตัวอักษรของหัวข้อ (ย่อ/ขยายตามขนาดตัวอักษรของหน้ากระดาษ)",
    )

    # paragraph
    content = fields.Html(
        string="เนื้อความ",
        sanitize=False,
        help="พิมพ์ข้อความ ใส่ {{รหัสฟิลด์}} ตรงจุดที่ต้องการให้ระบบแทนค่า",
    )
    insert_field_id = fields.Many2one(
        comodel_name="vpk.document.studio.field",
        string="แทรกฟิลด์",
        store=False,
        domain="[('template_id', '=', template_id)]",
        help="เลือกฟิลด์เพื่อต่อ {{รหัส}} ท้ายเนื้อความ",
    )
    align = fields.Selection(
        selection=ALIGNMENTS, string="การจัดชิด", default="justify"
    )
    first_line_indent = fields.Boolean(
        string="ย่อหน้าบรรทัดแรก 2.5 ซม.", default=True
    )
    bold = fields.Boolean(string="ตัวหนา")

    # signature
    sig_prefix = fields.Char(string="คำนำหน้า", default="ลงชื่อ")
    sig_role = fields.Char(string="บทบาท", help="เช่น ผู้เสนอ, ผู้พิจารณา, ผู้อนุมัติ")
    code_name = fields.Char(string="รหัสฟิลด์ ชื่อ", default="proposer_name")
    code_position = fields.Char(
        string="รหัสฟิลด์ ตำแหน่ง", default="proposer_position"
    )
    sig_align = fields.Selection(
        selection=SIGNATURE_ALIGNMENTS, string="ตำแหน่งลงชื่อ", default="right"
    )

    # table
    column_ids = fields.One2many(
        comodel_name="vpk.document.studio.block.column",
        inverse_name="block_id",
        string="คอลัมน์",
        copy=True,
    )
    table_header = fields.Boolean(string="แสดงหัวตาราง", default=True)
    table_borders = fields.Boolean(string="มีเส้นขอบตาราง", default=True)
    table_rows = fields.Integer(
        string="จำนวนแถว",
        default=1,
        help="จำนวนแถวคงที่ (ใช้เมื่อไม่ได้เลือกให้แตกแถวตามรายการ)",
    )
    table_footer_label = fields.Char(
        string="ข้อความแถวรวม",
        help="เช่น รวมเป็นเงินทั้งสิ้น (เว้นว่าง = ไม่มีแถวรวม)",
    )
    table_footer_value = fields.Char(
        string="ค่าแถวรวม",
        help="เช่น {{items_total}} (ผลรวมจำนวนเงินของรายการสินค้าใน PR)",
    )
    line_model = fields.Char(
        string="โมเดลของรายการย่อย",
        compute="_compute_line_model",
        help="โมเดลของแต่ละแถวในตาราง (ได้จากฟิลด์ที่ใช้แตกแถว)",
    )
    table_repeat_code = fields.Char(
        string="แตกแถวตามรายการของฟิลด์",
        help=(
            "ใส่รหัสฟิลด์ที่มีหลายบรรทัด เช่น items ระบบจะสร้างหนึ่งแถวต่อหนึ่งบรรทัด "
            "ในคอลัมน์ใช้ {{no}} {{no_th}} (ลำดับ), {{name}} (ชื่อ), {{qty}} (จำนวน), "
            "{{uom}} (หน่วย), {{unit_price}} (ราคาต่อหน่วย), {{amount}} (จำนวนเงิน), "
            "{{spec}} (รายละเอียด)"
        ),
    )

    # spacer
    lines = fields.Integer(string="จำนวนบรรทัด", default=1)

    @api.depends("table_repeat_code", "template_id.field_ids.map_field_id")
    def _compute_line_model(self):
        for rec in self:
            code = (rec.table_repeat_code or "").strip()
            field = rec.template_id.field_ids.filtered(lambda f: f.code == code)[:1]
            model = ""
            if field and field.map_field_id and field.map_field_id.ttype in (
                "one2many",
                "many2many",
            ):
                model = field.map_field_id.relation or ""
            elif field and (field.map_model_id.model == "purchase.request" or not field.map_model_id):
                model = "purchase.request.line"
            rec.line_model = model

    @api.depends(
        "block_type", "title", "heading_text", "content", "sig_role", "lines", "column_ids"
    )
    def _compute_summary(self):
        for rec in self:
            if rec.block_type == "memo_header":
                rec.summary = rec.title or _("หัวบันทึกข้อความ")
            elif rec.block_type == "heading":
                rec.summary = rec.heading_text or _("หัวข้อ")
            elif rec.block_type == "paragraph":
                text = re.sub(r"<[^>]+>", " ", rec.content or "")
                text = re.sub(r"\s+", " ", text).strip()
                rec.summary = text[:80] + ("…" if len(text) > 80 else "")
            elif rec.block_type == "table":
                rec.summary = _("ตาราง %s คอลัมน์") % len(rec.column_ids)
            elif rec.block_type == "signature":
                rec.summary = rec.sig_role or _("ลงชื่อ")
            else:
                rec.summary = _("%s บรรทัด") % (rec.lines or 1)

    @api.constrains(
        "code_agency",
        "code_number",
        "code_date",
        "code_subject",
        "code_recipient",
        "code_name",
        "code_position",
        "table_repeat_code",
    )
    def _check_codes(self):
        for rec in self:
            for name in (
                "code_agency",
                "code_number",
                "code_date",
                "code_subject",
                "code_recipient",
                "code_name",
                "code_position",
                "table_repeat_code",
            ):
                code = (rec[name] or "").strip()
                if code and not CODE_RE.match(code):
                    raise ValidationError(
                        _("รหัสฟิลด์ '%s' ต้องเป็นตัวพิมพ์เล็ก ตัวเลข หรือ _ และขึ้นต้นด้วยตัวอักษร")
                        % code
                    )

    @api.onchange("insert_field_id")
    def _onchange_insert_field_id(self):
        for rec in self:
            code = rec.insert_field_id.code
            if not code:
                continue
            token = "{{%s}}" % code
            content = (rec.content or "").strip()
            end = content.rfind("</p>")
            if end >= 0:
                content = content[:end] + " " + token + content[end:]
            else:
                content = "%s<p>%s</p>" % (content, token)
            rec.content = content
            rec.insert_field_id = False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_html(self, printable_cm, font_size=16.0):
        self.ensure_one()
        scale = (font_size or 16.0) / 16.0
        method = getattr(self, "_render_%s" % self.block_type, None)
        return method(printable_cm, scale) if method else ""

    def _render_memo_header(self, printable_cm, scale):
        avail = printable_cm - _LINE_SAFETY_CM
        parts = []
        title = escape(self.title or "")
        if title:
            parts.append(
                '<p style="margin: 0 0 0.2cm 0; text-align: center;">'
                '<b style="font-size: %.0fpt;">%s</b></p>' % (29 * scale, title)
            )

        label, label_w = _label_html("ส่วนราชการ", scale)
        parts.append(
            _row(
                label,
                fill_line_html(avail - label_w, _placeholder(self.code_agency)),
            )
        )

        label_t, w_t = _label_html("ที่", scale)
        label_d, w_d = _label_html("วันที่", scale)
        gap = 0.5
        room = avail - w_t - w_d - gap
        line_t = round(room * 0.5, 1)
        line_d = round(room - line_t, 1)
        parts.append(
            _row(
                label_t,
                fill_line_html(line_t, _placeholder(self.code_number)),
                '<span style="display: inline-block; width: %.1fcm;"></span>' % gap,
                label_d,
                fill_line_html(line_d, _placeholder(self.code_date)),
            )
        )

        label, label_w = _label_html("เรื่อง", scale)
        parts.append(
            _row(
                label,
                fill_line_html(avail - label_w, _placeholder(self.code_subject)),
            )
        )

        if self.show_recipient:
            label, label_w = _label_html("เรียน", scale)
            parts.append(
                _row(
                    label,
                    fill_line_html(
                        avail - label_w, _placeholder(self.code_recipient)
                    ),
                )
            )
        return "".join(parts)

    def _render_heading(self, printable_cm, scale):
        text = escape((self.heading_text or "").strip())
        if not text:
            return ""
        size = (self.heading_size or 16) * scale
        inner = '<span style="font-size: %.0fpt;">%s</span>' % (size, text)
        if self.heading_underline:
            inner = "<u>%s</u>" % inner
        if self.heading_bold:
            inner = "<b>%s</b>" % inner
        return (
            '<p style="margin: 0.2cm 0 0.1cm 0; text-align: %s;">%s</p>'
            % (self.heading_align or "left", inner)
        )

    def _render_paragraph(self, printable_cm, scale):
        return _style_paragraphs(
            self.content,
            self.align or "justify",
            PARAGRAPH_INDENT_CM if self.first_line_indent else 0,
            self.bold,
        )

    def _render_table(self, printable_cm, scale):
        columns = self.column_ids.sorted("sequence")
        if not columns:
            return ""
        fixed = sum(col.width_cm for col in columns if col.width_cm > 0)
        auto = [col for col in columns if col.width_cm <= 0]
        auto_w = max(1.5, (printable_cm - fixed) / len(auto)) if auto else 0.0
        border = "1px solid #000000" if self.table_borders else "none"

        def cell(tag, col, text, bold=False, align=None):
            width = col.width_cm if col.width_cm > 0 else auto_w
            pct = round(width / printable_cm * 100, 2)
            style = (
                "width: %.2f%%; border: %s; padding: 2px 6px; "
                "vertical-align: top; text-align: %s;" % (pct, border, align or col.align or "left")
            )
            inner = escape(text or "") or "&nbsp;"
            if bold:
                inner = "<b>%s</b>" % inner
            return '<%s width="%.2f%%" style="%s">%s</%s>' % (tag, pct, style, inner, tag)

        rows = []
        if self.table_header:
            rows.append(
                "<tr>%s</tr>"
                % "".join(
                    cell("td", col, col.header, bold=True, align="center")
                    for col in columns
                )
            )
        repeat = (self.table_repeat_code or "").strip()
        body_cells = "".join(cell("td", col, col.content) for col in columns)
        if repeat:
            rows.append('<tr data-vpk-repeat="%s">%s</tr>' % (escape(repeat), body_cells))
        else:
            rows.extend(["<tr>%s</tr>" % body_cells] * max(1, min(self.table_rows or 1, 50)))
        footer_label = (self.table_footer_label or "").strip()
        if footer_label and len(columns) >= 2:
            footer_style = (
                "border: %s; padding: 2px 6px; vertical-align: top; font-weight: bold;" % border
            )
            rows.append(
                '<tr><td colspan="%d" style="%s text-align: right;"><b>%s</b></td>'
                '<td style="%s text-align: right;"><b>%s</b></td></tr>'
                % (
                    len(columns) - 1,
                    footer_style,
                    escape(footer_label),
                    footer_style,
                    escape(self.table_footer_value or "") or "&nbsp;",
                )
            )
        return (
            '<table data-vpk-fixed-table="1" style="width: 100%%; table-layout: fixed; border-collapse: collapse; '
            'margin: 0.2cm 0;" border="%d">%s</table>'
            % (1 if self.table_borders else 0, "".join(rows))
        )

    def _render_signature(self, printable_cm, scale):
        box = min(SIGNATURE_BOX_CM, printable_cm)
        if self.sig_align == "left":
            margin = 0.0
        elif self.sig_align == "center":
            margin = max(0.0, (printable_cm - box) / 2)
        else:
            margin = max(0.0, printable_cm - box)
        prefix = escape(self.sig_prefix or "")
        role = escape(self.sig_role or "")
        prefix_w = len(prefix) * 0.25 + 0.4 if prefix else 0.0
        role_w = len(role) * 0.25 + 0.4 if role else 0.0
        line_w = max(2.0, box - prefix_w - role_w - 0.6)
        chunks = []
        if prefix:
            chunks.append(prefix + " ")
        chunks.append(fill_line_html(line_w))
        if role:
            chunks.append(" " + role)
        sign_line = _row(*chunks)
        name = _placeholder(self.code_name) if self.code_name else ""
        position = _placeholder(self.code_position) if self.code_position else ""
        lines = [sign_line]
        if name:
            lines.append('<p style="margin: 0;">( %s )</p>' % name)
        if position:
            lines.append('<p style="margin: 0;">%s</p>' % position)
        return (
            '<div style="margin: 0.6cm 0 0 %.1fcm; width: %.1fcm; '
            'text-align: center;">%s</div>' % (margin, box, "".join(lines))
        )

    def _render_spacer(self, printable_cm, scale):
        count = max(1, min(self.lines or 1, 20))
        return '<p style="margin: 0;">&nbsp;</p>' * count

    # ------------------------------------------------------------------
    # Keep the template layout in sync
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("template_id")._regenerate_layout_from_blocks_if_blocks()
        return records

    def write(self, vals):
        templates = self.mapped("template_id")
        result = super().write(vals)
        (templates | self.mapped("template_id"))._regenerate_layout_from_blocks_if_blocks()
        return result

    def unlink(self):
        templates = self.mapped("template_id")
        result = super().unlink()
        if not self.env.context.get("skip_layout_regen"):
            templates._regenerate_layout_from_blocks()
        return result


class DocumentStudioBlockColumn(models.Model):
    _name = "vpk.document.studio.block.column"
    _description = "คอลัมน์ตารางบล็อก Document Studio"
    _order = "sequence, id"

    block_id = fields.Many2one(
        comodel_name="vpk.document.studio.block",
        string="บล็อก",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    header = fields.Char(string="หัวคอลัมน์")
    width_cm = fields.Float(
        string="กว้าง (ซม.)",
        digits=(4, 1),
        help="0 = แบ่งพื้นที่ที่เหลือเท่าๆ กัน",
    )
    align = fields.Selection(
        selection=[("left", "ซ้าย"), ("center", "กลาง"), ("right", "ขวา")],
        string="การจัดชิด",
        default="left",
    )
    content = fields.Char(
        string="ข้อความในช่อง",
        help=(
            "ใส่ {{รหัสฟิลด์}} ได้ ในตารางแตกแถวใช้ {{no}} {{no_th}} {{name}} {{qty}} "
            "{{uom}} {{amount}} หรือ {{line.ชื่อฟิลด์}} ของรายการย่อย"
        ),
    )
    line_model = fields.Char(related="block_id.line_model")
    insert_line_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="แทรกฟิลด์รายการ",
        store=False,
        domain="[('model', '=', line_model), ('ttype', 'not in', ['binary', 'one2many', 'many2many'])]",
        help="เลือกฟิลด์ของรายการย่อย ระบบใส่ {{line.ชื่อฟิลด์}} ให้",
    )

    @api.onchange("insert_line_field_id")
    def _onchange_insert_line_field_id(self):
        for rec in self:
            if rec.insert_line_field_id:
                token = "{{line.%s}}" % rec.insert_line_field_id.name
                rec.content = ("%s %s" % (rec.content or "", token)).strip()
                rec.insert_line_field_id = False

    def _touch_templates(self):
        self.mapped("block_id.template_id")._regenerate_layout_from_blocks_if_blocks()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._touch_templates()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._touch_templates()
        return result

    def unlink(self):
        templates = self.mapped("block_id.template_id")
        result = super().unlink()
        templates._regenerate_layout_from_blocks_if_blocks()
        return result
