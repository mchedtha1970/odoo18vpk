#!/usr/bin/env python3
"""รอให้ Odoo พร้อม แล้วเปิดหน้า login ใน Google Chrome อัตโนมัติ

รัน:
    python scripts/playwright/open_login.py                  เปิดหน้า login อย่างเดียว
    python scripts/playwright/open_login.py --user uat.dept  เปิดแล้วเข้าสู่ระบบให้ด้วย

ตัวแปรที่ใช้ได้: ODOO_URL, ODOO_USER, ODOO_PASSWORD
รหัสผ่านอ่านจาก ODOO_PASSWORD ถ้าไม่ตั้งไว้จะใช้รหัสของผู้ใช้ทดสอบในหน้า login
หน้าต่างจะเปิดค้างไว้จนกว่าจะปิดเอง (ยกเว้นตอนใช้ --headless)
"""

import argparse
import asyncio
import os
import sys

from playwright.async_api import async_playwright

from odoo_session import (
    LOGIN_URL,
    launch_browser,
    open_login_page,
    submit_login,
    wait_for_server,
)


def parse_args():
    parser = argparse.ArgumentParser(description="เปิดหน้า login ของ Odoo อัตโนมัติ")
    parser.add_argument(
        "--user",
        default=os.environ.get("ODOO_USER"),
        help="ชื่อผู้ใช้ที่จะเข้าสู่ระบบ ถ้าไม่ระบุจะเปิดหน้า login ค้างไว้",
    )
    parser.add_argument(
        "--wait", type=int, default=180, help="เวลารอ Odoo พร้อม (วินาที)"
    )
    parser.add_argument(
        "--headless", action="store_true", help="ไม่แสดงหน้าต่าง และจบทันทีเมื่อโหลดเสร็จ"
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    print(f"รอ Odoo ที่ {LOGIN_URL} ...")
    wait_for_server(args.wait)

    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, headless=args.headless)
        page = await browser.new_page(no_viewport=not args.headless)
        await open_login_page(page)
        print("เปิดหน้า login แล้ว")

        if args.user:
            await submit_login(page, args.user)
            print(f"เข้าสู่ระบบเป็น {args.user} แล้ว: {page.url}")

        if not args.headless:
            print("ปิดหน้าต่างเบราว์เซอร์เพื่อจบสคริปต์")
            await page.wait_for_event("close", timeout=0)
        await browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
