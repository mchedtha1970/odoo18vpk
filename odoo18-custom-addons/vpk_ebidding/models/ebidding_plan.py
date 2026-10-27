# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

FISCAL_YEAR_RE = re.compile(r"^\d{4}$")


class EbiddingPlan(models.Model):
    _name = "ebidding.plan"
    _description = "แผนจัดซื้อจัดจ้างจาก e-GP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fiscal_year desc, id desc"
    _rec_name = "name"
    _rec_names_search = ["name", "code", "fiscal_year"]

    name = fields.Char(
        string="ชื่อ",
        required=True,
        tracking=True,
        default=lambda self: self._default_name(),
    )
    code = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
        index=True,
    )
    fiscal_year = fields.Char(
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        size=4,
        default=lambda self: self._default_fiscal_year(),
        help="ปีงบประมาณ พ.ศ. เช่น 2570 — หนึ่งปีงบมีได้หลายแผน",
    )
    notes = fields.Html(string="หมายเหตุ")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("recorded", "บันทึกแล้ว"),
        ],
        string="สถานะการบันทึก",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="ebidding.plan.line",
        inverse_name="plan_id",
        string="รายการแผน",
        copy=True,
    )
    line_count = fields.Integer(
        string="จำนวนแผน",
        compute="_compute_totals",
    )
    amount_total = fields.Monetary(
        string="รวมวงเงินแผน",
        compute="_compute_totals",
        currency_field="currency_id",
        store=True,
    )
    document_ids = fields.One2many(
        comodel_name="ebidding.plan.document",
        inverse_name="plan_id",
        string="เอกสาร e-GP",
        copy=True,
    )
    document_count = fields.Integer(
        string="จำนวนเอกสาร e-GP",
        compute="_compute_document_count",
    )

    _sql_constraints = [
        (
            "fiscal_year_company_uniq",
            "UNIQUE(company_id, fiscal_year)",
            "ปีงบประมาณนี้มีชุดแผนอยู่แล้ว",
        ),
    ]

    @api.model
    def _default_fiscal_year(self):
        today = fields.Date.context_today(self)
        year_ad = today.year
        if today.month >= 10:
            year_ad += 1
        return str(year_ad + 543)

    @api.model
    def _default_name(self):
        return _("แผนการจัดซื้อจัดจ้าง ปีงบประมาณ %s") % self._default_fiscal_year()

    def _name_from_fiscal_year(self, fiscal_year):
        return _("แผนการจัดซื้อจัดจ้าง ปีงบประมาณ %s") % (fiscal_year or "")

    @api.onchange("fiscal_year")
    def _onchange_fiscal_year(self):
        year = (self.fiscal_year or "").strip()
        if not year:
            return
        suggested = self._name_from_fiscal_year(year)
        prefix = _("แผนการจัดซื้อจัดจ้าง ปีงบประมาณ")
        old_prefix = _("แผนจัดซื้อจัดจ้างประจำปีงบประมาณ")
        if (
            not self.name
            or self.name.startswith(prefix)
            or self.name.startswith(old_prefix)
        ):
            self.name = suggested

    @api.depends("line_ids", "line_ids.amount_total")
    def _compute_totals(self):
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.amount_total = sum(plan.line_ids.mapped("amount_total"))

    @api.depends("document_ids")
    def _compute_document_count(self):
        for plan in self:
            plan.document_count = len(plan.document_ids)

    @api.constrains("fiscal_year")
    def _check_fiscal_year(self):
        for plan in self:
            year = (plan.fiscal_year or "").strip()
            if not FISCAL_YEAR_RE.fullmatch(year):
                raise ValidationError(
                    _("ปีงบประมาณต้องเป็นตัวเลข พ.ศ. 4 หลัก เช่น 2570")
                )
            year_int = int(year)
            if year_int < 2500 or year_int > 2700:
                raise ValidationError(
                    _("ปีงบประมาณต้องเป็น พ.ศ. เช่น 2569 หรือ 2570")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", _("New")) == _("New"):
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("ebidding.plan")
                    or _("New")
                )
            if vals.get("fiscal_year"):
                vals["fiscal_year"] = str(vals["fiscal_year"]).strip()
            if not vals.get("name") and vals.get("fiscal_year"):
                vals["name"] = self._name_from_fiscal_year(vals["fiscal_year"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("fiscal_year"):
            vals["fiscal_year"] = str(vals["fiscal_year"]).strip()
        return super().write(vals)

    def action_record(self):
        for plan in self:
            if not plan.line_ids:
                raise UserError(
                    _("ต้องมีรายการแผนอย่างน้อย 1 แผนก่อนยืนยันการบันทึก")
                )
        self.write({"state": "recorded"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("นำเข้าแผนจาก Excel"),
            "res_model": "ebidding.plan.import.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_plan_id": self.id,
            },
        }

    def action_open_publish_code_wizard(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("ต้องมีรายการแผนอย่างน้อย 1 รายการ"))
        wizard = self.env["ebidding.plan.publish.code.wizard"].create({
            "plan_id": self.id,
            "item_ids": [
                (0, 0, {"plan_line_id": line.id, "selected": False})
                for line in self.line_ids
            ],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("บันทึกรหัสเผยแพร่แผน"),
            "res_model": "ebidding.plan.publish.code.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการแผน"),
            "res_model": "ebidding.plan.line",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id},
        }

    def action_view_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("เอกสาร e-GP"),
            "res_model": "ebidding.plan.document",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {"default_plan_id": self.id},
            "views": [(False, "list"), (False, "form")],
        }
