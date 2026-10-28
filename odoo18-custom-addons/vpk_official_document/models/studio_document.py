import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ",
        index=True,
        ondelete="set null",
        copy=False,
    )
    official_document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        string="หนังสือราชการ",
        index=True,
        ondelete="set null",
        copy=False,
    )
    signer_line_ids = fields.One2many(
        related="official_document_id.signer_line_ids",
        string="ผู้อนุมัติ",
        readonly=False,
    )
    official_state = fields.Selection(
        related="official_document_id.state",
        string="สถานะหนังสือราชการ",
    )

    @api.depends("state", "official_document_id.signature_state")
    def _compute_signature_state(self):
        linked = self.filtered("official_document_id")
        for rec in linked:
            rec.signature_state = rec.official_document_id.signature_state or "not_sent"
        return super(DocumentStudioDocument, self - linked)._compute_signature_state()

    def _vpk_signing_enabled(self):
        self.ensure_one()
        return not self.official_document_id and super()._vpk_signing_enabled()

    def action_open_purchase_request(self):
        self.ensure_one()
        if not self.request_id:
            raise UserError(_("เอกสารนี้ไม่ได้ผูกกับใบขอซื้อ"))
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบขอซื้อ"),
            "res_model": "purchase.request",
            "res_id": self.request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_generate_docx(self):
        result = super().action_generate_docx()
        self._sync_files_to_official_document()
        return result

    def action_generate_pdf(self):
        result = super().action_generate_pdf()
        self._sync_files_to_official_document()
        return result

    def action_open_send_wizard(self):
        self.ensure_one()
        if not self.official_document_id:
            raise UserError(_("เอกสารนี้ยังไม่ได้ผูกกับหนังสือราชการ จึงส่งลงนามไม่ได้"))
        self._sync_files_to_official_document()
        return self.official_document_id.action_open_send_wizard()

    def _sync_files_to_official_document(self):
        for rec in self:
            official = rec.official_document_id
            if not official:
                continue
            if rec.docx_file:
                official._store_generated_file(
                    base64.b64decode(rec.docx_file),
                    rec.docx_filename or "document.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "docx",
                )
            if rec.pdf_file:
                official._store_generated_file(
                    base64.b64decode(rec.pdf_file),
                    rec.pdf_filename or "document.pdf",
                    "application/pdf",
                    "pdf",
                )
                egp_documents = self.env["purchase.requisition.egp.document"].search(
                    [
                        ("official_document_id", "=", official.id),
                        ("signature_state", "not in", ("waiting", "signed")),
                    ]
                )
                if egp_documents:
                    egp_documents.write(
                        {
                            "document_file": rec.pdf_file,
                            "document_filename": rec.pdf_filename or "document.pdf",
                        }
                    )

    @api.model
    def _values_from_record(self, template, record):
        if record and record._name == "purchase.request":
            values = self._values_from_purchase_request(template, record)
            generic = super()._values_from_record(template, record)
            # Heuristic PR values win; generic mapping fills any other field.
            for key, value in generic.items():
                if values.get(key) in (None, False, ""):
                    values[key] = value
            return values
        return super()._values_from_record(template, record)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            ref = vals.get("source_ref")
            if ref and not vals.get("request_id") and str(ref).startswith("purchase.request,"):
                rec_id = str(ref).split(",", 1)[1]
                if rec_id.isdigit():
                    vals["request_id"] = int(rec_id)
        return super().create(vals_list)

    @api.model
    def _values_from_purchase_request(self, template, request):
        values = template._default_values() if template else {}
        if not template or not request:
            return values
        Official = self.env["vpk.official.document"]
        item = Official._item_summary_from_request(request)
        method = Official._method_from_request(request)
        department = (
            request.department_id.name
            if request.department_id
            else request.company_id.name
        )
        proposer_name, proposer_position = Official._person_from_user(
            request.requested_by
        )
        amount = request.estimated_cost if "estimated_cost" in request._fields else 0.0
        date_value = fields.Date.to_string(
            request.date_start or fields.Date.context_today(request)
        )
        mapping = {
            "agency": request.company_id.name,
            "subject": _("ขออนุมัติจัดซื้อ%s") % item,
            "recipient": (
                request.memo_to
                if "memo_to" in request._fields and request.memo_to
                else ""
            ),
            "intro": request.description or "",
            "detail": request.description or "",
            "item_summary": item,
            "item_1": item,
            "department_name": department,
            "procurement_method": method,
            "memo_date": date_value,
            "doc_date": date_value,
            "proposer_name": proposer_name,
            "proposer_position": proposer_position,
            "amount_total": amount,
        }
        known = set(template.field_ids.mapped("code"))
        lines = request.line_ids.filtered(
            lambda line: not getattr(line, "cancelled", False)
        )
        for index, line in enumerate(lines[:10], start=1):
            code = "item_%s" % index
            if code in known:
                mapping[code] = self.env["vpk.document.studio.field"]._clean_product_line_name(line)
        StudioField = self.env["vpk.document.studio.field"]
        for field in template.field_ids:
            # 1. Explicit Model + Field mapping configured on the template field
            if field.map_field_id and (
                not field.map_model_id or field.map_model_id.model == request._name
            ):
                extracted = field.extract_mapped_record_value(request)
                if extracted not in (None, False, ""):
                    if field.field_type == "many2one":
                        dept = request.department_id.name if request.department_id else ""
                        label = "%s%s (%s รายการ)" % (
                            request.name or ("PR#%s" % request.id),
                            (" - %s" % dept) if dept else "",
                            len(lines),
                        )
                        values[field.code] = {
                            "res_id": request.id,
                            "label": label,
                            "text": str(extracted),
                        }
                    else:
                        values[field.code] = extracted
                    continue

            if field.field_type == "many2one" or field.code in (
                "items",
                "pr_lines",
                "pr_items",
                "product_lines",
            ):
                mode = field.relation_source or "pr_lines_name_only"
                lines_text = StudioField._format_pr_lines_text(request, mode=mode)
                dept = request.department_id.name if request.department_id else ""
                label = "%s%s (%s รายการ)" % (
                    request.name or ("PR#%s" % request.id),
                    (" - %s" % dept) if dept else "",
                    len(lines),
                )
                if field.field_type == "many2one":
                    values[field.code] = {
                        "res_id": request.id,
                        "label": label,
                        "text": lines_text,
                    }
                else:
                    values[field.code] = lines_text
        for code, value in mapping.items():
            if code in known and value not in (None, False, "") and not values.get(code):
                values[code] = value
        return values
