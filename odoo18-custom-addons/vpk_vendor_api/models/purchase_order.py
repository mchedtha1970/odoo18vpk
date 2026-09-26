# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import base64

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.vpk_official_document.models.pdf_stamp import (
    SignatureStampError,
    stamp_signature_on_pdf,
)

from .pdf_stamp import stamp_signature_bottom_left


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends("vpk_po_sent_on", "state", "vendor_signed", "signed_by", "signed_on")
    def _compute_vpk_vendor_confirm_state(self):
        return super()._compute_vpk_vendor_confirm_state()

    def _vpk_stamp_vendor_signature(self, signature_b64):
        """Replace the stored PO PDF with a copy that includes the vendor signature."""
        self.ensure_one()
        raw = (signature_b64 or "").strip()
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        if not raw:
            raise UserError(_("กรุณาลงลายเซ็น"))
        try:
            signature_bytes = base64.b64decode(raw)
        except Exception as error:
            raise UserError(_("ข้อมูลลายเซ็นไม่ถูกต้อง")) from error
        attachment = self._vpk_po_pdf_attachment()
        if not attachment or not attachment.raw:
            raise UserError(_("ยังไม่มีไฟล์ PDF ของใบสั่งซื้อ"))
        pdf_bytes = bytes(attachment.raw)
        try:
            stamped = stamp_signature_on_pdf(
                pdf_bytes, signature_bytes, ["ลงนามผู้รับจ้าง"]
            )
        except SignatureStampError:
            stamped = stamp_signature_bottom_left(pdf_bytes, signature_bytes)
        self._vpk_upsert_po_pdf(stamped)
        return self
