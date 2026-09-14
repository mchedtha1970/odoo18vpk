from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionEgpInvitation(models.Model):
    _name = "purchase.requisition.egp.invitation"
    _description = "ใบขอเชิญเสนอราคาในกระบวนการ eGP"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่ใบเชิญ",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ eGP",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        domain=[("requisition_type", "=", "egp_procurement")],
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้ประกอบการที่เชิญ",
        required=True,
        domain=[("supplier_rank", ">", 0)],
        context={"res_partner_search_mode": "supplier"},
        tracking=True,
    )
    invitation_date = fields.Date(
        string="วันที่เชิญ",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    submission_deadline = fields.Datetime(
        string="กำหนดยื่นข้อเสนอ",
        required=True,
        tracking=True,
    )
    subject = fields.Char(
        string="เรื่อง",
        required=True,
        default="ขอเชิญเสนอราคา",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("sent", "ส่งคำเชิญแล้ว"),
            ("responded", "ได้รับข้อเสนอแล้ว"),
            ("declined", "ไม่เข้าร่วม"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.invitation.line",
        inverse_name="invitation_id",
        string="รายการที่เชิญเสนอราคา",
        copy=True,
    )
    bid_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid",
        string="ข้อเสนอราคาที่ได้รับ",
        readonly=True,
        copy=False,
    )
    notes = fields.Html(string="เงื่อนไข/หมายเหตุ")
    company_id = fields.Many2one(
        related="requisition_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="requisition_id.currency_id",
        store=True,
        readonly=True,
    )
    egp_reference = fields.Char(
        related="requisition_id.egp_reference",
        string="เลขที่โครงการ e-GP",
        readonly=True,
    )
    purchase_request_id = fields.Many2one(
        related="requisition_id.purchase_request_id",
        string="ใบขอซื้ออ้างอิง",
        readonly=True,
    )

    _sql_constraints = [
        (
            "requisition_partner_uniq",
            "unique(requisition_id, partner_id)",
            "ผู้ประกอบการรายนี้มีใบเชิญเสนอราคาในกระบวนการ eGP แล้ว",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.name == _("New"):
                record.name = (
                    self.env["ir.sequence"].next_by_code(
                        "purchase.requisition.egp.invitation"
                    )
                    or _("New")
                )
            record._ensure_lines_from_requisition()
        return records

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        if self.requisition_id:
            self.subject = _("ขอเชิญเสนอราคาโครงการ %s") % (
                self.requisition_id.egp_project_name
                or self.requisition_id.display_name
            )

    def _ensure_lines_from_requisition(self):
        for invitation in self:
            if invitation.line_ids or not invitation.requisition_id:
                continue
            source_lines = invitation.requisition_id._get_rfq_source_pr_lines()
            values = []
            if source_lines:
                for line in source_lines:
                    values.append({
                        "invitation_id": invitation.id,
                        "product_id": line.product_id.id,
                        "name": line.name or line.product_id.display_name,
                        "product_qty": line.product_qty,
                        "product_uom_id": line.product_uom_id.id,
                    })
            else:
                for line in invitation.requisition_id.line_ids:
                    values.append({
                        "invitation_id": invitation.id,
                        "product_id": line.product_id.id,
                        "name": line.product_description_variants
                        or line.product_id.display_name,
                        "product_qty": line.product_qty,
                        "product_uom_id": line.product_uom_id.id,
                    })
            if values:
                self.env["purchase.requisition.egp.invitation.line"].create(values)

    def action_send(self):
        for invitation in self:
            if not invitation.line_ids:
                raise UserError(_("ใบเชิญต้องมีรายการอย่างน้อย 1 รายการ"))
            invitation.state = "sent"
            invitation.message_post(
                body=_("บันทึกการส่งใบขอเชิญเสนอราคาให้ %s")
                % invitation.partner_id.display_name
            )
        return True

    def action_mark_responded(self):
        for invitation in self:
            bid = invitation.bid_id
            if not bid:
                bid = self.env["purchase.requisition.egp.bid"].create({
                    "requisition_id": invitation.requisition_id.id,
                    "partner_id": invitation.partner_id.id,
                    "bid_date": fields.Date.context_today(invitation),
                    "notes": _("สร้างจากใบเชิญเสนอราคา %s") % invitation.name,
                })
            invitation.write({"state": "responded", "bid_id": bid.id})
        return self.action_open_bid()

    def action_decline(self):
        self.write({"state": "declined"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_bid(self):
        self.ensure_one()
        if not self.bid_id:
            raise UserError(_("ยังไม่มีข้อเสนอราคาที่เชื่อมกับใบเชิญนี้"))
        return {
            "type": "ir.actions.act_window",
            "name": _("บันทึกข้อเสนอราคา"),
            "res_model": "purchase.requisition.egp.bid",
            "res_id": self.bid_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_purchase_agreement_egp.action_report_egp_invitation"
        ).report_action(self)


class PurchaseRequisitionEgpInvitationLine(models.Model):
    _name = "purchase.requisition.egp.invitation.line"
    _description = "รายการในใบขอเชิญเสนอราคา eGP"
    _order = "sequence, id"

    invitation_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.invitation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="สินค้า/บริการ",
        required=True,
    )
    name = fields.Text(string="รายละเอียด", required=True)
    product_qty = fields.Float(
        string="จำนวน",
        digits="Product Unit of Measure",
        default=1.0,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="หน่วย",
    )


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    egp_invitation_ids = fields.One2many(
        comodel_name="purchase.requisition.egp.invitation",
        inverse_name="requisition_id",
        string="ใบขอเชิญเสนอราคา",
        copy=False,
    )
    egp_invitation_count = fields.Integer(
        compute="_compute_egp_invitation_count",
    )
    egp_has_winner = fields.Boolean(
        string="เลือกผู้ชนะแล้ว",
        compute="_compute_egp_has_winner",
    )

    @api.depends("egp_invitation_ids")
    def _compute_egp_invitation_count(self):
        for requisition in self:
            requisition.egp_invitation_count = len(requisition.egp_invitation_ids)

    @api.depends("egp_bid_ids.is_winner")
    def _compute_egp_has_winner(self):
        for requisition in self:
            requisition.egp_has_winner = bool(
                requisition.egp_bid_ids.filtered("is_winner")
            )

    def action_view_egp_invitations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบขอเชิญเสนอราคา"),
            "res_model": "purchase.requisition.egp.invitation",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {"default_requisition_id": self.id},
        }
