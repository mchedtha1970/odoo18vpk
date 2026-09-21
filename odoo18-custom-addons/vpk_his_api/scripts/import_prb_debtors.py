# ruff: noqa
"""Import PRB insurance debtors from Crystal AR extract and tag ลูกหนี้ พรบ.

Run inside Odoo shell:
  odoo shell -d VPK-S1 --no-http < /mnt/extra-addons/vpk_his_api/scripts/import_prb_debtors.py
"""
import re

import xlrd

SOURCE = "/tmp/prb.xls"
TAG_NAME = "ลูกหนี้ พรบ"
TAG_XMLID = "vpk_his_api.partner_category_prb_debtor"


def _clean_name(name):
    return re.sub(r"\s+", " ", str(name or "")).strip()


def _rows(path):
    wb = xlrd.open_workbook(path)
    ws = wb.sheet_by_index(0)
    out = []
    for r in range(ws.nrows):
        raw = ws.cell_value(r, 2)
        if not raw:
            continue
        match = re.match(r"^(\d+)\s+(.*)$", str(raw).strip())
        if not match:
            continue
        out.append((match.group(1), _clean_name(match.group(2))))
    return out


tag = env.ref(TAG_XMLID, raise_if_not_found=False)
if not tag:
    tag = env["res.partner.category"].search([("name", "=", TAG_NAME)], limit=1)
if not tag:
    tag = env["res.partner.category"].create({"name": TAG_NAME})

Partner = env["res.partner"]
created = updated = skipped = 0
for code, name in _rows(SOURCE):
    partner = Partner.search([("ref", "=", code)], limit=1)
    if not partner:
        partner = Partner.search([("name", "=", name), ("is_company", "=", True)], limit=1)
    vals = {
        "name": name,
        "ref": code,
        "is_company": True,
        "company_type": "company",
        "comment": "นำเข้าจากรายงานลูกหนี้ พรบ.",
    }
    if partner:
        write_vals = dict(vals)
        if tag not in partner.category_id:
            write_vals["category_id"] = [(4, tag.id)]
        if (partner.customer_rank or 0) < 1:
            write_vals["customer_rank"] = 1
        partner.write(write_vals)
        updated += 1
    else:
        vals["customer_rank"] = 1
        vals["category_id"] = [(4, tag.id)]
        Partner.create(vals)
        created += 1

env.cr.commit()
print("tag_id=%s created=%s updated=%s skipped=%s total=%s" % (
    tag.id, created, updated, skipped, created + updated + skipped
))
