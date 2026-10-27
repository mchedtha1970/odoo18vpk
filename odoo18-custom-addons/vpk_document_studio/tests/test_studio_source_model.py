# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStudioSourceModel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.template = cls.env["vpk.document.studio.template"].create(
            {
                "name": "ทดสอบโมเดลต้นทาง",
                "code": "source_model_test",
                "source_model_id": cls.partner_model.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "บริษัท ทดสอบ"})
        cls.env["res.partner"].create(
            {"name": "สมชาย", "email": "a@example.com", "parent_id": cls.partner.id}
        )
        cls.env["res.partner"].create(
            {"name": "สมหญิง", "email": "b@example.com", "parent_id": cls.partner.id}
        )

    def _add_fields(self):
        Field = self.env["vpk.document.studio.field"]
        name_field = self.env["ir.model.fields"]._get("res.partner", "name")
        children = self.env["ir.model.fields"]._get("res.partner", "child_ids")
        Field.create(
            {
                "template_id": self.template.id,
                "name": "ชื่อ",
                "code": "partner_name",
                "field_type": "char",
                "map_field_id": name_field.id,
            }
        )
        Field.create(
            {
                "template_id": self.template.id,
                "name": "ผู้ติดต่อ",
                "code": "contacts",
                "field_type": "many2one",
                "map_field_id": children.id,
            }
        )

    def test_field_model_follows_template_source(self):
        self._add_fields()
        for field in self.template.field_ids.filtered("map_field_id"):
            self.assertEqual(field.map_model_id, self.partner_model)

    def test_binding_action_created_and_removed(self):
        Actions = self.env["ir.actions.act_window"].sudo()
        domain = [
            ("res_model", "=", "vpk.document.studio.create.wizard"),
            ("binding_model_id", "=", self.partner_model.id),
        ]
        self.assertEqual(len(Actions.search(domain)), 1)
        self.template.source_model_id = False
        self.assertFalse(Actions.search(domain))

    def test_document_filled_from_source_record(self):
        self._add_fields()
        document = self.env["vpk.document.studio.document"].create(
            {
                "template_id": self.template.id,
                "source_ref": "res.partner,%d" % self.partner.id,
            }
        )
        values = document.value_json
        self.assertEqual(values["partner_name"], "บริษัท ทดสอบ")
        self.assertEqual(values["contacts"]["res_id"], self.partner.id)

    def test_generic_table_rows_with_line_tokens(self):
        self._add_fields()
        self.template.write(
            {
                "block_ids": [
                    (
                        0,
                        0,
                        {
                            "block_type": "table",
                            "table_repeat_code": "contacts",
                            "column_ids": [
                                (0, 0, {"header": "ลำดับ", "content": "{{no}}", "width_cm": 1.5}),
                                (0, 0, {"header": "ชื่อ", "content": "{{name}}"}),
                                (0, 0, {"header": "อีเมล", "content": "{{line.email}}"}),
                            ],
                        },
                    )
                ]
            }
        )
        document = self.env["vpk.document.studio.document"].create(
            {
                "template_id": self.template.id,
                "source_ref": "res.partner,%d" % self.partner.id,
            }
        )
        html = document._filled_body_html()
        for text in ("สมชาย", "สมหญิง", "a@example.com", "b@example.com"):
            self.assertIn(text, html)
        self.assertNotIn("{{line.email}}", html)

    def test_create_wizard(self):
        self._add_fields()
        wizard = (
            self.env["vpk.document.studio.create.wizard"]
            .with_context(active_model="res.partner", active_id=self.partner.id)
            .create({"template_id": self.template.id})
        )
        self.assertEqual(wizard.source_name, "บริษัท ทดสอบ")
        action = wizard.action_create()
        document = self.env["vpk.document.studio.document"].browse(action["res_id"])
        self.assertEqual(document.source_ref, self.partner)
