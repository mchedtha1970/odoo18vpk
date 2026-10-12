# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import frozendict


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    vpk_approver_line_ids = fields.One2many(
        comodel_name="vpk.approval.line",
        inverse_name="res_id",
        string="ผู้อนุมัติ",
        domain=lambda self: [("res_model", "=", self._name)],
        auto_join=True,
    )
    vpk_secretary_can_screen = fields.Boolean(
        compute="_compute_vpk_secretary_can_screen",
    )

    @api.depends(
        "review_ids.status",
        "review_ids.reviewer_ids",
        "review_ids.vpk_approval_role",
        "can_review",
    )
    def _compute_vpk_secretary_can_screen(self):
        secretary = self.env.ref(
            "vpk_official_document.user_director_secretary",
            raise_if_not_found=False,
        )
        for rec in self:
            pending = rec.review_ids.filtered(
                lambda review: review.status == "pending"
                and self.env.user in review.reviewer_ids
            )
            role_check = any(review.vpk_approval_role == "check" for review in pending)
            rec.vpk_secretary_can_screen = bool(
                rec.can_review
                and pending
                and (
                    role_check
                    or (secretary and self.env.user == secretary)
                )
            )

    def request_validation(self):
        # Purchase requests are approved by signing the related official documents.
        lined = self.filtered(
            lambda rec: rec._name != "purchase.request"
            and rec.vpk_approver_line_ids.filtered("user_id")
        )
        created = lined._vpk_create_reviews_from_approver_lines()
        rest = self - lined
        if rest:
            created |= super(TierValidation, rest).request_validation()
        return created

    def _vpk_create_reviews_from_approver_lines(self):
        """Use the approver table when it has names; otherwise keep tier definitions."""
        Review = self.env["tier.review"]
        Definition = self.env["tier.definition"]
        created = Review.browse()
        for rec in self:
            lines = rec.vpk_approver_line_ids.filtered("user_id").sorted(
                key=lambda line: (line.sequence, line.id)
            )
            if not lines:
                continue
            if rec.review_ids.filtered(
                lambda review: review.status in ("waiting", "pending")
            ):
                continue
            definition = Definition.search(
                [
                    ("model", "=", rec._name),
                    ("active", "=", True),
                    ("company_id", "in", [False] + rec._get_company().ids),
                ],
                limit=1,
                order="sequence, id",
            )
            if not definition:
                raise UserError(_("ยังไม่ได้ตั้งลำดับการอนุมัติของเอกสารนี้"))
            vals_list = []
            for index, line in enumerate(lines, start=1):
                vals_list.append(
                    {
                        "model": rec._name,
                        "res_id": rec.id,
                        "definition_id": definition.id,
                        "requested_by": self.env.uid,
                        "sequence": index,
                        "vpk_approver_user_id": line.user_id.id,
                        "vpk_approval_role": line._vpk_approval_role(),
                    }
                )
            created |= Review.sudo().create(vals_list)
        if created:
            created._compute_reviewer_ids()
            created._compute_can_review()
            self._notify_review_requested(created)
            self._update_counter({"review_created": True})
        return created

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != "form" or self._tier_validation_manual_config:
            return res
        if self._name == "purchase.request":
            doc = etree.XML(res["arch"])
            for node in doc.xpath(
                "//field[@name='review_ids'][@widget='tier_validation']"
            ):
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
            res["arch"] = etree.tostring(doc)
            return res
        if self._name == "vpk.official.document":
            return res
        doc = etree.XML(res["arch"])
        if doc.xpath("//field[@name='vpk_approver_line_ids']"):
            return res
        sheets = doc.xpath("/form/sheet")
        if not sheets:
            return res
        node = etree.fromstring(
            """
            <group name="vpk_approvers" string="ผู้อนุมัติ">
                <div class="text-muted" colspan="2">
                    เพิ่มผู้อนุมัติตามลำดับ ถ้าไม่เพิ่ม ระบบใช้ลำดับอนุมัติที่ตั้งไว้
                </div>
                <field name="vpk_approver_line_ids" nolabel="1" colspan="2"
                       readonly="validation_status not in ('no', False)"
                       context="{'default_res_model': '%s'}">
                    <list editable="bottom">
                        <field name="sequence" widget="handle"/>
                        <field name="res_model" column_invisible="1"/>
                        <field name="user_id" string="ผู้อนุมัติ"
                               widget="many2one_avatar_user"
                               options="{'no_create': True}"/>
                        <field name="position" string="ตำแหน่ง"/>
                        <field name="is_check" string="ตรวจสอบ"/>
                        <field name="is_sign" string="ลงนาม"/>
                    </list>
                </field>
            </group>
            """
            % self._name
        )
        View = self.env["ir.ui.view"]
        new_arch, new_models = View.postprocess_and_fields(node, self._name)
        new_node = etree.fromstring(new_arch)
        sheets[0].append(new_node)
        all_models = res["models"].copy()
        for model_name, view_fields in new_models.items():
            if model_name in all_models:
                all_models[model_name] = tuple(
                    set(all_models[model_name]) | set(view_fields)
                )
            else:
                all_models[model_name] = tuple(view_fields)
        res["arch"] = etree.tostring(doc)
        res["models"] = frozendict(all_models)
        return res
