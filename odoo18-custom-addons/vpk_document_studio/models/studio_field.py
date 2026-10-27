# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")
FIELD_TYPES = [
    ("char", "ข้อความสั้น"),
    ("text", "ข้อความยาว"),
    ("date", "วันที่"),
    ("integer", "ตัวเลข"),
    ("float", "ทศนิยม"),
    ("boolean", "ใช่ / ไม่ใช่"),
    ("selection", "ตัวเลือก"),
    ("many2one", "เลือกเรคคอร์ด / ตารางรายการ (Many2one)"),
]
RELATION_SOURCES = [
    ("pr_lines_name_only", "รายการสินค้าจากใบขอซื้อ (PR) — เฉพาะชื่อสินค้า"),
    ("pr_lines_thai", "รายการสินค้าจากใบขอซื้อ (PR) — เลขไทย ๑. ๒. ๓."),
    ("pr_lines_arabic", "รายการสินค้าจากใบขอซื้อ (PR) — เลขอารบิก 1. 2. 3."),
    ("pr_lines_name_qty", "รายการสินค้าจากใบขอซื้อ (PR) — ชื่อและจำนวน"),
]
_THAI_DIGITS_MAP = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
THAI_MONTHS = (
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)


class DocumentStudioField(models.Model):
    _name = "vpk.document.studio.field"
    _description = "ฟิลด์แบบฟอร์ม Document Studio"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="vpk.document.studio.template",
        string="แบบฟอร์ม",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    name = fields.Char(string="ป้ายชื่อ", required=True)
    code = fields.Char(
        string="รหัส",
        required=True,
        index=True,
        help="ใช้ในไฟล์ Word เป็น {{รหัส}} เช่น {{subject}} และให้ฟิลด์อื่นอ้างอิงได้ด้วย {{รหัสนี้}}",
    )
    field_type = fields.Selection(
        selection=FIELD_TYPES,
        string="ชนิดฟิลด์",
        required=True,
        default="char",
    )
    required = fields.Boolean(string="จำเป็น")
    selection_options = fields.Text(
        string="ตัวเลือก",
        help="พิมพ์หนึ่งตัวเลือกต่อบรรทัด สำหรับชนิดตัวเลือก",
    )
    relation_source = fields.Selection(
        selection=RELATION_SOURCES,
        string="การดึงข้อมูล Many2one",
        default="pr_lines_name_only",
        help="เมื่อเลือกใบขอซื้อ (PR) จะดึงรายการสินค้าทั้งหมดใน PR มารวมในฟิลด์นี้โดยไม่ต้องแยก item_1, item_2",
    )
    map_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="โมเดล (Model)",
        domain="[('transient', '=', False)]",
        ondelete="set null",
        compute="_compute_map_model_id",
        store=True,
        readonly=False,
        precompute=True,
        help=(
            "โมเดลต้นทางที่จะดึงข้อมูลมาแสดง ถ้าแบบฟอร์มกำหนด 'โมเดลต้นทาง' ไว้ "
            "ระบบใช้โมเดลนั้นให้อัตโนมัติ"
        ),
    )
    template_source_model_id = fields.Many2one(
        related="template_id.source_model_id",
        string="โมเดลต้นทางของแบบฟอร์ม",
        readonly=True,
    )
    map_model_name = fields.Char(
        related="map_model_id.model",
        string="ชื่อโมเดล",
        readonly=True,
    )
    map_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="ฟิลด์ที่ Map (Field)",
        domain="[('model_id', '=', map_model_id)]",
        ondelete="set null",
        help="เลือกฟิลด์ในโมเดลที่จะดึงค่ามาแสดง (เช่น line_ids, department_id, date_start)",
    )
    map_field_ttype = fields.Selection(
        related="map_field_id.ttype",
        readonly=True,
    )
    map_relation_model = fields.Char(
        related="map_field_id.relation",
        readonly=True,
    )
    map_sub_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="ฟิลด์ย่อยที่แสดงผล",
        domain="[('model', '=', map_relation_model)]",
        ondelete="set null",
        help="กรณีฟิลด์หลักเป็นตารางย่อย/ความสัมพันธ์ (เช่น line_ids) ให้เลือกฟิลด์ที่จะนำมาแสดง เช่น product_id หรือ name",
    )
    default_value = fields.Text(
        string="ค่าเริ่มต้น",
        help="ข้อความที่เติมให้เมื่อสร้างเอกสารใหม่ ผู้ใช้แก้ไขได้ในหน้าเอกสาร",
    )
    insert_code_id = fields.Many2one(
        comodel_name="vpk.document.studio.field",
        string="แทรกฟิลด์",
        store=False,
        domain="[('template_id', '=', template_id)]",
        help="เลือกฟิลด์เพื่อต่อ {{รหัส}} ท้ายรูปแบบแสดงผล",
    )
    display_template = fields.Text(
        string="รูปแบบแสดงผล",
        help=(
            "ประกอบข้อความจากฟิลด์อื่นด้วย {{รหัส}} เช่น "
            "ด้วย {{agency}} มีความประสงค์จะประกวดราคาซื้อ...\n"
            "ใช้ {{self}} สำหรับค่าที่ map/กรอกของฟิลด์นี้เอง "
            "และ {{รหัส_count}} / {{รหัส_count_th}} สำหรับจำนวนบรรทัด "
            "เช่น {{items_count}} หรือ {{items_count_th}}"
        ),
    )
    placeholder_hint = fields.Char(
        string="รหัสที่ใช้ได้อ้างอิง",
        compute="_compute_placeholder_hint",
    )
    help = fields.Char(string="คำอธิบาย")

    _sql_constraints = [
        (
            "code_template_uniq",
            "unique(template_id, code)",
            "รหัสฟิลด์ต้องไม่ซ้ำในแบบฟอร์มเดียวกัน",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = vals["code"].strip().lower()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            vals = dict(vals, code=vals["code"].strip().lower())
        return super().write(vals)

    @api.depends("template_id.source_model_id")
    def _compute_map_model_id(self):
        for rec in self:
            rec.map_model_id = rec.template_id.source_model_id or rec.map_model_id

    @api.onchange("map_model_id")
    def _onchange_map_model_id(self):
        if self.map_field_id and self.map_field_id.model_id != self.map_model_id:
            self.map_field_id = False
            self.map_sub_field_id = False

    @api.onchange("map_field_id")
    def _onchange_map_field_id(self):
        if self.map_field_id and self.map_field_id.ttype in ("one2many", "many2many"):
            self.field_type = "many2one"
        if not self.map_field_id or not self.map_field_id.relation:
            self.map_sub_field_id = False
            return
        if self.map_sub_field_id and self.map_sub_field_id.model != self.map_field_id.relation:
            self.map_sub_field_id = False
        if not self.map_sub_field_id and self.map_field_id.relation:
            default_sub = self.env["ir.model.fields"].sudo().search(
                [
                    ("model", "=", self.map_field_id.relation),
                    ("name", "in", ["product_id", "name", "display_name"]),
                ],
                limit=1,
            )
            if default_sub:
                self.map_sub_field_id = default_sub

    def extract_mapped_record_value(self, record):
        """Extract and format a value from `record` using `map_model_id`,
        `map_field_id`, and optional `map_sub_field_id`."""
        self.ensure_one()
        if not record or not record.exists() or not self.map_field_id:
            return None
        if self.map_model_id and record._name != self.map_model_id.model:
            return None
        fname = self.map_field_id.name
        if fname not in record._fields:
            return None
        raw_val = record[fname]
        ttype = self.map_field_id.ttype
        sub_fname = self.map_sub_field_id.name if self.map_sub_field_id else None

        if ttype in ("one2many", "many2many"):
            recs = raw_val
            if "cancelled" in recs._fields:
                recs = recs.filtered(lambda r: not r.cancelled)
            lines = []
            for idx, item in enumerate(recs, start=1):
                txt = self._extract_single_sub_value(item, sub_fname)
                if txt:
                    lines.append("%s. %s" % (idx, txt))
            return "\n".join(lines)

        if ttype == "many2one":
            if not raw_val:
                return ""
            if sub_fname:
                return self._extract_single_sub_value(raw_val, sub_fname)
            return self._clean_record_display(raw_val)

        if ttype in ("date", "datetime"):
            if not raw_val:
                return ""
            return fields.Date.to_string(raw_val) if self.field_type == "date" else self._format_thai_date(raw_val)

        if raw_val is False or raw_val is None:
            return ""
        return raw_val

    @api.model
    def _clean_record_display(self, rec):
        if not rec:
            return ""
        raw = rec.name if "name" in rec._fields and isinstance(rec.name, str) and rec.name else rec.display_name or ""
        return re.sub(r"^\s*\[[^\]]+\]\s*", "", str(raw)).strip()

    def _extract_single_sub_value(self, item, sub_fname=None):
        if not item:
            return ""
        if sub_fname and sub_fname in item._fields:
            sub_val = item[sub_fname]
            if isinstance(sub_val, models.BaseModel):
                return self._clean_record_display(sub_val)
            if sub_val is False or sub_val is None:
                return ""
            return re.sub(r"^\s*\[[^\]]+\]\s*", "", str(sub_val)).strip()
        if "product_id" in item._fields and item.product_id:
            return self._clean_record_display(item.product_id)
        return self._clean_record_display(item)

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            if not rec.code or not CODE_RE.match(rec.code):
                raise ValidationError(
                    _("รหัสฟิลด์ต้องเป็นภาษาอังกฤษตัวพิมพ์เล็ก ตัวเลข หรือ _ และขึ้นต้นด้วยตัวอักษร")
                )

    @api.constrains("field_type", "selection_options")
    def _check_selection_options(self):
        for rec in self:
            if rec.field_type == "selection" and not rec.option_list():
                raise ValidationError(
                    _("กรุณาระบุตัวเลือกอย่างน้อย 1 รายการ สำหรับฟิลด์ %s") % rec.name
                )

    @api.onchange("insert_code_id")
    def _onchange_insert_code_id(self):
        for rec in self:
            if rec.insert_code_id and rec.insert_code_id.code:
                text = rec.display_template or ""
                token = "{{%s}}" % rec.insert_code_id.code
                rec.display_template = (text + " " + token).strip()
                rec.insert_code_id = False

    @api.depends("template_id", "template_id.field_ids", "template_id.field_ids.code", "code")
    def _compute_placeholder_hint(self):
        for rec in self:
            codes = []
            if rec.template_id:
                codes = [
                    field.code
                    for field in rec.template_id.field_ids
                    if field.code and field.code != rec.code
                ]
            tokens = ["{{self}}"]
            for code in codes:
                tokens.append("{{%s}}" % code)
            rec.placeholder_hint = " ".join(tokens)

    def option_list(self):
        self.ensure_one()
        return [
            line.strip()
            for line in (self.selection_options or "").splitlines()
            if line.strip()
        ]

    def _parsed_default(self):
        self.ensure_one()
        raw = (self.default_value or "").strip()
        if self.field_type == "boolean":
            return raw.lower() in ("1", "true", "yes", "y", "ใช่")
        if not raw:
            return None if self.field_type in ("integer", "float", "date") else ""
        if self.field_type == "integer":
            try:
                return int(raw)
            except ValueError:
                return raw
        if self.field_type == "float":
            try:
                return float(raw)
            except ValueError:
                return raw
        return raw

    def _is_empty(self, value):
        self.ensure_one()
        if self.field_type == "boolean":
            return False
        return value is None or value is False or value == ""

    @api.model
    def _thai_digits(self, value):
        return str(value).translate(_THAI_DIGITS_MAP)

    @api.model
    def interpolate_placeholders(self, text, mapping, self_value=None):
        """Replace {{code}} / {{self}} using sibling field values."""
        if text is None or text is False:
            return ""
        result = str(text)
        if "{{" not in result:
            return result

        def replacer(match):
            code = match.group(1)
            if code == "self":
                if self_value is None or self_value is False:
                    return ""
                return str(self_value)
            if code in mapping:
                value = mapping.get(code)
                if value is None or value is False:
                    return ""
                return str(value)
            return match.group(0)

        for _unused in range(4):
            if "{{" not in result:
                break
            updated = PLACEHOLDER_RE.sub(replacer, result)
            if updated == result:
                break
            result = updated
        return result

    def _display_source(self, formatted_value):
        """Pick the text to interpolate: display_template, else the field value."""
        self.ensure_one()
        template = (self.display_template or "").strip()
        if template:
            return template
        if formatted_value in (None, False):
            return ""
        return formatted_value

    def format_value(self, value):
        self.ensure_one()
        if self._is_empty(value):
            return ""
        if self.field_type == "many2one":
            return self._format_many2one_value(value)
        if self.field_type == "boolean":
            return _("ใช่") if value else _("ไม่ใช่")
        if self.field_type == "date":
            return self._format_thai_date(value)
        if self.field_type == "integer":
            try:
                return str(int(value))
            except (TypeError, ValueError):
                return str(value)
        if self.field_type == "float":
            try:
                number = float(value)
            except (TypeError, ValueError):
                return str(value)
            text = ("%.10f" % number).rstrip("0").rstrip(".")
            return text or "0"
        return str(value)

    @api.model
    def _clean_product_line_name(self, line):
        raw = ""
        if line.product_id and line.product_id.name:
            raw = line.product_id.name.strip()
        if not raw:
            raw = (line.name or line.product_id.display_name or "").strip()
        raw = re.sub(r"^\s*\[[^\]]+\]\s*", "", raw)
        return raw.strip()

    @api.model
    def _format_pr_lines_text(self, request, mode="pr_lines_name_only"):
        if not request or not request.exists():
            return ""
        lines = request.line_ids.filtered(
            lambda line: not getattr(line, "cancelled", False) and (line.product_qty or line.name or line.product_id)
        )
        result = []
        for index, line in enumerate(lines, start=1):
            name = self._clean_product_line_name(line)
            if mode in ("pr_lines_name_only", "pr_lines_thai", None, False, ""):
                result.append("%s. %s" % (index, name))
                continue
            qty = line.product_qty or 0.0
            qty_txt = (
                "{:,.0f}".format(qty)
                if float(qty).is_integer()
                else "{:,.2f}".format(qty).rstrip("0").rstrip(".")
            )
            uom = line.product_uom_id.name if "product_uom_id" in line._fields and line.product_uom_id else ""
            cost = line.estimated_cost if "estimated_cost" in line._fields else 0.0
            cost_txt = "{:,.2f}".format(cost or 0.0)
            num_prefix = str(index)
            if mode == "pr_lines_name_qty":
                item_txt = "%s จำนวน %s %s" % (name, qty_txt, uom)
            else:
                item_txt = "%s จำนวน %s %s เป็นเงิน %s บาท" % (
                    name,
                    qty_txt,
                    uom,
                    cost_txt,
                )
            item_txt = re.sub(r"\s+", " ", item_txt).strip()
            result.append("%s. %s" % (num_prefix, item_txt))
        return "\n".join(result)

    @staticmethod
    def _fmt_qty(qty):
        qty = qty or 0.0
        if float(qty).is_integer():
            return "{:,.0f}".format(qty)
        return "{:,.2f}".format(qty).rstrip("0").rstrip(".")

    @staticmethod
    def _fmt_money(amount):
        return "{:,.2f}".format(amount or 0.0)

    def _record_from_value(self, value):
        """Record chosen in this many2one field (res_id stored in the document)."""
        self.ensure_one()
        target_model = self.map_model_id.model if self.map_model_id else "purchase.request"
        if target_model not in self.env:
            return None
        rec_id = None
        if isinstance(value, dict):
            rec_id = value.get("res_id") or value.get("id")
        elif isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
            rec_id = int(value)
        if not rec_id:
            return None
        record = self.env[target_model].sudo().browse(int(rec_id)).exists()
        return record or None

    def _row_source_records(self, record):
        """Sub records (lines) that become table rows for this field."""
        self.ensure_one()
        if self.map_field_id and self.map_field_id.ttype in ("one2many", "many2many"):
            fname = self.map_field_id.name
            lines = record[fname] if fname in record._fields else record.browse()
        elif record._name == "purchase.request":
            lines = record.line_ids
        else:
            return record.browse()
        if "cancelled" in lines._fields:
            lines = lines.filtered(lambda line: not line.cancelled)
        return lines

    _ROW_ALIASES = {
        "qty": ("product_qty", "product_uom_qty", "quantity", "qty"),
        "uom": ("product_uom_id", "product_uom", "uom_id"),
        "unit_price": ("price_unit", "unit_price"),
        "amount": ("price_subtotal", "estimated_cost", "amount", "amount_total", "price_total"),
        "spec": ("specifications", "description"),
    }

    def _first_field(self, record, candidates):
        for fname in candidates:
            if fname in record._fields:
                return fname
        return None

    def _format_row_value(self, record, fname):
        field = record._fields[fname]
        value = record[fname]
        if field.type == "monetary":
            return self._fmt_money(value)
        if field.type == "float":
            return self._fmt_qty(value) if float(value or 0).is_integer() else self._fmt_money(value)
        if field.type == "integer":
            return str(value or 0)
        if field.type == "boolean":
            return "ใช่" if value else ""
        if field.type in ("date", "datetime"):
            return self._format_thai_date(value) if value else ""
        if field.type == "selection":
            selection = dict(field._description_selection(record.env))
            return str(selection.get(value, value or ""))
        if field.type == "many2one":
            return self._clean_record_display(value) if value else ""
        if field.type in ("one2many", "many2many"):
            return ", ".join(self._clean_record_display(item) for item in value)
        return re.sub(r"^\s*\[[^\]]+\]\s*", "", str(value)).strip() if value else ""

    def _row_name(self, sub):
        if "product_id" in sub._fields and (sub.product_id or sub.name):
            return self._clean_product_line_name(sub)
        if "name" in sub._fields and sub.name:
            return str(sub.name).strip()
        return self._clean_record_display(sub)

    def _row_dict(self, sub, index, wanted=()):
        """Values for one table row: friendly aliases plus `line.<field>` tokens."""
        name = self._row_name(sub)
        row = {"no": str(index), "name": name, "line": name}
        amount_value = 0.0
        qty_value = 0.0
        for alias, candidates in self._ROW_ALIASES.items():
            fname = self._first_field(sub, candidates)
            row[alias] = self._format_row_value(sub, fname) if fname else ""
            if fname and sub._fields[fname].type in ("float", "monetary", "integer"):
                if alias == "amount":
                    amount_value = float(sub[fname] or 0.0)
                elif alias == "qty":
                    qty_value = float(sub[fname] or 0.0)
        if not row["unit_price"] and qty_value:
            row["unit_price"] = self._fmt_money(amount_value / qty_value)
        row["amount_value"] = amount_value
        for fname in wanted:
            if fname in sub._fields:
                row["line.%s" % fname] = self._format_row_value(sub, fname)
        return row

    def _relation_rows(self, value, wanted=()):
        """Structured rows (lines of the chosen record) for repeating table rows."""
        self.ensure_one()
        record = self._record_from_value(value)
        if not record:
            return []
        subs = self._row_source_records(record)
        if "product_qty" in subs._fields and "product_id" in subs._fields:
            subs = subs.filtered(lambda line: line.product_qty or line.name or line.product_id)
        return [
            self._row_dict(sub, index, wanted)
            for index, sub in enumerate(subs, start=1)
        ]

    def _format_many2one_value(self, value):
        self.ensure_one()
        mode = self.relation_source or "pr_lines_name_only"
        target_model = (
            self.map_model_id.model
            if self.map_model_id
            else "purchase.request"
        )
        if isinstance(value, dict):
            if value.get("text"):
                return str(value["text"])
            rec_id = value.get("res_id") or value.get("id")
            if rec_id and target_model in self.env:
                rec = self.env[target_model].sudo().browse(int(rec_id))
                if self.map_field_id:
                    mapped = self.extract_mapped_record_value(rec)
                    if mapped is not None:
                        return str(mapped)
                if target_model == "purchase.request":
                    return self._format_pr_lines_text(rec, mode=mode)
                return self._clean_record_display(rec)
            return ""
        if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
            if target_model in self.env:
                rec = self.env[target_model].sudo().browse(int(value))
                if self.map_field_id:
                    mapped = self.extract_mapped_record_value(rec)
                    if mapped is not None:
                        return str(mapped)
                if target_model == "purchase.request":
                    return self._format_pr_lines_text(rec, mode=mode)
                return self._clean_record_display(rec)
        return str(value)

    def _many2one_choices(self):
        self.ensure_one()
        if self.field_type != "many2one":
            return []
        target_model = (
            self.map_model_id.model
            if self.map_model_id
            else "purchase.request"
        )
        if target_model not in self.env:
            return []
        records = (
            self.env[target_model]
            .sudo()
            .search([], order="id desc", limit=80)
        )
        choices = []
        for rec in records:
            if self.map_field_id:
                preview = str(self.extract_mapped_record_value(rec) or "")
            elif target_model == "purchase.request":
                preview = self._format_pr_lines_text(
                    rec, mode=self.relation_source or "pr_lines_name_only"
                )
            else:
                preview = self._clean_record_display(rec)
            label = rec.display_name or ("%s#%s" % (target_model, rec.id))
            if target_model == "purchase.request":
                dept = rec.department_id.name if "department_id" in rec._fields and rec.department_id else ""
                line_count = len(
                    rec.line_ids.filtered(lambda l: not getattr(l, "cancelled", False))
                )
                label = "%s%s (%s รายการ)" % (
                    rec.name or ("PR#%s" % rec.id),
                    (" - %s" % dept) if dept else "",
                    line_count,
                )
            choices.append(
                {
                    "id": rec.id,
                    "label": label,
                    "preview": preview,
                }
            )
        return choices

    def _schema_dict(self):
        self.ensure_one()
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "field_type": self.field_type,
            "relation_source": self.relation_source or "pr_lines_name_only",
            "map_model": self.map_model_id.model if self.map_model_id else "",
            "map_model_label": self.map_model_id.name if self.map_model_id else "",
            "map_field": self.map_field_id.name if self.map_field_id else "",
            "map_sub_field": self.map_sub_field_id.name if self.map_sub_field_id else "",
            "required": bool(self.required),
            "help": self.help or "",
            "options": self.option_list() if self.field_type == "selection" else [],
            "m2o_choices": self._many2one_choices() if self.field_type == "many2one" else [],
            "default": self._parsed_default(),
            "display_template": self.display_template or "",
            "placeholder_hint": self.placeholder_hint or "",
        }

    @api.model
    def _format_thai_date(self, value):
        date_value = value
        if isinstance(value, str):
            try:
                date_value = fields.Date.from_string(value[:10])
            except (TypeError, ValueError):
                return value
        if not date_value:
            return ""
        month = THAI_MONTHS[date_value.month] if 1 <= date_value.month <= 12 else ""
        return "%s %s %s" % (date_value.day, month, date_value.year + 543)
