# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountBudgetPost(models.Model):
    _inherit = "account.budget.post"

    account_code = fields.Char(
        string="บัญชี",
        compute="_compute_account_code",
        store=True,
    )
    section_key = fields.Selection(
        selection=[
            ("material", "วัสดุ"),
            ("asset", "ครุภัณฑ์"),
            ("construction", "ก่อสร้าง"),
            ("project", "โครงการ"),
        ],
        string="กลุ่มแบบฟอร์ม",
        compute="_compute_section_key",
        store=True,
        readonly=False,
        index=True,
        help="ใช้กรองหมวดงบประมาณให้ตรงกับแบบฟอร์มคำของบ เช่น วัสดุ / ครุภัณฑ์",
    )

    @api.depends("account_ids", "account_ids.code", "account_ids.name")
    def _compute_account_code(self):
        for post in self:
            labels = []
            for account in post.account_ids:
                if not account.code and not account.name:
                    continue
                code = account.code or ""
                name = account.name or ""
                labels.append(f"[{code}] {name}" if code else name)
            post.account_code = ", ".join(labels)

    @api.model
    def _guess_section_key(self, name):
        text = (name or "").strip().casefold()
        if not text:
            return False
        if "ค่าวัสดุ" in text or "หมวดค่าวัสดุ" in text:
            return "material"
        if "ครุภัณฑ์" in text:
            return "asset"
        if "ก่อสร้าง" in text:
            return "construction"
        if "โครงการ" in text:
            return "project"
        return False

    @api.depends("name")
    def _compute_section_key(self):
        for post in self:
            guessed = self._guess_section_key(post.name)
            # Keep a manually set value when name no longer matches a known pattern.
            if guessed:
                post.section_key = guessed
            elif not post.section_key:
                post.section_key = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("section_key"):
                vals["section_key"] = self._guess_section_key(vals.get("name"))
        return super().create(vals_list)
