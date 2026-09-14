# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequisitionEgpDocumentType(models.Model):
    _name = "purchase.requisition.egp.document.type"
    _description = "e-GP Document Type"
    _order = "sequence, id"

    name = fields.Char(string="Title", required=True, translate=True)
    code = fields.Char(string="Code", required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class PurchaseRequisitionEgpDocument(models.Model):
    _name = "purchase.requisition.egp.document"
    _description = "Purchase Agreement e-GP Document"
    _order = "sequence, id"

    requisition_id = fields.Many2one(
        comodel_name="purchase.requisition",
        string="Purchase Agreement",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    document_type_id = fields.Many2one(
        comodel_name="purchase.requisition.egp.document.type",
        string="Title",
        required=True,
        ondelete="restrict",
        index=True,
    )
    egp_reference = fields.Char(string="e-GP Reference")
    document_date = fields.Date(string="Document Date")
    notes = fields.Text(string="Notes")
    document_file = fields.Binary(string="PDF File", attachment=True)
    document_filename = fields.Char(string="Filename")
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Attachment",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        related="requisition_id.company_id",
        store=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        requisition_id = self.env.context.get("default_requisition_id")
        if not res.get("egp_reference"):
            egp_reference = self.env.context.get("default_egp_reference")
            if not egp_reference and requisition_id:
                egp_reference = self.env["purchase.requisition"].browse(requisition_id).egp_reference
            if egp_reference:
                res["egp_reference"] = egp_reference
        return res

    @api.onchange("document_type_id", "requisition_id")
    def _onchange_document_type_id(self):
        if self.requisition_id.egp_reference:
            self.egp_reference = self.requisition_id.egp_reference

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence") and vals.get("requisition_id"):
                max_sequence = max(
                    self.search(
                        [("requisition_id", "=", vals["requisition_id"])],
                        order="sequence desc",
                        limit=1,
                    ).mapped("sequence") or [0]
                )
                vals["sequence"] = max_sequence + 10
            if vals.get("egp_reference") or not vals.get("requisition_id"):
                continue
            requisition = self.env["purchase.requisition"].browse(vals["requisition_id"])
            if requisition.egp_reference:
                vals["egp_reference"] = requisition.egp_reference
        records = super().create(vals_list)
        records._sync_attachment()
        records._update_requisition_egp_reference()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"document_file", "document_filename", "document_type_id"}.intersection(vals):
            self._sync_attachment()
        if {"egp_reference", "document_type_id"}.intersection(vals):
            self._update_requisition_egp_reference()
        return res

    def unlink(self):
        requisitions = self.mapped("requisition_id")
        res = super().unlink()
        requisitions._update_egp_reference_from_documents()
        return res

    def _sync_attachment(self):
        attachment_obj = self.env["ir.attachment"]
        for record in self:
            if not record.document_file:
                if record.attachment_id:
                    record.attachment_id.unlink()
                    record.attachment_id = False
                continue
            attachment_vals = {
                "name": record.document_filename
                or record.document_type_id.name
                or "e-GP Document.pdf",
                "type": "binary",
                "datas": record.document_file,
                "res_model": record._name,
                "res_id": record.id,
                "mimetype": "application/pdf",
            }
            if record.attachment_id:
                record.attachment_id.write(attachment_vals)
            else:
                record.attachment_id = attachment_obj.create(attachment_vals)

    def _update_requisition_egp_reference(self):
        self.mapped("requisition_id")._update_egp_reference_from_documents()

    def action_preview_document(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("Please attach a PDF file before previewing."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.attachment_id.id,
            "target": "new",
        }
