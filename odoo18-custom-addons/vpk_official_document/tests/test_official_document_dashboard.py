# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOfficialDocumentDashboard(TransactionCase):
    def test_dashboard_cards_open_document_list(self):
        doc_type = self.env.ref(
            "vpk_official_document.document_type_wa_committee_order"
        )
        other_type = self.env.ref(
            "vpk_official_document.document_type_integrity_over_100k"
        )
        self.env["vpk.official.document"].create(
            {
                "document_type": "wa_committee_order",
                "agency": "โรงพยาบาลวชิระภูเก็ต",
            }
        )
        waiting = self.env["vpk.official.document"].create(
            {
                "document_type": "integrity_over_100k",
            }
        )
        waiting.with_context(skip_validation_check=True).write({"state": "to_approve"})
        cancelled = self.env["vpk.official.document"].create(
            {
                "document_type": "wa_committee_order",
            }
        )
        cancelled.with_context(skip_validation_check=True).write({"state": "cancelled"})

        data = self.env["vpk.official.document.type"].get_dashboard_data()
        self.assertTrue(data["cards"])
        codes = [card["code"] for card in data["cards"]]
        self.assertIn("wa_committee_order", codes)
        self.assertIn("integrity_over_100k", codes)

        committee_card = next(
            card for card in data["cards"] if card["code"] == "wa_committee_order"
        )
        integrity_card = next(
            card for card in data["cards"] if card["code"] == "integrity_over_100k"
        )
        self.assertGreaterEqual(committee_card["total"], 2)
        self.assertGreaterEqual(committee_card["draft"], 1)
        self.assertGreaterEqual(integrity_card["waiting"], 1)

        action = doc_type.action_open_documents()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "vpk.official.document")
        self.assertEqual(action["view_mode"], "list,form")
        self.assertIn(("document_type", "=", "wa_committee_order"), action["domain"])
        self.assertEqual(
            action["context"]["default_document_type"], "wa_committee_order"
        )

        waiting_action = other_type.action_open_documents("waiting")
        self.assertIn(("document_type", "=", "integrity_over_100k"), waiting_action["domain"])
        self.assertIn(("state", "=", "to_approve"), waiting_action["domain"])

        kpi_total = next(item for item in data["kpis"] if item["key"] == "total")
        self.assertGreaterEqual(kpi_total["count"], 2)
        self.assertEqual(kpi_total["action"]["res_model"], "vpk.official.document")
        self.assertFalse(kpi_total["action"]["domain"])
