# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64
import io
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class PrPoReportExportWizard(models.TransientModel):
    _name = "pr.po.report.export.wizard"
    _description = "Export รายงานขอซื้อ/สั่งซื้อ ประจำวัน สัปดาห์ เดือน ปี"

    report_scope = fields.Selection(
        selection=[
            ("pr", "ใบขอซื้อ/จ้าง/เช่า (PR)"),
            ("po", "ใบสั่งซื้อ/จ้าง/เช่า (PO)"),
            ("both", "ทั้ง PR และ PO"),
        ],
        string="ประเภทรายงาน",
        required=True,
        default="both",
    )
    period_type = fields.Selection(
        selection=[
            ("day", "ประจำวัน"),
            ("week", "ประจำสัปดาห์"),
            ("month", "ประจำเดือน"),
            ("year", "ประจำปี"),
            ("custom", "กำหนดช่วงเอง"),
        ],
        string="ช่วงเวลา",
        required=True,
        default="month",
    )
    date_from = fields.Date(string="ตั้งแต่วันที่", required=True)
    date_to = fields.Date(string="ถึงวันที่", required=True)
    po_issued_status = fields.Selection(
        selection=[
            ("all", "ทั้งหมด"),
            ("not_issued", "ยังไม่ออกใบสั่งซื้อ/จ้าง/เช่า"),
            ("partial", "ออกบางส่วน"),
            ("issued", "ออกใบสั่งซื้อ/จ้าง/เช่าแล้ว"),
        ],
        string="สถานะการออกใบสั่งซื้อ (PR)",
        default="all",
        required=True,
    )
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="ประเภทจัดซื้อ (ซื้อ/จ้าง/เช่า)",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        res.setdefault("date_from", today.replace(day=1))
        res.setdefault("date_to", today)
        return res

    @api.onchange("period_type")
    def _onchange_period_type(self):
        today = fields.Date.context_today(self)
        if self.period_type == "day":
            self.date_from = today
            self.date_to = today
        elif self.period_type == "week":
            start = today - timedelta(days=today.weekday())
            self.date_from = start
            self.date_to = start + timedelta(days=6)
        elif self.period_type == "month":
            self.date_from = today.replace(day=1)
            self.date_to = today
        elif self.period_type == "year":
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today

    def _pr_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("date_start", ">=", self.date_from),
            ("date_start", "<=", self.date_to),
        ]
        if self.po_issued_status != "all":
            domain.append(("po_issued_status", "=", self.po_issued_status))
        if self.procurement_type_id:
            domain.append(("procurement_type_id", "=", self.procurement_type_id.id))
        return domain

    def _po_domain(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("date_order", ">=", fields.Datetime.to_datetime(self.date_from)),
            (
                "date_order",
                "<",
                fields.Datetime.to_datetime(self.date_to + timedelta(days=1)),
            ),
            ("state", "!=", "cancel"),
        ]
        if self.procurement_type_id:
            requests = self.env["purchase.request"].search(
                [("procurement_type_id", "=", self.procurement_type_id.id)]
            )
            order_ids = requests.mapped("line_ids.purchase_lines.order_id").ids
            domain.append(("id", "in", order_ids or [0]))
        return domain

    def action_view_pr(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ติดตามใบขอซื้อ/จ้าง/เช่า"),
            "res_model": "purchase.request",
            "view_mode": "list,pivot,graph,form",
            "domain": self._pr_domain(),
            "context": {
                "search_default_groupby_po_issued_status": 1,
            },
        }

    def action_view_po(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายงานใบสั่งซื้อ/จ้าง/เช่า"),
            "res_model": "purchase.order",
            "view_mode": "list,pivot,graph,form",
            "domain": self._po_domain(),
        }

    def action_export_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(
                _("ไม่พบไลบรารี xlsxwriter กรุณาติดตั้งแพ็กเกจ python xlsxwriter")
            )
        if self.date_from > self.date_to:
            raise UserError(_("วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด"))

        content = self._generate_xlsx()
        period_label = dict(self._fields["period_type"].selection).get(
            self.period_type, ""
        )
        filename = "รายงานขอซื้อ_สั่งซื้อ_%s_%s_%s.xlsx" % (
            period_label,
            self.date_from,
            self.date_to,
        )
        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _generate_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#1F4E79", "font_color": "white", "border": 1}
        )
        cell_fmt = workbook.add_format({"border": 1})
        money_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        date_fmt = workbook.add_format({"border": 1, "num_format": "YYYY-MM-DD"})

        if self.report_scope in ("pr", "both"):
            self._write_pr_sheet(workbook, header_fmt, cell_fmt, money_fmt, date_fmt)
        if self.report_scope in ("po", "both"):
            self._write_po_sheet(workbook, header_fmt, cell_fmt, money_fmt, date_fmt)

        workbook.close()
        output.seek(0)
        return output.read()

    def _write_pr_sheet(self, workbook, header_fmt, cell_fmt, money_fmt, date_fmt):
        sheet = workbook.add_worksheet("ใบขอซื้อ-จ้าง-เช่า")
        headers = [
            "เลขที่ PR",
            "วันที่",
            "สถานะ PR",
            "สถานะออกใบสั่งซื้อ",
            "ประเภทจัดซื้อ",
            "ผู้ขอ",
            "วงเงินประมาณ",
            "จำนวน PO",
            "PO ยืนยันแล้ว",
            "เลขที่ PO",
            "คำอธิบาย",
        ]
        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_fmt)

        status_labels = dict(
            self.env["purchase.request"]._fields["po_issued_status"].selection
        )
        state_labels = dict(self.env["purchase.request"]._fields["state"].selection)
        requests = self.env["purchase.request"].search(
            self._pr_domain(), order="date_start desc, name"
        )
        row = 1
        for pr in requests:
            po_names = ", ".join(pr.purchase_order_ids.mapped("name"))
            sheet.write(row, 0, pr.name or "", cell_fmt)
            sheet.write(row, 1, pr.date_start or "", date_fmt)
            sheet.write(row, 2, state_labels.get(pr.state, pr.state or ""), cell_fmt)
            sheet.write(
                row,
                3,
                status_labels.get(pr.po_issued_status, pr.po_issued_status or ""),
                cell_fmt,
            )
            sheet.write(
                row,
                4,
                pr.procurement_type_id.display_name
                if pr.procurement_type_id
                else "",
                cell_fmt,
            )
            sheet.write(
                row,
                5,
                pr.requested_by.display_name if pr.requested_by else "",
                cell_fmt,
            )
            sheet.write(row, 6, pr.estimated_cost or 0.0, money_fmt)
            sheet.write(row, 7, len(pr.purchase_order_ids), cell_fmt)
            sheet.write(row, 8, pr.confirmed_po_count or 0, cell_fmt)
            sheet.write(row, 9, po_names, cell_fmt)
            sheet.write(row, 10, pr.description or "", cell_fmt)
            row += 1

        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 4, 22)
        sheet.set_column(5, 5, 18)
        sheet.set_column(6, 6, 14)
        sheet.set_column(9, 10, 28)

    def _write_po_sheet(self, workbook, header_fmt, cell_fmt, money_fmt, date_fmt):
        sheet = workbook.add_worksheet("ใบสั่งซื้อ-จ้าง-เช่า")
        headers = [
            "เลขที่ PO",
            "วันที่สั่งซื้อ",
            "สถานะ",
            "ผู้จำหน่าย",
            "มูลค่า",
            "อ้างอิงจาก PR",
            "เลขที่ PR",
            "Origin",
        ]
        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_fmt)

        state_labels = dict(self.env["purchase.order"]._fields["state"].selection)
        orders = self.env["purchase.order"].search(
            self._po_domain(), order="date_order desc, name"
        )
        row = 1
        for po in orders:
            pr_names = ", ".join(po.purchase_request_ids.mapped("name"))
            sheet.write(row, 0, po.name or "", cell_fmt)
            sheet.write(
                row,
                1,
                fields.Date.to_date(po.date_order) if po.date_order else "",
                date_fmt,
            )
            sheet.write(row, 2, state_labels.get(po.state, po.state or ""), cell_fmt)
            sheet.write(
                row,
                3,
                po.partner_id.display_name if po.partner_id else "",
                cell_fmt,
            )
            sheet.write(row, 4, po.amount_total or 0.0, money_fmt)
            sheet.write(row, 5, _("ใช่") if po.has_purchase_request else _("ไม่"), cell_fmt)
            sheet.write(row, 6, pr_names, cell_fmt)
            sheet.write(row, 7, po.origin or "", cell_fmt)
            row += 1

        sheet.set_column(0, 0, 14)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 2, 14)
        sheet.set_column(3, 3, 28)
        sheet.set_column(4, 4, 14)
        sheet.set_column(6, 7, 24)
