# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import logging
import re
from html import escape
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .docx_merge import DocxMergeError, extract_repeat_tokens, merge_docx_bytes
from .pdf_converter import (
    PdfConversionError,
    convert_docx_bytes_to_html,
    convert_docx_bytes_to_pdf,
    convert_html_to_docx_bytes,
    convert_html_to_pdf_bytes,
    find_soffice,
    thai_font_face_css,
)
from .studio_field import PLACEHOLDER_RE

LINE_TOKEN_RE = re.compile(r"\{\{\s*line\.([a-z_][a-z0-9_]*)\s*\}\}")
from .word_layout import (
    apply_page_setup,
    build_layout_document,
    build_print_html,
    LIVE_FIELD_ATTR,
    expand_repeat_rows_html,
    fill_empty_field_boxes_html,
    live_field_span,
    parse_layout_html,
    refresh_live_fields_html,
)

_logger = logging.getLogger(__name__)

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
PDF_MIME = "application/pdf"


class DocumentStudioDocument(models.Model):
    _name = "vpk.document.studio.document"
    _description = "เอกสาร Document Studio"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    document_type_id = fields.Many2one(
        comodel_name="vpk.document.studio.document.type",
        string="ประเภทเอกสาร",
        compute="_compute_document_type_id",
        store=True,
        readonly=False,
        precompute=True,
        index=True,
        tracking=True,
        ondelete="restrict",
    )
    template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม",
        tracking=True,
        ondelete="restrict",
        index=True,
    )
    template_document_type_id = fields.Many2one(
        related="template_id.document_type_id",
        string="ประเภทเอกสารของแบบฟอร์ม",
    )
    source_mode = fields.Selection(
        selection=[
            ("studio", "สร้างจากแบบฟอร์ม"),
            ("uploaded", "แนบไฟล์ต้นทาง"),
        ],
        string="ที่มา",
        default="studio",
        required=True,
        copy=False,
    )
    date = fields.Date(
        string="วันที่",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("generated", "สร้างไฟล์แล้ว"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    source_ref = fields.Reference(
        selection="_selection_source_models",
        string="เรคคอร์ดต้นทาง",
        copy=False,
        help="เรคคอร์ดที่ดึงข้อมูลมาเติมในเอกสาร เช่น ใบขอซื้อหรือใบสั่งซื้อ",
    )
    source_model_id = fields.Many2one(
        related="template_id.source_model_id", string="โมเดลต้นทาง"
    )
    value_json = fields.Json(string="ค่าที่กรอก", default=dict)
    field_schema_json = fields.Json(
        string="โครงสร้างฟิลด์",
        compute="_compute_field_schema_json",
    )
    body = fields.Html(
        string="เนื้อหาเอกสาร",
        sanitize=False,
        prefetch=False,
        copy=True,
        help="ผลลัพธ์จากแบบฟอร์ม แสดงใน Word editor ก่อนพิมพ์ PDF",
    )
    layout_font = fields.Selection(
        related="template_id.layout_font",
        readonly=True,
    )
    layout_font_size = fields.Float(
        related="template_id.layout_font_size",
        readonly=True,
    )
    layout_margin_top = fields.Float(
        related="template_id.layout_margin_top",
        readonly=True,
    )
    layout_margin_bottom = fields.Float(
        related="template_id.layout_margin_bottom",
        readonly=True,
    )
    layout_margin_left = fields.Float(
        related="template_id.layout_margin_left",
        readonly=True,
    )
    layout_margin_right = fields.Float(
        related="template_id.layout_margin_right",
        readonly=True,
    )
    docx_file = fields.Binary(string="ไฟล์ Word", attachment=True, copy=False)
    docx_filename = fields.Char(string="ชื่อไฟล์ Word", copy=False)
    pdf_file = fields.Binary(string="ไฟล์ PDF", attachment=True, copy=False)
    pdf_filename = fields.Char(string="ชื่อไฟล์ PDF", copy=False)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้สร้าง",
        default=lambda self: self.env.user,
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    note = fields.Text(string="หมายเหตุ")

    @api.depends("template_id")
    def _compute_document_type_id(self):
        for rec in self:
            if rec.template_id.document_type_id:
                rec.document_type_id = rec.template_id.document_type_id
            elif not rec.document_type_id:
                rec.document_type_id = False

    @api.constrains("template_id", "source_mode")
    def _check_template_or_upload(self):
        for rec in self:
            if rec.source_mode == "studio" and not rec.template_id:
                raise ValidationError(_("กรุณาเลือกแบบฟอร์ม"))

    @api.depends(
        "template_id",
        "template_id.field_ids",
        "template_id.field_ids.code",
        "template_id.field_ids.display_template",
        "template_id.field_ids.help",
    )
    def _compute_field_schema_json(self):
        for rec in self:
            rec.field_schema_json = (
                rec.template_id._field_schema() if rec.template_id else []
            )

    @api.model
    def _extra_source_models(self):
        """Models allowed as source_ref even when no template uses them."""
        return ["purchase.request"]

    @api.model
    def _selection_source_models(self):
        templates = self.env["vpk.document.studio.template"].sudo().search(
            [("source_model_id", "!=", False)]
        )
        names = {model.model: model.name for model in templates.mapped("source_model_id")}
        for model_name in self._extra_source_models():
            if model_name in self.env:
                names.setdefault(model_name, self.env["ir.model"]._get(model_name).name)
        result = {model: "%s (%s)" % (name, model) for model, name in names.items()}
        return sorted(result.items(), key=lambda item: item[1])

    @api.model
    def _record_from_ref(self, ref):
        if not ref:
            return None
        if isinstance(ref, models.BaseModel):
            return ref.sudo() if ref else None
        model, _sep, rec_id = str(ref).partition(",")
        if model in self.env and rec_id.isdigit():
            record = self.env[model].sudo().browse(int(rec_id)).exists()
            return record or None
        return None

    @api.model
    def _values_from_record(self, template, record):
        """Fill field values from any record using the template's Model/Field mapping."""
        values = template._default_values() if template else {}
        if not template or not record:
            return values
        for field in template.field_ids:
            if not field.map_field_id:
                continue
            if field.map_model_id and field.map_model_id.model != record._name:
                continue
            extracted = field.extract_mapped_record_value(record)
            if field.field_type == "many2one":
                values[field.code] = {
                    "res_id": record.id,
                    "label": record.display_name or "%s#%s" % (record._name, record.id),
                    "text": "" if extracted in (None, False) else str(extracted),
                }
            elif extracted not in (None, False, ""):
                values[field.code] = extracted
        return values

    @api.onchange("source_ref")
    def _onchange_source_ref(self):
        record = self._record_from_ref(self.source_ref)
        if self.template_id and record:
            self.value_json = self._values_from_record(self.template_id, record)
            self.body = self._filled_body_html()

    def action_open_source_record(self):
        self.ensure_one()
        record = self._record_from_ref(self.source_ref)
        if not record:
            raise UserError(_("เอกสารนี้ยังไม่ได้เลือกเรคคอร์ดต้นทาง"))
        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _body_html_from_template(self, template, convert_word=False):
        if not template:
            return False
        html = (template.layout_html or "").strip()
        if html:
            return template.layout_html
        if convert_word and template.datas:
            try:
                html_text = convert_docx_bytes_to_html(template._template_bytes())
                body_html, _settings = parse_layout_html(html_text)
                return body_html or False
            except (PdfConversionError, UserError, Exception):
                _logger.info(
                    "Could not convert template %s Word file to HTML for body",
                    template.display_name,
                    exc_info=True,
                )
                return False
        return False

    @api.model
    def _live_body_codes(self):
        """Codes whose value may arrive after the body is filled; see _refresh_live_body_fields."""
        return set()

    def _interpolate_body_html(self, html, mapping, rows=None):
        if not html:
            return html
        html = expand_repeat_rows_html(html, mapping, rows)
        live_codes = self._live_body_codes()

        def replacer(match):
            code = match.group(1)
            value = mapping.get(code)
            text = "" if value is None or value is False else str(value).strip()
            if code in live_codes:
                return live_field_span(code, text)
            if not text:
                return ""
            return escape(text, quote=False).replace("\n", "<br/>")

        return fill_empty_field_boxes_html(PLACEHOLDER_RE.sub(replacer, html))

    def _refresh_live_body_fields(self):
        """Rewrite only the live-field spans of the stored body with current values."""
        for rec in self:
            if not rec.body or LIVE_FIELD_ATTR not in rec.body:
                continue
            body = refresh_live_fields_html(rec.body, rec._merge_mapping())
            if body != rec.body:
                rec.with_context(vpk_live_field_refresh=True).write({"body": body})

    def _filled_body_html(self, convert_word=False):
        self.ensure_one()
        if not self.template_id:
            return False
        html = self._body_html_from_template(
            self.template_id, convert_word=convert_word
        )
        if not html:
            return False
        return self._interpolate_body_html(
            html, self._merge_mapping(), self._repeat_rows_data()
        )

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id:
            self.value_json = self.template_id._default_values()
            self.body = self._filled_body_html()
            if self.template_id.company_id:
                self.company_id = self.template_id.company_id
        else:
            self.value_json = {}
            self.body = False

    def action_reload_body_from_template(self):
        for rec in self:
            if not rec.template_id:
                rec.body = False
                continue
            rec.body = rec._filled_body_html(convert_word=True)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        Template = self.env["vpk.document.studio.template"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "vpk.document.studio.document"
                    )
                    or _("New")
                )
            template = Template.browse(vals.get("template_id")) if vals.get("template_id") else Template
            if template:
                defaults = template._default_values()
                incoming = dict(vals.get("value_json") or {})
                source = self._record_from_ref(vals.get("source_ref"))
                if source and not incoming:
                    defaults.update(self._values_from_record(template, source))
                defaults.update(incoming)
                vals["value_json"] = defaults
                vals.setdefault("company_id", template.company_id.id)
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list):
            if rec.template_id and not vals.get("body"):
                rec.body = rec._filled_body_html(convert_word=True)
        return records

    def write(self, vals):
        template_changed = False
        if "template_id" in vals:
            new_tid = vals.get("template_id") or False
            template_changed = any((rec.template_id.id or False) != new_tid for rec in self)
            template = self.env["vpk.document.studio.template"].browse(new_tid)
            extra = {}
            if template_changed and "value_json" not in vals and template:
                extra["value_json"] = template._default_values()
            if extra:
                vals = dict(vals, **extra)
        result = super().write(vals)
        if template_changed and "body" not in vals:
            for rec in self:
                rec.body = (
                    rec._filled_body_html(convert_word=True)
                    if rec.template_id
                    else False
                )
        return result

    def action_save_body(self):
        self.ensure_one()
        if not (self.body or "").strip():
            raise UserError(_("ยังไม่มีเนื้อหาให้บันทึก"))
        self.message_post(
            body=_("บันทึกเนื้อหาเอกสารแล้ว"),
            subtype_xmlid="mail.mt_note",
        )
        return True

    def _values(self):
        self.ensure_one()
        return dict(self.value_json or {})

    def _missing_required(self):
        self.ensure_one()
        values = self._values()
        missing = []
        for field in self.template_id.field_ids:
            if not field.required:
                continue
            if (field.display_template or "").strip():
                continue
            if field._is_empty(values.get(field.code)):
                missing.append(field.name)
        return missing

    def _line_tokens_used(self):
        """Names used as {{line.<field>}} / {{items.<field>}} in layout and Word."""
        self.ensure_one()
        text = "%s %s" % (self.body or "", self.template_id.layout_html or "")
        tokens = set(LINE_TOKEN_RE.findall(text))
        if self.template_id.datas:
            try:
                for fields in extract_repeat_tokens(self.template_id._template_bytes()).values():
                    tokens.update(fields)
            except DocxMergeError:
                pass
        return sorted(tokens)

    def _repeat_rows_data(self):
        """Structured rows (lines of the chosen record) per field code."""
        self.ensure_one()
        values = self._values()
        wanted = self._line_tokens_used()
        data = {}
        for field in self.template_id.field_ids:
            if field.field_type != "many2one":
                continue
            data[field.code] = field._relation_rows(values.get(field.code), wanted)
        return data

    def _merge_mapping(self):
        self.ensure_one()
        values = self._values()
        Field = self.env["vpk.document.studio.field"]
        raw = {}
        for field in self.template_id.field_ids:
            formatted = field.format_value(values.get(field.code)) or ""
            raw[field.code] = formatted
            if field.field_type == "many2one":
                pr_rows = field._relation_rows(values.get(field.code))
                if pr_rows:
                    raw["%s_total" % field.code] = Field._fmt_money(
                        sum(row["amount_value"] for row in pr_rows)
                    )
            lines = [line for line in formatted.splitlines() if line.strip()]
            if lines:
                raw["%s_count" % field.code] = str(len(lines))
                raw["%s_count_th" % field.code] = Field._thai_digits(len(lines))
        sources = {}
        for field in self.template_id.field_ids:
            sources[field.code] = field._display_source(raw.get(field.code, ""))
        working = dict(raw)
        for _pass in range(4):
            snapshot = dict(working)
            for field in self.template_id.field_ids:
                working[field.code] = Field.interpolate_placeholders(
                    sources[field.code],
                    working,
                    self_value=raw.get(field.code, ""),
                )
            if working == snapshot:
                break
        result = {
            field.code: working.get(field.code, "")
            for field in self.template_id.field_ids
        }
        for key, value in raw.items():
            if key.endswith(("_count", "_count_th", "_total")) and key not in result:
                result[key] = value
        return result

    def _docx_bytes_from_body(self):
        self.ensure_one()
        template = self.template_id
        document_html = build_layout_document(
            self.body,
            template.layout_font,
            template.layout_font_size or 16.0,
            template._layout_margins(),
        )
        docx_bytes = convert_html_to_docx_bytes(
            document_html, soffice_path=self._soffice_path()
        )
        docx_bytes = apply_page_setup(
            docx_bytes,
            template.layout_font,
            template.layout_font_size or 16.0,
            template._layout_margins(),
        )
        return merge_docx_bytes(
            docx_bytes,
            self._merge_mapping(),
            known_codes=template._known_codes(),
            rows=self._repeat_rows_data(),
        )

    def _uses_word_template(self):
        self.ensure_one()
        return bool(self.template_id and self.template_id.datas)

    def _render_docx_bytes(self):
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("กรุณาเลือกแบบฟอร์ม"))
        if not self._uses_word_template():
            html = (self.body or "").strip()
            if html:
                try:
                    return self._docx_bytes_from_body()
                except (PdfConversionError, DocxMergeError, UserError, Exception) as error:
                    _logger.warning(
                        "Could not convert document %s body to Word, falling back to template file",
                        self.display_name,
                        exc_info=True,
                    )
                    raise UserError(str(error)) from error
        missing = self._missing_required()
        if missing:
            raise UserError(
                _("กรุณากรอกฟิลด์ที่จำเป็น: %s") % ", ".join(missing)
            )
        self.template_id.sudo()._sync_fields_from_word()
        try:
            return merge_docx_bytes(
                self.template_id._template_bytes(),
                self._merge_mapping(),
                known_codes=self.template_id._known_codes(),
                rows=self._repeat_rows_data(),
            )
        except DocxMergeError as error:
            raise UserError(str(error)) from error

    def _safe_basename(self):
        self.ensure_one()
        raw = self.name or "document"
        cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", raw).strip()
        return cleaned or "document"

    def _store_file(self, content, filename, mimetype, kind):
        self.ensure_one()
        field_file, field_name = {
            "docx": ("docx_file", "docx_filename"),
            "pdf": ("pdf_file", "pdf_filename"),
        }[kind]
        self.write(
            {
                "state": "generated",
                field_file: base64.b64encode(content),
                field_name: filename,
            }
        )
        self.message_post(
            body=_("สร้างไฟล์ %s แล้ว") % filename,
            subtype_xmlid="mail.mt_note",
        )

    def action_generate_docx(self):
        self.ensure_one()
        self._check_generated_from_template()
        content = self._render_docx_bytes()
        self._store_file(
            content,
            "%s.docx" % self._safe_basename(),
            DOCX_MIME,
            "docx",
        )
        return True

    def _soffice_path(self):
        params = self.env["ir.config_parameter"].sudo()
        return find_soffice(
            params.get_param("vpk_document_studio.soffice_path")
            or params.get_param("vpk_official_document.soffice_path")
            or params.get_param("py3o.conversion_command")
            or None
        )

    def _print_html(self):
        self.ensure_one()
        template = self.template_id
        html = self._interpolate_body_html(
            self.body or "", self._merge_mapping(), self._repeat_rows_data()
        )
        return build_print_html(
            html,
            template.layout_font,
            template.layout_font_size or 16.0,
            template._layout_margins(),
            font_face_css=thai_font_face_css(),
        )

    def _render_pdf_bytes(self):
        self.ensure_one()
        if not self._uses_word_template() and (self.body or "").strip():
            try:
                return convert_html_to_pdf_bytes(
                    self._print_html(),
                    soffice_path=self._soffice_path(),
                )
            except (PdfConversionError, Exception):
                _logger.warning(
                    "Direct HTML PDF failed for %s, falling back to Word conversion",
                    self.display_name,
                    exc_info=True,
                )
        docx_content = self._render_docx_bytes()
        return convert_docx_bytes_to_pdf(
            docx_content,
            soffice_path=self._soffice_path(),
        )

    def _check_generated_from_template(self):
        for rec in self:
            if rec.source_mode == "uploaded":
                raise UserError(
                    _("เอกสาร %s แนบไฟล์ต้นทางมา ไม่ได้สร้างจากแบบฟอร์ม") % rec.display_name
                )

    def attach_uploaded_file(self, file_b64, filename):
        """Store a user-supplied PDF or Word file as this document's file."""
        self.ensure_one()
        if not file_b64:
            raise UserError(_("กรุณาแนบไฟล์ต้นทาง"))
        name = filename or "document.pdf"
        lower = name.lower()
        if lower.endswith(".pdf"):
            kind = "pdf"
        elif lower.endswith(".docx"):
            kind = "docx"
        else:
            raise UserError(_("รองรับเฉพาะไฟล์ PDF หรือ Word (.docx)"))
        content = base64.b64decode(file_b64)
        self._store_file(content, name, PDF_MIME if kind == "pdf" else DOCX_MIME, kind)
        if kind == "docx" and not self.pdf_file:
            try:
                pdf_content = convert_docx_bytes_to_pdf(
                    content, soffice_path=self._soffice_path()
                )
            except Exception:
                _logger.info("Could not convert uploaded Word %s to PDF", name, exc_info=True)
            else:
                stem = name[:-5]
                self._store_file(pdf_content, "%s.pdf" % stem, PDF_MIME, "pdf")
        return True

    def action_generate_pdf(self):
        self.ensure_one()
        self._check_generated_from_template()
        try:
            docx_content = self._render_docx_bytes()
            self._store_file(
                docx_content,
                "%s.docx" % self._safe_basename(),
                DOCX_MIME,
                "docx",
            )
        except (PdfConversionError, DocxMergeError, UserError, Exception):
            _logger.warning(
                "Could not store Word file for %s while printing PDF",
                self.display_name,
                exc_info=True,
            )
        try:
            pdf_content = self._render_pdf_bytes()
        except PdfConversionError as error:
            raise UserError(str(error)) from error
        self._store_file(
            pdf_content,
            "%s.pdf" % self._safe_basename(),
            PDF_MIME,
            "pdf",
        )
        return self.action_open_pdf()

    def _pdf_content_url(self):
        self.ensure_one()
        filename = quote(self.pdf_filename or "document.pdf")
        return "/web/content/%s/%s/pdf_file/%s" % (self._name, self.id, filename)

    def action_open_pdf(self):
        self.ensure_one()
        if not self.pdf_filename and not self.pdf_file:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        return {
            "type": "ir.actions.act_url",
            "url": self._pdf_content_url(),
            "target": "new",
        }

    def action_draft(self):
        self.write({"state": "draft"})
        return True
