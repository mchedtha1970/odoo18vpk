# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import api, models

PAYMENT_REQUEST_CODE = "payment_request"


class ProcurementDocumentValues(models.AbstractModel):
    _inherit = "vpk.procurement.document.values"

    @api.model
    def values_for(self, record, type_code=False):
        if type_code == PAYMENT_REQUEST_CODE and record:
            values = self._payment_request_values(record)
            if values is not None:
                return values
        return super().values_for(record, type_code)

    @api.model
    def _payment_request_acceptance(self, record):
        """ใบตรวจรับที่ขอเบิกจ่าย: จาก WA โดยตรง หรือ context หรือใบแรกที่ยังไม่ขอ."""
        if record._name == "work.acceptance":
            return record
        wa_id = self.env.context.get("vpk_payment_wa_id")
        if wa_id:
            return self.env["work.acceptance"].browse(wa_id).exists()
        if record._name == "purchase.order":
            return record._vpk_payment_available_wa()[:1]
        return self.env["work.acceptance"]

    @api.model
    def _payment_request_values(self, record):
        acceptance = self._payment_request_acceptance(record).sudo()
        if not acceptance:
            return None
        order = acceptance.purchase_id
        values = dict(self.values_from_acceptance(acceptance, PAYMENT_REQUEST_CODE))
        company = order.company_id
        vendor = order.partner_id.name or ""
        contract = acceptance.contract_id if "contract_id" in acceptance._fields else False
        if contract:
            ref_text = "ตามสัญญา เลขที่ %s" % self.thai(contract.name)
        else:
            ref_text = "ตามใบสั่งซื้อ เลขที่ %s" % self.thai(order.name or "")
        installment = (
            acceptance.contract_installment_id
            if "contract_installment_id" in acceptance._fields
            else False
        )
        gross = acceptance.amount_total or 0.0
        penalty = acceptance.penalty_amount or 0.0
        pay = acceptance.payment_amount or 0.0
        accept_date = self.thai_date(acceptance.acceptance_date) if acceptance.acceptance_date else ""
        project = values.get("item_summary") or order.name or ""
        body = (
            "ด้วย  %(vendor)s  ได้ส่งมอบพัสดุ/งาน  %(ref)s  สำหรับ  %(project)s  "
            "และคณะกรรมการตรวจรับพัสดุได้ตรวจรับตามใบตรวจรับเลขที่  %(wa)s%(date)s  เรียบร้อยแล้ว  "
            "จึงขออนุมัติเบิกจ่ายเงินให้ผู้ขาย"
        ) % {
            "vendor": vendor,
            "ref": ref_text,
            "project": project,
            "wa": self.thai(acceptance.name or ""),
            "date": ("  เมื่อวันที่  %s" % accept_date) if accept_date else "",
        }
        lines = [
            "ใบสั่งซื้อเลขที่  %s" % self.thai(order.name or ""),
            "ผู้ขาย  %s" % vendor,
            "ใบตรวจรับเลขที่  %s%s"
            % (
                self.thai(acceptance.name or ""),
                ("  (%s)" % self.thai(installment.name)) if installment else "",
            ),
            "มูลค่าตามใบตรวจรับ  %s  บาท" % self.money(gross),
        ]
        if penalty:
            lines.append("หักค่าปรับ  %s  บาท" % self.money(penalty))
        lines.append("จำนวนเงินที่ขอเบิกจ่ายสุทธิ  %s  บาท" % self.money(pay))
        values.update(
            {
                "subject": "ขออนุมัติเบิกจ่ายเงิน  %s  ตามใบสั่งซื้อ  %s"
                % (vendor, self.thai(order.name or "")),
                "body": body,
                "payment_detail": "\n".join(lines),
                "pay_amount": self.money(pay),
                "baht_text": self.baht_text(pay, company),
                "wa_no": self.thai(acceptance.name or "-"),
                "po_name": order.name or "",
                "vendor_name": vendor,
            }
        )
        return values
