from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CommitteeConfirmWizard(models.TransientModel):
    _name = "procurement.committee.confirm.wizard"
    _description = "ยืนยันการเป็นกรรมการ"

    request_id = fields.Many2one(
        "purchase.request",
        string="ใบขอซื้อ",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    line_ids = fields.Many2many(
        "procurement.committee",
        string="รายการที่ขอความยินยอม",
        readonly=True,
    )
    summary = fields.Html(compute="_compute_summary")
    decline_reason = fields.Char(string="เหตุผลที่ไม่สามารถรับได้")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        request_id = values.get("request_id")
        if not request_id and self.env.context.get("active_model") == "purchase.request":
            request_id = self.env.context.get("active_id")
        if request_id:
            request = self.env["purchase.request"].browse(int(request_id))
            if request.exists():
                lines = request._committee_members().filtered(
                    lambda line: line.confirm_state == "pending"
                    and line.employee_id.user_id == self.env.user
                )
                values["request_id"] = request.id
                values["line_ids"] = [(6, 0, lines.ids)]
        return values

    @api.depends("line_ids", "request_id")
    def _compute_summary(self):
        for wizard in self:
            rows = []
            for line in wizard.line_ids:
                rows.append(
                    "<li>%s — %s</li>"
                    % (line._committee_role_label(), line._committee_type_label())
                )
            wizard.summary = _(
                "<p>ท่านถูกเสนอเป็นกรรมการในใบขอซื้อ <b>%(pr)s</b></p>"
                "<p>กรุณายืนยันว่าสามารถรับเป็นกรรมการได้ ก่อนเสนอแต่งตั้ง</p>"
                "<ul>%(rows)s</ul>"
            ) % {
                "pr": wizard.request_id.display_name if wizard.request_id else "-",
                "rows": "".join(rows),
            }

    def action_accept(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("ไม่มีรายการที่รอท่านยืนยัน"))
        self.line_ids.sudo().action_accept_confirm()
        return {"type": "ir.actions.act_window_close"}

    def action_decline(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("ไม่มีรายการที่รอท่านยืนยัน"))
        self.line_ids.sudo().action_decline_confirm(self.decline_reason)
        return {"type": "ir.actions.act_window_close"}
