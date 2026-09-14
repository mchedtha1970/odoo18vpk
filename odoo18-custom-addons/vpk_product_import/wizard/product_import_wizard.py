# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None


# Canonical Excel headers (row 1). Thai aliases accepted on import.
COLUMN_MAP = {
    "default_code": ["default_code", "รหัสสินค้า", "code", "sku"],
    "name": ["name", "ชื่อสินค้า", "product_name"],
    "egp_purchase_name": [
        "egp_purchase_name",
        "ชื่อสำหรับซื้อ e-gp",
        "ชื่อสำหรับซื้อใน e-gp",
        "ชื่อสำหรับซื้อ e-GP",
        "egp_name",
    ],
    "categ_path": ["categ_path", "หมวดหมู่", "category", "categ"],
    "uom": ["uom", "หน่วยนับ", "หน่วยวัด", "uom_id"],
    "uom_po": ["uom_po", "หน่วยซื้อ", "uom_po_id"],
    "type": ["type", "ประเภท"],
    "is_storable": ["is_storable", "เก็บสต็อก", "storable"],
    "tracking": ["tracking", "ติดตาม", "lot_tracking"],
    "use_expiration_date": [
        "use_expiration_date",
        "expiration",
        "expire",
        "วันหมดอายุ",
        "เปิดวันหมดอายุ",
    ],
    "expiration_time": [
        "expiration_time",
        "อายุวัน",
        "จำนวนวันหมดอายุ",
        "shelf_life_days",
    ],
    "use_time": ["use_time", "best_before_days"],
    "removal_time": ["removal_time", "removal_days"],
    "alert_time": ["alert_time", "alert_days"],
    "purchase_ok": ["purchase_ok", "ซื้อได้", "can_purchase"],
    "sale_ok": ["sale_ok", "ขายได้", "can_sale", "can_sell"],
    "purchase_method": [
        "purchase_method",
        "control_policy",
        "นโยบายการสั่งซื้อ",
        "นโยบายซื้อ",
        "นโยบายควบคุม",
    ],
    "list_price": ["list_price", "ราคาขาย", "sale_price"],
    "standard_price": ["standard_price", "ต้นทุน", "cost"],
    "barcode": ["barcode", "บาร์โค้ด"],
    "description": ["description", "รายละเอียด", "note"],
}

BOOL_TRUE = {"1", "true", "yes", "y", "t", "x", "ใช่", "จริง"}
BOOL_FALSE = {"0", "false", "no", "n", "f", "ไม่", "เท็จ", ""}

TYPE_MAP = {
    "consu": "consu",
    "consumable": "consu",
    "goods": "consu",
    "สินค้า": "consu",
    "service": "service",
    "บริการ": "service",
    "combo": "combo",
    # legacy Odoo ≤16
    "product": "consu",
    "stockable": "consu",
}

TRACKING_MAP = {
    "none": "none",
    "no": "none",
    "ไม่ติดตาม": "none",
    "": "none",
    "lot": "lot",
    "lots": "lot",
    "โดยล็อต": "lot",
    "ล็อต": "lot",
    "serial": "serial",
    "โดยหมายเลขซีเรียล": "serial",
    "ซีเรียล": "serial",
}

# Control Policy / นโยบายควบคุมบิลซื้อ
PURCHASE_METHOD_MAP = {
    "receive": "receive",
    "received": "receive",
    "on received quantities": "receive",
    "ตามจำนวนที่รับ": "receive",
    "รับเข้า": "receive",
    "purchase": "purchase",
    "ordered": "purchase",
    "on ordered quantities": "purchase",
    "ตามจำนวนที่สั่ง": "purchase",
    "สั่งซื้อ": "purchase",
}


class ProductImportWizard(models.TransientModel):
    _name = "vpk.product.import.wizard"
    _description = "Import Product Master"
    # Keep wizard long enough for users to fill the Excel template after download.
    # Default TransientModel vacuum (~1h) deletes the open dialog and causes
    # "Record does not exist ... ID: N" when clicking Import later.
    _transient_max_hours = 72.0
    _transient_max_count = 200

    data_file = fields.Binary(string="Excel File", attachment=False)
    filename = fields.Char(string="Filename")
    import_mode = fields.Selection(
        [
            ("upsert", "Create new + Update existing (by default_code)"),
            ("create", "Create only (skip if default_code exists)"),
            ("update", "Update only (skip if default_code not found)"),
        ],
        string="Import Mode",
        default="upsert",
        required=True,
        help="How to handle rows when Internal Reference (default_code) already exists.",
    )
    update_existing = fields.Boolean(
        string="Update existing products",
        default=True,
        help="Deprecated: use Import Mode instead.",
    )
    create_missing_category = fields.Boolean(
        string="Create missing categories",
        default=False,
        help="If category path is not found, create the missing nodes.",
    )
    enable_expiration_date = fields.Boolean(
        string="Enable Expiration Date",
        default=False,
        help="Default: turn on Expiration Date for imported products "
        "(when Excel column is blank). Requires lot/serial tracking.",
    )
    default_expiration_time = fields.Integer(
        string="Default Expiration Days",
        default=0,
        help="Default number of days after receipt until expiration "
        "(used when Excel expiration_time is blank).",
    )
    default_purchase_method = fields.Selection(
        [
            ("receive", "On received quantities"),
            ("purchase", "On ordered quantities"),
        ],
        string="Purchase Control Policy",
        default="receive",
        help="Default bill control policy for imported products "
        "(when Excel purchase_method is blank).\n"
        "On received quantities: bill based on received qty.\n"
        "On ordered quantities: bill based on ordered qty.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        default="draft",
    )
    log_text = fields.Text(string="Import Log", readonly=True)
    created_count = fields.Integer(readonly=True)
    updated_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    error_count = fields.Integer(readonly=True)

    # -------------------------------------------------------------------------
    # Template download
    # -------------------------------------------------------------------------
    def action_download_template(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(_("Missing Python library: xlsxwriter"))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#1F4E79",
                "font_color": "white",
                "border": 1,
            }
        )
        sample_fmt = workbook.add_format({"border": 1})
        note_fmt = workbook.add_format({"italic": True, "font_color": "#666666"})

        # --- Products sheet ---
        ws = workbook.add_worksheet("Products")
        headers = [
            "default_code",
            "name",
            "egp_purchase_name",
            "categ_path",
            "uom",
            "uom_po",
            "type",
            "is_storable",
            "tracking",
            "use_expiration_date",
            "expiration_time",
            "use_time",
            "removal_time",
            "alert_time",
            "purchase_ok",
            "sale_ok",
            "purchase_method",
            "list_price",
            "standard_price",
            "barcode",
            "description",
        ]
        widths = [
            14, 36, 36, 40, 12, 12, 10, 12, 10,
            18, 14, 10, 12, 10,
            12, 10, 16,
            12, 14, 16, 30,
        ]
        for col, (h, w) in enumerate(zip(headers, widths)):
            ws.write(0, col, h, header_fmt)
            ws.set_column(col, col, w)

        samples = [
            [
                "3012815",
                "Syringe Dispos 10ml",
                "Syringe Disposable 10 ml",
                "All / กลุ่มพัสดุ / 2.เวชภัณฑ์มิใช่ยา",
                "อัน",
                "กล่อง-100",
                "consu",
                "1",
                "lot",
                "1",
                "365",
                "30",
                "15",
                "7",
                "1",
                "1",
                "receive",
                "1.00",
                "1.71",
                "",
                "",
            ],
            [
                "DEMO-001",
                "ตัวอย่างสินค้าทั่วไป",
                "ตัวอย่างสินค้าทั่วไป (e-GP)",
                "All / กลุ่มพัสดุ / 5.วัสดุทั่วไป",
                "หน่วย",
                "หน่วย",
                "consu",
                "1",
                "none",
                "0",
                "",
                "",
                "",
                "",
                "1",
                "1",
                "purchase",
                "10",
                "8",
                "",
                "ตัวอย่าง",
            ],
        ]
        for r, row in enumerate(samples, start=1):
            for c, val in enumerate(row):
                ws.write(r, c, val, sample_fmt)

        ws.write(
            4,
            0,
            "หมายเหตุ: default_code = รหัสอ้างอิงภายใน (upsert key) | "
            "egp_purchase_name = ชื่อสำหรับซื้อใน e-GP | "
            "categ_path = path เต็มของหมวดหมู่ | "
            "type = consu/service | is_storable/tracking/purchase_ok/sale_ok/"
            "use_expiration_date = 1 หรือ 0 | "
            "tracking = none/lot/serial | "
            "expiration_time/use_time/removal_time/alert_time = จำนวนวัน | "
            "purchase_method = receive (ตามจำนวนที่รับ) หรือ purchase (ตามจำนวนที่สั่ง)",
            note_fmt,
        )

        # --- Categories reference ---
        ws_categ = workbook.add_worksheet("Categories")
        ws_categ.write(0, 0, "categ_path", header_fmt)
        ws_categ.set_column(0, 0, 50)
        categories = self.env["product.category"].search([], order="complete_name")
        for i, categ in enumerate(categories, start=1):
            ws_categ.write(i, 0, categ.complete_name)

        # --- UoM reference ---
        ws_uom = workbook.add_worksheet("UoM")
        ws_uom.write(0, 0, "uom_name", header_fmt)
        ws_uom.write(0, 1, "category", header_fmt)
        ws_uom.set_column(0, 0, 30)
        ws_uom.set_column(1, 1, 30)
        uoms = self.env["uom.uom"].search([], order="name")
        for i, uom in enumerate(uoms, start=1):
            ws_uom.write(i, 0, uom.display_name)
            ws_uom.write(i, 1, uom.category_id.display_name)

        workbook.close()
        content = output.getvalue()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "vpk_product_master_template.xlsx",
                "type": "binary",
                "datas": base64.b64encode(content),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "new",
        }

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        if not self.exists():
            raise UserError(
                _(
                    "หน้าต่าง Import หมดอายุแล้ว (ถูกปิดอัตโนมัติ)\n"
                    "กรุณาปิดหน้าต่างนี้ แล้วเปิด Import Product Master ใหม่ "
                    "จากนั้นอัปโหลดไฟล์และกด Import อีกครั้ง"
                )
            )
        if not self.data_file:
            raise UserError(_("Please upload an Excel file (.xlsx)."))
        if not openpyxl:
            raise UserError(_("Missing Python library: openpyxl"))

        rows = self._read_xlsx_rows()
        if not rows:
            raise UserError(_("No data rows found in the Excel file."))

        created = updated = skipped = errors = 0
        logs = []
        # Keep backward compatibility if old clients still send update_existing only
        mode = self.import_mode or (
            "upsert" if self.update_existing else "create"
        )
        Product = self.env["product.template"].with_context(
            tracking_disable=True,
            mail_create_nolog=True,
            mail_notrack=True,
        )

        for row_no, raw in rows:
            try:
                vals, code = self._prepare_product_vals(raw)
                existing = self._find_existing_product(code, Product)
                if existing:
                    if mode == "create":
                        skipped += 1
                        logs.append(
                            _("Row %s: skipped existing %s (create-only mode)")
                            % (row_no, code)
                        )
                        continue
                    self._update_existing_product(existing, vals, raw)
                    updated += 1
                    logs.append(
                        _("Row %s: updated %s (id=%s)")
                        % (row_no, code, existing.id)
                    )
                else:
                    if mode == "update":
                        skipped += 1
                        logs.append(
                            _("Row %s: skipped missing %s (update-only mode)")
                            % (row_no, code)
                        )
                        continue
                    # standard_price is related/computed on template; set after create
                    cost = vals.pop("standard_price", None)
                    barcode = (
                        str(raw["barcode"]).strip() if raw.get("barcode") else False
                    )
                    product = Product.create(vals)
                    if cost is not None and product.product_variant_ids:
                        product.product_variant_ids[0].with_context(
                            disable_auto_svl=True
                        ).standard_price = cost
                    if barcode and product.product_variant_ids:
                        product.product_variant_ids[0].barcode = barcode
                    # Ensure variant default_code matches template code
                    if product.product_variant_ids and not product.product_variant_ids[
                        0
                    ].default_code:
                        product.product_variant_ids[0].default_code = code
                    created += 1
                    logs.append(
                        _("Row %s: created %s (id=%s)")
                        % (row_no, code, product.id)
                    )
            except Exception as exc:
                errors += 1
                msg = _("Row %s: ERROR — %s") % (row_no, exc)
                logs.append(msg)
                _logger.warning("Product import row %s failed: %s", row_no, exc)

        summary = _(
            "Import finished: created=%(c)s, updated=%(u)s, skipped=%(s)s, errors=%(e)s"
        ) % {
            "c": created,
            "u": updated,
            "s": skipped,
            "e": errors,
        }
        self.write(
            {
                "state": "done",
                "created_count": created,
                "updated_count": updated,
                "skipped_count": skipped,
                "error_count": errors,
                "log_text": summary + "\n\n" + "\n".join(logs),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _normalize_default_code(self, value):
        """Normalize Excel cell to clean default_code string.

        Excel often stores numeric codes as float (3012815.0) which would not
        match existing '3012815' without normalization.
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            return str(value).strip()
        text = str(value).strip()
        # "3012815.0" from text-exported floats
        if text.endswith(".0") and text.replace(".", "", 1).isdigit():
            try:
                return str(int(float(text)))
            except ValueError:
                pass
        return text

    def _find_existing_product(self, code, Product=None):
        """Find product.template by default_code on template or variant."""
        Product = Product or self.env["product.template"]
        if not code:
            return Product.browse()
        # Include archived so we update instead of creating a duplicate code
        ProductAll = Product.with_context(active_test=False)
        existing = ProductAll.search([("default_code", "=", code)], limit=1)
        if existing:
            return existing
        variant = (
            self.env["product.product"]
            .with_context(active_test=False)
            .search([("default_code", "=", code)], limit=1)
        )
        return variant.product_tmpl_id if variant else Product.browse()

    def _update_existing_product(self, existing, vals, raw):
        """Update an existing product template from import vals."""
        write_vals = dict(vals)
        # Avoid UoM / tracking changes that stock forbids on used products
        has_moves = self.env["stock.move"].sudo().search_count(
            [("product_id", "in", existing.product_variant_ids.ids)],
            limit=1,
        )
        if has_moves:
            for key in ("uom_id", "uom_po_id", "is_storable", "tracking", "type"):
                write_vals.pop(key, None)

        cost = write_vals.pop("standard_price", None)
        write_vals["default_code"] = vals.get("default_code") or existing.default_code

        if write_vals:
            existing.write(write_vals)
        if cost is not None and existing.product_variant_ids:
            existing.product_variant_ids[0].with_context(
                disable_auto_svl=True
            ).standard_price = cost
        if raw.get("barcode") not in (None, ""):
            existing.product_variant_ids[:1].write(
                {"barcode": str(raw["barcode"]).strip()}
            )
        # Sync variant internal reference (single-variant products)
        code = vals.get("default_code")
        if code and len(existing.product_variant_ids) == 1:
            variant = existing.product_variant_ids[0]
            if variant.default_code != code:
                variant.default_code = code

    # -------------------------------------------------------------------------
    # Parsers / helpers
    # -------------------------------------------------------------------------
    def _read_xlsx_rows(self):
        raw = base64.b64decode(self.data_file)
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        # Prefer sheet named Products; else first sheet
        if "Products" in wb.sheetnames:
            ws = wb["Products"]
        else:
            ws = wb[wb.sheetnames[0]]

        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return []

        col_index = self._map_headers(header_row)
        if "default_code" not in col_index or "name" not in col_index:
            raise UserError(
                _("Excel must contain columns default_code and name (or Thai aliases).")
            )

        result = []
        for idx, row in enumerate(rows_iter, start=2):
            if not row or all(c is None or str(c).strip() == "" for c in row):
                continue
            data = {}
            for field, col in col_index.items():
                if col < len(row):
                    data[field] = row[col]
            # Skip note/instruction rows
            code = data.get("default_code")
            if code is None or str(code).strip() == "":
                continue
            if str(code).strip().startswith("หมายเหตุ"):
                continue
            result.append((idx, data))
        return result

    def _map_headers(self, header_row):
        normalized = []
        for cell in header_row:
            if cell is None:
                normalized.append("")
            else:
                normalized.append(str(cell).strip().lower())

        col_index = {}
        for field, aliases in COLUMN_MAP.items():
            for alias in aliases:
                alias_l = alias.lower()
                if alias_l in normalized:
                    col_index[field] = normalized.index(alias_l)
                    break
        return col_index

    def _prepare_product_vals(self, raw):
        code = self._normalize_default_code(raw.get("default_code"))
        name = str(raw.get("name") or "").strip()
        if not code:
            raise UserError(_("default_code is required"))
        if not name:
            raise UserError(_("name is required"))

        uom = self._find_uom(raw.get("uom"))
        if not uom:
            raise UserError(_("UoM not found: %s") % (raw.get("uom") or ""))
        uom_po = self._find_uom(raw.get("uom_po")) if raw.get("uom_po") else uom
        if not uom_po:
            raise UserError(_("Purchase UoM not found: %s") % raw.get("uom_po"))
        if uom_po.category_id != uom.category_id:
            raise UserError(
                _("UoM and Purchase UoM must be in the same category (%s vs %s)")
                % (uom.display_name, uom_po.display_name)
            )

        categ = self._find_or_create_category(raw.get("categ_path"))
        if not categ:
            raise UserError(_("Category not found: %s") % (raw.get("categ_path") or ""))

        ptype = self._parse_type(raw.get("type"))
        is_storable = self._parse_bool(raw.get("is_storable"), default=True)
        tracking = self._parse_tracking(raw.get("tracking"))
        if not is_storable and tracking != "none":
            tracking = "none"
        if ptype == "service":
            is_storable = False
            tracking = "none"

        use_expiry = self._parse_bool(
            raw.get("use_expiration_date"),
            default=bool(self.enable_expiration_date),
        )
        # Expiration date in Odoo UI requires lot/serial tracking
        if use_expiry and tracking == "none" and is_storable:
            tracking = "lot"
        if not is_storable or ptype == "service":
            use_expiry = False

        vals = {
            "default_code": code,
            "name": name,
            "categ_id": categ.id,
            "uom_id": uom.id,
            "uom_po_id": uom_po.id,
            "type": ptype,
            "is_storable": is_storable,
            "tracking": tracking,
            "purchase_ok": self._parse_bool(raw.get("purchase_ok"), default=True),
            "sale_ok": self._parse_bool(raw.get("sale_ok"), default=True),
            "list_price": self._parse_float(raw.get("list_price"), default=0.0),
        }
        if "purchase_method" in self.env["product.template"]._fields:
            vals["purchase_method"] = self._parse_purchase_method(
                raw.get("purchase_method")
            )
        if "use_expiration_date" in self.env["product.template"]._fields:
            vals["use_expiration_date"] = use_expiry
            if use_expiry:
                vals["expiration_time"] = self._parse_int(
                    raw.get("expiration_time"),
                    default=self.default_expiration_time or 0,
                )
                vals["use_time"] = self._parse_int(raw.get("use_time"), default=0)
                vals["removal_time"] = self._parse_int(
                    raw.get("removal_time"), default=0
                )
                vals["alert_time"] = self._parse_int(raw.get("alert_time"), default=0)

        if raw.get("description") not in (None, ""):
            vals["description"] = str(raw.get("description")).strip()

        if (
            "egp_purchase_name" in self.env["product.template"]._fields
            and raw.get("egp_purchase_name") not in (None, "")
        ):
            vals["egp_purchase_name"] = str(raw.get("egp_purchase_name")).strip()

        cost = raw.get("standard_price")
        if cost not in (None, ""):
            vals["standard_price"] = self._parse_float(cost, default=0.0)

        return vals, code

    def _parse_int(self, value, default=0):
        if value is None or value == "":
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip().replace(",", "")
        try:
            return int(float(text))
        except ValueError as exc:
            raise UserError(_("Invalid integer: %s") % value) from exc

    def _parse_bool(self, value, default=False):
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in BOOL_TRUE:
            return True
        if text in BOOL_FALSE:
            return False
        return default

    def _parse_float(self, value, default=0.0):
        if value is None or value == "":
            return default
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        try:
            return float(text)
        except ValueError as exc:
            raise UserError(_("Invalid number: %s") % value) from exc

    def _parse_type(self, value):
        if value is None or str(value).strip() == "":
            return "consu"
        key = str(value).strip().lower()
        if key not in TYPE_MAP:
            raise UserError(_("Invalid type '%s' (use consu or service)") % value)
        return TYPE_MAP[key]

    def _parse_tracking(self, value):
        if value is None:
            return "none"
        key = str(value).strip().lower()
        if key not in TRACKING_MAP:
            raise UserError(
                _("Invalid tracking '%s' (use none, lot or serial)") % value
            )
        return TRACKING_MAP[key]

    def _parse_purchase_method(self, value):
        if value is None or str(value).strip() == "":
            return self.default_purchase_method or "receive"
        key = str(value).strip().lower()
        if key not in PURCHASE_METHOD_MAP:
            raise UserError(
                _(
                    "Invalid purchase_method '%s' "
                    "(use receive = On received quantities, "
                    "or purchase = On ordered quantities)"
                )
                % value
            )
        return PURCHASE_METHOD_MAP[key]

    def _uom_name_variants(self, name):
        """Return possible display/name variants for lookup."""
        text = str(name).strip()
        variants = {text, text.lower()}
        # "กล่อง [100 อัน]" <-> "กล่อง-100"
        if "[" in text and "]" in text:
            variants.add(text.replace(" [", "-").replace("]", "").replace(" ", ""))
        if "-" in text:
            parts = text.split("-", 1)
            if len(parts) == 2:
                variants.add("%s [%s]" % (parts[0].strip(), parts[1].strip()))
        return variants

    def _find_uom(self, name):
        if not name or str(name).strip() == "":
            return self.env["uom.uom"]
        text = str(name).strip()
        Uom = self.env["uom.uom"]
        # Exact name (any language stored in JSON)
        uom = Uom.search([("name", "=", text)], limit=1)
        if uom:
            return uom
        # Case-insensitive / display_name match
        for candidate in Uom.search([]):
            names = set()
            if isinstance(candidate.name, str):
                names.add(candidate.name)
            # translated
            names.add(candidate.with_context(lang="th_TH").name)
            names.add(candidate.with_context(lang="en_US").name)
            names.add(candidate.display_name)
            for variant in self._uom_name_variants(text):
                if variant in names or variant.lower() in {n.lower() for n in names if n}:
                    return candidate
        return Uom

    def _find_or_create_category(self, path):
        Category = self.env["product.category"]
        if not path or str(path).strip() == "":
            return Category.search([("parent_id", "=", False)], limit=1)

        path = str(path).strip()
        # Exact complete_name
        categ = Category.search([("complete_name", "=", path)], limit=1)
        if categ:
            return categ
        # Try without leading "All / "
        if path.startswith("All / "):
            categ = Category.search([("complete_name", "=", path)], limit=1)
            if categ:
                return categ
        # Leaf name only
        leaf = path.split("/")[-1].strip()
        categ = Category.search([("name", "=", leaf)], limit=1)
        if categ:
            return categ

        if not self.create_missing_category:
            return Category

        # Create missing path nodes
        parts = [p.strip() for p in path.split("/") if p.strip()]
        parent = Category
        current = Category
        built = []
        for part in parts:
            built.append(part)
            complete = " / ".join(built)
            found = Category.search([("complete_name", "=", complete)], limit=1)
            if not found and part == "All" and not parent:
                found = Category.search([("parent_id", "=", False)], limit=1)
            if found:
                current = found
                parent = found
                continue
            current = Category.create(
                {
                    "name": part,
                    "parent_id": parent.id if parent else False,
                }
            )
            parent = current
        return current
