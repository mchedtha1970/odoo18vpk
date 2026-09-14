from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_PR_NAME_PLACEHOLDERS = frozenset({"", "/", "New", "ใหม่"})


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.annual.plan",
        string="แผนจัดซื้อจัดจ้าง",
        tracking=True,
        index=True,
        copy=False,
    )
    is_auto_generated = fields.Boolean(
        string="สร้างโดย Gen Auto",
        default=False,
        copy=False,
    )
    auto_gen_source = fields.Selection(
        selection=[
            ("orderpoint", "จุดสั่งซื้อ (Min-Max)"),
            ("contract_expiry", "สัญญาใกล้หมดอายุ"),
            ("manual", "สร้างด้วยตนเอง"),
        ],
        string="แหล่งที่มา Auto",
        default="manual",
        copy=False,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        domain=(
            "[('code', '=', 'incoming'),"
            " '|', ('warehouse_id', '=', False),"
            " ('warehouse_id.company_id', '=', company_id)]"
        ),
    )
    name_assignment = fields.Selection(
        selection=[
            ("auto", "อัตโนมัติ (จากระบบ)"),
            ("manual", "กำหนดเอง (Manual)"),
        ],
        string="รูปแบบเลขที่",
        default="auto",
        required=True,
        copy=False,
        help="ระบบออกเลขที่ใบขอซื้อจาก Sequence อัตโนมัติเมื่อบันทึก",
    )
    is_name_editable = fields.Boolean(default=False, copy=False)

    @api.model
    def _default_name_assignment(self):
        return "auto"

    @api.model
    def _get_pr_name_system_mode(self):
        return "auto"

    @api.model
    def _is_pr_name_placeholder(self, name):
        if not name:
            return True
        name = str(name).strip()
        return name in _PR_NAME_PLACEHOLDERS or name == _("New")

    @api.model
    def _vpk_next_pr_name(self, vals=None):
        vals = vals or {}
        sequence_date = vals.get("date_start") or fields.Date.context_today(self)
        company_id = vals.get("company_id") or self.env.company.id
        name = (
            self.env["ir.sequence"]
            .sudo()
            .with_company(company_id)
            .next_by_code("purchase.request", sequence_date=sequence_date)
        )
        if not name:
            raise UserError(
                _("ไม่พบ Sequence ใบขอซื้อ (purchase.request) กรุณาติดต่อผู้ดูแลระบบ")
            )
        return name

    @api.model
    def _get_default_name(self):
        return self._vpk_next_pr_name()

    def _vpk_assign_placeholder_names(self):
        placeholders = self.filtered(lambda rec: rec._is_pr_name_placeholder(rec.name))
        for rec in placeholders:
            rec.with_context(skip_vpk_pr_name=True).write(
                {
                    "name": rec._vpk_next_pr_name(
                        {
                            "date_start": rec.date_start,
                            "company_id": rec.company_id.id,
                        }
                    )
                }
            )

    @api.model
    def _vpk_force_pr_auto_name(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "vpk_procurement_auto_pr.pr_name_assignment", "auto"
        )
        recs = self.with_context(active_test=False).search(
            [
                "|",
                ("name_assignment", "!=", "auto"),
                ("is_name_editable", "=", True),
            ]
        )
        if recs:
            recs.with_context(skip_vpk_pr_name=True).write(
                {"name_assignment": "auto", "is_name_editable": False}
            )
        pending = self.with_context(active_test=False).search([])
        pending._vpk_assign_placeholder_names()

    @api.constrains("name", "company_id")
    def _check_pr_name_unique(self):
        for rec in self:
            if rec._is_pr_name_placeholder(rec.name):
                continue
            duplicate = self.search(
                [
                    ("id", "!=", rec.id),
                    ("name", "=", rec.name),
                    ("company_id", "=", rec.company_id.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("เลขที่ใบขอซื้อ/จ้าง '%s' ซ้ำกับเอกสารอื่นในระบบ")
                    % rec.name
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name_assignment"] = "auto"
            vals["is_name_editable"] = False
            if self._is_pr_name_placeholder(vals.get("name")):
                vals["name"] = self._vpk_next_pr_name(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "name_assignment" in vals:
            vals["name_assignment"] = "auto"
        if "is_name_editable" in vals:
            vals["is_name_editable"] = False
        if "name" in vals and self._is_pr_name_placeholder(vals.get("name")):
            vals.pop("name")
        res = super().write(vals)
        if not self.env.context.get("skip_vpk_pr_name"):
            self._vpk_assign_placeholder_names()
        return res

    def copy(self, default=None):
        default = dict(default or {})
        default["name_assignment"] = "auto"
        default["is_name_editable"] = False
        return super().copy(default)


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    procurement_plan_line_id = fields.Many2one(
        comodel_name="procurement.annual.plan.line",
        string="รายการแผนจัดซื้อ",
        copy=False,
        index=True,
    )
