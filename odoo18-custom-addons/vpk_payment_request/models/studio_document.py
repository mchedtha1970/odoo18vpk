# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

PAYMENT_REQUEST_CODE = "payment_request"
PAYMENT_FIELDS = [
    "payment_bill_id",
    "payment_state",
    "payment_ap_forwarded_on",
    "payment_finance_sent_on",
    "payment_finance_sent_by",
    "payment_amount",
]
AP_GROUP = "account.group_account_invoice"


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    payment_amount = fields.Monetary(
        string="จำนวนเงินที่ขอเบิกจ่าย",
        currency_field="payment_currency_id",
        copy=False,
    )
    payment_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_payment_currency_id",
        string="สกุลเงิน",
    )
    payment_bill_id = fields.Many2one(
        comodel_name="account.move",
        string="ใบเรียกเก็บ (ตั้งเจ้าหนี้)",
        copy=False,
        readonly=True,
        index=True,
        ondelete="set null",
    )
    payment_state = fields.Selection(
        selection=[
            ("draft", "ร่าง / รอลงนาม"),
            ("approved", "อนุมัติแล้ว (รอส่งเจ้าหนี้)"),
            ("wait_ap", "ส่งเจ้าหนี้แล้ว (รอตั้งหนี้)"),
            ("billed", "ตั้งเจ้าหนี้ (ฉบับร่าง)"),
            ("posted", "อนุมัติตั้งเจ้าหนี้แล้ว (รอส่งการเงิน)"),
            ("to_finance", "ส่งการเงินแล้ว (รอทำจ่าย)"),
            ("paid", "ทำจ่ายแล้ว"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะเบิกจ่าย",
        compute="_compute_payment_state",
        store=True,
        index=True,
    )
    payment_ap_forwarded_on = fields.Datetime(
        string="ส่งเจ้าหนี้เมื่อ", copy=False, readonly=True
    )
    payment_finance_sent_on = fields.Datetime(
        string="ส่งการเงินเมื่อ", copy=False, readonly=True
    )
    payment_finance_sent_by = fields.Many2one(
        comodel_name="res.users", string="ส่งการเงินโดย", copy=False, readonly=True
    )
    payment_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้ขาย",
        related="purchase_id.partner_id",
    )

    @api.depends("purchase_id.currency_id", "company_id")
    def _compute_payment_currency_id(self):
        for rec in self:
            rec.payment_currency_id = (
                rec.sudo().purchase_id.currency_id or rec.company_id.currency_id
            )

    @api.depends(
        "document_type_code",
        "state",
        "payment_bill_id",
        "payment_bill_id.state",
        "payment_bill_id.payment_state",
        "payment_ap_forwarded_on",
        "payment_finance_sent_on",
    )
    def _compute_payment_state(self):
        for rec in self:
            if rec.document_type_code != PAYMENT_REQUEST_CODE:
                rec.payment_state = False
            elif rec.state == "cancelled":
                rec.payment_state = "cancel"
            elif rec.state != "approved":
                rec.payment_state = "draft"
            elif rec.payment_bill_id and rec.payment_bill_id.state != "cancel":
                if rec.payment_finance_sent_on:
                    if rec.payment_bill_id.payment_state in ("paid", "in_payment"):
                        rec.payment_state = "paid"
                    else:
                        rec.payment_state = "to_finance"
                elif rec.payment_bill_id.state == "posted":
                    rec.payment_state = "posted"
                else:
                    rec.payment_state = "billed"
            elif not rec.payment_ap_forwarded_on:
                rec.payment_state = "approved"
            else:
                rec.payment_state = "wait_ap"

    # ------------------------------------------------------------------
    # tier validation: ฟิลด์ฝั่งเจ้าหนี้แก้ได้หลังลงนามครบ
    # ------------------------------------------------------------------
    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        res = super()._get_validation_exceptions(extra_domain, add_base_exceptions)
        return list(set(res + PAYMENT_FIELDS))

    def _get_under_validation_exceptions(self):
        return list(set(super()._get_under_validation_exceptions() + PAYMENT_FIELDS))

    def _get_after_validation_exceptions(self):
        return list(set(super()._get_after_validation_exceptions() + PAYMENT_FIELDS))

    # ------------------------------------------------------------------
    # ส่งหน่วยงานเจ้าหนี้ (กดปุ่มเอง หลังลงนามครบ)
    # ------------------------------------------------------------------
    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers)
        for rec in self.filtered(
            lambda doc: doc.document_type_code == PAYMENT_REQUEST_CODE
            and doc.state == "approved"
        ):
            rec.sudo().message_post(
                body=_(
                    "ใบขออนุมัติเบิกจ่ายลงนามครบแล้ว "
                    "จัดซื้อกดปุ่ม \"ส่งหน่วยงานเจ้าหนี้\" เพื่อส่งต่อให้เจ้าหนี้ดำเนินการ"
                ),
                subtype_xmlid="mail.mt_note",
            )
        return res

    def action_send_to_ap(self):
        """ปุ่ม ส่งหน่วยงานเจ้าหนี้: ทำได้เมื่อลงนามอนุมัติครบแล้วเท่านั้น."""
        for rec in self:
            if rec.document_type_code != PAYMENT_REQUEST_CODE:
                raise UserError(_("เอกสารนี้ไม่ใช่ใบขออนุมัติเบิกจ่าย"))
            if rec.state != "approved":
                raise UserError(
                    _("ส่งหน่วยงานเจ้าหนี้ได้หลังลงนามอนุมัติครบทุกลำดับแล้วเท่านั้น (%s)", rec.display_name)
                )
            if rec.payment_ap_forwarded_on:
                raise UserError(_("เอกสาร %s ส่งหน่วยงานเจ้าหนี้แล้ว", rec.display_name))
        self.sudo()._vpk_forward_to_ap()
        return True

    def _vpk_ap_partners(self):
        group = self.env.ref("account.group_account_invoice", raise_if_not_found=False)
        if not group:
            return self.env["res.partner"]
        users = self.env["res.users"].sudo().search(
            [("groups_id", "in", group.id), ("share", "=", False), ("active", "=", True)]
        )
        return users.partner_id

    def _vpk_forward_to_ap(self):
        partners = self._vpk_ap_partners()
        for rec in self:
            rec.with_context(skip_validation_check=True).write(
                {"payment_ap_forwarded_on": fields.Datetime.now()}
            )
            order = rec.purchase_id
            text = _(
                "จัดซื้อ (%(user)s) ส่งใบขออนุมัติเบิกจ่าย %(doc)s (ใบตรวจรับ %(wa)s) "
                "ให้หน่วยงานเจ้าหนี้ดึงรายการไปตั้งเจ้าหนี้",
                user=self.env.user.name,
                doc=rec.name or rec.display_name,
                wa=rec.wa_id.name or "-",
            )
            rec.message_post(
                body=text,
                partner_ids=partners.ids,
                subtype_xmlid="mail.mt_comment",
            )
            if order:
                order.message_post(body=text, subtype_xmlid="mail.mt_note")
        return True

    # ------------------------------------------------------------------
    # เจ้าหนี้ดึงรายการ → ใบเรียกเก็บฉบับร่าง
    # ------------------------------------------------------------------
    def _vpk_check_ap_access(self):
        if not (self.env.su or self.env.user.has_group(AP_GROUP)):
            raise UserError(_("เฉพาะเจ้าหน้าที่เจ้าหนี้เท่านั้นที่ทำรายการนี้ได้"))

    def action_create_ap_bill(self):
        self.ensure_one()
        self._vpk_check_ap_access()
        rec = self.sudo()
        if rec.document_type_code != PAYMENT_REQUEST_CODE:
            raise UserError(_("เอกสารนี้ไม่ใช่ใบขออนุมัติเบิกจ่าย"))
        if rec.state != "approved":
            raise UserError(_("ต้องลงนามอนุมัติครบทุกลำดับก่อน เจ้าหนี้จึงดึงรายการไปตั้งหนี้ได้"))
        if not rec.payment_ap_forwarded_on:
            raise UserError(_("จัดซื้อยังไม่ได้ส่งหน่วยงานเจ้าหนี้ (กดปุ่ม \"ส่งหน่วยงานเจ้าหนี้\" ก่อน)"))
        if rec.payment_bill_id and rec.payment_bill_id.state != "cancel":
            return rec._vpk_open_ap_bill()
        wa = rec.wa_id
        order = rec.purchase_id
        if not order or not wa or wa.state != "accept":
            raise UserError(_("ไม่พบใบตรวจรับที่ยืนยันตรวจรับของรายการนี้"))
        valid = self.env["work.acceptance"].sudo()._get_valid_wa("invoice", order.id)
        if wa not in valid:
            raise UserError(
                _("ใบตรวจรับ %s ถูกใช้ตั้งใบเรียกเก็บแล้ว", wa.name)
            )
        action = order.with_context(create_bill=False, wa_id=wa.id).action_create_invoice()
        move = self.env["account.move"].sudo().browse(action.get("res_id"))
        if not move:
            raise UserError(_("ไม่สามารถสร้างใบเรียกเก็บจากใบสั่งซื้อได้"))
        move.write({"payment_request_id": rec.id})
        rec.with_context(skip_validation_check=True).write({"payment_bill_id": move.id})
        rec.message_post(
            body=_("เจ้าหนี้ดึงรายการและสร้างใบเรียกเก็บฉบับร่าง %s", move.display_name),
            subtype_xmlid="mail.mt_note",
        )
        order.message_post(
            body=_(
                "เจ้าหนี้สร้างใบเรียกเก็บฉบับร่าง %(bill)s จากใบขออนุมัติเบิกจ่าย %(doc)s",
                bill=move.display_name,
                doc=rec.name or rec.display_name,
            ),
            subtype_xmlid="mail.mt_note",
        )
        return rec._vpk_open_ap_bill()

    # ------------------------------------------------------------------
    # ตั้งเจ้าหนี้เสร็จ (POST แล้ว) → ส่งการเงิน
    # ------------------------------------------------------------------
    def _vpk_finance_partners(self):
        group = self.env.ref("vpk_gfmis.group_gfmis_user", raise_if_not_found=False)
        if not group:
            return self.env["res.partner"]
        users = self.env["res.users"].sudo().search(
            [("groups_id", "in", group.id), ("share", "=", False), ("active", "=", True)]
        )
        return users.partner_id

    def action_send_to_finance(self):
        """ปุ่ม ส่งการเงิน: ทำได้เมื่อเจ้าหนี้อนุมัติตั้งเจ้าหนี้และ POST ใบเรียกเก็บแล้ว."""
        self._vpk_check_ap_access()
        partners = self._vpk_finance_partners()
        for rec in self.sudo():
            if rec.document_type_code != PAYMENT_REQUEST_CODE:
                raise UserError(_("เอกสารนี้ไม่ใช่ใบขออนุมัติเบิกจ่าย"))
            if rec.payment_finance_sent_on:
                raise UserError(_("เอกสาร %s ส่งการเงินแล้ว", rec.display_name))
            bill = rec.payment_bill_id
            if not bill or bill.state != "posted":
                raise UserError(
                    _(
                        "ส่งการเงินได้หลังอนุมัติตั้งเจ้าหนี้และ POST ใบเรียกเก็บแล้วเท่านั้น (%s)",
                        rec.display_name,
                    )
                )
            rec.with_context(skip_validation_check=True).write(
                {
                    "payment_finance_sent_on": fields.Datetime.now(),
                    "payment_finance_sent_by": self.env.user.id,
                }
            )
            text = _(
                "เจ้าหนี้ (%(user)s) อนุมัติตั้งเจ้าหนี้ %(bill)s แล้ว "
                "ส่งการเงินเพื่อทำรายการจ่าย (ใบขออนุมัติเบิกจ่าย %(doc)s)",
                user=self.env.user.name,
                bill=bill.name or bill.display_name,
                doc=rec.name or rec.display_name,
            )
            rec.message_post(
                body=text,
                partner_ids=partners.ids,
                subtype_xmlid="mail.mt_comment",
            )
            if rec.purchase_id:
                rec.purchase_id.message_post(body=text, subtype_xmlid="mail.mt_note")
            bill.message_post(body=text, subtype_xmlid="mail.mt_note")
        return True

    # ------------------------------------------------------------------
    # Dashboard งานเจ้าหนี้
    # ------------------------------------------------------------------
    @api.model
    def get_payment_ap_dashboard(self):
        self._vpk_check_ap_access()
        Doc = self.sudo()
        base = [("document_type_code", "=", PAYMENT_REQUEST_CODE)]
        stage_defs = [
            ("wait_ap", "รอตั้งเจ้าหนี้", "จัดซื้อส่งมาแล้ว ยังไม่ได้ดึงรายการ", "warn"),
            ("billed", "ตั้งเจ้าหนี้ (Draft)", "ดึงรายการแล้ว รออนุมัติและ POST", "info"),
            ("posted", "รอส่งการเงิน", "อนุมัติตั้งเจ้าหนี้และ POST แล้ว", "ok"),
            ("to_finance", "ส่งการเงินแล้ว", "ส่งต่อให้การเงินทำรายการจ่าย", "muted"),
        ]
        since = fields.Datetime.now() - timedelta(days=30)
        docs = Doc.search(
            base
            + [
                "|",
                ("payment_state", "in", ["wait_ap", "billed", "posted"]),
                "&",
                ("payment_state", "=", "to_finance"),
                ("payment_finance_sent_on", ">=", since),
            ],
            order="payment_ap_forwarded_on asc, id asc",
            limit=500,
        )
        labels = {key: label for key, label, _hint, _tone in stage_defs}
        now = fields.Datetime.now()
        rows = []
        for doc in docs:
            bill = doc.payment_bill_id
            forwarded = doc.payment_ap_forwarded_on
            bill_validation = (getattr(bill, "validation_status", "") or "") if bill else ""
            status_key = doc.payment_state
            state_label = labels.get(doc.payment_state, "")
            if doc.payment_state == "billed" and bill:
                if bill_validation in ("waiting", "pending"):
                    status_key = "wait_acc"
                    state_label = _("รอบัญชีอนุมัติ")
                elif bill_validation == "validated":
                    status_key = "acc_approved"
                    state_label = _("บัญชีอนุมัติ")
                elif bill_validation == "rejected":
                    status_key = "rejected"
                    state_label = _("ไม่อนุมัติ")
            rows.append(
                {
                    "id": doc.id,
                    "name": doc.name or doc.display_name,
                    "state": doc.payment_state,
                    "status_key": status_key,
                    "state_label": state_label,
                    "bill_validation_status": bill_validation,
                    "po_id": doc.purchase_id.id,
                    "po_name": doc.purchase_id.name or "",
                    "vendor": doc.purchase_id.partner_id.name or "",
                    "wa": doc.wa_id.name or "",
                    "amount": doc.payment_amount or 0.0,
                    "forwarded_on": fields.Datetime.to_string(forwarded) if forwarded else "",
                    "waiting_days": (now - forwarded).days if forwarded else 0,
                    "bill_id": bill.id if bill else False,
                    "bill_name": (
                        bill.name if bill and bill.name and bill.name != "/" else _("ฉบับร่าง")
                    )
                    if bill
                    else "",
                    "finance_sent_on": (
                        fields.Datetime.to_string(doc.payment_finance_sent_on)
                        if doc.payment_finance_sent_on
                        else ""
                    ),
                }
            )
        kpis = []
        for key, label, hint, tone in stage_defs:
            items = [row for row in rows if row["state"] == key]
            kpis.append(
                {
                    "key": key,
                    "label": label,
                    "hint": hint,
                    "tone": tone,
                    "count": len(items),
                    "amount": sum(row["amount"] for row in items),
                }
            )
        waiting_po = Doc.search_count(base + [("payment_state", "=", "approved")])
        return {
            "kpis": kpis,
            "rows": rows,
            "waiting_purchase_send": waiting_po,
            "currency_symbol": self.env.company.currency_id.symbol or "฿",
        }

    # ------------------------------------------------------------------
    # Dashboard การเงิน: ดึงรายการที่เจ้าหนี้ส่งมา → ทำจ่าย
    # ------------------------------------------------------------------
    @api.model
    def get_payment_finance_dashboard(self):
        self._vpk_check_ap_access()
        Doc = self.sudo()
        base = [("document_type_code", "=", PAYMENT_REQUEST_CODE)]
        since = fields.Datetime.now() - timedelta(days=30)
        docs = Doc.search(
            base
            + [
                "|",
                ("payment_state", "=", "to_finance"),
                "&",
                ("payment_state", "=", "paid"),
                ("payment_finance_sent_on", ">=", since),
            ],
            order="payment_finance_sent_on asc, id asc",
            limit=500,
        )
        labels = dict(self._fields["payment_state"].selection)
        now = fields.Datetime.now()
        po_model = self.env["purchase.order"]
        disbursement_labels = {}
        if "egp_disbursement_type" in po_model._fields:
            disbursement_labels = dict(po_model._fields["egp_disbursement_type"].selection)
        rows = []
        for doc in docs:
            bill = doc.payment_bill_id
            sent = doc.payment_finance_sent_on
            po = doc.purchase_id
            disbursement = (
                po.egp_disbursement_type
                if po and "egp_disbursement_type" in po._fields
                else False
            )
            rows.append(
                {
                    "id": doc.id,
                    "name": doc.name or doc.display_name,
                    "state": doc.payment_state,
                    "state_label": labels.get(doc.payment_state, ""),
                    "po_id": po.id if po else False,
                    "po_name": po.name or "",
                    "po_disbursement_type": disbursement or "",
                    "po_disbursement_label": disbursement_labels.get(disbursement, "") if disbursement else "",
                    "vendor": po.partner_id.name if po else "",
                    "wa": doc.wa_id.name or "",
                    "bill_id": bill.id if bill else False,
                    "bill_name": bill.name if bill and bill.name != "/" else "",
                    "amount": (bill.amount_total if bill else doc.payment_amount) or 0.0,
                    "residual": bill.amount_residual if bill else 0.0,
                    "due_date": fields.Date.to_string(bill.invoice_date_due) if bill and bill.invoice_date_due else "",
                    "sent_on": fields.Datetime.to_string(sent) if sent else "",
                    "waiting_days": (now - sent).days if sent else 0,
                    "overdue": bool(
                        bill
                        and bill.invoice_date_due
                        and bill.invoice_date_due < fields.Date.context_today(self)
                        and doc.payment_state == "to_finance"
                    ),
                    # เติมโดย vpk_disbursement_form เมื่อโมดูลติดตั้ง
                    "kb_id": False,
                    "kb_name": "",
                    "kb_state": "",
                    "kb_state_label": "ยังไม่มีใบขอเบิกเงิน",
                    "can_register_payment": False,
                    "draft_payment_id": False,
                    "draft_payment_name": "",
                    "draft_payment_validation": "",
                }
            )
        self._vpk_finance_dashboard_fill_draft_payments(rows)
        pending = [row for row in rows if row["state"] == "to_finance"]
        overdue = [row for row in rows if row["overdue"]]
        paid = [row for row in rows if row["state"] == "paid"]
        stage_defs = [
            ("to_finance", "รอทำจ่ายทั้งหมด", "รายการที่เจ้าหนี้ส่งมาแล้ว ยังไม่ได้ทำจ่าย", "warn", pending),
            ("overdue", "เกินกำหนดจ่าย", "รอทำจ่ายและเลยวันครบกำหนดแล้ว", "danger", overdue),
            ("paid", "ทำจ่ายแล้ว", "ทำรายการจ่ายแล้ว (ย้อนหลัง 30 วัน)", "ok", paid),
        ]
        kpis = []
        for key, label, hint, tone, items in stage_defs:
            kpis.append(
                {
                    "key": key,
                    "label": label,
                    "hint": hint,
                    "tone": tone,
                    "count": len(items),
                    "amount": sum(row["residual"] if key != "paid" else row["amount"] for row in items),
                }
            )
        return {"kpis": kpis, "rows": rows}

    @api.model
    def _vpk_finance_dashboard_fill_draft_payments(self, rows):
        """ผูกใบสำคัญจ่ายฉบับร่าง (รออนุมัติ/รอ POST) เข้าแถว Dashboard."""
        Payment = self.env["account.payment"].sudo()
        if "vpk_payment_request_id" not in Payment._fields:
            return rows
        request_ids = [row["id"] for row in rows if row.get("state") == "to_finance"]
        if not request_ids:
            return rows
        drafts = Payment.search(
            [
                ("vpk_payment_request_id", "in", request_ids),
                ("state", "=", "draft"),
                ("payment_type", "=", "outbound"),
            ],
            order="id desc",
        )
        by_request = {}
        for pay in drafts:
            by_request.setdefault(pay.vpk_payment_request_id.id, pay)
        for row in rows:
            pay = by_request.get(row["id"])
            if not pay:
                continue
            row["draft_payment_id"] = pay.id
            row["draft_payment_name"] = pay.name or pay.display_name or ""
            row["draft_payment_validation"] = getattr(pay, "validation_status", "") or ""
            # มีใบสำคัญจ่ายร่างแล้ว — ไม่ให้ดึงซ้ำ (ปุ่ม UI เปิดใบเดิมแทน)
            row["can_register_payment"] = False
        return rows

    def action_open_register_payment(self):
        """ยืนยันรายการจ่าย → สร้างรายการชำระเงินฉบับร่างทันที (ไม่เปิด wizard, ไม่ POST)."""
        self.ensure_one()
        self._vpk_check_ap_access()
        rec = self.sudo()
        bill = rec.payment_bill_id
        if not rec.payment_finance_sent_on or not bill:
            raise UserError(_("เจ้าหนี้ยังไม่ได้ส่งรายการนี้ให้การเงิน"))
        if bill.state != "posted":
            raise UserError(_("ใบเรียกเก็บยังไม่ได้อนุมัติ/POST"))
        if bill.payment_state in ("paid", "in_payment"):
            raise UserError(_("รายการนี้ทำจ่ายแล้ว"))

        Payment = self.env["account.payment"].sudo()
        existing = Payment.search(
            [
                ("vpk_payment_request_id", "=", rec.id),
                ("state", "=", "draft"),
                ("payment_type", "=", "outbound"),
            ],
            limit=1,
        )
        if existing:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("มีรายการชำระเงินแล้ว"),
                    "message": _(
                        "รายการ %s อยู่ในสถานะร่าง — บัญชีบันทึกได้ที่ "
                        "Dashboard รายการจ่ายชำระ รอบันทึกบัญชี"
                    )
                    % (existing.name or existing.display_name),
                    "type": "warning",
                    "sticky": False,
                },
            }

        # ใช้ context เดียวกับปุ่ม Register Payment (active = move lines)
        register_action = bill.action_register_payment()
        ctx = dict(register_action.get("context") or {})
        ctx.update(
            {
                "vpk_finance_draft_voucher": True,
                "vpk_finance_silent_create": True,
                "vpk_payment_request_id": rec.id,
            }
        )
        wizard = self.env["account.payment.register"].with_context(**ctx).create({})
        wizard.action_create_payments()

        payment = Payment.search(
            [
                ("vpk_payment_request_id", "=", rec.id),
                ("state", "=", "draft"),
                ("payment_type", "=", "outbound"),
            ],
            order="id desc",
            limit=1,
        )
        label = (payment.name or payment.display_name) if payment else ""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ยืนยันรายการจ่ายแล้ว"),
                "message": _(
                    "สร้างรายการชำระเงิน %s ฉบับร่างแล้ว — ส่งให้บัญชีบันทึกที่ "
                    "Dashboard รายการจ่ายชำระ รอบันทึกบัญชี"
                )
                % label,
                "type": "success",
                "sticky": False,
            },
        }

    def action_open_draft_payment_voucher(self):
        """เปิดใบสำคัญจ่ายฉบับร่างที่ดึงไว้แล้ว."""
        self.ensure_one()
        self._vpk_check_ap_access()
        pay = self.env["account.payment"].sudo().search(
            [
                ("vpk_payment_request_id", "=", self.id),
                ("state", "=", "draft"),
                ("payment_type", "=", "outbound"),
            ],
            limit=1,
        )
        if not pay:
            raise UserError(_("ยังไม่มีใบสำคัญจ่ายฉบับร่างของรายการนี้"))
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการชำระเงิน (รอบันทึกบัญชี)"),
            "res_model": "account.payment",
            "res_id": pay.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def _vpk_open_ap_bill(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบเรียกเก็บ"),
            "res_model": "account.move",
            "res_id": self.payment_bill_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_open_ap_bill(self):
        self.ensure_one()
        if not self.payment_bill_id:
            raise UserError(_("ยังไม่มีใบเรียกเก็บ"))
        return self.sudo()._vpk_open_ap_bill()

    def action_open_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            raise UserError(_("เอกสารนี้ไม่ได้ผูกกับใบสั่งซื้อ"))
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบสั่งซื้อ"),
            "res_model": "purchase.order",
            "res_id": self.purchase_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }
