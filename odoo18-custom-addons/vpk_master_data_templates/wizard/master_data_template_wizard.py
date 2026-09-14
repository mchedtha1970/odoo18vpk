# -*- coding: utf-8 -*-
import base64
import io
import zipfile

from odoo import fields, models, _
from odoo.exceptions import UserError

from .template_defs import (
    AREA_SHEETS,
    INSTRUCTIONS,
    SHEETS,
    TEMPLATE_AREAS,
    write_data_sheet,
)

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None


class VpkMasterDataTemplateWizard(models.TransientModel):
    _name = "vpk.master.data.template.wizard"
    _description = "Download Master Data Excel Templates"
    _transient_max_hours = 72.0

    include_warehouse = fields.Boolean(string="คลังสินค้า / Location", default=True)
    include_product = fields.Boolean(string="Product Master", default=True)
    include_product_category = fields.Boolean(string="Product Category", default=True)
    include_uom = fields.Boolean(string="UoM", default=True)
    include_asset = fields.Boolean(string="Fixed Asset / Profile", default=True)
    include_analytic = fields.Boolean(
        string="Analytic / แผนก / Project", default=True
    )
    include_equipment = fields.Boolean(
        string="Equipment ยกยอด (Maintenance ↔ Asset)",
        default=True,
    )
    include_vendor = fields.Boolean(string="Vendor / ผู้จำหน่าย", default=True)
    include_purchase_request = fields.Boolean(
        string="Purchase Request (PR)", default=True
    )
    include_purchase_order = fields.Boolean(
        string="Purchase Order (PO)", default=True
    )
    include_coa = fields.Boolean(string="ผังบัญชี (Chart of Accounts)", default=True)
    include_accounting_setup = fields.Boolean(
        string="ตั้งค่าบัญชี (สมุดรายวัน / ภาษี / เงื่อนไขชำระ)",
        default=True,
    )
    include_work_acceptance = fields.Boolean(
        string="ตรวจรับงาน (Work Acceptance)", default=True
    )
    include_vendor_bill = fields.Boolean(
        string="ใบแจ้งหนี้ผู้ขาย / ใบลดหนี้ (ระบบเจ้าหนี้)",
        default=True,
    )
    include_finance = fields.Boolean(
        string="การจ่ายชำระ / Statement (ระบบการเงิน)", default=True
    )
    include_journal_entry = fields.Boolean(
        string="รายการบัญชีทั่วไป / ยกยอด (ระบบบัญชี)", default=True
    )
    include_wht_cert = fields.Boolean(
        string="หนังสือรับรองหัก ณ ที่จ่าย (WHT)", default=True
    )
    include_checkbook = fields.Boolean(
        string="สมุดเช็ค (Checkbook)", default=True
    )
    download_mode = fields.Selection(
        [
            ("single", "ไฟล์เดียว (หลายชีต)"),
            ("zip", "แยกไฟล์ตามหมวด (ZIP)"),
        ],
        string="รูปแบบดาวน์โหลด",
        default="single",
        required=True,
    )

    def _selected_areas(self):
        self.ensure_one()
        mapping = {
            "warehouse": self.include_warehouse,
            "product": self.include_product,
            "product_category": self.include_product_category,
            "uom": self.include_uom,
            "asset": self.include_asset,
            "analytic": self.include_analytic,
            "equipment": self.include_equipment,
            "vendor": self.include_vendor,
            "purchase_request": self.include_purchase_request,
            "purchase_order": self.include_purchase_order,
            "coa": self.include_coa,
            "accounting_setup": self.include_accounting_setup,
            "work_acceptance": self.include_work_acceptance,
            "vendor_bill": self.include_vendor_bill,
            "finance": self.include_finance,
            "journal_entry": self.include_journal_entry,
            "wht_cert": self.include_wht_cert,
            "checkbook": self.include_checkbook,
        }
        return [area for area, enabled in mapping.items() if enabled]

    def action_download(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(
                _("ไม่พบไลบรารี xlsxwriter กรุณาติดตั้งแพ็กเกจ python xlsxwriter")
            )
        areas = self._selected_areas()
        if not areas:
            raise UserError(_("กรุณาเลือกอย่างน้อย 1 หมวด"))

        if self.download_mode == "zip":
            content, filename, mimetype = self._build_zip(areas)
        else:
            content = self._build_workbook(areas)
            filename = "vpk_master_data_templates.xlsx"
            mimetype = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(content),
                "mimetype": mimetype,
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "new",
        }

    def _build_zip(self, areas):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            labels = dict(TEMPLATE_AREAS)
            for area in areas:
                content = self._build_workbook([area])
                safe = area.replace("_", "-")
                zf.writestr("vpk_master_%s.xlsx" % safe, content)
            # always include a readme
            readme = self._readme_text(areas, labels)
            zf.writestr("README.txt", readme.encode("utf-8"))
        return (
            buf.getvalue(),
            "vpk_master_data_templates.zip",
            "application/zip",
        )

    def _readme_text(self, areas, labels):
        lines = [
            "VPK Master Data Templates",
            "=========================",
            "",
            "หมวดที่รวมในไฟล์นี้:",
        ]
        for area in areas:
            lines.append("- %s" % labels.get(area, area))
        lines.extend(
            [
                "",
                "ลำดับเตรียมข้อมูลที่แนะนำ:",
                "1) UoM",
                "2) Product Category → Product",
                "3) Warehouse → Location",
                "4) Analytic / แผนก / Project",
                "5) Asset Profile → Asset Card",
                "6) Equipment Category → Equipment",
                "7) Vendor → VendorBank → VendorPricelist",
                "8) Purchase Request → Lines",
                "9) Purchase Order → Lines",
                "10) Chart of Accounts → Journal / Tax / WHT / Payment Term",
                "11) Work Acceptance → Lines",
                "12) Vendor Bill → Lines → Tax Invoice",
                "13) Vendor Payment → Lines / Bank Statement",
                "14) Checkbook → Check lines",
                "15) Journal Entry / Opening Balance → WHT Certificate",
            ]
        )
        return "\n".join(lines)

    def _build_workbook(self, areas):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#1F4E79",
                "font_color": "white",
                "border": 1,
                "text_wrap": True,
                "valign": "vcenter",
            }
        )
        tech_fmt = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#D6DCE4",
                "font_color": "#1F4E79",
                "border": 1,
                "italic": True,
                "font_size": 9,
            }
        )
        sample_fmt = workbook.add_format({"border": 1})
        note_fmt = workbook.add_format({"italic": True, "font_color": "#666666"})
        title_fmt = workbook.add_format({"bold": True, "font_size": 14})
        wrap_fmt = workbook.add_format({"text_wrap": True, "valign": "top"})

        self._write_instructions(workbook, areas, title_fmt, wrap_fmt, header_fmt)

        for area in areas:
            for sheet_name in AREA_SHEETS.get(area, []):
                spec = SHEETS[sheet_name]
                ws = workbook.add_worksheet(sheet_name)
                rows, extra_note = self._sheet_export_rows(sheet_name)
                write_data_sheet(
                    ws,
                    sheet_name,
                    spec,
                    header_fmt,
                    tech_fmt,
                    sample_fmt,
                    note_fmt,
                    rows=rows,
                    extra_note=extra_note,
                )

        workbook.close()
        return output.getvalue()

    def _sheet_export_rows(self, sheet_name):
        """Return (rows, extra_note) from live data, or (None, '') to keep samples."""
        if sheet_name == "ChartOfAccounts":
            rows = self._export_chart_of_accounts()
            extra = "ส่งออกจากฐานข้อมูล %s จำนวน %d บัญชี" % (
                self.env.cr.dbname,
                len(rows),
            )
            return rows, extra
        return None, ""

    def _export_chart_of_accounts(self):
        Account = self.env["account.account"].with_context(
            lang="th_TH", active_test=False
        )
        has_wht = "wht_account" in Account._fields
        accounts = Account.search([]).sorted(lambda acc: (acc.code or "", acc.id))
        rows = []
        for acc in accounts:
            if not acc.code:
                continue
            rows.append(
                [
                    acc.code,
                    acc.name or "",
                    acc.account_type or "",
                    1 if acc.reconcile else 0,
                    1 if has_wht and acc.wht_account else 0,
                    1 if acc.deprecated else 0,
                    "",
                ]
            )
        return rows

    def _write_instructions(self, workbook, areas, title_fmt, wrap_fmt, header_fmt):
        ws = workbook.add_worksheet("Instructions")
        ws.set_column(0, 0, 32)
        ws.set_column(1, 1, 72)
        ws.write(0, 0, "VPK Master Data Templates — สำหรับเตรียมข้อมูลนำเข้า", title_fmt)
        labels = dict(TEMPLATE_AREAS)
        selected = ", ".join(labels.get(a, a) for a in areas)
        ws.write(1, 0, "หมวดที่เลือก")
        ws.write(1, 1, selected, wrap_fmt)
        ws.write(3, 0, "หัวข้อ", header_fmt)
        ws.write(3, 1, "รายละเอียด", header_fmt)
        for idx, (left, right) in enumerate(INSTRUCTIONS, start=4):
            ws.write(idx, 0, left)
            ws.write(idx, 1, right, wrap_fmt)
