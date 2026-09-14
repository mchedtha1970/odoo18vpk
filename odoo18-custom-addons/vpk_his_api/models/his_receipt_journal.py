# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, api, fields, models


SSO_RECEIPT_JOURNAL_CODE = "SSO"
SSO_CASH_CODE = "1101010114.101"
SSO_OUTSTANDING_CODE = "111005"
SSO_SUSPENSE_CODE = "111006"
HIS_CASH_JOURNAL_CODE = "HCSH"
HIS_CASH_ACCOUNT_CODE = "1101010101.101"
HIS_ADVANCE_JOURNAL_CODE = "HADV"
HIS_ADVANCE_ACCOUNT_CODE = "2103010103.101"


class HisReceiptJournalMixin(models.AbstractModel):
    _name = "vpk.his.receipt.journal.mixin"
    _description = "Ensure entitlement-receipt journals"

    @api.model
    def _find_account_by_code(self, code, company):
        Account = self.env["account.account"].sudo()
        rec = Account.search(
            [
                ("code", "=", code),
                ("deprecated", "=", False),
                ("company_ids", "in", company.id),
            ],
            limit=1,
        )
        if rec:
            return rec
        return Account.search(
            [("code", "=", code), ("deprecated", "=", False)], limit=1
        )

    @api.model
    def _ensure_account(self, company, code, name, account_type, reconcile=False):
        account = self._find_account_by_code(code, company)
        if account:
            vals = {}
            if account.deprecated:
                vals["deprecated"] = False
            if account.account_type != account_type:
                vals["account_type"] = account_type
            if account.reconcile != reconcile and account_type not in (
                "asset_cash",
                "liability_credit_card",
            ):
                vals["reconcile"] = reconcile
            if company not in account.company_ids:
                vals["company_ids"] = [Command.link(company.id)]
            if vals:
                account.write(vals)
            return account
        return self.env["account.account"].sudo().create(
            {
                "code": code,
                "name": name,
                "account_type": account_type,
                "reconcile": reconcile,
                "company_ids": [Command.link(company.id)],
            }
        )

    @api.model
    def _ensure_sso_receipt_journal(self, company=None):
        """Bank journal for SSO entitlement receipts pending bank remittance.

        Register Payment → รายรับคงค้าง-ประกันสังคม (รอเคลียร์)
        When SSO transfers into the hospital bank, match the statement to that
        outstanding account to clear it.
        """
        company = company or self.env.company
        Journal = self.env["account.journal"].sudo()
        cash = self._ensure_account(
            company,
            SSO_CASH_CODE,
            "เงินพักรับชำระสิทธิ์ประกันสังคม",
            "asset_cash",
            reconcile=False,
        )
        outstanding = self._ensure_account(
            company,
            SSO_OUTSTANDING_CODE,
            "รายรับคงค้าง-ประกันสังคม",
            "asset_current",
            reconcile=True,
        )
        suspense = self._ensure_account(
            company,
            SSO_SUSPENSE_CODE,
            "พักรายการธนาคาร-ประกันสังคม",
            "asset_current",
            reconcile=False,
        )
        journal = Journal.search(
            [
                ("code", "=", SSO_RECEIPT_JOURNAL_CODE),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        vals = {
            "name": "ลูกหนี้สิทธิ ประกันสังคม",
            "type": "bank",
            "default_account_id": cash.id,
            "suspense_account_id": suspense.id,
            "payment_sequence": True,
        }
        if "multiple_invoice_type" in Journal._fields:
            vals["multiple_invoice_type"] = "text"
        if "text_position" in Journal._fields:
            vals["text_position"] = "header"
        if journal:
            if not journal.default_account_id:
                journal.write(vals)
            if journal.name != "ลูกหนี้สิทธิ ประกันสังคม":
                journal.write({"name": "ลูกหนี้สิทธิ ประกันสังคม"})
        else:
            template = Journal.search(
                [
                    ("code", "=", "BNK1"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            ) or Journal.search(
                [("type", "=", "bank"), ("company_id", "=", company.id)],
                limit=1,
            )
            create_vals = dict(
                vals,
                code=SSO_RECEIPT_JOURNAL_CODE,
                company_id=company.id,
                bank_account_id=False,
            )
            if template:
                journal = template.copy(create_vals)
            else:
                journal = Journal.create(create_vals)
            journal.write({"name": "ลูกหนี้สิทธิ ประกันสังคม"})
        inbound = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_method_id.code == "manual"
        )
        if inbound:
            inbound.write(
                {
                    "payment_account_id": outstanding.id,
                    "name": "รับชำระสิทธิ์ประกันสังคม",
                }
            )
        return journal

    @api.model
    def _ensure_his_cash_journal(self, company=None):
        """Cash journal for HIS counter tenders.

        CSH1 on this CoA uses deprecated 110001 / outstanding 111003, so
        HIS cash must post to เงินสด 1101010101.101 instead.
        """
        company = company or self.env.company
        Journal = self.env["account.journal"].sudo()
        cash = self._ensure_account(
            company,
            HIS_CASH_ACCOUNT_CODE,
            "เงินสด",
            "asset_cash",
            reconcile=False,
        )
        journal = Journal.search(
            [
                ("code", "=", HIS_CASH_JOURNAL_CODE),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        vals = {
            "name": "HIS เงินสดเคาน์เตอร์",
            "type": "cash",
            "default_account_id": cash.id,
        }
        if "multiple_invoice_type" in Journal._fields:
            vals["multiple_invoice_type"] = "text"
        if "text_position" in Journal._fields:
            vals["text_position"] = "header"
        if journal:
            write_vals = {}
            if (
                not journal.default_account_id
                or journal.default_account_id.deprecated
                or journal.default_account_id != cash
            ):
                write_vals["default_account_id"] = cash.id
            if journal.name != vals["name"]:
                write_vals["name"] = vals["name"]
            if write_vals:
                journal.write(write_vals)
        else:
            template = Journal.search(
                [
                    ("code", "=", "CSH1"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            ) or Journal.search(
                [("type", "=", "cash"), ("company_id", "=", company.id)],
                limit=1,
            )
            create_vals = dict(vals, code=HIS_CASH_JOURNAL_CODE, company_id=company.id)
            if template:
                journal = template.copy(create_vals)
            else:
                journal = Journal.create(create_vals)
            journal.write({"name": vals["name"], "default_account_id": cash.id})
        inbound = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_method_id.code == "manual"
        )
        if inbound:
            inbound.write({"payment_account_id": cash.id})
        return journal

    @api.model
    def _bind_his_cash_journal(self, company=None):
        company = company or self.env.company
        journal = self._ensure_his_cash_journal(company)
        pmap = self.env["vpk.his.payment.method.map"].sudo().search(
            [("code", "=", "cash"), ("company_id", "=", company.id)],
            limit=1,
        )
        if pmap and pmap.create_payment and not pmap.is_entitlement:
            pmap.write({"journal_id": journal.id, "journal_type": "cash"})
        return journal

    @api.model
    def _advance_liability_account(self, company=None):
        company = company or self.env.company
        return self._ensure_account(
            company,
            HIS_ADVANCE_ACCOUNT_CODE,
            "รายได้ค่าบริการอื่นรับล่วงหน้า",
            "liability_current",
            reconcile=False,
        )

    @api.model
    def _ensure_his_advance_journal(self, company=None):
        """Journal for applying patient prepaid balance to a visit bill.

        Inbound outstanding is the unearned-revenue liability, so posting
        Dr รับล่วงหน้า / Cr ลูกหนี้ชำระเอง (no cash on the visit day).
        """
        company = company or self.env.company
        Journal = self.env["account.journal"].sudo()
        cash_default = self._ensure_account(
            company,
            HIS_CASH_ACCOUNT_CODE,
            "เงินสด",
            "asset_cash",
            reconcile=False,
        )
        liability = self._advance_liability_account(company)
        journal = Journal.search(
            [
                ("code", "=", HIS_ADVANCE_JOURNAL_CODE),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        vals = {
            "name": "HIS ตัดเงินล่วงหน้า",
            "type": "bank",
            "default_account_id": cash_default.id,
        }
        if "multiple_invoice_type" in Journal._fields:
            vals["multiple_invoice_type"] = "text"
        if "text_position" in Journal._fields:
            vals["text_position"] = "header"
        if journal:
            write_vals = {}
            if not journal.default_account_id or journal.default_account_id.deprecated:
                write_vals["default_account_id"] = cash_default.id
            if journal.name != vals["name"]:
                write_vals["name"] = vals["name"]
            if write_vals:
                journal.write(write_vals)
        else:
            template = Journal.search(
                [
                    ("code", "=", "BNK1"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            ) or Journal.search(
                [("type", "=", "bank"), ("company_id", "=", company.id)],
                limit=1,
            )
            create_vals = dict(
                vals,
                code=HIS_ADVANCE_JOURNAL_CODE,
                company_id=company.id,
                bank_account_id=False,
            )
            if template:
                journal = template.copy(create_vals)
            else:
                journal = Journal.create(create_vals)
            journal.write(
                {"name": vals["name"], "default_account_id": cash_default.id}
            )
        inbound = journal.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_method_id.code == "manual"
        )
        if inbound:
            inbound.write(
                {
                    "payment_account_id": liability.id,
                    "name": "ตัดเงินล่วงหน้า HIS",
                }
            )
        return journal

    @api.model
    def _bind_his_advance_journal(self, company=None):
        company = company or self.env.company
        self.env["vpk.his.payment.method.map"]._bind_advance_tenders(company)
        journal = self._ensure_his_advance_journal(company)
        cash_journal = self._ensure_his_cash_journal(company)
        apply_map = self.env["vpk.his.payment.method.map"].sudo().search(
            [("code", "=", "advance"), ("company_id", "=", company.id)],
            limit=1,
        )
        if apply_map:
            apply_map.write(
                {
                    "journal_id": journal.id,
                    "journal_type": "bank",
                    "create_payment": True,
                    "is_entitlement": False,
                }
            )
        in_map = self.env["vpk.his.payment.method.map"].sudo().search(
            [("code", "=", "advance_in"), ("company_id", "=", company.id)],
            limit=1,
        )
        if in_map:
            in_map.write(
                {
                    "journal_id": cash_journal.id,
                    "journal_type": "cash",
                    "create_payment": False,
                    "is_entitlement": False,
                }
            )
        return journal

    @api.model
    def _bind_sso_receipt_journal(self, company=None):
        company = company or self.env.company
        journal = self._ensure_sso_receipt_journal(company)
        maps = self.env["vpk.his.entitlement.map"].sudo().search(
            [("code", "=", "SSO"), ("company_id", "=", company.id)]
        )
        maps.write({"receipt_journal_id": journal.id})
        # Do not set partner inbound method to this journal: Register Payment
        # at remittance time must hit the bank and keep AR aging until then.
        pmap = self.env["vpk.his.payment.method.map"].sudo().search(
            [
                ("code", "=", "sso"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if pmap and pmap.is_entitlement:
            pmap.write({"journal_id": False, "create_payment": False})
        return journal
