from odoo import fields, models


class VpkBudgetType(models.Model):
    _name = "vpk.budget.type"
    _description = "Budget Type"
    _order = "sequence, name"

    CODE_SUPPLIES = "supplies_budget"
    CODE_ASSET = "asset_budget"
    CODE_CONSTRUCTION = "construction_budget"
    CODE_PROJECT = "project_budget"

    name = fields.Char(string="ชื่อประเภทงบประมาณ", required=True, translate=True)
    code = fields.Char(string="รหัส", required=True)
    section_key = fields.Selection(
        selection=[
            ("material", "พัสดุ"),
            ("asset", "ครุภัณฑ์"),
            ("construction", "ก่อสร้าง"),
            ("project", "โครงการ"),
        ],
        string="กลุ่มแบบฟอร์ม",
        required=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string="รายละเอียด")

    _sql_constraints = [
        ("vpk_budget_type_code_uniq", "unique(code)", "Budget type code must be unique."),
    ]
