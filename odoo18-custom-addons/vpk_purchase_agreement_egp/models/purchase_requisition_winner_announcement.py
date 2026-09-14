from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionWinnerAnnouncement(models.Model):
    _name = "purchase.requisition.winner.announcement"
    _description = "ประกาศผู้ชนะการเสนอราคา"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่ประกาศ",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่ประกาศ",
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
    award_report_id = fields.Many2one(
        comodel_name="purchase.requisition.award.report",
        string="รายงานผลการพิจารณาที่อนุมัติ",
        required=True,
        ondelete="restrict",
        domain="[('requisition_id', '=', requisition_id), ('state', '=', 'approved')]",
        tracking=True,
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
        default="ประกาศผู้ชนะการเสนอราคา",
        tracking=True,
    )
    winner_partner_id = fields.Many2one(
        related="award_report_id.winner_partner_id",
        string="ผู้ชนะการเสนอราคา",
        store=True,
        readonly=True,
    )
    winner_amount = fields.Monetary(
        related="award_report_id.winner_amount",
        string="ราคาที่เสนอ",
        currency_field="currency_id",
        store=True,
        readonly=True,
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
    procurement_method_id = fields.Many2one(
        related="requisition_id.procurement_method_id",
        string="วิธีการจัดซื้อจัดจ้าง",
        readonly=True,
    )
    reason = fields.Html(
        string="เหตุผลที่ได้รับการคัดเลือก",
        default=(
            "<p>เป็นผู้มีคุณสมบัติครบถ้วน ถูกต้องตามเงื่อนไข "
            "และเสนอราคาต่ำสุด/เหมาะสม เป็นประโยชน์ต่อทางราชการ</p>"
        ),
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("published", "ประกาศแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    published_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ประกาศ",
        readonly=True,
        tracking=True,
    )
    published_date = fields.Datetime(
        string="วันเวลาที่ประกาศ",
        readonly=True,
        tracking=True,
    )

    _sql_constraints = [
        (
            "requisition_announcement_uniq",
            "unique(requisition_id)",
            "กระบวนการ eGP นี้มีประกาศผู้ชนะแล้ว",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "purchase.requisition.winner.announcement"
                    )
                    or _("New")
                )
        return super().create(vals_list)

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        if self.requisition_id:
            self.award_report_id = self.requisition_id.award_report_ids.filtered(
                lambda report: report.state == "approved"
            )[:1]
            self.subject = _("ประกาศผู้ชนะการเสนอราคา โครงการ %s") % (
                self.requisition_id.egp_project_name
                or self.requisition_id.display_name
            )

    def action_publish(self):
        for announcement in self:
            if announcement.award_report_id.state != "approved":
                raise UserError(
                    _("ต้องอนุมัติรายงานผลการพิจารณาก่อนประกาศผู้ชนะ")
                )
            if not announcement.winner_partner_id:
                raise UserError(_("ไม่พบผู้ชนะการเสนอราคา"))
            announcement.write({
                "state": "published",
                "published_by": self.env.user.id,
                "published_date": fields.Datetime.now(),
            })
            announcement.message_post(
                body=_("เผยแพร่ประกาศผู้ชนะการเสนอราคาแล้ว")
            )
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({
            "state": "draft",
            "published_by": False,
            "published_date": False,
        })

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_purchase_agreement_egp.action_report_winner_announcement"
        ).report_action(self)


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    winner_announcement_ids = fields.One2many(
        comodel_name="purchase.requisition.winner.announcement",
        inverse_name="requisition_id",
        string="ประกาศผู้ชนะ",
        copy=False,
    )
    winner_announcement_count = fields.Integer(
        compute="_compute_winner_announcement_count",
    )

    @api.depends("winner_announcement_ids")
    def _compute_winner_announcement_count(self):
        for requisition in self:
            requisition.winner_announcement_count = len(
                requisition.winner_announcement_ids
            )

    def action_create_winner_announcement(self):
        self.ensure_one()
        approved_report = self.award_report_ids.filtered(
            lambda report: report.state == "approved"
        )[:1]
        if not approved_report:
            raise UserError(
                _(
                    "กรุณาจัดทำและอนุมัติรายงานผลการพิจารณา "
                    "ก่อนสร้างประกาศผู้ชนะ"
                )
            )
        announcement = self.winner_announcement_ids[:1]
        if not announcement:
            announcement = self.env[
                "purchase.requisition.winner.announcement"
            ].create({
                "requisition_id": self.id,
                "award_report_id": approved_report.id,
                "subject": _("ประกาศผู้ชนะการเสนอราคา โครงการ %s")
                % (self.egp_project_name or self.display_name),
            })
        return {
            "type": "ir.actions.act_window",
            "name": _("ประกาศผู้ชนะการเสนอราคา"),
            "res_model": "purchase.requisition.winner.announcement",
            "res_id": announcement.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_winner_announcements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ประกาศผู้ชนะการเสนอราคา"),
            "res_model": "purchase.requisition.winner.announcement",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {"default_requisition_id": self.id},
        }
