import base64
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _column_letters(ref):
    return "".join(char for char in ref if char.isalpha())


def _xlsx_rows(content):
    try:
        book = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as error:
        raise UserError(_("ไฟล์ต้องเป็น Excel .xlsx")) from error
    strings = []
    if "xl/sharedStrings.xml" in book.namelist():
        root = ET.fromstring(book.read("xl/sharedStrings.xml"))
        strings = ["".join(node.itertext()) for node in root.findall("m:si", NS)]
    sheet_name = "xl/worksheets/sheet1.xml"
    if sheet_name not in book.namelist():
        raise UserError(_("ไม่พบแผ่นงานใบนับในไฟล์"))
    sheet = ET.fromstring(book.read(sheet_name))
    rows = []
    for row in sheet.findall("m:sheetData/m:row", NS):
        values = {}
        for cell in row.findall("m:c", NS):
            ref = cell.get("r") or ""
            column = _column_letters(ref)
            kind = cell.get("t")
            node = cell.find("m:v", NS)
            if kind == "inlineStr":
                inline = cell.find("m:is", NS)
                values[column] = "".join(inline.itertext()) if inline is not None else ""
                continue
            if node is None or node.text is None:
                values[column] = ""
                continue
            if kind == "s":
                values[column] = strings[int(node.text)]
            else:
                values[column] = node.text
        rows.append(values)
    return rows


def _parse_qty(value):
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return None
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except ValueError as error:
        raise UserError(_("จำนวนที่นับได้ต้องเป็นตัวเลข ไม่ใช่ %s") % value) from error


class StockQuantCountSheetImport(models.TransientModel):
    _name = "stock.quant.count.sheet.import"
    _description = "นำเข้าใบนับสต็อก"

    data = fields.Binary(string="ไฟล์ใบนับ", required=True)
    filename = fields.Char(string="ชื่อไฟล์")
    skipped_blank = fields.Integer(string="แถวที่เว้นว่าง", readonly=True)
    line_ids = fields.One2many(
        "stock.quant.count.sheet.import.line",
        "wizard_id",
        string="รายการที่นับ",
    )

    def action_read(self):
        self.ensure_one()
        if not self.data:
            raise UserError(_("เลือกไฟล์ใบนับก่อน"))
        content = base64.b64decode(self.data)
        parsed, skipped = self._parse_count_sheet(content)
        if not parsed:
            raise UserError(_(
                "ไม่มีแถวที่ใสจำนวนที่นับได้ "
                "แถวที่เว้นว่างจะไม่ถูกนำเข้า"
            ))
        self.line_ids.unlink()
        self.write({
            "skipped_blank": skipped,
            "line_ids": [(0, 0, vals) for vals in parsed],
        })
        return self._reopen()

    def action_load_counts(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("อ่านไฟล์ก่อน แล้วยังไม่มีรายการที่นับ"))
        for line in self.line_ids:
            line.quant_id.inventory_quantity = line.counted_qty
            line.quant_id.user_id = self.env.user.id
        return {"type": "ir.actions.act_window_close"}

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _parse_count_sheet(self, content):
        rows = _xlsx_rows(content)
        header_index = None
        columns = {}
        for index, row in enumerate(rows):
            titles = {str(value).strip(): column for column, value in row.items()}
            if "id" in titles and "จำนวนที่นับได้" in titles:
                header_index = index
                columns = titles
                break
        if header_index is None:
            raise UserError(_(
                "ไม่พบหัวคอลัมน์ของใบนับ "
                "ใช้ไฟล์ที่ได้จากปุ่มใบนับ Excel"
            ))
        parsed = []
        skipped = 0
        for row in rows[header_index + 1:]:
            counted = _parse_qty(row.get(columns["จำนวนที่นับได้"]))
            if counted is None:
                if str(row.get(columns["id"]) or "").strip():
                    skipped += 1
                continue
            if counted < 0:
                raise UserError(_("จำนวนที่นับได้ต้องไม่ติดลบ"))
            raw_id = str(row.get(columns["id"]) or "").strip()
            if not raw_id:
                raise UserError(_("แถวที่ใสจำนวนแล้วไม่มีรหัสจากใบที่ส่งออก"))
            try:
                quant_id = int(float(raw_id))
            except ValueError as error:
                raise UserError(_("รหัสในใบนับไม่ถูกต้อง")) from error
            quant = self.env["stock.quant"].browse(quant_id).exists()
            if not quant or quant.location_id.usage not in ("internal", "transit"):
                raise UserError(_("ไม่พบรายการสต็อกของรหัส %s") % quant_id)
            product_cell = str(row.get(columns.get("สินค้า", ""), "") or "")
            code = quant.product_id.default_code or ""
            if product_cell and code and code not in product_cell:
                raise UserError(_(
                    "สินค้าในไฟล์ไม่ตรงกับรายการ %s"
                ) % quant.product_id.display_name)
            parsed.append({
                "quant_id": quant.id,
                "location_name": quant.location_id.complete_name,
                "product_name": quant.product_id.display_name,
                "lot_name": quant.lot_id.name or "",
                "on_hand": quant.quantity,
                "counted_qty": counted,
                "difference": counted - quant.quantity,
            })
        return parsed, skipped


class StockQuantCountSheetImportLine(models.TransientModel):
    _name = "stock.quant.count.sheet.import.line"
    _description = "รายการในใบนับสต็อก"

    wizard_id = fields.Many2one(
        "stock.quant.count.sheet.import",
        required=True,
        ondelete="cascade",
    )
    quant_id = fields.Many2one("stock.quant", string="รายการสต็อก", required=True)
    location_name = fields.Char(string="สถานที่")
    product_name = fields.Char(string="สินค้า")
    lot_name = fields.Char(string="ล็อต/หมายเลขซีเรียล")
    on_hand = fields.Float(string="ยอดในระบบ", digits="Product Unit of Measure")
    counted_qty = fields.Float(string="จำนวนที่นับได้", digits="Product Unit of Measure")
    difference = fields.Float(string="ส่วนต่าง", digits="Product Unit of Measure")
