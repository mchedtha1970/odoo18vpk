#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map hospital opening-stock drug names/IDs to ERP product codes."""

from __future__ import annotations

import csv
import re
import subprocess
import tempfile
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "UAT-Data-Migrate" / "คลังสินค้า" / "ยอดยกมา70_ได้รับจาก_รพ.xlsx"
IMPORT_XLSX = ROOT / "UAT-Data-Migrate" / "คลังสินค้า" / "ข้อมูลยาที่ นำเข้าระบบ.xlsx"
OUT = ROOT / "UAT-Data-Migrate" / "คลังสินค้า" / "mapping-ยอดยกมา70-รหัสยาERP.xlsx"

NAVY = "1F4E79"
NAVY_FILL = PatternFill("solid", fgColor=NAVY)
HINT = PatternFill("solid", fgColor="E8F1FA")
GREEN = PatternFill("solid", fgColor="E2EFDA")
YELLOW = PatternFill("solid", fgColor="FFF2CC")
ORANGE = PatternFill("solid", fgColor="FCE4D6")
RED = PatternFill("solid", fgColor="F8D7DA")
WHITE = PatternFill("solid", fgColor="FFFFFF")
THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
FONT = "Prompt"
TITLE = Font(name=FONT, size=16, bold=True, color=NAVY)
SUB = Font(name=FONT, size=11, color="475569")
HEAD = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY = Font(name=FONT, size=10, color="1E293B")
BOLD = Font(name=FONT, size=10, bold=True, color="1E293B")
WRAP = Alignment(wrap_text=True, vertical="center")
LEFT = Alignment(vertical="center", wrap_text=True)

STATUS_ตรงรหัส = "ตรงรหัส"
STATUS_ชื่อต่าง = "ตรงรหัส-ชื่อต่าง"
STATUS_ใกล้เคียง = "ใกล้เคียง-ต้องตรวจ"
STATUS_มีในไฟล์นำเข้า = "ไม่มีในระบบ-มีในไฟล์นำเข้า"
STATUS_ไม่ตรง = "ไม่ตรง"

STATUS_FILL = {
    STATUS_ตรงรหัส: GREEN,
    STATUS_ชื่อต่าง: YELLOW,
    STATUS_ใกล้เคียง: ORANGE,
    STATUS_มีในไฟล์นำเข้า: YELLOW,
    STATUS_ไม่ตรง: RED,
}

NOISE_LEAD = re.compile(
    r"^\s*(?:\[[^\]]+\]|\((?:จ่ายตึก|ยาหมด|คิดเงิน|เฉพาะ|pre-?paid|จ่าย)[^)]*\))\s*",
    re.I,
)
NOISE_ANY = re.compile(
    r"\((?:จ่ายตึกศรีฯ|คิดเงิน|ยาหมด[^)]*|เฉพาะ[^)]*)\)|"
    r"\[ยาหมดอายุ[^]]*\]|---herb\.?|\bherb\b",
    re.I,
)
STRENGTH = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(mcg|µg|μg|mg|g|ml|iu|units?|มก\.?|มล\.?|กรัม|%)",
    re.I,
)
FORM = re.compile(
    r"\b(tab\.?|tabs|tablet|tablets|cap\.?|caps|capsule|capsules|inj\.?|injection|"
    r"syr\.?|syrup|susp(?:en)?|cream|gel|oint(?:ment)?|drops?|amp(?:oule)?|vial|"
    r"film.?coated)\b|(แคปซูล|ยาแคปซูล|ยาเม็ด|เม็ด|ขวด|กล่อง|หลอด)",
    re.I,
)
UNIT_MAP = {
    "µg": "mcg",
    "μg": "mcg",
    "mcg": "mcg",
    "mg": "mg",
    "g": "g",
    "ml": "ml",
    "iu": "iu",
    "unit": "iu",
    "units": "iu",
    "มก": "mg",
    "มก.": "mg",
    "มล": "ml",
    "มล.": "ml",
    "กรัม": "g",
    "%": "%",
}


def nfc(value) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def pad_code(hid) -> str:
    if hid is None or hid == "":
        return ""
    if isinstance(hid, float) and hid == int(hid):
        hid = int(hid)
    text = str(hid).strip().split(".")[0]
    if text.isdigit() and len(text) < 5:
        return text.zfill(5)
    return text


def code_variants(hid) -> list[str]:
    raw = pad_code(hid)
    if not raw:
        return []
    out = [raw]
    if raw.isdigit():
        out.append(str(int(raw)))
        out.append(raw.zfill(5))
        out.append(raw.zfill(6))
    return list(dict.fromkeys(out))


def extract_strengths(text: str) -> list[tuple[float, str]]:
    found = []
    for match in STRENGTH.finditer(nfc(text)):
        try:
            val = float(match.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = UNIT_MAP.get(match.group(2).lower(), match.group(2).lower())
        found.append((val, unit))
    return found


def core_name(text: str) -> str:
    value = nfc(text)
    value = NOISE_LEAD.sub("", value)
    value = NOISE_ANY.sub(" ", value)
    value = FORM.sub(" ", value)
    value = re.sub(r"\[[^\]]{0,80}\]", " ", value)
    value = re.sub(r"\([^)]{0,80}\)", " ", value)
    value = value.lower().replace("µ", "u").replace("μ", "u")
    value = re.sub(r"(\d)\s+(mcg|mg|g|ml|iu|%)\b", r"\1\2", value, flags=re.I)
    value = re.sub(r"[^\wก-๙]+", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"^ยา\s*", "", value)
    return value


def names_close(a: str, b: str) -> bool:
    left = re.sub(r"\s+", " ", nfc(a)).lower()
    right = re.sub(r"\s+", " ", nfc(b)).lower()
    if left == right:
        return True
    return core_name(a) == core_name(b)


STOP_TOKENS = {
    "vaccine", "injection", "syrup", "cream", "tablet", "tablets", "capsule",
    "capsules", "suspension", "solution", "drops", "ointment", "inhaler",
    "ampoule", "vial", "oral", "forte", "plus", "extra", "adult", "child",
    "herb", "film", "coated", "inj", "tab", "cap", "syr", "gel", "drop",
    "เฉพาะ", "สำหรับ", "คิดเงิน", "ยาหมด", "จ่ายตึก", "วัคซีน", "ยาฉีด",
}

def brand_tokens(text: str) -> set[str]:
    found = {m.group(0).lower() for m in re.finditer(r"[A-Za-z][A-Za-z0-9\-]{3,}", nfc(text))}
    found |= {m.group(1).lower() for m in re.finditer(r"\b([A-Z]{2,})\b", nfc(text))}
    return {tok for tok in found if tok not in STOP_TOKENS}


def distinctive_tokens(text: str) -> set[str]:
    tokens = set(brand_tokens(text))
    for token in core_name(text).split():
        if re.match(r"^\d", token) or token in STOP_TOKENS:
            continue
        if len(token) >= 4:
            tokens.add(token)
    return tokens


def main_drug_tokens(text: str) -> list[str]:
    ordered = []
    for match in re.finditer(r"[A-Za-z][A-Za-z0-9\-]{2,}", nfc(text)):
        token = match.group(0).lower()
        if token in STOP_TOKENS or token in ordered:
            continue
        ordered.append(token)
    return ordered


def name_tags(text: str) -> set[str]:
    found = set()
    for match in re.finditer(r"\[([^\]]+)\]", nfc(text)):
        for part in re.split(r"[,/]", match.group(1)):
            tag = part.strip().lower()
            if tag in {"สปส"}:
                tag = "สปสช"
            if tag:
                found.add(tag)
    return found


def strength_overlap(a: str, b: str) -> bool:
    sa, sb = set(extract_strengths(a)), set(extract_strengths(b))
    if not sa or not sb:
        return True
    return bool(sa & sb)


def name_score(a: str, b: str) -> float:
    ca, cb = core_name(a), core_name(b)
    if not ca or not cb:
        return 0.0
    if ca == cb:
        return 1.0
    low_a, low_b = nfc(a).lower(), nfc(b).lower()
    a_is_vaccine = ("vaccine" in low_a) or ("วัคซีน" in low_a)
    b_is_vaccine = ("vaccine" in low_b) or ("วัคซีน" in low_b)
    if a_is_vaccine != b_is_vaccine:
        return 0.0
    mains_a, mains_b = main_drug_tokens(a), main_drug_tokens(b)
    if mains_a and mains_a[0] not in set(mains_b):
        return 0.0
    da, db = distinctive_tokens(a), distinctive_tokens(b)
    shared = da & db
    if not shared:
        return 0.0
    same_strength = strength_overlap(a, b)
    tag_bonus = 0.03 * len(name_tags(a) & name_tags(b))
    if mains_a and mains_a[0] in set(mains_b) and same_strength:
        return min(1.0, 0.94 + tag_bonus)
    if da == db and same_strength:
        return min(1.0, 0.99 + tag_bonus)
    if da <= db or db <= da:
        base = 0.96 if same_strength else 0.82
        return min(1.0, base + tag_bonus)
    overlap = len(shared) / len(da | db)
    sm = SequenceMatcher(None, ca, cb).ratio()
    score = max(0.72 + 0.26 * overlap, sm)
    if not same_strength:
        score *= 0.85
    return min(1.0, score + tag_bonus)


def dump_live_drugs(path: Path) -> list[dict]:
    sql = r"""
COPY (
  SELECT pp.default_code,
         COALESCE(pt.name->>'th_TH', pt.name->>'en_US', pt.name::text) AS name,
         pu.name->>'th_TH' AS uom,
         pc.complete_name AS categ
  FROM product_product pp
  JOIN product_template pt ON pt.id = pp.product_tmpl_id
  JOIN product_category pc ON pc.id = pt.categ_id
  LEFT JOIN uom_uom pu ON pu.id = pt.uom_id
  WHERE pc.complete_name ILIKE '%เวชภัณฑ์ ยา%'
    AND pp.active AND pt.active
  ORDER BY pp.default_code
) TO STDOUT WITH CSV HEADER
"""
    result = subprocess.run(
        ["docker", "exec", "odoo18vpk-docker-db-1", "psql", "-U", "odoo", "-d", "VPK-S1", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
    )
    path.write_text(result.stdout, encoding="utf-8")
    rows = []
    for rec in csv.DictReader(path.open(encoding="utf-8")):
        code = nfc(rec.get("default_code"))
        if not code:
            continue
        rows.append(
            {
                "code": code,
                "name": nfc(rec.get("name")),
                "uom": nfc(rec.get("uom")),
                "categ": nfc(rec.get("categ")),
                "source": "live",
            }
        )
    return rows


def load_import_drugs() -> list[dict]:
    wb = load_workbook(IMPORT_XLSX, data_only=True, read_only=True)
    rows = []
    for rec in wb.active.iter_rows(min_row=2, values_only=True):
        code = nfc(rec[1])
        name = nfc(rec[2])
        if not code or not name:
            continue
        rows.append(
            {
                "code": code,
                "name": name,
                "uom": nfc(rec[4]),
                "categ": nfc(rec[3]),
                "source": "import",
            }
        )
    wb.close()
    return rows


def load_hospital() -> list[dict]:
    wb = load_workbook(SRC, data_only=True, read_only=True)
    rows = []
    for idx, rec in enumerate(wb.active.iter_rows(min_row=2, values_only=True), start=1):
        if rec[1] is None or nfc(rec[1]) == "":
            continue
        rows.append(
            {
                "seq": idx,
                "hosp_id": rec[0],
                "hosp_code": pad_code(rec[0]),
                "name": nfc(rec[1]),
                "pack": nfc(rec[2]),
                "price": rec[3],
                "qty": rec[4] if rec[4] is not None else 0,
            }
        )
    wb.close()
    return rows


def index_by_code(items: list[dict]) -> dict[str, dict]:
    out = {}
    for item in items:
        out[item["code"]] = item
        if item["code"].isdigit():
            out[str(int(item["code"]))] = item
    return out


def token_index(items: list[dict]) -> dict[str, list[int]]:
    idx = defaultdict(list)
    for i, item in enumerate(items):
        for token in distinctive_tokens(item["name"]):
            if len(token) >= 4:
                idx[token].append(i)
            elif 2 <= len(token) <= 3 and token.isalpha():
                idx[f"~{token}"].append(i)
    return idx


def suggest(name: str, catalog: list[dict], index: dict[str, list[int]], limit: int = 5) -> list[tuple[float, dict]]:
    ids = set()
    tokens = distinctive_tokens(name)
    for token in tokens:
        if len(token) >= 4:
            ids.update(index.get(token, []))
    if not ids:
        for token in tokens:
            if 2 <= len(token) <= 3 and token.isalpha():
                ids.update(index.get(f"~{token}", []))
    scored = []
    seen = set()
    hosp_tags = name_tags(name)
    for i in ids:
        item = catalog[i]
        if item["code"] in seen:
            continue
        seen.add(item["code"])
        score = name_score(name, item["name"])
        if score >= 0.72:
            scored.append((score, item))
    scored.sort(
        key=lambda row: (
            -row[0],
            -len(hosp_tags & name_tags(row[1]["name"])),
            1 if "จ่ายตึก" in row[1]["name"] else 0,
            row[1]["code"],
        )
    )
    return scored[:limit]


def pick_import_alt(name: str, suggestions: list[tuple[float, dict]], live_code: str) -> tuple[str, str, str]:
    for score, item in suggestions:
        if item["code"] == live_code:
            continue
        if item["code"].startswith("100") and score >= 0.88:
            note = "จับจากชื่อในไฟล์นำเข้ายา"
            if "จ่ายตึก" in item["name"]:
                note += " (รายการจ่ายตึกศรีฯ)"
            return item["code"], item["name"], note
    for score, item in suggestions:
        if item["code"] == live_code:
            continue
        if score >= 0.92:
            return item["code"], item["name"], "จับจากชื่อในไฟล์นำเข้ายา"
    return "", "", ""


def map_rows(hospital, live_items, import_items):
    live_by_code = index_by_code(live_items)
    live_index = token_index(live_items)
    import_index = token_index(import_items)
    mapped = []
    used_live = set()

    for row in hospital:
        live_hit = None
        for variant in code_variants(row["hosp_id"]):
            if variant in live_by_code:
                live_hit = live_by_code[variant]
                break

        live_suggestions = suggest(row["name"], live_items, live_index)
        import_suggestions = suggest(row["name"], import_items, import_index)

        status = STATUS_ไม่ตรง
        erp_code = ""
        erp_name = ""
        erp_uom = ""
        name_same = ""
        note = ""
        alt_code, alt_name, alt_note = "", "", ""

        if live_hit:
            used_live.add(live_hit["code"])
            erp_code = live_hit["code"]
            erp_name = live_hit["name"]
            erp_uom = live_hit["uom"]
            if names_close(row["name"], live_hit["name"]):
                status = STATUS_ตรงรหัส
                name_same = "ใช่"
                note = "รหัสเดิมของ รพ. ตรงกับ default_code ในระบบ (เติมศูนย์หน้าให้ 5 หลัก)"
            else:
                status = STATUS_ชื่อต่าง
                name_same = "ไม่"
                note = "รหัสตรงกัน แต่ชื่อในระบบต่างจากไฟล์ รพ. เล็กน้อย ตรวจทานก่อนยกยอด"
            alt_code, alt_name, alt_note = pick_import_alt(row["name"], import_suggestions, erp_code)
        else:
            name_same = "ไม่"
            best_live = live_suggestions[0] if live_suggestions else None
            best_import = None
            for score, item in import_suggestions:
                if item["code"].startswith("100") and score >= 0.88:
                    best_import = (score, item)
                    break
            if not best_import and import_suggestions:
                best_import = import_suggestions[0]

            live_same = (
                best_live
                if best_live and best_live[0] >= 0.88 and strength_overlap(row["name"], best_live[1]["name"])
                else None
            )
            import_same = (
                best_import
                if best_import
                and best_import[0] >= 0.88
                and strength_overlap(row["name"], best_import[1]["name"])
                else None
            )

            if live_same:
                status = STATUS_ใกล้เคียง
                erp_code = live_same[1]["code"]
                erp_name = live_same[1]["name"]
                erp_uom = live_same[1]["uom"]
                used_live.add(erp_code)
                note = f"ไม่มีรหัส {row['hosp_code']} ในระบบ จับจากชื่อ คะแนน {live_same[0]:.2f}"
                hosp_ml = {val for val, unit in extract_strengths(row["name"]) if unit == "ml"}
                erp_ml = {val for val, unit in extract_strengths(erp_name) if unit == "ml"}
                if hosp_ml and erp_ml and not (hosp_ml & erp_ml):
                    note += " ปริมาตรไม่ตรง ต้องตรวจขนาดบรรจุ"
                alt_code, alt_name, alt_note = pick_import_alt(row["name"], import_suggestions, erp_code)
            elif import_same:
                status = STATUS_มีในไฟล์นำเข้า
                alt_code, alt_name = import_same[1]["code"], import_same[1]["name"]
                alt_note = "มีในไฟล์นำเข้ายา แต่ยังไม่มีรหัสนี้ในระบบตอนนี้"
                note = (
                    f"ไม่มีรหัส {row['hosp_code']} ในระบบ VPK-S1 "
                    f"แต่ชื่อตรงกับรหัสนำเข้า {alt_code}"
                )
                if best_live:
                    note += (
                        f" / ของในระบบที่ใกล้สุดคือ {best_live[1]['code']} "
                        f"{best_live[1]['name']} แต่ความแรงหรือชื่อไม่ตรง"
                    )
            elif best_live and best_live[0] >= 0.75:
                status = STATUS_ใกล้เคียง
                erp_code = best_live[1]["code"]
                erp_name = best_live[1]["name"]
                erp_uom = best_live[1]["uom"]
                used_live.add(erp_code)
                note = (
                    f"ไม่มีรหัส {row['hosp_code']} ในระบบ จับชื่อได้แต่ความแรง/ขนาดไม่ตรง "
                    f"คะแนน {best_live[0]:.2f}"
                )
                alt_code, alt_name, alt_note = pick_import_alt(row["name"], import_suggestions, erp_code)
            else:
                status = STATUS_ไม่ตรง
                note = f"ไม่พบรหัส {row['hosp_code']} และไม่พบชื่อที่ใกล้พอในระบบ"
                if best_import:
                    alt_code, alt_name = best_import[1]["code"], best_import[1]["name"]
                    alt_note = f"ตัวเลือกจากไฟล์นำเข้า คะแนน {best_import[0]:.2f}"

        if alt_note and not alt_code:
            alt_note = ""

        others = []
        for score, item in live_suggestions[1:4]:
            if item["code"] != erp_code:
                others.append(f"{item['code']} {item['name']} ({score:.2f})")
        mapped.append(
            {
                **row,
                "status": status,
                "erp_code": erp_code,
                "erp_name": erp_name,
                "erp_uom": erp_uom,
                "name_same": name_same,
                "note": note,
                "alt_code": alt_code,
                "alt_name": alt_name,
                "alt_note": alt_note,
                "others": " | ".join(others),
                "use_code": erp_code if status == STATUS_ตรงรหัส else "",
            }
        )

    missing_in_file = [item for item in live_items if item["code"] not in used_live]
    return mapped, missing_in_file


def style_header(ws, row, cols):
    for col, _title, _width in cols:
        cell = ws.cell(row, col)
        cell.fill = NAVY_FILL
        cell.font = HEAD
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = THIN


def apply_body(cell, fill=WHITE):
    cell.fill = fill
    cell.font = BODY
    cell.alignment = LEFT
    cell.border = THIN


def write_guide(wb, n_hosp, n_live, n_import):
    ws = wb.active
    ws.title = "คู่มือ"
    ws.sheet_properties.tabColor = NAVY
    ws["A1"] = "Mapping ยอดยกมาคลังยา รพ. วชิระภูเก็ต → รหัสยาในระบบ ERP"
    ws["A1"].font = TITLE
    ws.merge_cells("A1:B1")
    ws["A2"] = (
        "ไฟล์นี้แยกรายการจากไฟล์ยอดยกมาของโรงพยาบาล (ไม่มีรหัสสินค้า) "
        "ว่าตรงกับรหัสยาในระบบหรือไม่"
    )
    ws["A2"].font = SUB
    ws.merge_cells("A2:B2")

    lines = [
        ("แหล่งไฟล์ รพ.", str(SRC.name)),
        ("แหล่งรหัสในระบบตอนนี้", "ฐานข้อมูล VPK-S1 หมวด กลุ่มวัสดุ / 01. เวชภัณฑ์ ยา สินค้าที่ใช้งานอยู่"),
        ("แหล่งรหัสไฟล์นำเข้ายา", str(IMPORT_XLSX.name)),
        ("วันที่สร้างไฟล์", "22 ต.ค. 2569 (เทียบจากระบบ local VPK-S1)"),
        ("จำนวนแถวในไฟล์ รพ.", "ดูชีต สรุป คอลัมน์ B สูตรนับจากชีต ทั้งหมด"),
        ("วิธีจับคู่หลัก", "ใช้คอลัมน์ ID ของไฟล์ รพ. เติมศูนย์หน้าให้ครบ 5 หลัก แล้วเทียบกับรหัสสินค้า (default_code) ในระบบ เช่น 429 → 00429, 80 → 00080"),
        ("วิธีจับคู่สำรอง", "ถ้ารหัสเดิมไม่มีในระบบ จะเทียบชื่อยาหลังตัดคำนำหน้า เช่น [เบิกคุณพุ่ม], ---herb., รูปแบบยา (TAB/CAP) และเทียบความแรง mg/ml"),
        ("รหัสทางเลือก 100xxxx", "จับจากชื่อในไฟล์นำเข้ายา สำหรับกรณีที่ระบบตอนนี้ยังใช้รหัสเดิมของ HIS แต่มีรายการใหม่ในไฟล์นำเข้า"),
        ("สีเขียว", "ตรงรหัส ใช้ยกยอดได้"),
        ("สีเหลือง/ส้ม", "ต้องตรวจทานก่อนใช้รหัส"),
        ("สีแดง", "ไม่พบรายการที่จับคู่ได้ ต้องสร้างสินค้าใหม่หรือระบุรหัสเอง"),
        ("คอลัมน์ให้กรอก", "ในชีต ทั้งหมด คอลัมน์ P (รหัสที่ใช้ยกยอด) กรอกได้ แถวสีเขียวระบบใส่รหัสให้แล้ว"),
        ("สมมติฐาน", "หนึ่งรหัสยาอาจมีหลายแถวเพราะขนาดบรรจุต่างกัน (กล่อง 100 / กล่อง 500) รหัส ERP เป็นตัวเดียวกัน จำนวนยกมาต้องรวมหรือแยกตามหน่วยที่ใช้เก็บของจริง"),
        ("สิ่งที่ไฟล์นี้ยังไม่ทำ", "ยังไม่สร้างสต็อกเข้าคลัง และยังไม่แปลงขนาดบรรจุเป็นหน่วยนับในระบบ"),
    ]
    ws["A4"] = "หัวข้อ"
    ws["B4"] = "รายละเอียด"
    style_header(ws, 4, [(1, "", 28), (2, "", 90)])
    for i, (k, v) in enumerate(lines, start=5):
        ws.cell(i, 1, k)
        ws.cell(i, 2, v)
        apply_body(ws.cell(i, 1), HINT)
        apply_body(ws.cell(i, 2), WHITE)
        ws.cell(i, 1).font = BOLD
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 92
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 32
    for r in range(4, 5 + len(lines)):
        ws.row_dimensions[r].height = 36
    ws.freeze_panes = "A5"
    ws.sheet_view.showGridLines = False
    return n_hosp, n_live, n_import


ALL_COLS = [
    (1, "ลำดับ", 8),
    (2, "รหัสเดิม รพ. (ID)", 14),
    (3, "รหัสเดิมเติมศูนย์", 14),
    (4, "ชื่อจากไฟล์ รพ.", 46),
    (5, "ขนาดบรรจุ", 16),
    (6, "ราคาหน่วยละ", 12),
    (7, "จำนวนยกมา", 12),
    (8, "สถานะการจับคู่", 24),
    (9, "รหัสในระบบ ERP", 16),
    (10, "ชื่อในระบบ ERP", 46),
    (11, "หน่วยนับในระบบ", 14),
    (12, "ชื่อตรงกัน", 12),
    (13, "หมายเหตุการจับคู่", 42),
    (14, "รหัสทางเลือกในไฟล์นำเข้า", 18),
    (15, "ชื่อทางเลือกในไฟล์นำเข้า", 42),
    (16, "รหัสที่ใช้ยกยอด (กรอก/ตรวจแล้ว)", 22),
    (17, "ตัวเลือกอื่นในระบบ", 40),
]


def write_all(ws, rows):
    ws.sheet_properties.tabColor = "2E7D32"
    ws["A1"] = "รายการจากไฟล์ยอดยกมาของ รพ. ทั้งไฟล์ พร้อมผลการจับคู่รหัสยาในระบบ ERP"
    ws["A1"].font = TITLE
    ws.merge_cells("A1:Q1")
    for col, title, width in ALL_COLS:
        ws.cell(2, col, title)
        ws.column_dimensions[get_column_letter(col)].width = width
    style_header(ws, 2, ALL_COLS)
    ws.row_dimensions[2].height = 32
    for i, row in enumerate(rows, start=3):
        values = [
            row["seq"],
            row["hosp_id"],
            row["hosp_code"],
            row["name"],
            row["pack"],
            row["price"],
            row["qty"],
            row["status"],
            row["erp_code"],
            row["erp_name"],
            row["erp_uom"],
            row["name_same"],
            row["note"],
            row["alt_code"],
            row["alt_name"],
            row["use_code"],
            row["others"],
        ]
        fill = STATUS_FILL.get(row["status"], WHITE)
        for col, val in enumerate(values, start=1):
            cell = ws.cell(i, col, val)
            apply_body(cell, YELLOW if col == 16 and row["status"] != STATUS_ตรงรหัส else fill)
            if col in (6, 7):
                cell.number_format = "#,##0.00" if col == 6 else "#,##0"
                cell.alignment = Alignment(vertical="center", horizontal="right")
        ws.row_dimensions[i].height = 22
    last = 2 + len(rows)
    ws.auto_filter.ref = f"A2:Q{last}"
    ws.freeze_panes = "A3"
    ws.auto_filter.add_sort_condition("H3:H{}".format(last))
    return last


def write_summary(ws, rows):
    from collections import Counter

    counts = Counter(r["status"] for r in rows)

    ws.sheet_properties.tabColor = "C62828"
    ws["A1"] = "สรุปผลการจับคู่รหัสยา"
    ws["A1"].font = TITLE
    ws.merge_cells("A1:E1")
    ws["A2"] = (
        "คอลัมน์ B–D เป็นสูตรนับจากชีต ทั้งหมด จะอัปเดตเมื่อเปิดด้วย Excel "
        "คอลัมน์ E เป็นยอดนับ ณ วันสร้างไฟล์ 22 ต.ค. 2569 จากฐาน VPK-S1"
    )
    ws["A2"].font = SUB
    ws.merge_cells("A2:E2")

    headers = ["สถานะการจับคู่", "จำนวนแถว", "แถวที่ยกมา > 0", "แถวที่ยกมา = 0", "นับ ณ วันสร้างไฟล์"]
    for col, title in enumerate(headers, start=1):
        ws.cell(4, col, title)
    style_header(ws, 4, [(1, "", 32), (2, "", 14), (3, "", 16), (4, "", 16), (5, "", 20)])

    statuses = [
        STATUS_ตรงรหัส,
        STATUS_ชื่อต่าง,
        STATUS_ใกล้เคียง,
        STATUS_มีในไฟล์นำเข้า,
        STATUS_ไม่ตรง,
    ]
    for i, status in enumerate(statuses, start=5):
        ws.cell(i, 1, status)
        ws.cell(i, 2, f'=COUNTIF(ทั้งหมด!H:H,A{i})')
        ws.cell(i, 3, f'=COUNTIFS(ทั้งหมด!H:H,A{i},ทั้งหมด!G:G,">0")')
        ws.cell(i, 4, f'=COUNTIFS(ทั้งหมด!H:H,A{i},ทั้งหมด!G:G,0)')
        ws.cell(i, 5, counts.get(status, 0))
        fill = STATUS_FILL[status]
        for col in range(1, 6):
            apply_body(ws.cell(i, col), fill)
            if col > 1:
                ws.cell(i, col).number_format = "#,##0"
                ws.cell(i, col).alignment = Alignment(vertical="center", horizontal="center")

    ws.cell(10, 1, "รวมทั้งไฟล์")
    ws.cell(10, 2, "=SUM(B5:B9)")
    ws.cell(10, 3, "=SUM(C5:C9)")
    ws.cell(10, 4, "=SUM(D5:D9)")
    ws.cell(10, 5, "=SUM(E5:E9)")
    for col in range(1, 6):
        apply_body(ws.cell(10, col), HINT)
        ws.cell(10, col).font = BOLD
        if col > 1:
            ws.cell(10, col).number_format = "#,##0"
            ws.cell(10, col).alignment = Alignment(vertical="center", horizontal="center")

    ws["A12"] = "ตรวจความครบของแถว (ต้องเท่ากับจำนวนแถวในไฟล์ รพ.)"
    ws["A12"].font = BOLD
    ws.merge_cells("A12:D12")
    ws["A13"] = "จำนวนแถวในชีต ทั้งหมด"
    ws["B13"] = '=COUNTA(ทั้งหมด!D:D)-1'
    ws["C13"] = "ลบหัวตาราง 1 แถว"
    apply_body(ws.cell(13, 1), WHITE)
    apply_body(ws.cell(13, 2), HINT)
    apply_body(ws.cell(13, 3), WHITE)
    ws["B13"].number_format = "#,##0"

    ws["A15"] = "คำอธิบายสถานะ"
    ws["A15"].font = BOLD
    notes = [
        (STATUS_ตรงรหัส, "รหัสเดิมของ รพ. มีในระบบ และชื่อตรงหรือเทียบเท่า ใช้ยกยอดได้"),
        (STATUS_ชื่อต่าง, "รหัสตรงกัน แต่ตัวสะกด/วงเล็บของชื่อต่างจากระบบ ตรวจทานก่อน"),
        (STATUS_ใกล้เคียง, "รหัสเดิมไม่มีในระบบ แต่พบชื่อใกล้เคียง ต้องยืนยันด้วยตา"),
        (STATUS_มีในไฟล์นำเข้า, "ยังไม่มีในระบบตอนนี้ แต่มีรหัสในไฟล์นำเข้ายา"),
        (STATUS_ไม่ตรง, "ไม่พบรหัสและไม่พบชื่อที่ใกล้พอ ต้องสร้างสินค้าใหม่หรือหารหัสเอง"),
    ]
    ws.cell(16, 1, "สถานะ")
    ws.cell(16, 2, "ความหมาย")
    style_header(ws, 16, [(1, "", 32), (2, "", 70)])
    for i, (status, text) in enumerate(notes, start=17):
        ws.cell(i, 1, status)
        ws.cell(i, 2, text)
        apply_body(ws.cell(i, 1), STATUS_FILL[status])
        apply_body(ws.cell(i, 2), WHITE)

    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 22
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 32
    ws.freeze_panes = "A5"
    ws.sheet_view.showGridLines = False


def write_review(ws, rows):
    review = [r for r in rows if r["status"] != STATUS_ตรงรหัส]
    ws.sheet_properties.tabColor = "EF6C00"
    ws["A1"] = "เฉพาะรายการที่ต้องตรวจทาน หรือยังจับคู่ไม่ได้"
    ws["A1"].font = TITLE
    ws.merge_cells("A1:Q1")
    ws["A2"] = "กรองมาจากชีต ทั้งหมด โดยไม่รวมสถานะ ตรงรหัส — ตรวจคอลัมน์ P แล้วใส่รหัสที่ใช้ยกยอด"
    ws["A2"].font = SUB
    ws.merge_cells("A2:Q2")
    for col, title, width in ALL_COLS:
        ws.cell(3, col, title)
        ws.column_dimensions[get_column_letter(col)].width = width
    style_header(ws, 3, ALL_COLS)
    for i, row in enumerate(review, start=4):
        values = [
            row["seq"],
            row["hosp_id"],
            row["hosp_code"],
            row["name"],
            row["pack"],
            row["price"],
            row["qty"],
            row["status"],
            row["erp_code"],
            row["erp_name"],
            row["erp_uom"],
            row["name_same"],
            row["note"],
            row["alt_code"],
            row["alt_name"],
            row["use_code"],
            row["others"],
        ]
        fill = STATUS_FILL.get(row["status"], WHITE)
        for col, val in enumerate(values, start=1):
            cell = ws.cell(i, col, val)
            apply_body(cell, YELLOW if col == 16 else fill)
            if col in (6, 7):
                cell.number_format = "#,##0.00" if col == 6 else "#,##0"
        ws.row_dimensions[i].height = 22
    last = 3 + max(len(review), 1)
    ws.auto_filter.ref = f"A3:Q{last}"
    ws.freeze_panes = "A4"
    return len(review)


def write_missing(ws, missing):
    ws.sheet_properties.tabColor = "1565C0"
    ws["A1"] = "ยาที่อยู่ในระบบ ERP แต่ไม่มีในไฟล์ยอดยกมาของ รพ."
    ws["A1"].font = TITLE
    ws.merge_cells("A1:D1")
    ws["A2"] = (
        "ใช้ตรวจว่ามีรายการในคลังยาที่ระบบมีแล้วแต่โรงพยาบาลไม่ได้ส่งยอดมา "
        "ไม่ใช่รายการจากไฟล์ยกมา"
    )
    ws["A2"].font = SUB
    ws.merge_cells("A2:D2")
    cols = [(1, "รหัสในระบบ ERP", 18), (2, "ชื่อในระบบ ERP", 62), (3, "หน่วยนับ", 14), (4, "หมวดหมู่", 36)]
    for col, title, width in cols:
        ws.cell(3, col, title)
        ws.column_dimensions[get_column_letter(col)].width = width
    style_header(ws, 3, cols)
    for i, item in enumerate(missing, start=4):
        ws.cell(i, 1, item["code"])
        ws.cell(i, 2, item["name"])
        ws.cell(i, 3, item["uom"])
        ws.cell(i, 4, item["categ"])
        for col in range(1, 5):
            apply_body(ws.cell(i, col), WHITE)
        ws.row_dimensions[i].height = 20
    last = 3 + max(len(missing), 1)
    ws.auto_filter.ref = f"A3:D{last}"
    ws.freeze_panes = "A4"
    ws["F3"] = "จำนวนรายการ"
    ws["G3"] = f"=COUNTA(A:A)-3"
    apply_body(ws.cell(3, 6), HINT)
    apply_body(ws.cell(3, 7), HINT)
    ws.cell(3, 6).font = BOLD
    ws["G3"].number_format = "#,##0"
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 14


def main():
    with tempfile.TemporaryDirectory() as tmp:
        live_csv = Path(tmp) / "vpk_s1_drugs.csv"
        live_items = dump_live_drugs(live_csv)
    import_items = load_import_drugs()
    hospital = load_hospital()
    mapped, missing = map_rows(hospital, live_items, import_items)

    from collections import Counter

    counts = Counter(r["status"] for r in mapped)
    print("hospital rows", len(hospital))
    print("live drugs", len(live_items))
    print("import drugs", len(import_items))
    print("status", dict(counts))
    print("review", sum(1 for r in mapped if r["status"] != STATUS_ตรงรหัส))
    print("missing in hosp file", len(missing))

    wb = Workbook()
    write_guide(wb, len(hospital), len(live_items), len(import_items))
    ws_sum = wb.create_sheet("สรุป", 1)
    ws_all = wb.create_sheet("ทั้งหมด", 2)
    ws_rev = wb.create_sheet("ต้องตรวจทาน", 3)
    ws_miss = wb.create_sheet("ในระบบแต่ไม่มีในไฟล์รพ", 4)
    write_all(ws_all, mapped)
    write_summary(ws_sum, mapped)
    write_review(ws_rev, mapped)
    write_missing(ws_miss, missing)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
