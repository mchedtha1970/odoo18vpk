# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


PR_APPROVAL_PACKET_TYPES = (
    "wa_committee_order",
    "specific_method_approval",
)

class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    official_document_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="หนังสือราชการ",
    )
    official_document_count = fields.Integer(
        compute="_compute_official_document_count",
    )
    vpk_documents_signed_complete = fields.Boolean(
        string="ลงนามครบแล้ว",
        compute="_compute_vpk_documents_signed_complete",
    )
    issued_wa_committee_order_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="คำสั่งแต่งตั้งที่ออกแล้ว",
    )
    issued_integrity_document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="แบบแสดงความบริสุทธิ์ใจที่ออกแล้ว",
    )
    issued_spec_price_committee_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="บันทึกขออนุมัติแต่งตั้งคณะกรรมการกำหนดคุณลักษณะที่ออกแล้ว",
    )
    issued_specific_method_approval_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="รายงานขออนุมัติจัดซื้อจัดจ้างที่ออกแล้ว",
    )
    issued_purchase_approval_memo_id = fields.Many2one(
        comodel_name="vpk.official.document",
        compute="_compute_official_document_count",
        string="บันทึกข้อความอนุมัติขอซื้อที่ออกแล้ว",
    )
    purchase_approval_memo_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="เอกสารอนุมัติขอซื้อ",
        domain=[("document_type", "=", "purchase_approval_memo")],
    )
    specific_method_approval_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="รายงานขออนุมัติจัดซื้อจัดจ้าง",
        domain=[("document_type", "=", "specific_method_approval")],
    )
    wa_committee_order_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="เอกสารแต่งตั้งคณะกรรมการ",
        domain=[
            (
                "document_type",
                "in",
                ("wa_committee_order", "spec_price_committee"),
            )
        ],
    )
    integrity_over_100k_ids = fields.One2many(
        comodel_name="vpk.official.document",
        inverse_name="request_id",
        string="เอกสารแสดงความบริสุทธิ์ใจ",
        domain=[("document_type", "=", "integrity_over_100k")],
    )
    approval_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        compute="_compute_approval_attachment_ids",
        string="เอกสารอนุมัติ",
    )
    has_approval_attachments = fields.Boolean(
        compute="_compute_approval_attachment_ids",
    )
    official_document_to_create = fields.Many2one(
        comodel_name="vpk.official.document.type",
        string="เอกสารที่จะสร้าง",
        domain="[('create_from_purchase_request', '=', True)]",
    )

    @api.depends("official_document_ids", "official_document_ids.state")
    def _compute_official_document_count(self):
        Document = self.env["vpk.official.document"].sudo()
        counts = {
            row["request_id"][0]: row["request_id_count"]
            for row in Document.read_group(
                [("request_id", "in", self.ids)],
                ["request_id"],
                ["request_id"],
            )
        }
        for rec in self:
            rec.official_document_count = counts.get(rec.id, 0)
            rec.issued_wa_committee_order_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "wa_committee_order"
                    and doc.state != "cancelled"
                )
            )[:1]
            rec.issued_integrity_document_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "integrity_over_100k"
                    and doc.state != "cancelled"
                )
            )[:1]
            rec.issued_spec_price_committee_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "spec_price_committee"
                    and doc.state != "cancelled"
                )
            )[:1]
            rec.issued_specific_method_approval_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "specific_method_approval"
                    and doc.state != "cancelled"
                )
            )[:1]
            rec.issued_purchase_approval_memo_id = rec.official_document_ids.filtered(
                lambda doc: (
                    doc.document_type == "purchase_approval_memo"
                    and doc.state != "cancelled"
                )
            )[:1]

    @api.depends(
        "official_document_ids",
        "official_document_ids.state",
        "official_document_ids.pdf_attachment_id",
        "official_document_ids.pdf_file",
    )
    def _compute_approval_attachment_ids(self):
        for rec in self:
            if not isinstance(rec.id, int):
                rec.approval_attachment_ids = False
                rec.has_approval_attachments = False
                continue
            attachments = rec.env["ir.attachment"]
            for doc in rec._vpk_approval_packet_documents():
                attachments |= doc._get_pdf_attachment()
            rec.approval_attachment_ids = attachments
            rec.has_approval_attachments = bool(attachments)

    def _vpk_approval_packet_documents(self):
        self.ensure_one()
        documents = self.env["vpk.official.document"]
        for document_type in PR_APPROVAL_PACKET_TYPES:
            documents |= self.official_document_ids.filtered(
                lambda doc, dtype=document_type: (
                    doc.document_type == dtype and doc.state != "cancelled"
                )
            )[:1]
        return documents

    def _vpk_ensure_pr_approval_packet(self):
        """Create committee order + approval report PDFs before sending to the director."""
        Document = self.env["vpk.official.document"]
        packet = Document.browse()
        for rec in self:
            order = Document.create_from_purchase_request(rec)
            approval = Document.create_specific_method_approval_from_purchase_request(
                rec
            )
            for doc in order | approval:
                if not doc._get_pdf_attachment():
                    doc.with_context(skip_validation_check=True).action_generate_pdf()
                if not doc._get_pdf_attachment():
                    raise UserError(
                        _("ไม่สามารถสร้างไฟล์ PDF ของ %s ได้ กรุณากดพิมพ์ PDF ก่อนขออนุมัติ")
                        % doc.display_name
                    )
                if doc.state in ("draft", "generated"):
                    doc.with_context(skip_validation_check=True).write(
                        {"state": "to_approve"}
                    )
            packet |= order | approval
        return packet

    def _vpk_document_is_fully_approved(self, document):
        if document.state == "cancelled":
            return False
        if document.state == "approved":
            return True
        if document.review_ids:
            document.invalidate_recordset(["validation_status", "validated"])
            return document.validation_status == "validated"
        return False

    def _vpk_related_official_documents(self):
        self.ensure_one()
        return self.official_document_ids.filtered(
            lambda doc: doc.state != "cancelled"
        )

    @api.depends(
        "official_document_ids",
        "official_document_ids.state",
        "official_document_ids.validation_status",
        "official_document_ids.review_ids.status",
    )
    def _compute_can_send_to_egp(self):
        return super()._compute_can_send_to_egp()

    @api.depends(
        "official_document_ids",
        "official_document_ids.state",
        "official_document_ids.document_type",
        "official_document_ids.validation_status",
        "official_document_ids.review_ids.status",
    )
    def _compute_vpk_documents_signed_complete(self):
        for rec in self:
            rec.vpk_documents_signed_complete = rec._vpk_related_documents_all_approved()

    def _vpk_related_documents_all_approved(self):
        """True when every issued official document on this PR is fully signed."""
        self.ensure_one()
        documents = self._vpk_related_official_documents()
        if not documents:
            return False
        issued_types = set(documents.mapped("document_type"))
        if not set(PR_APPROVAL_PACKET_TYPES).issubset(issued_types):
            return False
        return all(self._vpk_document_is_fully_approved(doc) for doc in documents)

    def _vpk_packet_is_complete(self):
        self.ensure_one()
        packet = self._vpk_approval_packet_documents()
        if set(packet.mapped("document_type")) != set(PR_APPROVAL_PACKET_TYPES):
            return False
        return all(self._vpk_document_is_fully_approved(doc) for doc in packet)

    def _vpk_approve_if_packet_complete(self):
        """When both packet documents are approved, approve and confirm the PR."""
        now = fields.Datetime.now()
        for rec in self:
            if rec.state not in ("draft", "to_approve", "sent_to_procurement"):
                continue
            if not rec._vpk_packet_is_complete():
                continue
            pending = rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if pending:
                pending.write(
                    {
                        "status": "approved",
                        "done_by": self.env.user.id,
                        "reviewed_date": now,
                    }
                )
                pending._compute_can_review()
            rec.invalidate_recordset(["validation_status", "validated"])
            if hasattr(rec, "_vpk_auto_confirm_if_validated"):
                rec._vpk_auto_confirm_if_validated()
            if rec.state in ("draft", "to_approve", "sent_to_procurement"):
                # with_user() clears su; sudo() after keeps acting user for
                # approved_by while bypassing PR line record rules for signers
                # who are not the requester (e.g. director).
                # skip_check_state_condition: packet docs are the validation
                # gate — do not re-open PR tier validation on approve write.
                rec.with_user(self.env.user).sudo().with_context(
                    skip_validation_check=True,
                    skip_check_state_condition=True,
                    vpk_in_auto_confirm=True,
                ).button_approved()

    def _vpk_reset_approval_packet_reviews(self, status="rejected"):
        now = fields.Datetime.now()
        for rec in self:
            docs = rec._vpk_approval_packet_documents()
            pending = docs.mapped("review_ids").filtered(
                lambda review: review.status in ("waiting", "pending")
            )
            if status == "unlink":
                pending.unlink()
            elif pending:
                pending.write(
                    {
                        "status": status,
                        "done_by": self.env.user.id,
                        "reviewed_date": now,
                    }
                )
                pending._compute_can_review()
            docs.filtered(lambda doc: doc.state == "to_approve").with_context(
                skip_validation_check=True
            ).write({"state": "generated"})

    def request_validation(self):
        check_budget = getattr(self, "_check_budget_available_before_submit", None)
        if check_budget:
            action = check_budget()
            if isinstance(action, dict):
                return action
        packet = self._vpk_ensure_pr_approval_packet()
        created = super().request_validation()
        if isinstance(created, dict):
            return created
        packet._vpk_create_reviews_from_purchase_request(created)
        return created

    def restart_validation(self):
        self._vpk_reset_approval_packet_reviews(status="unlink")
        return super().restart_validation()

    def reject_tier(self):
        res = super().reject_tier()
        self._vpk_reset_approval_packet_reviews(status="rejected")
        return res

    def validate_tier(self):
        for rec in self:
            if rec._vpk_approval_packet_documents() and not rec._vpk_packet_is_complete():
                raise UserError(
                    _(
                        "กรุณาอนุมัติคำสั่งแต่งตั้งกรรมการ และรายงานขออนุมัติจัดซื้อจัดจ้างให้ครบก่อน "
                        "ระบบจะอนุมัติใบขอซื้อให้อัตโนมัติ"
                    )
                )
        return super().validate_tier()

    def _vpk_auto_confirm_if_validated(self):
        self.ensure_one()
        if self._vpk_approval_packet_documents() and not self._vpk_packet_is_complete():
            return
        return super()._vpk_auto_confirm_if_validated()

    def _sync_saraban_from_document(self, document):
        super()._sync_saraban_from_document(document)

    def action_view_official_documents(self):
        self.ensure_one()
        documents = self.official_document_ids
        if len(documents) == 1:
            return documents._action_open_form()
        return {
            "type": "ir.actions.act_window",
            "name": "หนังสือราชการ",
            "res_model": "vpk.official.document",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": {
                "default_request_id": self.id,
                "default_department_id": self.department_id.id,
                "default_document_type": "wa_committee_order",
            },
        }

    def action_create_wa_committee_order(self):
        self.ensure_one()
        document = self.env["vpk.official.document"].create_from_purchase_request(self)
        return document._action_open_form()

    def action_create_integrity_over_100k(self):
        self.ensure_one()
        document = self.env["vpk.official.document"].create_integrity_from_purchase_request(
            self
        )
        return document._action_open_form()

    def action_create_spec_price_committee(self):
        self.ensure_one()
        document = self.env[
            "vpk.official.document"
        ].create_spec_price_committee_from_purchase_request(self)
        return document._action_open_form()

    def action_create_specific_method_approval(self):
        self.ensure_one()
        document = self.env[
            "vpk.official.document"
        ].create_specific_method_approval_from_purchase_request(self)
        return document._action_open_form()

    def action_create_selected_official_document(self):
        self.ensure_one()
        creators = {
            "wa_committee_order": self.action_create_wa_committee_order,
            "spec_price_committee": self.action_create_spec_price_committee,
            "integrity_over_100k": self.action_create_integrity_over_100k,
            "specific_method_approval": self.action_create_specific_method_approval,
            "purchase_approval_memo": self.action_create_purchase_approval_memo,
        }
        document_type = self.official_document_to_create
        creator = creators.get(document_type.code) if document_type else None
        if not creator:
            if not document_type:
                raise UserError(_("กรุณาเลือกเอกสารที่จะสร้าง"))
            raise UserError(
                _("ยังไม่รองรับการสร้าง %(name)s จากใบขอซื้อ")
                % {"name": document_type.display_name}
            )
        return creator()

    def action_vpk_test_reset(self):
        """ทดสอบ: กลับเป็นฉบับร่าง และลบเอกสารที่เกิดจากใบขอซื้อนี้."""
        self.ensure_one()
        self._vpk_test_reset_to_draft()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("รีเซ็ตแล้ว"),
                "message": _(
                    "ใบขอซื้อกลับเป็นฉบับร่าง และลบเอกสารที่เกี่ยวข้องแล้ว"
                ),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                    "target": "current",
                },
            },
        }

    def _vpk_test_reset_to_draft(self):
        reset_ctx = {
            "skip_validation_check": True,
            "skip_check_state_condition": True,
            "skip_budget_check_reset": True,
            "skip_budget_refresh": True,
            "vpk_in_auto_confirm": True,
            "mail_notrack": True,
            "tracking_disable": True,
        }
        for request in self:
            orders = request._vpk_test_related_orders()
            requisitions = request._vpk_test_related_requisitions()
            acceptances = request._vpk_test_related_acceptances(orders)
            request._vpk_test_assert_can_reset(orders, acceptances)
            documents = request._vpk_test_related_official_documents(
                requisitions, orders, acceptances
            )
            request._vpk_test_unlink_records(documents)
            request._vpk_test_unlink_optional(
                "procurement.committee.appointment",
                [("request_id", "=", request.id)],
            )
            request._vpk_test_unlink_optional(
                "purchase.product.specification",
                [("request_id", "=", request.id)],
            )
            request._vpk_test_cancel_acceptances(acceptances)
            request._vpk_test_unlink_records(acceptances)
            request._vpk_test_cancel_orders(orders)
            request._vpk_test_unlink_records(orders)
            request._vpk_test_unlink_records(
                request.env["saraban.document"].search(
                    [("purchase_request_id", "=", request.id)]
                )
            )
            request._vpk_test_unlink_requisitions(requisitions)
            request.with_context(**reset_ctx)._vpk_test_reset_request_fields()

    def _vpk_test_related_requisitions(self):
        self.ensure_one()
        requisitions = self.env["purchase.requisition"]
        if hasattr(self, "_get_egp_requisitions"):
            requisitions |= self._get_egp_requisitions()
        if "purchase_request_id" in requisitions._fields:
            requisitions |= requisitions.search(
                [("purchase_request_id", "=", self.id)]
            )
        if "requisition_lines" in self.env["purchase.request.line"]._fields:
            requisitions |= self.line_ids.requisition_lines.requisition_id
        return requisitions.exists()

    def _vpk_test_related_orders(self):
        self.ensure_one()
        orders = self.line_ids.purchase_lines.order_id
        requisitions = self._vpk_test_related_requisitions()
        if requisitions and "requisition_id" in self.env["purchase.order"]._fields:
            orders |= self.env["purchase.order"].search(
                [("requisition_id", "in", requisitions.ids)]
            )
        return orders.exists()

    def _vpk_test_related_acceptances(self, orders):
        self.ensure_one()
        if "work.acceptance" not in self.env or not orders:
            return self.env["work.acceptance"].browse()
        return self.env["work.acceptance"].search(
            [("purchase_id", "in", orders.ids)]
        )

    def _vpk_test_related_official_documents(self, requisitions, orders, acceptances):
        self.ensure_one()
        documents = self.official_document_ids
        Document = self.env["vpk.official.document"]
        domain = [("request_id", "=", self.id)]
        extra = []
        if requisitions:
            extra.append(("requisition_id", "in", requisitions.ids))
        if orders:
            extra.append(("purchase_id", "in", orders.ids))
        if acceptances:
            extra.append(("wa_id", "in", acceptances.ids))
        if extra:
            domain = ["|"] * len(extra) + domain + extra
        documents |= Document.search(domain)
        return documents.exists()

    def _vpk_test_assert_can_reset(self, orders, acceptances):
        self.ensure_one()
        pickings = orders.picking_ids
        if acceptances and "wa_id" in self.env["stock.picking"]._fields:
            pickings |= self.env["stock.picking"].search(
                [("wa_id", "in", acceptances.ids)]
            )
        done_pickings = pickings.filtered(lambda picking: picking.state == "done")
        if done_pickings:
            raise UserError(
                _("ไม่สามารถรีเซ็ตได้ เพราะรับสินค้าแล้ว: %s")
                % ", ".join(done_pickings.mapped("name"))
            )
        posted_bills = orders.invoice_ids.filtered(
            lambda move: move.state == "posted"
        )
        if posted_bills:
            raise UserError(
                _("ไม่สามารถรีเซ็ตได้ เพราะมีใบแจ้งหนี้ที่ลงบัญชีแล้ว: %s")
                % ", ".join(posted_bills.mapped("name"))
            )

    def _vpk_test_unlink_records(self, records):
        records = records.exists()
        if not records:
            return
        reviews = self.env["tier.review"].sudo().search(
            [("model", "=", records._name), ("res_id", "in", records.ids)]
        )
        if reviews:
            reviews.with_context(skip_validation_check=True).unlink()
        if "mail.activity" in self.env:
            activities = self.env["mail.activity"].sudo().search(
                [("res_model", "=", records._name), ("res_id", "in", records.ids)]
            )
            if activities:
                activities.unlink()
        records.sudo().with_context(
            skip_validation_check=True,
            skip_check_state_condition=True,
            mail_notrack=True,
        ).unlink()

    def _vpk_test_unlink_optional(self, model_name, domain):
        if model_name not in self.env:
            return
        self._vpk_test_unlink_records(self.env[model_name].search(domain))

    def _vpk_test_cancel_acceptances(self, acceptances):
        for acceptance in acceptances.exists():
            if acceptance.state != "cancel" and hasattr(acceptance, "button_cancel"):
                acceptance.sudo().button_cancel()

    def _vpk_test_cancel_orders(self, orders):
        draft_bills = orders.invoice_ids.filtered(lambda move: move.state == "draft")
        self._vpk_test_unlink_records(draft_bills)
        pickings = orders.picking_ids.filtered(
            lambda picking: picking.state not in ("cancel", "done")
        )
        for picking in pickings:
            picking.sudo().action_cancel()
        for order in orders.exists():
            if order.state not in ("draft", "cancel"):
                order.sudo().button_cancel()

    def _vpk_test_unlink_requisitions(self, requisitions):
        requisitions = requisitions.exists()
        if not requisitions:
            return
        requisitions.sudo().with_context(
            skip_validation_check=True,
            mail_notrack=True,
        ).write({"state": "cancel"})
        self._vpk_test_unlink_records(requisitions)

    def _vpk_test_reset_request_fields(self):
        self.ensure_one()
        if "review_ids" in self._fields and self.review_ids:
            self.review_ids.sudo().with_context(
                skip_validation_check=True
            ).unlink()
        if (
            "budget_reservation_active" in self._fields
            and self.budget_reservation_active
            and hasattr(self, "_release_budget_reservation")
        ):
            self._release_budget_reservation()
        if "budget_check_line_ids" in self._fields:
            self.budget_check_line_ids.unlink()
        self.line_ids.do_uncancel()
        vals = {"state": "draft"}
        for field_name in (
            "substate_id",
            "sent_to_procurement_date",
            "procurement_owner_id",
            "procurement_claimed_date",
            "procurement_verified",
            "procurement_verified_by",
            "procurement_verified_date",
            "procurement_return_reason",
            "procurement_returned_by",
            "procurement_returned_date",
            "approved_by",
            "date_approved",
            "verified_by",
            "date_verified",
            "budget_check_message",
        ):
            if field_name in self._fields:
                vals[field_name] = False
        if "budget_check_state" in self._fields:
            vals["budget_check_state"] = "unchecked"
        if "budget_available_amount" in self._fields:
            vals["budget_available_amount"] = 0.0
        self.with_context(
            skip_validation_check=True,
            skip_check_state_condition=True,
            skip_budget_check_reset=True,
            skip_budget_refresh=True,
            vpk_in_auto_confirm=True,
        ).write(vals)
        self.message_post(
            body=_("รีเซ็ตสำหรับทดสอบ: กลับเป็นฉบับร่าง และลบเอกสารที่เกี่ยวข้อง")
        )

    def action_open_add_official_document_wizard(self):
        self.ensure_one()
        default_type = self.env["vpk.official.document.type"].search(
            [
                ("create_from_purchase_request", "=", True),
                ("code", "=", "purchase_approval_memo"),
            ],
            limit=1,
        )
        if not default_type:
            default_type = self.env["vpk.official.document.type"].search(
                [("create_from_purchase_request", "=", True)],
                limit=1,
            )
        wizard = self.env["vpk.official.document.add.wizard"].create(
            {
                "request_id": self.id,
                "document_type_id": default_type.id,
                "add_mode": "studio",
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("เพิ่มเอกสาร"),
            "res_model": "vpk.official.document.add.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_create_purchase_approval_memo(self):
        self.ensure_one()
        document = self.env[
            "vpk.official.document"
        ].create_purchase_approval_memo_from_purchase_request(self)
        return document._action_open_form()
