# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class MaintenanceVendorSend(models.Model):
    _name = "maintenance.vendor.send"
    _description = "คำร้องส่งเครื่องซ่อมบริษัท"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "send_date desc, id desc"

    name = fields.Char(string="เลขที่คำร้อง", copy=False, default="/", required=True)
    send_date = fields.Date(
        string="วันที่",
        default=fields.Date.context_today,
        tracking=True,
    )
    team_id = fields.Many2one(
        comodel_name="maintenance.team",
        string="แผนกช่าง",
        tracking=True,
    )
    request_id = fields.Many2one(
        comodel_name="maintenance.request",
        string="อ้างอิงเลขที่รับงาน",
        tracking=True,
    )
    equipment_id = fields.Many2one(
        comodel_name="maintenance.equipment",
        string="เครื่อง / ทรัพย์สิน",
    )
    equipment_name = fields.Char(string="ชื่อเครื่อง", required=True)
    room = fields.Char(string="ที่ห้อง")
    equipment_model = fields.Char(string="รุ่น")
    machine_number = fields.Char(string="หมายเลขเครื่อง")
    asset_number = fields.Char(string="หมายเลขครุภัณฑ์")
    building = fields.Char(string="ตึก / หน่วยงาน")
    symptom = fields.Text(string="อาการเสีย")
    vendor_id = fields.Many2one(comodel_name="res.partner", string="ศูนย์บริการ / บริษัท")
    vendor_name = fields.Char(string="ชื่อศูนย์บริการ / บริษัท")
    vendor_address = fields.Char(string="ที่อยู่")
    sign_date = fields.Date(string="ลงวันที่")
    technician_id = fields.Many2one(
        comodel_name="res.users",
        string="เจ้าหน้าที่ช่างผู้ส่งซ่อม",
        default=lambda self: self.env.user,
    )
    supervisor_id = fields.Many2one(
        comodel_name="res.users",
        string="หัวหน้างานซ่อมบำรุง",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                seq = self.env["ir.sequence"].next_by_code("vpk.maintenance.vendor.send") or "00000"
                day = fields.Date.to_date(vals.get("send_date")) or fields.Date.context_today(self)
                vals["name"] = "คำร้อง/%s/%s" % (day.year + 543, seq)
        return super().create(vals_list)

    @api.onchange("vendor_id")
    def _onchange_vendor_id(self):
        partner = self.vendor_id
        if not partner:
            return
        self.vendor_name = partner.name or ""
        address = partner.contact_address or ""
        self.vendor_address = " ".join(address.split())

    @api.onchange("equipment_id")
    def _onchange_equipment_id(self):
        equipment = self.equipment_id.sudo()
        if not equipment:
            return
        self.equipment_name = equipment.name or ""
        self.equipment_model = equipment.model or ""
        if equipment.serial_no:
            self.machine_number = equipment.serial_no
        number = equipment.asset_number or ""
        if not number and equipment.asset_id:
            number = equipment.asset_id.number or ""
        self.asset_number = number
        if equipment.location:
            self.room = equipment.location

    @api.onchange("request_id")
    def _onchange_request_id(self):
        request = self.request_id
        if not request:
            return
        equipment = request.equipment_id.sudo()
        self.team_id = request.maintenance_team_id
        self.equipment_id = equipment
        self.equipment_name = (equipment.name if equipment else "") or request.name or ""
        self.equipment_model = equipment.model or "" if equipment else ""
        self.machine_number = request.machine_number or (equipment.serial_no if equipment else "") or ""
        number = ""
        if equipment:
            number = equipment.asset_number or (equipment.asset_id.number if equipment.asset_id else "") or ""
        self.asset_number = number
        self.room = equipment.location or "" if equipment else ""
        self.building = request.department_id.name or ""
        self.symptom = request._mobile_plain(request.description)

    def _report_font_css(self):
        return self.env["maintenance.request"]._report_font_css()

    def _report_short_date(self, value):
        return self.env["maintenance.request"]._report_short_date(value)

    def _report_symptom_lines(self):
        self.ensure_one()
        lines = [line for line in (self.symptom or "").splitlines()] or [""]
        while len(lines) < 8:
            lines.append("")
        return lines[:12]

    def _vendor_send_defaults_from_request(self, request):
        equipment = request.equipment_id.sudo()
        number = ""
        if equipment:
            number = equipment.asset_number or (equipment.asset_id.number if equipment.asset_id else "") or ""
        return {
            "default_request_id": request.id,
            "default_team_id": request.maintenance_team_id.id,
            "default_equipment_id": equipment.id or False,
            "default_equipment_name": (equipment.name if equipment else "") or request.name,
            "default_equipment_model": equipment.model or "" if equipment else "",
            "default_machine_number": request.machine_number or (equipment.serial_no if equipment else "") or "",
            "default_asset_number": number,
            "default_room": equipment.location or "" if equipment else "",
            "default_building": request.department_id.name or "",
            "default_symptom": request._mobile_plain(request.description),
            "default_send_date": fields.Date.context_today(self),
        }
