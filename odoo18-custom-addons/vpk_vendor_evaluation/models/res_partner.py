from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    vendor_evaluation_ids = fields.One2many(
        comodel_name="vendor.evaluation",
        inverse_name="partner_id",
        string="ผลประเมิน",
    )
    vendor_evaluation_count = fields.Integer(
        compute="_compute_vendor_evaluation_fields",
        string="จำนวนครั้งประเมิน",
    )
    vendor_avg_score = fields.Float(
        compute="_compute_vendor_evaluation_fields",
        string="คะแนนเฉลี่ย (%)",
        digits=(5, 2),
    )
    vendor_latest_grade = fields.Char(
        compute="_compute_vendor_evaluation_fields",
        string="เกรดล่าสุด",
    )
    vendor_latest_grade_desc = fields.Char(
        compute="_compute_vendor_evaluation_fields",
        string="ผลประเมินล่าสุด",
    )

    @api.depends("vendor_evaluation_ids", "vendor_evaluation_ids.state",
                 "vendor_evaluation_ids.total_score", "vendor_evaluation_ids.grade")
    def _compute_vendor_evaluation_fields(self):
        for partner in self:
            evals = partner.vendor_evaluation_ids.filtered(
                lambda e: e.state == "approved"
            )
            partner.vendor_evaluation_count = len(evals)
            if evals:
                partner.vendor_avg_score = sum(evals.mapped("total_score")) / len(evals)
                latest = evals.sorted("evaluation_date", reverse=True)[:1]
                partner.vendor_latest_grade = latest.grade
                partner.vendor_latest_grade_desc = latest.grade_description
            else:
                partner.vendor_avg_score = 0
                partner.vendor_latest_grade = ""
                partner.vendor_latest_grade_desc = ""

    def action_view_vendor_evaluations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "ผลประเมินผู้จำหน่าย",
            "res_model": "vendor.evaluation",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
