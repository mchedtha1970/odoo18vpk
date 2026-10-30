from odoo import fields, models


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    default_approver_ids = fields.One2many(
        comodel_name="vpk.document.studio.template.approver",
        inverse_name="template_id",
        string="ผู้อนุมัติเริ่มต้น",
        copy=True,
        help="ลำดับผู้อนุมัติเริ่มต้นเมื่อสร้างเอกสารจากแบบฟอร์มนี้ "
        "ยังปรับได้ตอนสร้างเอกสารก่อนส่งอนุมัติ",
    )

    def _vpk_approver_row_vals(self):
        self.ensure_one()
        rows = []
        for index, line in enumerate(self.default_approver_ids, start=1):
            if not line.user_id:
                continue
            is_check = bool(line.is_check)
            is_sign = bool(line.is_sign) and not is_check
            if not is_check and not is_sign:
                is_sign = True
            rows.append(
                {
                    "sequence": line.sequence or index,
                    "user_id": line.user_id.id,
                    "position": line.position or "",
                    "is_check": is_check,
                    "is_sign": is_sign,
                }
            )
        return rows

    def _vpk_approver_wizard_commands(self):
        commands = [(5, 0, 0)]
        if not self:
            return commands
        self.ensure_one()
        for vals in self._vpk_approver_row_vals():
            commands.append((0, 0, vals))
        return commands
