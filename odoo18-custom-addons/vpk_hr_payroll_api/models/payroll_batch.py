# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class VpkHrPayrollBatch(models.Model):
    _name = "vpk.hr.payroll.batch"
    _description = "ชุดเงินเดือนจาก HR"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, copy=False, default=lambda self: _("ใหม่"), tracking=True)
    external_id = fields.Char(string="รหัสภายนอก", required=True, index=True, tracking=True)
    source_system = fields.Char(string="ระบบต้นทาง", required=True, default="hr", index=True)
    pay_date = fields.Date(string="วันที่จ่าย", required=True, tracking=True)
    period = fields.Char(string="งวด", tracking=True)
    description = fields.Char(string="คำอธิบาย")
    state = fields.Selection(
        [
            ("draft", "ร่าง"),
            ("ready", "พร้อมผ่าน"),
            ("posted", "ลงบัญชีแล้ว"),
            ("error", "ผิดพลาด"),
            ("cancelled", "ยกเลิก"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="สมุดรายวัน",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        check_company=True,
    )
    move_id = fields.Many2one("account.move", string="รายการสมุดรายวัน", copy=False, readonly=True)
    line_ids = fields.One2many("vpk.hr.payroll.line", "batch_id", string="รายการ")
    debit_total = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    credit_total = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    control_debit_total = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="company_id.currency_id")
    error_message = fields.Text(string="ข้อความผิดพลาด")

    _sql_constraints = [
        (
            "external_source_company_uniq",
            "unique(external_id, source_system, company_id)",
            "ชุดเงินเดือนนี้รับเข้าแล้ว",
        ),
    ]

    @api.depends("line_ids.amount", "line_ids.side", "line_ids.line_state")
    def _compute_totals(self):
        for batch in self:
            debit = credit = 0.0
            for line in batch.line_ids.filtered(lambda item: item.line_state == "ok"):
                if line.side == "debit":
                    debit += line.amount
                elif line.side == "credit":
                    credit += line.amount
            batch.debit_total = debit
            batch.credit_total = credit

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("ใหม่"):
                vals["name"] = sequence.next_by_code("vpk.hr.payroll.batch") or _("ใหม่")
        return super().create(vals_list)

    def action_validate(self):
        for batch in self:
            if batch.state == "posted":
                raise UserError(_("ชุด %s ลงบัญชีแล้ว") % batch.name)
            if batch.state == "cancelled":
                raise UserError(_("ชุด %s ถูกยกเลิก") % batch.name)
            batch.line_ids._validate_line()
            errors = batch.line_ids.filtered(lambda line: line.line_state == "error")
            message = []
            if errors:
                message.extend(errors.mapped("error_message"))
            rounding = batch.currency_id.rounding or 0.01
            if not errors and float_compare(
                batch.debit_total, batch.credit_total, precision_rounding=rounding
            ):
                message.append(
                    _("ยอดเดบิต %(debit)s ไม่เท่ากับเครดิต %(credit)s")
                    % {"debit": batch.debit_total, "credit": batch.credit_total}
                )
            if (
                not errors
                and not float_is_zero(batch.control_debit_total, precision_rounding=rounding)
                and float_compare(
                    batch.debit_total,
                    batch.control_debit_total,
                    precision_rounding=rounding,
                )
            ):
                message.append(
                    _("ยอดเดบิตไม่ตรงยอดควบคุม %(control)s")
                    % {"control": batch.control_debit_total}
                )
            if not batch.line_ids:
                message.append(_("ไม่มีรายการเงินเดือน"))
            batch.write(
                {
                    "state": "error" if message else "ready",
                    "error_message": "\n".join(message) if message else False,
                }
            )
        return True

    def action_post(self):
        for batch in self:
            if batch.state == "posted":
                continue
            batch.action_validate()
            if batch.state != "ready":
                raise UserError(batch.error_message or _("ชุดข้อมูลยังผ่านไม่ได้"))
            move = batch._create_payroll_move()
            move.action_post()
            batch.write({"move_id": move.id, "state": "posted", "error_message": False})
            batch.message_post(
                body=_("สร้างสมุดรายวัน %s จากชุดเงินเดือน HR") % move.name
            )
        return True

    def action_open_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการสมุดรายวัน"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.move_id.id,
        }

    def action_cancel(self):
        posted = self.filtered(lambda batch: batch.state == "posted")
        if posted:
            raise UserError(_("ชุดที่ลงบัญชีแล้วต้องกลับรายการที่สมุดรายวัน"))
        self.filtered(lambda batch: batch.state != "cancelled").write({"state": "cancelled"})
        return True

    def _payroll_journal(self):
        self.ensure_one()
        journal = self.journal_id or self.company_id.vpk_hr_payroll_journal_id
        if not journal:
            journal = self.env["account.journal"].search(
                [
                    ("type", "=", "general"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if not journal:
            raise UserError(_("ยังไม่กำหนดสมุดรายวันเงินเดือน"))
        return journal

    def _create_payroll_move(self):
        self.ensure_one()
        journal = self._payroll_journal()
        self.journal_id = journal.id
        label = self.description or _("เงินเดือน %(period)s") % {"period": self.period or self.pay_date}
        commands = []
        for line in self.line_ids:
            name = line.description or line.component_map_id.name or line.component_code
            if line.department_code:
                name = "%s [%s]" % (name, line.department_code)
            commands.append(
                fields.Command.create(
                    {
                        "name": name,
                        "account_id": line.account_id.id,
                        "debit": line.amount if line.side == "debit" else 0.0,
                        "credit": line.amount if line.side == "credit" else 0.0,
                    }
                )
            )
        return self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": self.pay_date,
                "ref": "%s %s" % (self.name, self.external_id),
                "company_id": self.company_id.id,
                "line_ids": commands,
                "narration": label,
            }
        )

    def to_api_dict(self):
        self.ensure_one()
        errors = [
            {"line_external_id": line.line_external_id or False, "message": line.error_message}
            for line in self.line_ids
            if line.line_state == "error" and line.error_message
        ]
        if self.error_message and self.state == "error":
            errors.append({"line_external_id": False, "message": self.error_message})
        return {
            "ok": self.state != "error",
            "batch_id": self.id,
            "name": self.name,
            "external_id": self.external_id,
            "source_system": self.source_system,
            "state": self.state,
            "pay_date": fields.Date.to_string(self.pay_date) if self.pay_date else False,
            "period": self.period or False,
            "debit_total": self.debit_total,
            "credit_total": self.credit_total,
            "move_id": self.move_id.id or False,
            "move_name": self.move_id.name or False,
            "errors": errors,
        }


class VpkHrPayrollLine(models.Model):
    _name = "vpk.hr.payroll.line"
    _description = "รายการในชุดเงินเดือน HR"
    _order = "id"

    batch_id = fields.Many2one(
        "vpk.hr.payroll.batch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="batch_id.company_id", store=True)
    line_external_id = fields.Char(string="รหัสบรรทัด")
    component_code = fields.Char(string="รหัสเงินเดือน", required=True)
    component_map_id = fields.Many2one("vpk.hr.payroll.component.map", string="แมป")
    description = fields.Char(string="คำอธิบาย")
    department_code = fields.Char(string="หน่วยงาน")
    amount = fields.Monetary(string="จำนวนเงิน", currency_field="currency_id", required=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    side = fields.Selection(related="component_map_id.side", store=True)
    account_id = fields.Many2one(related="component_map_id.account_id", store=True)
    line_state = fields.Selection(
        [("ok", "ผ่าน"), ("error", "ผิดพลาด")],
        default="ok",
        required=True,
    )
    error_message = fields.Char()

    def _validate_line(self):
        Map = self.env["vpk.hr.payroll.component.map"]
        for line in self:
            errors = []
            code = (line.component_code or "").strip()
            component = Map.search(
                [
                    ("code", "=", code),
                    ("company_id", "=", line.company_id.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            line.component_map_id = component.id if component else False
            if not component:
                errors.append(_("ไม่พบรหัสเงินเดือน %s") % code)
            elif not component.account_id:
                errors.append(_("รหัส %s ยังไม่ผูกบัญชี") % code)
            if float_compare(line.amount, 0.0, precision_digits=2) <= 0:
                errors.append(_("จำนวนเงินต้องมากกว่าศูนย์"))
            line.write(
                {
                    "line_state": "error" if errors else "ok",
                    "error_message": " ".join(errors) if errors else False,
                }
            )
