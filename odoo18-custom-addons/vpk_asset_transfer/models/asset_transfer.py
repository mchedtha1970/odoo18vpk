# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VpkAssetTransfer(models.Model):
    _name = "vpk.asset.transfer"
    _description = "ใบโอนทรัพย์สิน"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "id desc"

    # Tier validation: request from draft/request/in_progress; block approved/received
    _state_from = ["draft", "request", "in_progress"]
    _state_to = ["approved", "received"]
    _cancel_state = "cancel"
    _tier_validation_manual_config = False

    name = fields.Char(
        string="เลขที่เอกสาร",
        required=True,
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
        tracking=True,
    )
    date = fields.Date(
        string="วันที่เอกสาร",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    requester_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ขอ",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    source_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานต้นทาง",
        required=True,
        tracking=True,
        check_company=True,
        default=lambda self: self.env["account.asset"]._get_warehouse_analytic_account(),
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="แสดงเฉพาะทรัพย์สินที่ถือครองโดยหน่วยงานนี้ "
        "(ค่าเริ่มต้น: คลังสินค้า)",
    )
    dest_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานปลายทาง",
        required=True,
        tracking=True,
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    note = fields.Text(string="หมายเหตุ")
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("request", "ขอโอน"),
            ("in_progress", "ดำเนินการ"),
            ("approved", "อนุมัติ"),
            ("received", "รับโอน"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    line_ids = fields.One2many(
        comodel_name="vpk.asset.transfer.line",
        inverse_name="transfer_id",
        string="รายการทรัพย์สิน",
        copy=True,
    )
    line_count = fields.Integer(compute="_compute_line_count", string="จำนวนรายการ")
    can_receive = fields.Boolean(compute="_compute_can_receive")
    approved_date = fields.Datetime(string="วันเวลาอนุมัติครบ", readonly=True, copy=False)
    receiver_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้รับโอน",
        readonly=True,
        copy=False,
        tracking=True,
    )
    received_date = fields.Datetime(string="วันเวลารับโอน", readonly=True, copy=False)

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends("state")
    def _compute_can_receive(self):
        user = self.env.user
        can_recv = user.has_group(
            "vpk_asset_transfer.group_asset_transfer_receiver"
        ) or user.has_group("vpk_asset_transfer.group_asset_transfer_manager")
        for rec in self:
            rec.can_receive = bool(rec.state == "approved" and can_recv)

    @api.constrains("source_analytic_account_id", "dest_analytic_account_id")
    def _check_different_departments(self):
        for rec in self:
            if (
                rec.source_analytic_account_id
                and rec.dest_analytic_account_id
                and rec.source_analytic_account_id == rec.dest_analytic_account_id
            ):
                raise ValidationError(
                    _("หน่วยงานต้นทางและปลายทางต้องไม่เป็นหน่วยงานเดียวกัน")
                )

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        return list(set(res + ["state", "approved_date"]))

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        return list(
            set(
                res
                + [
                    "state",
                    "receiver_id",
                    "received_date",
                    "approved_date",
                ]
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.asset.transfer")
                    or _("New")
                )
        return super().create(vals_list)

    def _check_lines_ready(self, require_source_owning=True):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มรายการทรัพย์สินอย่างน้อย 1 รายการ"))
        assets = self.line_ids.mapped("asset_id")
        if len(assets) != len(self.line_ids):
            raise UserError(_("ทุกรายการต้องระบุบัตรทรัพย์สิน"))
        if len(assets) != len(set(assets.ids)):
            raise UserError(_("มีทรัพย์สินซ้ำในรายการใบโอน"))
        if not require_source_owning:
            return
        for line in self.line_ids:
            asset = line.asset_id
            owning = asset.owning_analytic_account_id
            if not owning:
                continue
            # Allow already transferred (owning = dest) for re-entrant receive
            if owning in (
                self.source_analytic_account_id,
                self.dest_analytic_account_id,
            ):
                continue
            raise UserError(
                _(
                    "ทรัพย์สิน %(asset)s อยู่ภายใต้ %(current)s "
                    "ไม่ตรงกับหน่วยงานต้นทาง %(source)s"
                )
                % {
                    "asset": asset.display_name,
                    "current": owning.display_name,
                    "source": self.source_analytic_account_id.display_name,
                }
            )

    def _apply_ownership_transfer(self):
        """Update each asset's owning department to destination (idempotent)."""
        self.ensure_one()
        for line in self.line_ids:
            asset = line.asset_id
            from_dept = (
                line.from_analytic_account_id
                or asset.owning_analytic_account_id
                or self.source_analytic_account_id
            )
            to_dept = self.dest_analytic_account_id
            line_vals = {
                "from_analytic_account_id": from_dept.id,
                "to_analytic_account_id": to_dept.id,
            }
            if (
                line.from_analytic_account_id != from_dept
                or line.to_analytic_account_id != to_dept
            ):
                line.write(line_vals)

            if asset.owning_analytic_account_id != to_dept:
                asset.write(
                    {
                        "owning_analytic_account_id": to_dept.id,
                        "analytic_distribution": {str(to_dept.id): 100},
                    }
                )
                asset.sudo().message_post(
                    body=_(
                        "โอนหน่วยงานถือครองจาก %(source)s ไป %(dest)s ตามใบโอน "
                        "<a href=# data-oe-model='vpk.asset.transfer' "
                        "data-oe-id='%(id)s'>%(name)s</a>"
                    )
                    % {
                        "source": from_dept.display_name,
                        "dest": to_dept.display_name,
                        "id": self.id,
                        "name": self.name,
                    }
                )
            else:
                # Owning already correct — still sync Analytic Distribution
                asset._sync_analytic_distribution_from_owning()
            # Sync maintenance equipment department note if linked
            if "equipment_id" in asset._fields and asset.equipment_id:
                equipment = asset.equipment_id
                eq_vals = {}
                # Keep free-text location intact; store agency in note trail if empty tip
                if hasattr(equipment, "location") and not equipment.location:
                    eq_vals["location"] = to_dept.display_name
                if eq_vals:
                    equipment.write(eq_vals)

    def action_request(self):
        """Submit → ขอโอน + start central tier validation."""
        for transfer in self:
            if transfer.state != "draft":
                raise UserError(_("ส่งขอโอนได้เฉพาะเอกสารสถานะร่าง"))
            transfer._check_lines_ready()
            if not transfer.need_validation:
                raise UserError(
                    _(
                        "ยังไม่ได้กำหนดลำดับการอนุมัติสำหรับใบโอนทรัพย์สิน\n"
                        "กรุณาไปที่เมนู การอนุมัติตามลำดับ → กำหนดลำดับการอนุมัติ "
                        "แล้วเลือกโมเดลใบโอนทรัพย์สิน"
                    )
                )
            reviews = transfer.request_validation()
            if reviews:
                transfer._update_counter({"review_created": True})
            transfer.with_context(skip_validation_check=True).write({"state": "request"})
            transfer.sudo().message_post(body=_("ส่งขอโอนแล้ว รอการอนุมัติตามลำดับ"))
        return True

    def _sync_state_from_tier(self):
        """Map tier progress → document states; apply ownership when fully approved."""
        for transfer in self:
            transfer.invalidate_recordset(
                ["validation_status", "validated", "review_ids"]
            )
            reviews = transfer.review_ids
            if not reviews:
                continue
            if transfer.validation_status == "validated":
                just_approved = transfer.state != "approved"
                if transfer.state not in ("approved", "received"):
                    transfer.with_context(skip_validation_check=True).write(
                        {
                            "state": "approved",
                            "approved_date": fields.Datetime.now(),
                        }
                    )
                # Auto-update owning department when transfer is fully approved
                transfer._apply_ownership_transfer()
                if just_approved:
                    transfer.sudo().message_post(
                        body=_(
                            "อนุมัติครบทุกลำดับแล้ว "
                            "ระบบอัปเดตหน่วยงานถือครองไปที่ %(dest)s แล้ว — รอรับโอน"
                        )
                        % {"dest": transfer.dest_analytic_account_id.display_name}
                    )
            elif transfer.validation_status == "rejected":
                if transfer.state != "cancel":
                    transfer.with_context(skip_validation_check=True).write(
                        {"state": "cancel"}
                    )
            elif reviews.filtered(lambda r: r.status == "approved"):
                if transfer.state in ("draft", "request"):
                    transfer.with_context(skip_validation_check=True).write(
                        {"state": "in_progress"}
                    )

    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers)
        self._sync_state_from_tier()
        return res

    def _rejected_tier(self, tiers=False):
        res = super()._rejected_tier(tiers)
        self.with_context(skip_validation_check=True).write({"state": "cancel"})
        return res

    def restart_validation(self):
        res = super().restart_validation()
        to_reset = self.filtered(lambda r: r.state in ("request", "in_progress"))
        if to_reset:
            to_reset.with_context(skip_validation_check=True).write(
                {"state": "draft", "approved_date": False}
            )
        return res

    def action_receive(self):
        """Confirm receipt after approval (ownership already moved on approve)."""
        for transfer in self:
            if transfer.state != "approved":
                raise UserError(_("รับโอนได้เฉพาะเอกสารที่อนุมัติแล้ว"))
            if transfer.validation_status != "validated":
                raise UserError(_("เอกสารยังอนุมัติตามลำดับไม่ครบ"))
            if not transfer.can_receive:
                raise UserError(_("คุณไม่มีสิทธิ์รับโอน"))
            transfer._check_lines_ready(require_source_owning=False)
            # Ensure department is updated (in case approved before this change)
            transfer._apply_ownership_transfer()
            transfer.with_context(skip_validation_check=True).write(
                {
                    "state": "received",
                    "receiver_id": self.env.user.id,
                    "received_date": fields.Datetime.now(),
                }
            )
            transfer.sudo().message_post(
                body=_("%s ยืนยันรับโอนแล้ว") % self.env.user.display_name
            )
        return True

    def action_cancel(self):
        for transfer in self:
            if transfer.state == "received":
                raise UserError(
                    _("เอกสารที่รับโอนแล้วไม่สามารถยกเลิกได้ กรุณาสร้างใบโอนกลับ")
                )
            if transfer.state == "approved":
                raise UserError(
                    _("เอกสารที่อนุมัติแล้วไม่สามารถยกเลิกได้ กรุณารับโอนหรือติดต่อผู้จัดการ")
                )
            if transfer.review_ids:
                transfer.review_ids.unlink()
            transfer.with_context(skip_validation_check=True).write({"state": "cancel"})
        return True

    def action_draft(self):
        for transfer in self:
            if transfer.state != "cancel":
                raise UserError(_("ตั้งเป็นร่างได้เฉพาะเอกสารที่ยกเลิกแล้ว"))
            if transfer.review_ids:
                transfer.review_ids.unlink()
            transfer.with_context(skip_validation_check=True).write(
                {
                    "state": "draft",
                    "approved_date": False,
                    "receiver_id": False,
                    "received_date": False,
                }
            )
        return True


class VpkAssetTransferLine(models.Model):
    _name = "vpk.asset.transfer.line"
    _description = "รายการใบโอนทรัพย์สิน"
    _order = "id"

    transfer_id = fields.Many2one(
        comodel_name="vpk.asset.transfer",
        string="ใบโอน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="transfer_id.company_id",
        store=True,
        readonly=True,
    )
    source_analytic_account_id = fields.Many2one(
        related="transfer_id.source_analytic_account_id",
        string="หน่วยงานต้นทาง",
        store=True,
        readonly=True,
    )
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="ทรัพย์สิน",
        required=True,
        check_company=True,
    )
    asset_number = fields.Char(
        related="asset_id.number",
        string="หมายเลขทรัพย์สิน",
        readonly=True,
    )
    asset_code = fields.Char(
        related="asset_id.code",
        string="รหัส",
        readonly=True,
    )
    asset_name = fields.Char(
        related="asset_id.name",
        string="ชื่อทรัพย์สิน",
        readonly=True,
    )
    profile_id = fields.Many2one(
        related="asset_id.profile_id",
        string="ประเภทสินทรัพย์",
        readonly=True,
    )
    owning_analytic_account_id = fields.Many2one(
        related="asset_id.owning_analytic_account_id",
        string="หน่วยงานปัจจุบัน",
        readonly=True,
    )
    from_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานต้นทาง (ณ วันโอน)",
        readonly=True,
        copy=False,
    )
    to_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงานปลายทาง (ณ วันโอน)",
        readonly=True,
        copy=False,
    )
    note = fields.Char(string="หมายเหตุ")

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


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    @api.model
    def _get_tier_validation_model_names(self):
        res = super()._get_tier_validation_model_names()
        res.append("vpk.asset.transfer")
        return res
