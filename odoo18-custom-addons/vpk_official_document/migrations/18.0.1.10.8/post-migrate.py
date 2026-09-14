# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import SUPERUSER_ID, api


def _user_by_name(env, name):
    name = " ".join((name or "").split())
    if not name:
        return env["res.users"]
    user = env["res.users"].search(
        [("name", "=", name), ("share", "=", False)],
        limit=1,
    )
    if user:
        return user
    employees = env["hr.employee"].search([("name", "=", name)], limit=2)
    if len(employees) == 1 and employees.user_id:
        return employees.user_id
    return env["res.users"]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Document = env["vpk.official.document"]
    Company = env["res.company"]

    officer = env["res.users"].search([("login", "=", "uat.officer")], limit=1)
    head_officer = env["res.users"].search(
        [("login", "=", "uat.head_officer")],
        limit=1,
    )
    for company in Company.search([]):
        updates = {}
        if not company.official_doc_signer_id:
            user = _user_by_name(env, company.official_doc_signer_name)
            if user:
                updates["official_doc_signer_id"] = user.id
        if not company.official_doc_head_officer_id:
            user = head_officer or _user_by_name(
                env, company.official_doc_head_officer_name
            )
            if user:
                updates["official_doc_head_officer_id"] = user.id
        if not company.official_doc_officer_id:
            user = officer or _user_by_name(env, company.official_doc_officer_name)
            if user:
                updates["official_doc_officer_id"] = user.id
        if updates:
            company.write(updates)

    mapping = (
        ("signer_id", "signer_name"),
        ("head_officer_id", "head_officer_name"),
        ("officer_id", "officer_name"),
    )
    for document in Document.search([]):
        updates = {}
        for user_field, name_field in mapping:
            if document[user_field] or not document[name_field]:
                continue
            user = _user_by_name(env, document[name_field])
            if user:
                updates[user_field] = user.id
        if updates:
            document.write(updates)
