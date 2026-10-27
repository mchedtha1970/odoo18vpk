# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EbiddingPlanLine(models.Model):
    _name = "ebidding.plan.line"
    _description = "รายการแผนจัดซื้อจัดจ้างจาก e-GP"
    _inherit = ["mail.thread"]
    _order = "plan_id, sequence, id"
    _rec_name = "project_name"

    plan_id = fields.Many2one(
        comodel_name="ebidding.plan",
        string="ชุดแผน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="ลำดับ", default=10)
    office_code = fields.Char(
        string="รหัสสำนักงานแผนฯ",
        required=True,
        help="รหัสสำนักงานแผนฯ ตามเทมเพลต Excel ของ e-GP (บังคับ)",
    )
    plan_code = fields.Char(
        string="รหัสแผนการจัดซื้อจัดจ้าง",
        index=True,
        copy=False,
        help="รหัสที่ระบบ e-GP ออกให้หลังบันทึกแผน",
    )
    project_name = fields.Char(
        string="ชื่อโครงการที่จะจัดซื้อจัดจ้าง",
        required=True,
    )
    expected_announce_month = fields.Date(
        string="เดือน/ปีที่คาดว่าจะประกาศ",
        required=True,
        help="เลือกเดือนและปี พ.ศ. แสดงเป็น ดด/ปปปป เช่น 06/2569",
    )
    budget_act_amount = fields.Monetary(
        string="เงินงบประมาณตามพ.ร.บ.รายจ่ายประจำปี",
        currency_field="currency_id",
        default=0.0,
    )
    budget_act_type_code = fields.Char(
        string="ประเภทเงินงบประมาณตาม พ.ร.บ.",
        help="รหัสประเภทเงินงบประมาณตาม พ.ร.บ.รายจ่ายประจำปี",
    )
    extra_budget_amount = fields.Monetary(
        string="เงินนอกงบประมาณ",
        currency_field="currency_id",
        default=0.0,
    )
    extra_budget_type_code = fields.Char(
        string="ประเภทเงินนอกงบประมาณ",
        help="รหัสประเภทเงินนอกงบประมาณ",
    )
    agency_budget_amount = fields.Monetary(
        string="เงินงบประมาณหน่วยงาน",
        currency_field="currency_id",
        default=0.0,
    )
    amount_total = fields.Monetary(
        string="จำนวนเงินงบประมาณโครงการ",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    import_type = fields.Selection(
        selection=[
            ("screen", "บันทึกที่หน้าจอ"),
            ("excel", "นำเข้าด้วย Excel"),
        ],
        string="ประเภทการนำเข้า",
        default="screen",
        required=True,
    )
    line_state = fields.Selection(
        selection=[
            ("not_published", "ยังไม่เผยแพร่ขึ้นเว็บไซต์"),
            ("submitted", "เสนอหัวหน้าอนุมัติ"),
            ("published", "เผยแพร่ขึ้นเว็บไซต์"),
        ],
        string="สถานะแผนการจัดซื้อจัดจ้าง",
        default="not_published",
        required=True,
        tracking=True,
        help="สถานะของแผนนี้ในระบบ e-GP การเผยแพร่ทำทีละแผน",
    )
    publish_code = fields.Char(
        string="รหัสเผยแพร่แผน",
        copy=False,
        index=True,
        help="รหัสเผยแพร่แผนจาก e-GP ของแผนนี้",
    )
    publish_round = fields.Integer(
        string="ครั้งที่ประกาศ",
        copy=False,
    )
    publish_date = fields.Date(
        string="วันที่ประกาศบนเว็บไซต์",
        copy=False,
    )
    approval_letter_number = fields.Char(
        string="เลขที่หนังสือขอความเห็นชอบ",
        copy=False,
    )
    approval_letter_date = fields.Date(
        string="วันที่หนังสือขอความเห็นชอบ",
        copy=False,
    )
    announcement_file = fields.Binary(
        string="ไฟล์ประกาศเผยแพร่แผน",
        attachment=True,
        help="ไฟล์ประกาศของแผนนี้ที่ดาวน์โหลดจากระบบ e-GP",
    )
    announcement_filename = fields.Char(string="ชื่อไฟล์ประกาศ")
    fiscal_year = fields.Char(
        related="plan_id.fiscal_year",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="plan_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        related="plan_id.currency_id",
        store=True,
    )
    plan_state = fields.Selection(related="plan_id.state")
    egp_requisition_ids = fields.One2many(
        comodel_name="purchase.requisition",
        inverse_name="ebidding_plan_line_id",
        string="กระบวนการ E-GP",
        copy=False,
    )
    egp_requisition_count = fields.Integer(
        string="จำนวนกระบวนการ E-GP",
        compute="_compute_egp_requisition_count",
    )

    def _compute_egp_requisition_count(self):
        for line in self:
            line.egp_requisition_count = len(line.egp_requisition_ids)

    @api.depends(
        "budget_act_amount",
        "extra_budget_amount",
        "agency_budget_amount",
    )
    def _compute_amount_total(self):
        for line in self:
            line.amount_total = (
                (line.budget_act_amount or 0.0)
                + (line.extra_budget_amount or 0.0)
                + (line.agency_budget_amount or 0.0)
            )

    @api.model
    def _normalize_announce_date(self, value):
        if not value:
            return value
        if isinstance(value, datetime):
            value = value.date()
        elif isinstance(value, str):
            value = fields.Date.to_date(value)
        if isinstance(value, date):
            return value.replace(day=1)
        return value

    @api.constrains(
        "budget_act_amount",
        "extra_budget_amount",
        "agency_budget_amount",
    )
    def _check_amount_source(self):
        for line in self:
            total = (
                (line.budget_act_amount or 0.0)
                + (line.extra_budget_amount or 0.0)
                + (line.agency_budget_amount or 0.0)
            )
            if total <= 0:
                raise ValidationError(
                    _(
                        "ต้องระบุจำนวนเงินอย่างน้อยหนึ่งแหล่ง "
                        "(งบ พ.ร.บ. / นอกงบประมาณ / งบหน่วยงาน) ของโครงการ %s"
                    )
                    % (line.project_name or "")
                )

    @api.depends("plan_code", "project_name")
    def _compute_display_name(self):
        for line in self:
            if line.plan_code:
                line.display_name = "%s — %s" % (
                    line.plan_code,
                    line.project_name or "",
                )
            else:
                line.display_name = line.project_name or _("รายการแผน")

    @api.constrains("plan_code", "fiscal_year", "company_id")
    def _check_plan_code_unique(self):
        for line in self:
            code = (line.plan_code or "").strip()
            if not code:
                continue
            domain = [
                ("id", "!=", line.id),
                ("company_id", "=", line.company_id.id),
                ("fiscal_year", "=", line.fiscal_year),
                ("plan_code", "=", code),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _("รหัสแผนการจัดซื้อจัดจ้าง %s ซ้ำในปีงบประมาณ %s")
                    % (code, line.fiscal_year)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not (vals.get("plan_code") or "").strip():
                vals["plan_code"] = False
            elif vals.get("plan_code"):
                vals["plan_code"] = vals["plan_code"].strip()
            if vals.get("expected_announce_month"):
                vals["expected_announce_month"] = self._normalize_announce_date(
                    vals["expected_announce_month"]
                )
        return super().create(vals_list)

    def write(self, vals):
        if "plan_code" in vals:
            code = (vals.get("plan_code") or "").strip()
            vals["plan_code"] = code or False
        if vals.get("expected_announce_month"):
            vals["expected_announce_month"] = self._normalize_announce_date(
                vals["expected_announce_month"]
            )
        return super().write(vals)

    def action_open_publish_code_wizard(self):
        if not self:
            raise UserError(_("กรุณาเลือกรายการแผนอย่างน้อย 1 รายการ"))
        wizard = self.env["ebidding.plan.publish.code.wizard"].create({
            "plan_id": self[:1].plan_id.id,
            "item_ids": [
                (0, 0, {"plan_line_id": line.id, "selected": True})
                for line in self
            ],
        })
        codes = set(filter(None, self.mapped("publish_code")))
        if len(codes) == 1:
            wizard.publish_code = codes.pop()
        return {
            "type": "ir.actions.act_window",
            "name": _("บันทึกรหัสเผยแพร่แผน"),
            "res_model": "ebidding.plan.publish.code.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_plan(self):
        self.ensure_one()
        if not self.plan_id:
            raise UserError(_("ยังไม่มีชุดแผนของรายการนี้"))
        return {
            "type": "ir.actions.act_window",
            "name": self.plan_id.display_name,
            "res_model": "ebidding.plan",
            "res_id": self.plan_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def _default_egp_procurement_method(self):
        method = self.env.ref(
            "l10n_th_gov_purchase_request.procurement_bidding",
            raise_if_not_found=False,
        )
        if method:
            return method
        return self.env["procurement.method"].search(
            [("name", "ilike", "e-bidding")],
            limit=1,
        )

    def _prepare_egp_requisition_vals(self):
        self.ensure_one()
        if not self.project_name:
            raise UserError(_("กรุณาระบุชื่อโครงการก่อนสร้างกระบวนการ E-GP"))
        vals = {
            "requisition_type": "egp_procurement",
            "egp_project_name": self.project_name,
            "company_id": self.company_id.id,
            "ebidding_plan_line_id": self.id,
            "user_id": self.env.user.id,
            "procurement_nature": "buy",
        }
        method = self._default_egp_procurement_method()
        if method:
            vals["procurement_method_id"] = method.id
        return vals

    def _open_egp_requisition(self, requisition):
        return {
            "type": "ir.actions.act_window",
            "name": _("กระบวนการ E-GP"),
            "res_model": "purchase.requisition",
            "res_id": requisition.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_create_egp_process(self):
        self.ensure_one()
        requisition = self.egp_requisition_ids[:1]
        if requisition:
            return self._open_egp_requisition(requisition)
        requisition = self.env["purchase.requisition"].create(
            self._prepare_egp_requisition_vals()
        )
        self.message_post(
            body=_("สร้างกระบวนการ E-GP %s จากชื่อโครงการแล้ว")
            % requisition.display_name
        )
        return self._open_egp_requisition(requisition)

    def action_open_egp_process(self):
        self.ensure_one()
        requisition = self.egp_requisition_ids[:1]
        if not requisition:
            raise UserError(_("ยังไม่มีกระบวนการ E-GP ของรายการนี้"))
        return self._open_egp_requisition(requisition)

    def get_formview_action(self, access_uid=None):
        if self.env.context.get("open_plan_form") and self[:1].plan_id:
            return self[:1].action_open_plan()
        return super().get_formview_action(access_uid=access_uid)
