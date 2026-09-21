# ruff: noqa
"""Second pass: remaining official HQ/hospital/hotel addresses."""
import re

ADDR = {
    "1050018": ("34 ซอยสุขุมวิท 4 ถนนสุขุมวิท แขวงคลองเตย เขตคลองเตย", "10110"),
    "1050026": ("87 เอ็ม.ไทย ทาวเวอร์ ออลซีซั่นส์เพลส ถนนวิทยุ แขวงลุมพินี เขตปทุมวัน", "10330"),
    "1050031": ("295 อาคารมิตรแท้ประกันภัย ถนนสี่พระยา แขวงสี่พระยา เขตบางรัก", "10500"),
    "1050034": ("999/1 เดอะไนน์ทาวเวอร์ ถนนพระราม 9 แขวงพัฒนาการ เขตสวนหลวง", "10250"),
    "2150062": ("82 อาคารแสงทองธานี ถนนสาทรเหนือ แขวงสีลม เขตบางรัก", "10500"),
    "2150104": ("1000/9 อาคารบีทีเอส วิชันนารี พาร์ค ถนนพหลโยธิน แขวงจตุจักร เขตจตุจักร", "10900"),
    "2160046": ("3 ซอย 3 ถนนพังงา ตำบลตลาดใหญ่ อำเภอเมืองภูเก็ต", "83000"),
    "2160152": ("26 ถนนภูเก็ต ตำบลตลาดใหญ่ อำเภอเมืองภูเก็ต", "83000"),
    "1170173": ("9 ซอยบางนา-ตราด 1 แขวงบางนา เขตบางนา", "10260"),
    "1200092": ("123 หมู่ 2 ตำบลอ้อมน้อย อำเภอกระทุ่มแบน", "74130"),
    "2160212": ("15 ถนนวิเศษกุล ตำบลทับเที่ยง อำเภอเมืองตรัง", "92000"),
    "2160213": ("38/11 ถนนสุขุมวิท ตำบลเนินพระ อำเภอเมืองระยอง", "21000"),
    "10401678": ("ตำบลคลองท่อมใต้ อำเภอคลองท่อม", "81120"),
}

TAMBON_RE = re.compile(r"(ตำบล|ต\.|แขวง)\s*([ก-๙A-Za-z0-9.\-/]+)")
AMPHOE_RE = re.compile(r"(อำเภอ|อ\.|เขต)\s*([ก-๙A-Za-z0-9.\-]+)")
PROVINCE_RE = re.compile(r"(จังหวัด|จ\.)\s*[ก-๙A-Za-z0-9.\-]+")
Zip = env["res.city.zip"]
Partner = env["res.partner"]


def _norm(text):
    return (text or "").replace(" ", "").replace("ตำบล", "ต.").replace("อำเภอ", "อ.")


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
    return re.sub(r"\s+", " ", street).strip(" ,"), tambon, amphoe, khwaeng


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
        if zipcode and rec.name == zipcode:
            score += 2
        if score:
            scored.append((score, rec.id, rec))
    if not scored:
        return Zip.browse()
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2]


ok = fail = 0
for code, (full, zipcode) in ADDR.items():
    partner = Partner.search([("ref", "=", code)], limit=1)
    if not partner:
        print("missing", code)
        continue
    street, tambon, amphoe, khwaeng = _parse(full)
    zip_rec = _find_zip(zipcode, tambon, amphoe, khwaeng)
    if not zip_rec:
        print("NOZIP", code, full, "|", tambon, amphoe)
        fail += 1
        continue
    partner.with_context(skip_check_zip=True).write(
        {
            "street": street or full,
            "zip_id": zip_rec.id,
            "city_id": zip_rec.city_id.id,
            "zip": zip_rec.name,
            "state_id": zip_rec.city_id.state_id.id,
            "country_id": zip_rec.city_id.country_id.id,
        }
    )
    partner.invalidate_recordset()
    print("OK", code, "|", partner.street, "|", partner.street2, "|", partner.city, "|", partner.zip)
    ok += 1

env.cr.commit()
print("pass2_ok=%s pass2_fail=%s" % (ok, fail))
