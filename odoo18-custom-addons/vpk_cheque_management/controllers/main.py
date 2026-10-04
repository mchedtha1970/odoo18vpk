# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class VpkChequeLayoutController(http.Controller):
    def _template(self, template_id):
        template = request.env["vpk.bank.cheque.template"].browse(template_id).exists()
        if not template:
            raise UserError(_("ไม่พบแบบเช็ค"))
        template.check_access("read")
        if not request.env.user.has_group("account.group_account_manager"):
            raise AccessError(_("เฉพาะผู้ดูแลบัญชีจัดตำแหน่งเช็คได้"))
        return template

    @http.route("/vpk/cheque/layout/<int:template_id>", type="http", auth="user")
    def cheque_layout(self, template_id, **kwargs):
        template = self._template(template_id)
        return request.render("vpk_cheque_management.cheque_layout_page", {
            "template": template,
            "updated": kwargs.get("updated"),
        })

    @http.route("/vpk/cheque/layout/update", type="http", auth="user", methods=["POST"], csrf=True)
    def cheque_layout_update(self, **post):
        template = self._template(int(post.get("template_id") or 0))
        line = request.env["vpk.bank.cheque.attribute.line"].browse(
            int(post.get("line_id") or 0)
        ).exists()
        if not line or line.template_id != template:
            raise UserError(_("ไม่พบรายการบนแบบเช็คนี้"))
        line.write({
            "left_displacement": _int_post(post.get("x")),
            "top_displacement": _int_post(post.get("y")),
            "width": _int_post(post.get("w")),
            "height": _int_post(post.get("h")),
        })
        return request.redirect("/vpk/cheque/layout/%s?updated=1" % template.id)

    @http.route("/vpk/cheque/preview/<int:template_id>", type="http", auth="user")
    def cheque_preview(self, template_id, **kwargs):
        template = self._template(template_id)
        return request.render("vpk_cheque_management.cheque_preview_page", {
            "template": template,
        })


def _int_post(value):
    try:
        return max(int(float(value or 0)), 0)
    except (TypeError, ValueError):
        return 0
