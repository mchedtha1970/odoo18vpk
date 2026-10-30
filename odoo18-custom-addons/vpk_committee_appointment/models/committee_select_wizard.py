from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProcurementCommitteeSelectWizard(models.TransientModel):
    _name = "procurement.committee.select.wizard"
    _description = "เลือกกรรมการหลายคน"

    request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="ใบขอซื้อ",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    committee_type = fields.Selection(
        selection=lambda self: self.env["procurement.committee"]
        ._fields["committee_type"]
        ._description_selection(self.env),
        string="คณะกรรมการ",
        required=True,
        readonly=True,
    )
    approve_role = fields.Selection(
        selection=lambda self: self.env["procurement.committee"]
        ._fields["approve_role"]
        ._description_selection(self.env),
        string="บทบาท",
        required=True,
        default="committee",
    )
    first_as_chairman = fields.Boolean(
        string="คนแรกเป็นประธาน",
        help="ถ้าคณะนี้ยังไม่มีประธาน ให้คนแรกที่เลือกเป็นประธาน คนที่เหลือใช้บทบาทที่ตั้งไว้",
    )
    existing_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        compute="_compute_existing_employee_ids",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="กรรมการที่เลือก",
    )

    @api.depends("request_id", "committee_type")
    def _compute_existing_employee_ids(self):
        Committee = self.env["procurement.committee"]
        for wizard in self:
            wizard.existing_employee_ids = Committee.search(
                [
                    ("request_id", "=", wizard.request_id.id),
                    ("committee_type", "=", wizard.committee_type),
                ]
            ).mapped("employee_id")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        request_id = values.get("request_id")
        committee_type = values.get("committee_type")
        if request_id and committee_type:
            has_chairman = self.env["procurement.committee"].search_count(
                [
                    ("request_id", "=", request_id),
                    ("committee_type", "=", committee_type),
                    ("approve_role", "=", "chairman"),
                ]
            )
            values["first_as_chairman"] = not has_chairman
        return values

    def action_add_members(self):
        self.ensure_one()
        employees = self.employee_ids - self.existing_employee_ids
        if not employees:
            raise UserError(_("กรุณาเลือกกรรมการอย่างน้อย 1 คน"))
        vals_list = []
        for index, employee in enumerate(employees):
            role = self.approve_role
            if index == 0 and self.first_as_chairman:
                role = "chairman"
            vals_list.append(
                {
                    "request_id": self.request_id.id,
                    "committee_type": self.committee_type,
                    "employee_id": employee.id,
                    "name": employee.display_name,
                    "approve_role": role,
                }
            )
        self.env["procurement.committee"].create(vals_list)
        return {"type": "ir.actions.act_window_close"}
