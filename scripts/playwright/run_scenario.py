#!/usr/bin/env python3
"""รัน scenario ทดสอบแบบ headless ตรวจผล แล้วเขียนรายงานลง scripts/playwright/reports/

รัน:
    python scripts/playwright/run_scenario.py --list
    python scripts/playwright/run_scenario.py purchase_medicine

ตรวจ 3 จุด: script จบสำเร็จ, สถานะเอกสารในฐานข้อมูล และ error ใน log ของ Odoo
รันได้เฉพาะ Odoo บนเครื่องนี้ เพราะ scenario สร้างข้อมูลและอนุมัติเอกสารจริงในฐานข้อมูล
exit code: 0 ผ่าน, 1 ไม่ผ่าน, 2 รันไม่ได้
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from odoo_session import BASE_URL, wait_for_server

HERE = Path(__file__).resolve().parent
REPORT_ROOT = HERE / "reports"
ODOO_CONTAINER = os.environ.get("ODOO_CONTAINER", "odoo18vpk-docker-odoo-1")
DB_CONTAINER = os.environ.get("DB_CONTAINER", "odoo18vpk-docker-db-1")
DB_NAME = os.environ.get("ODOO_DB", "VPK-S1")
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
LOG_ERROR = re.compile(r"^\S+ \S+ \d+ (ERROR|CRITICAL) |^Traceback ", re.M)
# cron ล้างข้อมูลชั่วคราวของรายงานบัญชีล้มเหลวเป็นระยะ ไม่เกี่ยวกับ scenario
LOG_IGNORE = re.compile(r"ir_autovacuum: Failed account\.report")
LOG_TIME = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ ")

# แต่ละ capture ดึงเลขเอกสารจากผลลัพธ์ของ script แล้วเทียบสถานะในตารางที่ระบุ
SCENARIOS = {
    "purchase_medicine": {
        "title": "ใบขอซื้อยา เอกสารลงนาม ถึงสร้างรายการ e-GP",
        "script": "create_medicine_purchase_request.py",
        "checks": [
            {
                "label": "ใบขอซื้อ",
                "capture": r"สร้างใบขอซื้อแล้ว:\s*(\S+)",
                "table": "purchase_request",
                "states": ["in_progress"],
            },
            {
                "label": "รายการ e-GP",
                "capture": r"สร้างรายการ e-GP แล้ว:\s*(\S+)",
                "table": "purchase_requisition",
                "states": ["draft"],
            },
            {
                "label": "บันทึกข้อความอนุมัติขอซื้อ",
                "capture": r"เอกสารลงนามครบ บันทึกข้อความอนุมัติขอซื้อ:\s*(\S+)",
                "table": "vpk_document_studio_document",
                "states": ["approved"],
            },
            {
                "label": "คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ",
                "capture": r"เอกสารลงนามครบ คำสั่งแต่งตั้งคณะกรรมการตรวจรับพัสดุ:\s*(\S+)",
                "table": "vpk_document_studio_document",
                "states": ["approved"],
            },
            {
                "label": "รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
                "capture": r"เอกสารลงนามครบ รายงานขออนุมัติจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง:\s*(\S+)",
                "table": "vpk_document_studio_document",
                "states": ["approved"],
            },
        ],
    },
}


def db_state(table, name):
    """อ่านอย่างเดียว ค่า name มาจากผลลัพธ์ของ script จึงส่งเป็นตัวแปรของ psql."""
    sql = f"SELECT state FROM {table} WHERE name = :'doc_name' ORDER BY id DESC LIMIT 1"
    result = subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", "odoo", "-d", DB_NAME,
         "-At", "-v", "ON_ERROR_STOP=1", "-v", f"doc_name={name}"],
        input=sql,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def odoo_errors(since):
    """คืนบรรทัด ERROR, CRITICAL และ Traceback ของ Odoo ตั้งแต่เริ่มรัน."""
    # ไม่ใช้ docker logs --since เพราะคืนค่าว่างบน Docker Desktop จึงกรองเวลาจากบรรทัด log เอง
    result = subprocess.run(
        ["docker", "logs", "--tail", "20000", ODOO_CONTAINER],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise RuntimeError(f"อ่าน log ของ Odoo ไม่ได้: {result.stderr.strip()}")
    errors = []
    record = None
    for line in (result.stdout + result.stderr).splitlines() + ["0000-00-00 00:00:00,000 "]:
        stamp = LOG_TIME.match(line)
        if stamp:
            if record and LOG_ERROR.search("\n".join(record)):
                if not LOG_IGNORE.search(record[0]):
                    errors.append(record[0])
            record = [line] if stamp.group(1) >= since else None
        elif record:
            record.append(line)
    return errors


def run_checks(scenario, output):
    checks = []
    for check in scenario["checks"]:
        match = re.search(check["capture"], output)
        name = match.group(1) if match else ""
        state = db_state(check["table"], name) if name else ""
        checks.append(
            {
                "label": check["label"],
                "document": name,
                "state": state,
                "expected": check["states"],
                "passed": state in check["states"],
            }
        )
    return checks


def write_report(folder, report, output):
    (folder / "output.log").write_text(output, encoding="utf-8")
    (folder / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        f"# {report['title']}",
        "",
        f"ผล: {'ผ่าน' if report['passed'] else 'ไม่ผ่าน'}",
        f"เริ่มรัน: {report['started_at']} ใช้เวลา {report['seconds']} วินาที",
        f"script exit code: {report['exit_code']}",
        "",
        "| รายการ | เอกสาร | สถานะ | ที่คาดหวัง | ผล |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            "| %s | %s | %s | %s | %s |"
            % (
                check["label"],
                check["document"] or "-",
                check["state"] or "-",
                ", ".join(check["expected"]),
                "ผ่าน" if check["passed"] else "ไม่ผ่าน",
            )
        )
    if report["skipped"]:
        lines += ["", "ขั้นตอนที่ถูกข้าม (ยังไม่ได้ทดสอบ):"]
        lines += [f"- {item}" for item in report["skipped"]]
    lines += ["", f"Odoo log error: {len(report['odoo_errors'])} บรรทัด"]
    lines += [f"- {line}" for line in report["odoo_errors"][:20]]
    if report["screenshot"]:
        lines += ["", f"ภาพหน้าจอ: {report['screenshot']}"]
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(name, timeout):
    scenario = SCENARIOS[name]
    started = datetime.now(timezone.utc)
    folder = REPORT_ROOT / f"{started:%Y%m%d-%H%M%S}-{name}"
    folder.mkdir(parents=True)
    screenshot = folder / "error.png"
    print(f"รัน {name}: {scenario['title']}")

    env = dict(os.environ, HEADLESS="1", HOLD_SECONDS="0", SCREENSHOT_PATH=str(screenshot))
    try:
        result = subprocess.run(
            [sys.executable, "-u", str(HERE / scenario["script"])],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired as error:
        exit_code = -1
        output = (error.stdout or b"").decode("utf-8", "replace")
        output += f"\nหมดเวลา {timeout} วินาที\n"

    finished = datetime.now(timezone.utc)
    errors = odoo_errors(started.strftime("%Y-%m-%d %H:%M:%S"))
    checks = run_checks(scenario, output)
    report = {
        "scenario": name,
        "title": scenario["title"],
        "passed": exit_code == 0 and all(c["passed"] for c in checks) and not errors,
        "exit_code": exit_code,
        "started_at": started.isoformat(timespec="seconds"),
        "seconds": round((finished - started).total_seconds()),
        "checks": checks,
        "skipped": re.findall(r"^ข้าม:\s*(.+)$", output, re.M),
        "odoo_errors": errors,
        "screenshot": str(screenshot) if screenshot.exists() else "",
    }
    write_report(folder, report, output)
    print("ผล:", "ผ่าน" if report["passed"] else "ไม่ผ่าน")
    print("รายงาน:", folder / "report.md")
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description="รัน scenario ทดสอบ Odoo")
    parser.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS))
    parser.add_argument("--list", action="store_true", help="แสดงรายการ scenario")
    parser.add_argument("--timeout", type=int, default=600, help="เวลาสูงสุดต่อ scenario (วินาที)")
    args = parser.parse_args()

    if args.list:
        for name, scenario in sorted(SCENARIOS.items()):
            print(f"{name}: {scenario['title']}")
        return 0
    if not args.scenario:
        parser.error("ระบุ scenario หรือใช้ --list")
    if urlparse(BASE_URL).hostname not in LOCAL_HOSTS:
        print(f"ไม่รัน: {BASE_URL} ไม่ใช่ Odoo บนเครื่องนี้")
        return 2
    wait_for_server(60)
    return run(args.scenario, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
