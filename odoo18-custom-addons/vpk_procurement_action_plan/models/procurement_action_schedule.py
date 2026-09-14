from odoo import fields, models


FISCAL_MONTH_SELECTION = [
    ("10", "ต.ค."),
    ("11", "พ.ย."),
    ("12", "ธ.ค."),
    ("01", "ม.ค."),
    ("02", "ก.พ."),
    ("03", "มี.ค."),
    ("04", "เม.ย."),
    ("05", "พ.ค."),
    ("06", "มิ.ย."),
    ("07", "ก.ค."),
    ("08", "ส.ค."),
    ("09", "ก.ย."),
]


class ProcurementActionSchedule(models.Model):
    """รายเดือนของแผนปฏิบัติการจัดซื้อจัดจ้าง (ปีงบประมาณ ต.ค.–ก.ย.)"""

    _name = "procurement.action.schedule"
    _description = "แผนปฏิบัติการรายเดือน"
    _order = "plan_line_id, sequence, month"

    plan_line_id = fields.Many2one(
        comodel_name="procurement.annual.plan.line",
        string="รายการแผน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    plan_id = fields.Many2one(
        related="plan_line_id.plan_id",
        store=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    month = fields.Selection(
        selection=FISCAL_MONTH_SELECTION,
        string="เดือน",
        required=True,
    )
    plan_approve = fields.Boolean(
        string="แผนอนุมัติ/ประกาศ",
        help="แผนการอนุมัติจัดซื้อ/จ้าง/เช่า หรือประกาศ",
    )
    plan_commit = fields.Boolean(
        string="แผนก่อหนี้ผูกพัน",
        help="วางแผนก่อหนี้ผูกพัน (PO/สัญญา)",
    )
    plan_delivery = fields.Boolean(
        string="แผนส่งมอบ",
        help="วางแผนกำหนดส่งมอบงาน/พัสดุ",
    )
    plan_disburse = fields.Boolean(
        string="แผนเบิกเงิน",
        help="วางแผนเบิกจ่ายเงินตามงวด",
    )
    note = fields.Char(string="หมายเหตุ")
    company_id = fields.Many2one(related="plan_line_id.company_id", store=True)

    def _compute_display_name(self):
        labels = dict(FISCAL_MONTH_SELECTION)
        for rec in self:
            parts = []
            if rec.plan_approve:
                parts.append("อนุมัติ/ประกาศ")
            if rec.plan_commit:
                parts.append("ก่อหนี้")
            if rec.plan_delivery:
                parts.append("ส่งมอบ")
            if rec.plan_disburse:
                parts.append("เบิกเงิน")
            rec.display_name = "%s: %s" % (
                labels.get(rec.month, rec.month or ""),
                ", ".join(parts) or "-",
            )
