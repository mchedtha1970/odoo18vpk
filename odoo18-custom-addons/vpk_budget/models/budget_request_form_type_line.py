from odoo import api, fields, models


class BudgetRequestFormTypeLine(models.Model):
    _name = "vpk.budget.request.form.type.line"
    _description = "Budget Request Form Type Line"
    _order = "sequence, id"

    form_type_id = fields.Many2one(
        comodel_name="vpk.budget.request.form.type",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    budget_type_id = fields.Many2one(
        comodel_name="vpk.budget.type",
        string="ประเภทงบประมาณ",
        required=True,
        ondelete="restrict",
    )
    line_type = fields.Char(
        related="budget_type_id.code",
        store=True,
        readonly=True,
    )
    section_key = fields.Selection(
        related="budget_type_id.section_key",
        store=True,
        readonly=True,
    )
    name = fields.Char(
        string="ชื่อแท็บ",
        help="ถ้าไม่ระบุ จะใช้ชื่อตามประเภทงบประมาณ",
    )

    _sql_constraints = [
        (
            "form_type_budget_type_unique",
            "unique(form_type_id, budget_type_id)",
            "Budget type must be unique per form type.",
        ),
    ]

    @api.model
    def _get_line_type_selection(self):
        return [
            (rec.code, rec.name)
            for rec in self.env["vpk.budget.type"].search(
                [("active", "=", True)], order="sequence, name"
            )
        ]

    @api.model
    def normalize_line_type(self, line_type):
        budget_type = self.env["vpk.budget.type"].search(
            [("code", "=", line_type)], limit=1
        )
        return budget_type.code if budget_type else line_type

    @api.model
    def line_types_for_section(self, section_key):
        return set(
            self.env["vpk.budget.type"]
            .search([("section_key", "=", section_key), ("active", "=", True)])
            .mapped("code")
        )

    @api.model
    def _budget_type_from_code(self, code):
        if not code:
            return self.env["vpk.budget.type"]
        return self.env["vpk.budget.type"].search([("code", "=", code)], limit=1)
