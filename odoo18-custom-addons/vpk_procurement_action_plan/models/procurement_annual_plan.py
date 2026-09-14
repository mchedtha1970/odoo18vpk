from odoo import api, fields, models


class ProcurementAnnualPlan(models.Model):
    _inherit = "procurement.annual.plan"

    is_action_plan = fields.Boolean(
        string="เป็นแผนปฏิบัติการ",
        default=True,
        tracking=True,
        help="แผนปฏิบัติการจัดซื้อจัดจ้างประจำปี "
             "(แผนอนุมัติ/ประกาศ, ก่อหนี้ผูกพัน, ส่งมอบ, เบิกเงิน)",
    )
    action_schedule_count = fields.Integer(
        string="จำนวนแผนรายเดือน",
        compute="_compute_action_schedule_count",
    )

    @api.depends("line_ids.action_schedule_ids")
    def _compute_action_schedule_count(self):
        Schedule = self.env["procurement.action.schedule"]
        for plan in self:
            plan.action_schedule_count = Schedule.search_count(
                [("plan_id", "=", plan.id)]
            )

    def action_view_action_schedules(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "แผนปฏิบัติการรายเดือน",
            "res_model": "procurement.action.schedule",
            "view_mode": "list,form",
            "domain": [("plan_id", "=", self.id)],
            "context": {
                "default_plan_id": self.id,
                "search_default_group_plan_line": 1,
            },
        }


class ProcurementAnnualPlanLine(models.Model):
    _inherit = "procurement.annual.plan.line"

    method_type = fields.Selection(
        selection=[
            ("specific", "เฉพาะเจาะจง"),
            ("egp", "e-GP / ประกาศ"),
            ("direct", "ซื้อโดยตรง"),
            ("lease", "เช่า"),
            ("hire", "จ้าง"),
            ("other", "อื่นๆ"),
        ],
        string="วิธีการจัดหา",
        default="egp",
    )
    date_approve_plan = fields.Date(
        string="แผนอนุมัติ/ประกาศ",
        help="กำหนดการอนุมัติจัดซื้อ/จ้าง/เช่า หรือประกาศ",
    )
    date_commit_plan = fields.Date(
        string="แผนก่อหนี้ผูกพัน",
        help="กำหนดก่อหนี้ผูกพัน (สั่งซื้อ/ทำสัญญา)",
    )
    date_delivery_plan = fields.Date(
        string="แผนส่งมอบ",
        help="กำหนดส่งมอบพัสดุ/งาน",
    )
    date_disburse_plan = fields.Date(
        string="แผนเบิกเงิน",
        help="กำหนดเบิกจ่ายเงิน",
    )
    action_schedule_ids = fields.One2many(
        comodel_name="procurement.action.schedule",
        inverse_name="plan_line_id",
        string="แผนปฏิบัติการรายเดือน",
    )
    schedule_summary = fields.Char(
        string="สรุปแผนปฏิบัติการ",
        compute="_compute_schedule_summary",
    )

    @api.depends(
        "date_approve_plan",
        "date_commit_plan",
        "date_delivery_plan",
        "date_disburse_plan",
        "action_schedule_ids.month",
        "action_schedule_ids.plan_approve",
        "action_schedule_ids.plan_commit",
        "action_schedule_ids.plan_delivery",
        "action_schedule_ids.plan_disburse",
    )
    def _compute_schedule_summary(self):
        month_labels = dict(self.env["procurement.action.schedule"]._fields["month"].selection)
        for line in self:
            parts = []
            if line.date_approve_plan:
                parts.append("อนุมัติ/ประกาศ %s" % line.date_approve_plan)
            if line.date_commit_plan:
                parts.append("ก่อหนี้ %s" % line.date_commit_plan)
            if line.date_delivery_plan:
                parts.append("ส่งมอบ %s" % line.date_delivery_plan)
            if line.date_disburse_plan:
                parts.append("เบิกเงิน %s" % line.date_disburse_plan)
            for sched in line.action_schedule_ids:
                flags = []
                if sched.plan_approve:
                    flags.append("อ")
                if sched.plan_commit:
                    flags.append("ก")
                if sched.plan_delivery:
                    flags.append("ส")
                if sched.plan_disburse:
                    flags.append("บ")
                if flags:
                    parts.append(
                        "%s[%s]" % (month_labels.get(sched.month, sched.month), "".join(flags))
                    )
            line.schedule_summary = " | ".join(parts) if parts else False
