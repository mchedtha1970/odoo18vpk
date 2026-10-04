# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

CHEQUE_DPI = 96


class VpkBankChequeAttribute(models.Model):
    _name = "vpk.bank.cheque.attribute"
    _description = "รายการที่พิมพ์บนเช็ค"
    _order = "name"

    name = fields.Char(string="ชื่อ", required=True, translate=True)
    attribute = fields.Selection(
        [
            ("cheque_date", "วันที่"),
            ("pay_line1", "ผู้รับเงิน บรรทัด 1"),
            ("pay_line2", "ผู้รับเงิน บรรทัด 2"),
            ("amount_line_1", "จำนวนเงินตัวอักษร บรรทัด 1"),
            ("amount_line_2", "จำนวนเงินตัวอักษร บรรทัด 2"),
            ("amount_box", "ช่องจำนวนเงิน"),
            ("account_number", "เลขที่บัญชี"),
            ("ac_pay", "ขีดคร่อม A/C Pay"),
        ],
        string="ชนิด",
        required=True,
    )
    demo_data = fields.Char(string="ข้อความตัวอย่าง")
    demo_data_date = fields.Date(
        string="วันที่ตัวอย่าง",
        default=fields.Date.context_today,
    )
    date_format = fields.Selection(
        [
            ("ddMMyyyy", "วันเดือนปี ค.ศ. ติดกัน"),
            ("MMddyyyy", "เดือนวันปี ค.ศ. ติดกัน"),
            ("ddMMyyyyBE", "วันเดือนปี พ.ศ. ติดกัน"),
        ],
        string="รูปแบบวันที่",
        default="ddMMyyyy",
    )

    def format_date_value(self, date_value):
        self.ensure_one()
        if not date_value:
            return ""
        cheque_date = fields.Date.to_date(date_value)
        year = cheque_date.year + 543 if self.date_format == "ddMMyyyyBE" else cheque_date.year
        day = f"{cheque_date.day:02d}"
        month = f"{cheque_date.month:02d}"
        year_text = f"{year:04d}"
        if self.date_format == "MMddyyyy":
            return f"{month}{day}{year_text}"
        return f"{day}{month}{year_text}"


class VpkBankChequeTemplate(models.Model):
    _name = "vpk.bank.cheque.template"
    _description = "แบบฟอร์มเช็ค"
    _order = "name"

    name = fields.Char(string="ชื่อแบบเช็ค", required=True)
    bank_id = fields.Many2one("res.bank", string="ธนาคาร", required=True)
    active = fields.Boolean(default=True)
    cheque_image = fields.Image(string="ภาพเช็ค")
    cheque_height = fields.Float(string="ความสูง", default=93, required=True)
    cheque_width = fields.Float(string="ความกว้าง", default=203, required=True)
    measure_unit = fields.Selection(
        [("mm", "มิลลิเมตร"), ("cm", "เซนติเมตร"), ("in", "นิ้ว")],
        string="หน่วยวัด",
        default="mm",
        required=True,
    )
    max_char_in_line1 = fields.Integer(
        string="จำนวนตัวอักษรสูงสุดบรรทัดแรก",
        help="ใช้ตัดจำนวนเงินตัวอักษรขึ้นบรรทัดที่ 2 เมื่อแบบเช็คมีทั้งสองบรรทัด",
    )
    line_ids = fields.One2many(
        "vpk.bank.cheque.attribute.line",
        "template_id",
        string="ตำแหน่งบนเช็ค",
    )
    page_width_mm = fields.Float(compute="_compute_page_mm")
    page_height_mm = fields.Float(compute="_compute_page_mm")
    cheque_width_px = fields.Integer(compute="_compute_page_mm")
    cheque_height_px = fields.Integer(compute="_compute_page_mm")

    @api.depends("cheque_width", "cheque_height", "measure_unit")
    def _compute_page_mm(self):
        factor = {"mm": 1.0, "cm": 10.0, "in": 25.4}
        for template in self:
            width_mm = (template.cheque_width or 0.0) * factor[template.measure_unit or "mm"]
            height_mm = (template.cheque_height or 0.0) * factor[template.measure_unit or "mm"]
            template.page_width_mm = width_mm
            template.page_height_mm = height_mm
            template.cheque_width_px = int(round(width_mm / 25.4 * CHEQUE_DPI))
            template.cheque_height_px = int(round(height_mm / 25.4 * CHEQUE_DPI))

    def _apply_cheque_paperformat(self):
        self.ensure_one()
        if self.page_width_mm <= 0 or self.page_height_mm <= 0:
            raise UserError(_("กำหนดความกว้างและความสูงของเช็คก่อนพิมพ์"))
        paperformat = self.env.ref("vpk_cheque_management.paperformat_bank_cheque")
        paperformat.sudo().write({
            "format": "custom",
            "page_width": self.page_width_mm,
            "page_height": self.page_height_mm,
            "orientation": "Portrait",
            "margin_top": 0,
            "margin_bottom": 0,
            "margin_left": 0,
            "margin_right": 0,
            "header_spacing": 0,
            "dpi": CHEQUE_DPI,
        })

    def action_open_layout(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("เพิ่มรายการบนเช็คก่อน แล้วจึงจัดตำแหน่ง"))
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": "/vpk/cheque/layout/%s" % self.id,
        }

    def action_preview_cheque(self):
        self.ensure_one()
        self._apply_cheque_paperformat()
        return self.env.ref(
            "vpk_cheque_management.action_report_cheque_preview"
        ).report_action(self)

    def preview_line_value(self, line):
        self.ensure_one()
        attribute = line.attribute_id
        if attribute.attribute == "cheque_date":
            return attribute.format_date_value(
                attribute.demo_data_date or fields.Date.context_today(self)
            )
        if attribute.attribute == "ac_pay":
            return "A/C Pay"
        return attribute.demo_data or ""


class VpkBankChequeAttributeLine(models.Model):
    _name = "vpk.bank.cheque.attribute.line"
    _description = "ตำแหน่งรายการบนเช็ค"
    _order = "id"

    template_id = fields.Many2one(
        "vpk.bank.cheque.template",
        string="แบบเช็ค",
        required=True,
        ondelete="cascade",
    )
    attribute_id = fields.Many2one(
        "vpk.bank.cheque.attribute",
        string="รายการ",
        required=True,
    )
    font_size = fields.Integer(string="ขนาดตัวอักษร", default=20)
    font_family = fields.Char(string="แบบอักษร")
    letter_spacing = fields.Integer(string="ระยะห่างตัวอักษร", default=0)
    top_displacement = fields.Integer(string="ระยะจากขอบบน")
    left_displacement = fields.Integer(string="ระยะจากขอบซ้าย")
    bottom_displacement = fields.Integer(string="ระยะจากขอบล่าง")
    right_displacement = fields.Integer(string="ระยะจากขอบขวา")
    height = fields.Integer(string="ความสูง")
    width = fields.Integer(string="ความกว้าง")

    @api.onchange("attribute_id")
    def _onchange_attribute_id(self):
        if self.attribute_id.attribute == "cheque_date" and not self.letter_spacing:
            self.letter_spacing = 12

    def action_reset_position(self):
        self.write({
            "top_displacement": 0,
            "left_displacement": 0,
            "bottom_displacement": 0,
            "right_displacement": 0,
            "height": 0,
            "width": 0,
        })
