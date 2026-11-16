# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64
import io
import math
from pathlib import Path

import xlwt
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_FONT_CSS_CACHE = None


def _load_official_thai_font_css():
    """โหลดฟอนต์ราชการ TH Sarabun New แบบ Base64 สำหรับ wkhtmltopdf."""
    global _FONT_CSS_CACHE
    if _FONT_CSS_CACHE is None:
        font_dir = (
            Path(__file__).resolve().parents[2]
            / "l10n-thailand-18.0/l10n_th_base_utils/static/fonts/thai/THSarabunNew"
        )
        faces = []
        for family, filename, weight in (
            ("THSarabunNew", "THSarabunNew-Regular.ttf", "normal"),
            ("THSarabunNew", "THSarabunNew-Bold.ttf", "bold"),
            ("THSarabunNew-Bold", "THSarabunNew-Bold.ttf", "normal"),
        ):
            path = font_dir / filename
            if not path.exists():
                continue
            encoded = base64.b64encode(path.read_bytes()).decode()
            faces.append(
                "@font-face {"
                f'font-family: "{family}";'
                f'src: url("data:font/truetype;base64,{encoded}") format("truetype");'
                f"font-weight: {weight};"
                "font-style: normal;"
                "}"
            )
        _FONT_CSS_CACHE = "\n".join(faces)

    layout_css = """
        body, div, table, thead, tbody, tr, td, span {
            font-family: "THSarabunNew", sans-serif !important;
        }
        table.vpk-gfmis-cover {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            font-family: "THSarabunNew", sans-serif !important;
            font-size: 22px;
            line-height: 1.05;
            color: #000;
        }
        table.vpk-gfmis-cover th,
        table.vpk-gfmis-cover td {
            border: 1px solid #000;
            padding: 2px 6px;
            vertical-align: middle;
            overflow: hidden;
        }
        table.vpk-gfmis-cover thead th {
            font-family: "THSarabunNew-Bold", "THSarabunNew", sans-serif !important;
            font-weight: bold;
            text-align: center;
            height: 25px;
            font-size: 22px;
        }
        table.vpk-gfmis-cover tr.main-row td {
            height: 23px;
            font-size: 22px;
        }
        table.vpk-gfmis-cover tr.sub-row td {
            height: 19px;
            font-size: 16px;
            color: #000;
        }
        .text-center { text-align: center; }
        .text-left { text-align: left; }
        .text-right { text-align: right; }
    """
    return f"{_FONT_CSS_CACHE}\n{layout_css}"


class VpkDisbursementCoverWizard(models.TransientModel):
    _name = "vpk.disbursement.cover.wizard"
    _description = "สร้างรายงานใบปะหน้าการขออนุมัติเบิกจ่ายจาก GFMIS"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="หน่วยงาน",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date_from = fields.Date(string="ตั้งแต่วันที่")
    date_to = fields.Date(string="ถึงวันที่")
    form_type_filter = fields.Selection(
        selection=[
            ("all", "ทั้งหมด (ขบ.01 และ ขบ.11)"),
            ("kb01", "เฉพาะ ขบ.01"),
            ("kb11", "เฉพาะ ขบ.11"),
        ],
        string="แบบฟอร์ม ขบ.",
        default="all",
        required=True,
    )
    state_filter = fields.Selection(
        selection=[
            ("all", "ทั้งหมด (ที่ยังไม่ยกเลิก)"),
            ("confirmed_uploaded", "ยืนยันข้อมูลแล้ว / อัปโหลดแล้ว"),
            ("uploaded", "เฉพาะอัปโหลดกรมบัญชีกลางแล้ว"),
        ],
        string="สถานะใบขอเบิกเงิน",
        default="all",
        required=True,
    )
    page_start = fields.Integer(
        string="หน้าที่ (เริ่มต้น)",
        default=1,
        required=True,
        help="เลขหน้าที่แสดงบนหัวตาราง เช่น หน้าที่ 61",
    )
    seq_start = fields.Integer(
        string="ลำดับที่ (เริ่มต้น)",
        default=1,
        required=True,
        help="เลขลำดับที่ของรายการแรก เช่น 1 หรือ 745",
    )
    fiscal_year_be = fields.Char(
        string="ปีงบประมาณ (พ.ศ.) สำหรับเลขฎีกา",
        default=lambda self: str(fields.Date.context_today(self).year + 543),
        required=True,
        help="ใช้ต่อท้ายเลขฎีกา เช่น 0745/2570",
    )
    rows_per_page = fields.Integer(
        string="จำนวนรายการต่อหน้า",
        default=12,
        required=True,
    )
    default_sub_note = fields.Char(
        string="ข้อความบรรทัดที่ 2 (ใต้ชื่อบริษัท)",
        default="(เงินฝากคลัง 910)",
    )
    line_ids = fields.One2many(
        comodel_name="vpk.disbursement.cover.wizard.line",
        inverse_name="wizard_id",
        string="รายการในใบปะหน้า",
    )
    excel_file = fields.Binary(string="ไฟล์ Excel", readonly=True)
    excel_filename = fields.Char(string="ชื่อไฟล์ Excel", readonly=True)

    @api.model
    def _prepare_line_vals_from_form(
        self, form, index, seq_no, fiscal_year_be, default_sub_note
    ):
        bill = form.invoice_id
        bill_no = ""
        if bill:
            bill_no = bill.ref or (bill.name if bill.name != "/" else "") or ""
        if not bill_no:
            bill_no = form.reference or form.gfmis_doc_number or ""

        kb_label = "ขบ.11" if form.form_type == "kb11" else "ขบ.01"
        deeka_no = f"{seq_no:04d}/{fiscal_year_be}" if fiscal_year_be else f"{seq_no:04d}"
        partner_name = form.partner_id.name if form.partner_id else ""

        return {
            "sequence": index * 10,
            "seq_no": seq_no,
            "transfer_date": "",
            "disbursement_form_id": form.id,
            "partner_name": partner_name,
            "sub_note": default_sub_note or "(เงินฝากคลัง 910)",
            "kb_label": kb_label,
            "deeka_no": deeka_no,
            "bill_no": bill_no,
            "amount_request": form.amount_request or 0.0,
            "wht_amount": form.wht_amount if form.tax_type != "none" else 0.0,
            "amount_net": form.amount_net or 0.0,
            "approver_note": "",
        }

    def _search_matching_forms(self):
        self.ensure_one()
        domain = [("company_id", "=", self.company_id.id)]
        if self.state_filter == "uploaded":
            domain.append(("state", "=", "uploaded"))
        elif self.state_filter == "confirmed_uploaded":
            domain.append(("state", "in", ["confirmed", "uploaded"]))
        else:
            domain.append(("state", "!=", "cancel"))

        if self.form_type_filter in ("kb01", "kb11"):
            domain.append(("form_type", "=", self.form_type_filter))
        if self.date_from:
            domain.append(("document_date", ">=", self.date_from))
        if self.date_to:
            domain.append(("document_date", "<=", self.date_to))

        return (
            self.env["vpk.disbursement.form"]
            .sudo()
            .search(domain, order="document_date asc, id asc")
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        Form = self.env["vpk.disbursement.form"].sudo()
        if active_model == "vpk.disbursement.form" and active_ids:
            forms = Form.browse(active_ids).filtered(lambda f: f.state != "cancel")
        else:
            forms = Form.search(
                [("state", "!=", "cancel")],
                order="document_date asc, id asc",
                limit=60,
            )

        seq_start = res.get("seq_start") or 1
        fy = res.get("fiscal_year_be") or str(
            fields.Date.context_today(self).year + 543
        )
        sub_note = res.get("default_sub_note") or "(เงินฝากคลัง 910)"
        lines = []
        for idx, form in enumerate(forms, start=1):
            seq_no = seq_start + idx - 1
            lines.append(
                (
                    0,
                    0,
                    self._prepare_line_vals_from_form(
                        form, idx, seq_no, fy, sub_note
                    ),
                )
            )
        if lines:
            res["line_ids"] = lines
        return res

    @api.onchange("seq_start", "fiscal_year_be")
    def _onchange_seq_or_year(self):
        seq = self.seq_start or 1
        fy = (self.fiscal_year_be or "").strip()
        for idx, line in enumerate(self.line_ids):
            current_seq = seq + idx
            line.seq_no = current_seq
            line.deeka_no = f"{current_seq:04d}/{fy}" if fy else f"{current_seq:04d}"

    @api.onchange("default_sub_note")
    def _onchange_default_sub_note(self):
        if not self.default_sub_note:
            return
        for line in self.line_ids:
            line.sub_note = self.default_sub_note

    def action_load_forms(self):
        """ดึงรายการใบขอเบิกเงินตามตัวกรองที่เลือก."""
        self.ensure_one()
        forms = self._search_matching_forms()
        seq_start = self.seq_start or 1
        fy = (self.fiscal_year_be or "").strip()
        sub_note = self.default_sub_note or "(เงินฝากคลัง 910)"
        new_lines = [(5, 0, 0)]
        for idx, form in enumerate(forms, start=1):
            seq_no = seq_start + idx - 1
            new_lines.append(
                (
                    0,
                    0,
                    self._prepare_line_vals_from_form(
                        form, idx, seq_no, fy, sub_note
                    ),
                )
            )
        self.line_ids = new_lines
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบปะหน้าการขออนุมัติเบิกจ่ายจาก GFMIS"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def get_paginated_pages(self):
        """แบ่งรายการออกเป็นหน้าละ rows_per_page รายการ เพื่อเรนเดอร์ตารางพร้อมเลขหน้า."""
        self.ensure_one()
        per_page = max(int(self.rows_per_page or 12), 1)
        lines = list(self.line_ids.sorted(key=lambda l: (l.sequence, l.id)))
        if not lines:
            return [
                {
                    "page_number": self.page_start or 1,
                    "lines": [],
                }
            ]
        total_pages = math.ceil(len(lines) / per_page)
        pages = []
        for page_idx in range(total_pages):
            chunk = lines[page_idx * per_page : (page_idx + 1) * per_page]
            pages.append(
                {
                    "page_number": (self.page_start or 1) + page_idx,
                    "lines": chunk,
                }
            )
        return pages

    def format_money(self, value):
        return f"{float(value or 0.0):,.2f}"

    @api.model
    def _get_official_thai_font_css(self):
        return Markup(_load_official_thai_font_css())

    def action_print_pdf(self):
        """พิมพ์รายงานใบปะหน้าการขออนุมัติเบิกจ่ายจาก GFMIS (PDF)."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มหรือดึงรายการใบขอเบิกเงินอย่างน้อย 1 รายการก่อนพิมพ์"))
        return self.env.ref(
            "vpk_disbursement_form.action_report_disbursement_cover_gfmis"
        ).report_action(self)

    def action_export_excel(self):
        """ส่งออกรายงานใบปะหน้าการขออนุมัติเบิกจ่ายจาก GFMIS เป็นไฟล์ Excel (.xls)."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มหรือดึงรายการใบขอเบิกเงินอย่างน้อย 1 รายการก่อนส่งออก"))

        wb = xlwt.Workbook(encoding="utf-8")
        pages = self.get_paginated_pages()

        border_thin = xlwt.Borders()
        border_thin.left = xlwt.Borders.THIN
        border_thin.right = xlwt.Borders.THIN
        border_thin.top = xlwt.Borders.THIN
        border_thin.bottom = xlwt.Borders.THIN

        font_bold = xlwt.Font()
        font_bold.name = "TH SarabunPSK"
        font_bold.bold = True
        font_bold.height = 16 * 20

        font_reg = xlwt.Font()
        font_reg.name = "TH SarabunPSK"
        font_reg.height = 16 * 20

        font_sub = xlwt.Font()
        font_sub.name = "TH SarabunPSK"
        font_sub.height = 12 * 20

        align_center = xlwt.Alignment()
        align_center.horz = xlwt.Alignment.HORZ_CENTER
        align_center.vert = xlwt.Alignment.VERT_CENTER

        align_left = xlwt.Alignment()
        align_left.horz = xlwt.Alignment.HORZ_LEFT
        align_left.vert = xlwt.Alignment.VERT_CENTER

        align_right = xlwt.Alignment()
        align_right.horz = xlwt.Alignment.HORZ_RIGHT
        align_right.vert = xlwt.Alignment.VERT_CENTER

        st_header = xlwt.XFStyle()
        st_header.font = font_bold
        st_header.borders = border_thin
        st_header.alignment = align_center

        st_center = xlwt.XFStyle()
        st_center.font = font_reg
        st_center.borders = border_thin
        st_center.alignment = align_center

        st_left = xlwt.XFStyle()
        st_left.font = font_reg
        st_left.borders = border_thin
        st_left.alignment = align_left

        st_sub = xlwt.XFStyle()
        st_sub.font = font_sub
        st_sub.borders = border_thin
        st_sub.alignment = align_left

        st_money = xlwt.XFStyle()
        st_money.font = font_reg
        st_money.borders = border_thin
        st_money.alignment = align_right
        st_money.num_format_str = "#,##0.00"

        ws = wb.add_sheet("ใบปะหน้า GFMIS")
        col_widths = [8, 12, 34, 10, 14, 18, 16, 14, 16, 14]
        for ci, w in enumerate(col_widths):
            ws.col(ci).width = w * 256

        row_idx = 0
        headers = [
            "ลำดับที่",
            "วันที่ โอน",
            "ชื่อบริษัท",
            "ขบ.",
            "ฎีกาที่",
            "เลขที่บิล",
            "จำนวนเงิน",
            "ภาษี",
            "เป็นเงิน",
            "ผู้อนุมัติ",
        ]
        for page in pages:
            for ci in range(10):
                val = f"หน้าที่ {page['page_number']}" if ci == 2 else ""
                ws.write(row_idx, ci, val, st_header)
            row_idx += 1

            for ci, h_text in enumerate(headers):
                ws.write(row_idx, ci, h_text, st_header)
            row_idx += 1

            for line in page["lines"]:
                ws.write(row_idx, 0, line.seq_no or "", st_center)
                ws.write(row_idx, 1, line.transfer_date or "", st_center)
                ws.write(row_idx, 2, line.partner_name or "", st_left)
                ws.write(row_idx, 3, line.kb_label or "", st_center)
                ws.write(row_idx, 4, line.deeka_no or "", st_center)
                ws.write(row_idx, 5, line.bill_no or "", st_center)
                ws.write(row_idx, 6, float(line.amount_request or 0.0), st_money)
                ws.write(row_idx, 7, float(line.wht_amount or 0.0), st_money)
                ws.write(row_idx, 8, float(line.amount_net or 0.0), st_money)
                ws.write(row_idx, 9, line.approver_note or "", st_center)
                row_idx += 1

                # แถวที่ 2 ใต้ชื่อบริษัท เช่น (เงินฝากคลัง 910)
                for ci in range(10):
                    ws.write(
                        row_idx,
                        ci,
                        (line.sub_note or "") if ci == 2 else "",
                        st_sub if ci == 2 else st_center,
                    )
                row_idx += 1

        buf = io.BytesIO()
        wb.save(buf)
        filename = f"ใบปะหน้าขออนุมัติเบิกจ่าย_GFMIS_หน้า_{self.page_start or 1}.xls"
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


class VpkDisbursementCoverWizardLine(models.TransientModel):
    _name = "vpk.disbursement.cover.wizard.line"
    _description = "รายการในใบปะหน้าการขออนุมัติเบิกจ่ายจาก GFMIS"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="vpk.disbursement.cover.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="ลำดับจัดเรียง", default=10)
    seq_no = fields.Integer(string="ลำดับที่", default=1)
    transfer_date = fields.Char(string="วันที่ โอน")
    disbursement_form_id = fields.Many2one(
        comodel_name="vpk.disbursement.form",
        string="ใบขอเบิกเงิน",
    )
    partner_name = fields.Char(string="ชื่อบริษัท", required=True)
    sub_note = fields.Char(
        string="หมายเหตุบรรทัดที่ 2",
        default="(เงินฝากคลัง 910)",
    )
    kb_label = fields.Char(string="ขบ.", default="ขบ.01")
    deeka_no = fields.Char(string="ฎีกาที่")
    bill_no = fields.Char(string="เลขที่บิล")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    amount_request = fields.Monetary(
        string="จำนวนเงิน",
        currency_field="currency_id",
    )
    wht_amount = fields.Monetary(
        string="ภาษี",
        currency_field="currency_id",
    )
    amount_net = fields.Monetary(
        string="เป็นเงิน",
        currency_field="currency_id",
    )
    approver_note = fields.Char(string="ผู้อนุมัติ")

    @api.onchange("disbursement_form_id")
    def _onchange_disbursement_form_id(self):
        form = self.disbursement_form_id
        if not form:
            return
        bill = form.invoice_id
        self.partner_name = form.partner_id.name if form.partner_id else ""
        self.kb_label = "ขบ.11" if form.form_type == "kb11" else "ขบ.01"
        self.bill_no = (
            (bill.ref or (bill.name if bill.name != "/" else ""))
            if bill
            else (form.reference or "")
        )
        self.amount_request = form.amount_request or 0.0
        self.wht_amount = form.wht_amount if form.tax_type != "none" else 0.0
        self.amount_net = form.amount_net or 0.0

    @api.onchange("amount_request", "wht_amount")
    def _onchange_amounts(self):
        self.amount_net = round(
            (self.amount_request or 0.0) - (self.wht_amount or 0.0), 2
        )
