from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionAwardReport(models.Model):
    _name = "purchase.requisition.award.report"
    _description = "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อสั่งจ้าง"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่รายงาน",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่รายงาน",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ eGP",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        domain=[("requisition_type", "=", "egp_procurement")],
    )
    purchase_request_id = fields.Many2one(
        related="requisition_id.purchase_request_id",
        string="ใบขอซื้ออ้างอิง",
        readonly=True,
    )
    egp_reference = fields.Char(
        related="requisition_id.egp_reference",
        string="เลขที่โครงการ e-GP",
        readonly=True,
    )
    subject = fields.Char(
        string="เรื่อง",
        required=True,
        default="รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง",
        tracking=True,
    )
    committee_meeting_date = fields.Date(
        string="วันที่คณะกรรมการพิจารณา",
        tracking=True,
    )
    evaluation_method = fields.Selection(
        selection=[
            ("lowest_price", "เกณฑ์ราคาต่ำสุด"),
            ("price_performance", "เกณฑ์ราคาและประสิทธิภาพ"),
            ("qualification", "เกณฑ์คุณสมบัติและเงื่อนไข"),
        ],
        string="เกณฑ์การพิจารณา",
        required=True,
        default="lowest_price",
        tracking=True,
    )
    winner_bid_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid",
        string="ข้อเสนอที่ได้รับการคัดเลือก",
        domain="[('requisition_id', '=', requisition_id)]",
        tracking=True,
    )
    winner_partner_id = fields.Many2one(
        related="winner_bid_id.partner_id",
        string="ผู้ชนะการเสนอราคา",
        readonly=True,
        store=True,
    )
    winner_amount = fields.Monetary(
        related="winner_bid_id.amount_total",
        string="วงเงินที่ขออนุมัติ",
        currency_field="currency_id",
        readonly=True,
        store=True,
    )
    currency_id = fields.Many2one(
        related="requisition_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="requisition_id.company_id",
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.requisition.award.report.line",
        inverse_name="report_id",
        string="ผลการพิจารณาผู้เสนอราคา",
        copy=True,
    )
    result_summary = fields.Html(
        string="สรุปผลการพิจารณา",
        default=(
            "<p>คณะกรรมการได้ตรวจสอบคุณสมบัติ เอกสารข้อเสนอ "
            "และเปรียบเทียบราคาของผู้ยื่นข้อเสนอแล้ว</p>"
        ),
    )
    recommendation = fields.Html(
        string="ข้อเสนอเพื่ออนุมัติ",
        default=(
            "<p>จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติสั่งซื้อ/สั่งจ้าง "
            "จากผู้เสนอราคาที่ได้รับการคัดเลือก และดำเนินการในขั้นตอนต่อไป</p>"
        ),
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string="วันที่อนุมัติ",
        readonly=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("to_approve", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("rejected", "ไม่อนุมัติ"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )

    _sql_constraints = [
        (
            "requisition_report_uniq",
            "unique(requisition_id)",
            "กระบวนการ eGP นี้มีรายงานผลการพิจารณาแล้ว",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "purchase.requisition.award.report"
                    )
                    or _("New")
                )
        reports = super().create(vals_list)
        reports._generate_lines_from_bids()
        return reports

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        if self.requisition_id:
            self.subject = _(
                "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง โครงการ %s"
            ) % (
                self.requisition_id.egp_project_name
                or self.requisition_id.display_name
            )
            self.winner_bid_id = (
                self.requisition_id.egp_bid_ids.filtered("is_winner")[:1]
            )

    def _generate_lines_from_bids(self):
        for report in self:
            if report.line_ids or not report.requisition_id:
                continue
            commands = []
            for sequence, bid in enumerate(
                report.requisition_id.egp_bid_ids, start=1
            ):
                commands.append((0, 0, {
                    "sequence": sequence * 10,
                    "bid_id": bid.id,
                    "partner_id": bid.partner_id.id,
                    "egp_bid_reference": bid.egp_bid_reference,
                    "bid_date": bid.bid_date,
                    "amount_total": bid.amount_total,
                    "result": (
                        "winner"
                        if bid == report.winner_bid_id or bid.is_winner
                        else "not_selected"
                    ),
                }))
            if commands:
                report.line_ids = commands

    def action_generate_results(self):
        for report in self:
            if report.state != "draft":
                raise UserError(_("สร้างผลการพิจารณาใหม่ได้เฉพาะสถานะร่าง"))
            report.line_ids.unlink()
            report._generate_lines_from_bids()
            if not report.line_ids:
                raise UserError(
                    _("ยังไม่มีข้อเสนอราคาในกระบวนการ eGP สำหรับจัดทำรายงาน")
                )
        return True

    def _sync_winner(self):
        for report in self:
            winner = report.winner_bid_id
            if not winner:
                continue
            (report.requisition_id.egp_bid_ids - winner).write(
                {"is_winner": False}
            )
            winner.write({"is_winner": True})
            for line in report.line_ids:
                line.result = (
                    "winner" if line.bid_id == winner else "not_selected"
                )

    def _update_line_results(self):
        for report in self:
            for line in report.line_ids:
                line.result = (
                    "winner"
                    if line.bid_id == report.winner_bid_id
                    else "not_selected"
                )

    def action_submit(self):
        for report in self:
            if not report.line_ids:
                raise UserError(_("กรุณาสร้างรายการผลการพิจารณาก่อน"))
            if not report.winner_bid_id:
                raise UserError(_("กรุณาเลือกข้อเสนอที่ได้รับการคัดเลือก"))
            if not report.winner_amount:
                raise UserError(_("ข้อเสนอที่ได้รับการคัดเลือกยังไม่มีราคา"))
            report._update_line_results()
            report.state = "to_approve"
        return True

    def action_approve(self):
        self._sync_winner()
        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
        })
        return True

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({
            "state": "draft",
            "approved_by": False,
            "approved_date": False,
        })

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_purchase_agreement_egp.action_report_award_approval"
        ).report_action(self)

    def action_create_winner_announcement(self):
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("ต้องอนุมัติรายงานผลก่อนสร้างประกาศผู้ชนะ"))
        return self.requisition_id.action_create_winner_announcement()


class PurchaseRequisitionAwardReportLine(models.Model):
    _name = "purchase.requisition.award.report.line"
    _description = "ผลการพิจารณาผู้เสนอราคา"
    _order = "sequence, id"

    report_id = fields.Many2one(
        comodel_name="purchase.requisition.award.report",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    bid_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid",
        string="ข้อเสนอราคา",
        ondelete="set null",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้เสนอราคา",
        required=True,
    )
    egp_bid_reference = fields.Char(string="เลขที่ใบเสนอราคา")
    bid_date = fields.Date(string="วันที่เสนอราคา")
    currency_id = fields.Many2one(
        related="report_id.currency_id",
        store=True,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="ราคาที่เสนอ",
        currency_field="currency_id",
    )
    result = fields.Selection(
        selection=[
            ("winner", "ได้รับการคัดเลือก"),
            ("not_selected", "ไม่ถูกคัดเลือก"),
            ("disqualified", "ไม่ผ่านคุณสมบัติ"),
        ],
        string="ผลการพิจารณา",
        default="not_selected",
        required=True,
    )
    notes = fields.Char(string="เหตุผล/หมายเหตุ")


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    award_report_ids = fields.One2many(
        comodel_name="purchase.requisition.award.report",
        inverse_name="requisition_id",
        string="รายงานผลการพิจารณา",
        copy=False,
    )
    award_report_count = fields.Integer(
        compute="_compute_award_report_count",
    )
    egp_award_approved = fields.Boolean(
        string="รายงานผลได้รับอนุมัติแล้ว",
        compute="_compute_egp_award_approved",
    )

    @api.depends("award_report_ids")
    def _compute_award_report_count(self):
        for requisition in self:
            requisition.award_report_count = len(requisition.award_report_ids)

    @api.depends("award_report_ids.state")
    def _compute_egp_award_approved(self):
        for requisition in self:
            requisition.egp_award_approved = bool(
                requisition.award_report_ids.filtered(
                    lambda report: report.state == "approved"
                )
            )

    def action_create_award_report(self):
        self.ensure_one()
        if len(self.egp_bid_ids) < 1:
            raise UserError(
                _("ต้องมีข้อเสนอราคาอย่างน้อย 1 รายการก่อนจัดทำรายงานผล")
            )
        report = self.award_report_ids[:1]
        if not report:
            winner = self.egp_bid_ids.filtered("is_winner")[:1]
            report = self.env["purchase.requisition.award.report"].create({
                "requisition_id": self.id,
                "winner_bid_id": winner.id if winner else False,
                "committee_meeting_date": fields.Date.context_today(self),
            })
        return {
            "type": "ir.actions.act_window",
            "name": _("รายงานผลการพิจารณาและขออนุมัติ"),
            "res_model": "purchase.requisition.award.report",
            "res_id": report.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_award_reports(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายงานผลการพิจารณา"),
            "res_model": "purchase.requisition.award.report",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {"default_requisition_id": self.id},
        }
