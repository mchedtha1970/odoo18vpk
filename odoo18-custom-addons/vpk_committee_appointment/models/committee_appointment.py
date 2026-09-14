from odoo import _, api, fields, models
from odoo.exceptions import UserError


COMMITTEE_TYPE_SELECTION = [
    ("price_mid", "คณะกรรมการกำหนดราคากลาง"),
    ("procurement", "คณะกรรมการจัดซื้อจัดจ้าง"),
    ("work_acceptance", "คณะกรรมการตรวจรับ"),
]

ROLE_SELECTION = [
    ("chairman", "ประธาน"),
    ("committee", "กรรมการ"),
    ("secretary", "เลขานุการ"),
]


class CommitteeAppointment(models.Model):
    _name = "procurement.committee.appointment"
    _description = "เอกสารแต่งตั้งคณะกรรมการซื้อจ้าง"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่เอกสาร",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    subject = fields.Char(
        string="เรื่อง",
        default="ขออนุมัติแต่งตั้งคณะกรรมการซื้อจ้าง",
        required=True,
        tracking=True,
    )
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ/จ้าง/เช่า",
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="หน่วยงาน",
        tracking=True,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้จัดทำ",
        default=lambda self: self.env.user,
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string="วันเวลาที่อนุมัติ",
        readonly=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("to_approve", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="procurement.committee.appointment.line",
        inverse_name="appointment_id",
        string="รายชื่อคณะกรรมการ",
        copy=True,
    )
    note = fields.Html(string="รายละเอียด/เหตุผล")
    email_sent = fields.Boolean(
        string="ส่งอีเมลแจ้งแล้ว",
        readonly=True,
        copy=False,
    )
    line_count = fields.Integer(compute="_compute_line_count")
    has_price_mid = fields.Boolean(compute="_compute_committee_flags", store=True)
    has_procurement = fields.Boolean(compute="_compute_committee_flags", store=True)
    has_work_acceptance = fields.Boolean(compute="_compute_committee_flags", store=True)

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends("line_ids.committee_type")
    def _compute_committee_flags(self):
        for rec in self:
            types = set(rec.line_ids.mapped("committee_type"))
            rec.has_price_mid = "price_mid" in types
            rec.has_procurement = "procurement" in types
            rec.has_work_acceptance = "work_acceptance" in types

    @api.onchange("request_id")
    def _onchange_request_id(self):
        if self.request_id:
            self.department_id = self.request_id.department_id
            if self.request_id.name:
                self.subject = _(
                    "ขออนุมัติแต่งตั้งคณะกรรมการซื้อจ้าง ตามใบขอซื้อ %s"
                ) % self.request_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "procurement.committee.appointment"
                    )
                    or _("New")
                )
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("กรุณาระบุรายชื่อคณะกรรมการอย่างน้อย 1 คน"))
            rec.state = "to_approve"
        return True

    def action_approve(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("กรุณาระบุรายชื่อคณะกรรมการอย่างน้อย 1 คน"))
            rec.write({
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })
            if rec.request_id:
                rec._sync_committees_to_pr()
            rec._notify_committee_members_approved()
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({
            "state": "draft",
            "approved_by": False,
            "approved_date": False,
            "email_sent": False,
        })

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_committee_appointment.action_report_committee_appointment"
        ).report_action(self)

    def _sync_committees_to_pr(self):
        """ซิงก์รายชื่อไปยังคณะกรรมการบน PR (แยกประเภท — คนละคนต่อประเภท)"""
        self.ensure_one()
        pr = self.request_id
        if not pr:
            return
        Committee = self.env["procurement.committee"]
        # ลบรายการเดิมของประเภทที่มีในเอกสารนี้
        types = set(self.line_ids.mapped("committee_type"))
        # รองรับเฉพาะประเภทที่มีบน procurement.committee
        sync_types = types & {"price_mid", "procurement", "work_acceptance"}
        if not sync_types:
            return
        existing = Committee.search([
            ("request_id", "=", pr.id),
            ("committee_type", "in", list(sync_types)),
        ])
        existing.unlink()
        for line in self.line_ids.filtered(lambda l: l.committee_type in sync_types):
            if not line.employee_id:
                continue
            # unique (employee_id, request_id) — ข้ามถ้าคนเดียวกันถูกใส่หลายประเภท
            if Committee.search_count([
                ("request_id", "=", pr.id),
                ("employee_id", "=", line.employee_id.id),
            ]):
                continue
            role = line.approve_role
            if role == "secretary" and role not in dict(
                Committee._fields["approve_role"].selection
            ):
                role = "committee"
            Committee.create({
                "request_id": pr.id,
                "employee_id": line.employee_id.id,
                "name": line.name or line.employee_id.name,
                "committee_type": line.committee_type,
                "approve_role": role if role in ("chairman", "committee", "secretary") else "committee",
                "note": line.note or _("จากเอกสารแต่งตั้ง %s") % self.name,
            })

    def _get_notify_partners(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        for line in self.line_ids:
            emp = line.employee_id
            if not emp:
                continue
            if emp.user_id and emp.user_id.partner_id:
                partners |= emp.user_id.partner_id
            elif emp.work_contact_id:
                partners |= emp.work_contact_id
            elif emp.work_email:
                # สร้าง/หา partner จากอีเมลชั่วคราวสำหรับส่งเมล
                partner = self.env["res.partner"].search([
                    ("email", "=", emp.work_email),
                ], limit=1)
                if not partner:
                    partner = self.env["res.partner"].sudo().create({
                        "name": emp.name,
                        "email": emp.work_email,
                        "type": "contact",
                    })
                partners |= partner
        return partners

    def _notify_committee_members_approved(self):
        """ส่งอีเมล + แจ้ง Inbox เมื่ออนุมัติแต่งตั้งแล้ว"""
        template = self.env.ref(
            "vpk_committee_appointment.mail_template_committee_appointed",
            raise_if_not_found=False,
        )
        for rec in self:
            partners = rec._get_notify_partners()
            if not partners:
                rec.message_post(
                    body=_(
                        "อนุมัติแต่งตั้งแล้ว แต่ไม่พบอีเมล/ผู้ใช้ของกรรมการสำหรับแจ้งเตือน"
                    ),
                    message_type="notification",
                )
                continue
            rec.message_subscribe(partner_ids=partners.ids)
            body = _(
                "<p><b>อนุมัติแต่งตั้งคณะกรรมการซื้อจ้างแล้ว</b></p>"
                "<ul>"
                "<li>เลขที่เอกสาร: %(name)s</li>"
                "<li>เรื่อง: %(subject)s</li>"
                "<li>ใบขอซื้ออ้างอิง: %(pr)s</li>"
                "<li>วันที่อนุมัติ: %(date)s</li>"
                "</ul>"
                "<p>กรุณาตรวจสอบรายละเอียดและปฏิบัติหน้าที่ตามที่ได้รับแต่งตั้ง</p>"
            ) % {
                "name": rec.name,
                "subject": rec.subject or "-",
                "pr": rec.request_id.display_name if rec.request_id else "-",
                "date": rec.approved_date or "-",
            }
            subject = _("แจ้งแต่งตั้งคณะกรรมการ — %s") % rec.name
            rec.message_notify(
                partner_ids=partners.ids,
                body=body,
                subject=subject,
            )
            rec.message_post(
                body=body,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )
            # ส่งอีเมลทีละคน (ระบุ email_to ให้ชัดเจน)
            if template:
                for line in rec.line_ids:
                    email = line.email or (
                        line.employee_id.work_email if line.employee_id else False
                    )
                    if not email and line.employee_id and line.employee_id.user_id:
                        email = line.employee_id.user_id.email
                    if not email:
                        continue
                    template.send_mail(
                        rec.id,
                        force_send=False,
                        email_values={
                            "email_to": email,
                            "recipient_ids": [],
                        },
                    )
            # กิจกรรมให้ผู้ที่มี user
            for line in rec.line_ids:
                user = line.employee_id.user_id if line.employee_id else False
                if user:
                    rec.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=user.id,
                        summary=_("แต่งตั้งคณะกรรมการ — %s") % rec.name,
                        note=_(
                            "ท่านได้รับการแต่งตั้งเป็น%(role)s ใน%(ctype)s\n"
                            "เอกสาร: %(name)s\nใบขอซื้อ: %(pr)s"
                        )
                        % {
                            "role": dict(ROLE_SELECTION).get(
                                line.approve_role, line.approve_role
                            ),
                            "ctype": dict(COMMITTEE_TYPE_SELECTION).get(
                                line.committee_type, line.committee_type
                            ),
                            "name": rec.name,
                            "pr": rec.request_id.display_name
                            if rec.request_id
                            else "-",
                        },
                    )
            rec.email_sent = True


class CommitteeAppointmentLine(models.Model):
    _name = "procurement.committee.appointment.line"
    _description = "รายชื่อคณะกรรมการในเอกสารแต่งตั้ง"
    _order = "committee_type, sequence, id"

    appointment_id = fields.Many2one(
        comodel_name="procurement.committee.appointment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    committee_type = fields.Selection(
        selection=COMMITTEE_TYPE_SELECTION,
        string="ประเภทคณะกรรมการ",
        required=True,
        default="procurement",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="พนักงาน",
        required=True,
        ondelete="restrict",
    )
    name = fields.Char(
        string="ชื่อ-สกุล",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
    )
    department_id = fields.Many2one(
        related="employee_id.department_id",
        store=True,
    )
    email = fields.Char(
        string="อีเมล",
        compute="_compute_from_employee",
        store=True,
        readonly=False,
    )
    approve_role = fields.Selection(
        selection=ROLE_SELECTION,
        string="ตำแหน่งในคณะ",
        required=True,
        default="committee",
    )
    note = fields.Char(string="หมายเหตุ")
    company_id = fields.Many2one(related="appointment_id.company_id", store=True)

    @api.depends("employee_id")
    def _compute_from_employee(self):
        for line in self:
            if line.employee_id:
                line.name = line.employee_id.name
                line.email = (
                    line.employee_id.work_email
                    or (line.employee_id.user_id.email if line.employee_id.user_id else False)
                )
            else:
                line.name = False
                line.email = False
