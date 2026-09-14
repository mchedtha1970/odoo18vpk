# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    def write(self, vals):
        # เมื่อปิดงาน (stage done) ให้สถานะดำเนินการเป็นซ่อมเสร็จสิ้นโดยอัตโนมัติ
        if "stage_id" in vals and "sub_state" not in vals:
            stage = self.env["maintenance.stage"].browse(vals["stage_id"])
            if stage.done:
                vals = dict(vals, sub_state="repaired")
        return super().write(vals)

    def reset_equipment_request(self):
        res = super().reset_equipment_request()
        self.write({"sub_state": "waiting_assessment"})
        return res

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
