# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64
from pathlib import Path

from odoo import api, models

WHT_4235_TYPE_CODE = "wht_4235"
WHT_4235_TEMPLATE_CODE = "wht_4235"
WHT_4235_TEMPLATE_NAME = "ใบรับรองหักภาษี ณ. ที่จ่าย แบบ 4235"
WHT_4235_FILENAME = "template_ใบรับรองการหักภาษี_แบบ4235.docx"

WHT_GENERAL_TYPE_CODE = "wht_general"
WHT_GENERAL_TEMPLATE_CODE = "wht_general"
WHT_GENERAL_TEMPLATE_NAME = "ใบรับรองการหักภาษี ณ ที่จ่าย (ทั่วไป)"
WHT_GENERAL_FILENAME = "ใบรับรองการหักภาษี_ทั่วไป.docx"


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    def _vpk_upsert_wht_template_and_fields(
        self,
        type_code,
        type_name,
        type_seq,
        template_code,
        template_name,
        docx_filename,
        local_docx_name,
        field_specs,
    ):
        Type = self.env["vpk.document.studio.document.type"].sudo().with_context(
            active_test=False
        )
        Template = self.sudo().with_context(active_test=False)
        Field = self.env["vpk.document.studio.field"].sudo()
        IrModel = self.env["ir.model"].sudo()
        IrField = self.env["ir.model.fields"].sudo()

        doc_type = Type.search([("code", "=", type_code)], limit=1)
        if not doc_type:
            doc_type = Type.create(
                {
                    "code": type_code,
                    "name": type_name,
                    "sequence": type_seq,
                    "company_id": False,
                }
            )

        source_model = IrModel._get("vpk.wht.cert.4235")
        template = Template.search(
            [
                "|",
                ("code", "=", template_code),
                ("name", "=", template_name),
            ],
            order="id desc",
            limit=1,
        )

        docx_path = (
            Path(__file__).resolve().parents[1] / "data" / local_docx_name
        )
        docx_b64 = (
            base64.b64encode(docx_path.read_bytes()) if docx_path.exists() else False
        )

        vals = {
            "name": template_name,
            "code": template_code,
            "document_type_id": doc_type.id,
            "source_model_id": source_model.id,
            "filename": docx_filename,
            "active": True,
        }
        if docx_b64:
            vals["datas"] = docx_b64

        if template:
            template.write(vals)
        else:
            template = Template.create(vals)

        if docx_b64 and hasattr(template, "_onlyoffice_word_attachment"):
            oo_att = template.with_context(skip_onlyoffice_sync=True)._onlyoffice_word_attachment()
            if oo_att:
                oo_att.with_context(skip_onlyoffice_sync=True).write(
                    {"datas": docx_b64, "name": docx_filename}
                )

        def _field(name):
            return IrField.search(
                [("model_id", "=", source_model.id), ("name", "=", name)], limit=1
            )

        sequence = 10
        for code, name, field_type, map_name in field_specs:
            field = template.field_ids.filtered(lambda rec, c=code: rec.code == c)[:1]
            map_field = _field(map_name)
            field_vals = {
                "template_id": template.id,
                "code": code,
                "name": name,
                "field_type": field_type,
                "sequence": sequence,
                "map_model_id": source_model.id,
                "map_field_id": map_field.id if map_field else False,
                "map_sub_field_id": False,
            }
            if field:
                field.write(field_vals)
            else:
                Field.create(field_vals)
            sequence += 10

        keep = {spec[0] for spec in field_specs}
        stale = template.field_ids.filtered(lambda rec: rec.code not in keep)
        if stale:
            stale.unlink()
        return template

    @api.model
    def _vpk_install_wht_4235_template(self):
        """ตั้งค่าแบบฟอร์ม ใบรับรองหักภาษี ณ. ที่จ่าย แบบ 4235 (wht_4235) และแบบทั่วไป (wht_general)."""
        field_specs_4235 = [
            ("wht_cert_no", "เลขที่รับรองหักภาษี ณ ที่จ่าย", "char", "wht_cert_no"),
            ("wht_disbursement_no", "ตามเอกสารขอเบิกเงินเลขที่", "char", "wht_disbursement_no"),
            ("wht_doc_day", "ลงวันที่ (วัน)", "char", "wht_doc_day"),
            ("wht_doc_month", "ลงวันที่ (เดือน)", "char", "wht_doc_month"),
            ("wht_doc_year", "ลงวันที่ (พ.ศ.)", "char", "wht_doc_year"),
            ("wht_contract_no", "ตามสัญญาเลขที่", "char", "wht_contract_no"),
            ("wht_contract_day", "วัน (สัญญา)", "char", "wht_contract_day"),
            ("wht_contract_month", "เดือน (สัญญา)", "char", "wht_contract_month"),
            ("wht_contract_year", "พ.ศ. (สัญญา)", "char", "wht_contract_year"),
            ("wht_vendor_name", "ชื่อผู้ถูกหักภาษี ณ ที่จ่าย", "char", "wht_vendor_name"),
            ("wht_vendor_address", "ที่อยู่ผู้ถูกหักภาษี ณ ที่จ่าย", "char", "wht_vendor_address"),
            ("wht_transferee_name", "โอนสิทธิเรียกร้องให้แก่", "char", "wht_transferee_name"),
            ("wht_transferee_address", "ที่อยู่ผู้รับโอนสิทธิ", "char", "wht_transferee_address"),
            ("wht_corp_income_type", "ประเภทเงินได้ (นิติบุคคล)", "char", "wht_corp_income_type"),
            ("wht_corp_pay_date", "วันเดือนปีที่จ่าย (นิติบุคคล)", "char", "wht_corp_pay_date"),
            ("wht_corp_base_baht", "เงินได้นิติบุคคล (บาท)", "char", "wht_corp_base_baht"),
            ("wht_corp_base_satang", "เงินได้นิติบุคคล (สต.)", "char", "wht_corp_base_satang"),
            ("wht_corp_tax_baht", "ภาษีนิติบุคคล (บาท)", "char", "wht_corp_tax_baht"),
            ("wht_corp_tax_satang", "ภาษีนิติบุคคล (สต.)", "char", "wht_corp_tax_satang"),
            ("wht_indiv_income_type", "ประเภทเงินได้ (บุคคลธรรมดา)", "char", "wht_indiv_income_type"),
            ("wht_indiv_pay_date", "วันเดือนปีที่จ่าย (บุคคลธรรมดา)", "char", "wht_indiv_pay_date"),
            ("wht_indiv_base_baht", "เงินได้บุคคลธรรมดา (บาท)", "char", "wht_indiv_base_baht"),
            ("wht_indiv_base_satang", "เงินได้บุคคลธรรมดา (สต.)", "char", "wht_indiv_base_satang"),
            ("wht_indiv_tax_baht", "ภาษีบุคคลธรรมดา (บาท)", "char", "wht_indiv_tax_baht"),
            ("wht_indiv_tax_satang", "ภาษีบุคคลธรรมดา (สต.)", "char", "wht_indiv_tax_satang"),
            ("wht_fine_income_type", "ประเภทเงินได้ (ค่าปรับ)", "char", "wht_fine_income_type"),
            ("wht_fine_pay_date", "วันเดือนปีที่จ่าย (ค่าปรับ)", "char", "wht_fine_pay_date"),
            ("wht_fine_base_baht", "เงินได้ค่าปรับ (บาท)", "char", "wht_fine_base_baht"),
            ("wht_fine_base_satang", "เงินได้ค่าปรับ (สต.)", "char", "wht_fine_base_satang"),
            ("wht_fine_tax_baht", "ค่าปรับ (บาท)", "char", "wht_fine_tax_baht"),
            ("wht_fine_tax_satang", "ค่าปรับ (สต.)", "char", "wht_fine_tax_satang"),
            ("wht_total_base_baht", "รวมเงินได้ (บาท)", "char", "wht_total_base_baht"),
            ("wht_total_base_satang", "รวมเงินได้ (สต.)", "char", "wht_total_base_satang"),
            ("wht_total_tax_baht", "รวมภาษี (บาท)", "char", "wht_total_tax_baht"),
            ("wht_total_tax_satang", "รวมภาษี (สต.)", "char", "wht_total_tax_satang"),
            ("wht_total_tax_text", "รวมเงินภาษี (ตัวอักษร)", "char", "wht_total_tax_text"),
            ("wht_signer_name", "ผู้ลงนามใบหักภาษี", "char", "wht_signer_name"),
            ("wht_signer_position", "ตำแหน่งผู้ลงนามใบหักภาษี", "char", "wht_signer_position"),
        ]
        for idx in range(1, 14):
            field_specs_4235.append(
                (f"wht_cid_{idx}", f"เลขประชาชน หลัก {idx}", "char", f"wht_cid_{idx}")
            )
        for idx in range(1, 14):
            field_specs_4235.append(
                (f"wht_tin_{idx}", f"เลขผู้เสียภาษี หลัก {idx}", "char", f"wht_tin_{idx}")
            )

        self._vpk_upsert_wht_template_and_fields(
            WHT_4235_TYPE_CODE,
            WHT_4235_TEMPLATE_NAME,
            245,
            WHT_4235_TEMPLATE_CODE,
            WHT_4235_TEMPLATE_NAME,
            WHT_4235_FILENAME,
            "template_wht_4235.docx",
            field_specs_4235,
        )
        self._vpk_install_wht_general_template()
        return True

    @api.model
    def _vpk_install_wht_general_template(self):
        """ตั้งค่าแบบฟอร์ม ใบรับรองการหักภาษี ณ ที่จ่าย (ทั่วไป) (wht_general)."""
        field_specs_general = [
            ("wht_cheque_no", "เช็คเลขที่", "char", "wht_cheque_no"),
            ("wht_doc_day", "ลงวันที่ (วัน)", "char", "wht_doc_day"),
            ("wht_doc_month", "ลงวันที่ (เดือน)", "char", "wht_doc_month"),
            ("wht_doc_year", "ลงวันที่ (พ.ศ.)", "char", "wht_doc_year"),
            ("wht_vendor_name", "ชื่อผู้ถูกหัก", "char", "wht_vendor_name"),
            ("wht_vendor_address", "ที่อยู่ผู้ถูกหัก", "char", "wht_vendor_address"),
            ("wht_corp_income_type", "ประเภทเงินได้ (นิติบุคคล)", "char", "wht_corp_income_type"),
            ("wht_corp_pay_date", "วัน เดือน ปี ที่จ่าย (นิติบุคคล)", "char", "wht_corp_pay_date"),
            ("wht_corp_base_formatted", "จำนวนเงินได้ (นิติบุคคล)", "char", "wht_corp_base_formatted"),
            ("wht_corp_tax_formatted", "ภาษี (นิติบุคคล)", "char", "wht_corp_tax_formatted"),
            ("wht_indiv_income_type", "ประเภทเงินได้ (บุคคลธรรมดา)", "char", "wht_indiv_income_type"),
            ("wht_indiv_pay_date", "วัน เดือน ปี ที่จ่าย (บุคคลธรรมดา)", "char", "wht_indiv_pay_date"),
            ("wht_indiv_base_formatted", "จำนวนเงินได้ (บุคคลธรรมดา)", "char", "wht_indiv_base_formatted"),
            ("wht_indiv_tax_formatted", "ภาษี (บุคคลธรรมดา)", "char", "wht_indiv_tax_formatted"),
            ("wht_total_base_formatted", "รวมจำนวนเงินได้", "char", "wht_total_base_formatted"),
            ("wht_total_tax_formatted", "รวมภาษี", "char", "wht_total_tax_formatted"),
            ("wht_total_tax_text", "รวมเงินภาษี (ตัวอักษร)", "char", "wht_total_tax_text"),
            ("wht_signer_name", "ผู้ลงนามใบหักภาษี", "char", "wht_signer_name"),
            ("wht_signer_position", "ตำแหน่งผู้ลงนามใบหักภาษี", "char", "wht_signer_position"),
        ]
        for idx in range(1, 14):
            field_specs_general.append(
                (f"wht_vat_{idx}", f"เลขผู้เสียภาษี หลัก {idx}", "char", f"wht_vat_{idx}")
            )

        return self._vpk_upsert_wht_template_and_fields(
            WHT_GENERAL_TYPE_CODE,
            WHT_GENERAL_TEMPLATE_NAME,
            246,
            WHT_GENERAL_TEMPLATE_CODE,
            WHT_GENERAL_TEMPLATE_NAME,
            WHT_GENERAL_FILENAME,
            "template_wht_general.docx",
            field_specs_general,
        )
