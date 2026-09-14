# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging

_logger = logging.getLogger(__name__)

KEEP = (
    {
        "xmlid": "budget_request_form_type_material",
        "code": "material_budget",
        "name": "แบบฟอร์มตั้งงบวัสดุ",
        "sequence": 10,
        "budget_type_code": "supplies_budget",
        "match_codes": ("material_budget", "แบบฟอร์มตั้งงบวัสดุ"),
        "match_names": ("แบบฟอร์มตั้งงบวัสดุ", "แบบตั้งงบวัสดุ"),
        "prefer_thai_duplicate": False,
    },
    {
        "xmlid": "budget_request_form_type_asset",
        "code": "asset",
        "name": "แบบฟอร์มครุภัณฑ์",
        "sequence": 20,
        "budget_type_code": "asset_budget",
        "match_codes": ("asset", "แบบฟอร์มครุภัณฑ์"),
        "match_names": ("แบบฟอร์มครุภัณฑ์",),
        "prefer_thai_duplicate": False,
    },
    {
        "xmlid": "budget_request_form_type_construction",
        "code": "construction",
        "name": "แบบฟอร์ม ก่อสร้าง",
        "sequence": 30,
        "budget_type_code": "construction_budget",
        "match_codes": ("construction", "แบบฟอร์ม ก่อสร้าง", "แบบฟอร์มก่อสร้าง"),
        "match_names": ("ก่อสร้าง",),
        "prefer_thai_duplicate": True,
    },
    {
        "xmlid": "budget_request_form_type_project",
        "code": "project",
        "name": "แบบฟอร์มโครงการ",
        "sequence": 40,
        "budget_type_code": "project_budget",
        "match_codes": ("project", "แบบฟอร์มโครงการ"),
        "match_names": ("โครงการ",),
        "prefer_thai_duplicate": True,
    },
)


def _label(record):
    return "%s %s" % (record.name or "", record.code or "")


def _pick_record(Form, spec, used_ids):
    xml_rec = Form.env.ref("vpk_budget.%s" % spec["xmlid"], raise_if_not_found=False)
    if spec.get("prefer_thai_duplicate"):
        alt = Form.search(
            [
                ("id", "not in", list(used_ids) + ([xml_rec.id] if xml_rec else [])),
                ("name", "ilike", spec["match_names"][0]),
            ],
            order="id",
            limit=1,
        )
        if alt:
            return alt
    if xml_rec and xml_rec.id not in used_ids:
        return xml_rec
    for code in spec["match_codes"]:
        rec = Form.search(
            [("code", "=", code), ("id", "not in", list(used_ids))],
            limit=1,
        )
        if rec:
            return rec
    recs = Form.search(
        [("name", "ilike", spec["match_names"][0]), ("id", "not in", list(used_ids))],
        order="id",
    )
    if spec["xmlid"] == "budget_request_form_type_asset":
        recs = recs.filtered(
            lambda rec: "คอม" not in (rec.name or "") and "ต่ำกว่าแสน" not in (rec.name or "")
        )
    return recs[:1]


def _rebind_xmlid(env, xmlid_name, record):
    imd = env["ir.model.data"].search(
        [("module", "=", "vpk_budget"), ("name", "=", xmlid_name)],
        limit=1,
    )
    if imd:
        if imd.res_id != record.id:
            imd.write({"res_id": record.id, "noupdate": True})
        return
    env["ir.model.data"].create(
        {
            "module": "vpk_budget",
            "name": xmlid_name,
            "model": "vpk.budget.request.form.type",
            "res_id": record.id,
            "noupdate": True,
        }
    )


def _reassign(env, source, target):
    if not source or source == target:
        return
    env.cr.execute(
        """
        UPDATE departmental_budget_request
           SET form_type_id = %s
         WHERE form_type_id = %s
        """,
        (target.id, source.id),
    )
    env.cr.execute(
        """
        UPDATE departmental_budget_request_summary_wizard
           SET form_type_id = %s
         WHERE form_type_id = %s
        """,
        (target.id, source.id),
    )
    env.cr.execute(
        """
        UPDATE purchase_request
           SET budget_form_type_id = %s
         WHERE budget_form_type_id = %s
        """,
        (target.id, source.id),
    )


def _ensure_line(env, form, budget_type_code):
    Line = env["vpk.budget.request.form.type.line"]
    budget_type = env["vpk.budget.type"].search(
        [("code", "=", budget_type_code)], limit=1
    )
    if not form or not budget_type:
        return
    if not Line.search_count(
        [("form_type_id", "=", form.id), ("budget_type_id", "=", budget_type.id)]
    ):
        Line.create(
            {
                "form_type_id": form.id,
                "budget_type_id": budget_type.id,
                "sequence": 10,
            }
        )


def _target_for_extra(name, keepers):
    if any(token in name for token in ("วัสดุ", "material")):
        return keepers["budget_request_form_type_material"]
    if any(token in name for token in ("ก่อสร้าง", "construction")):
        return keepers["budget_request_form_type_construction"]
    if any(token in name for token in ("โครงการ", "project", "ค่าใช้จ่าย")):
        return keepers["budget_request_form_type_project"]
    return keepers["budget_request_form_type_asset"]


def migrate(cr, version):
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    Form = env["vpk.budget.request.form.type"].with_context(active_test=False)
    keepers = {}
    used_ids = set()
    for spec in KEEP:
        rec = _pick_record(Form, spec, used_ids)
        if not rec:
            rec = Form.create(
                {
                    "code": "tmp_%s" % spec["code"],
                    "name": spec["name"],
                    "sequence": spec["sequence"],
                    "active": True,
                }
            )
        keepers[spec["xmlid"]] = rec
        used_ids.add(rec.id)

    extras = Form.search([("id", "not in", list(used_ids))])
    for extra in extras:
        target = _target_for_extra(_label(extra), keepers)
        _reassign(env, extra, target)
        _logger.info("Removing extra budget form %s -> %s", extra.display_name, target.code)
        extra.unlink()

    for spec in KEEP:
        rec = keepers[spec["xmlid"]]
        rec.write(
            {
                "code": spec["code"],
                "name": spec["name"],
                "sequence": spec["sequence"],
                "active": True,
            }
        )
        _rebind_xmlid(env, spec["xmlid"], rec)
        _ensure_line(env, rec, spec["budget_type_code"])
        _logger.info("Kept budget form %s id=%s", spec["code"], rec.id)

    env["ir.model.data"].search(
        [
            ("module", "=", "vpk_budget"),
            ("name", "=", "budget_request_form_type_small_item"),
        ]
    ).unlink()
    Form._sync_department_budget_request_menus()
