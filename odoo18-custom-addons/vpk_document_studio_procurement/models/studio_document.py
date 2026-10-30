from odoo import _, api, fields, models
from odoo.exceptions import UserError

PR_APPROVAL_PACKET_TYPES = ("wa_committee_order", "specific_method_approval")
LINK_FIELDS = {
    "purchase.request": "request_id",
    "work.acceptance": "wa_id",
    "purchase.order": "purchase_id",
    "purchase.requisition": "requisition_id",
}


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ",
        index=True,
        ondelete="set null",
        copy=False,
    )
    wa_id = fields.Many2one(
        comodel_name="work.acceptance",
        string="ใบตรวจรับ",
        index=True,
        ondelete="set null",
        copy=False,
    )
    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="ใบสั่งซื้อ",
        index=True,
        ondelete="set null",
        copy=False,
    )
    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="เอกสาร e-GP",
        index=True,
        ondelete="set null",
        copy=False,
    )
    document_type_code = fields.Char(
        related="document_type_id.code",
        string="รหัสประเภทเอกสาร",
        store=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Links and values
    # ------------------------------------------------------------------
    @api.model
    def _extra_source_models(self):
        return super()._extra_source_models() + list(LINK_FIELDS)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            ref = vals.get("source_ref")
            if not ref:
                continue
            model, _sep, rec_id = str(ref).partition(",")
            field_name = LINK_FIELDS.get(model)
            if field_name and rec_id.isdigit() and not vals.get(field_name):
                vals[field_name] = int(rec_id)
        records = super().create(vals_list)
        for rec in records:
            rec._vpk_fill_links_from_sources()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "pdf_file" in vals and not self.env.context.get("vpk_egp_file_sync"):
            self._sync_pdf_to_egp_documents()
        return res

    def _sync_pdf_to_egp_documents(self):
        """Show the studio PDF (generated or signed) as the file of the linked e-GP documents."""
        EgpDocument = self.env["purchase.requisition.egp.document"].sudo()
        for rec in self:
            egp_documents = EgpDocument.search([("studio_document_id", "=", rec.id)])
            if not egp_documents or not rec.pdf_file:
                continue
            egp_documents.with_context(vpk_egp_file_sync=True).write(
                {
                    "document_file": rec.pdf_file,
                    "document_filename": rec.pdf_filename or "%s.pdf" % rec.name,
                }
            )

    def _vpk_fill_links_from_sources(self):
        Values = self.env["vpk.procurement.document.values"]
        for rec in self:
            vals = {}
            if rec.wa_id:
                if not rec.purchase_id and rec.wa_id.purchase_id:
                    vals["purchase_id"] = rec.wa_id.purchase_id.id
                if not rec.request_id:
                    request = Values.request_from_acceptance(rec.wa_id)
                    if request:
                        vals["request_id"] = request.id
            elif rec.purchase_id and not rec.request_id:
                request = Values.request_from_order(rec.purchase_id)
                if request:
                    vals["request_id"] = request.id
            if vals:
                rec.with_context(skip_validation_check=True).write(vals)

    @api.model
    def _values_from_record(self, template, record):
        values = super()._values_from_record(template, record)
        if not template or not record:
            return values
        type_code = template.document_type_id.code
        Values = self.env["vpk.procurement.document.values"]
        provided = Values.values_for(record, type_code)
        people = Values.people_from_approver_lines(template.default_approver_ids)
        for key, value in people.items():
            if value:
                provided[key] = value
        if people:
            committee = Values.committee_rows(
                request=record if record._name == "purchase.request" else None,
                acceptance=record if record._name == "work.acceptance" else None,
            )
            provided.update(Values.integrity_values(provided, committee))
        if record._name == "purchase.request":
            StudioField = self.env["vpk.document.studio.field"]
            lines = record.line_ids.filtered(
                lambda line: not getattr(line, "cancelled", False)
            )
            for index, line in enumerate(lines[:10], start=1):
                provided.setdefault(
                    "item_%s" % index, StudioField._clean_product_line_name(line)
                )
            for field in template.field_ids.filtered(lambda f: f.field_type == "many2one"):
                if values.get(field.code):
                    continue
                values[field.code] = {
                    "res_id": record.id,
                    "label": record.display_name,
                    "text": StudioField._format_pr_lines_text(
                        record, mode=field.relation_source or "pr_lines_name_only"
                    ),
                }
        for field in template.field_ids:
            value = provided.get(field.code)
            if value in (None, False, ""):
                continue
            if values.get(field.code) in (None, False, "") or field.default_value == values.get(
                field.code
            ):
                values[field.code] = value
        return values

    def _vpk_source_record(self):
        self.ensure_one()
        for field_name in ("wa_id", "purchase_id", "request_id"):
            if self[field_name]:
                return self[field_name]
        return self._record_from_ref(self.source_ref)

    def action_reload_values_from_source(self):
        for rec in self:
            if rec.state not in ("draft", "generated"):
                raise UserError(_("เอกสารส่งลงนามแล้ว ไม่สามารถดึงข้อมูลใหม่ได้"))
            record = rec._vpk_source_record()
            if not rec.template_id or not record:
                continue
            rec.value_json = rec._values_from_record(rec.template_id, record.sudo())
            rec.body = rec._filled_body_html(convert_word=True)
        return True

    # ------------------------------------------------------------------
    # Default approvers
    # ------------------------------------------------------------------
    def _vpk_default_approver_vals(self):
        """Sequential approver dicts: template first, else committee of this request."""
        self.ensure_one()
        if self.template_id:
            rows = self.template_id._vpk_approver_row_vals()
            if rows:
                return rows
        Values = self.env["vpk.procurement.document.values"]
        code = self.document_type_code
        if code not in ("inspection_report", "integrity_over_100k"):
            return []
        rows = []
        seen = set()
        for member in Values.committee_rows(request=self.request_id, acceptance=self.wa_id):
            user = member.get("user")
            if not user or user.id in seen:
                continue
            seen.add(user.id)
            rows.append(
                {
                    "sequence": len(rows) + 1,
                    "user_id": user.id,
                    "position": member.get("position") or "",
                    "is_check": False,
                    "is_sign": True,
                }
            )
        return rows

    def _vpk_seed_default_approvers(self, replace=False, rows=None):
        Line = self.env["vpk.approval.line"].sudo()
        for rec in self:
            if rec.vpk_approver_line_ids and not replace:
                continue
            source = rows if rows is not None else rec._vpk_default_approver_vals()
            rec.vpk_approver_line_ids.sudo().unlink()
            seen = set()
            vals_list = []
            for item in source:
                if isinstance(item, dict):
                    user = self.env["res.users"].browse(item.get("user_id"))
                    position = item.get("position") or ""
                    is_check = bool(item.get("is_check"))
                    is_sign = bool(item.get("is_sign")) and not is_check
                    if not is_check and not is_sign:
                        is_sign = True
                else:
                    user, position, is_check = item
                    is_sign = not is_check
                if not user or user.id in seen:
                    continue
                seen.add(user.id)
                vals_list.append(
                    {
                        "res_model": rec._name,
                        "res_id": rec.id,
                        "sequence": len(vals_list) + 1,
                        "user_id": user.id,
                        "position": position or "",
                        "is_check": is_check,
                        "is_sign": is_sign,
                    }
                )
            if vals_list:
                Line.create(vals_list)
        return True

    def action_reset_default_approvers(self):
        for rec in self:
            if rec.state not in ("draft", "generated"):
                raise UserError(_("เอกสารส่งลงนามแล้ว ไม่สามารถเปลี่ยนผู้อนุมัติได้"))
        self._vpk_seed_default_approvers(replace=True)
        return True

    def action_send_for_signature(self):
        self.filtered(lambda doc: not doc.vpk_approver_line_ids)._vpk_seed_default_approvers()
        return super().action_send_for_signature()

    # ------------------------------------------------------------------
    # Purchase request approval packet
    # ------------------------------------------------------------------
    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers)
        requests = self.filtered(
            lambda doc: doc.state == "approved"
            and doc.document_type_code in PR_APPROVAL_PACKET_TYPES
        ).sudo().mapped("request_id")
        if requests:
            requests._vpk_approve_if_packet_complete()
        return res

    def _rejected_tier(self, tiers=False):
        res = super()._rejected_tier(tiers)
        if self.env.context.get("vpk_skip_pr_reject_from_packet"):
            return res
        for rec in self.filtered(
            lambda doc: doc.document_type_code in PR_APPROVAL_PACKET_TYPES
        ):
            request = rec.sudo().request_id
            if request and request.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                request.with_context(vpk_skip_pr_reject_from_packet=True).sudo()._vpk_reject_from_packet()
        return res

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _action_open_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.document_type_id.name or _("เอกสาร"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_form(self):
        return self._action_open_form()

    def _vpk_review_card_context(self):
        self.ensure_one()
        source = self.request_id or self.requisition_id or self.wa_id or self.purchase_id
        return source.display_name if source else super()._vpk_review_card_context()

    def action_delete_from_source(self):
        for rec in self:
            if rec.state in ("to_approve", "approved"):
                raise UserError(_("ไม่สามารถลบเอกสารที่ส่งลงนามหรืออนุมัติแล้ว"))
        self.sudo().unlink()
        return True

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

    @api.model
    def _vpk_create_for_record(
        self, record, document_type, template=False, extra=None, approver_rows=None
    ):
        """Create a studio document of `document_type` from `record`."""
        if not template:
            template = self.env["vpk.document.studio.template"]._vpk_template_for_type(
                document_type, record.company_id
            )
        if not template:
            raise UserError(
                _(
                    'ยังไม่มีแบบฟอร์ม Document Studio สำหรับประเภทเอกสาร "%s" '
                    "กรุณาสร้างแบบฟอร์มและเลือกประเภทเอกสารนี้ก่อน"
                )
                % document_type.display_name
            )
        vals = {
            "template_id": template.id,
            "document_type_id": document_type.id,
            "source_ref": "%s,%d" % (record._name, record.id),
            "company_id": record.company_id.id,
        }
        vals.update(extra or {})
        document = self.create(vals)
        kwargs = {}
        if approver_rows is not None:
            kwargs = {"replace": True, "rows": approver_rows}
        document._vpk_seed_default_approvers(**kwargs)
        return document

    @api.model
    def _vpk_find_for_record(self, record, type_code):
        field_name = LINK_FIELDS.get(record._name)
        if not field_name:
            return self.browse()
        return self.search(
            [
                (field_name, "=", record.id),
                ("document_type_code", "=", type_code),
                ("state", "!=", "cancelled"),
            ],
            order="id desc",
            limit=1,
        )


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    @api.model
    def _vpk_template_for_type(self, document_type, company=None):
        company = company or self.env.company
        return self.search(
            [
                ("document_type_id", "=", document_type.id),
                ("active", "=", True),
                ("company_id", "in", [False, company.id]),
            ],
            order="company_id desc, id desc",
            limit=1,
        )
