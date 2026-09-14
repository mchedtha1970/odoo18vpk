from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


GRADE_THRESHOLDS = [
    (90, "A", "ดีเยี่ยม"),
    (80, "B", "ดี"),
    (70, "C", "พอใช้"),
    (60, "D", "ต้องปรับปรุง"),
    (0,  "F", "ไม่ผ่านเกณฑ์"),
]


class VendorEvaluation(models.Model):
    _name = "vendor.evaluation"
    _description = "ผลประเมินผู้จำหน่าย"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "evaluation_date desc, id desc"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จำหน่าย",
        required=True,
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ (PO)",
        domain="[('partner_id', '=', partner_id), "
               "('state', 'in', ['purchase', 'done'])]",
        tracking=True,
    )
    evaluation_date = fields.Date(
        string="วันที่ประเมิน",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    period_start = fields.Date(string="ช่วงประเมิน: ตั้งแต่")
    period_end = fields.Date(string="ช่วงประเมิน: ถึง")
    evaluator_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ประเมิน",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("confirmed", "ยืนยัน"),
            ("approved", "อนุมัติ"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="vendor.evaluation.line",
        inverse_name="evaluation_id",
        string="รายการประเมิน",
    )
    total_score = fields.Float(
        string="คะแนนรวม (%)",
        compute="_compute_total_score",
        store=True,
        digits=(5, 2),
        aggregator="avg",
    )
    delivery_score = fields.Float(
        string="คะแนนการจัดส่ง (%)",
        compute="_compute_criteria_scores",
        store=True,
        digits=(5, 2),
        aggregator="avg",
    )
    quality_score = fields.Float(
        string="คะแนนคุณภาพ (%)",
        compute="_compute_criteria_scores",
        store=True,
        digits=(5, 2),
        aggregator="avg",
    )
    price_score = fields.Float(
        string="คะแนนราคา (%)",
        compute="_compute_criteria_scores",
        store=True,
        digits=(5, 2),
        aggregator="avg",
    )
    service_score = fields.Float(
        string="คะแนนบริการ (%)",
        compute="_compute_criteria_scores",
        store=True,
        digits=(5, 2),
        aggregator="avg",
    )
    document_score = fields.Float(
        string="คะแนนเอกสาร (%)",
        compute="_compute_criteria_scores",
        store=True,
        digits=(5, 2),
        aggregator="avg",
    )
    grade = fields.Char(
        string="เกรด",
        compute="_compute_total_score",
        store=True,
    )
    grade_description = fields.Char(
        string="ผลประเมิน",
        compute="_compute_total_score",
        store=True,
    )
    notes = fields.Html(string="หมายเหตุ / ข้อเสนอแนะ")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    @api.depends("line_ids.weighted_score")
    def _compute_total_score(self):
        for rec in self:
            rec.total_score = sum(rec.line_ids.mapped("weighted_score"))
            rec.grade = "N/A"
            rec.grade_description = ""
            for threshold, grade, desc in GRADE_THRESHOLDS:
                if rec.total_score >= threshold:
                    rec.grade = grade
                    rec.grade_description = desc
                    break

    @api.depends("line_ids.score_pct", "line_ids.criteria_id.code")
    def _compute_criteria_scores(self):
        field_by_code = {
            "DELIVERY": "delivery_score",
            "QUALITY": "quality_score",
            "PRICE": "price_score",
            "SERVICE": "service_score",
            "DOCUMENT": "document_score",
        }
        for evaluation in self:
            values = dict.fromkeys(field_by_code.values(), 0.0)
            for line in evaluation.line_ids:
                field_name = field_by_code.get(
                    (line.criteria_id.code or "").upper()
                )
                if field_name:
                    values[field_name] = line.score_pct
            for field_name, score in values.items():
                evaluation[field_name] = score

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("กรุณาเพิ่มรายการประเมินอย่างน้อย 1 เกณฑ์"))
            rec.state = "confirmed"

    def action_approve(self):
        for rec in self:
            rec.state = "approved"
            rec.partner_id._compute_vendor_evaluation_fields()

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_load_criteria(self):
        """โหลดเกณฑ์ประเมินทั้งหมดที่ active อยู่เข้ามาใน line"""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("สามารถโหลดเกณฑ์ได้เฉพาะใบประเมินสถานะร่าง"))
        existing_criteria = self.line_ids.mapped("criteria_id")
        criteria = self.env["vendor.evaluation.criteria"].search([
            ("id", "not in", existing_criteria.ids),
        ])
        for c in criteria:
            self.env["vendor.evaluation.line"].create({
                "evaluation_id": self.id,
                "criteria_id": c.id,
                "score": 0,
            })


class VendorEvaluationLine(models.Model):
    _name = "vendor.evaluation.line"
    _description = "รายการประเมินผู้จำหน่าย"
    _order = "sequence, id"

    evaluation_id = fields.Many2one(
        comodel_name="vendor.evaluation",
        string="ใบประเมิน",
        required=True,
        ondelete="cascade",
    )
    criteria_id = fields.Many2one(
        comodel_name="vendor.evaluation.criteria",
        string="เกณฑ์ประเมิน",
        required=True,
    )
    sequence = fields.Integer(related="criteria_id.sequence", store=True)
    weight = fields.Float(
        related="criteria_id.weight",
        string="น้ำหนัก (%)",
        store=True,
    )
    max_score = fields.Float(
        related="criteria_id.max_score",
        string="คะแนนเต็ม",
        store=True,
    )
    score = fields.Float(
        string="คะแนนที่ได้",
        digits=(5, 2),
    )
    score_pct = fields.Float(
        string="คะแนน (%)",
        compute="_compute_weighted_score",
        store=True,
        digits=(5, 2),
    )
    weighted_score = fields.Float(
        string="คะแนนถ่วงน้ำหนัก",
        compute="_compute_weighted_score",
        store=True,
        digits=(5, 2),
    )
    remark = fields.Char(string="หมายเหตุ")

    @api.depends("score", "max_score", "weight")
    def _compute_weighted_score(self):
        for line in self:
            if line.max_score:
                line.score_pct = (line.score / line.max_score) * 100
                line.weighted_score = line.score_pct * line.weight / 100
            else:
                line.score_pct = 0
                line.weighted_score = 0

    @api.constrains("score", "max_score")
    def _check_score(self):
        for line in self:
            if line.score < 0:
                raise ValidationError(
                    _("คะแนนต้องไม่ติดลบ")
                )
            if line.score > line.max_score:
                raise ValidationError(
                    _("คะแนน (%(score)s) เกินคะแนนเต็ม (%(max)s) "
                      "ของเกณฑ์ '%(criteria)s'")
                    % {
                        "score": line.score,
                        "max": line.max_score,
                        "criteria": line.criteria_id.name,
                    }
                )
