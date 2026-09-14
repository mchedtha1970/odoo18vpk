from odoo import fields, models


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
        string="คณะกรรมการกำหนดราคากลาง",
        domain=[("committee_type", "=", "price_mid")],
    )

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
