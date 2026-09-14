from odoo import _, api, fields, models
from odoo.exceptions import UserError

import base64
from io import BytesIO

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class DepartmentalBudgetSummaryWizard(models.TransientModel):
    _name = "departmental.budget.request.summary.wizard"
    _description = "Departmental Budget Request Summary Wizard"

    fiscal_year = fields.Char(
        string="ปีงบประมาณ",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year),
    )
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    form_type_id = fields.Many2one(
        comodel_name="vpk.budget.request.form.type",
        string="แบบฟอร์มคำของบ",
        required=True,
    )
    is_form_type_locked = fields.Boolean(compute="_compute_is_form_type_locked")
    summary_section = fields.Selection(
        selection=[
            ("material", "พัสดุ"),
            ("asset", "ครุภัณฑ์"),
            ("construction", "ก่อสร้าง"),
            ("project", "โครงการ"),
        ],
        compute="_compute_summary_section",
    )
    fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="แหล่งเงิน",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน / ศูนย์ต้นทุน",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    prior_fiscal_year_ce = fields.Char(compute="_compute_fiscal_year_labels")
    current_fiscal_year_ce = fields.Char(compute="_compute_fiscal_year_labels")
    line_ids = fields.One2many(
        comodel_name="departmental.budget.request.summary.line",
        inverse_name="wizard_id",
        string="รายการสรุป",
    )
    total_prior_year_plan = fields.Float(
        string="รวมแผนปีก่อน",
        compute="_compute_totals",
        digits=0,
    )
    total_disbursed = fields.Float(compute="_compute_totals", digits=0)
    total_payable = fields.Float(compute="_compute_totals", digits=0)
    total_committed = fields.Float(compute="_compute_totals", digits=0)
    total_spent = fields.Float(compute="_compute_totals", digits=0)
    total_remaining = fields.Float(compute="_compute_totals", digits=0)
    total_stock = fields.Float(compute="_compute_totals", digits=0)
    total_requested_plan = fields.Float(compute="_compute_totals", digits=0)
    total_amount = fields.Float(compute="_compute_totals", digits=0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        form_type_id = self.env.context.get("default_form_type_id")
        if form_type_id and "form_type_id" in fields_list:
            res["form_type_id"] = form_type_id
        return res

    @api.depends_context("default_form_type_id")
    def _compute_is_form_type_locked(self):
        locked = bool(self.env.context.get("default_form_type_id"))
        for wizard in self:
            wizard.is_form_type_locked = locked

    @api.depends("form_type_id", "form_type_id.line_type_ids.section_key")
    def _compute_summary_section(self):
        for wizard in self:
            wizard.summary_section = (
                wizard.form_type_id._get_primary_section()
                if wizard.form_type_id
                else False
            )

    @api.depends("fiscal_year")
    def _compute_fiscal_year_labels(self):
        request_model = self.env["departmental.budget.request"]
        for wizard in self:
            ce_current = request_model._fiscal_year_to_ce(wizard.fiscal_year)
            wizard.current_fiscal_year_ce = str(ce_current) if ce_current else ""
            wizard.prior_fiscal_year_ce = (
                str(ce_current - 1) if ce_current else ""
            )

    @api.depends(
        "line_ids.prior_year_plan_amount",
        "line_ids.disbursed_amount",
        "line_ids.payable_amount",
        "line_ids.committed_not_received_amount",
        "line_ids.total_spent_amount",
        "line_ids.remaining_amount",
        "line_ids.stock_amount",
        "line_ids.requested_plan_amount",
        "line_ids.total_amount",
        "line_ids.qty_new_purchase",
        "line_ids.qty_replacement",
        "line_ids.qty_addition",
    )
    def _compute_totals(self):
        for wizard in self:
            lines = wizard.line_ids
            wizard.total_prior_year_plan = sum(lines.mapped("prior_year_plan_amount"))
            wizard.total_disbursed = sum(lines.mapped("disbursed_amount"))
            wizard.total_payable = sum(lines.mapped("payable_amount"))
            wizard.total_committed = sum(
                lines.mapped("committed_not_received_amount")
            )
            wizard.total_spent = sum(lines.mapped("total_spent_amount"))
            wizard.total_remaining = sum(lines.mapped("remaining_amount"))
            wizard.total_stock = sum(lines.mapped("stock_amount"))
            wizard.total_requested_plan = sum(lines.mapped("requested_plan_amount"))
            wizard.total_amount = sum(lines.mapped("total_amount"))

    def _fiscal_year_search_values(self):
        self.ensure_one()
        request_model = self.env["departmental.budget.request"]
        be_year = request_model._fiscal_year_to_be(self.fiscal_year)
        ce_year = request_model._fiscal_year_to_ce(self.fiscal_year)
        values = set()
        if be_year:
            values.add(str(be_year))
        if ce_year:
            values.add(str(ce_year))
        return list(values)

    def _base_line_domain(self):
        self.ensure_one()
        if not self.form_type_id:
            raise UserError(_("กรุณาเลือกแบบฟอร์มคำของบ"))
        domain = [
            ("request_id.form_type_id", "=", self.form_type_id.id),
            ("request_id.fiscal_year", "in", self._fiscal_year_search_values()),
            ("request_id.state", "!=", "rejected"),
        ]
        if self.budget_post_id:
            domain.append(("budget_post_id", "=", self.budget_post_id.id))
        if self.fund_source_id:
            domain.append(
                ("request_id.fund_source_id", "=", self.fund_source_id.id)
            )
        if self.analytic_account_id:
            domain.append(
                ("request_id.analytic_account_id", "=", self.analytic_account_id.id)
            )
        return domain

    def _load_material_summary(self):
        self.ensure_one()
        line_domain = self._base_line_domain() + [
            ("line_type", "=", "supplies_budget"),
            (
                "request_id.form_type_id.line_type_ids.budget_type_id.code",
                "=",
                "supplies_budget",
            ),
        ]
        request_lines = self.env["departmental.budget.request.line"].search(line_domain)
        grouped = {}
        for line in request_lines:
            if not line.material_sub_type_id:
                continue
            key = line.material_sub_type_id.id
            grouped[key] = grouped.get(key, line.browse()) | line

        material_sub_types = self.env["vpk.budget.material.sub.type"].search(
            [("active", "=", True)],
            order="budget_group_id, sequence, id",
        )

        line_commands = []
        sequence = 10
        for sub_type in material_sub_types:
            lines = grouped.get(sub_type.id, self.env["departmental.budget.request.line"])
            prior_year_plan = sum(lines.mapped("prior_year_plan_amount"))
            disbursed = sum(lines.mapped("disbursed_amount"))
            payable = sum(lines.mapped("payable_amount"))
            committed = sum(lines.mapped("committed_not_received_amount"))
            remaining = sum(lines.mapped("remaining_amount"))
            stock = sum(lines.mapped("stock_amount"))
            requested_plan = sum(lines.mapped("requested_plan_amount"))
            notes = sorted(
                {
                    note.strip()
                    for note in lines.mapped("material_note")
                    if note and note.strip()
                }
            )
            line_commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": sequence,
                        "budget_group_id": sub_type.budget_group_id.id,
                        "material_sub_type_id": sub_type.id,
                        "prior_year_plan_amount": prior_year_plan,
                        "disbursed_amount": disbursed,
                        "payable_amount": payable,
                        "committed_not_received_amount": committed,
                        "remaining_amount": remaining,
                        "stock_amount": stock,
                        "requested_plan_amount": requested_plan,
                        "material_note": ", ".join(notes),
                        "request_count": len(lines.mapped("request_id")),
                    },
                )
            )
            sequence += 10
        self.write({"line_ids": line_commands})

    def _generic_line_label(self, line, section):
        if section == "asset":
            if line.asset_categ_id:
                return line.asset_categ_id.name
            return line.item_name or line.usage_budget_type_name or "-"
        return line.item_name or "-"

    def _load_asset_summary(self):
        self.ensure_one()
        line_domain = self._base_line_domain() + [
            ("line_type", "=", "asset_budget"),
        ]
        request_lines = self.env["departmental.budget.request.line"].search(
            line_domain,
            order="request_id, sequence, id",
        )

        line_commands = []
        sequence = 10
        for line in request_lines:
            request = line.request_id
            line_commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": sequence,
                        "request_id": request.id,
                        "department_name": request.analytic_account_id.name or "",
                        "budget_post_id": line.budget_post_id.id,
                        "line_label": line.item_name or "",
                        "current_quantity": line.current_quantity,
                        "current_age_year": line.current_age_year or "",
                        "requested_quantity": line.requested_quantity,
                        "unit_price": line.unit_price,
                        "total_amount": line.total_amount,
                        "qty_new_purchase": line.qty_new_purchase,
                        "qty_replacement": line.qty_replacement,
                        "qty_addition": line.qty_addition,
                        "reason": line.reason or "",
                        "request_count": 1,
                    },
                )
            )
            sequence += 10
        self.write({"line_ids": line_commands})

    def _load_construction_summary(self):
        self.ensure_one()
        line_domain = self._base_line_domain() + [
            ("line_type", "=", "construction_budget"),
        ]
        request_lines = self.env["departmental.budget.request.line"].search(
            line_domain,
            order="request_id, sequence, id",
        )

        line_commands = []
        sequence = 10
        for line in request_lines:
            request = line.request_id
            line_commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": sequence,
                        "request_id": request.id,
                        "department_name": request.analytic_account_id.name or "",
                        "budget_post_id": line.budget_post_id.id,
                        "line_label": line.item_name or "",
                        "usage_area": line.usage_area or "",
                        "construction_location": line.construction_location or "",
                        "unit_name": line.unit_name or "",
                        "requested_quantity": line.requested_quantity or line.quantity,
                        "unit_price": line.unit_price,
                        "total_amount": line.total_amount,
                        "construction_request_improvement": line.construction_request_improvement,
                        "construction_request_expansion": line.construction_request_expansion,
                        "reason": line.reason or "",
                        "request_count": 1,
                    },
                )
            )
            sequence += 10
        self.write({"line_ids": line_commands})

    def _load_generic_summary(self, section):
        self.ensure_one()
        section_codes = {
            "asset": "asset_budget",
            "construction": "construction_budget",
            "project": "project_budget",
        }
        line_domain = self._base_line_domain() + [
            ("line_type", "=", section_codes[section]),
        ]
        request_lines = self.env["departmental.budget.request.line"].search(line_domain)
        grouped = {}
        for line in request_lines:
            key = (
                line.budget_post_id.id,
                self._generic_line_label(line, section),
            )
            grouped[key] = grouped.get(key, line.browse()) | line

        line_commands = []
        sequence = 10
        for (budget_post_id, label), lines in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1])
        ):
            line_commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": sequence,
                        "budget_post_id": budget_post_id,
                        "line_label": label,
                        "requested_quantity": sum(lines.mapped("requested_quantity")),
                        "total_amount": sum(lines.mapped("total_amount")),
                        "requested_plan_amount": sum(
                            lines.mapped("requested_plan_amount")
                        ),
                        "request_count": len(lines.mapped("request_id")),
                    },
                )
            )
            sequence += 10
        self.write({"line_ids": line_commands})

    def action_load_summary(self):
        self.ensure_one()
        if not self.fiscal_year:
            raise UserError(_("กรุณาระบุปีงบประมาณ"))
        if not self.form_type_id:
            raise UserError(_("กรุณาเลือกแบบฟอร์มคำของบ"))

        self.line_ids.unlink()

        section = self.summary_section
        if section == "material":
            self._load_material_summary()
        elif section == "asset":
            self._load_asset_summary()
        elif section == "construction":
            self._load_construction_summary()
        elif section == "project":
            self._load_generic_summary(section)
        else:
            raise UserError(
                _("แบบฟอร์มคำของบนี้ยังไม่รองรับการสรุปรายการ")
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _fiscal_period_label_be(self, be_year):
        if not be_year:
            return ""
        short_year = be_year % 100
        return f"ต.ค.{short_year - 1:02d}- มิ.ย.{short_year:02d}"

    def _get_summary_fiscal_years(self):
        self.ensure_one()
        request_model = self.env["departmental.budget.request"]
        be_current = request_model._fiscal_year_to_be(self.fiscal_year)
        be_prior = be_current - 1 if be_current else 0
        ce_current = request_model._fiscal_year_to_ce(self.fiscal_year)
        ce_prior = ce_current - 1 if ce_current else 0
        return {
            "be_current": be_current,
            "be_prior": be_prior,
            "ce_current": ce_current,
            "ce_prior": ce_prior,
            "prior_period": self._fiscal_period_label_be(be_prior),
            "current_period": self._fiscal_period_label_be(be_current),
        }

    def _generate_summary_xlsx(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(
                _("ไม่พบไลบรารี xlsxwriter กรุณาติดตั้งแพ็กเกจ python xlsxwriter")
            )
        if not self.line_ids:
            raise UserError(_("กรุณากดแสดงสรุปก่อนส่งออก Excel"))
        if self.summary_section == "asset":
            return self._generate_asset_summary_xlsx()
        if self.summary_section == "construction":
            return self._generate_construction_summary_xlsx()
        if self.summary_section != "material":
            raise UserError(
                _("การส่งออก Excel รองรับเฉพาะแบบฟอร์มวัสดุ ครุภัณฑ์ และก่อสร้าง")
            )

        fy = self._get_summary_fiscal_years()
        fund_name = self.fund_source_id.name or "เงินบำรุง"
        budget_post_name = self.budget_post_id.name or "ทุกหมวดงบประมาณ"
        form_type_name = self.form_type_id.name or ""

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("สรุปคำของบ")
        worksheet.set_landscape()
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)

        title_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "font_size": 12,
                "text_wrap": True,
            }
        )
        subtitle_fmt = workbook.add_format(
            {"align": "left", "valign": "vcenter", "font_size": 10}
        )
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True,
                "bg_color": "#E2EFDA",
            }
        )
        cell_fmt = workbook.add_format({"border": 1, "valign": "vcenter"})
        cell_center_fmt = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter"}
        )
        text_fmt = workbook.add_format({"border": 1, "valign": "vcenter", "text_wrap": True})
        money_fmt = workbook.add_format(
            {"border": 1, "num_format": "#,##0.00", "align": "right", "valign": "vcenter"}
        )
        total_label_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#FFF2CC",
            }
        )
        total_money_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "bg_color": "#FFF2CC",
            }
        )

        worksheet.set_column(0, 0, 6)
        worksheet.set_column(1, 1, 24)
        worksheet.set_column(2, 9, 14)
        worksheet.set_column(10, 10, 18)

        title_line_1 = (
            f"สรุปแผนการใช้{fund_name} {budget_post_name} "
            f"ปีงบประมาณ {fy['be_prior']} ({fy['prior_period']}) และ"
        )
        title_line_2 = (
            f"คำขอตั้งปรับแผน{fund_name} {budget_post_name} "
            f"ประจำปีงบประมาณ {fy['be_current']}"
        )
        worksheet.merge_range(0, 0, 0, 10, title_line_1, title_fmt)
        worksheet.merge_range(1, 0, 1, 10, title_line_2, title_fmt)

        filter_parts = [
            f"แบบฟอร์ม: {form_type_name}",
            f"ปีงบประมาณ (ค.ศ.): {fy['ce_current']}",
            f"หมวดงบประมาณ: {budget_post_name}",
        ]
        if self.analytic_account_id:
            filter_parts.append(f"หน่วยงาน: {self.analytic_account_id.name}")
        worksheet.merge_range(2, 0, 2, 10, " | ".join(filter_parts), subtitle_fmt)

        header_row = 3
        subheader_row = 4
        worksheet.merge_range(header_row, 0, subheader_row, 0, "ลำดับที่", header_fmt)
        worksheet.merge_range(header_row, 1, subheader_row, 1, "ประเภทหมวดวัสดุ", header_fmt)
        worksheet.merge_range(
            header_row,
            2,
            subheader_row,
            2,
            f"แผนปีงบฯ {fy['be_prior']}\n(บาท)",
            header_fmt,
        )
        worksheet.merge_range(
            header_row,
            3,
            header_row,
            5,
            f"ผลการดำเนินงาน ณ 30 มิ.ย. {fy['be_prior']} (บาท)",
            header_fmt,
        )
        worksheet.write(subheader_row, 3, "เบิกจ่ายแล้ว", header_fmt)
        worksheet.write(subheader_row, 4, "เจ้าหนี้ค้างจ่าย", header_fmt)
        worksheet.write(subheader_row, 5, "ก่อหนี้/ยังไม่ตรวจรับ", header_fmt)
        worksheet.merge_range(
            header_row,
            6,
            subheader_row,
            6,
            "รวมรายจ่าย\n(1+2+3)",
            header_fmt,
        )
        worksheet.merge_range(
            header_row, 7, subheader_row, 7, "ยอดเงินคงเหลือ\n(บาท)", header_fmt
        )
        worksheet.merge_range(
            header_row, 8, subheader_row, 8, "วัสดุคงคลัง\n(บาท)", header_fmt
        )
        worksheet.merge_range(
            header_row,
            9,
            subheader_row,
            9,
            f"คำขอตั้งแผนปีงบฯ {fy['be_current']}\n(บาท)",
            header_fmt,
        )
        worksheet.merge_range(header_row, 10, subheader_row, 10, "หมายเหตุ", header_fmt)

        row = subheader_row + 1
        for index, line in enumerate(self.line_ids, start=1):
            worksheet.write(row, 0, index, cell_center_fmt)
            worksheet.write(
                row,
                1,
                line.material_sub_type_id.name or "",
                text_fmt,
            )
            worksheet.write_number(row, 2, line.prior_year_plan_amount or 0.0, money_fmt)
            worksheet.write_number(row, 3, line.disbursed_amount or 0.0, money_fmt)
            worksheet.write_number(row, 4, line.payable_amount or 0.0, money_fmt)
            worksheet.write_number(
                row, 5, line.committed_not_received_amount or 0.0, money_fmt
            )
            worksheet.write_number(row, 6, line.total_spent_amount or 0.0, money_fmt)
            worksheet.write_number(row, 7, line.remaining_amount or 0.0, money_fmt)
            worksheet.write_number(row, 8, line.stock_amount or 0.0, money_fmt)
            worksheet.write_number(row, 9, line.requested_plan_amount or 0.0, money_fmt)
            worksheet.write(row, 10, line.material_note or "", text_fmt)
            row += 1

        worksheet.merge_range(row, 0, row, 1, "รวม", total_label_fmt)
        worksheet.write_number(row, 2, self.total_prior_year_plan or 0.0, total_money_fmt)
        worksheet.write_number(row, 3, self.total_disbursed or 0.0, total_money_fmt)
        worksheet.write_number(row, 4, self.total_payable or 0.0, total_money_fmt)
        worksheet.write_number(row, 5, self.total_committed or 0.0, total_money_fmt)
        worksheet.write_number(row, 6, self.total_spent or 0.0, total_money_fmt)
        worksheet.write_number(row, 7, self.total_remaining or 0.0, total_money_fmt)
        worksheet.write_number(row, 8, self.total_stock or 0.0, total_money_fmt)
        worksheet.write_number(row, 9, self.total_requested_plan or 0.0, total_money_fmt)
        worksheet.write(row, 10, "", total_label_fmt)

        workbook.close()
        output.seek(0)
        return output.read()

    def _generate_construction_summary_xlsx(self):
        self.ensure_one()
        fy = self._get_summary_fiscal_years()
        budget_post_name = self.budget_post_id.name or "ทุกหมวดงบประมาณ"
        form_type_name = self.form_type_id.name or ""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("รายละเอียดก่อสร้าง")
        worksheet.set_landscape()
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(left=0.2, right=0.2, top=0.4, bottom=0.4)

        title_fmt = workbook.add_format(
            {"bold": True, "align": "center", "valign": "vcenter", "font_size": 12}
        )
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True,
                "bg_color": "#E2EFDA",
            }
        )
        group_fmt = workbook.add_format(
            {"bold": True, "border": 1, "align": "left", "valign": "vcenter"}
        )
        group_money_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
            }
        )
        cell_fmt = workbook.add_format({"border": 1, "valign": "top"})
        text_fmt = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})
        center_fmt = workbook.add_format(
            {"border": 1, "align": "center", "valign": "top"}
        )
        money_fmt = workbook.add_format(
            {"border": 1, "num_format": "#,##0.00", "align": "right", "valign": "top"}
        )
        total_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "bg_color": "#FFF2CC",
            }
        )

        widths = [5, 32, 10, 22, 14, 10, 14, 10, 16, 42]
        for col, width in enumerate(widths):
            worksheet.set_column(col, col, width)

        title = (
            f"รายละเอียดคำขอตั้งแผนเงินบำรุง โรงพยาบาลวชิระภูเก็ต "
            f"{form_type_name} ปีงบประมาณ {fy['be_current']} {budget_post_name}"
        )
        worksheet.merge_range(0, 0, 0, 9, title, title_fmt)
        if self.analytic_account_id:
            department_label = self.analytic_account_id.name
        else:
            department_label = "ทุกหน่วยงาน"
        worksheet.merge_range(
            1,
            0,
            1,
            9,
            f"(งาน {department_label} )",
            cell_fmt,
        )

        header_row = 2
        worksheet.merge_range(header_row, 0, header_row + 1, 0, "ลำดับที่", header_fmt)
        worksheet.merge_range(header_row, 1, header_row + 1, 1, "รายการ", header_fmt)
        worksheet.merge_range(
            header_row, 2, header_row + 1, 2, "พื้นที่ใช้สอย\n(ตร.ม.)", header_fmt
        )
        worksheet.merge_range(
            header_row, 3, header_row + 1, 3, "สถานที่ก่อสร้าง", header_fmt
        )
        worksheet.merge_range(
            header_row, 4, header_row + 1, 4, "ราคาต่อหน่วย\n(บาท)", header_fmt
        )
        worksheet.merge_range(
            header_row, 5, header_row + 1, 5, "จำนวน\n(หน่วย)", header_fmt
        )
        worksheet.merge_range(header_row, 6, header_row + 1, 6, "รวมเงิน\n(บาท)", header_fmt)
        worksheet.merge_range(header_row, 7, header_row, 8, "ประเภทการขอ", header_fmt)
        worksheet.write(header_row + 1, 7, "ปรับปรุง", header_fmt)
        worksheet.write(header_row + 1, 8, "ขยายพื้นที่/\nต่อเติม", header_fmt)
        worksheet.merge_range(
            header_row,
            9,
            header_row + 1,
            9,
            "เหตุผล คำชี้แจง\n(1 ล้านขึ้นไปเขียนโครงการด้วย)",
            header_fmt,
        )

        row = header_row + 2
        running_no = 1
        current_department = None
        sorted_lines = self.line_ids.sorted(
            lambda item: (item.department_name or "", item.sequence)
        )
        department_totals = {}
        for line in sorted_lines:
            department = line.department_name or "-"
            department_totals[department] = (
                department_totals.get(department, 0.0) + (line.total_amount or 0.0)
            )

        for line in sorted_lines:
            department = line.department_name or "-"
            if department != current_department:
                current_department = department
                worksheet.merge_range(row, 0, row, 5, department, group_fmt)
                worksheet.write_number(
                    row,
                    6,
                    department_totals.get(department, 0.0),
                    group_money_fmt,
                )
                worksheet.write(row, 7, "", group_fmt)
                worksheet.write(row, 8, "", group_fmt)
                worksheet.write(row, 9, "", group_fmt)
                row += 1

            worksheet.write(row, 0, running_no, center_fmt)
            worksheet.write(row, 1, line.line_label or "", text_fmt)
            worksheet.write(row, 2, line.usage_area or "", center_fmt)
            worksheet.write(row, 3, line.construction_location or "", text_fmt)
            worksheet.write_number(row, 4, line.unit_price or 0.0, money_fmt)
            worksheet.write_number(row, 5, line.requested_quantity or 0.0, center_fmt)
            worksheet.write_number(row, 6, line.total_amount or 0.0, money_fmt)
            worksheet.write(row, 7, "1" if line.construction_request_improvement else "", center_fmt)
            worksheet.write(row, 8, "1" if line.construction_request_expansion else "", center_fmt)
            worksheet.write(row, 9, line.reason or "", text_fmt)
            worksheet.set_row(row, 54)
            row += 1
            running_no += 1

        worksheet.merge_range(row, 0, row, 5, "รวม", group_fmt)
        worksheet.write_number(row, 6, self.total_amount or 0.0, total_fmt)
        worksheet.write(row, 7, "", group_fmt)
        worksheet.write(row, 8, "", group_fmt)
        worksheet.write(row, 9, "", group_fmt)

        workbook.close()
        output.seek(0)
        return output.read()

    def _generate_asset_summary_xlsx(self):
        self.ensure_one()
        fy = self._get_summary_fiscal_years()
        budget_post_name = self.budget_post_id.name or "ทุกหมวดงบประมาณ"
        form_type_name = self.form_type_id.name or ""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("รายละเอียดครุภัณฑ์")
        worksheet.set_landscape()
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(left=0.2, right=0.2, top=0.4, bottom=0.4)

        title_fmt = workbook.add_format(
            {"bold": True, "align": "center", "valign": "vcenter", "font_size": 12}
        )
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True,
                "bg_color": "#E2EFDA",
            }
        )
        group_fmt = workbook.add_format(
            {"bold": True, "border": 1, "align": "left", "valign": "vcenter"}
        )
        group_money_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
            }
        )
        cell_fmt = workbook.add_format({"border": 1, "valign": "top"})
        text_fmt = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})
        center_fmt = workbook.add_format(
            {"border": 1, "align": "center", "valign": "top"}
        )
        money_fmt = workbook.add_format(
            {"border": 1, "num_format": "#,##0.00", "align": "right", "valign": "top"}
        )
        total_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "bg_color": "#FFF2CC",
            }
        )

        widths = [5, 30, 9, 10, 9, 12, 12, 10, 10, 10, 40]
        for col, width in enumerate(widths):
            worksheet.set_column(col, col, width)

        title = (
            f"รายละเอียดคำของบตั้งแผนเงินบำรุง โรงพยาบาลวชิระภูเก็ต "
            f"{form_type_name} ปีงบประมาณ {fy['be_current']}"
        )
        worksheet.merge_range(0, 0, 0, 10, title, title_fmt)
        worksheet.merge_range(
            1,
            0,
            1,
            10,
            f"หมวดงบประมาณ: {budget_post_name}",
            cell_fmt,
        )

        header_row = 2
        worksheet.merge_range(header_row, 0, header_row + 1, 0, "ลำดับ\nที่", header_fmt)
        worksheet.merge_range(
            header_row,
            1,
            header_row + 1,
            1,
            "รายการ\n(ชื่อทั้งภาษาไทยและภาษาอังกฤษ)",
            header_fmt,
        )
        worksheet.merge_range(header_row, 2, header_row, 3, "ปัจจุบันมีอยู่", header_fmt)
        worksheet.write(header_row + 1, 2, "จำนวน\n(เครื่อง)", header_fmt)
        worksheet.write(header_row + 1, 3, "อายุ\nการใช้งาน\n(ปี)", header_fmt)
        worksheet.merge_range(header_row, 4, header_row + 1, 4, "จำนวน\nที่ขอตั้ง", header_fmt)
        worksheet.merge_range(header_row, 5, header_row + 1, 5, "ราคาต่อ\nหน่วย\n(บาท)", header_fmt)
        worksheet.merge_range(header_row, 6, header_row + 1, 6, "รวมเงิน\n(บาท)", header_fmt)
        worksheet.merge_range(header_row, 7, header_row, 9, "ประเภทการขอ", header_fmt)
        worksheet.write(header_row + 1, 7, "ซื้อใหม่", header_fmt)
        worksheet.write(header_row + 1, 8, "ซื้อทดแทน", header_fmt)
        worksheet.write(header_row + 1, 9, "ซื้อเพิ่ม", header_fmt)
        worksheet.merge_range(
            header_row,
            10,
            header_row + 1,
            10,
            "เหตุผลคำชี้แจง\n(เกิน 5 ล้าน แนบโครงการเป็น spec ในใบเสนอราคา /\nต่ำกว่า 5 ล้าน แนบ spec ในใบเสนอราคา)",
            header_fmt,
        )

        row = header_row + 2
        running_no = 1
        current_department = None
        sorted_lines = self.line_ids.sorted(
            lambda item: (item.department_name or "", item.sequence)
        )
        department_totals = {}
        for line in sorted_lines:
            department = line.department_name or "-"
            department_totals[department] = (
                department_totals.get(department, 0.0) + (line.total_amount or 0.0)
            )

        for line in sorted_lines:
            department = line.department_name or "-"
            if department != current_department:
                current_department = department
                worksheet.merge_range(
                    row,
                    0,
                    row,
                    5,
                    department,
                    group_fmt,
                )
                worksheet.write_number(
                    row,
                    6,
                    department_totals.get(department, 0.0),
                    group_money_fmt,
                )
                worksheet.write(row, 7, "", group_fmt)
                worksheet.write(row, 8, "", group_fmt)
                worksheet.write(row, 9, "", group_fmt)
                worksheet.write(row, 10, "", group_fmt)
                row += 1

            worksheet.write(row, 0, running_no, center_fmt)
            worksheet.write(row, 1, line.line_label or "", text_fmt)
            worksheet.write_number(row, 2, line.current_quantity or 0.0, center_fmt)
            worksheet.write(row, 3, line.current_age_year or "", center_fmt)
            worksheet.write_number(row, 4, line.requested_quantity or 0.0, center_fmt)
            worksheet.write_number(row, 5, line.unit_price or 0.0, money_fmt)
            worksheet.write_number(row, 6, line.total_amount or 0.0, money_fmt)
            worksheet.write_number(row, 7, line.qty_new_purchase or 0.0, center_fmt)
            worksheet.write_number(row, 8, line.qty_replacement or 0.0, center_fmt)
            worksheet.write_number(row, 9, line.qty_addition or 0.0, center_fmt)
            worksheet.write(row, 10, line.reason or "", text_fmt)
            worksheet.set_row(row, 72)
            row += 1
            running_no += 1

        worksheet.merge_range(row, 0, row, 5, "รวม", group_fmt)
        worksheet.write_number(row, 6, self.total_amount or 0.0, total_fmt)
        worksheet.write(row, 7, "", group_fmt)
        worksheet.write(row, 8, "", group_fmt)
        worksheet.write(row, 9, "", group_fmt)
        worksheet.write(row, 10, "", group_fmt)

        workbook.close()
        output.seek(0)
        return output.read()

    def action_export_excel(self):
        self.ensure_one()
        content = self._generate_summary_xlsx()
        form_type_name = self.form_type_id.name or "form"
        filename = "สรุปคำของบ_%s_%s_%s.xlsx" % (
            form_type_name or "form",
            self.budget_post_id.name or "ทุกหมวดงบประมาณ",
            self.current_fiscal_year_ce or self.fiscal_year,
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


class DepartmentalBudgetSummaryLine(models.TransientModel):
    _name = "departmental.budget.request.summary.line"
    _description = "Departmental Budget Request Summary Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="departmental.budget.request.summary.wizard",
        required=True,
        ondelete="cascade",
    )
    summary_section = fields.Selection(related="wizard_id.summary_section")
    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        comodel_name="departmental.budget.request",
        string="เลขที่คำขอ",
        readonly=True,
    )
    department_name = fields.Char(string="กลุ่มงาน/หน่วยงาน", readonly=True)
    budget_post_id = fields.Many2one(
        comodel_name="account.budget.post",
        string="หมวดงบประมาณ",
        readonly=True,
    )
    line_label = fields.Text(string="รายการ", readonly=True)
    usage_area = fields.Char(string="พื้นที่ใช้สอย (ตร.ม.)", readonly=True)
    construction_location = fields.Char(string="สถานที่ก่อสร้าง", readonly=True)
    unit_name = fields.Char(string="หน่วย", readonly=True)
    current_quantity = fields.Float(string="จำนวนปัจจุบัน", digits=0, readonly=True)
    current_age_year = fields.Char(string="อายุการใช้งาน (ปี)", readonly=True)
    requested_quantity = fields.Float(string="จำนวนที่ขอตั้ง", digits=0, readonly=True)
    unit_price = fields.Float(string="ราคาต่อหน่วย", digits=0, readonly=True)
    total_amount = fields.Float(string="รวมเงิน", digits=0, readonly=True)
    qty_new_purchase = fields.Float(string="ซื้อใหม่", digits=0, readonly=True)
    qty_replacement = fields.Float(string="ซื้อทดแทน", digits=0, readonly=True)
    qty_addition = fields.Float(string="ซื้อเพิ่ม", digits=0, readonly=True)
    construction_request_improvement = fields.Boolean(
        string="ขอปรับปรุง",
        readonly=True,
    )
    construction_request_expansion = fields.Boolean(
        string="ขอขยาย/ต่อเติม",
        readonly=True,
    )
    reason = fields.Text(string="เหตุผลคำชี้แจง", readonly=True)
    budget_group_id = fields.Many2one(
        comodel_name="vpk.budget.group",
        string="กลุ่มงบประมาณ",
        readonly=True,
    )
    material_sub_type_id = fields.Many2one(
        comodel_name="vpk.budget.material.sub.type",
        string="ประเภทหมวดวัสดุ",
        readonly=True,
    )
    prior_year_plan_amount = fields.Float(
        string="แผนปีงบก่อน (บาท)",
        digits=0,
        readonly=True,
    )
    disbursed_amount = fields.Float(
        string="เบิกจ่ายแล้ว (บาท)",
        digits=0,
        readonly=True,
    )
    payable_amount = fields.Float(
        string="เจ้าหนี้คงค้าง (บาท)",
        digits=0,
        readonly=True,
    )
    committed_not_received_amount = fields.Float(
        string="ก่อหนี้/ยังไม่ตรวจรับ (บาท)",
        digits=0,
        readonly=True,
    )
    total_spent_amount = fields.Float(
        string="รวมรายจ่าย (บาท)",
        compute="_compute_total_spent_amount",
        digits=0,
        readonly=True,
    )
    remaining_amount = fields.Float(
        string="ยอดเงินคงเหลือ (บาท)",
        digits=0,
        readonly=True,
    )
    stock_amount = fields.Float(
        string="วัสดุคงคลัง (บาท)",
        digits=0,
        readonly=True,
    )
    requested_plan_amount = fields.Float(
        string="คำขอตั้งแผนปีงบ (บาท)",
        digits=0,
        readonly=True,
    )
    material_note = fields.Char(string="หมายเหตุ", readonly=True)
    request_count = fields.Integer(string="จำนวนคำของบ", readonly=True)

    @api.depends(
        "disbursed_amount",
        "payable_amount",
        "committed_not_received_amount",
    )
    def _compute_total_spent_amount(self):
        for line in self:
            line.total_spent_amount = (
                line.disbursed_amount
                + line.payable_amount
                + line.committed_not_received_amount
            )


class DepartmentalBudgetCoverWizard(models.TransientModel):
    _name = "departmental.budget.request.cover.wizard"
    _description = "Departmental Budget Request Cover Wizard"

    fiscal_year = fields.Char(
        string="ปีงบประมาณ",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year + 543),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    fund_source_id = fields.Many2one(
        comodel_name="vpk.budget.fund.source",
        string="แหล่งเงิน",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน / ศูนย์ต้นทุน",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    line_ids = fields.One2many(
        comodel_name="departmental.budget.request.cover.line",
        inverse_name="wizard_id",
        string="รายการใบปะหน้า",
    )
    total_asset_above_amount = fields.Float(compute="_compute_totals", digits=0)
    total_asset_below_amount = fields.Float(compute="_compute_totals", digits=0)
    total_construction_amount = fields.Float(compute="_compute_totals", digits=0)
    total_amount = fields.Float(compute="_compute_totals", digits=0)

    @api.depends(
        "line_ids.asset_above_amount",
        "line_ids.asset_below_amount",
        "line_ids.construction_amount",
    )
    def _compute_totals(self):
        for wizard in self:
            wizard.total_asset_above_amount = sum(
                wizard.line_ids.mapped("asset_above_amount")
            )
            wizard.total_asset_below_amount = sum(
                wizard.line_ids.mapped("asset_below_amount")
            )
            wizard.total_construction_amount = sum(
                wizard.line_ids.mapped("construction_amount")
            )
            wizard.total_amount = (
                wizard.total_asset_above_amount
                + wizard.total_asset_below_amount
                + wizard.total_construction_amount
            )

    def _fiscal_year_search_values(self):
        self.ensure_one()
        request_model = self.env["departmental.budget.request"]
        be_year = request_model._fiscal_year_to_be(self.fiscal_year)
        ce_year = request_model._fiscal_year_to_ce(self.fiscal_year)
        values = set()
        if be_year:
            values.add(str(be_year))
        if ce_year:
            values.add(str(ce_year))
        return list(values)

    def _base_line_domain(self):
        self.ensure_one()
        domain = [
            ("request_id.fiscal_year", "in", self._fiscal_year_search_values()),
            ("request_id.state", "!=", "rejected"),
        ]
        if self.fund_source_id:
            domain.append(("request_id.fund_source_id", "=", self.fund_source_id.id))
        if self.analytic_account_id:
            domain.append(
                ("request_id.analytic_account_id", "=", self.analytic_account_id.id)
            )
        return domain

    def _is_below_asset_form(self, form_type):
        label = "%s %s" % (form_type.name or "", form_type.code or "")
        normalized = label.replace(",", "").replace(" ", "")
        return "ต่ำกว่าแสน" in normalized or "100000" in normalized

    def action_load_cover(self):
        self.ensure_one()
        if not self.fiscal_year:
            raise UserError(_("กรุณาระบุปีงบประมาณ"))

        self.line_ids.unlink()
        grouped = {}
        line_domain = self._base_line_domain() + [
            ("section_key", "in", ("asset", "construction")),
        ]
        request_lines = self.env["departmental.budget.request.line"].search(
            line_domain,
            order="request_id, sequence, id",
        )

        for line in request_lines:
            analytic = line.request_id.analytic_account_id
            if not analytic:
                continue
            vals = grouped.setdefault(
                analytic.id,
                {
                    "analytic_account_id": analytic.id,
                    "department_name": analytic.name or "",
                    "asset_above_amount": 0.0,
                    "asset_below_amount": 0.0,
                    "construction_amount": 0.0,
                },
            )
            if line.section_key == "construction":
                vals["construction_amount"] += line.total_amount or 0.0
            elif self._is_below_asset_form(line.request_id.form_type_id):
                vals["asset_below_amount"] += line.total_amount or 0.0
            else:
                vals["asset_above_amount"] += line.total_amount or 0.0

        line_commands = []
        sequence = 10
        for vals in sorted(grouped.values(), key=lambda item: item["department_name"]):
            if not (
                vals["asset_above_amount"]
                or vals["asset_below_amount"]
                or vals["construction_amount"]
            ):
                continue
            vals["sequence"] = sequence
            line_commands.append((0, 0, vals))
            sequence += 10
        self.write({"line_ids": line_commands})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _generate_cover_xlsx(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(
                _("ไม่พบไลบรารี xlsxwriter กรุณาติดตั้งแพ็กเกจ python xlsxwriter")
            )
        if not self.line_ids:
            raise UserError(_("กรุณากดแสดงใบปะหน้าก่อนส่งออก Excel"))

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("ใบปะหน้า")
        worksheet.set_portrait()
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(left=0.25, right=0.25, top=0.4, bottom=0.4)

        title_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "font_size": 12,
            }
        )
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True,
            }
        )
        total_header_fmt = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True,
                "bg_color": "#BFBFBF",
            }
        )
        cell_fmt = workbook.add_format({"border": 1, "valign": "vcenter"})
        center_fmt = workbook.add_format(
            {"border": 1, "align": "center", "valign": "vcenter"}
        )
        money_fmt = workbook.add_format(
            {
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
            }
        )
        total_label_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#FFF2CC",
            }
        )
        total_money_fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "num_format": "#,##0.00",
                "align": "right",
                "valign": "vcenter",
                "bg_color": "#FFF2CC",
            }
        )

        worksheet.set_column(0, 0, 6)
        worksheet.set_column(1, 1, 42)
        worksheet.set_column(2, 4, 18)
        worksheet.set_column(5, 5, 18)

        title = (
            "รายละเอียดคำขอตั้งแผนเงินบำรุง โรงพยาบาลวชิระภูเก็ต "
            f"ปีงบประมาณ {self.fiscal_year}"
        )
        worksheet.merge_range(0, 0, 0, 5, title, title_fmt)
        worksheet.merge_range(1, 0, 3, 0, "ลำดับ", header_fmt)
        worksheet.merge_range(1, 1, 3, 1, "หน่วยงาน/กลุ่มงาน", header_fmt)
        worksheet.merge_range(1, 2, 1, 3, "ครุภัณฑ์", header_fmt)
        worksheet.write(2, 2, "100,000 บาท ขึ้นไป", header_fmt)
        worksheet.write(2, 3, "ต่ำกว่า 100,000 บาท", header_fmt)
        worksheet.write(3, 2, "งบประมาณ", header_fmt)
        worksheet.write(3, 3, "งบประมาณ", header_fmt)
        worksheet.merge_range(1, 4, 2, 4, "สิ่งก่อสร้าง", header_fmt)
        worksheet.write(3, 4, "งบประมาณ", header_fmt)
        worksheet.merge_range(1, 5, 3, 5, "รวมทั้งหมด", total_header_fmt)

        row = 4
        for index, line in enumerate(
            self.line_ids.sorted(lambda item: item.sequence),
            start=1,
        ):
            worksheet.write(row, 0, index, center_fmt)
            worksheet.write(row, 1, line.department_name or "", cell_fmt)
            worksheet.write_number(row, 2, line.asset_above_amount or 0.0, money_fmt)
            worksheet.write_number(row, 3, line.asset_below_amount or 0.0, money_fmt)
            worksheet.write_number(row, 4, line.construction_amount or 0.0, money_fmt)
            worksheet.write_number(row, 5, line.total_amount or 0.0, money_fmt)
            row += 1

        worksheet.merge_range(row, 0, row, 1, "รวม", total_label_fmt)
        worksheet.write_number(row, 2, self.total_asset_above_amount or 0.0, total_money_fmt)
        worksheet.write_number(row, 3, self.total_asset_below_amount or 0.0, total_money_fmt)
        worksheet.write_number(row, 4, self.total_construction_amount or 0.0, total_money_fmt)
        worksheet.write_number(row, 5, self.total_amount or 0.0, total_money_fmt)

        workbook.close()
        output.seek(0)
        return output.read()

    def action_export_excel(self):
        self.ensure_one()
        content = self._generate_cover_xlsx()
        filename = "ใบปะหน้าคำของบ_%s.xlsx" % (self.fiscal_year or "budget")
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


class DepartmentalBudgetCoverLine(models.TransientModel):
    _name = "departmental.budget.request.cover.line"
    _description = "Departmental Budget Request Cover Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="departmental.budget.request.cover.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน / ศูนย์ต้นทุน",
        readonly=True,
    )
    department_name = fields.Char(string="หน่วยงาน/กลุ่มงาน", readonly=True)
    asset_above_amount = fields.Float(
        string="ครุภัณฑ์ 100,000 บาทขึ้นไป",
        digits=0,
        readonly=True,
    )
    asset_below_amount = fields.Float(
        string="ครุภัณฑ์ต่ำกว่า 100,000 บาท",
        digits=0,
        readonly=True,
    )
    construction_amount = fields.Float(
        string="สิ่งก่อสร้าง",
        digits=0,
        readonly=True,
    )
    total_amount = fields.Float(
        string="รวม",
        compute="_compute_total_amount",
        digits=0,
        readonly=True,
    )

    @api.depends("asset_above_amount", "asset_below_amount", "construction_amount")
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = (
                line.asset_above_amount
                + line.asset_below_amount
                + line.construction_amount
            )
