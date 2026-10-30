# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TierReview(models.Model):
    _inherit = "tier.review"

    vpk_approver_user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้อนุมัติที่เพิ่มในเอกสาร",
        ondelete="set null",
        index=True,
    )
    vpk_approval_role = fields.Selection(
        selection=[
            ("check", "ตรวจสอบ"),
            ("sign", "ลงนาม"),
        ],
        string="หน้าที่ในลำดับอนุมัติ",
    )

    vpk_card_title = fields.Char(
        string="หัวข้อการ์ด",
        compute="_compute_vpk_card_info",
    )
    vpk_card_number = fields.Char(
        string="เลขที่เอกสาร",
        compute="_compute_vpk_card_info",
    )
    vpk_card_department = fields.Char(
        string="หน่วยงาน",
        compute="_compute_vpk_card_info",
    )
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

    @api.model
    def _get_reviewer_fields(self):
        return super()._get_reviewer_fields() + ["vpk_approver_user_id"]

    def _get_reviewers(self):
        if self.vpk_approver_user_id:
            return self.vpk_approver_user_id
        return super()._get_reviewers()

    @api.depends("model", "res_id", "vpk_approval_role", "name")
    def _compute_vpk_card_info(self):
        for rec in self:
            prefix = "ตรวจสอบ" if rec.vpk_approval_role == "check" else "ลงนาม"
            title = ""
            number = ""
            department = ""
            document = rec._vpk_card_document()
            info = rec._vpk_document_card_info(document)
            if info:
                subject = (info.get("subject") or "").strip()
                title = ("%s %s" % (prefix, subject)).strip() if subject else prefix
                number = info.get("number") or ""
                department = info.get("department") or ""
            elif document:
                title = document.display_name or ""
                number = document.name if "name" in document._fields else ""
                department_field = document._fields.get("department_id")
                if department_field and document.department_id:
                    department = document.department_id.display_name
            rec.vpk_card_title = title or rec.name or ""
            rec.vpk_card_number = number or ""
            rec.vpk_card_department = department or ""

    def _vpk_card_document(self):
        self.ensure_one()
        if not self.model or not self.res_id or self.model not in self.env:
            return self.env["tier.review"]
        return self.env[self.model].sudo().browse(self.res_id).exists()

    @api.model
    def _vpk_document_card_info(self, document):
        """Card texts from documents implementing ``_vpk_review_card_info``."""
        if document and hasattr(document, "_vpk_review_card_info"):
            return document._vpk_review_card_info()
        return {}

    @api.depends("model", "res_id")
    def _compute_res_display_name(self):
        for rec in self:
            name = ""
            try:
                document = rec._vpk_card_document()
                info = rec._vpk_document_card_info(document)
                if info:
                    name = info.get("type_label") or document.display_name
                    if info.get("context"):
                        name = "{} · {}".format(info["context"], name)
                elif document:
                    name = document.display_name
            except Exception:
                name = ""
            rec.res_display_name = name

    @api.depends("model", "res_id")
    def _compute_model_display_name(self):
        for rec in self:
            label = ""
            try:
                info = rec._vpk_document_card_info(rec._vpk_card_document())
                label = info.get("type_label") or ""
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
        document = self._vpk_card_document()
        if document and hasattr(document, "_sign_viewer_action"):
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
        """Overridden by modules whose documents are signed in the PDF viewer."""
        self.ensure_one()
        return self.action_open_resource()

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
        """Reviews hidden from the inbox; extended by document modules."""
        hidden_ids = []
        # Deduplicate approved reviews per (model, res_id, actor_user) so each
        # approver sees one card per approved document.
        approved_reviews = self.sudo().search(
            [("status", "=", "approved")],
            order="sequence desc, id desc",
        )
        seen_approved_keys = set()
        for rev in approved_reviews:
            actor_id = (
                rev.done_by.id
                or getattr(rev, "vpk_signer_user_id", self.env["res.users"]).id
                or rev.vpk_approver_user_id.id
            )
            if not actor_id:
                continue
            key = (rev.model, rev.res_id, actor_id)
            if key in seen_approved_keys:
                hidden_ids.append(rev.id)
            else:
                seen_approved_keys.add(key)
        return hidden_ids

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
            ("vpk_inbox_visible", "=", True),
            "|",
            ("done_by", "=", self.env.uid),
            ("reviewer_ids", "in", self.env.uid),
        ]

    @api.model
    def _my_all_domain(self):
        return [
            "|",
            "&",
            "&",
            ("status", "=", "pending"),
            ("can_review", "=", True),
            "&",
            ("reviewer_ids", "in", self.env.uid),
            ("vpk_inbox_visible", "=", True),
            "&",
            "&",
            ("status", "=", "approved"),
            ("vpk_inbox_visible", "=", True),
            "|",
            ("done_by", "=", self.env.uid),
            ("reviewer_ids", "in", self.env.uid),
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

    @api.model
    def get_my_review_counts(self):
        pending_domain = self._my_pending_domain()
        approved_domain = self._my_approved_domain()
        all_domain = self._my_all_domain()
        pending_count = self.search_count(pending_domain)
        approved_count = self.search_count(approved_domain)
        return {
            "pending_count": pending_count,
            "approved_count": approved_count,
            "total_count": pending_count + approved_count,
            "pending_domain": pending_domain,
            "approved_domain": approved_domain,
            "all_domain": all_domain,
        }

    _APPROVAL_STATUS_LABEL = {
        "approved": "อนุมัติแล้ว",
        "pending": "รออนุมัติ",
        "waiting": "ยังไม่ถึงคิว",
        "rejected": "ไม่อนุมัติ",
        "cancel": "ยกเลิก",
    }

    @api.model
    def get_approval_status_board(self):
        """In-progress and fully approved documents, with each approver in sequence."""
        reviews = self.search([("status", "in", ("pending", "waiting", "approved"))])
        keys = {
            (review.model, review.res_id)
            for review in reviews
            if review.model and review.res_id and review.model in self.env
        }
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        payload = {
            "updated_at": now.strftime("%H:%M"),
            "total": 0,
            "open_count": 0,
            "done_count": 0,
            "types": [],
        }
        if not keys:
            return payload
        grouped = {}
        for review in reviews:
            if (review.model, review.res_id) not in keys:
                continue
            grouped.setdefault((review.model, review.res_id), self.env["tier.review"])
            grouped[(review.model, review.res_id)] |= review
        type_buckets = {}
        for key, chain in grouped.items():
            document = self._approval_board_document(key[0], key[1])
            if not document:
                continue
            steps = [
                self._approval_board_step(review, document)
                for review in chain.sorted(lambda review: (review.sequence, review.id))
            ]
            waiting = [step for step in steps if step["status"] == "pending"]
            statuses = {step["status"] for step in steps}
            if waiting or "waiting" in statuses:
                progress = "open"
                progress_label = "อยู่ระหว่างอนุมัติ"
            elif statuses == {"approved"}:
                progress = "done"
                progress_label = "อนุมัติครบแล้ว"
            else:
                continue
            card = {
                "model": key[0],
                "res_id": key[1],
                "name": document["name"],
                "subtitle": document["subtitle"],
                "progress": progress,
                "progress_label": progress_label,
                "waiting_on": ", ".join(step["person"] for step in waiting),
                "steps": steps,
            }
            bucket = type_buckets.setdefault(
                document["type_key"],
                {
                    "key": document["type_key"],
                    "label": document["type_label"],
                    "documents": [],
                },
            )
            bucket["documents"].append(card)
        types = []
        for bucket in type_buckets.values():
            bucket["documents"].sort(
                key=lambda card: (card["progress"] != "open", card["name"] or "")
            )
            bucket["count"] = len(bucket["documents"])
            bucket["open_count"] = len(
                [card for card in bucket["documents"] if card["progress"] == "open"]
            )
            bucket["done_count"] = bucket["count"] - bucket["open_count"]
            types.append(bucket)
        types.sort(
            key=lambda bucket: (
                bucket["open_count"] == 0,
                -bucket["count"],
                bucket["label"] or "",
            )
        )
        payload["types"] = types
        payload["total"] = sum(bucket["count"] for bucket in types)
        payload["open_count"] = sum(bucket["open_count"] for bucket in types)
        payload["done_count"] = sum(bucket["done_count"] for bucket in types)
        return payload

    @api.model
    def _approval_board_document(self, model, res_id):
        try:
            document = self.env[model].sudo().browse(res_id).exists()
        except Exception:
            return False
        if not document:
            return False
        info = self._vpk_document_card_info(document)
        if info.get("hide_on_board"):
            return False
        type_label = info.get("type_label") or document._description or model
        type_key = info.get("type_key") or model
        subtitle_parts = [info.get("context"), info.get("subject")] if info else []
        signer_id = info.get("signer_id") or False
        return {
            "type_key": type_key,
            "type_label": type_label,
            "name": document.display_name or str(res_id),
            "subtitle": " · ".join(part for part in subtitle_parts if part),
            "model": model,
            "signer_id": signer_id,
            "signed_document": bool(info),
            "secretary_id": self._approval_board_secretary_id(),
        }

    @api.model
    def _approval_board_secretary_id(self):
        secretary = self.env.ref(
            "vpk_tier_validation.user_director_secretary",
            raise_if_not_found=False,
        )
        return secretary.id if secretary else False

    @api.model
    def _approval_board_step(self, review, document):
        person = getattr(review, "vpk_signer_name", "") or ""
        if not person and review.status == "approved" and review.done_by:
            person = review.done_by.name
        if not person:
            person = review.todo_by or ""
        if not person and review.reviewer_ids:
            person = ", ".join(review.reviewer_ids.mapped("name"))
        if not person:
            person = review.name or "ไม่ระบุผู้อนุมัติ"
        status = review.status or "waiting"
        return {
            "sequence": review.sequence,
            "person": person,
            "status": status,
            "status_label": self._approval_board_status_label(review, document, status),
            "current": status == "pending",
        }

    @api.model
    def _approval_board_status_label(self, review, document, status):
        if status == "approved" and getattr(review, "vpk_approval_role", False) == "check":
            return "ตรวจสอบแล้ว"
        if status == "approved" and document.get("signed_document"):
            user_ids = set()
            signer_user = getattr(review, "vpk_signer_user_id", False)
            if signer_user:
                user_ids.add(signer_user.id)
            user_ids.update(review.reviewer_ids.ids)
            if document.get("secretary_id") in user_ids:
                return "ตรวจสอบแล้ว"
            if document.get("signer_id") in user_ids:
                return "ลงนามและอนุมัติแล้ว"
            return "ลงนามแล้ว"
        return self._APPROVAL_STATUS_LABEL.get(status, status)
