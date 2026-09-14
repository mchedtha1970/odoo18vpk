# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TierReview(models.Model):
    _inherit = "tier.review"

    res_display_name = fields.Char(
        string="Document",
        compute="_compute_res_display_name",
        store=False,
    )
    model_display_name = fields.Char(
        string="Document Type",
        compute="_compute_model_display_name",
        store=False,
    )

    @api.depends("model", "res_id")
    def _compute_res_display_name(self):
        for rec in self:
            name = ""
            if rec.model and rec.res_id:
                try:
                    doc = self.env[rec.model].browse(rec.res_id)
                    if doc.exists():
                        if rec.model == "vpk.official.document":
                            type_labels = dict(
                                doc._fields["document_type"]._description_selection(
                                    doc.env
                                )
                            )
                            name = type_labels.get(
                                doc.document_type, doc.display_name
                            )
                            if doc.request_id:
                                name = "{} · {}".format(
                                    doc.request_id.display_name, name
                                )
                        else:
                            name = doc.display_name
                except Exception:
                    name = ""
            rec.res_display_name = name

    @api.depends("model", "res_id")
    def _compute_model_display_name(self):
        for rec in self:
            label = ""
            if rec.model == "vpk.official.document" and rec.res_id:
                try:
                    doc = self.env[rec.model].browse(rec.res_id)
                    if doc.exists():
                        type_labels = dict(
                            doc._fields["document_type"]._description_selection(
                                doc.env
                            )
                        )
                        label = type_labels.get(doc.document_type, doc._description)
                except Exception:
                    label = ""
            if not label and rec.model and rec.model in self.env:
                try:
                    label = self.env[rec.model]._description
                except Exception:
                    label = rec.model
            elif not label and rec.model:
                label = rec.model
            rec.model_display_name = label

    def action_open_resource(self):
        self.ensure_one()
        context = {}
        if self.model == "vpk.official.document":
            context["vpk_auto_open_sign_viewer"] = True
        return {
            "type": "ir.actions.act_window",
            "name": self.res_display_name or self.name,
            "res_model": self.model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
            "context": context,
        }

    def action_open_pdf_viewer(self):
        """Open the official-document PDF in the sign viewer without the form."""
        self.ensure_one()
        if self.model != "vpk.official.document" or not self.res_id:
            return self.action_open_resource()
        if "vpk.official.document" not in self.env:
            return self.action_open_resource()
        document = self.env["vpk.official.document"].browse(self.res_id).exists()
        if not document:
            return self.action_open_resource()
        attachment = False
        if hasattr(document, "_get_pdf_attachment"):
            attachment = document._get_pdf_attachment()
        if not attachment:
            raise UserError(_("ยังไม่มีไฟล์ PDF กรุณากดพิมพ์ PDF ก่อน"))
        title = self.res_display_name or document.display_name
        return {
            "type": "ir.actions.client",
            "tag": "vpk_official_document_sign_pdf_viewer",
            "name": title,
            "params": {
                "attachment_id": attachment.id,
                "res_model": document._name,
                "res_id": document.id,
                "title": title,
                "can_sign": bool(self.can_review),
            },
        }

    vpk_inbox_visible = fields.Boolean(
        string="Show in My Approvals",
        compute="_compute_vpk_inbox_visible",
        search="_search_vpk_inbox_visible",
    )

    def _compute_vpk_inbox_visible(self):
        hidden_ids = set(self._vpk_hidden_pr_inbox_review_ids())
        for rec in self:
            rec.vpk_inbox_visible = rec.id not in hidden_ids

    @api.model
    def _vpk_hidden_pr_inbox_review_ids(self):
        """Hide PR inbox rows while committee/approval packet documents are pending."""
        if "vpk.official.document" not in self.env:
            return []
        Document = self.env["vpk.official.document"]
        if "document_type" not in Document._fields:
            return []
        pending_docs = Document.search(
            [
                (
                    "document_type",
                    "in",
                    ("wa_committee_order", "specific_method_approval"),
                ),
                ("state", "=", "to_approve"),
                ("request_id", "!=", False),
            ]
        )
        pr_ids = pending_docs.mapped("request_id").ids
        if not pr_ids:
            return []
        return self.search(
            [
                ("model", "=", "purchase.request"),
                ("res_id", "in", pr_ids),
                ("status", "in", ("pending", "waiting")),
            ]
        ).ids

    @api.model
    def _search_vpk_inbox_visible(self, operator, value):
        hidden_ids = self._vpk_hidden_pr_inbox_review_ids()
        visible_wanted = (operator == "=" and value) or (
            operator == "!=" and not value
        )
        if visible_wanted:
            return [("id", "not in", hidden_ids)]
        return [("id", "in", hidden_ids or [0])]

    @api.model
    def _my_pending_domain(self):
        return [
            ("status", "=", "pending"),
            ("can_review", "=", True),
            ("reviewer_ids", "in", self.env.uid),
            ("vpk_inbox_visible", "=", True),
        ]

    @api.model
    def _my_approved_domain(self):
        return [
            ("status", "=", "approved"),
            ("done_by", "=", self.env.uid),
        ]

    @api.model
    def _my_rejected_domain(self):
        return [
            ("status", "=", "rejected"),
            ("done_by", "=", self.env.uid),
        ]

    @api.model
    def get_my_pending_count(self):
        return self.search_count(self._my_pending_domain())
