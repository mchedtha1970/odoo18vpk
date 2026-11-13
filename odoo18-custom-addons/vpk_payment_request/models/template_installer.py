# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
from odoo import api, models

from odoo.addons.vpk_document_studio_procurement.models.template_installer import (
    MEMO_HEADER,
    TEXT_CODES,
    _heading,
    _para,
    _sign,
)

PAYMENT_REQUEST_CODE = "payment_request"
PAYMENT_REQUEST_NAME = "บันทึกข้อความขออนุมัติเบิกจ่าย"
PAYMENT_REQUEST_BLOCKS = [
    MEMO_HEADER,
    _para("{{body}}"),
    _heading("รายละเอียดการเบิกจ่าย"),
    _para("{{payment_detail}}", indent=False, align="left"),
    _para(
        "จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติเบิกจ่ายเงินให้{{vendor_name}}  "
        "เป็นจำนวนเงินสุทธิ  {{pay_amount}}  บาท  ({{baht_text}})  "
        "และส่งเรื่องให้เจ้าหนี้ดำเนินการต่อไป"
    ),
    _sign("เจ้าหน้าที่", "officer_name", "officer_position", align="left"),
    _sign("หัวหน้าเจ้าหน้าที่", "head_officer_name", "head_officer_position"),
    _para("อนุมัติ", indent=False, align="center"),
    _sign("", "signer_name", "signer_position", align="center", prefix=""),
]


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    @api.model
    def _vpk_install_payment_request_template(self):
        Type = self.env["vpk.document.studio.document.type"].sudo().with_context(active_test=False)
        Template = self.sudo().with_context(active_test=False)
        Block = self.env["vpk.document.studio.block"].sudo()
        company = self.env.ref("base.main_company", raise_if_not_found=False) or self.env.company
        doc_type = Type.search([("code", "=", PAYMENT_REQUEST_CODE), ("company_id", "=", False)], limit=1)
        if not doc_type:
            doc_type = Type.create(
                {
                    "code": PAYMENT_REQUEST_CODE,
                    "name": PAYMENT_REQUEST_NAME,
                    "sequence": 200,
                    "company_id": False,
                }
            )
        if Template.search([("document_type_id", "=", doc_type.id)], limit=1):
            return True
        template = Template.create(
            {
                "name": PAYMENT_REQUEST_NAME,
                "code": "vpk_%s" % PAYMENT_REQUEST_CODE,
                "document_type_id": doc_type.id,
                "source_model_id": self.env["ir.model"]._get("purchase.order").id,
                "company_id": company.id,
            }
        )
        Block.with_context(skip_layout_regen=True).create(
            [
                dict(vals, template_id=template.id, sequence=(index + 1) * 10)
                for index, vals in enumerate(PAYMENT_REQUEST_BLOCKS)
            ]
        )
        template._regenerate_layout_from_blocks()
        template.field_ids.filtered(
            lambda field: field.code in TEXT_CODES or field.code == "payment_detail"
        ).write({"field_type": "text"})
        return True
