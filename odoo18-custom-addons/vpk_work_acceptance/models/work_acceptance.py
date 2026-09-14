# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    # --- Contract link ---
    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญาอ้างอิง",
        related="purchase_id.contract_id",
        store=True,
        readonly=True,
    )
    contract_installment_id = fields.Many2one(
        comodel_name="purchase.contract.installment",
        string="งวดงาน",
        tracking=True,
        domain="[('contract_id', '=', contract_id)]",
    )

    # --- Committee / Inspector ---
    committee_ids = fields.One2many(
        comodel_name="work.acceptance.committee",
        inverse_name="wa_id",
        string="คณะกรรมการตรวจรับ",
        copy=True,
    )
    inspector_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ควบคุมงาน/ผู้ตรวจรับ",
        tracking=True,
    )

    # --- Acceptance detail ---
    acceptance_type = fields.Selection(
        selection=[
            ("full", "ตรวจรับครบถ้วน"),
            ("partial", "ตรวจรับบางส่วน"),
            ("reject", "ไม่ผ่านการตรวจรับ"),
        ],
        string="ผลการตรวจรับ",
        default="full",
        tracking=True,
    )
    acceptance_date = fields.Date(
        string="วันที่ตรวจรับ",
        default=fields.Date.context_today,
    )
    delivery_date = fields.Date(
        string="วันที่ส่งมอบงาน",
    )
    due_date_contract = fields.Date(
        string="วันครบกำหนดตามสัญญา",
    )
    is_late = fields.Boolean(
        string="ส่งงานล่าช้า",
        compute="_compute_is_late",
        store=True,
    )
    late_days = fields.Integer(
        string="จำนวนวันล่าช้า",
        compute="_compute_is_late",
        store=True,
    )
    penalty_amount = fields.Monetary(
        string="ค่าปรับ",
        currency_field="currency_id",
    )
    acceptance_note = fields.Text(
        string="รายละเอียดการตรวจรับ",
    )
    warranty_end_date = fields.Date(
        string="วันสิ้นสุดประกัน",
    )

    # --- Computed amounts ---
    amount_total = fields.Monetary(
        string="มูลค่ารวม",
        compute="_compute_amount_total",
        store=True,
        currency_field="currency_id",
    )
    requester_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="ผู้ขอซื้อ/ขอจ้าง",
        compute="_compute_requester_notification",
    )
    requester_email_to = fields.Char(
        string="อีเมลผู้ขอซื้อ/ขอจ้าง",
        compute="_compute_requester_notification",
    )
    requester_notification_status = fields.Selection(
        selection=[
            ("pending", "รอส่ง"),
            ("queued", "เข้าคิวส่งแล้ว"),
            ("no_email", "ไม่พบอีเมลผู้ขอ"),
            ("error", "ส่งไม่สำเร็จ"),
        ],
        string="สถานะแจ้งผู้ขอ",
        default="pending",
        readonly=True,
        copy=False,
        tracking=True,
    )
    requester_notified_at = fields.Datetime(
        string="วันที่แจ้งผู้ขอ",
        readonly=True,
        copy=False,
    )
    requester_notification_error = fields.Text(
        string="ข้อผิดพลาดการแจ้งเตือน",
        readonly=True,
        copy=False,
    )
    requester_notification_mail_ids = fields.Many2many(
        comodel_name="mail.mail",
        relation="work_acceptance_requester_mail_rel",
        column1="work_acceptance_id",
        column2="mail_id",
        string="อีเมลแจ้งผู้ขอ",
        readonly=True,
        copy=False,
    )

    @api.depends("delivery_date", "due_date_contract")
    def _compute_is_late(self):
        for rec in self:
            if rec.delivery_date and rec.due_date_contract:
                delta = (rec.delivery_date - rec.due_date_contract).days
                rec.is_late = delta > 0
                rec.late_days = max(delta, 0)
            else:
                rec.is_late = False
                rec.late_days = 0

    @api.depends("wa_line_ids.price_subtotal")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.wa_line_ids.mapped("price_subtotal"))

    @api.depends(
        "purchase_id.order_line.purchase_request_lines.request_id.requested_by",
        "purchase_id.order_line.purchase_request_lines.request_id.requested_by.email",
    )
    def _compute_requester_notification(self):
        for acceptance in self:
            requests = acceptance.purchase_id.order_line.mapped(
                "purchase_request_lines.request_id"
            )
            requesters = requests.mapped("requested_by")
            acceptance.requester_user_ids = requesters
            acceptance.requester_email_to = ", ".join(
                requesters.filtered("email").mapped("email")
            )

    def button_accept(self, force=False):
        for rec in self:
            if rec.acceptance_type == "reject":
                raise UserError(
                    _("ไม่สามารถตรวจรับได้ เนื่องจากผลการตรวจรับเป็น 'ไม่ผ่าน'")
                )
            if not rec.wa_line_ids:
                raise UserError(_("กรุณาระบุรายการตรวจรับอย่างน้อย 1 รายการ"))
        result = super().button_accept(force=force)
        self.filtered(
            lambda acceptance: acceptance.state == "accept"
            and acceptance.requester_notification_status != "queued"
        ).action_send_requester_notification()
        return result

    def action_send_requester_notification(self):
        template = self.env.ref(
            "vpk_work_acceptance.mail_template_requester_acceptance_completed"
        )
        for acceptance in self:
            if acceptance.state != "accept":
                raise UserError(
                    _("ส่งอีเมลแจ้งผู้ขอได้หลังตรวจรับเรียบร้อยแล้วเท่านั้น")
                )
            if not acceptance.requester_email_to:
                acceptance.write({
                    "requester_notification_status": "no_email",
                    "requester_notification_error": (
                        "ไม่พบอีเมลผู้ขอซื้อ/ขอจ้างจาก PR ต้นทาง"
                    ),
                })
                acceptance.message_post(
                    body=_("ไม่พบอีเมลผู้ขอซื้อ/ขอจ้างจาก PR ต้นทาง")
                )
                continue
            try:
                mail_id = template.send_mail(
                    acceptance.id,
                    force_send=False,
                    email_values={
                        "email_to": acceptance.requester_email_to,
                    },
                )
                acceptance.write({
                    "requester_notification_status": "queued",
                    "requester_notified_at": fields.Datetime.now(),
                    "requester_notification_error": False,
                    "requester_notification_mail_ids": [(4, mail_id)],
                })
                acceptance.message_post(
                    body=_(
                        "เข้าคิวส่งอีเมลแจ้งผลตรวจรับให้ผู้ขอแล้ว: %s"
                    )
                    % acceptance.requester_email_to
                )
            except Exception as error:
                acceptance.write({
                    "requester_notification_status": "error",
                    "requester_notification_error": str(error),
                })

    def button_draft(self):
        result = super().button_draft()
        self.write({
            "requester_notification_status": "pending",
            "requester_notified_at": False,
            "requester_notification_error": False,
        })
        return result

    @api.onchange("purchase_id")
    def _onchange_purchase_id_contract(self):
        if self.purchase_id and self.purchase_id.contract_id:
            contract = self.purchase_id.contract_id
            pr_lines = self.purchase_id.order_line.mapped(
                "purchase_request_lines"
            )
            installment = pr_lines.mapped("contract_installment_id")[:1]
            if installment:
                self.contract_installment_id = installment
            if contract.date_end:
                self.due_date_contract = contract.date_end


class WorkAcceptanceCommittee(models.Model):
    _name = "work.acceptance.committee"
    _description = "คณะกรรมการตรวจรับ"
    _order = "sequence, id"

    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        string="ใบตรวจรับ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string="ชื่อ-สกุล",
        required=True,
    )
    position = fields.Char(
        string="ตำแหน่ง",
    )
    role = fields.Selection(
        selection=[
            ("chairman", "ประธานกรรมการ"),
            ("member", "กรรมการ"),
            ("secretary", "กรรมการและเลขานุการ"),
        ],
        string="บทบาท",
        default="member",
        required=True,
    )
    employee_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ใช้งาน",
    )
    note = fields.Char(string="หมายเหตุ")
