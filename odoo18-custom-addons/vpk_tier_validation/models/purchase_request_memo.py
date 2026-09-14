# -*- coding: utf-8 -*-
"""Helpers and default content for VPK official memo (บันทึกข้อความ)."""

from pathlib import Path

from markupsafe import Markup

from odoo import api, fields, models

THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
COMMITTEE_ROLE_LABELS = {
    "chairman": "ประธานกรรมการ",
    "committee": "กรรมการ",
}

MEMO_EXCEPTION_FIELDS = [
    "memo_agency",
    "memo_ref_prefix",
    "memo_ref",
    "memo_date",
    "memo_subject",
    "memo_to",
    "memo_item_summary",
    "memo_procurement_method",
    "memo_delivery_days",
    "memo_show_committee",
    "memo_body",
    "memo_body_page2",
    "memo_closing",
    "memo_approval",
    "memo_proposer_name",
    "memo_proposer_position",
    "memo_approver_name",
    "memo_approver_position",
    "memo_approver_acting",
]


def _load_official_memo_inline_css():
    static_dir = Path(__file__).resolve().parent.parent / "static/src"
    fonts_css = (static_dir / "scss/thai_fonts_embedded.scss").read_text(
        encoding="utf-8"
    )
    layout_css = (static_dir / "css/official_memo_report_layout.css").read_text(
        encoding="utf-8"
    )
    return f"{fonts_css}\n{layout_css}"


class PurchaseRequestMemo(models.Model):
    _inherit = "purchase.request"

    memo_agency = fields.Char(string="ส่วนราชการ")
    memo_ref_prefix = fields.Char(
        string="คำนำหน้าเลขที่",
        default="ภก ๐๐๓๓.๒๐๑/",
    )
    memo_ref = fields.Char(string="ที่ (เลขที่หนังสือ)")
    memo_date = fields.Date(
        string="วันที่หนังสือ",
        default=fields.Date.context_today,
    )
    memo_subject = fields.Char(string="เรื่อง")
    memo_to = fields.Char(string="เรียน")
    memo_item_summary = fields.Char(string="รายการพัสดุ/บริการ (สรุป)")
    memo_procurement_method = fields.Char(string="วิธีจัดซื้อจัดจ้าง (ข้อความ)")
    memo_delivery_days = fields.Integer(string="ระยะเวลาส่งมอบ (วัน)", default=365)
    memo_show_committee = fields.Boolean(
        string="แสดงคณะกรรมการในเอกสาร",
        default=True,
    )
    memo_body = fields.Html(string="เนื้อหา (ข้อ ๑-๖)")
    memo_body_page2 = fields.Html(string="เนื้อหา (ข้อ ๗-๑๐)")
    memo_closing = fields.Html(string="ข้อความปิดท้าย (หน้า ๓)")
    memo_approval = fields.Html(string="หน้าอนุมัติ (หน้า ๔)")
    memo_proposer_name = fields.Char(string="ผู้เสนอ (ชื่อ)")
    memo_proposer_position = fields.Char(string="ผู้เสนอ (ตำแหน่ง)")
    memo_approver_name = fields.Char(string="ผู้อนุมัติ (ชื่อ)")
    memo_approver_position = fields.Char(string="ผู้อนุมัติ (ตำแหน่ง)")
    memo_approver_acting = fields.Char(
        string="ผู้อนุมัติ (ปฏิบัติราชการแทน)",
    )

    @api.model
    def _get_validation_exceptions(self, extra_domain=None, add_base_exceptions=True):
        res = super()._get_validation_exceptions(extra_domain, add_base_exceptions)
        return list(set(res + MEMO_EXCEPTION_FIELDS))

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        return list(
            set(
                res
                + MEMO_EXCEPTION_FIELDS
                + [
                    "approved_by",
                    "date_approved",
                    "verified_by",
                    "date_verified",
                ]
            )
        )

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        return list(set(res + MEMO_EXCEPTION_FIELDS))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_memo_defaults(vals)
        return super().create(vals_list)

    def _apply_memo_defaults(self, vals):
        company = self.env.company
        vals.setdefault("memo_agency", company.vpk_memo_agency)
        vals.setdefault("memo_to", company.vpk_memo_default_to)
        if not vals.get("memo_subject") and vals.get("name"):
            vals["memo_subject"] = vals["name"]
        if not vals.get("memo_ref") and vals.get("name"):
            vals["memo_ref"] = vals["name"]

    @api.onchange("name", "description")
    def _onchange_memo_defaults(self):
        if not self.memo_subject:
            self.memo_subject = self.description or self.name
        if not self.memo_ref and self.name:
            self.memo_ref = self.name
        if not self.memo_agency:
            self.memo_agency = self.env.company.vpk_memo_agency
        if not self.memo_to:
            self.memo_to = self.env.company.vpk_memo_default_to

    def _thai_digits(self, value):
        if value is None:
            return ""
        return str(value).translate(THAI_DIGITS)

    def _format_memo_date_thai(self):
        self.ensure_one()
        if not self.memo_date:
            return ""
        return self.env["thai.utils"].format_thai_date(self.memo_date)

    def _get_memo_agency_display(self):
        self.ensure_one()
        agency = self.memo_agency or self.env.company.vpk_memo_agency or ""
        phone = self.env.company.vpk_memo_phone or ""
        if phone and phone not in agency:
            return f"{agency} {phone}".strip()
        return agency

    def _get_memo_ref_display(self):
        self.ensure_one()
        prefix = self.memo_ref_prefix or ""
        ref = self.memo_ref or self.name or ""
        return f"{prefix}{self._thai_digits(ref)}"

    def action_print_official_memo(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_tier_validation.action_report_purchase_request_official_memo"
        ).report_action(self)

    @api.model
    def _get_official_memo_inline_css(self):
        """Inline fonts + layout CSS for wkhtmltopdf offline PDF rendering."""
        return Markup(_load_official_memo_inline_css())

    def _memo_company_name(self):
        return self.company_id.name or "โรงพยาบาลวชิระภูเก็ต"

    def _get_memo_item_summary(self):
        self.ensure_one()
        if self.memo_item_summary:
            return self.memo_item_summary
        if self.line_ids:
            line = self.line_ids[0]
            qty = int(line.product_qty) if line.product_qty == int(line.product_qty) else line.product_qty
            return line.name or line.product_id.display_name or ""
        return self.description or self.memo_subject or ""

    def _get_memo_procurement_method_label(self):
        self.ensure_one()
        if self.memo_procurement_method:
            return self.memo_procurement_method
        if self.procurement_method_id:
            name = self.procurement_method_id.name or ""
            if "bid" in name.lower() or "e-" in name.lower():
                return "วิธีประกวดราคาอิเล็กทรอนิกส์ (e-bidding)"
            return name
        return "วิธีประกวดราคาอิเล็กทรอนิกส์ (e-bidding)"

    def _format_thai_currency(self, amount):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        value = currency.round(amount or 0.0)
        formatted = f"{value:,.2f}"
        return self._thai_digits(formatted)

    def _get_memo_opening_paragraph(self):
        self.ensure_one()
        item = self._get_memo_item_summary()
        method = self._get_memo_procurement_method_label()
        amount = self._format_thai_currency(self.estimated_cost)
        agency = self.memo_agency or self.env.company.vpk_memo_agency or "กลุ่มงานพัสดุ"
        return (
            f"ด้วย {agency} มีความประสงค์จะดำเนินการ{item} "
            f"ด้วย{method} วงเงินประมาณ {amount} บาท "
            f"เพื่อใช้ในการปฏิบัติงานของ{self._memo_company_name()} "
            f"จึงขอดำเนินการตามระเบียบที่เกี่ยวข้อง โดยมีรายละเอียดดังนี้"
        )

    @staticmethod
    def _memo_item_block(title, body=""):
        if body:
            return f'<p class="vpk-memo-para-indent"><strong>{title}</strong> {body}</p>'
        return f'<p class="vpk-memo-para-indent"><strong>{title}</strong></p>'

    @staticmethod
    def _memo_sub_item_block(content):
        return f'<p class="vpk-memo-para-indent">{content}</p>'

    def _get_committee_employee_position(self, employee):
        if not employee:
            return ""
        if employee.job_title:
            return employee.job_title
        if employee.job_id:
            return employee.job_id.name
        return ""

    def _get_memo_committee_formal_list(self, committee_type="procurement"):
        self.ensure_one()
        if committee_type == "procurement":
            members = self.procurement_committee_ids
            chairman_role = "ประธานกรรมการฯ"
        else:
            members = self.work_acceptance_committee_ids
            chairman_role = "ประธานกรรมการ"
        members = members.sorted(
            key=lambda c: (0 if c.approve_role == "chairman" else 1, c.id)
        )
        org = self._memo_company_name()
        result = []
        for index, member in enumerate(members, start=1):
            if member.approve_role == "chairman":
                role = chairman_role
            else:
                role = COMMITTEE_ROLE_LABELS.get(member.approve_role, "กรรมการ")
            result.append(
                {
                    "no": index,
                    "name": member.name,
                    "role": role,
                    "position": self._get_committee_employee_position(member.employee_id),
                    "organization": org,
                }
            )
        return result

    def _get_default_memo_body_html(self):
        self.ensure_one()
        item = self._get_memo_item_summary()
        method = self._get_memo_procurement_method_label()
        amount = self._format_thai_currency(self.estimated_cost)
        days = self._thai_digits(self.memo_delivery_days or 365)
        company = self._memo_company_name()
        blocks = [
            self._memo_item_block(
                "๑. เหตุผลและความจำเป็นที่ต้องดำเนินการ",
                f"ด้วยกลุ่มภารกิจของ{company} มีความจำเป็นต้อง{item} "
                f"เพื่อใช้ในการปฏิบัติงานตามภารกิจ วงเงินประมาณ {amount} บาท",
            ),
            self._memo_item_block(
                "๒. รายละเอียดคุณลักษณะเฉพาะของพัสดุที่จะดำเนินการ",
                f"{item} ตามรายละเอียดในใบขอซื้อเลขที่ {self.name or ''}",
            ),
            self._memo_item_block(
                "๓. ราคากลางของพัสดุที่จะดำเนินการ",
                f"ราคากลาง {amount} บาท",
            ),
            self._memo_item_block(
                "๔. วงเงินที่จะดำเนินการ",
                f"{item} ด้วย{method} วงเงิน {amount} บาท",
            ),
            self._memo_item_block(
                "๕. กำหนดเวลาที่ต้องการใช้พัสดุนั้น หรือให้งานนั้นแล้วเสร็จ",
                f"ให้แล้วเสร็จภายใน {days} วัน นับแต่วันที่ลงนามในสัญญา",
            ),
            (
                '<p class="vpk-memo-para-indent"><strong>๖. วิธีที่จะดำเนินการ '
                "และเหตุผลที่ต้องดำเนินการโดยวิธีนั้น</strong></p>"
                + self._memo_sub_item_block(
                    f"<u>๖.๑ วิธีที่จะดำเนินการ</u> {method} "
                    "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐"
                )
                + self._memo_sub_item_block(
                    f"<u>๖.๒ เหตุผลที่ต้องดำเนินการโดยวิธีนี้</u> "
                    f"เนื่องจากวงเงินเกิน ๕๐๐,๐๐๐ บาท จึงต้องดำเนินการโดย{method}"
                )
            ),
        ]
        return Markup("\n".join(blocks))

    def _get_default_memo_body_page2_html(self):
        self.ensure_one()
        item = self._get_memo_item_summary()
        method = self._get_memo_procurement_method_label()
        company = self._memo_company_name()
        blocks = [
            self._memo_item_block(
                "๗. หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ",
                "การพิจารณาคัดเลือกข้อเสนอโดยใช้เกณฑ์ราคา",
            ),
            self._memo_item_block(
                "๘. ร่างประกาศ และร่างเอกสารประกวดราคา",
                f"ร่างประกาศและร่างเอกสาร{method} สำหรับ{item} "
                f"เพื่อเผยแพร่รับฟังความคิดเห็นผ่านเว็บไซต์{company} "
                "และเว็บไซต์กรมบัญชีกลาง",
            ),
            (
                '<p class="vpk-memo-para-indent"><strong>๙. ข้อระเบียบและกฎหมาย</strong></p>'
                + self._memo_sub_item_block(
                    "๙.๑ พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐"
                )
                + self._memo_sub_item_block(
                    "๙.๒ ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
                    "พ.ศ. ๒๕๖๐ ข้อ ๒๒"
                )
                + self._memo_sub_item_block(
                    f"๙.๓ คำสั่งจังหวัดภูเก็ต เรื่อง มอบอำนาจให้ผู้อำนวยการ{company} "
                    "อนุมัติการจัดซื้อจัดจ้างตามวิธีเฉพาะเจาะจง/ประกาศเชิญชวงวงเงินไม่เกิน ๑๐,๐๐๐,๐๐๐ บาท"
                )
            ),
            (
                '<p class="vpk-memo-para-indent"><strong>๑๐. ข้อเสนออื่น ๆ</strong></p>'
                + self._memo_sub_item_block(
                    "๑๐.๑ ให้ดำเนินการตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
                    "พ.ศ. ๒๕๖๐ ข้อ ๒๕ (๑) และ (๕)"
                )
                + self._memo_sub_item_block(
                    "๑๐.๒ แต่งตั้งคณะกรรมการพิจารณาผลการประกวดราคาอิเล็กทรอนิกส์ "
                    "และคณะกรรมการตรวจรับพัสดุ ดังต่อไปนี้"
                )
            ),
        ]
        return Markup("\n".join(blocks))

    def _get_default_memo_closing_html(self):
        self.ensure_one()
        item = self._get_memo_item_summary()
        method = self._get_memo_procurement_method_label()
        return Markup(
            f"""
<p class="vpk-memo-para-indent">ตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ
พ.ศ. ๒๕๖๐ ข้อ ๕๕ ข้อ ๕๖ ข้อ ๕๗ ข้อ ๕๘ และข้อ ๑๗๕
ให้แต่งตั้งคณะกรรมการตรวจรับพัสดุสำหรับ{item}
ด้วย{method} ตามรายละเอียดข้างต้น</p>

<p class="vpk-memo-para-indent">จึงเรียนมาเพื่อโปรดพิจารณา หากเห็นชอบขอได้โปรด</p>
<ol class="vpk-memo-ol">
<li>อนุมัติการดำเนินการ{item} ด้วย{method}</li>
<li>ลงนามในคำสั่งแต่งตั้งคณะกรรมการพิจารณาผลการประกวดราคาอิเล็กทรอนิกส์
และคณะกรรมการตรวจรับพัสดุ</li>
<li>ลงนามในร่างประกาศและร่างเอกสาร{method}</li>
</ol>
"""
        )

    def _get_default_memo_approval_html(self):
        self.ensure_one()
        item = self._get_memo_item_summary()
        method = self._get_memo_procurement_method_label()
        return Markup(
            f"""
<p class="vpk-memo-salutation">เรียน {self.memo_to or 'ผู้ว่าราชการจังหวัดภูเก็ต'}</p>
<ol class="vpk-memo-ol">
<li>ได้ตรวจสอบแล้วเห็นควรอนุมัติให้ดำเนินการ{item}
ด้วย{method} ตามที่เสนอ</li>
<li>ลงนามในคำสั่งแต่งตั้งคณะกรรมการพิจารณาผลการประกวดราคาอิเล็กทรอนิกส์
และคณะกรรมการตรวจรับพัสดุ</li>
<li>ลงนามในร่างประกาศและร่างเอกสาร{method} สำหรับ{item}</li>
<li>เป็นอำนาจของผู้อำนวยการ{self._memo_company_name()}</li>
</ol>
"""
        )

    def action_generate_memo_content(self):
        for rec in self:
            if not rec.memo_item_summary:
                rec.memo_item_summary = rec._get_memo_item_summary()
            if not rec.memo_procurement_method:
                rec.memo_procurement_method = rec._get_memo_procurement_method_label()
            rec.memo_body = rec._get_default_memo_body_html()
            rec.memo_body_page2 = rec._get_default_memo_body_page2_html()
            rec.memo_closing = rec._get_default_memo_closing_html()
            rec.memo_approval = rec._get_default_memo_approval_html()
            company = rec.company_id
            if not rec.memo_proposer_name and company.vpk_memo_proposer_name:
                rec.memo_proposer_name = company.vpk_memo_proposer_name
            if not rec.memo_proposer_position and company.vpk_memo_proposer_position:
                rec.memo_proposer_position = company.vpk_memo_proposer_position
            if not rec.memo_approver_name and company.vpk_memo_approver_name:
                rec.memo_approver_name = company.vpk_memo_approver_name
            if not rec.memo_approver_position and company.vpk_memo_approver_position:
                rec.memo_approver_position = company.vpk_memo_approver_position
            if not rec.memo_approver_acting and company.vpk_memo_approver_acting:
                rec.memo_approver_acting = company.vpk_memo_approver_acting
        return True

    @api.onchange("line_ids", "estimated_cost", "procurement_method_id")
    def _onchange_memo_auto_summary(self):
        if not self.memo_item_summary and self.line_ids:
            self.memo_item_summary = self._get_memo_item_summary()
        if not self.memo_procurement_method and self.procurement_method_id:
            self.memo_procurement_method = self._get_memo_procurement_method_label()
