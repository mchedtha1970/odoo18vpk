# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models


THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


class SarabanDocument(models.Model):
    """ทะเบียนงานสารบรรณ (จำลองระบบสารบรรณสำหรับเชื่อมกับ PR)."""

    _name = "saraban.document"
    _description = "งานสารบรรณ"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "register_date desc, id desc"
    _rec_name = "book_no"

    name = fields.Char(
        string="ชื่อเรื่อง",
        required=True,
        tracking=True,
    )
    book_no = fields.Char(
        string="เลขที่สารบรรณ",
        copy=False,
        readonly=True,
        tracking=True,
        index=True,
    )
    book_no_display = fields.Char(
        string="เลขที่แสดงผล",
        compute="_compute_book_no_display",
        store=True,
    )
    register_date = fields.Date(
        string="วันที่ลงทะเบียน",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    doc_type = fields.Selection(
        selection=[
            ("memo", "บันทึกข้อความ"),
            ("letter", "หนังสือภายนอก"),
            ("internal", "หนังสือภายใน"),
            ("other", "อื่นๆ"),
        ],
        string="ประเภทเอกสาร",
        default="memo",
        required=True,
    )
    purpose = fields.Selection(
        selection=[
            ("pr_approval", "เอกสารอนุมัติขอซื้อ"),
            ("official_document", "หนังสือราชการ / คำสั่ง"),
        ],
        string="ใช้กับ",
        default="pr_approval",
        required=True,
        index=True,
        tracking=True,
        help="เลขจากใบขอซื้อใช้กับรายงานขออนุมัติจัดซื้อจัดจ้าง "
        "หนังสือราชการและคำสั่งอื่นต้องขอเลขแยกเอกสาร",
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("registered", "ลงทะเบียนแล้ว"),
            ("cancelled", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        tracking=True,
    )
    org_code = fields.Char(
        string="รหัสหน่วยงาน",
        default="ภก ๐๐๓๓.๒๐๑",
    )
    fiscal_year_be = fields.Char(
        string="ปีงบประมาณ (พ.ศ.)",
        compute="_compute_fiscal_year_be",
        store=True,
    )
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ/จ้าง/เช่า",
        ondelete="set null",
        index=True,
        tracking=True,
    )
    source_ref = fields.Char(
        string="อ้างอิงระบบต้นทาง",
        help="เช่น purchase.request/61",
        index=True,
        copy=False,
    )
    external_id = fields.Char(
        string="รหัสอ้างอิงสารบรรณ",
        copy=False,
        index=True,
        help="รหัสจากระบบสารบรรณภายนอก (ถ้ามี)",
    )
    note = fields.Text(string="หมายเหตุ")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends("register_date")
    def _compute_fiscal_year_be(self):
        for rec in self:
            if not rec.register_date:
                rec.fiscal_year_be = False
                continue
            # ปีงบ ต.ค.–ก.ย. → ปี พ.ศ. ของช่วงสิ้นสุด
            d = rec.register_date
            ce_year = d.year + 1 if d.month >= 10 else d.year
            rec.fiscal_year_be = str(ce_year + 543)

    @api.depends("org_code", "book_no", "fiscal_year_be")
    def _compute_book_no_display(self):
        for rec in self:
            if not rec.book_no:
                rec.book_no_display = False
                continue
            prefix = (rec.org_code or "").strip()
            if prefix and not prefix.endswith("/"):
                prefix = prefix + "/"
            display = "%s%s" % (prefix, rec.book_no)
            rec.book_no_display = display.translate(THAI_DIGITS)

    def action_register(self):
        """ออกเลขสารบรรณจาก Sequence."""
        for rec in self.filtered(lambda d: d.state == "draft"):
            if not rec.book_no:
                seq = self.env["ir.sequence"].next_by_code("saraban.document") or _(
                    "ใหม่"
                )
                # รูปแบบ: ปีงบ/รันนิ่ง เช่น 2569/0042
                year = rec.fiscal_year_be or str(fields.Date.context_today(rec).year + 543)
                # seq may already include year — use running number only
                running = seq.split("/")[-1] if "/" in seq else seq
                rec.book_no = "%s/%s" % (year, running)
            if not rec.external_id:
                rec.external_id = "SAR-%s-%s" % (
                    rec.fiscal_year_be or fields.Date.context_today(rec).year + 543,
                    rec.book_no.split("/")[-1],
                )
            rec.state = "registered"
            if rec.purchase_request_id and rec.purpose != "official_document":
                rec.purchase_request_id._sync_saraban_from_document(rec)
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def action_open_purchase_request(self):
        self.ensure_one()
        if not self.purchase_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "res_id": self.purchase_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
