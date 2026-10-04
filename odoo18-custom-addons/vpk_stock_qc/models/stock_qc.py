# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockQc(models.Model):
    _name = "vpk.stock.qc"
    _description = "ตรวจคุณภาพสินค้ารับเข้า"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="เลขที่",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="ใบรับสินค้า",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    picking_state = fields.Selection(
        related="picking_id.state",
        string="สถานะใบรับ",
    )
    partner_id = fields.Many2one(
        related="picking_id.partner_id",
        string="ผู้ขาย",
        store=True,
    )
    origin = fields.Char(
        related="picking_id.origin",
        string="เอกสารอ้างอิง",
        store=True,
    )
    warehouse_id = fields.Many2one(
        related="picking_id.picking_type_id.warehouse_id",
        string="คลังรับ",
        store=True,
    )
    company_id = fields.Many2one(
        related="picking_id.company_id",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "รอตรวจ"),
            ("passed", "ผ่าน"),
            ("failed", "ไม่ผ่าน"),
        ],
        string="ผลตรวจ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ตรวจ",
        tracking=True,
        copy=False,
    )
    date_done = fields.Datetime(
        string="วันที่ตรวจ",
        copy=False,
    )
    note = fields.Text(string="หมายเหตุ")
    line_ids = fields.One2many(
        comodel_name="vpk.stock.qc.line",
        inverse_name="qc_id",
        string="รายการตรวจ",
    )
    check_ids = fields.One2many(
        comodel_name="vpk.stock.qc.check",
        inverse_name="qc_id",
        string="จุดควบคุม",
    )
    check_todo_count = fields.Integer(compute="_compute_line_result")
    line_count = fields.Integer(compute="_compute_line_result")
    fail_count = fields.Integer(compute="_compute_line_result")

    _sql_constraints = [
        (
            "picking_unique",
            "unique(picking_id)",
            "ใบรับนี้มีใบตรวจคุณภาพแล้ว",
        ),
    ]

    @api.depends("line_ids.result", "check_ids.quality_state")
    def _compute_line_result(self):
        for qc in self:
            qc.line_count = len(qc.line_ids)
            qc.fail_count = len(qc.line_ids.filtered(lambda line: line.result == "fail"))
            qc.check_todo_count = len(
                qc.check_ids.filtered(lambda check: check.quality_state == "none")
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.stock.qc") or "New"
                )
        records = super().create(vals_list)
        for record in records.filtered(lambda qc: not qc.line_ids and qc.picking_id):
            record._load_lines_from_picking()
        return records

    def _load_lines_from_picking(self):
        self.ensure_one()
        moves = self.picking_id.move_ids.filtered(
            lambda move: move.state not in ("cancel",)
        )
        self.line_ids = [
            (0, 0, {"move_id": move.id, "product_uom_qty": move.product_uom_qty})
            for move in moves
        ]

    def action_confirm(self):
        for qc in self:
            if qc.state != "draft":
                continue
            if not qc.line_ids:
                raise UserError(_("ไม่มีรายการสินค้าให้ตรวจ"))
            pending = qc.line_ids.filtered(lambda line: not line.result)
            if pending:
                raise UserError(
                    _("ยังตรวจไม่ครบ: %s")
                    % ", ".join(pending.mapped("product_id.display_name"))
                )
            failed = qc.line_ids.filtered(lambda line: line.result == "fail")
            if failed:
                qc.write({"state": "failed", "user_id": self.env.uid, "date_done": fields.Datetime.now()})
                names = ", ".join(failed.mapped("product_id.display_name"))
                qc.message_post(body=_("ไม่ผ่านการตรวจคุณภาพ: %s") % names)
                if qc.picking_id:
                    qc.picking_id.message_post(
                        body=_("ตรวจคุณภาพ %s ไม่ผ่าน: %s") % (qc.name, names)
                    )
            else:
                qc.write({
                    "state": "passed",
                    "user_id": self.env.uid,
                    "date_done": fields.Datetime.now(),
                })
                qc.message_post(body=_("ผ่านการตรวจคุณภาพทุกรายการ"))
                if qc.picking_id:
                    qc.picking_id.message_post(
                        body=_("ตรวจคุณภาพ %s ผ่านแล้ว สามารถรับเข้าคลังได้") % qc.name
                    )
        return True

    def action_reset(self):
        locked = self.filtered(lambda qc: qc.picking_state in ("done", "cancel"))
        if locked:
            raise UserError(_("ใบรับปิดแล้ว ไม่สามารถตรวจใหม่ได้"))
        self.write({"state": "draft", "date_done": False})
        self.check_ids.filtered(lambda check: check.quality_state != "none").write({
            "quality_state": "none",
            "user_id": False,
            "control_date": False,
            "measure": 0.0,
        })
        self.line_ids._refresh_result_from_checks()
        return True

    def _sync_control_checks(self):
        Point = self.env["vpk.stock.qc.point"]
        for qc in self.filtered(lambda record: record.state == "draft" and record.picking_id):
            products = qc.line_ids.product_id
            existing = {
                (check.point_id.id, check.product_id.id)
                for check in qc.check_ids
            }
            vals_list = []
            for point, product in Point._matches(products, qc.picking_id.picking_type_id):
                key = (point.id, product.id)
                if key in existing:
                    continue
                line = qc.line_ids.filtered(lambda item, product=product: item.product_id == product)[:1]
                vals_list.append({
                    "qc_id": qc.id,
                    "line_id": line.id,
                    "point_id": point.id,
                    "product_id": product.id,
                    "title": point.title,
                    "test_type": point.test_type,
                })
                existing.add(key)
            if vals_list:
                self.env["vpk.stock.qc.check"].create(vals_list)

    def action_open_check_wizard(self):
        self.ensure_one()
        self._sync_control_checks()
        checks = self.check_ids.filtered(lambda check: check.quality_state == "none")
        if not checks:
            checks = self.check_ids
        if not checks:
            raise UserError(_("ยังไม่มีจุดควบคุมสำหรับใบรับนี้ กำหนดได้ที่การกำหนดค่า → จุดควบคุมคุณภาพ"))
        return checks.action_open_wizard()

    def write(self, vals):
        if set(vals) - {"message_follower_ids", "message_ids", "activity_ids"}:
            locked = self.filtered(lambda qc: qc.state != "draft")
            allowed = {"state", "user_id", "date_done", "message_main_attachment_id"}
            if locked and (set(vals) - allowed):
                raise UserError(_("ใบที่บันทึกผลแล้ว แก้ได้หลังกดตรวจใหม่"))
        return super().write(vals)


class StockQcLine(models.Model):
    _name = "vpk.stock.qc.line"
    _description = "รายการตรวจคุณภาพสินค้ารับเข้า"
    _order = "id"

    qc_id = fields.Many2one(
        comodel_name="vpk.stock.qc",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_id = fields.Many2one(
        comodel_name="stock.move",
        string="รายการรับ",
        ondelete="restrict",
    )
    product_id = fields.Many2one(
        related="move_id.product_id",
        string="สินค้า",
        store=True,
    )
    product_uom_qty = fields.Float(
        string="จำนวนตามใบรับ",
        digits="Product Unit of Measure",
    )
    product_uom = fields.Many2one(
        related="move_id.product_uom",
        string="หน่วย",
    )
    result = fields.Selection(
        selection=[
            ("pass", "ผ่าน"),
            ("fail", "ไม่ผ่าน"),
        ],
        string="ผลการตรวจ",
    )
    note = fields.Char(string="หมายเหตุ")
    qc_state = fields.Selection(related="qc_id.state")
    check_ids = fields.One2many(
        comodel_name="vpk.stock.qc.check",
        inverse_name="line_id",
        string="จุดควบคุม",
    )

    def _refresh_result_from_checks(self):
        for line in self:
            checks = line.check_ids
            if not checks:
                continue
            if any(check.quality_state == "none" for check in checks):
                line.result = False
            elif any(check.quality_state == "fail" for check in checks):
                line.result = "fail"
            else:
                line.result = "pass"

