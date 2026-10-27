# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

FALLBACK_DOCUMENT_TYPES = [
    ("wa_committee_order", "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ"),
    ("integrity_over_100k", "แบบแสดงความบริสุทธิ์ใจ (วงเงินมากกว่า ๑๐๐,๐๐๐ บาท)"),
    (
        "spec_price_committee",
        "ขออนุมัติแต่งตั้งคณะกรรมการกำหนดรายละเอียดคุณลักษณะ",
    ),
    (
        "specific_method_approval",
        "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
    ),
    ("winner_announcement", "ประกาศผู้ชนะการเสนอราคา"),
    ("award_approval", "รายงานผลการพิจารณาจัดซื้อจัดจ้าง"),
    ("purchase_approval_memo", "บันทึกข้อความอนุมัติขอซื้อ"),
    ("inspection_report", "ใบตรวจรับการจัดซื้อ/จัดจ้าง"),
]

TYPE_ICONS = {
    "wa_committee_order": "users",
    "integrity_over_100k": "balance",
    "spec_price_committee": "list",
    "specific_method_approval": "file",
    "winner_announcement": "bullhorn",
    "award_approval": "trophy",
    "purchase_approval_memo": "pencil",
    "inspection_report": "clipboard",
}

TYPE_TONES = {
    "wa_committee_order": "navy",
    "integrity_over_100k": "teal",
    "spec_price_committee": "indigo",
    "specific_method_approval": "amber",
    "winner_announcement": "rose",
    "award_approval": "violet",
    "purchase_approval_memo": "sky",
    "inspection_report": "green",
}


class OfficialDocumentType(models.Model):
    _name = "vpk.official.document.type"
    _description = "ประเภทหนังสือราชการ"
    _order = "sequence, id"

    name = fields.Char(string="ชื่อประเภท", required=True, translate=True)
    code = fields.Char(
        string="รหัส",
        index=True,
        copy=False,
        help="เว้นว่างได้ ระบบจะออกให้เอง ไม่เปลี่ยนรหัสของประเภทที่มากับระบบ",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_system = fields.Boolean(
        string="ประเภทของระบบ",
        default=False,
        copy=False,
        help="ประเภทที่มากับระบบ แก้ชื่อได้ แต่ลบหรือเปลี่ยนรหัสไม่ได้",
    )
    create_from_purchase_request = fields.Boolean(
        string="สร้างจากใบขอซื้อ",
        help="แสดงในช่องเอกสารที่จะสร้างของแท็บเอกสารราชการที่เกี่ยวข้อง",
    )
    create_from_work_acceptance = fields.Boolean(
        string="สร้างจากใบรับมอบงาน",
        help="แสดงในช่องเอกสารที่จะสร้างของแท็บเอกสารราชการที่เกี่ยวข้องในใบรับมอบงาน",
    )
    note = fields.Text(string="คำอธิบาย")

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "รหัสประเภทเอกสารต้องไม่ซ้ำ",
        ),
    ]

    @api.model
    def selection_pairs(self):
        """Options for document type dropdowns. Falls back while the table is loading."""
        if not self.env.registry.ready:
            return list(FALLBACK_DOCUMENT_TYPES)
        types = self.sudo().with_context(active_test=False).search([])
        if not types:
            return list(FALLBACK_DOCUMENT_TYPES)
        return [(item.code, item.name) for item in types if item.active]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code(
                        "vpk.official.document.type"
                    )
                    or "type"
                )
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            protected = self.filtered("is_system")
            if any(rec.code != vals["code"] for rec in protected):
                raise UserError(_("ไม่สามารถเปลี่ยนรหัสประเภทเอกสารของระบบ"))
        return super().write(vals)

    def unlink(self):
        if any(self.mapped("is_system")):
            raise UserError(_("ไม่สามารถลบประเภทเอกสารของระบบ ปิดการใช้งานแทนได้"))
        return super().unlink()

    def _dashboard_icon(self):
        self.ensure_one()
        return TYPE_ICONS.get(self.code, "file")

    def _dashboard_tone(self):
        self.ensure_one()
        return TYPE_TONES.get(self.code, "slate")

    def action_open_documents(self, state=None):
        self.ensure_one()
        domain = [("document_type", "=", self.code)]
        if state == "draft":
            domain.append(("state", "in", ["draft", "generated"]))
        elif state == "waiting":
            domain.append(("state", "=", "to_approve"))
        elif state == "approved":
            domain.append(("state", "=", "approved"))
        elif state:
            domain.append(("state", "=", state))
        return self._documents_action(
            self.name,
            domain=domain,
            context={"default_document_type": self.code},
        )

    @api.model
    def action_open_all_documents(self, state=None):
        domain = []
        if state == "draft":
            domain = [("state", "in", ["draft", "generated"])]
        elif state == "waiting":
            domain = [("state", "=", "to_approve")]
        elif state == "approved":
            domain = [("state", "=", "approved")]
        elif state:
            domain = [("state", "=", state)]
        titles = {
            "draft": _("ร่าง / สร้างไฟล์แล้ว"),
            "waiting": _("รออนุมัติ"),
            "approved": _("อนุมัติแล้ว"),
        }
        return self._documents_action(
            titles.get(state, _("หนังสือราชการทั้งหมด")),
            domain=domain,
        )

    @api.model
    def _documents_action(self, name, domain=None, context=None):
        list_view = self.env.ref(
            "vpk_official_document.view_official_document_list",
            raise_if_not_found=False,
        )
        form_view = self.env.ref(
            "vpk_official_document.view_official_document_form",
            raise_if_not_found=False,
        )
        views = []
        if list_view:
            views.append((list_view.id, "list"))
        else:
            views.append((False, "list"))
        if form_view:
            views.append((form_view.id, "form"))
        else:
            views.append((False, "form"))
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "vpk.official.document",
            "view_mode": "list,form",
            "views": views,
            "domain": domain or [],
            "context": context or {},
            "target": "current",
        }

    @api.model
    def get_dashboard_data(self):
        types = self.search([])
        counts = defaultdict(lambda: defaultdict(int))
        if types:
            grouped = self.env["vpk.official.document"]._read_group(
                [("document_type", "in", types.mapped("code"))],
                ["document_type", "state"],
                ["__count"],
            )
            for document_type, state, count in grouped:
                counts[document_type][state] = count
                counts[document_type]["all"] += count
                if state != "cancelled":
                    counts[document_type]["active"] += count

        cards = []
        totals = defaultdict(int)
        for rec in types:
            bucket = counts[rec.code]
            draft = bucket["draft"] + bucket["generated"]
            waiting = bucket["to_approve"]
            approved = bucket["approved"]
            total = bucket["all"]
            totals["total"] += total
            totals["draft"] += draft
            totals["waiting"] += waiting
            totals["approved"] += approved
            cards.append(
                {
                    "id": rec.id,
                    "code": rec.code,
                    "name": rec.name,
                    "note": rec.note or "",
                    "icon": rec._dashboard_icon(),
                    "tone": rec._dashboard_tone(),
                    "total": total,
                    "draft": draft,
                    "waiting": waiting,
                    "approved": approved,
                    "action": rec.action_open_documents(),
                    "draft_action": rec.action_open_documents("draft"),
                    "waiting_action": rec.action_open_documents("waiting"),
                    "approved_action": rec.action_open_documents("approved"),
                }
            )

        return {
            "title": _("หนังสือราชการ"),
            "subtitle": _("เลือกประเภทเอกสารเพื่อดูรายการ"),
            "kpis": [
                {
                    "key": "total",
                    "label": _("เอกสารทั้งหมด"),
                    "count": totals["total"],
                    "tone": "navy",
                    "action": self.action_open_all_documents(),
                },
                {
                    "key": "draft",
                    "label": _("ร่าง / สร้างไฟล์แล้ว"),
                    "count": totals["draft"],
                    "tone": "slate",
                    "action": self.action_open_all_documents("draft"),
                },
                {
                    "key": "waiting",
                    "label": _("รออนุมัติ"),
                    "count": totals["waiting"],
                    "tone": "amber",
                    "action": self.action_open_all_documents("waiting"),
                },
                {
                    "key": "approved",
                    "label": _("อนุมัติแล้ว"),
                    "count": totals["approved"],
                    "tone": "green",
                    "action": self.action_open_all_documents("approved"),
                },
            ],
            "cards": cards,
        }
