# -*- coding: utf-8 -*-
from datetime import timedelta
from pathlib import Path

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")
PO_FORM_REPORT = "vpk_purchase_order_form.report_purchase_order_vpk_form"
MIN_LINE_ROWS = 8


def _load_po_form_inline_css():
    module_static = Path(__file__).resolve().parent.parent / "static/src"
    layout_css = (module_static / "css/po_form_layout.css").read_text(encoding="utf-8")
    # Reuse embedded Thai fonts from vpk_tier_validation when available.
    fonts_css = ""
    tier_fonts = (
        Path(__file__).resolve().parents[2]
        / "vpk_tier_validation/static/src/scss/thai_fonts_embedded.scss"
    )
    if tier_fonts.exists():
        fonts_css = tier_fonts.read_text(encoding="utf-8")
    return f"{fonts_css}\n{layout_css}"


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    vpk_po_delivery_days = fields.Integer(
        string="กำหนดส่งมอบ (วัน)",
        help="จำนวนวันส่งมอบนับถัดจากวันที่ผู้รับจ้างได้รับใบสั่งซื้อ",
    )
    vpk_po_delivery_deadline = fields.Date(
        string="ครบกำหนดส่งมอบ",
    )
    vpk_po_warranty_months = fields.Integer(
        string="ระยะเวลารับประกัน (เดือน)",
    )
    vpk_po_delivery_place = fields.Text(
        string="สถานที่ส่งมอบ",
    )
    vpk_po_file_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="purchase_order_vpk_po_file_rel",
        column1="order_id",
        column2="attachment_id",
        string="ไฟล์ใบสั่งซื้อ",
        copy=False,
    )
    has_pdf = fields.Boolean(
        string="มีไฟล์ PDF",
        compute="_compute_vpk_po_pdf_meta",
        store=True,
    )
    pdf_filename = fields.Char(
        string="ชื่อไฟล์ PDF",
        compute="_compute_vpk_po_pdf_meta",
        store=True,
    )
    pdf_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="ไฟล์ PDF",
        compute="_compute_vpk_po_pdf_meta",
        store=True,
    )
    vpk_po_type_label = fields.Char(
        string="ประเภท",
        compute="_compute_vpk_po_type_label",
    )
    vpk_po_sent_on = fields.Datetime(
        string="ส่งให้ผู้ขายเมื่อ",
        copy=False,
        readonly=True,
    )
    vpk_vendor_confirm_state = fields.Selection(
        selection=[
            ("not_sent", "ยังไม่ส่ง"),
            ("waiting", "รอผู้ขายยืนยัน"),
            ("confirmed", "ผู้ขายยืนยันแล้ว"),
        ],
        string="สถานะการยืนยัน",
        compute="_compute_vpk_vendor_confirm_state",
        store=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        if "vpk_po_delivery_days" in fields_list and not res.get("vpk_po_delivery_days"):
            res["vpk_po_delivery_days"] = company.vpk_po_delivery_days or 90
        if "vpk_po_warranty_months" in fields_list and not res.get(
            "vpk_po_warranty_months"
        ):
            res["vpk_po_warranty_months"] = company.vpk_po_warranty_months or 3
        if "vpk_po_delivery_place" in fields_list and not res.get(
            "vpk_po_delivery_place"
        ):
            res["vpk_po_delivery_place"] = company.vpk_po_delivery_place
        return res

    @api.onchange("date_order", "vpk_po_delivery_days")
    def _onchange_vpk_po_delivery_deadline(self):
        for order in self:
            if order.date_order and order.vpk_po_delivery_days:
                base = fields.Datetime.to_datetime(order.date_order).date()
                order.vpk_po_delivery_deadline = base + timedelta(
                    days=order.vpk_po_delivery_days
                )

    def _vpk_po_pdf_filename(self):
        self.ensure_one()
        return "ใบสั่งซื้อ-%s.pdf" % (self.name or self.id)

    def _vpk_po_form_report(self):
        return self.env.ref(
            "vpk_purchase_order_form.action_report_purchase_order_vpk_form"
        )

    def _vpk_po_pdf_attachment(self):
        self.ensure_one()
        found = self._vpk_po_form_report().retrieve_attachment(self)
        if found:
            return found
        linked = self.vpk_po_file_ids.filtered(
            lambda attachment: attachment.name == self._vpk_po_pdf_filename()
        )[:1]
        return linked or self.env["ir.attachment"]

    def _vpk_upsert_po_pdf(self, content):
        """เก็บไฟล์ PDF ที่พิมพ์ไว้บนใบสั่งซื้อ แทนที่ไฟล์เดิมถ้าพิมพ์ซ้ำ."""
        self.ensure_one()
        filename = self._vpk_po_pdf_filename()
        attachment = self._vpk_po_pdf_attachment()
        if attachment:
            attachment.write(
                {
                    "name": filename,
                    "raw": content,
                    "mimetype": "application/pdf",
                }
            )
        else:
            attachment = self.env["ir.attachment"].create(
                {
                    "name": filename,
                    "raw": content,
                    "mimetype": "application/pdf",
                    "res_model": self._name,
                    "res_id": self.id,
                    "type": "binary",
                }
            )
            self.message_post(
                body=_("บันทึกไฟล์ %s") % filename,
                attachment_ids=[attachment.id],
                subtype_xmlid="mail.mt_note",
            )
        self.vpk_po_file_ids = attachment
        return attachment

    def _vpk_ensure_po_pdf_attachment(self):
        self.ensure_one()
        attachment = self._vpk_po_pdf_attachment()
        if attachment:
            return attachment
        report = self._vpk_po_form_report()
        self.env["ir.actions.report"]._render_qweb_pdf(report.report_name, self.ids)
        attachment = self._vpk_po_pdf_attachment()
        if not attachment:
            raise UserError(_("ยังบันทึกไฟล์ใบสั่งซื้อไม่ได้ กรุณากดพิมพ์ใบสั่งซื้อก่อน"))
        return attachment

    def _compute_vpk_po_type_label(self):
        for order in self:
            order.vpk_po_type_label = _("ใบสั่งซื้อ")

    @api.depends("vpk_po_file_ids", "vpk_po_file_ids.name")
    def _compute_vpk_po_pdf_meta(self):
        for order in self:
            attachment = order._vpk_po_pdf_attachment() if isinstance(order.id, int) else False
            order.pdf_attachment_id = attachment.id if attachment else False
            order.pdf_filename = attachment.name if attachment else False
            order.has_pdf = bool(attachment)

    @api.depends("vpk_po_sent_on", "state")
    def _compute_vpk_vendor_confirm_state(self):
        for order in self:
            signed = "vendor_signed" in order._fields and bool(order.vendor_signed)
            if signed:
                order.vpk_vendor_confirm_state = "confirmed"
            elif order.vpk_po_sent_on:
                order.vpk_vendor_confirm_state = "waiting"
            else:
                order.vpk_vendor_confirm_state = "not_sent"

    def action_save_vpk_po_pdf(self):
        """พิมพ์แล้วเก็บไฟล์ไว้บนใบสั่งซื้อ โดยไม่เปิดดาวน์โหลด."""
        self.ensure_one()
        report = self._vpk_po_form_report()
        self.env["ir.actions.report"]._render_qweb_pdf(report.report_name, self.ids)
        return True

    def action_open_pdf_viewer(self):
        self.ensure_one()
        attachment = self._vpk_po_pdf_attachment()
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        return {
            "type": "ir.actions.client",
            "tag": "vpk_official_document_sign_pdf_viewer",
            "name": self.display_name,
            "params": {
                "attachment_id": attachment.id,
                "res_model": self._name,
                "res_id": self.id,
                "title": self.pdf_filename or attachment.name,
                "can_sign": False,
            },
        }

    def action_print_vpk_po_form(self):
        self.ensure_one()
        return self._vpk_po_form_report().report_action(self)

    def _vpk_vendor_app_user(self):
        """Portal user of the winner, the account that signs in the vendor app."""
        self.ensure_one()
        commercial = self.partner_id.commercial_partner_id
        partners = commercial | commercial.child_ids
        return partners.user_ids.filtered(
            lambda user: user.active and user._is_portal()
        )[:1]

    def action_send_vpk_po_to_winner(self):
        """ส่งไฟล์ใบสั่งซื้อเข้าแอปผู้ขาย เพื่อให้ผู้ชนะลงนามยืนยันกลับมา."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("กรุณาระบุผู้ชนะก่อนส่งใบสั่งซื้อ"))
        if self.vpk_vendor_confirm_state == "confirmed":
            raise UserError(_("ผู้ขายยืนยันใบสั่งซื้อนี้แล้ว"))
        if self.vpk_vendor_confirm_state == "waiting":
            raise UserError(_("ใบสั่งซื้อนี้อยู่ในแอปผู้ขายแล้ว รอผู้ขายลงนาม"))
        portal_user = self._vpk_vendor_app_user()
        if not portal_user:
            raise UserError(
                _(
                    "ผู้ขาย %(vendor)s ยังไม่มีบัญชีแอปผู้ขาย "
                    "กรุณาสร้าง User Portal ก่อนส่ง",
                    vendor=self.partner_id.display_name,
                )
            )
        self._vpk_ensure_po_pdf_attachment()
        if self.state == "draft":
            self.write({"state": "sent"})
        self.write({"vpk_po_sent_on": fields.Datetime.now()})
        self.message_post(
            body=_(
                "ส่งใบสั่งซื้อเข้าแอปผู้ขายของ %(vendor)s (บัญชี %(login)s) "
                "เพื่อลงนามยืนยัน สถานะจะกลับมาเป็นผู้ขายยืนยันแล้วเมื่อผู้ขายบันทึกลายเซ็น",
                vendor=self.partner_id.display_name,
                login=portal_user.login,
            )
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ส่งเข้าแอปผู้ขายแล้ว"),
                "message": _(
                    "ใบสั่งซื้อ %(po)s อยู่ในรายการรอยืนยันของ %(vendor)s",
                    po=self.name or "",
                    vendor=self.partner_id.display_name,
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    @api.model
    def _get_po_form_inline_css(self):
        return Markup(_load_po_form_inline_css())

    def _thai_digits(self, value):
        if value is None:
            return ""
        return str(value).translate(THAI_DIGITS)

    def _po_form_format_amount(self, amount):
        return self._thai_digits("{:,.2f}".format(amount or 0.0))

    def _po_form_format_qty(self, qty):
        qty = qty or 0.0
        if abs(qty - round(qty)) < 1e-9:
            return self._thai_digits(int(round(qty)))
        formatted = "{:.4f}".format(qty).rstrip("0").rstrip(".")
        return self._thai_digits(formatted)

    def _po_form_baht_text(self, amount=None):
        self.ensure_one()
        if amount is None:
            amount = self.amount_total or 0.0
        currency = self.currency_id or self.company_id.currency_id
        try:
            text = currency.with_context(lang="th_TH").amount_to_text(amount)
        except Exception:
            text = currency.amount_to_text(amount)
        text = (text or "").strip()
        if text and "บาท" not in text:
            text = f"{text}บาทถ้วน"
        return text

    def _po_form_date_thai(self, date_value=None, short=True):
        self.ensure_one()
        if date_value is None:
            if self.date_order:
                date_value = fields.Datetime.to_datetime(self.date_order).date()
            else:
                return ""
        if not date_value:
            return ""
        month_format = "short" if short else "full"
        formatted = self.env["thai.utils"].format_thai_date(
            date_value, month_format=month_format
        )
        return self._thai_digits(formatted)

    def _po_form_partner_address_lines(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return []
        lines = []
        street = " ".join(
            part for part in [partner.street or "", partner.street2 or ""] if part
        ).strip()
        if street:
            lines.append(self._thai_digits(street))
        city_line = " ".join(
            part
            for part in [
                partner.city or "",
                partner.state_id.name if partner.state_id else "",
                partner.zip or "",
            ]
            if part
        ).strip()
        if city_line:
            lines.append(self._thai_digits(city_line))
        return lines

    def _po_form_partner_vat(self):
        self.ensure_one()
        vat = (self.partner_id.vat or "").strip()
        if not vat:
            return ""
        digits = "".join(ch for ch in vat if ch.isdigit())
        if len(digits) == 13:
            spaced = (
                f"{digits[0]} {digits[1:5]} {digits[5:10]} {digits[10:12]} {digits[12]}"
            )
            return self._thai_digits(spaced)
        return self._thai_digits(vat)

    def _po_form_partner_phone(self):
        self.ensure_one()
        phone = self.partner_id.phone or self.partner_id.mobile or ""
        return self._thai_digits(phone)

    def _po_form_agency_name(self):
        self.ensure_one()
        company = self.company_id
        return (
            company.vpk_po_agency_name
            or (
                company.vpk_memo_agency
                if "vpk_memo_agency" in company._fields
                else False
            )
            or company.name
            or "จังหวัดภูเก็ต"
        )

    def _po_form_agency_address_lines(self):
        self.ensure_one()
        company = self.company_id
        raw = company.vpk_po_agency_address or ""
        if not raw.strip():
            bits = [
                company.street or "",
                company.street2 or "",
                company.city or "",
                company.state_id.name if company.state_id else "",
                company.zip or "",
            ]
            raw = " ".join(b for b in bits if b)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not lines and raw:
            lines = [raw.strip()]
        return [self._thai_digits(ln) for ln in lines]

    def _po_form_delivery_days(self):
        self.ensure_one()
        return self.vpk_po_delivery_days or self.company_id.vpk_po_delivery_days or 90

    def _po_form_warranty_months(self):
        self.ensure_one()
        return (
            self.vpk_po_warranty_months
            or self.company_id.vpk_po_warranty_months
            or 3
        )

    def _po_form_delivery_place(self):
        self.ensure_one()
        place = self.vpk_po_delivery_place or self.company_id.vpk_po_delivery_place or ""
        return self._thai_digits(place)

    def _po_form_delivery_deadline_display(self):
        self.ensure_one()
        if self.vpk_po_delivery_deadline:
            return self._po_form_date_thai(self.vpk_po_delivery_deadline, short=True)
        return "____________________"

    def _po_form_penalty_rate_display(self):
        self.ensure_one()
        rate = self.company_id.vpk_po_penalty_rate or 0.20
        return self._thai_digits("{:.2f}".format(rate))

    def _po_form_penalty_min_display(self):
        self.ensure_one()
        amount = self.company_id.vpk_po_penalty_min or 100.0
        if abs(amount - round(amount)) < 1e-9:
            return self._thai_digits(int(round(amount)))
        return self._po_form_format_amount(amount)

    def _po_form_lines(self):
        """Active PO lines for printing (skip section/display-only if any)."""
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda line: not line.display_type and line.product_qty
        )
        return lines

    def _po_form_line_rows(self):
        """Rows for table including empty padding rows."""
        self.ensure_one()
        rows = []
        for idx, line in enumerate(self._po_form_lines(), start=1):
            rows.append(
                {
                    "no": self._thai_digits(idx),
                    "name": line.name or (line.product_id.display_name if line.product_id else ""),
                    "qty": self._po_form_format_qty(line.product_qty),
                    "uom": line.product_uom.name if line.product_uom else "",
                    "price_unit": self._po_form_format_amount(line.price_unit),
                    # ตามแบบ: ยอดบรรทัดรวมภาษีให้ตรงยอดรวมทั้งสิ้น
                    "amount": self._po_form_format_amount(line.price_total),
                }
            )
        while len(rows) < MIN_LINE_ROWS:
            rows.append(
                {
                    "no": "",
                    "name": "",
                    "qty": "",
                    "uom": "",
                    "price_unit": "",
                    "amount": "",
                }
            )
        return rows

    def _po_form_signer_name(self):
        self.ensure_one()
        return self.company_id.vpk_po_signer_name or ""

    def _po_form_signer_position(self):
        self.ensure_one()
        return self.company_id.vpk_po_signer_position or ""
