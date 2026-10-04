from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionWinnerAnnouncement(models.Model):
    _name = "purchase.requisition.winner.announcement"
    _description = "ประกาศผู้ชนะการเสนอราคา"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่ประกาศ",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่ประกาศ",
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
    award_report_id = fields.Many2one(
        comodel_name="purchase.requisition.award.report",
        string="รายงานผลการพิจารณาที่อนุมัติ",
        required=True,
        ondelete="restrict",
        domain="[('requisition_id', '=', requisition_id), ('state', '=', 'approved')]",
        tracking=True,
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
        default="ประกาศผู้ชนะการเสนอราคา",
        tracking=True,
    )
    winner_partner_id = fields.Many2one(
        related="award_report_id.winner_partner_id",
        string="ผู้ชนะการเสนอราคา",
        store=True,
        readonly=True,
    )
    winner_amount = fields.Monetary(
        related="award_report_id.winner_amount",
        string="ราคาที่เสนอ",
        currency_field="currency_id",
        store=True,
        readonly=True,
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
    procurement_method_id = fields.Many2one(
        related="requisition_id.procurement_method_id",
        string="วิธีการจัดซื้อจัดจ้าง",
        readonly=True,
    )
    reason = fields.Html(
        string="เหตุผลที่ได้รับการคัดเลือก",
        default=(
            "<p>เป็นผู้มีคุณสมบัติครบถ้วน ถูกต้องตามเงื่อนไข "
            "และเสนอราคาต่ำสุด/เหมาะสม เป็นประโยชน์ต่อทางราชการ</p>"
        ),
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("published", "ประกาศแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
    )
    published_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ประกาศ",
        readonly=True,
        tracking=True,
    )
    published_date = fields.Datetime(
        string="วันเวลาที่ประกาศ",
        readonly=True,
        tracking=True,
    )

    _sql_constraints = [
        (
            "requisition_announcement_uniq",
            "unique(requisition_id)",
            "กระบวนการ eGP นี้มีประกาศผู้ชนะแล้ว",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "purchase.requisition.winner.announcement"
                    )
                    or _("New")
                )
        return super().create(vals_list)

    @api.onchange("requisition_id")
    def _onchange_requisition_id(self):
        if self.requisition_id:
            self.award_report_id = self.requisition_id.award_report_ids.filtered(
                lambda report: report.state == "approved"
            )[:1]
            self.subject = _("ประกาศผู้ชนะการเสนอราคา โครงการ %s") % (
                self.requisition_id.egp_project_name
                or self.requisition_id.display_name
            )

    def action_publish(self):
        for announcement in self:
            if announcement.award_report_id.state != "approved":
                raise UserError(
                    _("ต้องอนุมัติรายงานผลการพิจารณาก่อนประกาศผู้ชนะ")
                )
            if not announcement.winner_partner_id:
                raise UserError(_("ไม่พบผู้ชนะการเสนอราคา"))
            announcement.write({
                "state": "published",
                "published_by": self.env.user.id,
                "published_date": fields.Datetime.now(),
            })
            announcement.message_post(
                body=_("เผยแพร่ประกาศผู้ชนะการเสนอราคาแล้ว")
            )
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({
            "state": "draft",
            "published_by": False,
            "published_date": False,
        })

    def _report_province(self):
        self.ensure_one()
        company = self.company_id
        state = company.state_id or company.partner_id.state_id
        name = state.name if state else "ภูเก็ต"
        if name.startswith("จังหวัด"):
            return name
        return "จังหวัด%s" % name

    def _report_agency(self):
        self.ensure_one()
        company = self.company_id
        if "official_doc_agency" in company._fields and company.official_doc_agency:
            return company.official_doc_agency
        return company.name or ""

    def _report_method_phrase(self):
        self.ensure_one()
        method = self.procurement_method_id.name or "วิธีเฉพาะเจาะจง"
        if method.startswith("โดย"):
            return method
        if method.startswith("วิธี"):
            return "โดย%s" % method
        return "โดยวิธี%s" % method

    def _report_thai_digits(self, value):
        return str(value).translate(
            str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
        )

    def _report_thai_date(self):
        self.ensure_one()
        date_value = self.date
        if not date_value:
            return ""
        if "thai.utils" in self.env:
            formatted = self.env["thai.utils"].format_thai_date(
                date_value,
                format_date="{day} {month} พ.ศ. {year}",
            )
        else:
            months = (
                "",
                "มกราคม",
                "กุมภาพันธ์",
                "มีนาคม",
                "เมษายน",
                "พฤษภาคม",
                "มิถุนายน",
                "กรกฎาคม",
                "สิงหาคม",
                "กันยายน",
                "ตุลาคม",
                "พฤศจิกายน",
                "ธันวาคม",
            )
            formatted = "%s %s พ.ศ. %s" % (
                date_value.day,
                months[date_value.month],
                date_value.year + 543,
            )
        return self._report_thai_digits(formatted)

    def _report_amount_display(self):
        self.ensure_one()
        return self._report_thai_digits("{:,.2f}".format(self.winner_amount or 0.0))

    def _report_amount_text(self):
        self.ensure_one()
        currency = self.currency_id
        if not currency:
            return ""
        try:
            return currency.with_context(lang="th_TH").amount_to_text(
                self.winner_amount or 0.0
            )
        except Exception:
            return currency.amount_to_text(self.winner_amount or 0.0) or ""

    def _report_signer_full(self):
        self.ensure_one()
        company = self.company_id
        if "official_doc_signer_name" in company._fields and company.official_doc_signer_name:
            return company.official_doc_signer_name
        return "นายวีระศักดิ์ หล่อทองคำ"

    def _report_signer_title(self):
        self.ensure_one()
        company = self.company_id
        if (
            "official_doc_signer_position" in company._fields
            and company.official_doc_signer_position
        ):
            return company.official_doc_signer_position
        return "ผู้อำนวยการโรงพยาบาลวชิระภูเก็ต"

    def _winner_egp_document(self):
        self.ensure_one()
        return self.requisition_id.egp_document_ids.filtered(
            lambda doc: doc.document_type_code == "winner_announcement"
        )[:1]

    def _docx_values(self):
        """Values for Word template — same mapping as Gen บนแท็บเอกสาร e-GP."""
        self.ensure_one()
        egp = self._winner_egp_document()
        if egp:
            return egp._winner_announcement_values()
        # Fallback เมื่อยังไม่มีแถวเอกสาร e-GP: สร้างค่าจากประกาศนี้โดยตรง
        Document = self.env["purchase.requisition.egp.document"]
        winner_type = self.env.ref(
            "vpk_purchase_agreement_egp.egp_document_type_winner_announcement"
        )
        temp = Document.new(
            {
                "requisition_id": self.requisition_id.id,
                "document_type_id": winner_type.id,
                "egp_reference": self.egp_reference,
                "document_date": self.date,
            }
        )
        return temp._winner_announcement_values()

    def _render_docx_bytes(self):
        self.ensure_one()
        from .winner_announcement_docx import (
            WinnerAnnouncementRenderError,
            load_template_bytes,
            render_winner_announcement_docx,
        )

        try:
            return render_winner_announcement_docx(
                load_template_bytes(),
                self._docx_values(),
            )
        except WinnerAnnouncementRenderError as error:
            raise UserError(str(error)) from error

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
                _("ไม่พบตัวแปลง PDF กรุณาติดตั้งโมดูลเอกสารราชการก่อนพิมพ์ประกาศผู้ชนะ")
            ) from error
        try:
            return convert_docx_bytes_to_pdf(docx_content)
        except PdfConversionError as error:
            raise UserError(str(error)) from error

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "vpk_purchase_agreement_egp.action_report_winner_announcement"
        ).report_action(self)


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    winner_announcement_ids = fields.One2many(
        comodel_name="purchase.requisition.winner.announcement",
        inverse_name="requisition_id",
        string="ประกาศผู้ชนะ",
        copy=False,
    )
    winner_announcement_count = fields.Integer(
        compute="_compute_winner_announcement_count",
    )

    @api.depends("winner_announcement_ids")
    def _compute_winner_announcement_count(self):
        for requisition in self:
            requisition.winner_announcement_count = len(
                requisition.winner_announcement_ids
            )

    def action_file_winner_announcement(self):
        """สร้างไฟล์ประกาศผู้ชนะแล้วเก็บในแท็บเอกสาร e-GP."""
        self.ensure_one()
        if not self._get_egp_winner_bid() and not self.vendor_id:
            raise UserError(
                _("กรุณาเลือกผู้ชนะในแท็บเปรียบเทียบราคาก่อนสร้างประกาศผู้ชนะ")
            )
        doc_type = self.env.ref(
            "vpk_purchase_agreement_egp.egp_document_type_winner_announcement",
            raise_if_not_found=False,
        )
        if not doc_type:
            raise UserError(_("ไม่พบหัวข้อเอกสารประกาศผู้ชนะ"))
        existing = self.egp_document_ids.filtered(
            lambda doc: doc.document_type_id == doc_type
        )[:1]
        if (
            existing
            and "signature_state" in existing._fields
            and existing.signature_state in ("waiting", "signed")
        ):
            raise UserError(_("เอกสารถูกส่งลงนามแล้ว ไม่สามารถสร้างใหม่ได้"))
        vals = {
            "document_type_id": doc_type.id,
            "requisition_id": self.id,
            "egp_reference": self.egp_reference,
            "document_date": fields.Date.context_today(self),
        }
        if existing:
            existing.write(vals)
            document = existing
        else:
            document = self.env["purchase.requisition.egp.document"].create(vals)
        document.action_generate_winner_document()
        return True

    def action_create_winner_announcement(self):
        self.ensure_one()
        approved_report = self.award_report_ids.filtered(
            lambda report: report.state == "approved"
        )[:1]
        if not approved_report:
            raise UserError(
                _(
                    "กรุณาจัดทำและอนุมัติรายงานผลการพิจารณา "
                    "ก่อนสร้างประกาศผู้ชนะ"
                )
            )
        announcement = self.winner_announcement_ids[:1]
        if not announcement:
            announcement = self.env[
                "purchase.requisition.winner.announcement"
            ].create({
                "requisition_id": self.id,
                "award_report_id": approved_report.id,
                "subject": _("ประกาศผู้ชนะการเสนอราคา โครงการ %s")
                % (self.egp_project_name or self.display_name),
            })
        return {
            "type": "ir.actions.act_window",
            "name": _("ประกาศผู้ชนะการเสนอราคา"),
            "res_model": "purchase.requisition.winner.announcement",
            "res_id": announcement.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_winner_announcements(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ประกาศผู้ชนะการเสนอราคา"),
            "res_model": "purchase.requisition.winner.announcement",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {"default_requisition_id": self.id},
        }
