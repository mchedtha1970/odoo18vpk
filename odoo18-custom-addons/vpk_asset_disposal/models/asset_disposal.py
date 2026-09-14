# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VpkAssetDisposal(models.Model):
    _name = "vpk.asset.disposal"
    _description = "ใบขออนุมัติจำหน่ายทรัพย์สิน"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "id desc"

    _state_from = ["draft", "request", "in_progress"]
    _state_to = ["approved", "done"]
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
    reason = fields.Text(
        string="เหตุผลการจำหน่าย",
        tracking=True,
    )
    disposal_method = fields.Selection(
        selection=[
            ("auction", "ขายทอดตลาด"),
            ("sale", "ขาย"),
            ("trade_in", "แลกเปลี่ยน/เทิร์น"),
            ("transfer", "โอนให้หน่วยงานอื่น"),
            ("donation", "บริจาค"),
            ("destroy", "ทำลาย"),
            ("lost", "สูญหาย/ชำรุดสิ้นสภาพ"),
            ("other", "อื่น ๆ"),
        ],
        string="วิธีการตัดจำหน่าย",
        default="other",
        required=True,
        tracking=True,
    )
    retirement_date = fields.Date(
        string="วันที่ตัดจำหน่าย",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    approval_reference = fields.Char(
        string="เลขที่หนังสือ/มติอนุมัติ",
        tracking=True,
        index=True,
    )
    buyer_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้ซื้อ/ผู้รับโอน",
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    total_purchase_value = fields.Monetary(
        string="มูลค่าซื้อรวม",
        compute="_compute_retirement_totals",
        currency_field="currency_id",
    )
    total_residual_value = fields.Monetary(
        string="มูลค่าคงเหลือรวม",
        compute="_compute_retirement_totals",
        currency_field="currency_id",
    )
    total_proceeds_amount = fields.Monetary(
        string="มูลค่าที่ได้รับรวม",
        compute="_compute_retirement_totals",
        currency_field="currency_id",
    )
    total_gain_loss_amount = fields.Monetary(
        string="กำไร/(ขาดทุน) จากการจำหน่าย",
        compute="_compute_retirement_totals",
        currency_field="currency_id",
    )
    account_sale_id = fields.Many2one(
        comodel_name="account.account",
        string="บัญชีรับเงินจากการจำหน่าย",
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
        check_company=True,
        default=lambda self: self._get_default_disposal_account("sale"),
    )
    account_gain_id = fields.Many2one(
        comodel_name="account.account",
        string="บัญชีกำไรจากการจำหน่าย",
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
        check_company=True,
        default=lambda self: self._get_default_disposal_account("gain"),
    )
    account_loss_id = fields.Many2one(
        comodel_name="account.account",
        string="บัญชีขาดทุนจากการจำหน่าย",
        domain="[('company_ids', 'in', company_id), ('deprecated', '=', False)]",
        check_company=True,
        default=lambda self: self._get_default_disposal_account("loss"),
    )
    removal_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="vpk_asset_disposal_removal_move_rel",
        column1="disposal_id",
        column2="move_id",
        string="รายการบัญชีตัดจำหน่าย",
        copy=False,
        readonly=True,
    )
    removal_move_count = fields.Integer(
        string="จำนวนรายการบัญชี",
        compute="_compute_removal_summary",
    )
    removed_asset_count = fields.Integer(
        string="จำนวนสินทรัพย์ที่ตัดแล้ว",
        compute="_compute_removal_summary",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="vpk_asset_disposal_attachment_rel",
        column1="disposal_id",
        column2="attachment_id",
        string="เอกสารประกอบการตัดจำหน่าย",
    )
    note = fields.Text(string="หมายเหตุ")
    state = fields.Selection(
        selection=[
            ("draft", "ร่าง"),
            ("request", "ขออนุมัติ"),
            ("in_progress", "ดำเนินการ"),
            ("approved", "อนุมัติ"),
            ("done", "เสร็จสิ้น"),
            ("cancel", "ยกเลิก"),
        ],
        string="สถานะ",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    line_ids = fields.One2many(
        comodel_name="vpk.asset.disposal.line",
        inverse_name="disposal_id",
        string="รายการทรัพย์สิน",
        copy=True,
    )
    line_count = fields.Integer(compute="_compute_line_count", string="จำนวนรายการ")
    approved_date = fields.Datetime(
        string="วันเวลาอนุมัติครบ",
        readonly=True,
        copy=False,
    )
    done_date = fields.Datetime(
        string="วันเวลาเสร็จสิ้น",
        readonly=True,
        copy=False,
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.model
    def _get_default_disposal_account(self, account_kind):
        account_codes = {
            "sale": "4205010110.101",
            "gain": "4205010110.101",
            "loss": "5203010119.101",
        }
        return self.env["account.account"].search(
            [
                ("code", "=", account_codes[account_kind]),
                ("company_ids", "in", self.env.company.id),
                ("deprecated", "=", False),
            ],
            limit=1,
        )

    @api.depends(
        "line_ids.purchase_value",
        "line_ids.value_residual",
        "line_ids.proceeds_amount",
    )
    def _compute_retirement_totals(self):
        for disposal in self:
            disposal.total_purchase_value = sum(
                disposal.line_ids.mapped("purchase_value")
            )
            disposal.total_residual_value = sum(
                disposal.line_ids.mapped("value_residual")
            )
            disposal.total_proceeds_amount = sum(
                disposal.line_ids.mapped("proceeds_amount")
            )
            disposal.total_gain_loss_amount = (
                disposal.total_proceeds_amount
                - disposal.total_residual_value
            )

    @api.depends("removal_move_ids", "line_ids.asset_id.state")
    def _compute_removal_summary(self):
        for disposal in self:
            disposal.removal_move_count = len(disposal.removal_move_ids)
            disposal.removed_asset_count = len(
                disposal.line_ids.filtered(
                    lambda line: line.asset_id.state == "removed"
                )
            )

    @api.model
    def _get_waiting_disposal_sub_state(self):
        sub_state = self.env.ref(
            "l10n_th_account_asset_management.asset_sub_state_open_3",
            raise_if_not_found=False,
        )
        if sub_state:
            return sub_state
        return self.env["account.asset.sub.state"].search(
            [("name", "=", "รอจำหน่าย"), ("open", "=", True)],
            limit=1,
        )

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        return list(set(res + ["state", "approved_date", "done_date"]))

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        return list(
            set(
                res
                + [
                    "state",
                    "approved_date",
                    "done_date",
                    "account_sale_id",
                    "account_gain_id",
                    "account_loss_id",
                    "removal_move_ids",
                ]
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("vpk.asset.disposal")
                    or _("New")
                )
        return super().create(vals_list)

    def _check_lines_ready(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_("กรุณาระบุเหตุผลการจำหน่าย"))
        if not self.retirement_date:
            raise UserError(_("กรุณาระบุวันที่ตัดจำหน่าย"))
        if not self.line_ids:
            raise UserError(_("กรุณาเพิ่มรายการทรัพย์สินอย่างน้อย 1 รายการ"))
        assets = self.line_ids.mapped("asset_id")
        if len(assets) != len(self.line_ids):
            raise UserError(_("ทุกรายการต้องระบุบัตรทรัพย์สิน"))
        if len(assets) != len(set(assets.ids)):
            raise UserError(_("มีทรัพย์สินซ้ำในรายการใบขออนุมัติจำหน่าย"))

        waiting = self._get_waiting_disposal_sub_state()
        for line in self.line_ids:
            asset = line.asset_id
            if asset.state == "removed":
                raise UserError(
                    _("ทรัพย์สิน %s ถูกจำหน่ายออกจากระบบแล้ว")
                    % asset.display_name
                )
            if waiting and asset.asset_sub_state_id != waiting:
                raise UserError(
                    _(
                        "ทรัพย์สิน %(asset)s ไม่ได้อยู่สถานะย่อย 'รอจำหน่าย' "
                        "(ปัจจุบัน: %(current)s)"
                    )
                    % {
                        "asset": asset.display_name,
                        "current": asset.asset_sub_state_id.display_name
                        or "-",
                    }
                )

    def action_load_waiting_disposal_assets(self):
        """ดึงทรัพย์สินที่ Sub-Status = รอจำหน่าย มาใส่ในรายการ"""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("ดึงรายการได้เฉพาะเอกสารสถานะร่าง"))

        waiting = self._get_waiting_disposal_sub_state()
        if not waiting:
            raise UserError(_("ไม่พบ Sub-Status 'รอจำหน่าย' ในระบบ"))

        existing_asset_ids = set(self.line_ids.mapped("asset_id").ids)
        domain = [
            ("company_id", "=", self.company_id.id),
            ("state", "!=", "removed"),
            ("asset_sub_state_id", "=", waiting.id),
        ]
        assets = self.env["account.asset"].search(domain, order="number, id")
        to_add = assets.filtered(lambda a: a.id not in existing_asset_ids)
        if not to_add:
            raise UserError(
                _("ไม่พบทรัพย์สินสถานะย่อย 'รอจำหน่าย' ที่ยังไม่ได้อยู่ในรายการนี้")
            )

        self.write(
            {
                "line_ids": [
                    (0, 0, {"asset_id": asset.id}) for asset in to_add
                ]
            }
        )
        self.message_post(
            body=_("ดึงรายการรอจำหน่ายเพิ่ม %s รายการ") % len(to_add)
        )
        return True

    def action_request(self):
        """ส่งขออนุมัติ + เริ่ม tier validation"""
        for disposal in self:
            if disposal.state != "draft":
                raise UserError(_("ส่งขออนุมัติได้เฉพาะเอกสารสถานะร่าง"))
            disposal._check_lines_ready()
            if not disposal.need_validation:
                raise UserError(
                    _(
                        "ยังไม่ได้กำหนดลำดับการอนุมัติสำหรับใบขออนุมัติจำหน่าย\n"
                        "กรุณาไปที่เมนู การอนุมัติตามลำดับ → กำหนดลำดับการอนุมัติ"
                    )
                )
            reviews = disposal.request_validation()
            if reviews:
                disposal._update_counter({"review_created": True})
            disposal.with_context(skip_validation_check=True).write(
                {"state": "request"}
            )
            disposal.sudo().message_post(
                body=_("ส่งขออนุมัติจำหน่ายแล้ว รอการอนุมัติตามลำดับ")
            )
        return True

    def _sync_state_from_tier(self):
        for disposal in self:
            disposal.invalidate_recordset(
                ["validation_status", "validated", "review_ids"]
            )
            reviews = disposal.review_ids
            if not reviews:
                continue
            if disposal.validation_status == "validated":
                if disposal.state not in ("approved", "done"):
                    disposal.with_context(skip_validation_check=True).write(
                        {
                            "state": "approved",
                            "approved_date": fields.Datetime.now(),
                        }
                    )
                    disposal.sudo().message_post(
                        body=_("อนุมัติครบทุกลำดับแล้ว — พร้อมดำเนินการจำหน่าย")
                    )
            elif disposal.validation_status == "rejected":
                if disposal.state != "cancel":
                    disposal.with_context(skip_validation_check=True).write(
                        {"state": "cancel"}
                    )
            elif reviews.filtered(lambda r: r.status == "approved"):
                if disposal.state in ("draft", "request"):
                    disposal.with_context(skip_validation_check=True).write(
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

    def action_done(self):
        """Create standard removal entries and mark every asset as Removed."""
        for disposal in self:
            if disposal.state != "approved":
                raise UserError(_("ทำเสร็จสิ้นได้เฉพาะเอกสารที่อนุมัติแล้ว"))
            if disposal.validation_status != "validated":
                raise UserError(_("เอกสารยังอนุมัติตามลำดับไม่ครบ"))
            disposal._check_lines_ready()
            if not disposal.account_gain_id or not disposal.account_loss_id:
                raise UserError(
                    _(
                        "กรุณาระบุบัญชีกำไรและบัญชีขาดทุนจากการจำหน่าย"
                    )
                )

            removal_move_ids = []
            for line in disposal.line_ids:
                asset = line.asset_id
                if asset.state == "removed":
                    continue
                if asset.state not in ("open", "close"):
                    raise UserError(
                        _(
                            "สินทรัพย์ %(asset)s ต้องอยู่สถานะ Running หรือ Close "
                            "ก่อนตัดจำหน่าย"
                        )
                        % {"asset": asset.display_name}
                    )
                if line.proceeds_amount and not disposal.account_sale_id:
                    raise UserError(
                        _(
                            "กรุณาระบุบัญชีรับเงินจากการจำหน่าย "
                            "เนื่องจากมีมูลค่าที่ได้รับ"
                        )
                    )
                posted_lines = asset.depreciation_line_ids.filtered(
                    lambda depreciation: depreciation.type == "depreciate"
                    and depreciation.move_check
                )
                last_posted_date = (
                    max(posted_lines.mapped("line_date"))
                    if posted_lines
                    else False
                )
                if (
                    last_posted_date
                    and disposal.retirement_date <= last_posted_date
                ):
                    raise UserError(
                        _(
                            "วันที่ตัดจำหน่ายของ %(asset)s ต้องหลังวันที่ลงบัญชี"
                            "ค่าเสื่อมราคาล่าสุด %(date)s"
                        )
                        % {
                            "asset": asset.display_name,
                            "date": last_posted_date,
                        }
                    )

                action = asset.remove()
                context = action.get("context", {})
                Wizard = self.env["account.asset.remove"].with_context(
                    **context
                )
                values = Wizard.default_get(list(Wizard._fields))
                values.update(
                    {
                        "date_remove": disposal.retirement_date,
                        "sale_value": line.proceeds_amount,
                        "account_sale_id": disposal.account_sale_id.id,
                        "account_plus_value_id": disposal.account_gain_id.id,
                        "account_min_value_id": disposal.account_loss_id.id,
                        "posting_regime": "gain_loss_on_sale",
                        "note": _(
                            "ตัดจำหน่ายตามเอกสาร %(document)s "
                            "(%(reference)s)"
                        )
                        % {
                            "document": disposal.name,
                            "reference": disposal.approval_reference or "-",
                        },
                    }
                )
                result = Wizard.create(values).remove()
                move_domain = result.get("domain", [])
                move_ids = [
                    value
                    for field_name, operator, value in move_domain
                    if field_name == "id" and operator == "="
                ]
                removal_move_ids.extend(move_ids)

            disposal.with_context(skip_validation_check=True).write(
                {
                    "state": "done",
                    "done_date": fields.Datetime.now(),
                    "removal_move_ids": [
                        (6, 0, removal_move_ids)
                    ],
                }
            )
            for line in disposal.line_ids:
                asset = line.asset_id
                asset.sudo().message_post(
                    body=_(
                        "อนุมัติจำหน่ายตามเอกสาร "
                        "<a href=# data-oe-model='vpk.asset.disposal' "
                        "data-oe-id='%(id)s'>%(name)s</a>"
                    )
                    % {"id": disposal.id, "name": disposal.name}
                )
            disposal.sudo().message_post(body=_("ปิดงานใบขออนุมัติจำหน่ายแล้ว"))
        return True

    def action_view_removal_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการบัญชีตัดจำหน่าย"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.removal_move_ids.ids)],
        }

    def action_cancel(self):
        for disposal in self:
            if disposal.state in ("done", "approved"):
                raise UserError(
                    _("เอกสารที่อนุมัติ/เสร็จสิ้นแล้วไม่สามารถยกเลิกได้")
                )
            if disposal.review_ids:
                disposal.review_ids.unlink()
            disposal.with_context(skip_validation_check=True).write(
                {"state": "cancel"}
            )
        return True

    def action_draft(self):
        for disposal in self:
            if disposal.state not in (
                "cancel",
                "request",
                "in_progress",
                "approved",
            ):
                raise UserError(
                    _(
                        "กลับเป็นร่างได้เฉพาะเอกสารที่ยกเลิก "
                        "อยู่ระหว่างอนุมัติ หรืออนุมัติแล้ว"
                    )
                )
            if disposal.removal_move_ids or disposal.removed_asset_count:
                raise UserError(
                    _(
                        "ไม่สามารถกลับเป็นร่างได้ เนื่องจากมีการสร้างรายการบัญชี"
                        "หรือตัดสินทรัพย์ออกจากทะเบียนแล้ว"
                    )
                )
            if disposal.review_ids:
                disposal.review_ids.unlink()
            disposal.with_context(skip_validation_check=True).write(
                {
                    "state": "draft",
                    "approved_date": False,
                    "done_date": False,
                }
            )
            disposal.sudo().message_post(
                body=_(
                    "ผู้ใช้ %(user)s นำเอกสารกลับเป็นร่างเพื่อแก้ไข"
                )
                % {"user": self.env.user.display_name}
            )
        return True


class VpkAssetDisposalLine(models.Model):
    _name = "vpk.asset.disposal.line"
    _description = "รายการใบขออนุมัติจำหน่ายทรัพย์สิน"
    _order = "id"

    disposal_id = fields.Many2one(
        comodel_name="vpk.asset.disposal",
        string="ใบขออนุมัติจำหน่าย",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="disposal_id.company_id",
        store=True,
        readonly=True,
    )
    asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="ทรัพย์สิน",
        required=True,
        check_company=True,
        domain="[('company_id', '=', company_id), ('state', '!=', 'removed')]",
        index=True,
    )
    asset_number = fields.Char(
        related="asset_id.number",
        string="เลขที่ทรัพย์สิน",
        store=True,
        readonly=True,
    )
    asset_code = fields.Char(
        related="asset_id.code",
        string="รหัส",
        store=True,
        readonly=True,
    )
    asset_name = fields.Char(
        related="asset_id.name",
        string="ชื่อทรัพย์สิน",
        store=True,
        readonly=True,
    )
    profile_id = fields.Many2one(
        related="asset_id.profile_id",
        string="ประเภท",
        store=True,
        readonly=True,
    )
    owning_analytic_account_id = fields.Many2one(
        related="asset_id.owning_analytic_account_id",
        string="หน่วยงานถือครอง",
        store=True,
        readonly=True,
    )
    asset_sub_state_id = fields.Many2one(
        related="asset_id.asset_sub_state_id",
        string="Sub-Status",
        store=True,
        readonly=True,
    )
    purchase_value = fields.Monetary(
        related="asset_id.purchase_value",
        string="มูลค่าซื้อ",
        store=True,
        readonly=True,
        currency_field="company_currency_id",
    )
    method_number = fields.Integer(
        related="asset_id.method_number",
        string="อายุการใช้งาน (ปี)",
        store=True,
        readonly=True,
    )
    date_start = fields.Date(
        related="asset_id.date_start",
        string="วันที่เริ่มต้น",
        store=True,
        readonly=True,
    )
    years_in_use = fields.Integer(
        string="ใช้มาแล้วกี่ปี",
        compute="_compute_years_in_use",
    )
    value_residual = fields.Monetary(
        related="asset_id.value_residual",
        string="มูลค่าคงเหลือ",
        store=True,
        readonly=True,
        currency_field="company_currency_id",
    )
    repair_total_value = fields.Monetary(
        string="มูลค่าซ่อมทั้งหมด",
        compute="_compute_repair_total_value",
        currency_field="company_currency_id",
    )
    proceeds_amount = fields.Monetary(
        string="มูลค่าที่ได้รับ",
        currency_field="company_currency_id",
        help="ราคาขายทอดตลาด ราคาขาย หรือมูลค่าที่ได้รับจากการจำหน่ายรายการนี้",
    )
    gain_loss_amount = fields.Monetary(
        string="กำไร/(ขาดทุน)",
        compute="_compute_gain_loss_amount",
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )
    note = fields.Char(string="หมายเหตุ")

    _sql_constraints = [
        (
            "disposal_asset_uniq",
            "unique(disposal_id, asset_id)",
            "ทรัพย์สินซ้ำในเอกสารเดียวกันไม่ได้",
        ),
    ]

    @api.depends("date_start", "asset_id.date_start")
    def _compute_years_in_use(self):
        today = fields.Date.context_today(self)
        for line in self:
            start = line.date_start or (
                line.asset_id.date_start if line.asset_id else False
            )
            if not start:
                line.years_in_use = 0
                continue
            years = today.year - start.year
            if (today.month, today.day) < (start.month, start.day):
                years -= 1
            line.years_in_use = max(years, 0)

    @api.depends("asset_id", "asset_id.equipment_id")
    def _compute_repair_total_value(self):
        """มูลค่าอะไหล่ที่เบิกซ่อมทั้งหมดของทรัพย์สิน (จากคำขอซ่อมทั้งหมด)"""
        MaintenanceRequest = self.env["maintenance.request"]
        has_parts = "parts_total_value" in MaintenanceRequest._fields
        for line in self:
            equipment = (
                line.asset_id.equipment_id
                if line.asset_id and "equipment_id" in line.asset_id._fields
                else False
            )
            if not equipment or not has_parts:
                line.repair_total_value = 0.0
                continue
            requests = MaintenanceRequest.search(
                [
                    ("equipment_id", "=", equipment.id),
                    ("archive", "=", False),
                ]
            )
            line.repair_total_value = sum(requests.mapped("parts_total_value"))

    @api.depends("proceeds_amount", "value_residual")
    def _compute_gain_loss_amount(self):
        for line in self:
            line.gain_loss_amount = (
                line.proceeds_amount - line.value_residual
            )

    def action_open_asset(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ทรัพย์สิน"),
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
        res.append("vpk.asset.disposal")
        return res
