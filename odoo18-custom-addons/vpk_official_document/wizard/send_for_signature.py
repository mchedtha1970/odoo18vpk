# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class OfficialDocumentSendWizard(models.TransientModel):
    _name = "vpk.official.document.send.wizard"
    _description = "ส่งเอกสารเพื่อลงนาม"

    document_id = fields.Many2one(
        comodel_name="vpk.official.document",
        string="เอกสาร",
        required=True,
        readonly=True,
    )
    skip_approval = fields.Boolean(
        string="ข้ามการอนุมัติ (ทดสอบ)",
        help="ถือว่าเอกสารลงนามครบแล้ว โดยไม่เข้ากล่องอนุมัติ ใช้ทดสอบเดินเอกสารต่อ",
    )

    def action_confirm(self):
        self.ensure_one()
        document = self.document_id
        if self.skip_approval:
            document.action_skip_approval_for_test()
            return {"type": "ir.actions.act_window_close"}
        if document.document_type == "award_approval":
            egp = self.env["purchase.requisition.egp.document"].sudo().search(
                [("official_document_id", "=", document.id)],
                limit=1,
            )
            report = egp.award_report_id if egp else False
            if report and report.state == "draft":
                report.sudo().action_submit()
        document.action_send_for_signature()
        return {"type": "ir.actions.act_window_close"}
