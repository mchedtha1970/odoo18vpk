import base64

from odoo import _, fields, models
from odoo.exceptions import ValidationError
from markupsafe import escape


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    fund_source_id = fields.Many2one(
        comodel_name="budget.fund.source",
        string="Fund Source",
        tracking=True,
    )
    budget_workflow_state = fields.Selection(
        selection=[
            ("department", "Department Submitted"),
            ("budget_office", "Budget Office Review"),
            ("management", "Executive Review"),
            ("pending_provincial", "Pending Provincial Health Office"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Budget Workflow Stage",
        default="department",
        tracking=True,
    )
    memo_department_name = fields.Char(
        string="ส่วนราชการ",
        default=lambda self: self.env.company.name,
    )
    memo_phone = fields.Char(string="โทร")
    memo_document_no = fields.Char(
        string="ที่",
        help="เลขหนังสือสำหรับบันทึกข้อความขอซื้อ",
    )
    memo_date = fields.Date(
        string="วันที่บันทึกข้อความ",
        default=fields.Date.context_today,
    )
    memo_subject = fields.Char(
        string="เรื่อง",
        default="รายงานขอซื้อ",
    )
    memo_to = fields.Char(
        string="เรียน",
        default="ผู้อำนวยการ",
    )
    memo_style_preset = fields.Selection(
        selection=[
            ("official", "ทางการ (ค่าเริ่มต้น)"),
            ("formal", "กระชับอ่านง่าย"),
            ("compact", "ประหยัดพื้นที่"),
        ],
        string="รูปแบบเอกสาร",
        default="official",
    )
    memo_body_html = fields.Html(
        string="เนื้อหาบันทึกข้อความ",
        default=(
            "<p>ด้วยหน่วยงานมีความประสงค์ขออนุมัติจัดซื้อพัสดุ/ครุภัณฑ์เพื่อใช้ในการปฏิบัติงาน</p>"
            "<p>จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ</p>"
        ),
    )
    memo_intro = fields.Html(
        string="เกริ่นนำ",
        default="<p>ด้วยหน่วยงานมีความประสงค์ขออนุมัติจัดซื้อพัสดุ/ครุภัณฑ์เพื่อใช้ในการปฏิบัติงาน</p>",
    )
    memo_reason = fields.Html(
        string="เหตุผลและความจำเป็น",
    )
    memo_scope = fields.Html(
        string="รายละเอียดพัสดุที่ขอซื้อ",
    )
    memo_budget_amount = fields.Monetary(
        string="วงเงินงบประมาณที่ขออนุมัติ",
        currency_field="currency_id",
        help="หากไม่ระบุ ระบบจะใช้ยอดประมาณการรวมจากใบขอซื้อ",
    )
    memo_signer_name = fields.Char(string="ผู้จัดทำ")
    memo_signer_position = fields.Char(string="ตำแหน่งผู้จัดทำ")
    memo_approver_name = fields.Char(string="ผู้อนุมัติ")
    memo_approver_position = fields.Char(string="ตำแหน่งผู้อนุมัติ")
    memo_pdf_file = fields.Binary(
        string="ไฟล์ PDF บันทึกข้อความ",
        readonly=True,
        copy=False,
        attachment=True,
    )
    memo_pdf_filename = fields.Char(
        string="ชื่อไฟล์ PDF",
        readonly=True,
        copy=False,
    )
    memo_pdf_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="เอกสาร PDF บันทึกข้อความ",
        readonly=True,
        copy=False,
    )
    committee_memo_date = fields.Date(
        string="วันที่บันทึกแต่งตั้ง",
        default=fields.Date.context_today,
    )
    committee_memo_subject = fields.Char(
        string="เรื่องแต่งตั้ง",
        default="แต่งตั้งคณะกรรมการจัดซื้อจัดจ้าง",
    )
    committee_memo_to = fields.Char(
        string="เรียน (แต่งตั้ง)",
        default="ผู้อำนวยการ",
    )
    committee_memo_body_html = fields.Html(
        string="เนื้อหาบันทึกแต่งตั้ง",
        default=(
            "<p>เพื่อให้การดำเนินการจัดซื้อจัดจ้างเป็นไปตามระเบียบและมีความโปร่งใส "
            "จึงขอแต่งตั้งคณะกรรมการดำเนินงานตามรายชื่อดังต่อไปนี้</p>"
        ),
    )
    committee_memo_pdf_file = fields.Binary(
        string="ไฟล์ PDF บันทึกแต่งตั้ง",
        readonly=True,
        copy=False,
        attachment=True,
    )
    committee_memo_pdf_filename = fields.Char(
        string="ชื่อไฟล์ PDF บันทึกแต่งตั้ง",
        readonly=True,
        copy=False,
    )
    committee_memo_pdf_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="เอกสาร PDF บันทึกแต่งตั้ง",
        readonly=True,
        copy=False,
    )

    def button_to_approve(self):
        self._check_budget_available_before_submit()
        return super().button_to_approve()

    def action_check_budget_status(self):
        self.ensure_one()
        if not self.budget_id:
            raise ValidationError(_("กรุณาเลือก Budget Number ก่อนตรวจสอบสถานะงบประมาณ"))

        snapshot = self.budget_id._get_budget_control_snapshot(exclude_request_id=self.id)
        company_currency = self.company_id.currency_id
        required_amount = self.currency_id._convert(
            self.estimated_cost,
            company_currency,
            self.company_id,
            self.date_start or fields.Date.context_today(self),
        )
        remaining_after_request = snapshot["available"] - required_amount
        is_enough = remaining_after_request >= 0.0
        
        def _format_money(amount):
            amount_text = "{:,.2f}".format(amount or 0.0)
            if company_currency.symbol:
                if company_currency.position == "before":
                    return "{}{}".format(company_currency.symbol, amount_text)
                return "{} {}".format(amount_text, company_currency.symbol)
            return amount_text

        message = _(
            "งบประมาณที่อนุมัติ: %(approved)s\n"
            "ใช้จริงแล้ว: %(actual)s\n"
            "งบผูกพันคงค้าง: %(encumbrance)s\n"
            "งบคงเหลือปัจจุบัน: %(available)s\n"
            "ยอดที่ขอใช้ครั้งนี้: %(requested)s\n"
            "คงเหลือหลังรายการนี้: %(remaining)s"
        ) % {
            "approved": _format_money(snapshot["approved"]),
            "actual": _format_money(snapshot["actual"]),
            "encumbrance": _format_money(snapshot["encumbrance"]),
            "available": _format_money(snapshot["available"]),
            "requested": _format_money(required_amount),
            "remaining": _format_money(remaining_after_request),
        }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("สถานะงบประมาณ: %s") % (_("เพียงพอ") if is_enough else _("ไม่เพียงพอ")),
                "message": message,
                "type": "success" if is_enough else "warning",
                "sticky": True,
            },
        }

    def action_print_purchase_memo(self):
        self.ensure_one()
        report = self.env.ref("hospital_budget_customization.action_report_purchase_request_memo")
        pdf_content, _content_type = report._render_qweb_pdf(self.id)
        filename = "บันทึกข้อความขอซื้อ-{}.pdf".format(self.name or self.id)
        attachment_vals = {
            "name": filename,
            "datas": base64.b64encode(pdf_content),
            "res_model": self._name,
            "res_id": self.id,
            "type": "binary",
            "mimetype": "application/pdf",
        }
        attachment = self.env["ir.attachment"].create(attachment_vals)
        self.write(
            {
                "memo_pdf_file": base64.b64encode(pdf_content),
                "memo_pdf_filename": filename,
                "memo_pdf_attachment_id": attachment.id,
            }
        )
        self.message_post(
            body=_("แนบเอกสารบันทึกข้อความขอซื้ออัตโนมัติ"),
            attachment_ids=[attachment.id],
            subtype_xmlid="mail.mt_note",
        )
        return report.report_action(self)

    def action_print_committee_memo(self):
        self.ensure_one()
        report = self.env.ref(
            "hospital_budget_customization.action_report_purchase_request_committee_memo"
        )
        pdf_content, _content_type = report._render_qweb_pdf(self.id)
        filename = "บันทึกแต่งตั้งคณะกรรมการ-{}.pdf".format(self.name or self.id)
        attachment_vals = {
            "name": filename,
            "datas": base64.b64encode(pdf_content),
            "res_model": self._name,
            "res_id": self.id,
            "type": "binary",
            "mimetype": "application/pdf",
        }
        attachment = self.env["ir.attachment"].create(attachment_vals)
        self.write(
            {
                "committee_memo_pdf_file": base64.b64encode(pdf_content),
                "committee_memo_pdf_filename": filename,
                "committee_memo_pdf_attachment_id": attachment.id,
            }
        )
        self.message_post(
            body=_("แนบเอกสารบันทึกแต่งตั้งคณะกรรมการอัตโนมัติ"),
            attachment_ids=[attachment.id],
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/{}?download=false".format(attachment.id),
            "target": "new",
        }

    def action_view_memo_pdf(self):
        self.ensure_one()
        if not self.memo_pdf_attachment_id:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/{}?download=false".format(self.memo_pdf_attachment_id.id),
            "target": "new",
        }

    def action_view_committee_memo_pdf(self):
        self.ensure_one()
        if not self.committee_memo_pdf_attachment_id:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/{}?download=false".format(
                self.committee_memo_pdf_attachment_id.id
            ),
            "target": "new",
        }

    def _get_memo_amount_display(self):
        self.ensure_one()
        amount = self.memo_budget_amount or self.estimated_cost or 0.0
        symbol = self.currency_id.symbol or ""
        amount_text = "{:,.2f}".format(amount)
        if symbol:
            if self.currency_id.position == "before":
                return "{}{}".format(symbol, amount_text)
            return "{} {}".format(amount_text, symbol)
        return amount_text

    def _get_scope_list_html(self):
        self.ensure_one()
        items = []
        for line in self.line_ids.filtered(lambda l: not l.cancelled):
            name = line.name or line.product_id.display_name or "-"
            qty = "{:,.2f}".format(line.product_qty or 0.0).rstrip("0").rstrip(".")
            uom = line.product_uom_id.name or ""
            items.append(
                "<li>{} ({} {})</li>".format(
                    escape(name),
                    escape(qty),
                    escape(uom),
                )
            )
        if items:
            return "<ul>{}</ul>".format("".join(items))
        return "<p>....................................................................................................</p>"

    def _build_memo_template_html(self, intro_html, reason_html, scope_html):
        self.ensure_one()
        amount_html = "<p><strong>3. วงเงินงบประมาณที่ขออนุมัติ</strong> {}</p>".format(
            escape(self._get_memo_amount_display())
        )
        return """
            {intro}
            <p><strong>1. เหตุผลและความจำเป็น</strong></p>
            {reason}
            <p><strong>2. รายละเอียดพัสดุที่ขอซื้อ</strong></p>
            {scope}
            {amount}
            <p>จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ</p>
        """.format(
            intro=intro_html or "<p></p>",
            reason=reason_html or "<p></p>",
            scope=scope_html or "<p></p>",
            amount=amount_html,
        )

    def action_memo_load_template(self):
        for rec in self:
            intro_html = (
                rec.memo_intro
                or "<p>ด้วยหน่วยงานมีความประสงค์ขออนุมัติจัดซื้อพัสดุ/ครุภัณฑ์เพื่อใช้ในการปฏิบัติงาน</p>"
            )
            reason_html = (
                rec.memo_reason
                or "<p>เนื่องจากมีความจำเป็นในการใช้งานตามภารกิจของหน่วยงาน</p>"
            )
            scope_html = rec.memo_scope or rec._get_scope_list_html()
            rec.memo_body_html = rec._build_memo_template_html(
                intro_html=intro_html,
                reason_html=reason_html,
                scope_html=scope_html,
            )
        return True

    def action_memo_reset_template(self):
        for rec in self:
            rec.memo_body_html = rec._build_memo_template_html(
                intro_html="<p>ด้วยหน่วยงานมีความประสงค์ขออนุมัติจัดซื้อพัสดุ/ครุภัณฑ์เพื่อใช้ในการปฏิบัติงาน</p>",
                reason_html="<p>โปรดระบุเหตุผลและความจำเป็น</p>",
                scope_html=rec._get_scope_list_html(),
            )
        return True

    def action_move_to_budget_office(self):
        self.write({"budget_workflow_state": "budget_office"})

    def action_move_to_management(self):
        self.write({"budget_workflow_state": "management"})

    def action_mark_pending_provincial(self):
        self.write({"budget_workflow_state": "pending_provincial"})

    def button_approved(self):
        self.write({"budget_workflow_state": "approved"})
        return super().button_approved()

    def button_rejected(self):
        self.write({"budget_workflow_state": "rejected"})
        return super().button_rejected()

    def _check_budget_available_before_submit(self):
        for request in self:
            if not request.budget_id:
                continue
            snapshot = request.budget_id._get_budget_control_snapshot(
                exclude_request_id=request.id
            )
            required_amount = request.currency_id._convert(
                request.estimated_cost,
                request.company_id.currency_id,
                request.company_id,
                request.date_start or fields.Date.context_today(request),
            )
            if snapshot["available"] < required_amount:
                raise ValidationError(
                    _(
                        "Budget is insufficient for request %(name)s.\n"
                        "Available: %(available).2f\n"
                        "Requested: %(requested).2f\n"
                        "Please do budget transfer/adjustment before approval."
                    )
                    % {
                        "name": request.name,
                        "available": snapshot["available"],
                        "requested": required_amount,
                    }
                )


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    fund_source_id = fields.Many2one(
        comodel_name="budget.fund.source",
        related="request_id.fund_source_id",
        store=True,
        readonly=True,
    )
