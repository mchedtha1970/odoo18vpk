# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64
import io
import re
from datetime import date
from dateutil.relativedelta import relativedelta

import xlsxwriter
from PIL import Image

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_ILLEGAL_XML_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufdd0-\ufdef\ufffe\uffff]"
)


def _clean_excel_text(value):
    if value is None or value is False:
        return ""
    text = _ILLEGAL_XML_CHARS_RE.sub("", str(value)).strip()
    # ป้องกันกรณีข้อความขึ้นต้นด้วย '=' ทำให้ Excel มองเป็นสูตรที่ผิดพลาด
    if text.startswith(("=", "+", "-", "@")):
        text = " " + text
    return text


def _clean_sheet_title(title, used_titles):
    cleaned = _ILLEGAL_XML_CHARS_RE.sub("", str(title or "ครุภัณฑ์"))
    cleaned = re.sub(r"[\\/*?:\[\]']+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)[:28].strip() or "ครุภัณฑ์"
    candidate = cleaned
    idx = 2
    while candidate.lower() in used_titles:
        suffix = f" ({idx})"
        candidate = f"{cleaned[: 31 - len(suffix)].strip()}{suffix}"
        idx += 1
    used_titles.add(candidate.lower())
    return candidate


class VpkAssetDepreciationReportWizard(models.TransientModel):
    _name = "vpk.asset.depreciation.report.wizard"
    _description = "รายงานค่าเสื่อมประจำปีโรงพยาบาลวชิระภูเก็ต"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="หน่วยงาน",
        default=lambda self: self.env.company,
        required=True,
    )
    fiscal_year_be = fields.Char(
        string="ปีงบประมาณ (พ.ศ.)",
        default=lambda self: str(
            fields.Date.context_today(self).year
            + (1 if fields.Date.context_today(self).month >= 10 else 0)
            + 543
        ),
        required=True,
        help="เช่น 2569 — ระบบจะตั้งช่วงวันที่ 1 ต.ค. 2568 ถึง 30 ก.ย. 2569 และใช้เลขท้าย 2 หลักบนหัวคอลัมน์ (ประจำปี69 / ค่าเสื่อมสะสม69 / มูลค่าสุทธิ69)",
    )
    date_start = fields.Date(
        string="ตั้งแต่วันที่",
        required=True,
        default=lambda self: self._default_fy_dates()[0],
    )
    date_end = fields.Date(
        string="ถึงวันที่ (สิ้นงวด)",
        required=True,
        default=lambda self: self._default_fy_dates()[1],
    )
    filter_mode = fields.Selection(
        selection=[
            ("all", "แสดงทั้งหมด (ทุกประเภทครุภัณฑ์ / Asset Profile)"),
            ("by_profile", "แยกตามประเภทครุภัณฑ์ (เลือก Asset Profile)"),
        ],
        string="การเลือกประเภทครุภัณฑ์",
        default="all",
        required=True,
    )
    profile_ids = fields.Many2many(
        comodel_name="account.asset.profile",
        relation="vpk_asset_depr_report_wizard_profile_rel",
        column1="wizard_id",
        column2="profile_id",
        string="ประเภทครุภัณฑ์ (Asset Profile)",
    )
    sheet_mode = fields.Selection(
        selection=[
            ("per_profile", "แยกชีตตาม Asset Profile (1 ประเภทต่อ 1 ชีต)"),
            ("single_sheet", "รวมในชีตเดียว (แบ่งหัวกลุ่มตาม Asset Profile)"),
        ],
        string="รูปแบบชีตใน Excel",
        default="per_profile",
        required=True,
    )
    state_filter = fields.Selection(
        selection=[
            ("all", "ทั้งหมด (รวมร่างและกำลังใช้งาน)"),
            ("open_close", "เฉพาะที่ยืนยันแล้ว (กำลังใช้งาน / ปิดแล้ว)"),
        ],
        string="สถานะสินทรัพย์",
        default="all",
        required=True,
    )
    exclude_zero_value = fields.Boolean(
        string="แสดงเฉพาะรายการที่มีมูลค่ามากกว่า 0",
        default=True,
    )
    max_rows_per_profile = fields.Integer(
        string="จำกัดจำนวนรายการสูงสุดต่อประเภท (0 = ไม่จำกัด)",
        default=0,
        help="ใส่ 0 เพื่อดึงข้อมูลทั้งหมด หรือใส่จำนวนเพื่อทดสอบความเร็ว",
    )
    excel_file = fields.Binary(string="ไฟล์ Excel", readonly=True)
    excel_filename = fields.Char(string="ชื่อไฟล์ Excel", readonly=True)

    @api.model
    def _default_fy_dates(self):
        today = fields.Date.context_today(self)
        fy_ce = today.year + (1 if today.month >= 10 else 0)
        return date(fy_ce - 1, 10, 1), date(fy_ce, 9, 30)

    @api.onchange("fiscal_year_be")
    def _onchange_fiscal_year_be(self):
        raw = (self.fiscal_year_be or "").strip()
        if raw.isdigit() and len(raw) == 4:
            be_year = int(raw)
            ce_year = be_year - 543 if be_year > 2400 else be_year
            self.date_start = date(ce_year - 1, 10, 1)
            self.date_end = date(ce_year, 9, 30)

    def _short_year_suffix(self):
        raw = re.sub(r"\D", "", self.fiscal_year_be or "")
        if len(raw) >= 2:
            return raw[-2:]
        return str((self.date_end.year + 543) % 100)

    def _format_thai_date_be(self, d):
        if not d:
            return ""
        return f"{d.day:02d}/{d.month:02d}/{d.year + 543}"

    def _compute_asset_depreciation_metrics(self, asset, fy_start, fy_end):
        """คำนวณ มูลค่ารวม, อายุการใช้งาน, ค่าเสื่อมประจำปี, ค่าเสื่อมสะสม, และมูลค่าสุทธิ."""
        purchase_val = round(float(asset.purchase_value or 0.0), 2)
        salvage_val = float(
            asset.salvage_value if asset.salvage_value is not None else 1.0
        )
        if salvage_val <= 0 and purchase_val > 1.0:
            salvage_val = 1.0
        depr_base = max(round(purchase_val - salvage_val, 2), 0.0)
        life_years = int(asset.useful_life_years or asset.method_number or 0)

        depr_lines = asset.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate" and l.line_date
        )
        if depr_lines:
            annual_depr = round(
                sum(
                    l.amount
                    for l in depr_lines
                    if fy_start <= l.line_date <= fy_end
                ),
                2,
            )
            accum_depr = round(
                sum(l.amount for l in depr_lines if l.line_date <= fy_end),
                2,
            )
            if accum_depr > depr_base and depr_base > 0:
                accum_depr = depr_base
            net_val = max(
                round(purchase_val - accum_depr, 2),
                round(salvage_val, 2) if purchase_val > 0 else 0.0,
            )
            return purchase_val, life_years, annual_depr, accum_depr, net_val

        start_d = asset.acquisition_date or asset.date_start
        if not start_d or life_years <= 0 or depr_base <= 0:
            return purchase_val, life_years, 0.0, 0.0, purchase_val

        end_d = start_d + relativedelta(years=life_years)
        if start_d > fy_end:
            return purchase_val, life_years, 0.0, 0.0, purchase_val

        if end_d <= fy_start:
            return (
                purchase_val,
                life_years,
                0.0,
                depr_base,
                round(purchase_val - depr_base, 2),
            )

        total_days = max((end_d - start_d).days, 1)
        p_start = max(start_d, fy_start)
        p_end = min(end_d, fy_end)
        overlap_days = max(
            (p_end - p_start).days + (1 if p_start == start_d else 0), 0
        )
        annual_depr = min(round(depr_base * overlap_days / total_days, 2), depr_base)

        if fy_end >= end_d:
            accum_depr = depr_base
        else:
            acc_days = max((fy_end - start_d).days + 1, 0)
            accum_depr = min(round(depr_base * acc_days / total_days, 2), depr_base)

        net_val = max(round(purchase_val - accum_depr, 2), round(salvage_val, 2))
        return purchase_val, life_years, annual_depr, accum_depr, net_val

    def _get_grouped_assets_data(self):
        """ดึงข้อมูลสินทรัพย์จัดกลุ่มตาม Asset Profile (รวมกลุ่มที่มีชื่อเดียวกันเข้าด้วยกัน)."""
        self.ensure_one()
        Asset = self.env["account.asset"].sudo()
        Profile = self.env["account.asset.profile"].sudo()

        domain = [("company_id", "=", self.company_id.id)]
        if self.exclude_zero_value:
            domain.append(("purchase_value", ">", 0))
        if self.state_filter == "open_close":
            domain.append(("state", "in", ["open", "close"]))
        else:
            domain.append(("state", "!=", "removed"))

        if self.filter_mode == "by_profile":
            if not self.profile_ids:
                raise UserError(
                    _("กรุณาเลือกประเภทครุภัณฑ์ (Asset Profile) อย่างน้อย 1 ประเภท")
                )
            profiles = self.profile_ids
        else:
            profiles = Profile.search(
                [("company_id", "in", [False, self.company_id.id])],
                order="name asc, id asc",
            )

        # รวม Profile ที่มีชื่อฐานเดียวกัน (เช่น 'ครุภัณฑ์สำนักงาน' กับ 'ครุภัณฑ์สำนักงาน - Interface') เข้าเป็นกลุ่มเดียว
        grouped_profiles = {}
        profile_order = []
        for profile in profiles:
            p_name = re.sub(r"\s*-\s*Interface\s*$", "", profile.name or "").strip()
            p_name = re.sub(r"\s+", " ", p_name) or "ครุภัณฑ์"
            if p_name not in grouped_profiles:
                grouped_profiles[p_name] = []
                profile_order.append(p_name)
            grouped_profiles[p_name].append(profile.id)

        limit_per = int(self.max_rows_per_profile or 0)
        groups = []
        for p_name in profile_order:
            p_ids = grouped_profiles[p_name]
            p_domain = domain + [("profile_id", "in", p_ids)]
            assets = Asset.search(
                p_domain,
                order="code asc, number asc, id asc",
                limit=limit_per if limit_per > 0 else None,
            )
            if not assets:
                continue
            header_label = (
                p_name if p_name.startswith("ประเภท") else f"ประเภท{p_name}"
            )
            rows = []
            for idx, asset in enumerate(assets, start=1):
                p_val, life, annual, accum, net = (
                    self._compute_asset_depreciation_metrics(
                        asset, self.date_start, self.date_end
                    )
                )
                first_line_name = _clean_excel_text(
                    (asset.name or "").splitlines()[0] if asset.name else ""
                )
                sub_col = _clean_excel_text(asset.equipment_model or "")
                asset_code = _clean_excel_text(asset.number or asset.code or "")
                acq_date = asset.acquisition_date or asset.date_start
                rows.append(
                    {
                        "seq": idx,
                        "name": first_line_name,
                        "sub_col": sub_col,
                        "code": asset_code,
                        "date_str": self._format_thai_date_be(acq_date),
                        "purchase_value": p_val,
                        "life_years": life,
                        "annual_depr": annual,
                        "accum_depr": accum,
                        "net_value": net,
                    }
                )
            groups.append(
                {
                    "profile_name": _clean_excel_text(p_name),
                    "header_label": _clean_excel_text(header_label),
                    "rows": rows,
                }
            )

        if not groups:
            raise UserError(_("ไม่พบรายการสินทรัพย์ตามเงื่อนไขที่เลือก"))
        return groups

    def _get_logo_png_bytes(self):
        logo_b64 = self.company_id.logo
        if not logo_b64:
            return None
        try:
            raw = base64.b64decode(logo_b64)
            with Image.open(io.BytesIO(raw)) as im:
                im = im.convert("RGBA")
                im.thumbnail((52, 52))
                out = io.BytesIO()
                im.save(out, format="PNG")
                return out.getvalue()
        except Exception:
            return None

    def _write_profile_table_xlsxwriter(
        self, ws, start_row, group, yr_suffix, fmts, logo_bytes=None, include_main_title=True
    ):
        """เขียนตาราง 1 ประเภทครุภัณฑ์ลงใน worksheet ด้วย xlsxwriter (0-indexed rows/cols)."""
        r = start_row
        if include_main_title:
            ws.set_row(r, 28)
            ws.merge_range(
                r,
                0,
                r,
                9,
                "รายงานค่าเสื่อมประจำปีโรงพยาบาลวชิระภูเก็ต",
                fmts["title"],
            )
            ws.set_row(r + 1, 20)
            if logo_bytes:
                ws.insert_image(
                    r + 1,
                    0,
                    "logo.png",
                    {
                        "image_data": io.BytesIO(logo_bytes),
                        "x_offset": 6,
                        "y_offset": 2,
                        "object_position": 2,
                    },
                )
            r += 2

        # กรอบประเภทครุภัณฑ์ เช่น "ประเภทครุภัณฑ์สำนักงาน" ที่คอลัมน์ B (col=1)
        ws.set_row(r, 24)
        ws.write_string(r, 1, group["header_label"], fmts["cat_box"])
        r += 1

        # แถวหัวตาราง 10 คอลัมน์ (ทุกคอลัมน์มีข้อความไม่ว่าง ताकि AutoFilter ของ Excel ไม่แจ้งเตือน)
        header_row = r
        ws.set_row(header_row, 25)
        headers = [
            "ลำดับ",
            "รายการ",
            "รุ่น/รายละเอียด",
            "รหัสครุภัณฑ์",
            "วันที่",
            "มูลค่ารวม",
            "อายุการใช้งาน",
            f"ประจำปี{yr_suffix}",
            f"ค่าเสื่อมสะสม{yr_suffix}",
            f"มูลค่าสุทธิ{yr_suffix}",
        ]
        for ci, h_text in enumerate(headers):
            fmt = fmts["header_blue"] if ci >= 6 else fmts["header_white"]
            ws.write_string(header_row, ci, h_text, fmt)
        r += 1

        total_purchase = 0.0
        total_annual = 0.0
        total_accum = 0.0
        total_net = 0.0
        for row_data in group["rows"]:
            ws.set_row(r, 21)
            ws.write_number(r, 0, int(row_data["seq"]), fmts["center"])
            ws.write_string(r, 1, row_data["name"], fmts["left"])
            ws.write_string(r, 2, row_data["sub_col"], fmts["left"])
            ws.write_string(r, 3, row_data["code"], fmts["left"])
            ws.write_string(r, 4, row_data["date_str"], fmts["center"])
            ws.write_number(r, 5, float(row_data["purchase_value"]), fmts["money"])
            if row_data["life_years"]:
                ws.write_number(r, 6, int(row_data["life_years"]), fmts["center"])
            else:
                ws.write_string(r, 6, "", fmts["center"])
            ws.write_number(r, 7, float(row_data["annual_depr"]), fmts["money"])
            ws.write_number(r, 8, float(row_data["accum_depr"]), fmts["money"])
            ws.write_number(r, 9, float(row_data["net_value"]), fmts["money"])

            total_purchase += row_data["purchase_value"]
            total_annual += row_data["annual_depr"]
            total_accum += row_data["accum_depr"]
            total_net += row_data["net_value"]
            r += 1

        # แถวรวมท้ายตาราง
        ws.set_row(r, 23)
        ws.merge_range(
            r,
            0,
            r,
            4,
            f"รวม {group['header_label']} ({len(group['rows']):,} รายการ)",
            fmts["total_label"],
        )
        ws.write_number(r, 5, round(total_purchase, 2), fmts["total_money"])
        ws.write_string(r, 6, "", fmts["total_label"])
        ws.write_number(r, 7, round(total_annual, 2), fmts["total_money"])
        ws.write_number(r, 8, round(total_accum, 2), fmts["total_money"])
        ws.write_number(r, 9, round(total_net, 2), fmts["total_money"])

        return header_row, r

    def _set_sheet_columns_xlsxwriter(self, ws):
        widths = [8, 38, 16, 24, 14, 16, 14, 15, 16, 15]
        for ci, w in enumerate(widths):
            ws.set_column(ci, ci, w)

    def action_export_excel(self):
        """สร้างและดาวน์โหลดไฟล์ Excel (.xlsx) ด้วย xlsxwriter ที่ผ่านมาตรฐาน Microsoft Excel 100%."""
        self.ensure_one()
        groups = self._get_grouped_assets_data()
        yr_suffix = self._short_year_suffix()
        logo_bytes = self._get_logo_png_bytes()

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})

        font_name = "TH SarabunPSK"
        money_num_fmt = '#,##0.00;(#,##0.00);"-"'
        fmts = {
            "title": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 18,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                }
            ),
            "cat_box": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 15,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 2,
                    "border_color": "#1E6B43",
                }
            ),
            "header_white": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 15,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "bg_color": "#FFFFFF",
                }
            ),
            "header_blue": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 15,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "bg_color": "#B4C6E7",
                }
            ),
            "center": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 14,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                }
            ),
            "left": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 14,
                    "align": "left",
                    "valign": "vcenter",
                    "border": 1,
                }
            ),
            "money": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 14,
                    "align": "right",
                    "valign": "vcenter",
                    "border": 1,
                    "num_format": money_num_fmt,
                }
            ),
            "total_label": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 15,
                    "bold": True,
                    "align": "center",
                    "valign": "vcenter",
                    "border": 1,
                    "bg_color": "#EDEDED",
                }
            ),
            "total_money": wb.add_format(
                {
                    "font_name": font_name,
                    "font_size": 15,
                    "bold": True,
                    "align": "right",
                    "valign": "vcenter",
                    "border": 1,
                    "bg_color": "#EDEDED",
                    "num_format": money_num_fmt,
                }
            ),
        }

        used_titles = set()
        if self.sheet_mode == "per_profile":
            for group in groups:
                sheet_title = _clean_sheet_title(group["profile_name"], used_titles)
                ws = wb.add_worksheet(sheet_title)
                self._set_sheet_columns_xlsxwriter(ws)
                header_row, last_row = self._write_profile_table_xlsxwriter(
                    ws,
                    start_row=0,
                    group=group,
                    yr_suffix=yr_suffix,
                    fmts=fmts,
                    logo_bytes=logo_bytes,
                    include_main_title=True,
                )
                if last_row > header_row + 1:
                    ws.autofilter(header_row, 0, last_row - 1, 9)
        else:
            ws = wb.add_worksheet(f"รายงานค่าเสื่อมปี{yr_suffix}")
            self._set_sheet_columns_xlsxwriter(ws)
            current_row = 0
            first_header_row = None
            last_data_row = None
            for idx, group in enumerate(groups):
                h_row, end_row = self._write_profile_table_xlsxwriter(
                    ws,
                    start_row=current_row,
                    group=group,
                    yr_suffix=yr_suffix,
                    fmts=fmts,
                    logo_bytes=logo_bytes if idx == 0 else None,
                    include_main_title=(idx == 0),
                )
                if first_header_row is None:
                    first_header_row = h_row
                last_data_row = end_row
                current_row = end_row + 2
            if first_header_row is not None and last_data_row:
                ws.autofilter(first_header_row, 0, last_data_row, 9)

        wb.close()

        profile_tag = (
            "ทั้งหมด"
            if self.filter_mode == "all"
            else f"{len(self.profile_ids)}_ประเภท"
        )
        filename = f"รายงานค่าเสื่อมประจำปี_{self.fiscal_year_be}_{profile_tag}.xlsx"
        self.write(
            {
                "excel_file": base64.b64encode(buf.getvalue()),
                "excel_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self._name}/{self.id}/excel_file/{filename}?download=true",
            "target": "self",
        }
