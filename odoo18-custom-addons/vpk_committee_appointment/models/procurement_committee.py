from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def html_notify_body(template, **values):
    """Build HTML for message_notify/message_post without showing raw tags."""
    safe = {}
    for key, value in values.items():
        if isinstance(value, Markup):
            safe[key] = value
        else:
            safe[key] = escape(value or "")
    return Markup(str(template)) % safe


class ProcurementCommittee(models.Model):
    _inherit = "procurement.committee"

    committee_type = fields.Selection(
        selection_add=[
            ("price_mid", "คณะกรรมการกำหนดคุณลักษณะและราคากลาง"),
        ],
        ondelete={
            "price_mid": lambda recs: recs.write({"committee_type": "procurement"}),
        },
    )
    approve_role = fields.Selection(
        selection_add=[
            ("secretary", "เลขานุการ"),
        ],
        ondelete={
            "secretary": lambda recs: recs.write({"approve_role": "committee"}),
        },
    )
    confirm_state = fields.Selection(
        [
            ("not_sent", "ยังไม่ส่งคำขอ"),
            ("pending", "รอตอบ"),
            ("accepted", "ยินยอมแล้ว"),
            ("declined", "ไม่สามารถรับได้"),
        ],
        string="สถานะยินยอม",
        default="not_sent",
        required=True,
        copy=False,
        index=True,
    )
    confirm_request_date = fields.Datetime(
        string="วันที่ส่งคำขอยืนยัน",
        readonly=True,
        copy=False,
    )
    confirm_reply_date = fields.Datetime(
        string="วันที่ตอบคำขอยืนยัน",
        readonly=True,
        copy=False,
    )
    confirm_requested_by = fields.Many2one(
        "res.users",
        string="ผู้ส่งคำขอยืนยัน",
        readonly=True,
        copy=False,
    )
    confirm_note = fields.Char(
        string="เหตุผลที่ไม่รับ",
        copy=False,
    )
    confirm_activity_id = fields.Many2one(
        "mail.activity",
        string="กิจกรรมยืนยันกรรมการ",
        copy=False,
        ondelete="set null",
    )
    _sql_constraints = [
        (
            "employee_request_uniq",
            "unique(employee_id, request_id, committee_type)",
            "คนเดียวกันห้ามซ้ำในคณะกรรมการชุดเดียวกัน",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Reuse an existing row when the form resends a saved member as a new line."""
        last_by_key = {}
        key_order = []
        incomplete = []
        for vals in vals_list:
            request_id = vals.get("request_id")
            employee_id = vals.get("employee_id")
            committee_type = vals.get("committee_type")
            if request_id and employee_id and committee_type:
                key = (int(request_id), int(employee_id), committee_type)
                if key not in last_by_key:
                    key_order.append(key)
                last_by_key[key] = vals
            else:
                incomplete.append(vals)

        records = self.browse()
        to_create = []
        for key in key_order:
            vals = last_by_key[key]
            existing = self.search(
                [
                    ("request_id", "=", key[0]),
                    ("employee_id", "=", key[1]),
                    ("committee_type", "=", key[2]),
                ],
                limit=1,
            )
            if existing:
                write_vals = {name: value for name, value in vals.items() if name != "request_id"}
                if write_vals:
                    existing.write(write_vals)
                records |= existing
            else:
                to_create.append(vals)
        to_create.extend(incomplete)
        if to_create:
            records |= super().create(to_create)
        return records

    def write(self, vals):
        if "employee_id" in vals and "confirm_state" not in vals:
            vals = dict(
                vals,
                confirm_state="not_sent",
                confirm_request_date=False,
                confirm_reply_date=False,
                confirm_requested_by=False,
                confirm_note=False,
                confirm_activity_id=False,
            )
        return super().write(vals)

    def _committee_type_label(self):
        self.ensure_one()
        return dict(
            self._fields["committee_type"]._description_selection(self.env)
        ).get(self.committee_type, self.committee_type or "")

    def _committee_role_label(self):
        self.ensure_one()
        return dict(
            self._fields["approve_role"]._description_selection(self.env)
        ).get(self.approve_role, self.approve_role or "")

    def _confirm_user(self):
        self.ensure_one()
        return self.employee_id.user_id if self.employee_id else self.env["res.users"]

    def _check_confirm_user(self):
        self.ensure_one()
        user = self._confirm_user()
        if not user or user != self.env.user:
            raise UserError(_("เฉพาะกรรมการที่ถูกเสนอในใบขอซื้อนี้เท่านั้นที่ตอบคำขอยืนยันได้"))
        if self.confirm_state != "pending":
            raise UserError(_("ไม่มีคำขอยืนยันที่รอท่านตอบสำหรับรายการนี้"))
        return user

    def _close_confirm_activity(self):
        activities = self.mapped("confirm_activity_id").filtered(lambda act: act.exists())
        remaining = self.sudo().search(
            [
                ("confirm_activity_id", "in", activities.ids),
                ("id", "not in", self.ids),
                ("confirm_state", "=", "pending"),
            ]
        )
        done = activities - remaining.mapped("confirm_activity_id")
        for activity in done:
            if activity.exists():
                activity.action_feedback()
        self.sudo().write({"confirm_activity_id": False})

    def _notify_requester_reply(self, accepted):
        self.ensure_one()
        request = self.request_id
        if not request:
            return
        requester = self.confirm_requested_by or request.requested_by
        partner = requester.partner_id if requester else False
        if not partner:
            return
        role = "%s (%s)" % (self._committee_role_label(), self._committee_type_label())
        if accepted:
            subject = _("กรรมการยินยอมแล้ว — %s") % request.display_name
            body = html_notify_body(
                _("<p><b>%(name)s</b> ยืนยันว่าสามารถเป็น%(role)s ได้</p><p>ใบขอซื้อ: %(pr)s</p>"),
                name=self.display_name,
                role=role,
                pr=request.display_name,
            )
        else:
            subject = _("กรรมการไม่สามารถรับได้ — %s") % request.display_name
            body = html_notify_body(
                _(
                    "<p><b>%(name)s</b> แจ้งว่าไม่สามารถเป็น%(role)s ได้</p>"
                    "<p>ใบขอซื้อ: %(pr)s</p>"
                    "<p>เหตุผล: %(reason)s</p>"
                ),
                name=self.display_name,
                role=role,
                pr=request.display_name,
                reason=self.confirm_note or "-",
            )
        request.message_notify(
            partner_ids=partner.ids,
            subject=subject,
            body=body,
        )
        request.message_post(body=body, message_type="notification")

    def action_accept_confirm(self):
        """กรรมการยืนยันว่าสามารถรับเป็นกรรมการได้"""
        for rec in self:
            rec._check_confirm_user()
            rec.sudo().write(
                {
                    "confirm_state": "accepted",
                    "confirm_reply_date": fields.Datetime.now(),
                    "confirm_note": False,
                }
            )
            rec._close_confirm_activity()
            rec._notify_requester_reply(True)
        return True

    def action_decline_confirm(self, reason=False):
        """กรรมการแจ้งว่าไม่สามารถรับเป็นกรรมการได้"""
        for rec in self:
            rec._check_confirm_user()
            rec.sudo().write(
                {
                    "confirm_state": "declined",
                    "confirm_reply_date": fields.Datetime.now(),
                    "confirm_note": reason or False,
                }
            )
            rec._close_confirm_activity()
            rec._notify_requester_reply(False)
        return True
