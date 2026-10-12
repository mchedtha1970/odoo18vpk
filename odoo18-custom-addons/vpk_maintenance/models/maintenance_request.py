# -*- coding: utf-8 -*-
import re
from pathlib import Path
from urllib.parse import unquote

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_REPORT_FONT_CSS = None


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    sub_state = fields.Selection(
        selection=[
            ("waiting_assessment", "รอประเมิน"),
            ("assessed", "ประเมินแล้ว"),
            ("repairing", "กำลังซ่อม"),
            ("waiting_parts", "รออะไหล่"),
            ("waiting_disposal", "รอจำหน่าย"),
            ("repaired", "ซ่อมเสร็จสิ้น"),
        ],
        string="สถานะการดำเนินการ",
        default="waiting_assessment",
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    assessment_result_id = fields.Many2one(
        comodel_name="maintenance.assessment.result",
        string="ผลการประเมิน",
        tracking=True,
        copy=False,
        index=True,
        ondelete="restrict",
    )
    assessment_result_code = fields.Char(
        related="assessment_result_id.code",
        string="รหัสผลการประเมิน",
    )
    department_id = fields.Many2one(
        comodel_name="maintenance.department",
        string="ฝ่าย / งาน / ตึก",
        tracking=True,
        ondelete="restrict",
    )
    requester_phone = fields.Char(string="โทร")
    request_qty = fields.Integer(string="จำนวน", default=1)
    machine_number = fields.Char(string="หมายเลขเครื่อง", copy=False)
    receipt_number = fields.Char(
        string="เลขที่รับซ่อม",
        copy=False,
        readonly=True,
        index=True,
        tracking=True,
    )
    receipt_date = fields.Date(
        string="วันที่รับ",
        copy=False,
        default=fields.Date.context_today,
    )
    receipt_time = fields.Float(
        string="เวลา",
        copy=False,
        default=lambda self: self._default_receipt_time(),
    )
    signature = fields.Image(
        string="ลายเซ็น",
        copy=False,
        attachment=True,
    )
    chief_signature = fields.Image(
        string="ลายเซ็นหัวหน้างาน",
        copy=False,
        attachment=True,
    )
    chief_signed_on = fields.Date(
        string="วันที่ลงชื่อ",
        copy=False,
    )
    assignee_signature = fields.Image(
        string="ลายเซ็นผู้ได้รับมอบหมาย",
        copy=False,
        attachment=True,
    )
    assignee_signed_on = fields.Date(
        string="วันที่ลงชื่อ",
        copy=False,
    )
    prelim_outsource = fields.Boolean(string="ว่าจ้างช่างภายนอกดำเนินการซ่อม")
    prelim_outsource_reason = fields.Char(string="เนื่องจาก")
    prelim_purchase_parts = fields.Boolean(
        string="จัดซื้อวัสดุ อุปกรณ์ซ่อม ตามรายการขออนุมัติเบิกวัสดุงานช่าง",
    )
    prelim_material_volume = fields.Char(string="เล่มที่")
    prelim_material_number = fields.Char(string="เลขที่")
    prelim_finish_days = fields.Integer(string="ประมาณการแล้วเสร็จภายใน (วัน)")
    prelim_dispose = fields.Boolean(string="แทงจำหน่าย")
    prelim_initial_check = fields.Boolean(string="ตรวจเช็คเบื้องต้น")
    prelim_check_reason = fields.Char(string="เนื่องจาก")
    technician_signature = fields.Image(
        string="ลายเซ็นช่างผู้ปฏิบัติงาน",
        copy=False,
        attachment=True,
    )
    technician_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    chief_comment = fields.Text(string="ความคิดเห็นของหัวหน้าช่าง")
    chief_comment_signature = fields.Image(
        string="ลายเซ็นหัวหน้าช่าง",
        copy=False,
        attachment=True,
    )
    chief_comment_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    deputy_approved = fields.Boolean(string="อนุมัติ")
    deputy_acknowledged = fields.Boolean(string="ทราบ")
    deputy_comment = fields.Text(string="ความคิดเห็นของรองผู้อำนวยการฝ่ายบริหาร")
    deputy_signature = fields.Image(
        string="ลายเซ็นรองผู้อำนวยการฝ่ายบริหาร",
        copy=False,
        attachment=True,
    )
    deputy_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    director_comment = fields.Text(string="ความคิดเห็นของผู้อำนวยการ")
    director_signature = fields.Image(
        string="ลายเซ็นผู้อำนวยการโรงพยาบาลวชิระภูเก็ต",
        copy=False,
        attachment=True,
    )
    director_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    result_issue_volume = fields.Char(string="เล่มที่")
    result_issue_number = fields.Char(string="เลขที่")
    issuer_signature = fields.Image(
        string="ลายเซ็นผู้จ่ายวัสดุช่าง",
        copy=False,
        attachment=True,
    )
    issuer_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    repair_done_signature = fields.Image(
        string="ลายเซ็นช่างผู้ปฏิบัติงาน",
        copy=False,
        attachment=True,
    )
    repair_done_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    repair_detail = fields.Text(string="รายละเอียดการซ่อม / ข้อเสนอแนะ")
    cost_line_ids = fields.One2many(
        comodel_name="maintenance.request.cost.line",
        inverse_name="request_id",
        string="สรุปค่าใช้จ่าย",
        copy=False,
    )
    used_material_line_ids = fields.One2many(
        comodel_name="maintenance.request.material.line",
        inverse_name="request_id",
        string="วัสดุที่ใช้ในการดำเนินการ",
        copy=False,
    )
    satisfaction = fields.Selection(
        selection=[
            ("high", "มาก"),
            ("medium", "ปานกลาง"),
            ("low", "น้อย"),
        ],
        string="มีความพึงพอใจ",
    )
    service_speed = fields.Selection(
        selection=[
            ("high", "มาก"),
            ("medium", "ปานกลาง"),
            ("low", "น้อย"),
            ("very_slow", "ช้ามาก"),
        ],
        string="การปฏิบัติงานรวดเร็ว",
    )
    other_feedback = fields.Text(string="ข้อเสนอแนะ / ข้อร้องเรียนอื่นๆ")
    dept_head_signature = fields.Image(
        string="ลายเซ็นหัวหน้าหน่วยงาน",
        copy=False,
        attachment=True,
    )
    dept_head_signed_on = fields.Date(string="วันที่ลงชื่อ", copy=False)
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        related="equipment_id.asset_id",
        string="ทรัพย์สิน",
        store=True,
        readonly=True,
    )
    asset_state = fields.Selection(
        related="asset_id.state",
        string="สถานะทรัพย์สิน",
    )
    parts_picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="maintenance_request_id",
        string="ใบเบิกอะไหล่",
        copy=False,
    )
    parts_picking_count = fields.Integer(
        string="จำนวนใบเบิกอะไหล่",
        compute="_compute_parts_picking_count",
    )
    parts_move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="maintenance_request_id",
        string="รายการอะไหล่ที่เบิก",
        copy=False,
    )
    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="maintenance_request_id",
        string="Purchase Request",
        copy=False,
    )
    purchase_request_count = fields.Integer(
        string="จำนวน PR",
        compute="_compute_purchase_request_count",
    )
    vendor_send_ids = fields.One2many(
        comodel_name="maintenance.vendor.send",
        inverse_name="request_id",
        string="คำร้องส่งซ่อมบริษัท",
        copy=False,
    )
    vendor_send_count = fields.Integer(
        string="จำนวนคำร้องส่งซ่อมบริษัท",
        compute="_compute_vendor_send_count",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="สกุลเงิน",
    )
    parts_total_value = fields.Monetary(
        string="มูลค่ารวมอะไหล่",
        compute="_compute_parts_total_value",
        currency_field="company_currency_id",
    )

    @api.depends("parts_picking_ids")
    def _compute_parts_picking_count(self):
        for request in self:
            request.parts_picking_count = len(request.parts_picking_ids)

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        for request in self:
            request.purchase_request_count = len(request.purchase_request_ids)

    @api.depends("vendor_send_ids")
    def _compute_vendor_send_count(self):
        for request in self:
            request.vendor_send_count = len(request.vendor_send_ids)

    @api.depends(
        "parts_move_ids",
        "parts_move_ids.state",
        "parts_move_ids.quantity",
        "parts_move_ids.product_uom_qty",
        "parts_move_ids.product_id.standard_price",
        "parts_move_ids.stock_valuation_layer_ids.value",
    )
    def _compute_parts_total_value(self):
        for request in self:
            moves = request.parts_move_ids.filtered(lambda m: m.state != "cancel")
            request.parts_total_value = sum(moves.mapped("parts_value"))

    @api.model
    def _default_receipt_time(self):
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return now.hour + (now.minute / 60.0)

    @api.onchange("equipment_id")
    def _onchange_equipment_machine_number(self):
        equipment = self.equipment_id
        if equipment and not self.machine_number:
            self.machine_number = equipment.sudo().serial_no or ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("receipt_date", fields.Date.context_today(self))
            vals.setdefault("receipt_time", self._default_receipt_time())
        records = super().create(vals_list)
        records._assign_receipt_values()
        return records

    def _assign_receipt_values(self):
        for request in self:
            vals = {}
            if not request.receipt_number:
                seq = self.env["ir.sequence"].next_by_code("vpk.maintenance.receipt") or "00000"
                day = request.request_date or fields.Date.context_today(self)
                vals["receipt_number"] = "ซ่อม/%s/%s" % (day.year + 543, seq)
            if not request.machine_number and request.equipment_id:
                serial = request.equipment_id.sudo().serial_no
                if serial:
                    vals["machine_number"] = serial
            if vals:
                request.with_context(mail_notrack=True).write(vals)

    @api.model
    def _backfill_receipt_numbers(self):
        pending = self.sudo().search([("receipt_number", "=", False)])
        for request in pending:
            if not request.receipt_date and request.request_date:
                request.receipt_date = request.request_date
        pending._assign_receipt_values()

    def _report_font_css(self):
        """TH Sarabun New as a data-URI, so wkhtmltopdf can embed the government font."""
        global _REPORT_FONT_CSS
        if _REPORT_FONT_CSS is None:
            path = (
                Path(__file__).resolve().parents[2]
                / "vpk_tier_validation"
                / "static/src/scss/thai_fonts_embedded.scss"
            )
            _REPORT_FONT_CSS = (
                Markup(path.read_text(encoding="utf-8")) if path.is_file() else Markup("")
            )
        return _REPORT_FONT_CSS

    def _report_date_line(self, value):
        months = (
            "",
            "มกราคม",
            "กุมภาพันธ์",
            "มีนาคม",
            "เมษายน",
            "พฤษภาคม",
            "มิถุนายน",
            "กรกฎาคม",
            "สิงหาคม",
            "กันยายน",
            "ตุลาคม",
            "พฤศจิกายน",
            "ธันวาคม",
        )
        if not value:
            return "วันที่ ............ เดือน .................... พ.ศ. ............"
        return "วันที่ %s เดือน %s พ.ศ. %s" % (value.day, months[value.month], value.year + 543)

    def _report_short_date(self, value):
        if not value:
            return ""
        return "%02d/%02d/%s" % (value.day, value.month, value.year + 543)

    def _report_clock(self, value):
        if not value:
            return ""
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if minutes >= 60:
            hours += 1
            minutes -= 60
        return "%02d:%02d" % (hours % 24, minutes)

    def _report_team_on(self, code):
        self.ensure_one()
        xmlid = {
            "civil": "vpk_maintenance.maintenance_team_civil",
            "general": "vpk_maintenance.maintenance_team_general",
            "medical": "vpk_maintenance.maintenance_team_medical",
        }.get(code)
        team = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False
        return bool(team and self.maintenance_team_id == team)

    def _report_item_name(self):
        self.ensure_one()
        equipment = self.equipment_id.sudo()
        if equipment:
            return equipment.name or ""
        return self.name or ""

    def _report_asset_number(self):
        self.ensure_one()
        equipment = self.equipment_id.sudo()
        if equipment and equipment.asset_number:
            return equipment.asset_number
        asset = (equipment.asset_id or self.asset_id).sudo() if (equipment or self.asset_id) else False
        if asset and "number" in asset._fields and asset.number:
            return asset.number
        return ""

    def _report_rows(self, lines, size=4):
        rows = list(lines)
        blank = lines.browse()
        while len(rows) < size:
            rows.append(blank)
        return rows

    def _report_money(self, amount):
        if not amount:
            return ""
        return "{:,.2f}".format(amount)

    def write(self, vals):
        # เมื่อปิดงาน (stage done) ให้สถานะดำเนินการเป็นซ่อมเสร็จสิ้นโดยอัตโนมัติ
        if "stage_id" in vals and "sub_state" not in vals:
            stage = self.env["maintenance.stage"].browse(vals["stage_id"])
            if stage.done:
                vals = dict(vals, sub_state="repaired")
        vals = self._fill_signature_dates(vals)
        return super().write(vals)

    def _fill_signature_dates(self, vals):
        """ใส่วันที่ลงชื่อเมื่อบันทึกลายเซ็น และล้างวันที่เมื่อเอาลายเซ็นออก"""
        vals = dict(vals)
        today = fields.Date.context_today(self)
        for signature_field, date_field in (
            ("chief_signature", "chief_signed_on"),
            ("assignee_signature", "assignee_signed_on"),
            ("technician_signature", "technician_signed_on"),
            ("chief_comment_signature", "chief_comment_signed_on"),
            ("deputy_signature", "deputy_signed_on"),
            ("director_signature", "director_signed_on"),
            ("issuer_signature", "issuer_signed_on"),
            ("repair_done_signature", "repair_done_signed_on"),
            ("dept_head_signature", "dept_head_signed_on"),
        ):
            if signature_field not in vals or date_field in vals:
                continue
            vals[date_field] = today if vals.get(signature_field) else False
        return vals

    def reset_equipment_request(self):
        res = super().reset_equipment_request()
        self.write({"sub_state": "waiting_assessment"})
        return res

    @api.model
    def _ensure_parts_issue_picking_type(self):
        """สร้าง Operation Type เบิกอะไหล่ (รหัส PARTS) ถ้ายังไม่มี"""
        PickingType = self.env["stock.picking.type"]
        company = self.env.company
        existing = PickingType.search(
            [
                ("sequence_code", "=", "PARTS"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if existing:
            return existing

        warehouse = self.env["stock.warehouse"].search(
            [("code", "=", "PARCL"), ("company_id", "=", company.id)],
            limit=1,
        )
        if not warehouse:
            warehouse = self.env["stock.warehouse"].search(
                [("company_id", "=", company.id)],
                limit=1,
            )
        if not warehouse or not warehouse.lot_stock_id:
            return PickingType

        Location = self.env["stock.location"]
        dest = Location.search(
            [
                ("name", "=", "เบิกอะไหล่"),
                ("usage", "=", "inventory"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if not dest:
            virtual = self.env.ref(
                "stock.stock_location_locations_virtual",
                raise_if_not_found=False,
            )
            dest = Location.create(
                {
                    "name": "เบิกอะไหล่",
                    "usage": "inventory",
                    "location_id": virtual.id if virtual else False,
                    "company_id": company.id,
                }
            )

        picking_type = PickingType.with_context(lang="th_TH").create(
            {
                "name": "เบิกอะไหล่",
                "code": "outgoing",
                "sequence_code": "PARTS",
                "warehouse_id": warehouse.id,
                "company_id": company.id,
                "default_location_src_id": warehouse.lot_stock_id.id,
                "default_location_dest_id": dest.id,
                "use_existing_lots": True,
            }
        )
        picking_type.with_context(lang="en_US").write({"name": "Spare Parts Issue"})
        return picking_type

    def _get_parts_issue_picking_type(self):
        """หา Operation Type เบิกอะไหล่ ของบริษัท"""
        self.ensure_one()
        PickingType = self.env["stock.picking.type"]
        domain_company = [
            "|",
            ("company_id", "=", False),
            ("company_id", "=", self.company_id.id),
        ]
        picking_type = PickingType.search(
            domain_company + [("sequence_code", "=", "PARTS")],
            limit=1,
        )
        if not picking_type:
            picking_type = PickingType.search(
                domain_company + [("name", "=", "เบิกอะไหล่")],
                limit=1,
            )
        if not picking_type:
            raise UserError(
                _(
                    "ไม่พบ Operation Type 'เบิกอะไหล่' (รหัส PARTS)\n"
                    "กรุณาสร้างที่ Inventory → Configuration → Operations Types"
                )
            )
        return picking_type

    def action_create_parts_issue(self):
        """สร้างใบเบิกอะไหล่จากคำขอซ่อม และเปิดฟอร์มให้กรอกรายการ"""
        self.ensure_one()
        if self.archive:
            raise UserError(_("ไม่สามารถเบิกอะไหล่จากคำขอที่ถูกยกเลิกได้"))

        picking_type = self._get_parts_issue_picking_type()
        origin = self.name
        if self.equipment_id:
            origin = f"{self.name} / {self.equipment_id.display_name}"

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": origin,
                "maintenance_request_id": self.id,
                "company_id": self.company_id.id,
                "note": _("เบิกอะไหล่สำหรับคำขอซ่อม: %s", self.name),
            }
        )
        # ถ้ายังรอประเมิน/ประเมินแล้ว ให้เลื่อนเป็นรออะไหล่เมื่อเริ่มเบิก
        if self.sub_state in ("waiting_assessment", "assessed"):
            self.sub_state = "waiting_parts"

        return {
            "type": "ir.actions.act_window",
            "name": _("เบิกอะไหล่"),
            "res_model": "stock.picking",
            "res_id": picking.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_parts_pickings(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("ใบเบิกอะไหล่"),
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("maintenance_request_id", "=", self.id)],
            "context": {
                "default_maintenance_request_id": self.id,
                "default_origin": self.name,
            },
        }
        if len(self.parts_picking_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.parts_picking_ids.id,
                }
            )
        return action

    def _get_outsource_pr_product(self):
        """สินค้าบริการสำหรับจ้างซ่อมภายนอก"""
        product = self.env.ref(
            "vpk_maintenance.product_outsource_repair",
            raise_if_not_found=False,
        )
        if product:
            return product
        return self.env["product.product"].search(
            [
                ("default_code", "=", "SVC-OUTSRC-REPAIR"),
                ("purchase_ok", "=", True),
            ],
            limit=1,
        )

    def action_create_outsource_pr(self):
        """สร้าง Purchase Request สำหรับจ้างซ่อมภายนอก / ไม่มีอะไหล่"""
        self.ensure_one()
        if self.archive:
            raise UserError(_("ไม่สามารถเปิด PR จากคำขอที่ถูกยกเลิกได้"))

        allowed_codes = ("outsource", "repair_without_parts")
        if not self.assessment_result_id or self.assessment_result_id.code not in allowed_codes:
            raise UserError(
                _(
                    "ปุ่มเปิด PR ใช้เมื่อผลการประเมินเป็น "
                    "'จ้างซ่อมภายนอก' หรือ 'ซ่อมได้ไม่มีอะไหล่'"
                )
            )

        origin = self.name
        if self.equipment_id:
            origin = f"{self.name} / {self.equipment_id.display_name}"

        line_name = _("จ้างซ่อมภายนอก: %s", self.name)
        if self.equipment_id:
            line_name = _(
                "จ้างซ่อมภายนอก: %s (%s)",
                self.name,
                self.equipment_id.display_name,
            )

        description_parts = [
            _("อ้างอิงคำขอซ่อม: %s", self.name),
            _("ผลการประเมิน: %s", self.assessment_result_id.display_name),
        ]
        if self.equipment_id:
            description_parts.append(
                _("Equipment: %s", self.equipment_id.display_name)
            )
        if self.description:
            # description on maintenance.request is Html
            description_parts.append(str(self.description))

        product = self._get_outsource_pr_product()
        line_vals = {
            "name": line_name,
            "product_qty": 1.0,
            "date_required": fields.Date.context_today(self),
            "estimated_cost": 0.0,
        }
        if product:
            line_vals.update(
                {
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                }
            )

        pr_vals = {
            "origin": origin,
            "description": "\n".join(description_parts),
            "company_id": self.company_id.id,
            "requested_by": self.env.user.id,
            "maintenance_request_id": self.id,
            "line_ids": [(0, 0, line_vals)],
        }
        pr = self.env["purchase.request"].create(pr_vals)

        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Request"),
            "res_model": "purchase.request",
            "res_id": pr.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Purchase Request"),
            "res_model": "purchase.request",
            "view_mode": "list,form",
            "domain": [("maintenance_request_id", "=", self.id)],
            "context": {
                "default_maintenance_request_id": self.id,
                "default_origin": self.name,
            },
        }
        if len(self.purchase_request_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.purchase_request_ids.id,
                }
            )
        return action

    def _get_asset_waiting_disposal_sub_state(self):
        """หา Sub-Status 'รอจำหน่าย' ของ Fixed Asset"""
        sub_state = self.env.ref(
            "l10n_th_account_asset_management.asset_sub_state_open_3",
            raise_if_not_found=False,
        )
        if sub_state:
            return sub_state
        return self.env["account.asset.sub.state"].search(
            [
                ("name", "=", "รอจำหน่าย"),
                ("open", "=", True),
            ],
            limit=1,
        )

    def action_open_asset_dispose(self):
        """ตั้ง sub status คำขอซ่อม + Sub-Status บนบัตร Asset เป็นรอจำหน่าย"""
        self.ensure_one()
        if self.archive:
            raise UserError(_("ไม่สามารถแทงจำหน่ายจากคำขอที่ถูกยกเลิกได้"))
        if (
            not self.assessment_result_id
            or self.assessment_result_id.code != "not_worth_dispose"
        ):
            raise UserError(
                _(
                    "ปุ่มแทงจำหน่ายใช้เมื่อผลการประเมินเป็น "
                    "'ซ่อมไม่คุ้มแทงจำหน่าย'"
                )
            )
        if not self.equipment_id:
            raise UserError(_("กรุณาเลือก Equipment ที่เชื่อมกับทรัพย์สินก่อน"))
        asset = self.equipment_id.asset_id
        if not asset:
            raise UserError(
                _(
                    "Equipment นี้ยังไม่ได้เชื่อมกับ Fixed Asset\n"
                    "ไม่สามารถแทงจำหน่ายได้"
                )
            )

        asset_sub_state = self._get_asset_waiting_disposal_sub_state()
        if not asset_sub_state:
            raise UserError(
                _("ไม่พบ Sub-Status 'รอจำหน่าย' ในระบบ Fixed Asset")
            )
        if "asset_sub_state_id" not in asset._fields:
            raise UserError(
                _("บัตรสินทรัพย์นี้ยังไม่รองรับ Sub-Status")
            )

        asset.write({"asset_sub_state_id": asset_sub_state.id})
        self.write({"sub_state": "waiting_disposal"})
        self.message_post(
            body=_(
                "ตั้งสถานะเป็นรอจำหน่าย (คำขอซ่อม + บัตรสินทรัพย์: %s)",
                asset.display_name,
            )
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("ทรัพย์สินคงที่"),
            "res_model": "account.asset",
            "res_id": asset.id,
            "view_mode": "form",
            "target": "current",
        }

    def _mobile_plain(self, value):
        text = re.sub(r"<[^>]+>", " ", value or "")
        return re.sub(r"\s+", " ", text).strip()

    def _mobile_date(self, value):
        if not value:
            return ""
        return "%02d/%02d/%s" % (value.day, value.month, value.year + 543)

    def _mobile_state_label(self):
        labels = dict(self._fields["sub_state"]._description_selection(self.env))
        return labels.get(self.sub_state, self.sub_state or "")

    def _mobile_card(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name or "",
            "receipt_number": self.receipt_number or "",
            "sub_state": self.sub_state,
            "status": self._mobile_state_label(),
            "team": self.maintenance_team_id.name or "",
            "department": self.department_id.name or "",
            "equipment": self.equipment_id.sudo().display_name or "",
            "assignee": self.user_id.name or "",
            "request_date": self._mobile_date(self.request_date),
            "phone": self.requester_phone or "",
        }

    @api.model
    def mobile_search(self, state_filter="open", query="", limit=40, offset=0):
        company = self.env.company
        domain = [
            ("archive", "=", False),
            "|",
            ("company_id", "=", False),
            ("company_id", "=", company.id),
        ]
        open_states = [
            "waiting_assessment",
            "assessed",
            "repairing",
            "waiting_parts",
            "waiting_disposal",
        ]
        if state_filter == "open":
            domain.append(("sub_state", "in", open_states))
        elif state_filter == "with_parts":
            domain.append(("parts_move_ids.state", "=", "done"))
        elif state_filter and state_filter != "all":
            domain.append(("sub_state", "=", state_filter))
        query = (query or "").strip()
        if query:
            domain += [
                "|",
                "|",
                ("name", "ilike", query),
                ("receipt_number", "ilike", query),
                ("equipment_id.name", "ilike", query),
            ]
        requests = self.search(domain, order="write_date desc, id desc", limit=limit, offset=offset)
        return {
            "count": self.search_count(domain),
            "requests": [request._mobile_card() for request in requests],
        }

    def mobile_detail(self):
        self.ensure_one()
        card = self._mobile_card()
        parts = []
        for move in self.parts_move_ids:
            if move.state == "cancel":
                continue
            parts.append({
                "id": move.id,
                "name": move.sudo().product_id.display_name or "",
                "qty": move.product_uom_qty,
                "state": move.state,
            })
        card.update({
            "symptom": self._mobile_plain(self.description),
            "repair_detail": self.repair_detail or "",
            "machine_number": self.machine_number or "",
            "requester": self.employee_id.name or "",
            "qty": self.request_qty or 0,
            "parts_total": self.parts_total_value or 0,
            "parts": parts,
            "states": [
                {"key": key, "label": label}
                for key, label in self._fields["sub_state"]._description_selection(self.env)
            ],
        })
        return card

    def mobile_update(self, sub_state=None, repair_detail=None):
        self.ensure_one()
        if self.archive:
            raise UserError(_("ไม่สามารถแก้ไขคำขอที่ถูกยกเลิกได้"))
        vals = {}
        if sub_state:
            allowed = {key for key, _label in self._fields["sub_state"]._description_selection(self.env)}
            if sub_state not in allowed:
                raise UserError(_("สถานะไม่ถูกต้อง"))
            vals["sub_state"] = sub_state
        if repair_detail is not None:
            vals["repair_detail"] = repair_detail
        if vals:
            self.write(vals)
        return self.mobile_detail()

    def _mobile_asset_payload(self, asset):
        asset = asset.sudo()
        equipment = asset.equipment_id
        serial = asset.equipment_serial_no or ""
        model = asset.equipment_model or ""
        location = asset.equipment_location or ""
        if equipment:
            serial = serial or equipment.serial_no or ""
            model = model or equipment.model or ""
            location = location or equipment.location or ""
        return {
            "id": asset.id,
            "number": asset.number or "",
            "name": asset.name or "",
            "serial": serial or "",
            "model": model or "",
            "location": location or "",
        }

    def _mobile_asset_code(self, raw):
        text = unquote((raw or "").strip())
        if "/ai/" in text:
            text = unquote(text.split("/ai/", 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/"))
        return text.strip()

    def _mobile_asset_company_domain(self):
        return [("company_id", "in", [self.env.company.id, False])]

    @api.model
    def mobile_search_assets(self, query, limit=20):
        text = (query or "").strip()
        if len(text) < 2:
            return []
        try:
            limit_value = min(int(limit or 20), 20)
        except (TypeError, ValueError):
            limit_value = 20
        assets = self.env["account.asset"].sudo().search(
            self._mobile_asset_company_domain() + [
                ("state", "!=", "removed"),
                "|", "|", "|",
                ("number", "ilike", text),
                ("name", "ilike", text),
                ("code", "ilike", text),
                ("equipment_serial_no", "ilike", text),
            ],
            limit=limit_value,
            order="number, name, id",
        )
        return [self._mobile_asset_payload(asset) for asset in assets]

    @api.model
    def mobile_lookup_asset(self, raw):
        code = self._mobile_asset_code(raw)
        if not code:
            raise UserError(_("ไม่พบรหัสทรัพย์สินใน QR"))
        Asset = self.env["account.asset"].sudo()
        company = self._mobile_asset_company_domain()
        asset = Asset.search(company + [("number", "=", code), ("state", "!=", "removed")], limit=1)
        if not asset:
            asset = Asset.search(company + [("code", "=", code), ("state", "!=", "removed")], limit=1)
        if not asset:
            asset = Asset.search(
                company + [("equipment_serial_no", "=", code), ("state", "!=", "removed")],
                limit=1,
            )
        if not asset:
            equipment = self.env["maintenance.equipment"].sudo().search(
                company + ["|", ("asset_number", "=", code), ("serial_no", "=", code)],
                limit=1,
            )
            asset = equipment.asset_id
        if not asset:
            raise UserError(_("ไม่พบทรัพย์สิน %s") % code)
        return self._mobile_asset_payload(asset)

    def _mobile_link_asset(self, vals, asset_id):
        if not asset_id:
            return
        try:
            asset_key = int(asset_id)
        except (TypeError, ValueError) as err:
            raise UserError(_("ทรัพย์สินไม่ถูกต้อง")) from err
        asset = self.env["account.asset"].sudo().browse(asset_key).exists()
        if not asset or (asset.company_id and asset.company_id != self.env.company):
            raise UserError(_("ไม่พบทรัพย์สิน"))
        equipment = asset.equipment_id
        if not equipment:
            equipment = self.env["maintenance.equipment"].sudo().search(
                [("asset_id", "=", asset.id)], limit=1
            )
        if equipment and not asset.equipment_id:
            asset.equipment_id = equipment.id
        if not equipment:
            asset.action_create_equipment()
            equipment = asset.equipment_id
        if not equipment:
            raise UserError(_("ไม่สามารถเชื่อมทรัพย์สินกับงานซ่อมได้"))
        vals["equipment_id"] = equipment.id

    @api.model
    def mobile_form_options(self):
        departments = self.env["maintenance.department"].search([], order="name")
        employee = self.env["hr.employee"].sudo().search(
            [("user_id", "=", self.env.user.id)], limit=1
        )
        phone = ""
        if employee:
            phone = employee.work_phone or employee.mobile_phone or ""
        return {
            "departments": [{"id": department.id, "name": department.name} for department in departments],
            "phone": phone or "",
            "requester": employee.name or self.env.user.name,
        }

    @api.model
    def mobile_create(self, payload):
        name = (payload.get("name") or "").strip()
        symptom = (payload.get("symptom") or "").strip()
        if not name:
            raise UserError(_("กรุณาระบุเรื่องที่แจ้งซ่อม"))
        try:
            qty = int(payload.get("qty") or 1)
        except (TypeError, ValueError) as err:
            raise UserError(_("จำนวนไม่ถูกต้อง")) from err
        if qty < 1:
            raise UserError(_("จำนวนต้องมากกว่า 0"))
        user = self.env.user
        vals = {
            "name": name,
            "description": "<p>%s</p>" % escape(symptom) if symptom else False,
            "requester_phone": (payload.get("phone") or "").strip(),
            "request_qty": qty,
            "owner_user_id": user.id,
            "request_date": fields.Date.context_today(self),
            "maintenance_type": "corrective",
            "company_id": self.env.company.id,
        }
        department_id = payload.get("department_id")
        if department_id:
            department = self.env["maintenance.department"].browse(int(department_id)).exists()
            if not department:
                raise UserError(_("ไม่พบฝ่าย / งาน / ตึก"))
            vals["department_id"] = department.id
        employee = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
        if employee and "employee_id" in self._fields:
            vals["employee_id"] = employee.id
        self._mobile_link_asset(vals, payload.get("asset_id"))
        # owner_user_id is computed and stays empty unless the equipment is
        # assigned to this employee, so the standard "own requests" rule blocks
        # a normal user at create time. Create as superuser, then follow the
        # requester so they can read the request they just opened.
        record = self.sudo().create(vals)
        partner = user.partner_id
        if partner and partner not in record.message_partner_ids:
            record.sudo().message_subscribe(partner_ids=[partner.id])
        return record.with_user(user).mobile_detail()

    def action_open_vendor_send(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("คำร้องส่งเครื่องซ่อมบริษัท"),
            "res_model": "maintenance.vendor.send",
            "view_mode": "list,form",
            "domain": [("request_id", "=", self.id)],
            "context": self.env["maintenance.vendor.send"]._vendor_send_defaults_from_request(self),
        }
        if len(self.vendor_send_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.vendor_send_ids.id})
        return action

    def action_view_linked_asset(self):
        self.ensure_one()
        if not self.asset_id:
            raise UserError(_("ไม่พบทรัพย์สินที่เชื่อมกับ Equipment ของคำขอนี้"))
        return {
            "type": "ir.actions.act_window",
            "name": _("ทรัพย์สินคงที่"),
            "res_model": "account.asset",
            "res_id": self.asset_id.id,
            "view_mode": "form",
            "target": "current",
        }
