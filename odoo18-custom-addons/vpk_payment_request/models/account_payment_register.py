# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import _, api, fields, models

from .account_payment_method import GFMIS_VENDOR_DIRECT_CODE


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    available_company_bank_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_available_company_bank_ids",
        string="บัญชีธนาคารบริษัทที่ใช้ได้",
    )
    company_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="บัญชีธนาคารที่ตัดจ่าย",
        compute="_compute_company_bank_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_company_bank_ids)]",
        help="แสดงเฉพาะบัญชีธนาคารที่ผูกกับสมุดบันทึกภายใต้บัญชี COA เดียวกับสมุดที่เลือก",
    )
    is_gfmis_vendor_direct = fields.Boolean(
        compute="_compute_is_gfmis_vendor_direct",
    )
    vpk_payment_method_touched = fields.Boolean(
        default=False,
        help="ผู้ใช้เลือกวิธีชำระเงินเองแล้ว — ไม่บังคับค่าจาก PO อีก",
    )
    has_company_bank_choices = fields.Boolean(
        compute="_compute_available_company_bank_ids",
    )
    vpk_filtered_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        compute="_compute_vpk_filtered_journal_ids",
        string="สมุดบันทึกตามวิธีชำระเงิน",
    )
    vpk_ref_bill_number = fields.Char(
        string="เลขที่ Bill",
        compute="_compute_vpk_document_refs",
        store=True,
        readonly=False,
    )
    vpk_ref_po_number = fields.Char(
        string="เลขที่ PO",
        compute="_compute_vpk_document_refs",
        store=True,
        readonly=False,
    )
    vpk_ref_wa_number = fields.Char(
        string="เลขที่ใบตรวจรับงาน",
        compute="_compute_vpk_document_refs",
        store=True,
        readonly=False,
    )
    vpk_ref_contract_number = fields.Char(
        string="เลขที่สัญญา (GF-ที่อ้างอิง)",
        compute="_compute_vpk_document_refs",
        store=True,
        readonly=False,
        help="เลขที่สัญญา/ใบสั่งซื้อจากสัญญาที่ผูกใบเรียกเก็บ หรือค่าการอ้างอิงจากเอกสาร GFMIS/ขบ.",
    )

    @api.depends("payment_method_line_id", "payment_method_line_id.code")
    def _compute_is_gfmis_vendor_direct(self):
        for wizard in self:
            wizard.is_gfmis_vendor_direct = (
                wizard.payment_method_line_id.code == GFMIS_VENDOR_DIRECT_CODE
            )

    @api.model
    def _vpk_join_unique(self, values):
        seen = set()
        ordered = []
        for value in values:
            text = (value or "").strip()
            if not text or text == "/" or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
        return ", ".join(ordered)

    def _vpk_moves_from_wizard(self):
        self.ensure_one()
        return self.line_ids.move_id

    def _vpk_contract_ref_from_moves(self, moves):
        """เลขที่สัญญา — ชอบเลขสัญญา/ใบสั่งซื้อ แล้วค่อยการอ้างอิงจากขบ./GFMIS."""
        refs = []
        if "contract_id" in moves._fields:
            for contract in moves.mapped("contract_id"):
                if not contract:
                    continue
                refs.append(
                    contract.contract_po_number
                    or contract.egp_contract_control_no
                    or contract.name
                )
        if refs:
            return self._vpk_join_unique(refs)

        gf_refs = []
        if "disbursement_form_ids" in moves._fields:
            gf_refs.extend(moves.mapped("disbursement_form_ids.reference"))
        if "gfmis_document_ids" in moves._fields:
            gf_refs.extend(moves.mapped("gfmis_document_ids.reference"))
        return self._vpk_join_unique(gf_refs)

    @api.depends("line_ids", "line_ids.move_id")
    def _compute_vpk_document_refs(self):
        for wizard in self:
            moves = wizard._vpk_moves_from_wizard()
            wizard.vpk_ref_bill_number = wizard._vpk_join_unique(moves.mapped("name"))

            po_names = moves.invoice_line_ids.mapped("purchase_line_id.order_id.name")
            if not po_names:
                po_names = moves.mapped("invoice_origin")
            wizard.vpk_ref_po_number = wizard._vpk_join_unique(po_names)

            wa_names = []
            if "wa_id" in moves._fields:
                wa_names = moves.mapped("wa_id.name")
            wizard.vpk_ref_wa_number = wizard._vpk_join_unique(wa_names)

            wizard.vpk_ref_contract_number = wizard._vpk_contract_ref_from_moves(moves)

    def _vpk_payment_method_lines_for_type(self):
        """รวมวิธีจ่ายจากสมุดที่ใช้ได้ทั้งหมด (เลือกวิธีก่อนสมุดบันทึก)."""
        self.ensure_one()
        lines = self.env["account.payment.method.line"]
        for journal in self.available_journal_ids:
            lines |= journal._get_available_payment_method_lines(self.payment_type)
        return lines

    def _vpk_unique_method_lines(self, lines):
        """หนึ่งบรรทัดต่อโค้ด — ใช้ line ของสมุดปัจจุบันก่อน."""
        self.ensure_one()
        by_code = {}
        preferred = self.env["account.payment.method.line"]
        if self.journal_id:
            preferred = lines.filtered(lambda line: line.journal_id == self.journal_id)
        for line in preferred | lines:
            if line.code and line.code not in by_code:
                by_code[line.code] = line
        return self.env["account.payment.method.line"].browse(
            [line.id for line in by_code.values()]
        )

    def _vpk_journals_for_method_code(self, method_code):
        """สมุดที่ใช้ได้และมีวิธีชำระเงินตามโค้ดที่เลือก."""
        self.ensure_one()
        journals = self.available_journal_ids
        if not method_code:
            return journals
        return journals.filtered(
            lambda journal, code=method_code: code
            in journal._get_available_payment_method_lines(self.payment_type).mapped("code")
        )

    def _vpk_pick_journal(self, journals):
        """เลือกสมุดเริ่มต้น — ชอบสมุดที่มีบัญชีธนาคารผูกไว้."""
        self.ensure_one()
        if not journals:
            return self.env["account.journal"]
        with_bank = journals.filtered("bank_account_id")
        pool = with_bank or journals
        preferred = self.payment_method_line_id.journal_id
        if preferred in pool:
            return preferred
        if self.journal_id in pool:
            return self.journal_id
        return pool[0]

    def _vpk_method_line_on_journal(self, journal, method_code):
        """หา method line ของสมุดที่โค้ดตรงกับที่เลือก."""
        self.ensure_one()
        if not journal or not method_code:
            return self.env["account.payment.method.line"]
        return journal._get_available_payment_method_lines(self.payment_type).filtered(
            lambda line: line.code == method_code
        )[:1]

    def _vpk_purchase_orders_from_wizard(self):
        """ใบสั่งซื้อที่ผูกกับใบเรียกเก็บใน wizard (รวมจากใบขออนุมัติเบิกจ่าย)."""
        self.ensure_one()
        moves = self._vpk_moves_from_wizard()
        orders = moves.invoice_line_ids.mapped("purchase_line_id.order_id")
        req_id = self.env.context.get("vpk_payment_request_id")
        if req_id and "vpk.document.studio.document" in self.env:
            doc = self.env["vpk.document.studio.document"].browse(req_id)
            if doc.exists() and "purchase_id" in doc._fields and doc.purchase_id:
                orders |= doc.purchase_id
        return orders

    def _vpk_preferred_payment_method_code(self):
        """PO จาก e-GP ที่เบิกผ่าน GFMIS → ใช้วิธีตรงเข้าบัญชีผู้ขายจาก GFMIS."""
        self.ensure_one()
        orders = self._vpk_purchase_orders_from_wizard()
        if not orders or "egp_disbursement_type" not in orders._fields:
            return False
        types = {value for value in orders.mapped("egp_disbursement_type") if value}
        if types == {"gfmis"}:
            return GFMIS_VENDOR_DIRECT_CODE
        return False

    @api.depends(
        "available_journal_ids",
        "payment_method_line_id",
        "payment_method_line_id.code",
        "payment_type",
    )
    def _compute_vpk_filtered_journal_ids(self):
        for wizard in self:
            wizard.vpk_filtered_journal_ids = wizard._vpk_journals_for_method_code(
                wizard.payment_method_line_id.code
            )

    @api.depends("payment_type", "available_journal_ids", "journal_id")
    def _compute_payment_method_line_fields(self):
        """แสดงวิธีจ่ายไม่ซ้ำโค้ด จากทุกสมุดที่ใช้ได้."""
        for wizard in self:
            if wizard.available_journal_ids:
                wizard.available_payment_method_line_ids = wizard._vpk_unique_method_lines(
                    wizard._vpk_payment_method_lines_for_type()
                )
            else:
                wizard.available_payment_method_line_ids = False

    @api.depends("payment_type", "available_journal_ids", "payment_method_line_id", "journal_id", "line_ids")
    def _compute_payment_method_line_id(self):
        """คงโค้ดวิธีที่เลือก — สลับเป็น line ของสมุดปัจจุบันเมื่อเปลี่ยนสมุด."""
        for wizard in self:
            all_lines = wizard._vpk_payment_method_lines_for_type()
            available = wizard._vpk_unique_method_lines(all_lines)
            if not available:
                wizard.payment_method_line_id = False
                continue

            current = wizard.payment_method_line_id
            method_code = current.code if current else False
            preferred_code = wizard._vpk_preferred_payment_method_code()

            # PO เป็น GFMIS → ตั้งวิธีตรงเข้า บช ผู้ขายจาก GFMIS จนกว่าผู้ใช้จะเลือกเอง
            if preferred_code and not wizard.vpk_payment_method_touched:
                preferred_line = available.filtered(lambda line: line.code == preferred_code)[:1]
                if preferred_line:
                    if wizard.journal_id:
                        on_journal = wizard._vpk_method_line_on_journal(
                            wizard.journal_id, preferred_code
                        )
                        wizard.payment_method_line_id = on_journal or preferred_line
                    else:
                        wizard.payment_method_line_id = preferred_line
                    continue

            if method_code and wizard.journal_id:
                on_journal = wizard._vpk_method_line_on_journal(
                    wizard.journal_id, method_code
                )
                if on_journal:
                    wizard.payment_method_line_id = on_journal
                    continue

            if current and current in available:
                continue

            if method_code:
                same_code = available.filtered(lambda line: line.code == method_code)[:1]
                if same_code:
                    wizard.payment_method_line_id = same_code
                    continue

            preferred = wizard.line_ids.move_id.preferred_payment_method_line_id
            if len(preferred) == 1 and preferred.code:
                same = available.filtered(lambda line: line.code == preferred.code)[:1]
                if same:
                    wizard.payment_method_line_id = same
                    continue

            wizard.payment_method_line_id = available[0]._origin

    @api.depends(
        "available_journal_ids",
        "payment_method_line_id",
        "payment_method_line_id.code",
        "payment_type",
    )
    def _compute_journal_id(self):
        """หลังเลือกวิธีชำระเงิน ให้สมุดเหลือเฉพาะที่มีวิธีนั้น (ชอบสมุดที่มีบัญชีผูก)."""
        for wizard in self:
            journals = wizard._vpk_journals_for_method_code(
                wizard.payment_method_line_id.code
            )
            if wizard.journal_id in journals:
                continue
            wizard.journal_id = wizard._vpk_pick_journal(journals)

    @api.onchange("payment_method_line_id")
    def _onchange_vpk_payment_method_journal(self):
        """เลือกวิธีชำระเงินก่อน — กรองสมุดบันทึกให้เหลือเฉพาะที่มีวิธีนั้น."""
        if self.payment_method_line_id:
            self.vpk_payment_method_touched = True
        method = self.payment_method_line_id
        journals = self._vpk_journals_for_method_code(method.code if method else False)
        self.vpk_filtered_journal_ids = journals

        if method and method.code:
            if self.journal_id not in journals:
                self.journal_id = self._vpk_pick_journal(journals)
            on_journal = self._vpk_method_line_on_journal(self.journal_id, method.code)
            if on_journal and on_journal != method:
                self.payment_method_line_id = on_journal
            self._onchange_vpk_journal_company_bank()

        return {
            "domain": {
                "journal_id": [("id", "in", journals.ids)],
            }
        }

    def _vpk_banks_linked_to_journal(self, journal):
        """บัญชีธนาคารที่ผูกกับสมุดบันทึก (และสมุดอื่นที่ใช้บัญชี COA เดียวกัน)."""
        self.ensure_one()
        if not journal:
            return self.env["res.partner.bank"]
        company = self.company_id or journal.company_id
        Journal = self.env["account.journal"]
        PartnerBank = self.env["res.partner.bank"]

        if journal.default_account_id:
            sibling_journals = Journal.search(
                [
                    ("type", "=", "bank"),
                    ("company_id", "=", company.id),
                    ("default_account_id", "=", journal.default_account_id.id),
                ]
            )
        else:
            sibling_journals = journal

        # เฉพาะบัญชีที่ผูกไว้จริง: journal.bank_account_id หรือ bank.journal_id
        banks = sibling_journals.mapped("bank_account_id")
        banks |= PartnerBank.search(
            [
                ("journal_id", "in", sibling_journals.ids),
                ("partner_id", "=", company.partner_id.id),
            ]
        )
        return banks.filtered(lambda bank: bool(bank))

    @api.depends("journal_id", "journal_id.default_account_id", "company_id")
    def _compute_available_company_bank_ids(self):
        for wizard in self:
            banks = wizard._vpk_banks_linked_to_journal(wizard.journal_id)
            wizard.available_company_bank_ids = banks
            wizard.has_company_bank_choices = bool(banks)

    @api.depends(
        "journal_id",
        "journal_id.bank_account_id",
        "available_company_bank_ids",
    )
    def _compute_company_bank_id(self):
        for wizard in self:
            banks = wizard.available_company_bank_ids
            preferred = wizard.journal_id.bank_account_id
            if preferred and preferred in banks:
                wizard.company_bank_id = preferred
            elif wizard.company_bank_id in banks:
                continue
            else:
                wizard.company_bank_id = banks[:1] if banks else False

    @api.onchange("journal_id")
    def _onchange_vpk_journal_company_bank(self):
        """เมื่อเลือกสมุดบันทึก — sync วิธีจ่ายและบัญชีธนาคารที่ผูกไว้."""
        banks = self._vpk_banks_linked_to_journal(self.journal_id)
        self.available_company_bank_ids = banks
        self.has_company_bank_choices = bool(banks)
        preferred = self.journal_id.bank_account_id
        if preferred and preferred in banks:
            self.company_bank_id = preferred
        elif self.company_bank_id not in banks:
            self.company_bank_id = banks[:1] if banks else False

        method_code = self.payment_method_line_id.code
        if method_code and self.journal_id:
            on_journal = self._vpk_method_line_on_journal(self.journal_id, method_code)
            if on_journal:
                self.payment_method_line_id = on_journal

        return {
            "domain": {
                "company_bank_id": [("id", "in", banks.ids)],
            }
        }

    @api.onchange("company_bank_id")
    def _onchange_vpk_company_bank_journal(self):
        """เมื่อเลือกบัญชีธนาคารที่ผูกไว้ ให้สลับสมุดบันทึกให้ตรงกัน."""
        bank = self.company_bank_id
        if not bank:
            return
        journal = bank.journal_id
        if not journal:
            journal = self.env["account.journal"].search(
                [
                    ("type", "=", "bank"),
                    ("bank_account_id", "=", bank.id),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if journal and journal != self.journal_id:
            self.journal_id = journal
            method_code = self.payment_method_line_id.code
            on_journal = self._vpk_method_line_on_journal(journal, method_code)
            if on_journal:
                self.payment_method_line_id = on_journal

    def _vpk_is_finance_draft_voucher(self):
        """ดึงรายการจาก Dashboard การเงิน → สร้างใบสำคัญจ่ายฉบับร่าง ไม่ POST."""
        return bool(self.env.context.get("vpk_finance_draft_voucher"))

    def _vpk_sync_method_line_to_journal(self, journal, method_code):
        """ให้ payment_method_line_id อยู่ในสมุดที่เลือก (กัน error ตอนสร้างใบจ่าย)."""
        self.ensure_one()
        if not journal or not method_code:
            return self.payment_method_line_id
        on_journal = self._vpk_method_line_on_journal(journal, method_code)
        return on_journal or self.payment_method_line_id

    def _create_payment_vals_from_wizard(self, batch_result):
        # sync method line ก่อน super สร้าง vals — กรณีเลือกวิธีก่อนแล้วเปลี่ยนสมุด
        journal = self.journal_id
        if self.company_bank_id:
            preferred = self.company_bank_id.journal_id
            if not preferred:
                preferred = self.env["account.journal"].search(
                    [
                        ("type", "=", "bank"),
                        ("bank_account_id", "=", self.company_bank_id.id),
                        ("company_id", "=", self.company_id.id),
                    ],
                    limit=1,
                )
            if preferred:
                journal = preferred
                if self.journal_id != preferred:
                    self.journal_id = preferred
        method_code = self.payment_method_line_id.code
        synced = self._vpk_sync_method_line_to_journal(journal, method_code)
        if synced and synced != self.payment_method_line_id:
            self.payment_method_line_id = synced

        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals.update(
            {
                "vpk_ref_bill_number": self.vpk_ref_bill_number,
                "vpk_ref_po_number": self.vpk_ref_po_number,
                "vpk_ref_wa_number": self.vpk_ref_wa_number,
                "vpk_ref_contract_number": self.vpk_ref_contract_number,
            }
        )
        request_id = self.env.context.get("vpk_payment_request_id")
        if request_id:
            payment_vals["vpk_payment_request_id"] = request_id
        moves = self.line_ids.move_id
        if moves:
            payment_vals["vpk_source_bill_ids"] = [(6, 0, moves.ids)]

        if journal:
            payment_vals["journal_id"] = journal.id
            synced = self._vpk_sync_method_line_to_journal(journal, method_code)
            if synced:
                payment_vals["payment_method_line_id"] = synced.id

        if self.company_bank_id:
            bank_label = self.company_bank_id.display_name
            tag = _("ตัดจาก %s") % bank_label
            memo = payment_vals.get("memo") or ""
            if tag not in memo:
                payment_vals["memo"] = (
                    ("%s | %s" % (memo, tag)).strip(" |") if memo else tag
                )
        return payment_vals

    def _post_payments(self, to_process, edit_mode=False):
        """ใบสำคัญจ่ายจาก Dashboard การเงินค้างร่างไว้ให้อนุมัติก่อน POST.

        หมายเหตุ: ถ้ามี write-off (เช่น WHT) Odoo 18 จะ set state=in_process
        ตอนสร้าง journal entry — ต้องดึงกลับเป็น draft เพื่อรออนุมัติ.
        """
        if self._vpk_is_finance_draft_voucher():
            payments = self.env["account.payment"]
            for vals in to_process:
                payments |= vals.get("payment") or self.env["account.payment"]
            draft_payments = payments.filtered(lambda pay: pay.state != "draft")
            if draft_payments:
                draft_payments.with_context(
                    skip_validation_check=True,
                    skip_account_move_synchronization=True,
                ).write({"state": "draft"})
            return
        return super()._post_payments(to_process, edit_mode=edit_mode)

    def _reconcile_payments(self, to_process, edit_mode=False):
        """ยังไม่ reconcile จนกว่าบัญชีจะ POST ใบสำคัญจ่าย."""
        if self._vpk_is_finance_draft_voucher():
            return
        return super()._reconcile_payments(to_process, edit_mode=edit_mode)

    def action_create_payments(self):
        action = super().action_create_payments()
        if not self._vpk_is_finance_draft_voucher():
            return action
        # จากปุ่มยืนยันรายการจ่าย — ไม่เปิดฟอร์ม/wizard ต่อ
        if self.env.context.get("vpk_finance_silent_create"):
            return True
        if isinstance(action, dict):
            action = dict(action)
            action["name"] = _("รายการชำระเงิน (รอบันทึกบัญชี)")
            action["context"] = {
                **(action.get("context") or {}),
                "create": False,
                "vpk_finance_draft_voucher": True,
            }
        return action
