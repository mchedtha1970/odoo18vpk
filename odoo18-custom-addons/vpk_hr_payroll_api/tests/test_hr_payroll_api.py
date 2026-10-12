# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrPayrollApi(TransactionCase):
    def test_ingest_then_post_creates_balanced_journal(self):
        company = self.env.company
        expense = self.env["account.account"].create(
            {
                "name": "เงินเดือนทดสอบ",
                "code": "T591001",
                "account_type": "expense",
                "company_ids": [fields_command(company)],
            }
        )
        liability = self.env["account.account"].create(
            {
                "name": "เงินเดือนค้างจ่ายทดสอบ",
                "code": "T211001",
                "account_type": "liability_current",
                "company_ids": [fields_command(company)],
            }
        )
        Map = self.env["vpk.hr.payroll.component.map"]
        Map.search([("code", "in", ["SALARY", "NET"]), ("company_id", "=", company.id)]).write(
            {"account_id": False}
        )
        salary = Map.search([("code", "=", "SALARY"), ("company_id", "=", company.id)], limit=1)
        net = Map.search([("code", "=", "NET"), ("company_id", "=", company.id)], limit=1)
        salary.account_id = expense
        net.account_id = liability
        result = self.env["vpk.hr.payroll.service"].ingest_payroll(
            {
                "external_id": "HR-PAY-TEST-1",
                "source_system": "hr",
                "pay_date": "2026-10-25",
                "period": "2569-10",
                "description": "เงินเดือนทดสอบ",
                "lines": [
                    {"line_external_id": "1", "component_code": "SALARY", "amount": 1000},
                    {"line_external_id": "2", "component_code": "NET", "amount": 1000},
                ],
                "control_totals": {"debit_total": 1000},
            }
        )
        batch = self.env["vpk.hr.payroll.batch"].browse(result["batch_id"])
        self.assertEqual(batch.state, "ready")
        batch.action_post()
        self.assertEqual(batch.state, "posted")
        self.assertEqual(batch.move_id.state, "posted")
        self.assertEqual(batch.move_id.amount_total, 1000)


def fields_command(company):
    from odoo import fields

    return fields.Command.set([company.id])
