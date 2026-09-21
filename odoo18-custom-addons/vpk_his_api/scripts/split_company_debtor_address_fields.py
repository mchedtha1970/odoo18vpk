# ruff: noqa
"""Split ลูกหนี้ บริษัท street blobs into Thai partner form fields.

Form mapping (l10n_th_base_location):
  street  = บ้านเลขที่ / หมู่ / ถนน
  street2 = ตำบล / แขวง   (from zip_id)
  city    = อำเภอ / เขต     (from zip_id)
  zip_id  = รหัสไปรษณีย์ + ตำบล
"""
import re

TAG = "ลูกหนี้ บริษัท"
Zip = env["res.city.zip"]
Partner = env["res.partner"]

TAMBON_RE = re.compile(r"(ตำบล|ต\.|แขวง)\s*([ก-๙A-Za-z0-9.\-]+)")
AMPHOE_RE = re.compile(r"(อำเภอ|อ\.|เขต)\s*([ก-๙A-Za-z0-9.\-]+)")
PROVINCE_RE = re.compile(r"(จังหวัด|จ\.)\s*[ก-๙A-Za-z0-9.\-]+")


def _norm(text):
    text = (text or "").replace(" ", "")
    for src, dst in (
        ("ตำบล", "ต."),
        ("อำเภอ", "อ."),
        ("แขวง", "แขวง"),
        ("เขต", "เขต"),
    ):
        text = text.replace(src, dst)
    return text


def _parse(street):
    street = re.sub(r"\s+", " ", street or "").strip()
    tambon = amphoe = None
    khwaeng = False
    m = TAMBON_RE.search(street)
    if m:
        tambon = m.group(2).strip()
        khwaeng = m.group(1).startswith("แขวง")
        street = (street[: m.start()] + street[m.end() :]).strip()
    m = AMPHOE_RE.search(street)
    if m:
        amphoe = m.group(2).strip()
        street = (street[: m.start()] + street[m.end() :]).strip()
    street = PROVINCE_RE.sub("", street)
    street = re.sub(r"\s+", " ", street).strip(" ,")
    street = re.sub(r"\s*หาดกะตะ\s*", " ", street).strip()
    return street, tambon, amphoe, khwaeng


def _city_name(zip_rec):
    return zip_rec.city_id.with_context(lang="en_US").name or zip_rec.city_id.name or ""


def _find_zip(zipcode, tambon, amphoe, khwaeng):
    records = Zip.browse()
    if tambon:
        prefix = "แขวง" if khwaeng else "ต."
        records = Zip.search([("city_id.name", "ilike", prefix + tambon)])
        if not records:
            records = Zip.search([("city_id.name", "ilike", tambon)])
    if not records and zipcode:
        records = Zip.search([("name", "=", zipcode)])
    if not records:
        return Zip.browse()

    tambon_n = _norm(tambon)
    amphoe_n = _norm(amphoe)
    scored = []
    for rec in records:
        name = _norm(_city_name(rec))
        score = 0
        if tambon_n and tambon_n in name:
            score += 10
        if amphoe_n and amphoe_n in name:
            score += 5
        elif amphoe_n:
            short = amphoe_n.replace("เมืองภูเก็ต", "เมือง").replace(
                "เมืองกระบี่", "เมือง"
            ).replace("เมืองพังงา", "เมือง").replace(
                "เมืองสุราษฎร์ธานี", "เมือง"
            ).replace("เมืองสมุทรปราการ", "เมือง")
            if short and short in name:
                score += 3
        if zipcode and rec.name == zipcode:
            score += 2
        if score:
            scored.append((score, rec.id, rec))
    if not scored:
        return Zip.browse()
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2]


# Defaults when tambon is missing but province/zip is known.
DEFAULT_TAMBON = {
    "1030234": ("ตลาดใหญ่", "เมืองภูเก็ต", False),  # เทศบาลนครภูเก็ต
    "1040114": ("ดุสิต", "ดุสิต", True),  # คุรุสภา ถ.นครราชสีมา
    "1110033": ("หาดใหญ่", "หาดใหญ่", False),
}

cat = env["res.partner.category"].search([("name", "=", TAG)], limit=1)
partners = Partner.search(
    [("category_id", "in", cat.ids), ("street", "!=", False), ("street", "!=", "")]
)

ok = fail = 0
for partner in partners:
    street, tambon, amphoe, khwaeng = _parse(partner.street)
    extra = DEFAULT_TAMBON.get(partner.ref or "")
    if extra and not tambon:
        tambon, amphoe, khwaeng = extra
    zip_rec = _find_zip(partner.zip, tambon, amphoe, khwaeng)
    if not zip_rec:
        print("NOZIP", partner.ref, partner.street, "|", tambon, amphoe)
        fail += 1
        continue
    vals = {
        "street": street or partner.street,
        "zip_id": zip_rec.id,
        "city_id": zip_rec.city_id.id,
        "zip": zip_rec.name,
        "state_id": zip_rec.city_id.state_id.id,
        "country_id": zip_rec.city_id.country_id.id,
    }
    partner.with_context(skip_check_zip=True).write(vals)
    partner.invalidate_recordset()
    print(
        "OK",
        partner.ref,
        "|",
        partner.street,
        "|",
        partner.street2,
        "|",
        partner.city,
        "|",
        partner.zip,
        "|",
        zip_rec.id,
    )
    ok += 1

env.cr.commit()
print("split_ok=%s split_fail=%s" % (ok, fail))
