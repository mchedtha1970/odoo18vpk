# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import api, models

GFMIS_VENDOR_DIRECT_CODE = "gfmis_vendor_direct"


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res[GFMIS_VENDOR_DIRECT_CODE] = {
            "mode": "multi",
            "type": ("bank",),
        }
        return res

    @api.model
    def _vpk_ensure_gfmis_vendor_direct_method_lines(self):
        """สร้างบรรทัดวิธีจ่ายบนสมุดธนาคารที่ยังไม่มี."""
        method = self.env.ref(
            "vpk_payment_request.account_payment_method_gfmis_vendor_direct",
            raise_if_not_found=False,
        )
        if not method:
            method = self.search(
                [
                    ("code", "=", GFMIS_VENDOR_DIRECT_CODE),
                    ("payment_type", "=", "outbound"),
                ],
                limit=1,
            )
        if not method:
            return
        journals = self.env["account.journal"].search([("type", "=", "bank")])
        Line = self.env["account.payment.method.line"]
        for journal in journals:
            exists = journal.outbound_payment_method_line_ids.filtered(
                lambda line, m=method: line.payment_method_id == m
            )
            if exists:
                continue
            Line.create(
                {
                    "payment_method_id": method.id,
                    "journal_id": journal.id,
                    "name": method.name,
                }
            )


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _get_method_codes_using_bank_account(self):
        """แสดงบัญชีธนาคารผู้รับบนฟอร์มจ่าย (สำหรับอ้างอิง GFMIS)."""
        codes = super()._get_method_codes_using_bank_account()
        return list(codes) + [GFMIS_VENDOR_DIRECT_CODE]

    @api.model
    def _get_method_codes_needing_bank_account(self):
        """ไม่บังคับ validate/trust บัญชีผู้รับ — จ่ายจริงผ่าน GFMIS ไม่ใช่ไฟล์โอน Odoo.

        ถ้าใส่โค้ดนี้ใน needing list จะ error เมื่อบัญชีผู้รับยังไม่น่าเชื่อถือ
        (allow_out_payment=False) ซึ่งพบบ่อยกับผู้ขายในระบบโรงพยาบาล.
        """
        return super()._get_method_codes_needing_bank_account()
