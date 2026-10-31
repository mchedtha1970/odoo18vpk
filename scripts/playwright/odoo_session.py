"""ส่วนกลางของ script Playwright: รอ Odoo พร้อม เปิด Chrome และเข้าสู่ระบบ

ตัวแปรที่ใช้ได้: ODOO_URL, ODOO_PASSWORD
รหัสผ่านอ่านจาก ODOO_PASSWORD ถ้าไม่ตั้งไว้จะใช้รหัสของผู้ใช้ทดสอบในหน้า login
"""

import os
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("ODOO_URL", "http://127.0.0.1:8069").rstrip("/")
LOGIN_URL = f"{BASE_URL}/web/login"


def wait_for_server(timeout=180):
    """รอจน /web/login ตอบ 200 ระหว่าง Odoo เพิ่งสตาร์ตอาจตอบ error หรือยังไม่รับการเชื่อมต่อ."""
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(LOGIN_URL, timeout=30) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError) as error:
            last_error = error
        time.sleep(2)
    raise SystemExit(f"Odoo ไม่พร้อมภายใน {timeout} วินาที: {LOGIN_URL} ({last_error})")


async def launch_browser(playwright, headless=False, slow_mo=0):
    return await playwright.chromium.launch(
        channel="chrome", headless=headless, slow_mo=slow_mo
    )


async def open_login_page(page):
    await page.goto(LOGIN_URL, wait_until="load")
    await page.locator("#login").wait_for(state="visible")


async def submit_login(page, user, password=None):
    password = password or os.environ.get("ODOO_PASSWORD", "").strip()
    if not password:
        option = page.locator(f'#vpk_test_user option[value="{user}"]')
        if await option.count():
            password = await option.get_attribute("data-password") or ""
    if not password:
        raise SystemExit(f"ไม่พบรหัสผ่านของ {user} ตั้งค่า ODOO_PASSWORD ก่อนรันสคริปต์")

    # ตั้งค่าตรง ๆ เพราะ fill() พึ่ง focus ทำให้ช่องรหัสผ่านว่างเป็นบางครั้ง
    await page.evaluate(
        """([login, passwordValue]) => {
            document.querySelector('#login').value = login;
            document.querySelector('#password').value = passwordValue;
        }""",
        [user, password],
    )
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
        await page.locator("button.vpk-login-submit").click()

    # login ไม่ผ่าน Odoo จะแสดงหน้า /web/login เดิมพร้อมข้อความแจ้งเตือน
    if "/web/login" in page.url:
        alert = page.locator(".alert-danger")
        message = await alert.first.inner_text() if await alert.count() else ""
        raise SystemExit(f"เข้าสู่ระบบไม่สำเร็จ: {message.strip()}")


async def login_as(page, user, password=None):
    await page.goto(f"{BASE_URL}/web/session/logout", wait_until="domcontentloaded")
    await open_login_page(page)
    await submit_login(page, user, password)
