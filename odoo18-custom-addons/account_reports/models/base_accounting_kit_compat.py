# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Compatibility with base_accounting_kit wizard models that `_inherit` account.report.

Those TransientModels copy Many2many fields from account.report. Without a unique
relation table they either exceed PostgreSQL's 63-char name limit or collide with
account.report / parent kit models. Give each concrete kit model a short relation.
"""

from odoo import fields, models


def _horiz_m2m(relation):
    return fields.Many2many(
        string="Horizontal Groups",
        comodel_name="account.report.horizontal.group",
        relation=relation,
        column1="report_id",
        column2="horizontal_group_id",
    )


# Direct children of account.report
class AccountCommonJournalReport(models.TransientModel):
    _inherit = "account.common.journal.report"
    horizontal_group_ids = _horiz_m2m("kit_acjr_horiz_grp_rel")


class AccountCommonAccountReport(models.TransientModel):
    _inherit = "account.common.account.report"
    horizontal_group_ids = _horiz_m2m("kit_acar_horiz_grp_rel")


class KitAccountTaxReport(models.TransientModel):
    _inherit = "kit.account.tax.report"
    horizontal_group_ids = _horiz_m2m("kit_tax_horiz_grp_rel")


class CashFlowReport(models.TransientModel):
    _inherit = "cash.flow.report"
    horizontal_group_ids = _horiz_m2m("kit_cfr_horiz_grp_rel")


class FinancialReport(models.TransientModel):
    _inherit = "financial.report"
    horizontal_group_ids = _horiz_m2m("kit_fin_horiz_grp_rel")


class AccountCommonPartnerReport(models.TransientModel):
    _inherit = "account.common.partner.report"
    horizontal_group_ids = _horiz_m2m("kit_acpr_horiz_grp_rel")


# Nested kit wizards
class AccountPrintJournal(models.TransientModel):
    _inherit = "account.print.journal"
    horizontal_group_ids = _horiz_m2m("kit_apj_horiz_grp_rel")


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.report.general.ledger"
    horizontal_group_ids = _horiz_m2m("kit_argl_horiz_grp_rel")


class AccountBalanceReport(models.TransientModel):
    _inherit = "account.balance.report"
    horizontal_group_ids = _horiz_m2m("kit_abr_horiz_grp_rel")


class AccountReportPartnerLedger(models.TransientModel):
    _inherit = "account.report.partner.ledger"
    horizontal_group_ids = _horiz_m2m("kit_arpl_horiz_grp_rel")


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = "account.aged.trial.balance"
    horizontal_group_ids = _horiz_m2m("kit_aatb_horiz_grp_rel")
