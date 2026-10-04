import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
_PRODUCT_CODE_RE = re.compile(r"^\[[^\]]+\]\s*")
_CRITERIA_TEXT = {
    "lowest_price": (
        "โดยเกณฑ์การพิจารณาผลการยื่นข้อเสนอครั้งนี้ "
        "จะพิจารณาตัดสินโดยใช้หลักเกณฑ์ราคา"
    ),
    "price_performance": (
        "โดยเกณฑ์การพิจารณาผลการยื่นข้อเสนอครั้งนี้ "
        "จะพิจารณาตัดสินโดยใช้หลักเกณฑ์ราคาประกอบเกณฑ์อื่น"
    ),
    "qualification": (
        "โดยเกณฑ์การพิจารณาผลการยื่นข้อเสนอครั้งนี้ "
        "จะพิจารณาตัดสินโดยใช้เกณฑ์คุณสมบัติและเงื่อนไข"
    ),
}


class PurchaseRequisitionAwardReport(models.Model):
    _name = "purchase.requisition.award.report"
    _description = "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อสั่งจ้าง"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่รายงาน",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่รายงาน",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="กระบวนการ eGP",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        domain=[("requisition_type", "=", "egp_procurement")],
    )
    purchase_request_id = fields.Many2one(
        related="requisition_id.purchase_request_id",
        string="ใบขอซื้ออ้างอิง",
        readonly=True,
    )
    egp_reference = fields.Char(
        related="requisition_id.egp_reference",
        string="เลขที่โครงการ e-GP",
        readonly=True,
    )
    subject = fields.Char(
        string="เรื่อง",
        required=True,
        default="รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง",
        tracking=True,
    )
    committee_meeting_date = fields.Date(
        string="วันที่คณะกรรมการพิจารณา",
        tracking=True,
    )
    evaluation_method = fields.Selection(
        selection=[
            ("lowest_price", "เกณฑ์ราคาต่ำสุด"),
            ("price_performance", "เกณฑ์ราคาและประสิทธิภาพ"),
            ("qualification", "เกณฑ์คุณสมบัติและเงื่อนไข"),
        ],
        string="เกณฑ์การพิจารณา",
        required=True,
        default="lowest_price",
        tracking=True,
    )
    winner_bid_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid",
        string="ข้อเสนอที่ได้รับการคัดเลือก",
        domain="[('requisition_id', '=', requisition_id)]",
        tracking=True,
    )
    winner_partner_id = fields.Many2one(
        related="winner_bid_id.partner_id",
        string="ผู้ชนะการเสนอราคา",
        readonly=True,
        store=True,
    )
    winner_amount = fields.Monetary(
        related="winner_bid_id.amount_total",
        string="วงเงินที่ขออนุมัติ",
        currency_field="currency_id",
        readonly=True,
        store=True,
    )
    currency_id = fields.Many2one(
        related="requisition_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="requisition_id.company_id",
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        comodel_name="purchase.requisition.award.report.line",
        inverse_name="report_id",
        string="ผลการพิจารณาผู้เสนอราคา",
        copy=True,
    )
    result_summary = fields.Html(
        string="สรุปผลการพิจารณา",
        default=(
            "<p>คณะกรรมการได้ตรวจสอบคุณสมบัติ เอกสารข้อเสนอ "
            "และเปรียบเทียบราคาของผู้ยื่นข้อเสนอแล้ว</p>"
        ),
    )
    recommendation = fields.Html(
        string="ข้อเสนอเพื่ออนุมัติ",
        default=(
            "<p>จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติสั่งซื้อ/สั่งจ้าง "
            "จากผู้เสนอราคาที่ได้รับการคัดเลือก และดำเนินการในขั้นตอนต่อไป</p>"
        ),
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติ",
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string="วันที่อนุมัติ",
        readonly=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("to_approve", "รออนุมัติ"),
            ("approved", "อนุมัติแล้ว"),
            ("rejected", "ไม่อนุมัติ"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )

    _sql_constraints = [
        (
            "requisition_report_uniq",
            "unique(requisition_id)",
            "กระบวนการ eGP นี้มีรายงานผลการพิจารณาแล้ว",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "purchase.requisition.award.report"
                    )
                    or _("New")
                )
        reports = super().create(vals_list)
        reports._generate_lines_from_bids()
        return reports

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        if self.requisition_id:
            self.subject = _(
                "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อ/สั่งจ้าง โครงการ %s"
            ) % (
                self.requisition_id.egp_project_name
                or self.requisition_id.display_name
            )
            self.winner_bid_id = (
                self.requisition_id.egp_bid_ids.filtered("is_winner")[:1]
            )

    def _generate_lines_from_bids(self):
        for report in self:
            if report.line_ids or not report.requisition_id:
                continue
            commands = []
            for sequence, bid in enumerate(
                report.requisition_id.egp_bid_ids, start=1
            ):
                commands.append((0, 0, {
                    "sequence": sequence * 10,
                    "bid_id": bid.id,
                    "partner_id": bid.partner_id.id,
                    "egp_bid_reference": bid.egp_bid_reference,
                    "bid_date": bid.bid_date,
                    "amount_total": bid.amount_total,
                    "result": (
                        "winner"
                        if bid == report.winner_bid_id or bid.is_winner
                        else "not_selected"
                    ),
                }))
            if commands:
                report.line_ids = commands

    def action_generate_results(self):
        for report in self:
            if report.state != "draft":
                raise UserError(_("สร้างผลการพิจารณาใหม่ได้เฉพาะสถานะร่าง"))
            report.line_ids.unlink()
            report._generate_lines_from_bids()
            if not report.line_ids:
                raise UserError(
                    _("ยังไม่มีข้อเสนอราคาในกระบวนการ eGP สำหรับจัดทำรายงาน")
                )
        return True

    def _sync_winner(self):
        for report in self:
            winner = report.winner_bid_id
            if not winner:
                continue
            (report.requisition_id.egp_bid_ids - winner).write(
                {"is_winner": False}
            )
            winner.write({"is_winner": True})
            for line in report.line_ids:
                line.result = (
                    "winner" if line.bid_id == winner else "not_selected"
                )

    def _update_line_results(self):
        for report in self:
            for line in report.line_ids:
                line.result = (
                    "winner"
                    if line.bid_id == report.winner_bid_id
                    else "not_selected"
                )

    def action_submit(self):
        for report in self:
            if not report.line_ids:
                raise UserError(_("กรุณาสร้างรายการผลการพิจารณาก่อน"))
            if not report.winner_bid_id:
                raise UserError(_("กรุณาเลือกข้อเสนอที่ได้รับการคัดเลือก"))
            if not report.winner_amount:
                raise UserError(_("ข้อเสนอที่ได้รับการคัดเลือกยังไม่มีราคา"))
            report._update_line_results()
            report.state = "to_approve"
        return True

    def action_approve(self):
        self._sync_winner()
        self.write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
        })
        return True

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({
            "state": "draft",
            "approved_by": False,
            "approved_date": False,
        })

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_purchase_agreement_egp.action_report_award_approval"
        ).report_action(self)

    def _file_award_egp_document(self, pdf_bytes):
        """Store the printed report on the e-GP documents tab."""
        self.ensure_one()
        if not pdf_bytes or not self.requisition_id:
            return self.env["purchase.requisition.egp.document"]
        doc_type = self.env.ref(
            "vpk_purchase_agreement_egp.egp_document_type_award_approval",
            raise_if_not_found=False,
        )
        if not doc_type:
            return self.env["purchase.requisition.egp.document"]
        existing = self.requisition_id.egp_document_ids.filtered(
            lambda doc: doc.document_type_id == doc_type
        )[:1]
        if (
            existing
            and "signature_state" in existing._fields
            and existing.signature_state in ("waiting", "signed")
        ):
            return existing
        filename = "รายงานผลการพิจารณา-%s.pdf" % (
            self.name or self.requisition_id.name or self.id
        )
        vals = {
            "document_type_id": doc_type.id,
            "requisition_id": self.requisition_id.id,
            "egp_reference": self.requisition_id.egp_reference,
            "document_date": self.date,
            "document_file": base64.b64encode(pdf_bytes),
            "document_filename": filename,
            "award_report_id": self.id,
        }
        Document = self.env["purchase.requisition.egp.document"]
        if existing:
            existing.write(vals)
            document = existing
        else:
            document = Document.create(vals)
        ensure = getattr(document, "_ensure_award_official_document", None)
        if ensure:
            ensure()
        return document

    def _thai_digits(self, value):
        return str(value).translate(_THAI_DIGITS)

    def _money_text(self, amount):
        return self._thai_digits("{:,.2f}".format(amount or 0.0))

    def _format_memo_date(self):
        self.ensure_one()
        if not self.date:
            return ""
        formatted = self.env["thai.utils"].format_thai_date(self.date)
        return self._thai_digits(formatted)

    def _company_text(self, field_name, default=""):
        company = self.company_id
        if field_name in company._fields and company[field_name]:
            return company[field_name]
        return default

    def _docx_agency(self):
        self.ensure_one()
        company = self.company_id
        agency = self._company_text("vpk_memo_agency", company.name or "")
        request = self.purchase_request_id
        department = ""
        if request and "department_id" in request._fields and request.department_id:
            department = request.department_id.name or ""
        if department and department not in agency:
            agency = ("%s %s" % (department, agency)).strip()
        phone = self._company_text("vpk_memo_phone")
        if not phone and company.phone:
            phone = "โทร. %s" % self._thai_digits(company.phone)
        if phone and phone not in agency:
            agency = "%s  %s" % (agency, phone)
        return agency.strip()

    def _docx_recipient(self):
        self.ensure_one()
        request = self.purchase_request_id
        if request and "memo_to" in request._fields and request.memo_to:
            return request.memo_to
        return self._company_text("vpk_memo_default_to", "ผู้ว่าราชการจังหวัดภูเก็ต")

    def _docx_method_phrase(self):
        self.ensure_one()
        requisition = self.requisition_id
        method = ""
        if requisition.procurement_method_id:
            method = requisition.procurement_method_id.name or ""
        method = method or "วิธีเฉพาะเจาะจง"
        if method.startswith("โดย"):
            return method
        return "โดย%s" % method

    def _docx_item_rows(self):
        self.ensure_one()
        winner = self.winner_bid_id
        bids = winner if winner else self.requisition_id.egp_bid_ids
        rows = []
        for bid in bids:
            vendor = bid.partner_id.name or ""
            agreed_bid = bool(winner and bid == winner) or bool(bid.is_winner)
            lines = bid.line_ids
            if not lines:
                continue
            amounts = [line.price_subtotal or 0.0 for line in lines]
            if not any(amounts) and len(lines) == 1 and bid.amount_total:
                amounts = [bid.amount_total]
            elif not any(amounts) and bid.amount_total:
                amounts = [0.0 for _line in lines]
            for line, amount in zip(lines, amounts):
                rows.append(self._docx_item_from_line(line, vendor, amount, agreed_bid, len(rows) + 1))
        if rows:
            return rows
        for line in self.line_ids:
            agreed = line.result == "winner"
            amount = line.amount_total or 0.0
            label = line.partner_id.name or line.egp_bid_reference or "-"
            rows.append({
                "item_desc": "%s %s" % (self._thai_digits("%s." % (len(rows) + 1)), label),
                "vendor_name": line.partner_id.name or "",
                "offer_price": self._money_text(amount) if amount else "",
                "agreed_price": self._money_text(amount) if agreed and amount else "",
            })
        return rows

    def _docx_item_from_line(self, line, vendor, amount, agreed, index):
        name = (line.name or line.product_id.display_name or "").strip()
        name = _PRODUCT_CODE_RE.sub("", name)
        qty = line.product_qty or 0.0
        uom = line.product_uom_id.name or ""
        if qty:
            qty_text = (
                self._thai_digits(int(qty))
                if float(qty).is_integer()
                else self._thai_digits(qty)
            )
            detail = "%s\nจำนวน %s %s" % (name, qty_text, uom)
        else:
            detail = name
        price = self._money_text(amount) if amount else ""
        return {
            "item_desc": "%s %s" % (self._thai_digits("%s." % index), detail),
            "vendor_name": vendor,
            "offer_price": price,
            "agreed_price": price if agreed else "",
        }

    def _docx_total_text(self, items):
        self.ensure_one()
        if self.winner_amount:
            return self._money_text(self.winner_amount)
        total = 0.0
        for item in items:
            raw = (item.get("agreed_price") or "").translate(
                str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
            ).replace(",", "")
            if raw:
                total += float(raw)
        if not total:
            return ""
        return self._money_text(total)

    def _docx_values(self):
        self.ensure_one()
        items = self._docx_item_rows()
        company = self.company_id
        hospital = company.name or "โรงพยาบาลวชิระภูเก็ต"
        project = self.requisition_id.egp_project_name or ""
        count = self._thai_digits(len(items) or 0)
        if project:
            intro = (
                "ขอรายงานผลการพิจารณา%s จำนวน %s รายการ %s ดังนี้"
                % (project, count, self._docx_method_phrase())
            )
        else:
            intro = (
                "ขอรายงานผลการพิจารณาจัดซื้อจัดจ้าง จำนวน %s รายการ %s ดังนี้"
                % (count, self._docx_method_phrase())
            )
        signer_position = self._company_text(
            "official_doc_signer_position",
            self._company_text("vpk_memo_approver_position", "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"),
        )
        return {
            "agency": self._docx_agency(),
            "memo_number": self._thai_digits(self.name or ""),
            "memo_date": self._format_memo_date(),
            "subject": self.subject or "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อสั่งจ้าง",
            "recipient": self._docx_recipient(),
            "intro": intro,
            "items": items,
            "total_amount": self._docx_total_text(items),
            "criteria": _CRITERIA_TEXT.get(
                self.evaluation_method, _CRITERIA_TEXT["lowest_price"]
            ),
            "hospital_opinion": (
                "%sพิจารณาแล้ว เห็นสมควรจัดซื้อจากผู้เสนอราคาดังกล่าว" % hospital
            ),
            "request_text": (
                "จึงเรียนมาเพื่อโปรดพิจารณา หากเห็นชอบขอได้โปรดอนุมัติให้สั่งซื้อสั่งจ้าง"
                "จากผู้เสนอราคาดังกล่าว"
            ),
            "officer_name": self._company_text("official_doc_officer_name", "........................"),
            "officer_position": self._company_text("official_doc_officer_position", "เจ้าหน้าที่"),
            "head_officer_name": self._company_text(
                "official_doc_head_officer_name",
                self._company_text("vpk_memo_proposer_name", "........................"),
            ),
            "head_officer_position": self._company_text(
                "official_doc_head_officer_position",
                self._company_text("vpk_memo_proposer_position", "หัวหน้าเจ้าหน้าที่"),
            ),
            "approver_authority": signer_position,
            "signer_name": self._company_text(
                "official_doc_signer_name",
                self._company_text("vpk_memo_approver_name", "........................"),
            ),
            "signer_position": signer_position,
            "signer_acting": self._company_text(
                "vpk_memo_approver_acting",
                "ปฏิบัติราชการแทนผู้ว่าราชการจังหวัดภูเก็ต",
            ),
        }

    def _official_award_template(self):
        """Template record already set on หนังสือราชการ for this form."""
        self.ensure_one()
        if "vpk.official.document.template" not in self.env:
            return self.env["purchase.requisition.award.report"]
        templates = self.env["vpk.official.document.template"].sudo().search(
            [("active", "=", True)]
        )
        by_type = templates.filtered(
            lambda item: item.document_type == "award_approval"
        )[:1]
        if by_type:
            return by_type
        for code in ("award_approval", "PO_APP"):
            found = templates.filtered(lambda item, wanted=code: item.code == wanted)
            if found:
                return found[:1]
        return templates.filtered(
            lambda item: "รายงานผลการพิจารณา" in (item.name or "")
        )[:1]

    def _award_template_bytes(self):
        """Load the Word file from the official-document template record."""
        self.ensure_one()
        import base64

        template = self._official_award_template()
        if template and template.datas:
            return base64.b64decode(template.datas), template
        from .award_approval_docx import load_template_bytes

        return load_template_bytes(), template

    def _committee_member_values(self):
        self.ensure_one()
        request = self.purchase_request_id
        lines = request.work_acceptance_committee_ids if (
            request and "work_acceptance_committee_ids" in request._fields
        ) else []
        role_labels = {
            "chairman": "ประธานกรรมการ",
            "committee": "กรรมการ",
        }
        members = []
        for line in lines:
            position = ""
            employee = line.employee_id
            if employee and employee.job_id:
                position = employee.job_id.name or ""
            members.append({
                "name": line.name or "",
                "position": position,
                "role": role_labels.get(line.approve_role, "กรรมการ"),
            })
        return members

    def _specific_method_values(self):
        """Values for the Word template already stored as PO_APP."""
        self.ensure_one()
        amount = self.winner_amount or 0.0
        amount_text = self._money_text(amount) if amount else ""
        baht_text = ""
        if self.currency_id and amount:
            try:
                baht_text = self.currency_id.with_context(lang="th_TH").amount_to_text(
                    amount
                )
            except Exception:
                baht_text = ""
        items = self._docx_item_rows()
        work_lines = []
        for item in items:
            label = (item.get("item_desc") or "").replace("\n", " ")
            price = item.get("agreed_price") or item.get("offer_price") or ""
            if price:
                work_lines.append("%s เป็นเงิน %s บาท" % (label, price))
            elif label:
                work_lines.append(label)
        project = self.requisition_id.egp_project_name or "จัดซื้อจัดจ้าง"
        hospital = self.company_id.name or "โรงพยาบาลวชิระภูเก็ต"
        method = self._docx_method_phrase()
        body = (
            "ด้วย%s  มีความประสงค์ในการ%s  จำนวน  %s  รายการ  "
            "เป็นจำนวนเงินทั้งสิ้น  %s  บาท%s  %s"
        ) % (
            hospital,
            project,
            self._thai_digits(len(items) or 0),
            amount_text or "-",
            ("  (%s)" % baht_text) if baht_text else "",
            method,
        )
        budget_source = "งบประมาณของหน่วยงาน"
        request = self.purchase_request_id
        if request and "budget_source" in request._fields and request.budget_source:
            budget_source = request.budget_source
        delivery = "๓๐"
        if request and "memo_delivery_days" in request._fields and request.memo_delivery_days:
            delivery = self._thai_digits(request.memo_delivery_days)
        signer_position = self._company_text(
            "official_doc_signer_position",
            self._company_text(
                "vpk_memo_approver_position", "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"
            ),
        )
        return {
            "agency": self._docx_agency(),
            "memo_number": self._thai_digits(self.name or ""),
            "order_date": self._format_memo_date(),
            "subject": self.subject or "รายงานผลการพิจารณาและขออนุมัติสั่งซื้อสั่งจ้าง",
            "recipient": self._docx_recipient(),
            "body": body,
            "reason": "เพื่อจัดซื้อจัดจ้าง%s" % project,
            "work_detail": "\n".join(work_lines),
            "amount_text": amount_text,
            "baht_text": baht_text,
            "price_mid_source": "ราคาที่ได้รับการพิจารณา",
            "budget_source": budget_source,
            "delivery_days": delivery,
            "criteria_text": _CRITERIA_TEXT.get(
                self.evaluation_method, _CRITERIA_TEXT["lowest_price"]
            ).replace("โดยเกณฑ์การพิจารณาผลการยื่นข้อเสนอครั้งนี้ จะพิจารณาตัดสินโดยใช้", "การพิจารณาคัดเลือกข้อเสนอโดยใช้"),
            "members": self._committee_member_values(),
            "officer_name": self._company_text("official_doc_officer_name", ""),
            "officer_position": self._company_text("official_doc_officer_position", "เจ้าหน้าที่"),
            "head_officer_name": self._company_text(
                "official_doc_head_officer_name",
                self._company_text("vpk_memo_proposer_name", ""),
            ),
            "head_officer_position": self._company_text(
                "official_doc_head_officer_position",
                self._company_text("vpk_memo_proposer_position", "หัวหน้าเจ้าหน้าที่"),
            ),
            "signer_name": self._company_text(
                "official_doc_signer_name",
                self._company_text("vpk_memo_approver_name", ""),
            ),
            "signer_position": signer_position,
            "approver_acting": self._company_text(
                "vpk_memo_approver_acting",
                "ปฏิบัติราชการแทนผู้ว่าราชการจังหวัดภูเก็ต",
            ),
        }

    def _render_docx_bytes(self):
        self.ensure_one()
        from .award_approval_docx import (
            AwardApprovalRenderError,
            render_award_approval_docx,
        )

        template_bytes, template = self._award_template_bytes()
        if not template_bytes:
            raise UserError(
                _("ไม่พบไฟล์แบบฟอร์มรายงานผลการพิจารณาในเอกสารราชการ")
            )
        render_errors = (AwardApprovalRenderError,)
        try:
            from odoo.addons.vpk_official_document.models.docx_renderer import (
                OfficialDocumentRenderError,
                render_specific_method_approval_docx,
            )
        except ImportError:
            OfficialDocumentRenderError = AwardApprovalRenderError
            render_specific_method_approval_docx = None
        render_errors = (AwardApprovalRenderError, OfficialDocumentRenderError)
        use_award_form = bool(
            template and template.document_type == "award_approval"
        ) or b"item_desc" in template_bytes
        try:
            if use_award_form:
                return render_award_approval_docx(
                    template_bytes, self._docx_values()
                )
            if render_specific_method_approval_docx is None:
                raise UserError(
                    _("ไม่พบตัวเติมแบบฟอร์มในโมดูลเอกสารราชการ")
                )
            return render_specific_method_approval_docx(
                template_bytes, self._specific_method_values()
            )
        except render_errors as error:
            label = template.display_name if template else ""
            raise UserError(
                _("เติมแบบฟอร์ม %s ไม่สำเร็จ: %s") % (label, error)
            ) from error

    def _render_pdf_from_docx(self):
        self.ensure_one()
        docx_content = self._render_docx_bytes()
        try:
            from odoo.addons.vpk_official_document.models.pdf_converter import (
                PdfConversionError,
                convert_docx_bytes_to_pdf,
            )
        except ImportError as error:
            raise UserError(
                _("ไม่พบตัวแปลง PDF กรุณาติดตั้งโมดูลเอกสารราชการก่อนพิมพ์รายงานผล")
            ) from error
        try:
            return convert_docx_bytes_to_pdf(docx_content)
        except PdfConversionError as error:
            raise UserError(str(error)) from error

    def action_create_winner_announcement(self):
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("ต้องอนุมัติรายงานผลก่อนสร้างประกาศผู้ชนะ"))
        return self.requisition_id.action_create_winner_announcement()


class PurchaseRequisitionAwardReportLine(models.Model):
    _name = "purchase.requisition.award.report.line"
    _description = "ผลการพิจารณาผู้เสนอราคา"
    _order = "sequence, id"

    report_id = fields.Many2one(
        comodel_name="purchase.requisition.award.report",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    bid_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.bid",
        string="ข้อเสนอราคา",
        ondelete="set null",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้เสนอราคา",
        required=True,
    )
    egp_bid_reference = fields.Char(string="เลขที่ใบเสนอราคา")
    bid_date = fields.Date(string="วันที่เสนอราคา")
    currency_id = fields.Many2one(
        related="report_id.currency_id",
        store=True,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="ราคาที่เสนอ",
        currency_field="currency_id",
    )
    result = fields.Selection(
        selection=[
            ("winner", "ได้รับการคัดเลือก"),
            ("not_selected", "ไม่ถูกคัดเลือก"),
            ("disqualified", "ไม่ผ่านคุณสมบัติ"),
        ],
        string="ผลการพิจารณา",
        default="not_selected",
        required=True,
    )
    notes = fields.Char(string="เหตุผล/หมายเหตุ")


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    award_report_ids = fields.One2many(
        comodel_name="purchase.requisition.award.report",
        inverse_name="requisition_id",
        string="รายงานผลการพิจารณา",
        copy=False,
    )
    award_report_count = fields.Integer(
        compute="_compute_award_report_count",
    )
    egp_award_approved = fields.Boolean(
        string="รายงานผลได้รับอนุมัติแล้ว",
        compute="_compute_egp_award_approved",
    )

    @api.depends("award_report_ids")
    def _compute_award_report_count(self):
        for requisition in self:
            requisition.award_report_count = len(requisition.award_report_ids)

    @api.depends("award_report_ids.state")
    def _compute_egp_award_approved(self):
        for requisition in self:
            requisition.egp_award_approved = bool(
                requisition.award_report_ids.filtered(
                    lambda report: report.state == "approved"
                )
            )

    def action_create_award_report(self):
        self.ensure_one()
        if len(self.egp_bid_ids) < 1:
            raise UserError(
                _("ต้องมีข้อเสนอราคาอย่างน้อย 1 รายการก่อนจัดทำรายงานผล")
            )
        report = self.award_report_ids[:1]
        if not report:
            winner = self.egp_bid_ids.filtered("is_winner")[:1]
            report = self.env["purchase.requisition.award.report"].create({
                "requisition_id": self.id,
                "winner_bid_id": winner.id if winner else False,
                "committee_meeting_date": fields.Date.context_today(self),
            })
        return {
            "type": "ir.actions.act_window",
            "name": _("รายงานผลการพิจารณาและขออนุมัติ"),
            "res_model": "purchase.requisition.award.report",
            "res_id": report.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_award_reports(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายงานผลการพิจารณา"),
            "res_model": "purchase.requisition.award.report",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {"default_requisition_id": self.id},
        }
