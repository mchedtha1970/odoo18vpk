from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProcurementPlanAmendment(models.Model):
    _name = "procurement.plan.amendment"
    _description = "คำขออนุมัติเพิ่มแผนจัดซื้อจัดจ้าง"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    plan_id = fields.Many2one(
        comodel_name="procurement.annual.plan",
        string="แผนอ้างอิง",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    reason = fields.Text(string="เหตุผลการขอเพิ่มแผน", required=True)
    source_type = fields.Selection(
        selection=[
            ("orderpoint", "ถึงจุดสั่งซื้อ (นอกแผน)"),
            ("contract_expiry", "สัญญาใกล้หมดอายุ (นอกแผน)"),
            ("manual", "ขอเพิ่มแผนด้วยตนเอง"),
        ],
        string="ที่มา",
        default="manual",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("submitted", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("rejected", "ไม่อนุมัติ"),
            ("cancelled", "ยกเลิก"),
        ],
        default="draft",
        tracking=True,
        required=True,
    )
    line_ids = fields.One2many(
        comodel_name="procurement.plan.amendment.line",
        inverse_name="amendment_id",
        string="รายการที่ขอเพิ่ม",
    )
    company_id = fields.Many2one(related="plan_id.company_id", store=True)
    requested_by = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "procurement.plan.amendment"
                    )
                    or _("New")
                )
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("กรุณาเพิ่มรายการที่ขอเพิ่มแผนอย่างน้อย 1 รายการ"))
            rec.state = "submitted"

    def action_approve(self):
        """อนุมัติแล้ว เพิ่มรายการเข้าแผนหลัก — จากนั้นจึงจะ Gen Auto PR ได้"""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("อนุมัติได้เฉพาะสถานะรออนุมัติ"))
            PlanLine = self.env["procurement.annual.plan.line"]
            for line in rec.line_ids:
                PlanLine.create({
                    "plan_id": rec.plan_id.id,
                    "name": line.name,
                    "purchase_type": line.purchase_type,
                    "product_id": line.product_id.id,
                    "contract_id": line.contract_id.id,
                    "qty_planned": line.qty_requested,
                    "uom_id": line.product_id.uom_id.id if line.product_id else False,
                    "unit_price": (
                        line.amount_requested / line.qty_requested
                        if line.qty_requested
                        else 0.0
                    ),
                    "amount_planned": line.amount_requested,
                    "partner_id": line.partner_id.id,
                })
            rec.state = "approved"
            rec.message_post(
                body=_("อนุมัติเพิ่มแผนแล้ว — รายการถูกเพิ่มเข้าแผน %s")
                % rec.plan_id.display_name
            )

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})


class ProcurementPlanAmendmentLine(models.Model):
    _name = "procurement.plan.amendment.line"
    _description = "รายการคำขอเพิ่มแผน"
    _order = "id"

    amendment_id = fields.Many2one(
        comodel_name="procurement.plan.amendment",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="รายละเอียด", required=True)
    purchase_type = fields.Selection(
        selection=[
            ("buy", "ซื้อ"),
            ("hire", "จ้าง"),
            ("lease", "เช่า"),
        ],
        required=True,
        default="buy",
    )
    product_id = fields.Many2one(comodel_name="product.product", string="สินค้า")
    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        string="สัญญา",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จำหน่าย",
        domain="[('supplier_rank', '>', 0)]",
    )
    qty_requested = fields.Float(string="จำนวนที่ขอ", default=1.0)
    amount_requested = fields.Float(string="วงเงินที่ขอ")
