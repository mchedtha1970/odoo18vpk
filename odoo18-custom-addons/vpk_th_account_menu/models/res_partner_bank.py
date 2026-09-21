# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    journal_code = fields.Char(
        string="รหัสสมุดรายวัน",
        compute="_compute_journal_code",
        store=True,
    )
    journal_name = fields.Char(
        string="สมุดรายวัน",
        compute="_compute_journal_code",
        store=True,
    )

    @api.depends("journal_id", "journal_id.code", "journal_id.name")
    def _compute_journal_code(self):
        for rec in self:
            journal = rec.journal_id[:1]
            rec.journal_code = journal.code or False
            rec.journal_name = journal.display_name or False

    @api.model
    def action_open_company_bank_accounts(self):
        company_partners = self.env["res.company"].search([]).partner_id
        list_view = self.env.ref("vpk_th_account_menu.view_hospital_bank_account_list")
        form_view = self.env.ref(
            "account.view_partner_bank_form_inherit_account", raise_if_not_found=False
        ) or self.env.ref("base.view_partner_bank_form")
        search_view = self.env.ref("base.view_partner_bank_search")
        return {
            "type": "ir.actions.act_window",
            "name": _("บัญชีธนาคารโรงพยาบาล"),
            "res_model": "res.partner.bank",
            "view_mode": "list,form",
            "views": [(list_view.id, "list"), (form_view.id, "form")],
            "search_view_id": [search_view.id],
            "domain": [("partner_id", "in", company_partners.ids)],
            "context": {
                "default_partner_id": self.env.company.partner_id.id,
                "default_allow_out_payment": True,
            },
            "help": _(
                "<p class='o_view_nocontent_smiling_face'>ยังไม่มีบัญชีธนาคารของโรงพยาบาล</p>"
                "<p>รายการนี้แสดงเฉพาะบัญชีที่ผูกกับบริษัท พร้อมรหัสสมุดรายวัน BK*</p>"
            ),
        }
