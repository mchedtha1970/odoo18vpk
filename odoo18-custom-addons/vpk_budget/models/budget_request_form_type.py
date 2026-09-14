from odoo import api, fields, models


class BudgetRequestFormType(models.Model):
    _name = "vpk.budget.request.form.type"
    _description = "Budget Request Form Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        string="รหัส",
        required=True,
        help="รหัสอ้างอิงแบบฟอร์มคำของบ",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    line_type_ids = fields.One2many(
        comodel_name="vpk.budget.request.form.type.line",
        inverse_name="form_type_id",
        string="Line Types",
        copy=True,
    )
    allowed_line_type_codes = fields.Char(
        compute="_compute_allowed_line_type_codes",
        store=True,
    )
    request_action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Department Request Action",
        copy=False,
        ondelete="set null",
    )
    request_menu_id = fields.Many2one(
        comodel_name="ir.ui.menu",
        string="Department Request Menu",
        copy=False,
        ondelete="set null",
    )
    summary_action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Summary Wizard Action",
        copy=False,
        ondelete="set null",
    )
    summary_menu_id = fields.Many2one(
        comodel_name="ir.ui.menu",
        string="Summary Wizard Menu",
        copy=False,
        ondelete="set null",
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "Form type code must be unique."),
    ]

    @api.depends("line_type_ids", "line_type_ids.budget_type_id", "line_type_ids.line_type")
    def _compute_allowed_line_type_codes(self):
        for rec in self:
            rec.allowed_line_type_codes = ",".join(
                rec.line_type_ids.mapped("line_type")
            )

    def has_line_type(self, *line_types):
        self.ensure_one()
        allowed = set(self.line_type_ids.mapped("line_type"))
        return bool(allowed.intersection(line_types))

    def has_section(self, section_key):
        self.ensure_one()
        return bool(
            self.line_type_ids.filtered(
                lambda line: line.budget_type_id.section_key == section_key
            )
        )

    def _get_request_menu_name(self):
        self.ensure_one()
        return (self.name or self.code or "").strip()

    def _get_primary_section(self):
        self.ensure_one()
        for section_key in ("material", "asset", "construction", "project"):
            if self.has_section(section_key):
                return section_key
        return False

    @api.model
    def _ensure_default_line_type_mappings(self):
        """Create default budget type mappings when missing (safe on upgrade)."""
        defaults = {
            "budget_request_form_type_material": "supplies_budget",
            "budget_request_form_type_asset": "asset_budget",
            "budget_request_form_type_construction": "construction_budget",
            "budget_request_form_type_project": "project_budget",
        }
        line_model = self.env["vpk.budget.request.form.type.line"]
        budget_type_model = self.env["vpk.budget.type"]
        for line in line_model.search([("budget_type_id", "=", False)]):
            if not line.line_type:
                continue
            budget_type = budget_type_model.search(
                [("code", "=", line.line_type)], limit=1
            )
            if budget_type:
                line.budget_type_id = budget_type
        for xmlid, budget_type_code in defaults.items():
            form_type = self.env.ref(f"vpk_budget.{xmlid}", raise_if_not_found=False)
            budget_type = budget_type_model.search(
                [("code", "=", budget_type_code)], limit=1
            )
            if not form_type or not budget_type:
                continue
            if line_model.search_count(
                [
                    ("form_type_id", "=", form_type.id),
                    ("budget_type_id", "=", budget_type.id),
                ]
            ):
                continue
            line_model.create(
                {
                    "form_type_id": form_type.id,
                    "budget_type_id": budget_type.id,
                    "sequence": 10,
                }
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_department_budget_request_menus()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in ("name", "code", "active", "sequence")):
            self._sync_department_budget_request_menus()
        return res

    def unlink(self):
        menus = self.request_menu_id | self.summary_menu_id
        actions = self.request_action_id | self.summary_action_id
        res = super().unlink()
        menus.sudo().exists().unlink()
        actions.sudo().exists().unlink()
        return res

    @api.model
    def _sync_department_budget_request_menus(self):
        self._sync_department_budget_request_list_menus()
        self._sync_department_budget_summary_menus()

    @api.model
    def _sync_department_budget_request_list_menus(self):
        """Create/update department budget request menus per form type."""
        parent_menu = self.env.ref(
            "vpk_budget.menu_departmental_budget_request_root",
            raise_if_not_found=False,
        )
        if not parent_menu:
            return

        self = self.sudo()
        list_view = self.env.ref(
            "vpk_budget.view_departmental_budget_request_list_by_form_type",
            raise_if_not_found=False,
        ) or self.env.ref("vpk_budget.view_departmental_budget_request_list")
        form_view = self.env.ref("vpk_budget.view_departmental_budget_request_form")
        search_view = self.env.ref("vpk_budget.view_departmental_budget_request_search")
        user_group = self.env.ref("vpk_budget.group_vpk_budget_user")

        for form_type in self.with_context(active_test=False).search(
            [], order="sequence, name, id"
        ):
            menu_name = form_type._get_request_menu_name()
            form_section = False
            for section_key in ("material", "asset", "construction", "project"):
                if form_type.has_section(section_key):
                    form_section = section_key
                    break
            action_vals = {
                "name": menu_name,
                "type": "ir.actions.act_window",
                "res_model": "departmental.budget.request",
                "view_mode": "list,form",
                "domain": (
                    f"[('form_type_id', '=', {form_type.id}), "
                    f"('requester_id', '=', uid)]"
                ),
                "context": repr(
                    {
                        "default_form_type_id": form_type.id,
                        "search_default_my_request": 1,
                        "vpk_budget_form_section": form_section,
                    }
                ),
                "search_view_id": search_view.id,
            }
            if form_type.request_action_id:
                action = form_type.request_action_id
                action.write(action_vals)
            else:
                action = self.env["ir.actions.act_window"].create(action_vals)
                form_type.request_action_id = action

            action.write(
                {
                    "view_ids": [
                        (5, 0, 0),
                        (
                            0,
                            0,
                            {
                                "view_mode": "list",
                                "view_id": list_view.id,
                                "sequence": 1,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "view_mode": "form",
                                "view_id": form_view.id,
                                "sequence": 2,
                            },
                        ),
                    ],
                }
            )

            menu_vals = {
                "name": menu_name,
                "parent_id": parent_menu.id,
                "action": f"ir.actions.act_window,{action.id}",
                "sequence": form_type.sequence + 10,
                "groups_id": [(6, 0, [user_group.id])],
                "active": form_type.active,
            }
            if form_type.request_menu_id:
                form_type.request_menu_id.write(menu_vals)
            else:
                menu = self.env["ir.ui.menu"].create(menu_vals)
                form_type.request_menu_id = menu

    @api.model
    def _sync_department_budget_summary_menus(self):
        """Create/update summary wizard menus per form type."""
        parent_menu = self.env.ref(
            "vpk_budget.menu_departmental_budget_summary_root",
            raise_if_not_found=False,
        )
        if not parent_menu:
            return

        self = self.sudo()
        wizard_action = self.env.ref(
            "vpk_budget.action_departmental_budget_summary_wizard"
        )
        wizard_view = self.env.ref(
            "vpk_budget.view_departmental_budget_summary_wizard_form"
        )
        user_group = self.env.ref("vpk_budget.group_vpk_budget_user")

        for form_type in self.with_context(active_test=False).search(
            [], order="sequence, name, id"
        ):
            menu_name = form_type._get_request_menu_name()
            action_vals = {
                "name": menu_name,
                "type": "ir.actions.act_window",
                "res_model": "departmental.budget.request.summary.wizard",
                "view_mode": "form",
                "target": "new",
                "context": repr(
                    {
                        "default_form_type_id": form_type.id,
                    }
                ),
            }
            if form_type.summary_action_id:
                action = form_type.summary_action_id
                action.write(action_vals)
            else:
                action = wizard_action.copy({"name": menu_name})
                action.write(action_vals)
                form_type.summary_action_id = action

            action.write(
                {
                    "view_ids": [
                        (5, 0, 0),
                        (
                            0,
                            0,
                            {
                                "view_mode": "form",
                                "view_id": wizard_view.id,
                                "sequence": 1,
                            },
                        ),
                    ],
                }
            )

            menu_vals = {
                "name": menu_name,
                "parent_id": parent_menu.id,
                "action": f"ir.actions.act_window,{action.id}",
                "sequence": form_type.sequence + 10,
                "groups_id": [(6, 0, [user_group.id])],
                "active": form_type.active,
            }
            if form_type.summary_menu_id:
                form_type.summary_menu_id.write(menu_vals)
            else:
                menu = self.env["ir.ui.menu"].create(menu_vals)
                form_type.summary_menu_id = menu
