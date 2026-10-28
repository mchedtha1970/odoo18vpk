from odoo import api, models

TEXT_CODES = {
    "body",
    "work_detail",
    "committee_lines",
    "spec_committee_lines",
    "intro",
    "inspect_intro",
    "inspection_signers",
    "integrity_people",
    "integrity_signers",
}
LEGAL_TEXT = (
    "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  พ.ศ. ๒๕๖๐  "
    "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  พ.ศ. ๒๕๖๐  "
    "และกฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจง  "
    "วงเงินการจัดซื้อจัดจ้างที่ไม่ทำข้อตกลงเป็นหนังสือ  "
    "และวงเงินการจัดซื้อจัดจ้างในการแต่งตั้งผู้ตรวจรับพัสดุ  พ.ศ. ๒๕๖๐"
)


def _p(text):
    return "<p>%s</p>" % text


def _heading(text, align="left", size=16, bold=True):
    return {
        "block_type": "heading",
        "heading_text": text,
        "heading_align": align,
        "heading_size": size,
        "heading_bold": bold,
    }


def _para(text, indent=True, align="justify"):
    return {
        "block_type": "paragraph",
        "content": _p(text),
        "first_line_indent": indent,
        "align": align,
    }


def _sign(role, name_code, position_code, align="right", prefix="ลงชื่อ"):
    return {
        "block_type": "signature",
        "sig_prefix": prefix,
        "sig_role": role,
        "code_name": name_code,
        "code_position": position_code,
        "sig_align": align,
    }


MEMO_HEADER = {"block_type": "memo_header", "show_recipient": True, "code_number": "saraban_no_th"}

TEMPLATES = {
    "wa_committee_order": (
        "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ",
        [
            _heading("คำสั่ง{{agency}}", align="center", size=18),
            _heading("ที่  {{saraban_no_th}}", align="center", bold=False),
            _heading("เรื่อง  {{subject}}", align="center", bold=False),
            _heading("---------------------------------------------------", align="center", bold=False),
            _para("{{body}}"),
            _para("{{committee_lines}}", indent=False, align="left"),
            _para(
                "โดยให้มีอำนาจหน้าที่  ทำการตรวจรับพัสดุให้เป็นไปตามเงื่อนไขของสัญญาหรือข้อตกลงนั้น  "
                "และปฏิบัติตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
                "พ.ศ. ๒๕๖๐"
            ),
            _para("ทั้งนี้  ตั้งแต่บัดนี้เป็นต้นไป  หรือจนกว่าจะดำเนินการตรวจรับพัสดุแล้วเสร็จ"),
            _para("สั่ง  ณ  วันที่  {{order_date_th}}"),
            _sign("", "signer_name", "signer_position", prefix=""),
        ],
    ),
    "spec_price_committee": (
        "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะเฉพาะและราคากลาง",
        [
            MEMO_HEADER,
            _heading("๑. ต้นเรื่อง"),
            _para("{{body}}"),
            _heading("๒. ระเบียบ/วิธีปฏิบัติ"),
            _para(
                "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  พ.ศ. ๒๕๖๐  "
                "ข้อ  ๒๑  ในการซื้อหรือจ้างที่มิใช่การจ้างก่อสร้าง  ให้หัวหน้าหน่วยงานของรัฐแต่งตั้ง"
                "คณะกรรมการขึ้นมาคณะหนึ่งหรือจะให้เจ้าหน้าที่หรือบุคคลใดบุคคลหนึ่งรับผิดชอบ"
                "ในการจัดทำร่างขอบเขตของงานหรือรายละเอียดคุณลักษณะเฉพาะของพัสดุที่จะซื้อหรือจ้าง"
            ),
            _heading("๓. ข้อเสนอ"),
            _para(
                "เพื่อให้การดำเนินการจัดซื้อ/จัดจ้างดังกล่าว  เป็นไปอย่างมีประสิทธิภาพ  "
                "เกิดประโยชน์สูงสุดแก่ทางราชการ  และเป็นไปตามข้อกฎหมายและหนังสือสั่งการที่เกี่ยวข้อง  "
                "จึงเห็นควรแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะเฉพาะและกำหนดราคากลาง  ดังนี้"
            ),
            _para("{{spec_committee_lines}}", indent=False, align="left"),
            _para(
                "จึงเรียนมาเพื่อโปรดพิจารณา  หากเห็นชอบตามข้อเสนอ  "
                "โปรดลงนามในคำสั่งแต่งตั้งคณะกรรมการฯ  ที่แนบมาพร้อมบันทึกนี้ด้วย  จักเป็นพระคุณ"
            ),
            _sign("", "signer_name", "signer_position", prefix=""),
        ],
    ),
    "specific_method_approval": (
        "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
        [
            MEMO_HEADER,
            _para("{{body}}"),
            _heading("๑. เหตุผลและความจำเป็นที่ต้องซื้อหรือจ้าง"),
            _para("{{reason_text}}"),
            _heading("๒. รายละเอียดของพัสดุที่จะซื้อหรือจ้าง"),
            _para("{{work_detail}}", indent=False, align="left"),
            _heading("๓. ราคากลางและรายละเอียดของราคากลาง"),
            _para("จำนวน  {{amount_text}}  บาท  ({{baht_text}})  จาก{{price_mid_source}}"),
            _heading("๔. วงเงินที่จะซื้อหรือจ้าง"),
            _para(
                "ภายในวงเงินงบประมาณ  {{amount_text}}  บาท  ({{baht_text}})  "
                "โดยเบิกจ่ายจาก{{budget_source}}"
            ),
            _heading("๕. กำหนดเวลาที่ต้องการใช้พัสดุนั้นหรือให้งานนั้นแล้วเสร็จ"),
            _para(
                "กำหนดเวลาส่งมอบงานหรือให้งานแล้วเสร็จภายใน  {{delivery_days_th}}  วัน  "
                "นับถัดจากวันที่ลงนามในสัญญา"
            ),
            _heading("๖. วิธีที่จะซื้อหรือจ้าง  และเหตุผลที่ต้องซื้อหรือจ้าง"),
            _para(
                "โดย{{procurement_method}}  ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ  "
                "พ.ศ. ๒๕๖๐  มาตรา  ๕๖  (๒)  (ข)  การจัดซื้อจัดจ้างที่มีการผลิต  จำหน่าย  ก่อสร้าง  "
                "หรือให้บริการทั่วไป  และมีวงเงินในการจัดซื้อจัดจ้างครั้งหนึ่งไม่เกิน  ๕๐๐,๐๐๐  บาท"
            ),
            _heading("๗. หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ"),
            _para("การพิจารณาคัดเลือกข้อเสนอโดยใช้เกณฑ์ราคา"),
            _heading("๘. ข้อเสนออื่น ๆ"),
            _para("แต่งตั้งคณะกรรมการตรวจรับพัสดุ  " + LEGAL_TEXT + "  ดังนี้"),
            _para("{{committee_lines}}", indent=False, align="left"),
            _para(
                "จึงเรียนมาเพื่อโปรดพิจารณา  หากเห็นชอบขอได้โปรด  "
                "๑. อนุมัติให้ความเห็นชอบรายงานขออนุมัติจัดซื้อ/จัดจ้าง  "
                "และอนุมัติให้ดำเนินการตามรายละเอียดข้างต้น  ภายในวงเงิน  {{amount_text}}  บาท  "
                "({{baht_text}})  ๒. อนุมัติแต่งตั้งคณะกรรมการตรวจรับพัสดุตามรายชื่อที่เสนอข้างต้น"
            ),
            _sign("เจ้าหน้าที่", "officer_name", "officer_position", align="left"),
            _sign("หัวหน้าเจ้าหน้าที่", "head_officer_name", "head_officer_position"),
            _para("อนุมัติ", indent=False, align="center"),
            _sign("", "signer_name", "signer_position", align="center", prefix=""),
            _para("{{approver_acting}}", indent=False, align="center"),
        ],
    ),
    "purchase_approval_memo": (
        "บันทึกข้อความอนุมัติขอซื้อ",
        [
            MEMO_HEADER,
            _para("{{body}}"),
            _para("{{work_detail}}", indent=False, align="left"),
            _para("จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ"),
            _sign("ผู้เสนอ", "proposer_name", "proposer_position"),
            _sign("ผู้พิจารณา", "head_officer_name", "head_officer_position", align="left"),
            _sign("ผู้อนุมัติ", "signer_name", "signer_position"),
        ],
    ),
    "integrity_over_100k": (
        "แบบแสดงความบริสุทธิ์ใจ (วงเงินมากกว่า ๑๐๐,๐๐๐ บาท)",
        [
            _heading("แบบแสดงความบริสุทธิ์ใจในการจัดซื้อจัดจ้างทุกวิธีของหน่วยงาน", align="center"),
            _heading("ในการเปิดเผยข้อมูลความขัดแย้งทางผลประโยชน์", align="center"),
            _heading("ของหัวหน้าเจ้าหน้าที่, เจ้าหน้าที่  และคณะกรรมการตรวจรับพัสดุ", align="center"),
            _heading("-----------------------------------", align="center", bold=False),
            _para("{{integrity_people}}", indent=False, align="left"),
            _para(
                "ขอให้คำรับรองว่าไม่มีความเกี่ยวข้องหรือมีส่วนได้ส่วนเสียไม่ว่าโดยตรงหรือโดยอ้อม  "
                "หรือผลประโยชน์ใด ๆ  ที่ก่อให้เกิดความขัดแย้งทางผลประโยชน์กับผู้ขาย  ผู้รับจ้าง  "
                "ผู้เสนองาน  หรือผู้ชนะประมูล  หรือผู้มีส่วนเกี่ยวข้องที่เข้ามามีนิติสัมพันธ์  "
                "และวางตัวเป็นกลางในการดำเนินการเกี่ยวกับการพัสดุ  ปฏิบัติหน้าที่ด้วยจิตสำนึก  "
                "ด้วยความโปร่งใส  สามารถให้มีการตรวจสอบได้  และปฏิบัติหน้าที่อย่างเต็มขีดความสามารถ  "
                "เพื่อให้การจัดซื้อจัดจ้างของ{{item_summary}}  เกิดประโยชน์สูงสุด"
            ),
            _para(
                "หากปรากฏว่าเกิดความขัดแย้งทางผลประโยชน์ระหว่างข้าพเจ้ากับผู้ขาย  ผู้รับจ้าง  "
                "ผู้เสนองาน  หรือผู้ชนะประมูล  หรือผู้มีส่วนเกี่ยวข้องที่เข้ามามีนิติสัมพันธ์  "
                "ข้าพเจ้าจะรายงานให้ทราบโดยเร็วที่สุด  เพื่อพิจารณาว่าข้าพเจ้าควรถอนตัว"
                "ออกจากผู้มีส่วนเกี่ยวข้องกับการจัดซื้อจัดจ้างครั้งนี้หรือไม่"
            ),
            _para("{{integrity_signers}}", indent=False, align="center"),
        ],
    ),
    "inspection_report": (
        "ใบตรวจรับการจัดซื้อ/จัดจ้าง",
        [
            _heading("ใบตรวจรับการจัดซื้อ/จัดจ้าง", align="center", size=18),
            _heading("{{report_date}}", align="right", bold=False),
            _para("{{intro}}"),
            _para("{{inspect_intro}}"),
            _heading("๑. ผลการตรวจรับ"),
            _para(
                "{{chk_correct}} ถูกต้อง<br/>{{chk_complete}} ครบถ้วนตามสัญญา<br/>"
                "{{chk_incomplete}} ไม่ครบถ้วนตามสัญญา"
            ),
            _heading("๒. ค่าปรับ"),
            _para("{{chk_fine}} มีค่าปรับ{{fine_text}}<br/>{{chk_nofine}} ไม่มีค่าปรับ"),
            _heading("๓. การเบิกจ่ายเงิน"),
            _para("เบิกจ่ายเงิน เป็นจำนวนเงินทั้งสิ้น {{pay_amount}} บาท"),
            _para("{{inspection_signers}}", indent=False, align="center"),
            _para(
                "หมายเหตุ : เลขที่โครงการ {{project_no}}<br/>เลขคุมสัญญา {{contract_no}}<br/>"
                "เลขคุมตรวจรับ {{wa_no}}",
                indent=False,
                align="left",
            ),
        ],
    ),
    "winner_announcement": (
        "ประกาศผู้ชนะการเสนอราคา",
        [
            _heading("ประกาศ{{agency}}", align="center", size=18),
            _heading("เรื่อง  {{subject}}", align="center", bold=False),
            _heading("---------------------------------------------------", align="center", bold=False),
            _para("{{body_intro}}"),
            _para("{{body_winner}}"),
            _para("ประกาศ  ณ  วันที่  {{announce_date_th}}", indent=False, align="center"),
            _sign("", "signer_name", "signer_position", align="center", prefix=""),
            _para("{{approver_acting}}", indent=False, align="center"),
        ],
    ),
}

DOCUMENT_TYPES = [
    ("wa_committee_order", "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ", "purchase.request"),
    ("spec_price_committee", "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะ", "purchase.request"),
    ("specific_method_approval", "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง", "purchase.request"),
    ("ebidding_method_approval", "รายงานขออนุมัติดำเนินการประกวดราคาด้วยวิธี e-bidding", "purchase.request"),
    ("purchase_approval_memo", "บันทึกข้อความอนุมัติขอซื้อ", "purchase.request"),
    ("integrity_over_100k", "แบบแสดงความบริสุทธิ์ใจ (วงเงินมากกว่า ๑๐๐,๐๐๐ บาท)", "purchase.request"),
    ("inspection_report", "ใบตรวจรับการจัดซื้อ/จัดจ้าง", "work.acceptance"),
    ("winner_announcement", "ประกาศผู้ชนะการเสนอราคา", "purchase.requisition"),
    ("award_approval", "รายงานผลการพิจารณาจัดซื้อจัดจ้าง", "purchase.requisition"),
    ("egp_document", "เอกสารกระบวนการ e-GP", "purchase.requisition"),
]


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    @api.model
    def _vpk_keep_soffice_path(self):
        params = self.env["ir.config_parameter"].sudo()
        legacy = params.get_param("vpk_official_document.soffice_path")
        if legacy and not params.get_param("vpk_document_studio.soffice_path"):
            params.set_param("vpk_document_studio.soffice_path", legacy)
        return True

    @api.model
    def _vpk_install_procurement_templates(self):
        self._vpk_keep_soffice_path()
        Type = self.env["vpk.document.studio.document.type"].sudo().with_context(active_test=False)
        Template = self.sudo().with_context(active_test=False)
        Block = self.env["vpk.document.studio.block"].sudo()
        company = self.env.ref("base.main_company", raise_if_not_found=False) or self.env.company
        for sequence, (code, name, model_name) in enumerate(DOCUMENT_TYPES, start=1):
            doc_type = Type.search([("code", "=", code), ("company_id", "=", False)], limit=1)
            if not doc_type:
                doc_type = Type.create(
                    {"code": code, "name": name, "sequence": sequence * 10, "company_id": False}
                )
            spec = TEMPLATES.get(code)
            if not spec or Template.search([("document_type_id", "=", doc_type.id)], limit=1):
                continue
            template_name, blocks = spec
            source_model = self.env["ir.model"]._get(model_name) if model_name in self.env else False
            template = Template.create(
                {
                    "name": template_name,
                    "code": "vpk_%s" % code,
                    "document_type_id": doc_type.id,
                    "source_model_id": source_model.id if source_model else False,
                    "company_id": company.id,
                }
            )
            Block.with_context(skip_layout_regen=True).create(
                [
                    dict(vals, template_id=template.id, sequence=(index + 1) * 10)
                    for index, vals in enumerate(blocks)
                ]
            )
            template._regenerate_layout_from_blocks()
            template.field_ids.filtered(lambda f: f.code in TEXT_CODES).write(
                {"field_type": "text"}
            )
        return True
