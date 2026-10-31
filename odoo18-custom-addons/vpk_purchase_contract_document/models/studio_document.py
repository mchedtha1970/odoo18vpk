# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, models


class DocumentStudioDocument(models.Model):
    _inherit = "vpk.document.studio.document"

    @api.model
    def _extra_source_models(self):
        return super()._extra_source_models() + ["purchase.contract"]

    def write(self, vals):
        res = super().write(vals)
        if "pdf_file" in vals and not self.env.context.get("vpk_contract_file_sync"):
            self._sync_pdf_to_contract_documents()
        return res

    def _sync_pdf_to_contract_documents(self):
        """Show the studio PDF (generated or signed) as the file of the linked contract documents."""
        ContractDocument = self.env["purchase.contract.document"].sudo()
        for rec in self:
            documents = ContractDocument.search([("studio_document_id", "=", rec.id)])
            if not documents or not rec.pdf_file:
                continue
            documents.write(
                {
                    "document_file": rec.pdf_file,
                    "document_filename": rec.pdf_filename or "%s.pdf" % rec.name,
                }
            )
