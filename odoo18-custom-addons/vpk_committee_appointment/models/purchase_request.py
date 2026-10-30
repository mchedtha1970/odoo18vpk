from collections import defaultdict

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .procurement_committee import html_notify_body


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    committee_appointment_ids = fields.One2many(
        comodel_name="procurement.committee.appointment",
        inverse_name="request_id",
        string="เอกสารแต่งตั้งคณะกรรมการ",
    )
    committee_appointment_count = fields.Integer(
        compute="_compute_committee_appointment_count",
    )
    price_mid_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="คณะกรรมการกำหนดคุณลักษณะและราคากลาง",
        domain=[("committee_type", "=", "price_mid")],
    )
    committee_member_count = fields.Integer(
        compute="_compute_committee_confirm_status",
    )
    committee_confirm_summary = fields.Char(
        string="สรุปความยินยอมกรรมการ",
        compute="_compute_committee_confirm_status",
    )
    committee_confirm_all_accepted = fields.Boolean(
        compute="_compute_committee_confirm_status",
    )
    committee_confirm_pending_mine = fields.Boolean(
        compute="_compute_committee_confirm_status",
        search="_search_committee_confirm_pending_mine",
    )

    def _committee_members(self):
        self.ensure_one()
        members = self.procurement_committee_ids | self.work_acceptance_committee_ids
        if "price_mid_committee_ids" in self._fields:
            members |= self.price_mid_committee_ids
        return members

    @api.depends(
        "procurement_committee_ids.confirm_state",
        "procurement_committee_ids.employee_id",
        "work_acceptance_committee_ids.confirm_state",
        "work_acceptance_committee_ids.employee_id",
        "price_mid_committee_ids.confirm_state",
        "price_mid_committee_ids.employee_id",
    )
    def _compute_committee_confirm_status(self):
        uid = self.env.uid
        for rec in self:
            members = rec._committee_members()
            rec.committee_member_count = len(members)
            accepted = members.filtered(lambda line: line.confirm_state == "accepted")
            pending = members.filtered(lambda line: line.confirm_state == "pending")
            declined = members.filtered(lambda line: line.confirm_state == "declined")
            not_sent = members.filtered(lambda line: line.confirm_state == "not_sent")
            rec.committee_confirm_all_accepted = bool(members) and not (
                members - accepted
            )
            rec.committee_confirm_pending_mine = bool(
                pending.filtered(lambda line: line.employee_id.user_id.id == uid)
            )
            if not members:
                rec.committee_confirm_summary = False
            else:
                rec.committee_confirm_summary = _(
                    "ยินยอม %(accepted)s / รอตอบ %(pending)s / ไม่รับ %(declined)s / ยังไม่ส่ง %(not_sent)s"
                ) % {
                    "accepted": len(accepted),
                    "pending": len(pending),
                    "declined": len(declined),
                    "not_sent": len(not_sent),
                }

    def _search_committee_confirm_pending_mine(self, operator, value):
        lines = self.env["procurement.committee"].search(
            [
                ("employee_id.user_id", "=", self.env.uid),
                ("confirm_state", "=", "pending"),
            ]
        )
        request_ids = lines.mapped("request_id").ids
        if operator not in ("=", "!="):
            return []
        include = bool(value) if operator == "=" else not bool(value)
        return [("id", "in" if include else "not in", request_ids)]

    def action_request_committee_confirm(self):
        """ส่ง notify ในระบบให้กรรมการที่ยืนยันว่าสามารถรับเป็นกรรมการได้"""
        for rec in self:
            rec._request_committee_confirm()
        return True

    def _request_committee_confirm(self):
        self.ensure_one()
        members = self._committee_members().filtered("employee_id")
        if not members:
            raise UserError(_("กรุณาระบุกรรมการในใบขอซื้อก่อนส่งคำขอยืนยัน"))

        skipped = members.filtered(lambda line: not line._confirm_user())
        targets = members - skipped
        already_accepted = targets.filtered(lambda line: line.confirm_state == "accepted")
        to_notify = targets - already_accepted
        if not to_notify and not skipped:
            raise UserError(_("กรรมการทุกคนยืนยันแล้ว ไม่ต้องส่งคำขอซ้ำ"))
        if not to_notify and skipped:
            raise UserError(
                _(
                    "ไม่สามารถส่ง notify ได้ เพราะกรรมการต่อไปนี้ยังไม่มีผู้ใช้ในระบบ:\n%s"
                )
                % "\n".join("- %s" % name for name in skipped.mapped("display_name"))
            )

        now = fields.Datetime.now()
        by_user = defaultdict(lambda: self.env["procurement.committee"])
        for line in to_notify:
            by_user[line._confirm_user()] |= line

        for user, lines in by_user.items():
            role_lines = Markup("").join(
                Markup("<li>%s — %s</li>")
                % (
                    escape(line._committee_role_label()),
                    escape(line._committee_type_label()),
                )
                for line in lines
            )
            subject = _("ขอความยินยอมเป็นกรรมการ — %s") % self.display_name
            body = html_notify_body(
                _(
                    "<p>เรียน %(name)s</p>"
                    "<p>ท่านถูกเสนอเป็นกรรมการในใบขอซื้อ <b>%(pr)s</b> ดังนี้</p>"
                    "<ul>%(roles)s</ul>"
                    "<p>กรุณาเปิดใบขอซื้อนี้ แล้วกด <b>ยืนยันว่าสามารถเป็นกรรมการได้</b> "
                    "ก่อนเสนอแต่งตั้ง</p>"
                ),
                name=user.display_name,
                pr=self.display_name,
                roles=role_lines,
            )
            self.message_notify(
                partner_ids=user.partner_id.ids,
                subject=subject,
                body=body,
            )
            existing_activity = lines.mapped("confirm_activity_id").filtered(
                lambda act: act.exists() and act.user_id == user
            )[:1]
            activity = existing_activity or self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                summary=_("ยืนยันการเป็นกรรมการ — %s") % self.name,
                note=_(
                    "ท่านถูกเสนอเป็นกรรมการในใบขอซื้อ %(pr)s\n"
                    "กรุณาเปิดใบขอซื้อแล้วกดยืนยันว่าสามารถรับเป็นกรรมการได้"
                )
                % {"pr": self.display_name},
            )
            lines.write(
                {
                    "confirm_state": "pending",
                    "confirm_request_date": now,
                    "confirm_reply_date": False,
                    "confirm_requested_by": self.env.user.id,
                    "confirm_note": False,
                    "confirm_activity_id": activity.id,
                }
            )

        self.message_post(
            body=_(
                "ส่งคำขอยืนยันเป็นกรรมการในระบบแล้ว %(count)s คน"
            )
            % {"count": len(by_user)},
            message_type="notification",
        )
        if skipped:
            self.message_post(
                body=_(
                    "กรรมการต่อไปนี้ยังไม่มีผู้ใช้ในระบบ จึงยังไม่ได้รับ notify: %s"
                )
                % ", ".join(skipped.mapped("display_name")),
                message_type="notification",
            )
        return True

    def action_open_my_committee_confirm(self):
        """เปิดหน้าต่างให้กรรมการที่ถูกเสนอตอบคำขอยืนยัน"""
        self.ensure_one()
        lines = self._committee_members().filtered(
            lambda line: line.confirm_state == "pending"
            and line.employee_id.user_id == self.env.user
        )
        if not lines:
            raise UserError(_("ไม่มีคำขอยืนยันที่รอท่านตอบในใบขอซื้อนี้"))
        wizard = self.env["procurement.committee.confirm.wizard"].create(
            {
                "request_id": self.id,
                "line_ids": [(6, 0, lines.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("ยืนยันการเป็นกรรมการ"),
            "res_model": "procurement.committee.confirm.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_committee_select_wizard(self):
        self.ensure_one()
        committee_type = self.env.context.get("committee_type")
        if not committee_type:
            return False
        labels = dict(
            self.env["procurement.committee"]._fields["committee_type"]._description_selection(self.env)
        )
        return {
            "type": "ir.actions.act_window",
            "name": "เลือกกรรมการ: %s" % labels.get(committee_type, ""),
            "res_model": "procurement.committee.select.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
                "default_committee_type": committee_type,
            },
        }

    def _compute_committee_appointment_count(self):
        Appointment = self.env["procurement.committee.appointment"].sudo()
        counts = dict(
            (row["request_id"][0], row["request_id_count"])
            for row in Appointment.read_group(
                [("request_id", "in", self.ids)],
                ["request_id"],
                ["request_id"],
            )
        )
        for rec in self:
            rec.committee_appointment_count = counts.get(rec.id, 0)

    def action_view_committee_appointments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "แต่งตั้งคณะกรรมการ",
            "res_model": "procurement.committee.appointment",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": {
                "default_request_id": self.id,
                "default_department_id": self.department_id.id,
            },
        }

    def action_create_committee_appointment(self):
        self.ensure_one()
        members = self._committee_members()
        pending = members.filtered(lambda line: line.confirm_state != "accepted")
        if pending:
            details = "\n".join(
                "- %s (%s / %s): %s"
                % (
                    line.display_name,
                    line._committee_role_label(),
                    line._committee_type_label(),
                    dict(line._fields["confirm_state"].selection).get(
                        line.confirm_state, line.confirm_state
                    ),
                )
                for line in pending
            )
            raise UserError(
                _(
                    "กรุณาให้กรรมการยืนยันว่าสามารถรับเป็นกรรมการได้ก่อนเสนอแต่งตั้ง:\n%s"
                )
                % details
            )
        appointment = self.env["procurement.committee.appointment"].create({
            "request_id": self.id,
            "department_id": self.department_id.id,
            "subject": "ขออนุมัติแต่งตั้งคณะกรรมการซื้อจ้าง ตามใบขอซื้อ %s"
            % self.name,
        })
        return {
            "type": "ir.actions.act_window",
            "name": "แต่งตั้งคณะกรรมการ",
            "res_model": "procurement.committee.appointment",
            "res_id": appointment.id,
            "view_mode": "form",
            "target": "current",
        }
