# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""อ่านไฟล์ template .xls (BIFF8) แล้วคัดลอกเป็น workbook ใหม่เพื่อกรอกข้อมูล

ใช้ xlrd (อ่านพร้อม format) + xlwt (เขียน .xls) ซึ่งเป็นไลบรารีที่มากับ Odoo
คัดลอก: ค่าในเซลล์ รูปแบบ (font / border / fill / number format / alignment)
ความกว้างคอลัมน์ ความสูงแถว การรวมเซลล์ และการซ่อนชีต/คอลัมน์

ไม่คัดลอก: ปุ่ม Option/Checkbox (form control) และสูตร — สูตรจะถูกแทนด้วยค่าที่คำนวณแล้ว
"""
import functools
import io
import itertools
import re
import string
import struct

import xlrd
import xlwt
from xlrd import compdoc

_CELL_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def _password_term(index, char):
    value = ord(char) << (index + 1)
    return (value & 0x7FFF) | ((value & (0x7FFF << 15)) >> 15)


@functools.lru_cache(maxsize=None)
def password_for_hash(target_hash):
    """หาข้อความรหัสผ่านที่ให้ค่า hash (16 บิต) ตรงกับ hash เดิมใน template

    template เก็บเฉพาะ hash ของรหัสผ่านป้องกันชีต (Excel 97-2003 ตรวจรหัสด้วย hash เท่านั้น)
    จึงสร้างข้อความอื่นที่ hash ตรงกัน เพื่อให้ไฟล์ใหม่ล็อกด้วยรหัสผ่านเดียวกับ template
    (รหัสเดิมของฝ่ายการเงินยังใช้ปลดล็อกได้)
    """
    if not target_hash:
        return ""
    alphabet = string.ascii_lowercase + string.digits
    for length in (6, 7, 8):
        wanted = target_hash ^ length ^ 0xCE4B
        half = length // 2
        left = {}
        for chars in itertools.product(alphabet, repeat=half):
            value = 0
            for index, char in enumerate(chars):
                value ^= _password_term(index, char)
            left.setdefault(value, "".join(chars))
        for chars in itertools.product(alphabet, repeat=length - half):
            value = 0
            for index, char in enumerate(chars):
                value ^= _password_term(half + index, char)
            if (wanted ^ value) in left:
                return left[wanted ^ value] + "".join(chars)
    return ""


def read_sheet_protection(content):
    """อ่านค่าป้องกันชีต (PROTECT / OBJECTPROTECT / SCENPROTECT / PASSWORD) ของแต่ละชีตตามลำดับ"""
    stream = compdoc.CompDoc(content, logfile=io.StringIO()).get_named_stream("Workbook")
    result = []
    current = None
    pos = 0
    while pos + 4 <= len(stream):
        rid, length = struct.unpack("<HH", stream[pos : pos + 4])
        data = stream[pos + 4 : pos + 4 + length]
        if rid == 0x0809:  # BOF
            kind = struct.unpack("<H", data[2:4])[0] if len(data) >= 4 else 0
            current = {} if kind == 0x0010 else None  # 0x10 = worksheet
            if current is not None:
                result.append(current)
        elif current is not None and length >= 2:
            value = struct.unpack("<H", data[:2])[0]
            if rid == 0x0012:
                current["protect"] = bool(value)
            elif rid == 0x0063:
                current["obj_protect"] = bool(value)
            elif rid == 0x00DD:
                current["scen_protect"] = bool(value)
            elif rid == 0x0013:
                current["password_hash"] = value
        pos += 4 + length
    return result


def cell_to_rc(address):
    """'B13' -> (12, 1)"""
    match = _CELL_RE.match(address)
    if not match:
        raise ValueError("Invalid cell address: %s" % address)
    col = 0
    for ch in match.group(1).upper():
        col = col * 26 + ord(ch) - 64
    return int(match.group(2)) - 1, col - 1


class XlsTemplate:
    """workbook ที่คัดลอกมาจาก template พร้อมให้ set ค่าเซลล์"""

    def __init__(self, content):
        self._rb = xlrd.open_workbook(file_contents=content, formatting_info=True)
        self._wb = xlwt.Workbook(encoding="utf-8")
        self._styles = {}
        self._sheets = {}  # name -> (xlrd sheet, xlwt sheet)
        self._xf_of = {}  # (sheet, r, c) -> xlrd xf index
        self._protection = read_sheet_protection(content)
        self._copy()

    # ------------------------------------------------------------------
    # คัดลอก workbook
    # ------------------------------------------------------------------
    def _copy(self):
        rb, wb = self._rb, self._wb
        wb.dates_1904 = bool(rb.datemode)
        for idx, rgb in (rb.colour_map or {}).items():
            if rgb and 8 <= idx <= 63:
                wb.set_colour_RGB(idx, *rgb)
        for index, sheet in enumerate(rb.sheets()):
            ws = wb.add_sheet(sheet.name, cell_overwrite_ok=True)
            self._sheets[sheet.name] = (sheet, ws)
            self._copy_sheet(sheet, ws)
            if index < len(self._protection):
                self._copy_protection(ws, self._protection[index])

    @staticmethod
    def _copy_protection(ws, info):
        """ล็อกชีต (Protect Sheet) เหมือน template เดิม"""
        ws.protect = info.get("protect", False)
        ws.obj_protect = info.get("obj_protect", False)
        ws.scen_protect = info.get("scen_protect", False)
        if info.get("password_hash"):
            ws.password = password_for_hash(info["password_hash"])

    def _copy_sheet(self, sheet, ws):
        ws.visibility = sheet.visibility
        ws.show_grid = bool(sheet.show_grid_lines)
        ws.col_default_width = sheet.defcolwidth or 8
        ws.paper_size_code = 9
        ws.portrait = True
        ws.fit_num_pages = 1
        ws.fit_width_to_pages = 1
        ws.fit_height_to_pages = 1
        for colx, info in sheet.colinfo_map.items():
            col = ws.col(colx)
            col.width = info.width
            col.hidden = bool(info.hidden)
            if info.xf_index is not None and info.xf_index >= 0:
                col.set_style(self._style(info.xf_index))
        for rowx, info in sheet.rowinfo_map.items():
            row = ws.row(rowx)
            if info.height:
                row.height = info.height
                row.height_mismatch = 1
            row.hidden = bool(info.hidden)
            if info.has_default_xf_index and info.xf_index >= 0:
                row.set_style(self._style(info.xf_index))
        for rlo, rhi, clo, chi in sheet.merged_cells:
            ws._Worksheet__merged_ranges.append((rlo, rhi - 1, clo, chi - 1))
        for rowx in range(sheet.nrows):
            for colx in range(sheet.ncols):
                xf = sheet.cell_xf_index(rowx, colx)
                ctype = sheet.cell_type(rowx, colx)
                if xf is None or xf < 0:
                    if ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        continue
                    xf = 0
                self._xf_of[(sheet.name, rowx, colx)] = xf
                self._write(ws, rowx, colx, ctype, sheet.cell_value(rowx, colx), xf)

    def _write(self, ws, rowx, colx, ctype, value, xf):
        style = self._style(xf)
        if ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK, xlrd.XL_CELL_ERROR):
            ws.write(rowx, colx, None, style)
        elif ctype == xlrd.XL_CELL_BOOLEAN:
            ws.write(rowx, colx, bool(value), style)
        else:
            ws.write(rowx, colx, value, style)

    def _style(self, xf_index):
        if xf_index in self._styles:
            return self._styles[xf_index]
        rb = self._rb
        xf = rb.xf_list[xf_index]
        style = xlwt.XFStyle()

        src_font = rb.font_list[xf.font_index]
        font = xlwt.Font()
        font.name = src_font.name
        font.height = src_font.height
        font.bold = bool(src_font.bold)
        font.italic = bool(src_font.italic)
        font.underline = src_font.underline_type
        font.struck_out = bool(src_font.struck_out)
        font.escapement = src_font.escapement
        font.colour_index = src_font.colour_index
        font.family = src_font.family
        font.charset = src_font.character_set
        style.font = font

        fmt = rb.format_map.get(xf.format_key)
        style.num_format_str = fmt.format_str if fmt else "General"

        al = xlwt.Alignment()
        al.horz = xf.alignment.hor_align
        al.vert = xf.alignment.vert_align
        al.wrap = xf.alignment.text_wrapped
        al.rota = xf.alignment.rotation
        al.inde = xf.alignment.indent_level
        al.shri = xf.alignment.shrink_to_fit
        al.dire = xf.alignment.text_direction
        style.alignment = al

        bd = xlwt.Borders()
        b = xf.border
        bd.left, bd.right = b.left_line_style, b.right_line_style
        bd.top, bd.bottom = b.top_line_style, b.bottom_line_style
        bd.left_colour, bd.right_colour = b.left_colour_index, b.right_colour_index
        bd.top_colour, bd.bottom_colour = b.top_colour_index, b.bottom_colour_index
        style.borders = bd

        pat = xlwt.Pattern()
        pat.pattern = xf.background.fill_pattern
        pat.pattern_fore_colour = xf.background.pattern_colour_index
        pat.pattern_back_colour = xf.background.background_colour_index
        style.pattern = pat

        prot = xlwt.Protection()
        prot.cell_locked = xf.protection.cell_locked
        prot.formula_hidden = xf.protection.formula_hidden
        style.protection = prot

        self._styles[xf_index] = style
        return style

    # ------------------------------------------------------------------
    # กรอกข้อมูล
    # ------------------------------------------------------------------
    def set(self, sheet_name, address, value):
        """กำหนดค่าเซลล์ โดยคงรูปแบบเดิมของเซลล์ไว้ (None/'' = ล้างค่า)"""
        _sheet, ws = self._sheets[sheet_name]
        rowx, colx = cell_to_rc(address)
        xf = self._xf_of.get((sheet_name, rowx, colx), 0)
        style = self._style(xf)
        if value is None or value == "":
            ws.write(rowx, colx, None, style)
        elif isinstance(value, bool):
            ws.write(rowx, colx, value, style)
        else:
            ws.write(rowx, colx, value, style)

    def get_text(self, sheet_name, address):
        sheet, _ws = self._sheets[sheet_name]
        rowx, colx = cell_to_rc(address)
        if rowx < sheet.nrows and colx < sheet.ncols:
            return sheet.cell_value(rowx, colx)
        return ""

    def to_bytes(self):
        buf = io.BytesIO()
        self._wb.save(buf)
        return buf.getvalue()
