from odoo import _, fields, models
from odoo.exceptions import UserError


class VpkBudgetRequestLoadWizard(models.TransientModel):
    _name = "vpk.budget.request.load.wizard"
    _description = "Load Budget Request Lines by Category"

    request_id = fields.Many2one(
        comodel_name="departmental.budget.request",
        required=True,
        readonly=True,
    )
    target = fields.Selection(
        selection=[
            ("material", "วัสดุ"),
            ("asset", "ครุภัณฑ์"),
        ],
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(related="request_id.company_id")
    form_section_key = fields.Char(related="request_id.form_section_key")
    budget_post_ids = fields.Many2many(
        comodel_name="account.budget.post",
        relation="vpk_budget_request_load_wizard_post_rel",
        column1="wizard_id",
        column2="budget_post_id",
        string="หมวดงบประมาณ",
        domain=(
            "[('company_id', 'in', [False, company_id]),"
            " '|', ('section_key', '=', False), ('section_key', '=', form_section_key)]"
        ),
    )

    def action_load(self):
        self.ensure_one()
        if not self.budget_post_ids:
            raise UserError(_("กรุณาเลือกหมวดงบประมาณ"))
        request = self.request_id
        if self.target == "asset":
            return request.action_load_asset_category_products(self.budget_post_ids)
        return request.action_load_material_category_products(self.budget_post_ids)
