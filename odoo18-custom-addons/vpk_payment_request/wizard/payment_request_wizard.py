# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models
from odoo.exceptions import UserError

PAYMENT_REQUEST_CODE = "payment_request"


class PaymentRequestWizard(models.TransientModel):
    _name = "vpk.payment.request.wizard"
    _description = "เพิ่มเอกสารขออนุมัติเบิกจ่าย"

    purchase_id = fields.Many2one("purchase.order", string="ใบสั่งซื้อ", required=True, readonly=True)
    available_wa_ids = fields.Many2many(
        "work.acceptance", compute="_compute_available_wa_ids", string="ใบตรวจรับที่ขอได้"
    )
    wa_id = fields.Many2one(
        "work.acceptance",
        string="ใบตรวจรับ",
        required=True,
        domain="[('id', 'in', available_wa_ids)]",
    )
    amount = fields.Monetary(
        string="จำนวนเงินที่ขอเบิกจ่าย",
        related="wa_id.payment_amount",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(related="purchase_id.currency_id")
    add_mode = fields.Selection(
        selection=[
            ("studio", "สร้างจากแบบฟอร์มขออนุมัติเบิกจ่าย"),
            ("attach", "แนบไฟล์เอกสารที่จัดทำแล้ว"),
        ],
        string="วิธีเพิ่มเอกสาร",
        required=True,
        default="studio",
    )
    file = fields.Binary(string="ไฟล์เอกสาร")
    filename = fields.Char(string="ชื่อไฟล์")
    notes = fields.Text(string="หมายเหตุ")

    @api.depends("purchase_id")
    def _compute_available_wa_ids(self):
        for rec in self:
            rec.available_wa_ids = rec.purchase_id._vpk_payment_available_wa() if rec.purchase_id else False

    @api.model
    def _open_for(self, order):
        wizard = self.create(
            {
                "purchase_id": order.id,
                "wa_id": order._vpk_payment_available_wa()[:1].id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("ขออนุมัติเบิกจ่าย"),
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_confirm(self):
        self.ensure_one()
        order = self.purchase_id
        order._vpk_check_can_request_payment()
        if self.wa_id not in order._vpk_payment_available_wa():
            raise UserError(_("ใบตรวจรับ %s ขอเบิกจ่ายไม่ได้ (มีใบขอแล้วหรือถูกใช้ตั้งหนี้แล้ว)") % self.wa_id.name)
        Document = self.env["vpk.document.studio.document"]
        doc_type = self.env["vpk.document.studio.document.type"].search(
            [("code", "=", PAYMENT_REQUEST_CODE)], limit=1
        )
        if not doc_type:
            raise UserError(_("ไม่พบประเภทเอกสารขออนุมัติเบิกจ่าย กรุณาอัปเดตโมดูล"))
        extra = {
            "wa_id": self.wa_id.id,
            "purchase_id": order.id,
            "payment_amount": self.wa_id.payment_amount,
            "note": self.notes,
        }
        if self.add_mode == "attach":
            if not self.file:
                raise UserError(_("กรุณาแนบไฟล์เอกสาร"))
            document = Document.create(
                dict(
                    extra,
                    source_mode="uploaded",
                    document_type_id=doc_type.id,
                    source_ref="purchase.order,%d" % order.id,
                    company_id=order.company_id.id,
                )
            )
            document.attach_uploaded_file(self.file, self.filename)
            document._vpk_seed_default_approvers()
        else:
            document = Document.with_context(
                vpk_payment_wa_id=self.wa_id.id
            )._vpk_create_for_record(order, doc_type, extra=extra)
        if self.notes:
            document.message_post(body=self.notes)
        order.message_post(
            body=_(
                "ขออนุมัติเบิกจ่าย: สร้างเอกสาร %(doc)s จากใบตรวจรับ %(wa)s กรุณาเพิ่มผู้อนุมัติแล้วส่งลงนาม",
                doc=document.display_name,
                wa=self.wa_id.name,
            ),
            subtype_xmlid="mail.mt_note",
        )
        return document._action_open_form()
