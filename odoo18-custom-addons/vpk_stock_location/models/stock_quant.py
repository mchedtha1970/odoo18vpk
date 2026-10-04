import base64
from io import BytesIO

from odoo import _, models
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

COUNT_SHEET_HEADERS = [
    "id",
    "สถานที่",
    "สินค้า",
    "ล็อต/หมายเลขซีเรียล",
    "หน่วย",
    "ยอดในระบบ",
    "จำนวนที่นับได้",
]


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_validate(self):
        """แอปตรวจนับยังเรียกชื่อเมธอดของ Barcode รุ่นเก่า ซึ่ง Odoo 18 ไม่มีแล้ว"""
        quants = self.with_context(inventory_mode=True).filtered("inventory_quantity_set")
        if not quants:
            return True
        result = quants.with_context(inventory_name=_("นับจากแอปสแกน")).action_apply_inventory()
        return result or True

    def action_export_count_sheet(self):
        """ส่งออกแถวที่เลือกเป็นไฟล์ Excel สำหรับนับ แล้วนำเข้ากลับมา"""
        if xlsxwriter is None:
            raise UserError(_("ยังติดตั้ง xlsxwriter ไม่ได้"))
        quants = self.filtered(lambda quant: quant.location_id.usage in ("internal", "transit"))
        quants = quants.sorted(
            key=lambda quant: (
                quant.location_id.complete_name or "",
                quant.product_id.default_code or "",
                quant.lot_id.name or "",
                quant.id,
            )
        )
        if not quants:
            raise UserError(_(
                "เลือกแถวที่ต้องการนับก่อน "
                "กรองตำแหน่งหรือสินค้า แล้วเลือกแถว "
                "ถ้ามีหลายหน้า ให้กดเลือกทั้งหมด"
            ))
        content = quants._vpk_count_sheet_xlsx()
        attachment = self.env["ir.attachment"].create({
            "name": "ใบนับสต็อก.xlsx",
            "datas": base64.b64encode(content),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "res_model": "stock.quant",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def action_open_count_sheet_import(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("นำเข้าใบนับ"),
            "res_model": "stock.quant.count.sheet.import",
            "view_mode": "form",
            "target": "new",
        }

    def _vpk_count_sheet_xlsx(self):
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        sheet = workbook.add_worksheet("ใบนับ")
        header = workbook.add_format({"bold": True, "bg_color": "#E6F2F2", "border": 1, "locked": True})
        locked = workbook.add_format({"locked": True, "border": 1})
        locked_qty = workbook.add_format({"locked": True, "border": 1, "num_format": "#,##0.00"})
        unlocked = workbook.add_format({
            "locked": False,
            "border": 1,
            "num_format": "#,##0.00",
            "bg_color": "#FFF8E1",
        })
        note = workbook.add_format({"italic": True, "font_color": "#555555", "locked": True})
        sheet.write(0, 0, "ใส่จำนวนที่คอลัมน์จำนวนที่นับได้ แล้วบันทึกไฟล์ แถวที่เว้นว่างจะไม่ถูกปรับ", note)
        for col, title in enumerate(COUNT_SHEET_HEADERS):
            sheet.write(1, col, title, header)
        for row_index, quant in enumerate(self, start=2):
            sheet.write(row_index, 0, quant.id, locked)
            sheet.write(row_index, 1, quant.location_id.complete_name or "", locked)
            sheet.write(row_index, 2, quant.product_id.display_name or "", locked)
            sheet.write(row_index, 3, quant.lot_id.name or "", locked)
            sheet.write(row_index, 4, quant.product_uom_id.name or "", locked)
            sheet.write_number(row_index, 5, quant.quantity or 0.0, locked_qty)
            sheet.write(row_index, 6, "", unlocked)
        sheet.set_column(0, 0, None, None, {"hidden": True})
        sheet.set_column(1, 1, 28)
        sheet.set_column(2, 2, 42)
        sheet.set_column(3, 3, 22)
        sheet.set_column(4, 4, 12)
        sheet.set_column(5, 6, 16)
        sheet.freeze_panes(2, 0)
        sheet.autofilter(1, 0, max(1, 1 + len(self)), len(COUNT_SHEET_HEADERS) - 1)
        sheet.protect("", {
            "select_locked_cells": True,
            "select_unlocked_cells": True,
        })
        help_sheet = workbook.add_worksheet("คำอธิบาย")
        help_lines = [
            "1. กรองตำแหน่งหรือสินค้าบนหน้าการปรับปรุงสินค้าคงคลัง แล้วเลือกแถวก่อนกดใบนับ Excel",
            "2. แก้ได้เฉพาะช่องจำนวนที่นับได้ ช่องอื่นล็อกไว้",
            "3. แถวที่ยังไม่นับ ให้เว้นช่องจำนวนที่นับได้ว่าง ระบบจะไม่นำแถวนั้นเข้า",
            "4. อย่าลบคอลัมน์รหัสที่ถูกซ่อนไว้",
            "5. บันทึกไฟล์ แล้วกลับมากดนำเข้าใบนับ",
            "6. ยอดในระบบยังไม่เปลี่ยน จนกว่าจะตรวจส่วนต่างแล้วกดนำไปใช้",
        ]
        for index, line in enumerate(help_lines):
            help_sheet.write(index, 0, line)
        help_sheet.set_column(0, 0, 90)
        workbook.close()
        return buffer.getvalue()
