from odoo import api, fields, models


class DocumentStudioDocumentType(models.Model):
    _inherit = "vpk.document.studio.document.type"

    egp_document_type_ids = fields.Many2many(
        comodel_name="purchase.requisition.egp.document.type",
        relation="vpk_studio_doc_type_egp_type_rel",
        column1="studio_type_id",
        column2="egp_type_id",
        string="ประเภทเอกสาร e-GP",
        help="เมื่อเพิ่มเอกสารในกระบวนการ e-GP ด้วยประเภทเหล่านี้ จะแสดงแบบฟอร์มของประเภทนี้ให้เลือก",
    )


class DocumentStudioTemplate(models.Model):
    _inherit = "vpk.document.studio.template"

    @api.model
    def _templates_for_linked_type(self, field_name, linked_type, company):
        """Active templates whose studio document type is linked to ``linked_type``."""
        if not linked_type:
            return self.browse()
        return self.search(
            [
                ("active", "=", True),
                ("company_id", "in", [False, company.id]),
                ("document_type_id.%s" % field_name, "in", linked_type.ids),
            ]
        )
