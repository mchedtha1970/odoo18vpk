# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    saraban_document_ids = fields.One2many(
        comodel_name="saraban.document",
        inverse_name="purchase_request_id",
        string="งานสารบรรณ",
    )
    saraban_document_id = fields.Many2one(
        comodel_name="saraban.document",
        string="เอกสารสารบรรณ",
        compute="_compute_saraban_document_id",
        store=True,
        readonly=True,
    )
    saraban_status = fields.Selection(
        selection=[
            ("none", "ยังไม่ขอเลข"),
            ("pending", "รอลงทะเบียน"),
            ("registered", "ได้เลขสารบรรณแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะสารบรรณ",
        compute="_compute_saraban_status",
        store=True,
        tracking=True,
    )
    saraban_book_no = fields.Char(
        string="เลขที่สารบรรณ",
        related="saraban_document_id.book_no",
        store=True,
        readonly=True,
    )
    saraban_book_no_display = fields.Char(
        string="เลขที่สารบรรณ (แสดงผล)",
        related="saraban_document_id.book_no_display",
        readonly=True,
    )
    saraban_external_id = fields.Char(
        string="รหัสอ้างอิงสารบรรณ",
        related="saraban_document_id.external_id",
        readonly=True,
    )
    saraban_document_count = fields.Integer(
        compute="_compute_saraban_document_id",
    )

    @api.depends(
        "saraban_document_ids",
        "saraban_document_ids.state",
        "saraban_document_ids.purpose",
    )
    def _compute_saraban_document_id(self):
        for request in self:
            docs = request.saraban_document_ids.filtered(
                lambda d: d.state != "cancelled"
                and (d.purpose or "pr_approval") == "pr_approval"
            ).sorted("id", reverse=True)
            request.saraban_document_id = docs[:1]
            request.saraban_document_count = len(request.saraban_document_ids)

    @api.depends("saraban_document_id", "saraban_document_id.state")
    def _compute_saraban_status(self):
        for request in self:
            doc = request.saraban_document_id
            if not doc:
                request.saraban_status = "none"
            elif doc.state == "draft":
                request.saraban_status = "pending"
            elif doc.state == "registered":
                request.saraban_status = "registered"
            elif doc.state == "cancelled":
                request.saraban_status = "cancelled"
            else:
                request.saraban_status = "none"

    def _sync_saraban_from_document(self, document):
        """ดึงเลขสารบรรณมาใส่เลขที่หนังสือในบันทึกข้อความ."""
        self.ensure_one()
        vals = {
            "memo_date": document.register_date or fields.Date.context_today(self),
        }
        if document.book_no:
            vals["memo_ref"] = document.book_no
        if document.org_code:
            prefix = document.org_code.strip()
            if not prefix.endswith("/"):
                prefix += "/"
            vals["memo_ref_prefix"] = prefix
        if document.name and not self.memo_subject:
            vals["memo_subject"] = document.name
        self.with_context(skip_validation_check=True).write(vals)
        self.message_post(
            body=_(
                "เชื่อมต่อระบบสารบรรณสำเร็จ<br/>"
                "เลขที่สารบรรณ: <b>%(book)s</b><br/>"
                "รหัสอ้างอิง: %(ext)s"
            )
            % {
                "book": document.book_no_display or document.book_no,
                "ext": document.external_id or "-",
            }
        )

    def action_request_saraban_number(self):
        """สร้างงานสารบรรณจาก PR และออกเลขอัตโนมัติ."""
        Saraban = self.env["saraban.document"]
        for request in self:
            existing = request.saraban_document_ids.filtered(
                lambda d: (d.purpose or "pr_approval") == "pr_approval"
                and d.state in ("draft", "registered")
            )
            if existing.filtered(lambda d: d.state == "registered"):
                raise UserError(
                    _(
                        "PR %(name)s มีเลขสารบรรณสำหรับเอกสารอนุมัติขอซื้อแล้ว (%(book)s)\n"
                        "เลขนี้ใช้กับรายงานขออนุมัติจัดซื้อจัดจ้าง "
                        "หนังสือราชการและคำสั่งอื่นให้กดขอเลขที่เอกสารนั้น\n"
                        "หากต้องการออกเลขอนุมัติขอซื้อใหม่ ให้ยกเลิกเอกสารสารบรรณเดิมก่อน"
                    )
                    % {
                        "name": request.name,
                        "book": existing.filtered(
                            lambda d: d.state == "registered"
                        )[:1].book_no_display,
                    }
                )
            draft = existing.filtered(lambda d: d.state == "draft")[:1]
            subject = (
                request.memo_subject
                or request.description
                or _("ขออนุมัติจัดซื้อ/จ้าง/เช่า ตาม %s") % request.name
            )
            if draft:
                doc = draft
                doc.write(
                    {
                        "name": subject,
                        "purpose": "pr_approval",
                        "source_ref": "purchase.request/%s" % request.id,
                    }
                )
            else:
                doc = Saraban.create(
                    {
                        "name": subject,
                        "purpose": "pr_approval",
                        "doc_type": "memo",
                        "purchase_request_id": request.id,
                        "source_ref": "purchase.request/%s" % request.id,
                        "org_code": (request.memo_ref_prefix or "ภก ๐๐๓๓.๒๐๑").rstrip(
                            "/"
                        ),
                        "company_id": request.company_id.id,
                        "note": _("สร้างจากใบขอซื้อ/จ้าง/เช่า %s สำหรับเอกสารอนุมัติขอซื้อ")
                        % request.name,
                    }
                )
            doc.action_register()
        return True

    def action_view_saraban_documents(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("งานสารบรรณ"),
            "res_model": "saraban.document",
            "view_mode": "list,form",
            "domain": [("purchase_request_id", "=", self.id)],
            "context": {
                "default_purchase_request_id": self.id,
                "default_name": self.memo_subject or self.description or self.name,
                "default_source_ref": "purchase.request/%s" % self.id,
            },
        }
        if self.saraban_document_count == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.saraban_document_ids[:1].id
        return action
