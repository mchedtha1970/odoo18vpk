# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VpkAssetInventoryCount(models.Model):
    _name = "vpk.asset.inventory.count"
    _description = "ตรวจนับทรัพย์สินประจำปี"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
        tracking=True,
    )
    fiscal_year = fields.Char(
        string="ปีงบประมาณ",
        required=True,
        default=lambda self: str(fields.Date.context_today(self).year + 543),
        tracking=True,
    )
    date = fields.Date(
        string="วันที่เอกสาร",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_start = fields.Date(string="วันเริ่มนับ", tracking=True)
    date_end = fields.Date(string="วันสิ้นสุดนับ", tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("open", "เปิดนับ"),
            ("done", "ปิดนับ"),
            ("cancel", "ยกเลิก"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    note = fields.Text(string="หมายเหตุ")
    sheet_ids = fields.One2many(
        comodel_name="vpk.asset.inventory.sheet",
        inverse_name="count_id",
        string="Sheet ตามหน่วยงาน",
    )
    line_ids = fields.One2many(
        comodel_name="vpk.asset.inventory.line",
        inverse_name="count_id",
        string="รายการตรวจนับ",
    )
    sheet_count = fields.Integer(compute="_compute_progress", string="จำนวน Sheet")
    line_count = fields.Integer(compute="_compute_progress", string="จำนวน")
    counted_line_count = fields.Integer(compute="_compute_progress", string="จำนวนที่นับ")
    progress = fields.Float(
        string="ความคืบหน้า (%)",
        compute="_compute_progress",
        digits=(16, 1),
    )

    @api.depends(
        "sheet_ids",
        "line_ids",
        "line_ids.is_counted",
    )
    def _compute_progress(self):
        for rec in self:
            rec.sheet_count = len(rec.sheet_ids)
            rec.line_count = len(rec.line_ids)
            counted = len(rec.line_ids.filtered("is_counted"))
            rec.counted_line_count = counted
            rec.progress = (counted * 100.0 / rec.line_count) if rec.line_count else 0.0

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/asset-inventory/{rec.id}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.asset.inventory.count")
                    or _("New")
                )
        return super().create(vals_list)

    def action_generate_sheets(self):
        """Generate sheets for ALL company assets (qty=1), grouped by owning department."""
        Asset = self.env["account.asset"]
        for count in self:
            if count.state != "draft":
                raise UserError(_("สร้าง Sheet ได้เฉพาะสถานะร่าง"))
            # Clear previous sheets/lines
            count.line_ids.unlink()
            count.sheet_ids.unlink()

            assets = Asset.search(
                [
                    ("company_id", "=", count.company_id.id),
                    ("state", "!=", "removed"),
                ]
            )
            if not assets:
                raise UserError(_("ไม่พบทรัพย์สินในระบบสำหรับบริษัทนี้"))

            warehouse = Asset._get_warehouse_analytic_account(count.company_id)
            by_dept = {}
            for asset in assets:
                dept = asset.owning_analytic_account_id or warehouse
                by_dept.setdefault(dept, Asset.browse())
                by_dept[dept] |= asset

            Sheet = self.env["vpk.asset.inventory.sheet"]
            Line = self.env["vpk.asset.inventory.line"]
            for dept, dept_assets in by_dept.items():
                sheet = Sheet.create(
                    {
                        "count_id": count.id,
                        "analytic_account_id": dept.id,
                    }
                )
                Line.create(
                    [
                        {
                            "count_id": count.id,
                            "sheet_id": sheet.id,
                            "asset_id": asset.id,
                            "system_qty": 1.0,
                            "counted_qty": 0.0,
                        }
                        for asset in dept_assets.sorted(
                            lambda a: (a.number or "", a.name or "", a.id)
                        )
                    ]
                )
            count.invalidate_recordset()
            count.message_post(
                body=_(
                    "สร้างรายการทรัพย์สินทั้งหมด %(lines)s รายการ "
                    "(%(sheets)s Sheet ตามหน่วยงาน) — จำนวนในระบบ = 1 ต่อรายการ"
                )
                % {"sheets": len(count.sheet_ids), "lines": len(count.line_ids)}
            )
        return True

    def action_open(self):
        for count in self:
            if count.state != "draft":
                raise UserError(_("เปิดนับได้เฉพาะสถานะร่าง"))
            if not count.line_ids:
                raise UserError(_("กรุณาสร้าง Sheet รายการตรวจนับก่อน"))
            count._portal_ensure_token()
            for sheet in count.sheet_ids:
                sheet._portal_ensure_token()
            for line in count.line_ids:
                line._portal_ensure_token()
            count.state = "open"
        return True

    def action_done(self):
        for count in self:
            if count.state != "open":
                raise UserError(_("ปิดนับได้เฉพาะสถานะเปิดนับ"))
            count.state = "done"
        return True

    def action_cancel(self):
        for count in self:
            if count.state == "done":
                raise UserError(_("เอกสารที่ปิดนับแล้วไม่สามารถยกเลิกได้"))
            count.state = "cancel"
        return True

    def action_draft(self):
        for count in self:
            if count.state != "cancel":
                raise UserError(_("ตั้งเป็นร่างได้เฉพาะที่ยกเลิกแล้ว"))
            count.state = "draft"
        return True

    def action_open_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการตรวจนับ"),
            "res_model": "vpk.asset.inventory.line",
            "view_mode": "list,form",
            "domain": [("count_id", "=", self.id)],
            "context": {"default_count_id": self.id, "search_default_pending": 1},
        }

    def action_open_sheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sheet ตามหน่วยงาน"),
            "res_model": "vpk.asset.inventory.sheet",
            "view_mode": "list,form",
            "domain": [("count_id", "=", self.id)],
            "context": {"default_count_id": self.id},
        }

    def action_open_portal(self):
        """Open portal inventory home / scan page in a new tab."""
        self.ensure_one()
        base = self.get_base_url().rstrip("/")
        return {
            "type": "ir.actions.act_url",
            "url": f"{base}/my/asset-inventory",
            "target": "new",
        }

    def action_open_portal_scan(self):
        """Open portal scan page for this count."""
        self.ensure_one()
        base = self.get_base_url().rstrip("/")
        return {
            "type": "ir.actions.act_url",
            "url": f"{base}/my/asset-inventory/scan/{self.id}",
            "target": "new",
        }


class VpkAssetInventorySheet(models.Model):
    _name = "vpk.asset.inventory.sheet"
    _description = "Sheet ตรวจนับตามหน่วยงาน"
    _inherit = ["mail.thread", "portal.mixin"]
    _order = "analytic_account_id, id"

    name = fields.Char(compute="_compute_name", store=True)
    count_id = fields.Many2one(
        comodel_name="vpk.asset.inventory.count",
        string="รอบตรวจนับ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="count_id.company_id", store=True)
    fiscal_year = fields.Char(related="count_id.fiscal_year", store=True)
    count_state = fields.Selection(related="count_id.state", store=True)
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน",
        required=True,
        index=True,
        check_company=True,
    )
    line_ids = fields.One2many(
        comodel_name="vpk.asset.inventory.line",
        inverse_name="sheet_id",
        string="รายการ",
    )
    line_count = fields.Integer(compute="_compute_progress", string="จำนวน")
    counted_line_count = fields.Integer(compute="_compute_progress", string="จำนวนที่นับ")
    progress = fields.Float(
        string="ความคืบหน้า (%)",
        compute="_compute_progress",
        digits=(16, 1),
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="vpk_asset_inventory_sheet_user_rel",
        column1="sheet_id",
        column2="user_id",
        string="ผู้แทนหน่วยงาน",
        help="ผู้ใช้ที่เข้าถึง Sheet นี้ผ่าน Portal (ถ้าว่างใช้หน่วยงานบน User)",
    )

    @api.depends("count_id.name", "analytic_account_id.name")
    def _compute_name(self):
        for sheet in self:
            sheet.name = "%s — %s" % (
                sheet.count_id.name or "",
                sheet.analytic_account_id.display_name or "",
            )

    @api.depends("line_ids", "line_ids.is_counted")
    def _compute_progress(self):
        for sheet in self:
            sheet.line_count = len(sheet.line_ids)
            counted = len(sheet.line_ids.filtered("is_counted"))
            sheet.counted_line_count = counted
            sheet.progress = (
                (counted * 100.0 / sheet.line_count) if sheet.line_count else 0.0
            )

    def _compute_access_url(self):
        super()._compute_access_url()
        for sheet in self:
            sheet.access_url = f"/my/asset-inventory/sheet/{sheet.id}"

    def action_open_portal(self):
        """Open this department sheet on portal (with access token)."""
        self.ensure_one()
        self._portal_ensure_token()
        url = self.get_base_url().rstrip("/") + self.access_url
        if self.access_token:
            url = f"{url}?access_token={self.access_token}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }


class VpkAssetInventoryLine(models.Model):
    _name = "vpk.asset.inventory.line"
    _description = "รายการตรวจนับทรัพย์สิน"
    _order = "sheet_id, asset_number, id"
    _inherit = ["portal.mixin"]

    count_id = fields.Many2one(
        comodel_name="vpk.asset.inventory.count",
        string="รอบตรวจนับ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sheet_id = fields.Many2one(
        comodel_name="vpk.asset.inventory.sheet",
        string="Sheet",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="count_id.company_id", store=True)
    count_state = fields.Selection(related="count_id.state", store=True)
    analytic_account_id = fields.Many2one(
        related="sheet_id.analytic_account_id",
        string="หน่วยงาน",
        store=True,
    )
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="ทรัพย์สิน",
        required=True,
        index=True,
        check_company=True,
    )
    asset_number = fields.Char(
        related="asset_id.number",
        string="เลขทรัพย์สิน",
        store=True,
        index=True,
    )
    asset_name = fields.Char(related="asset_id.name", string="ชื่อทรัพย์สิน", store=True)
    system_qty = fields.Float(string="จำนวนในระบบ", default=1.0, digits=(16, 2), required=True)
    counted_qty = fields.Float(string="Count", default=0.0, digits=(16, 2))
    difference = fields.Float(
        string="ผลต่าง",
        compute="_compute_difference",
        store=True,
        digits=(16, 2),
    )
    is_counted = fields.Boolean(
        string="นับแล้ว",
        compute="_compute_is_counted",
        store=True,
        index=True,
    )
    counted_by = fields.Many2one(comodel_name="res.users", string="ผู้บันทึก", readonly=True)
    counted_date = fields.Datetime(string="วันเวลาบันทึก", readonly=True)
    note = fields.Char(string="หมายเหตุ")

    _sql_constraints = [
        (
            "asset_unique_per_count",
            "unique(count_id, asset_id)",
            "ทรัพย์สินซ้ำในรอบตรวจนับเดียวกัน",
        ),
    ]

    @api.depends("system_qty", "counted_qty")
    def _compute_difference(self):
        for line in self:
            line.difference = line.counted_qty - line.system_qty

    @api.depends("counted_date")
    def _compute_is_counted(self):
        for line in self:
            line.is_counted = bool(line.counted_date)

    def _compute_access_url(self):
        super()._compute_access_url()
        for line in self:
            line.access_url = f"/my/asset-inventory/line/{line.id}"

    def get_portal_qr_url(self):
        """Absolute URL for mobile camera QR → opens count form.

        Prefer short public link /ai/<asset_number> so phone camera opens browser.
        """
        self.ensure_one()
        self._portal_ensure_token()
        from urllib.parse import quote

        number = (self.asset_number or "").strip()
        base = self.get_base_url().rstrip("/")
        if number:
            return f"{base}/ai/{quote(number, safe='')}"
        return f"{base}{self.access_url}?access_token={self.access_token}"

    def action_register_count(self, qty, note=None, user=None):
        """Record counted quantity from portal / backend."""
        user = user or self.env.user
        for line in self:
            if line.count_id.state != "open":
                raise UserError(_("บันทึกจำนวนได้เฉพาะช่วงเปิดนับ"))
            line.write(
                {
                    "counted_qty": qty,
                    "note": note if note is not None else line.note,
                    "counted_by": user.id,
                    "counted_date": fields.Datetime.now(),
                }
            )
        return True

    def action_open_asset(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("บัตรทรัพย์สิน"),
            "res_model": "account.asset",
            "view_mode": "form",
            "res_id": self.asset_id.id,
            "target": "current",
        }
