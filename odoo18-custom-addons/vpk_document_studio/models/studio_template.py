# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import re
from html import escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .docx_merge import (
    DocxMergeError,
    build_placeholder_guide_docx,
    extract_placeholders,
)
from .pdf_converter import (
    PdfConversionError,
    convert_docx_bytes_to_html,
    convert_docx_bytes_to_pdf,
    convert_html_to_docx_bytes,
)
from .studio_field import CODE_RE, PLACEHOLDER_RE
from .word_layout import (
    ROW_TOKENS,
    apply_page_setup,
    build_layout_document,
    parse_layout_html,
)

LAYOUT_FONTS = [
    ("TH SarabunIT๙", "TH SarabunIT๙"),
    ("TH Sarabun New", "TH Sarabun New"),
]

PLACEHOLDER_LABELS = {
    "agency": "ส่วนราชการ",
    "subject": "เรื่อง",
    "recipient": "เรียน",
    "intro": "ย่อหน้าแรก",
    "body_2": "เนื้อหาเพิ่มเติม",
    "item_1": "รายการ 1",
    "item_2": "รายการ 2",
    "item_3": "รายการ 3",
    "item_4": "รายการ 4",
    "item_5": "รายการ 5",
    "memo_number": "ที่",
    "memo_date": "วันที่บันทึก",
    "proposer_name": "ชื่อผู้เสนอ",
    "proposer_position": "ตำแหน่งผู้เสนอ",
    "reviewer_name": "ชื่อผู้พิจารณา",
    "reviewer_position": "ตำแหน่งผู้พิจารณา",
    "reviewer_date": "วันที่พิจารณา",
    "approver_name": "ชื่อผู้อนุมัติ",
    "approver_position": "ตำแหน่งผู้อนุมัติ",
    "approver_date": "วันที่อนุมัติ",
    "doc_date": "วันที่",
    "detail": "รายละเอียด",
    "items": "รายการสินค้า (จากใบขอซื้อ PR)",
    "pr_lines": "รายการสินค้า (จากใบขอซื้อ PR)",
    "product_lines": "รายการสินค้า (จากใบขอซื้อ PR)",
}


_DERIVED_CODE_RE = re.compile(r".+_(count|count_th|total)$")
_RESERVED_CODES = {"self"}


class DocumentStudioTemplate(models.Model):
    _name = "vpk.document.studio.template"
    _description = "แบบฟอร์ม Document Studio"
    _order = "name, id"

    name = fields.Char(string="ชื่อแบบฟอร์ม", required=True)
    code = fields.Char(string="รหัส", required=True, index=True, copy=False)
    note = fields.Text(
        string="คำอธิบาย",
        default=(
            "กำหนดฟิลด์แล้วใส่ {{รหัสฟิลด์}} ในไฟล์ Word เช่น {{subject}}\n"
            "จากนั้นสร้างเอกสารจากแบบฟอร์มนี้ กรอกค่า แล้วสั่งพิมพ์"
        ),
    )
    active = fields.Boolean(default=True)
    datas = fields.Binary(string="ไฟล์ Word (.docx)", attachment=True)
    filename = fields.Char(string="ชื่อไฟล์")
    layout_html = fields.Html(
        string="Word layout",
        sanitize=False,
        prefetch=False,
        copy=True,
    )
    source_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="โมเดลต้นทาง",
        domain="[('transient', '=', False)]",
        ondelete="set null",
        help=(
            "โมเดลของเอกสารต้นทางที่ใช้สร้างเอกสาร เช่น ใบขอซื้อ หรือใบสั่งซื้อ "
            "เมื่อกำหนดแล้ว ฟิลด์ทุกตัวเลือกข้อมูลจากโมเดลนี้ "
            "และจะมีเมนู 'สร้างเอกสารจาก Document Studio' ในหน้าของโมเดลนั้น"
        ),
    )
    source_model_name = fields.Char(related="source_model_id.model", string="ชื่อโมเดลต้นทาง")
    block_ids = fields.One2many(
        comodel_name="vpk.document.studio.block",
        inverse_name="template_id",
        string="บล็อกเอกสาร",
        copy=True,
    )
    layout_font = fields.Selection(
        selection=LAYOUT_FONTS,
        string="ฟอนต์",
        default="TH SarabunIT๙",
        required=True,
    )
    layout_font_size = fields.Float(string="ขนาดฟอนต์ (pt)", default=16.0)
    layout_margin_top = fields.Float(string="ขอบบน (ซม.)", default=2.5, digits=(4, 2))
    layout_margin_bottom = fields.Float(string="ขอบล่าง (ซม.)", default=2.0, digits=(4, 2))
    layout_margin_left = fields.Float(string="ขอบซ้าย (ซม.)", default=3.0, digits=(4, 2))
    layout_margin_right = fields.Float(string="ขอบขวา (ซม.)", default=2.0, digits=(4, 2))
    layout_preview_pdf = fields.Binary(
        string="ตัวอย่างไฟล์ Word",
        attachment=True,
        copy=False,
    )
    layout_preview_filename = fields.Char(copy=False)
    layout_placeholder_hint = fields.Html(
        string="ฟิลด์ที่ใช้ได้",
        compute="_compute_layout_placeholder_hint",
        sanitize=False,
    )
    field_ids = fields.One2many(
        comodel_name="vpk.document.studio.field",
        inverse_name="template_id",
        string="ฟิลด์",
        copy=True,
    )
    field_count = fields.Integer(
        string="จำนวนฟิลด์",
        compute="_compute_field_count",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "รหัสแบบฟอร์มต้องไม่ซ้ำในบริษัทเดียวกัน",
        ),
    ]

    @api.depends("field_ids")
    def _compute_field_count(self):
        for rec in self:
            rec.field_count = len(rec.field_ids)

    @api.depends("field_ids.code", "field_ids.name")
    def _compute_layout_placeholder_hint(self):
        for rec in self:
            chips = "".join(
                '<span class="badge text-bg-light border me-1 mb-1">'
                "<code>{{%s}}</code> %s</span>"
                % (escape(field.code or ""), escape(field.name or ""))
                for field in rec.field_ids
                if field.code
            )
            rec.layout_placeholder_hint = chips or _(
                "<span class='text-muted'>ยังไม่มีฟิลด์ พิมพ์ {{รหัสฟิลด์}} ใน layout "
                "แล้วบันทึกเป็นไฟล์ Word ระบบจะสร้างฟิลด์ให้</span>"
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = vals["code"].strip().lower()
        records = super().create(vals_list)
        records._sync_fields_from_word()
        records._sync_source_binding_actions()
        return records

    def write(self, vals):
        if vals.get("code"):
            vals = dict(vals, code=vals["code"].strip().lower())
        if "datas" in vals and "layout_preview_pdf" not in vals:
            vals = dict(vals, layout_preview_pdf=False, layout_preview_filename=False)
        result = super().write(vals)
        if "datas" in vals:
            self._sync_fields_from_word()
        if "source_model_id" in vals or "active" in vals:
            self._sync_source_binding_actions()
        if not self.env.context.get("skip_layout_regen") and (
            "layout_font_size" in vals
            or any(key.startswith("layout_margin_") for key in vals)
        ):
            self._regenerate_layout_from_blocks_if_blocks()
        return result

    def unlink(self):
        result = super().unlink()
        self.env["vpk.document.studio.template"]._sync_source_binding_actions()
        return result

    # ------------------------------------------------------------------
    # "Create document" action on every source model
    # ------------------------------------------------------------------

    @api.model
    def _sync_source_binding_actions(self):
        """Keep one 'สร้างเอกสารจาก Document Studio' action per source model."""
        Template = self.env["vpk.document.studio.template"].sudo()
        Actions = self.env["ir.actions.act_window"].sudo()
        wizard_model = "vpk.document.studio.create.wizard"
        wanted = Template.search([("source_model_id", "!=", False)]).mapped("source_model_id")
        existing = Actions.search(
            [("res_model", "=", wizard_model), ("binding_model_id", "!=", False)]
        )
        existing_models = existing.mapped("binding_model_id")
        group = self.env.ref(
            "vpk_document_studio.group_document_studio_user", raise_if_not_found=False
        )
        for model in wanted - existing_models:
            Actions.create(
                {
                    "name": _("สร้างเอกสารจาก Document Studio"),
                    "res_model": wizard_model,
                    "view_mode": "form",
                    "target": "new",
                    "binding_model_id": model.id,
                    "binding_type": "action",
                    "binding_view_types": "list,form",
                    "groups_id": [(6, 0, group.ids)] if group else False,
                }
            )
        stale = existing.filtered(lambda action: action.binding_model_id not in wanted)
        stale.unlink()
        return True

    # ------------------------------------------------------------------
    # Standard blocks -> layout_html
    # ------------------------------------------------------------------

    def _printable_width_cm(self):
        self.ensure_one()
        return max(
            5.0,
            21.0 - (self.layout_margin_left or 0.0) - (self.layout_margin_right or 0.0),
        )

    def _regenerate_layout_from_blocks_if_blocks(self):
        if self.env.context.get("skip_layout_regen"):
            return
        self.filtered("block_ids")._regenerate_layout_from_blocks()

    def _regenerate_layout_from_blocks(self):
        for rec in self:
            width = rec._printable_width_cm()
            size = rec.layout_font_size or 16.0
            html = "".join(
                block._render_html(width, size) for block in rec.block_ids.sorted("sequence")
            )
            codes = []
            for block in rec.block_ids.sorted("sequence"):
                block_html = block._render_html(width, size)
                skip = set()
                repeat = (block.table_repeat_code or "").strip()
                if block.block_type == "table" and repeat:
                    skip = set(ROW_TOKENS)
                    if repeat not in codes:
                        codes.append(repeat)
                for code in PLACEHOLDER_RE.findall(block_html):
                    if code not in skip and code not in codes:
                        codes.append(code)
            rec.with_context(skip_layout_regen=True).write({"layout_html": html})
            rec._ensure_fields_for_codes(codes)
        return True

    def _ensure_fields_for_codes(self, codes):
        """Create form fields for `{{codes}}` used by the blocks."""
        self.ensure_one()
        Field = self.env["vpk.document.studio.field"]
        known = set(self.field_ids.mapped("code"))
        sequence = max(self.field_ids.mapped("sequence") or [0])
        created = []
        for code in codes:
            if code in known or not CODE_RE.match(code):
                continue
            if code in _RESERVED_CODES or _DERIVED_CODE_RE.match(code):
                continue
            sequence += 10
            Field.create(
                {
                    "template_id": self.id,
                    "code": code,
                    "name": self._label_for_code(code),
                    "field_type": self._field_type_for_code(code),
                    "sequence": sequence,
                }
            )
            known.add(code)
            created.append(code)
        return created

    def action_regenerate_layout(self):
        self.ensure_one()
        self._regenerate_layout_from_blocks()
        return True

    def action_load_memo_preset(self):
        """Replace the blocks with the standard บันทึกข้อความ layout."""
        self.ensure_one()
        self.block_ids.with_context(skip_layout_regen=True).unlink()
        Block = self.env["vpk.document.studio.block"].with_context(
            skip_layout_regen=True
        )
        presets = [
            {"block_type": "memo_header"},
            {
                "block_type": "paragraph",
                "content": (
                    "<p>ด้วย {{agency}} มีความประสงค์จะประกวดราคาซื้อ "
                    "จำนวน {{items_count_th}} รายการ ด้วยวิธีประกวดราคาอิเล็กทรอนิกส์ "
                    "(e-bidding) ซึ่งมีรายละเอียด ดังต่อไปนี้</p>"
                ),
            },
            {
                "block_type": "table",
                "table_repeat_code": "items",
                "table_footer_label": "รวมเป็นเงินทั้งสิ้น",
                "table_footer_value": "{{items_total}}",
                "column_ids": [
                    (0, 0, {"sequence": 10, "header": "ลำดับ", "width_cm": 1.5,
                            "align": "center", "content": "{{no_th}}"}),
                    (0, 0, {"sequence": 20, "header": "รายการ", "width_cm": 0.0,
                            "align": "left", "content": "{{name}}"}),
                    (0, 0, {"sequence": 30, "header": "จำนวน", "width_cm": 3.0,
                            "align": "center", "content": "{{qty}} {{uom}}"}),
                    (0, 0, {"sequence": 40, "header": "จำนวนเงิน (บาท)", "width_cm": 3.0,
                            "align": "right", "content": "{{amount}}"}),
                ],
            },
            {
                "block_type": "paragraph",
                "content": "<p>จึงเรียนมาเพื่อโปรดพิจารณา</p>",
            },
            {
                "block_type": "signature",
                "sig_role": "ผู้เสนอ",
                "code_name": "proposer_name",
                "code_position": "proposer_position",
            },
        ]
        Block.create(
            [
                dict(vals, template_id=self.id, sequence=(index + 1) * 10)
                for index, vals in enumerate(presets)
            ]
        )
        self._regenerate_layout_from_blocks()
        return True

    def _layout_margins(self):
        self.ensure_one()
        return {
            "top": self.layout_margin_top,
            "bottom": self.layout_margin_bottom,
            "left": self.layout_margin_left,
            "right": self.layout_margin_right,
        }

    @api.model
    def _layout_font_from_word(self, font_name):
        keys = [key for key, _label in LAYOUT_FONTS]
        if font_name in keys:
            return font_name
        if font_name and "IT" in font_name.upper():
            return "TH SarabunIT๙"
        return "TH Sarabun New"

    def _render_layout_preview(self):
        self.ensure_one()
        try:
            pdf_bytes = convert_docx_bytes_to_pdf(self._template_bytes())
        except PdfConversionError as error:
            raise UserError(str(error)) from error
        self.write(
            {
                "layout_preview_pdf": base64.b64encode(pdf_bytes),
                "layout_preview_filename": "%s-preview.pdf" % (self.code or "form"),
            }
        )

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            if rec.code and " " in rec.code:
                raise ValidationError(_("รหัสแบบฟอร์มห้ามมีช่องว่าง"))

    def _template_bytes(self):
        self.ensure_one()
        if not self.datas:
            raise UserError(_("กรุณาอัปโหลดไฟล์ Word ของแบบฟอร์ม %s") % self.name)
        return base64.b64decode(self.datas)

    def _field_schema(self):
        self.ensure_one()
        return [field._schema_dict() for field in self.field_ids]

    def _default_values(self):
        self.ensure_one()
        return {field.code: field._parsed_default() for field in self.field_ids}

    def _known_codes(self):
        self.ensure_one()
        return set(self.field_ids.mapped("code"))

    @api.model
    def _label_for_code(self, code):
        if code in PLACEHOLDER_LABELS:
            return PLACEHOLDER_LABELS[code]
        if code.startswith("item_"):
            return _("รายการ %s") % code.split("_", 1)[-1]
        return code.replace("_", " ").strip() or code

    @api.model
    def _field_type_for_code(self, code):
        if code in ("items", "pr_lines", "pr_items", "product_lines"):
            return "many2one"
        if code.endswith("_date") or code in ("date", "memo_date", "doc_date"):
            return "date"
        if (
            code.startswith("item_")
            or code.startswith("body_")
            or code in ("intro", "detail", "note")
        ):
            return "text"
        return "char"

    def _sync_fields_from_word(self):
        """Create form fields for {{placeholders}} found in the Word file."""
        created = []
        Field = self.env["vpk.document.studio.field"]
        for rec in self:
            if not rec.datas:
                continue
            try:
                found = extract_placeholders(rec._template_bytes())
            except DocxMergeError:
                continue
            known = set(rec.field_ids.mapped("code"))
            sequence = max(rec.field_ids.mapped("sequence") or [0])
            for code in found:
                if code in known or not CODE_RE.match(code):
                    continue
                sequence += 10
                Field.create(
                    {
                        "template_id": rec.id,
                        "code": code,
                        "name": rec._label_for_code(code),
                        "field_type": rec._field_type_for_code(code),
                        "sequence": sequence,
                    }
                )
                known.add(code)
                created.append(code)
        return created

    def action_sync_fields_from_word(self):
        self.ensure_one()
        created = self._sync_fields_from_word()
        if created:
            message = _("เพิ่มฟิลด์จาก Word %s รายการ: %s") % (
                len(created),
                ", ".join("{{%s}}" % code for code in created),
            )
        else:
            message = _("ฟิลด์ครบตาม Word แล้ว")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ดึงฟิลด์จาก Word"),
                "message": message,
                "type": "success",
                "sticky": bool(created),
            },
        }

    def _placeholder_report(self):
        self.ensure_one()
        try:
            found = extract_placeholders(self._template_bytes())
        except DocxMergeError as error:
            raise UserError(str(error)) from error
        known = self._known_codes()
        unknown = [code for code in found if code not in known]
        unused = [field.code for field in self.field_ids if field.code not in set(found)]
        return {
            "found": found,
            "unknown": unknown,
            "unused": unused,
        }

    def action_check_placeholders(self):
        self.ensure_one()
        report = self._placeholder_report()
        if not report["found"] and not self.field_ids:
            message = _("ยังไม่มีฟิลด์และไม่พบ placeholder ในไฟล์ Word")
            ntype = "warning"
        elif not report["found"]:
            message = _("ไม่พบ {{placeholder}} ในไฟล์ Word")
            ntype = "warning"
        elif not report["unknown"] and not report["unused"]:
            message = _("ไฟล์ Word ตรงกับฟิลด์ทั้งหมด (%s รายการ)") % len(
                report["found"]
            )
            ntype = "success"
        else:
            parts = []
            if report["unknown"]:
                parts.append(
                    _("ใน Word แต่ไม่มีฟิลด์: %s")
                    % ", ".join("{{%s}}" % code for code in report["unknown"])
                )
            if report["unused"]:
                parts.append(
                    _("มีฟิลด์แต่ไม่พบใน Word: %s")
                    % ", ".join("{{%s}}" % code for code in report["unused"])
                )
            message = "\n".join(parts)
            ntype = "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ตรวจ placeholder"),
                "message": message,
                "type": ntype,
                "sticky": ntype != "success",
            },
        }

    def action_download_placeholder_docx(self):
        self.ensure_one()
        try:
            content = build_placeholder_guide_docx(
                self.name,
                self._field_schema(),
            )
        except DocxMergeError as error:
            raise UserError(str(error)) from error
        filename = "placeholders-%s.docx" % (self.code or "form")
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(content),
                "res_model": self._name,
                "res_id": self.id,
                "type": "binary",
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def action_create_document(self):
        self.ensure_one()
        document = self.env["vpk.document.studio.document"].create(
            {"template_id": self.id}
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร"),
            "res_model": "vpk.document.studio.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }
