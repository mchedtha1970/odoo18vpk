# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GenerateInstallmentsWizard(models.TransientModel):
    _name = "purchase.contract.generate.installments"
    _description = "Generate Contract Installments"

    contract_id = fields.Many2one(
        comodel_name="purchase.contract",
        required=True,
        readonly=True,
    )
    amount_total = fields.Monetary(
        string="มูลค่ารวมสัญญา",
        related="contract_id.amount_total",
        readonly=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="contract_id.currency_id",
        readonly=True,
    )
    installment_count = fields.Integer(
        string="จำนวนงวด",
        required=True,
        default=1,
    )
    split_mode = fields.Selection(
        selection=[
            ("equal", "แบ่งเท่ากัน"),
            ("manual", "กำหนดเอง (สร้างงวดเปล่า)"),
        ],
        string="วิธีแบ่ง",
        default="equal",
        required=True,
    )
    clear_existing = fields.Boolean(
        string="ลบงวดเดิมก่อนสร้างใหม่",
        default=True,
    )

    @api.constrains("installment_count")
    def _check_installment_count(self):
        for wizard in self:
            if wizard.installment_count < 1:
                raise UserError(_("จำนวนงวดต้องอย่างน้อย 1 งวด"))
            if wizard.installment_count > 100:
                raise UserError(_("จำนวนงวดต้องไม่เกิน 100 งวด"))

    def action_generate(self):
        self.ensure_one()
        contract = self.contract_id
        if not contract.amount_total:
            raise UserError(_("กรุณาระบุมูลค่ารวมสัญญาก่อนสร้างงวด"))

        if self.clear_existing and contract.installment_ids:
            contract.installment_ids.unlink()

        count = self.installment_count
        total = contract.amount_total

        if self.split_mode == "equal":
            base_amount = total / count
            # ปัดเศษ 2 ตำแหน่ง แล้วเอาผลต่างไปใส่งวดสุดท้าย
            base_amount = round(base_amount, 2)
            remainder = round(total - base_amount * count, 2)
        else:
            base_amount = 0.0
            remainder = 0.0

        vals_list = []
        for i in range(1, count + 1):
            amount = base_amount
            if self.split_mode == "equal" and i == count:
                amount = base_amount + remainder
            vals_list.append(
                {
                    "contract_id": contract.id,
                    "name": _("งวดที่ %d") % i,
                    "sequence": i * 10,
                    "amount": amount,
                }
            )

        self.env["purchase.contract.installment"].create(vals_list)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("สร้างงวดสำเร็จ"),
                "message": _("สร้าง %d งวดเรียบร้อยแล้ว") % count,
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "purchase.contract",
                    "res_id": contract.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                    "target": "current",
                },
            },
        }
