#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""สร้างเอกสารออกแบบธีมหลังบ้าน (vpk_sidebar_menu) และหน้า Login (vpk_login_page) เป็นไฟล์ Word

ภาพประกอบ: python3 scripts/playwright/shot_theme_design.py
รัน: python3 docs/build_theme_design_docx.py
ผลลัพธ์: docs/เอกสารออกแบบ-Theme-ERP-VPK.docx
"""
from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from build_his_interface_design_docx import (
    DOCS,
    NAVY,
    TEAL,
    SpecDoc,
    add_page_number,
    set_run_font,
)

OUT = DOCS / "เอกสารออกแบบ-Theme-ERP-VPK.docx"
FIG = DOCS / "manual_assets" / "figures" / "theme"
DOC_CODE = "VPK-THEME-DD-001"


class ThemeDoc(SpecDoc):
    def __init__(self):
        super().__init__()
        self.fig_no = 0

    def _setup_page(self):
        super()._setup_page()
        section = self.doc.sections[0]
        hp = section.header.paragraphs[0]
        hp.clear()
        r = hp.add_run("โรงพยาบาลวชิระภูเก็ต  ·  Theme Design (Odoo 18)")
        set_run_font(r, size=11, color=NAVY)
        fp = section.footer.paragraphs[0]
        fp.clear()
        r = fp.add_run(f"{DOC_CODE}  ·  ร่าง  ·  หน้า ")
        set_run_font(r, size=11, color=NAVY)
        add_page_number(fp)

    def figure(self, filename, caption, width_cm=16.5):
        path = FIG / filename
        if not path.is_file():
            self.note(f"ไม่พบภาพ {filename} — รัน scripts/playwright/shot_theme_design.py ก่อน")
            return
        self.fig_no += 1
        self.doc.add_picture(str(path), width=Cm(width_cm))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        para = self.p(f"รูปที่ {self.fig_no}  {caption}", size=13, align="center", space_after=10, color=TEAL)
        para.paragraph_format.space_before = Pt(2)


def build():
    d = ThemeDoc()

    # ----- Cover -----
    d.p("โรงพยาบาลวชิระภูเก็ต", size=20, bold=True, align="center", space_after=4, color=NAVY)
    d.p("ระบบ ERP (Odoo 18)", size=15, align="center", space_after=18, color=TEAL)
    d.p("เอกสารออกแบบธีม", size=26, bold=True, align="center", space_after=4, color=NAVY)
    d.p("ธีมหลังบ้านและหน้าเข้าสู่ระบบ", size=22, bold=True, align="center", space_after=6, color=NAVY)
    d.p("Theme Design Document", size=16, align="center", space_after=20, color=TEAL)
    d.p(
        "ครอบคลุม Design Tokens · Sidebar · Theme Settings · Control panel / Form / List / Kanban / Notebook / Chatter / Dialog · หน้า Login",
        size=14,
        align="center",
        space_after=24,
    )
    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["รหัสเอกสาร", DOC_CODE],
            ["เวอร์ชัน", "1.2 (ร่าง)"],
            ["วันที่", "17 พฤศจิกายน 2569"],
            ["สถานะ", "Draft — อ้างอิงจากซอร์สโค้ดปัจจุบัน"],
            ["โมดูลหลัก", "vpk_sidebar_menu v18.0.1.9.0 (ธีมหลังบ้าน)"],
            ["โมดูลร่วม", "vpk_login_page v18.0.1.3.4 (Login / Signup / Reset password)"],
            ["แนวทางออกแบบ", "Modern SaaS (แนว Linear / Stripe / Notion) ตาม modern_erp_ai_guidelines.md: โทน slate สีหลักน้ำเงิน ข้อมูลหนาแน่นแต่อ่านง่าย เงาบาง"],
            ["ผู้ใช้เอกสาร", "ทีมพัฒนา · ผู้ดูแลระบบ · ผู้ออกแบบ UX/UI"],
        ],
        col_widths=[5.0, 12.0],
    )

    # ----- 1 Overview -----
    d.page_break()
    d.h1("วัตถุประสงค์และขอบเขต")
    d.p(
        "ธีมนี้เปลี่ยนหน้าตา Odoo 18 หลังบ้านจากเมนูแนวนอนด้านบนเป็น Sidebar แนวตั้งด้านซ้าย "
        "พร้อมระบบตั้งค่าธีม (สี ฟอนต์ ขนาด ตำแหน่ง Chatter ฯลฯ) ที่เป็นค่ากลางชุดเดียวทั้งระบบ "
        "แก้ไขได้เฉพาะ System Administrator และปรับสไตล์ทั้งระบบเป็นแนว Modern SaaS "
        "ได้แก่ ปุ่ม แท็บ ฟิลด์ฟอร์ม ตารางข้อมูล ป้ายสถานะ และ Dialog",
        align="justify",
    )
    d.h2("ขอบเขตที่ครอบคลุม")
    d.bullets(
        [
            "Navbar / App menu → Sidebar สีขาวพร้อมเมนูย่อยซ้อนหลายชั้น และปุ่มค้นหาเมนู (⌘K / Ctrl K)",
            "Theme Settings panel (ค่ากลางทั้งระบบ เปิดได้เฉพาะ System Administrator)",
            "สไตล์ Control panel, Form view, List view, Kanban, Notebook, Chatter, Dialog/Wizard, Dropdown, Systray และป้ายสถานะ",
            "ฟอนต์ Inter + Noto Sans Thai (ค่าเริ่มต้น) และ IBM Plex Sans Thai / Anuphan / Kanit / Sarabun / Prompt / Roboto ทั้งหลังบ้านและหน้า Portal",
            "ไอคอนลายเส้น Lucide ใน sidebar และ systray, RemixIcon แทน FontAwesome บางส่วนในหน้าจออื่น",
            "หน้า Login แบบเต็มจอสองคอลัมน์ (โมดูล vpk_login_page)",
            "ฟิลด์ HTML แบบ TinyMCE (widget tinymce_html) ที่อยู่ในโมดูลเดียวกัน",
        ]
    )
    d.note("รายงาน PDF (QWeb report), หน้า Website สาธารณะ และสีของหน้า Login อยู่นอกขอบเขตการปรับสไตล์รอบนี้")
    d.h2("หลักการออกแบบ (จาก guideline)")
    d.table(
        ["หลักการ", "การนำไปใช้ในธีม"],
        [
            ["พื้นที่ทำงานสะอาด", "พื้นแอป slate-50 #f8fafc, การ์ด/sidebar/ตารางพื้นขาวมีเส้นขอบ slate-200 #e2e8f0"],
            ["สีหลักใช้เท่าที่จำเป็น", "น้ำเงิน blue-600 #2563eb (hover blue-700 #1d4ed8) ใช้กับปุ่มหลัก ลิงก์ เมนูที่ active และ focus ring เท่านั้น"],
            ["ลำดับตัวอักษร", "หัวข้อ slate-900 #0f172a, ตัวอักษรรอง slate-500/600, หัวตารางตัวเล็ก พิมพ์ใหญ่ เว้นระยะตัวอักษร"],
            ["ตัวเลขอ่านง่าย", "tabular-nums ในตาราง ฟิลด์ตัวเลข/วันที่ และ stat button; ตัวเลขชิดขวา"],
            ["เงาบาง", "shadow-sm กับการ์ด/ปุ่ม; เงากลางกับ dropdown; เงาใหญ่สุดกับ dialog"],
            ["มุมโค้ง", "การ์ด 12px (rounded-xl), ปุ่มและช่องกรอก 6px (rounded-md)"],
            ["สถานะเป็นป้ายอ่อน", "พื้นสี -50 ตัวอักษร -700 ขอบ -200 (เขียว/เหลือง/แดง/น้ำเงิน/เทา)"],
            ["ลดสิ่งรบกวน", "ปุ่มรองในแถวตาราง (ลบ, เปิดฟอร์ม) แสดงเมื่อชี้แถวเท่านั้น"],
        ],
        col_widths=[4.5, 12.5],
    )
    d.figure("02_sidebar_list.png", "ภาพรวมหน้าจอหลังบ้าน: Sidebar สีขาวและตารางใบขอซื้อในกรอบการ์ด")

    # ----- 2 Architecture -----
    d.h1("สถาปัตยกรรมโดยรวม")
    d.code(
        "ผู้ใช้ login → WebClient (patch) onMounted\n"
        "  → ใส่ class o_vpk_sidebar_menu ที่ <body>\n"
        "  → applyThemeConfig(DEFAULT_THEME_CONFIG)          ค่าเริ่มต้นก่อนโหลด\n"
        "  → RPC /vpk/theme/config → vpk.theme.config (record กลาง vpk_theme_config_global)\n"
        "  → applyThemeConfig(config)\n"
        "       ├─ body classes   vpk_theme_*, vpk_font_*, vpk_chatter_*, ...\n"
        "       ├─ CSS variables  --vpk-* บน :root\n"
        "       └─ <style> ที่ JS สร้าง (systray grid / notebook)\n"
        "  → SCSS ทุกไฟล์อ่านค่าผ่าน var(--vpk-*)\n"
        "\n"
        "Theme Settings panel (เฉพาะ System Administrator)\n"
        "  เปลี่ยนค่า → applyThemeConfig(draft)              preview สด ยังไม่บันทึก\n"
        "  Apply      → RPC /vpk/theme/config/save           ตรวจ base.group_system\n"
        "             → vpk.theme.config (record กลาง)        มีผลกับผู้ใช้ทุกคน\n"
        "                └─ font_family, font_size → หน้า Portal / Login"
    )
    d.h2("หลักการสำคัญ")
    d.bullets(
        [
            "ค่าธีมทุกตัวกลายเป็น CSS custom property บน document.documentElement ผ่านฟังก์ชันเดียว "
            "applyThemeConfig() (static/src/js/theme_utils.js) SCSS ไม่ฮาร์ดโค้ดสีหลัก จึงเปลี่ยนธีมได้ทันทีโดยไม่ต้อง compile asset ใหม่",
            "ทุก rule ถูก scope ด้วย body.o_web_client.o_vpk_sidebar_menu ซึ่งใส่ตอน WebClient mount "
            "ถ้าถอนโมดูลหรือ WebClient ยังไม่ mount สไตล์จะไม่มีผล",
            "ลำดับการโหลด CSS มีผลต่อการ override — ไฟล์ส่วนใหญ่โหลดผ่าน ir.asset แบบ append ที่ sequence 100–120 "
            "เพื่อให้อยู่ท้าย bundle และชนะ CSS ของโมดูลอื่น (เช่น base_accounting_kit) โดย modern_ui.scss (seq 120) โหลดท้ายสุด",
        ]
    )

    # ----- 3 Data model -----
    d.page_break()
    d.h1("Data Model")
    d.h2("vpk.theme.config")
    d.p("ไฟล์: models/vpk_theme_config.py — ทั้งระบบใช้ record กลาง record เดียว")
    d.table(
        ["ฟิลด์", "ชนิด", "ค่าเริ่มต้น", "ค่าที่เลือกได้ / ข้อจำกัด"],
        [
            ["theme_style", "Selection", "rounded", "rounded, standard, square"],
            ["menu_position", "Selection", "vertical", "vertical, horizontal"],
            ["chatter_position", "Selection", "bottom", "right, bottom"],
            ["tree_form_split_view", "Boolean", "False", ""],
            ["list_view_density", "Selection", "comfortable", "comfortable, compact"],
            ["list_view_sticky_header", "Boolean", "False", ""],
            ["sidebar_color", "Char", "#2563eb", "Primary Color — สีหลักของระบบ (ปุ่ม ลิงก์ เมนูที่ active focus ring) ชื่อฟิลด์คงไว้เพื่อความเข้ากันได้"],
            ["sidebar_active_color", "Char", "#1d4ed8", "Primary Hover Color — สีปุ่มหลักตอน hover"],
            ["sidebar_text_color", "Char", "#ffffff", "Text on Primary — ตัวอักษรบนปุ่มหลัก"],
            ["font_family", "Selection", "inter", "default, inter, kanit, sarabun, prompt, roboto"],
            ["font_size", "Selection", "medium", "small, medium, large"],
            ["loader_style", "Selection", "default", "default, dots, bars"],
            ["sidebar_width", "Integer", "256", "clamp 200–420 px ใน create/write"],
            ["sidebar_collapsed_width", "Integer", "80", "clamp 56–120 px"],
        ],
        col_widths=[4.6, 2.4, 2.6, 7.4],
    )
    d.h2("ค่ากลางชุดเดียว (Global) และสิทธิ์")
    d.p(
        "ทั้งระบบมี record เดียวคือ vpk_sidebar_menu.vpk_theme_config_global (สร้างจาก "
        "data/vpk_theme_config_data.xml แบบ noupdate) ผู้ใช้ทุกคนเห็นธีมเดียวกัน และอ่านค่าผ่าน _get_global_config()",
        align="justify",
    )
    d.table(
        ["กลุ่ม", "อ่าน", "แก้ไข / สร้าง", "ลบ"],
        [
            ["base.group_user (ผู้ใช้ทั่วไป)", "✓", "✗", "✗"],
            ["base.group_system (System Administrator)", "✓", "✓", "✗"],
        ],
        col_widths=[8.0, 2.5, 3.5, 3.0],
    )
    d.p(
        "สิทธิ์ถูกบังคับ 3 ชั้น: ACL ใน security/ir.model.access.csv, การตรวจ base.group_system ใน controller "
        "ก่อนบันทึก และการซ่อนปุ่มตั้งค่าธีมในหน้าจอสำหรับผู้ที่ไม่ใช่ admin (user.isSystem)",
        align="justify",
    )
    d.h2("การแชร์ฟอนต์ไปหน้า Portal")
    d.p(
        "หน้า Portal / Vendor / Login อ่าน font_family และ font_size จาก record กลางโดยตรงผ่าน "
        "_get_portal_font_settings() จึงใช้ฟอนต์เดียวกับหลังบ้านเสมอ",
        align="justify",
    )
    d.h2("Migration ที่เกี่ยวข้อง")
    d.table(
        ["เวอร์ชัน", "สิ่งที่ทำ"],
        [
            ["18.0.1.7.54", "ปรับ sidebar_width 240 → 288"],
            ["18.0.1.7.69", "ลดทุกค่า sidebar_width ลง 10%"],
            ["18.0.1.7.70", "แก้ค่าที่ได้จากข้อก่อน (259) กลับเป็น 288"],
            [
                "18.0.1.8.0",
                "เปลี่ยนจากธีมรายผู้ใช้เป็นธีมกลาง: คัดลอกค่าของผู้ใช้ base.user_admin (ถ้าไม่มีใช้ค่าที่บันทึกล่าสุด) "
                "ไปที่ record กลาง ลบ config รายผู้ใช้ ลบฟิลด์ res.users.vpk_theme_config_id และ System Parameter vpk.portal.font_*",
            ],
            [
                "18.0.1.9.0",
                "เปลี่ยนเป็นสไตล์ Modern SaaS: ตั้ง record กลางเป็น rounded, สี #2563eb / #1d4ed8 / #ffffff, ฟอนต์ inter "
                "ขนาด medium, sidebar 256 / 80 px (ค่าอื่น เช่น ตำแหน่ง chatter และ sticky header คงเดิม)",
            ],
        ],
        col_widths=[4.0, 13.0],
    )

    # ----- 4 API -----
    d.h1("API (Controller)")
    d.p("ไฟล์: controllers/main.py — ทั้งสอง route เป็น type='json', auth='user'")
    d.table(
        ["Route", "หน้าที่", "Request / Response"],
        [
            ["/vpk/theme/config", "อ่านธีมกลาง (ผู้ใช้ทุกคน)", "{} → dict ของทุกฟิลด์ในหัวข้อ 3.1"],
            [
                "/vpk/theme/config/save",
                "บันทึกธีมกลาง (เฉพาะ System Administrator)",
                "dict บางฟิลด์ (whitelist ตาม CONFIG_FIELDS) → dict หลังบันทึก",
            ],
        ],
        col_widths=[5.0, 5.0, 7.0],
    )
    d.p(
        "ถ้าผู้ใช้ที่ไม่อยู่ใน base.group_system เรียก /vpk/theme/config/save ระบบจะตอบ AccessError "
        "\"Only System Administrators can change the theme.\" การบันทึกไม่ใช้ sudo() จึงผ่าน ACL ของ Odoo อีกชั้นหนึ่ง",
        align="justify",
    )

    # ----- 5 Tokens -----
    d.page_break()
    d.h1("Design Tokens (CSS Custom Properties)")
    d.p(
        "ค่าเริ่มต้นประกาศใน sidebar_menu.scss (:root) token สีหลัก ขนาด และมุมโค้งถูกเขียนทับตอนรันไทม์โดย "
        "applyThemeConfig() ส่วน token โทน slate เป็นค่าคงที่",
        align="justify",
    )
    d.h2("สีหลัก (ปรับได้จาก Theme Settings)")
    d.table(
        ["Token", "ที่มา", "ใช้กับ"],
        [
            ["--vpk-primary", "sidebar_color", "ปุ่มหลัก ลิงก์ เมนูที่ active แท็บที่ active focus ring checkbox ตัวนับแจ้งเตือน"],
            ["--vpk-primary-hover", "sidebar_active_color", "ปุ่มหลัก/ลิงก์ตอน hover"],
            ["--vpk-on-primary", "sidebar_text_color", "ตัวอักษรบนปุ่มหลัก"],
            ["--vpk-primary-soft", "color-mix(primary 8%, ขาว)", "พื้นเมนูที่ active แถวที่เลือก ป้ายสถานะ primary ขั้น statusbar ปัจจุบัน"],
            ["--vpk-primary-ring", "color-mix(primary 25%, โปร่ง)", "วงแหวน focus ของปุ่มค้นหา sidebar และปุ่มหลัก"],
            ["--o-brand-primary, --o-action", "sidebar_color", "override ตัวแปรของ Odoo core"],
        ],
        col_widths=[4.8, 4.6, 7.6],
    )
    d.h2("สีพื้นผิวและตัวอักษร (คงที่ — slate)")
    d.table(
        ["Token", "ค่า", "Tailwind", "ใช้กับ"],
        [
            ["--vpk-app-bg", "#f8fafc", "slate-50", "พื้นหลังแอป รอบการ์ดฟอร์ม/ตาราง/kanban"],
            ["--vpk-surface", "#ffffff", "white", "sidebar การ์ด ตาราง dialog control panel"],
            ["--vpk-surface-muted", "#f8fafc", "slate-50", "หัวตาราง แถว hover footer dialog ช่องค้นหา"],
            ["--vpk-hover-bg", "#f1f5f9", "slate-100", "hover ของเมนู ปุ่มไอคอน dropdown item"],
            ["--vpk-border", "#e2e8f0", "slate-200", "ขอบการ์ด ช่องกรอก เส้นแบ่งหลัก"],
            ["--vpk-border-subtle", "#f1f5f9", "slate-100", "เส้นแบ่งแถวตาราง"],
            ["--vpk-field-border-hover", "#cbd5e1", "slate-300", "ขอบช่องกรอกตอน hover"],
            ["--vpk-text", "#0f172a", "slate-900", "ตัวอักษรหลัก หัวข้อ"],
            ["--vpk-text-secondary", "#475569", "slate-600", "label ฟอร์ม เมนู sidebar"],
            ["--vpk-text-muted", "#64748b", "slate-500", "หัวตาราง คำทักทาย ไอคอน systray"],
            ["--vpk-text-faint", "#94a3b8", "slate-400", "ลูกศรเมนู ไอคอนรอง"],
        ],
        col_widths=[4.6, 2.2, 2.4, 7.8],
    )
    d.note(
        "Token ชื่อเดิม (--vpk-sidebar-bg-start, -bg-end, -bg-gradient, -bg, -text, --vpk-primary-color, "
        "--vpk-primary-color-dark) ยังตั้งค่าอยู่เพื่อให้โมดูลอื่นใช้ได้ แต่ชี้ไปที่สีหลัก (-bg-gradient เป็นสีเรียบแล้ว)"
    )
    d.h2("ป้ายสถานะ (Status pills)")
    d.table(
        ["สถานะ", "คลาส Odoo", "พื้น", "ตัวอักษร", "ขอบ"],
        [
            ["สำเร็จ", "text-bg-success", "#ecfdf5", "#047857", "#a7f3d0"],
            ["รอดำเนินการ", "text-bg-warning", "#fffbeb", "#b45309", "#fde68a"],
            ["ผิดพลาด/ยกเลิก", "text-bg-danger", "#fff1f2", "#be123c", "#fecdd3"],
            ["ข้อมูล", "text-bg-info", "#eff6ff", "#1d4ed8", "#bfdbfe"],
            ["หลัก", "text-bg-primary", "primary-soft", "primary", "primary 25%"],
            ["ทั่วไป", "text-bg-secondary / light / muted", "#f1f5f9", "#475569", "#e2e8f0"],
        ],
        col_widths=[3.0, 4.8, 3.0, 3.0, 3.2],
    )
    d.p(
        "ทุกป้ายเป็นทรงแคปซูล (border-radius 9999px) ตัวอักษรหนา 500 มีผลเฉพาะในพื้นที่เนื้อหาและ dialog "
        "ไม่กระทบตัวนับแจ้งเตือนใน systray",
        align="justify",
    )
    d.h2("Typography")
    d.table(
        ["Token", "small", "medium (ค่าเริ่มต้น)", "large"],
        [
            ["--vpk-font-size (base)", "12px", "13px", "14px"],
            ["--vpk-font-size-sm (หัวตาราง)", "11px", "11px", "12px"],
            ["--vpk-font-size-md", "12px", "13px", "14px"],
            ["--vpk-font-size-lg (หัว dialog)", "14px", "15px", "16px"],
            ["--vpk-font-size-xl (ชื่อเรกคอร์ด)", "18px", "20px", "22px"],
            ["--vpk-list-header-height", "2rem", "2.25rem", "2.5rem"],
            ["--vpk-list-thead-padding-y", "0.4rem", "0.5rem", "0.6rem"],
            ["--vpk-field-height", "30px", "34px", "38px"],
        ],
        col_widths=[6.2, 3.2, 4.4, 3.2],
    )
    d.p(
        "--vpk-font-family และ --bs-body-font-family ตั้งตามที่เลือก ค่าเริ่มต้น inter = 'Inter', 'Noto Sans Thai', sans-serif "
        "(Inter ไม่มีอักษรไทย จึงจับคู่กับ Noto Sans Thai ที่ออกแบบให้เข้ากัน) ตัวเลือกอื่นคือ IBM Plex Sans Thai / Anuphan / Kanit / Sarabun / Prompt / Roboto "
        "ถ้าเลือก default จะใช้ฟอนต์ของ Odoo ฟอนต์โหลดจาก Google Fonts เฉพาะเมื่อไม่ใช่ default "
        "ถ้าเครื่องผู้ใช้เข้า Google Fonts ไม่ได้ เบราว์เซอร์จะใช้ฟอนต์ระบบแทน",
        align="justify",
    )
    d.h2("รูปทรงและเงา")
    d.table(
        ["Token", "rounded (ค่าเริ่มต้น)", "standard", "square"],
        [
            ["--vpk-border-radius-lg (การ์ด dialog ตาราง)", "12px", "8px", "0"],
            ["--vpk-border-radius-md (ปุ่ม ช่องกรอก เมนู)", "6px", "4px", "0"],
            ["--vpk-border-radius-sm (facet, kbd)", "4px", "3px", "0"],
        ],
        col_widths=[7.4, 3.8, 2.9, 2.9],
    )
    d.table(
        ["Token", "ค่า", "ใช้กับ"],
        [
            ["--vpk-shadow-sm", "0 1px 2px 0 rgba(15,23,42,.05)", "การ์ดฟอร์ม statusbar chatter ตาราง ปุ่ม (--vpk-box-shadow-common ชี้มาที่ค่านี้)"],
            ["--vpk-shadow-md", "0 4px 6px -1px rgba(15,23,42,.08), 0 2px 4px -2px rgba(15,23,42,.05)", "dropdown เมนูผู้ใช้ sidebar บนมือถือ"],
            ["(dialog)", "0 10px 15px -3px rgba(15,23,42,.1), 0 4px 6px -4px rgba(15,23,42,.1)", ".modal-content"],
        ],
        col_widths=[3.6, 7.4, 6.0],
    )
    d.h2("Layout")
    d.table(
        ["Token", "ความหมาย"],
        [
            ["--vpk-sidebar-width", "ความกว้าง sidebar ตอนกาง (ค่าเริ่มต้น 256px = w-64)"],
            ["--vpk-sidebar-width-collapsed", "ความกว้างตอนพับ (ค่าเริ่มต้น 80px = w-20)"],
            ["--vpk-main-offset", "ระยะ padding-left ของเนื้อหา วัดจากความกว้าง sidebar จริง (0 บนมือถือ/fullscreen)"],
            ["--vpk-main-width", "ความกว้างพื้นที่เนื้อหาที่ใช้ได้"],
            ["--vpk-viewport-width", "ความกว้าง viewport"],
            ["--vpk-notebook-min-height", "ความสูงขั้นต่ำของ notebook = max(400px, 38% ของความสูงจอ) และล็อกไม่ให้หดเมื่อสลับแท็บ"],
        ],
        col_widths=[6.0, 11.0],
    )
    d.h2("Body classes")
    d.p(
        "applyThemeConfig() ใส่คลาสที่ <body> เพื่อให้ SCSS แยกสไตล์ตามค่าได้: o_vpk_sidebar_menu, "
        "o_vpk_sidebar_collapsed, vpk_theme_{rounded|standard|square}, vpk_font_{family}, vpk_font_size_{size}, "
        "vpk_loader_{style}, vpk_chatter_{right|bottom}, vpk_list_compact, vpk_list_sticky_header, "
        "vpk_tree_split_view, vpk_menu_{horizontal|vertical}",
        align="justify",
    )

    # ----- 6 Components -----
    d.page_break()
    d.h1("การออกแบบส่วนประกอบหน้าจอ")

    d.h2("Sidebar (แทน NavBar)")
    d.p("ไฟล์: js/sidebar_menu.js, xml/sidebar_menu.xml, scss/sidebar_menu.scss")
    d.p(
        "Patch web.NavBar แบบ replace ทั้ง <header class=\"o_navbar\"> แล้ววาง sidebar ด้วย position: fixed "
        "ชิดซ้าย สูงเต็มจอ พื้นขาว เส้นขอบขวา slate-200 ไม่มีเงา เมนูเดิมของ Odoo (o_main_navbar) ยังอยู่แต่ถูกซ่อนด้วย d-none",
        align="justify",
    )
    d.table(
        ["ส่วน", "รายละเอียด"],
        [
            ["โลโก้", "แถบสูง 56px มีเส้นใต้ โลโก้บริษัทสูงสุด 40px ตอนพับเหลือไอคอน 32px"],
            ["โปรไฟล์ผู้ใช้", "แถวเดียว: Avatar วงกลม 36px + ชื่อ (13px/600 slate-900) + คำทักทาย (11px slate-500) hover พื้น slate-100 คลิกเปิด User menu (ขอบ slate-200 เงากลาง)"],
            ["ปุ่มค้นหา (⌘K)", "กล่องสูง 34px พื้น slate-50 ขอบ slate-200 มีไอคอนค้นหา ข้อความ Search… และป้าย ⌘K (Mac) / Ctrl K คลิกเปิด Command Palette ของ Odoo ในโหมดค้นหาเมนู ตอนพับเหลือปุ่มไอคอน 40px"],
            ["Systray", "ไอคอน 30×30px grid 7 คอลัมน์ ช่องว่าง 2px สี slate-500 hover พื้น slate-100 มีเส้นใต้แยกจากเมนู"],
            ["รายการแอป", "ไอคอนแอป 20px + ชื่อ padding 7px 10px มุม radius-md ตัวอักษร slate-600; hover พื้น slate-100; แอปที่ active พื้น primary-soft ตัวอักษรสีหลัก หนา 500"],
            ["เมนูย่อย", "ซ้อนได้ไม่จำกัดชั้น (template SubMenuItem เรียกตัวเองซ้ำ) มีเส้นนำสายตาแนวตั้ง slate-200 ด้านซ้าย เมนูที่มีลูกหนา 500"],
            ["ปุ่มพับ", "แถบล่างสุดสูง 40px เส้นบน slate-200 ไอคอน slate-500 hover พื้น slate-100"],
        ],
        col_widths=[3.5, 13.5],
    )
    d.h3("พฤติกรรม")
    d.bullets(
        [
            "คลิกแอปที่มีเมนูย่อย: กาง/หุบ และเปิด action แรกของแอป เมื่อกางแอปใหม่ แอปอื่นจะหุบ (accordion)",
            "แอปปัจจุบันถูกกางอัตโนมัติเมื่อเปลี่ยนหน้า",
            "โหมดพับ: ซ่อนชื่อแอป ข้อมูลผู้ใช้ systray เมนูย่อย และข้อความในปุ่มค้นหา เหลือแต่ไอคอน",
            "จอ ≤ 767.98px: sidebar ซ่อนนอกจอ มีปุ่ม hamburger มุมซ้ายบน เปิดแล้วมี backdrop slate-900 โปร่ง 30% คลิกเพื่อปิด",
            "สถานะพับ/กางไม่ถูกบันทึก รีเฟรชหน้าแล้วจะกลับเป็นกาง",
        ]
    )
    d.figure("03_sidebar_detail.png", "Sidebar: โลโก้ โปรไฟล์ผู้ใช้ ปุ่มค้นหา ⌘K Systray และรายการแอป", width_cm=6.0)
    d.figure("05_sidebar_collapsed.png", "Sidebar ในโหมดพับ เหลือเฉพาะไอคอนแอปและปุ่มค้นหา")
    d.figure("09_command_palette.png", "ปุ่มค้นหาใน Sidebar เปิด Command Palette ค้นหาเมนู")

    d.h2("Systray")
    d.p("ไฟล์: xml/sidebar_menu.xml, xml/systray_inherit.xml, scss/systray_spiffy.scss")
    d.p("ย้าย systray จาก navbar มาไว้ใต้ปุ่มค้นหา แบ่งเป็นสองกลุ่มที่แสดงต่อกันใน grid เดียว", align="justify")
    d.bullets(
        [
            "Primary (ปุ่มที่ธีมสร้างเอง): สลับบริษัท, Debug (เฉพาะโหมด debug), Theme Setting, Sidebar Size, Pin sidebar, Notes (เปิด Discuss), Tips "
            "— ปุ่ม Theme Setting, Sidebar Size และ Tips แสดงเฉพาะ System Administrator",
            "Secondary (ดึงจาก systray registry ตามลำดับคงที่): Debug menu, Messaging, Tier Validation reviewer, My Profile, Activity",
            "ตัวนับแจ้งเตือนเป็นแคปซูลสีหลัก ตัวอักษรขาว มีขอบขาว 2px; dropdown ของ systray ขอบ slate-200 เงากลาง",
            "ซ่อน web.user_menu และ burger_menu เพราะย้ายไปอยู่ที่โปรไฟล์แล้ว",
            "ถ้าไม่อยู่ในโหมด debug จะเว้นช่องว่างแทนปุ่ม Debug เพื่อไม่ให้ grid เลื่อน",
        ]
    )

    d.h2("Theme Settings Panel")
    d.p("ไฟล์: js/theme_config_panel.js, xml/theme_config_panel.xml, scss/theme_config_panel.scss")
    d.p(
        "เปิดได้เฉพาะ System Administrator ค่าที่ Apply มีผลกับผู้ใช้ทุกคน (ใต้หัวข้อ panel มีข้อความ "
        "\"Applies to all users\") ผู้ใช้อื่นจะเห็นค่าใหม่เมื่อโหลดหน้าใหม่ "
        "Drawer เลื่อนเข้าจากขวา กว้าง 95vw สูงสุด 920px มีเส้นขอบซ้าย slate-200 และ overlay slate-900 โปร่ง 30% "
        "แบ่งเป็นแท็บซ้าย 220px และเนื้อหาขวา สีเน้นในแผงใช้สีหลัก",
        align="justify",
    )
    d.table(
        ["แท็บ", "ตัวเลือก"],
        [
            ["General Settings", "Theme Style, Badge Style (Pill / Rounded / Square), Menu Position, Chatter Position, Tree Form Split View, List View Density, Sticky Header"],
            ["Colors", "Primary Color (ปุ่ม ลิงก์ เมนูที่ active), Primary Hover Color, Text on Primary (color picker + ช่องพิมพ์ HEX), Sidebar Background: Light (ขาว) หรือ Gradient ไล่สีบนลงล่าง เลือกสี Top / Bottom ได้ (ค่าเริ่มต้น #15803d → #14532d) โหมด Gradient เปลี่ยนตัวอักษร ไอคอน และเส้นใน sidebar เป็นสีขาว"],
            ["Sidebar Size", "Preset Compact 224 / Default 256 / Wide 300 / Extra Wide 360 + slider 200–420; ตอนพับ Narrow 64 / Default 80 / Wide 96 + slider 56–120"],
            ["Font Family", "Default, Inter, IBM Plex Sans Thai, Anuphan, Kanit, Sarabun, Prompt, Roboto"],
            ["Font Size", "Small, Medium, Large"],
            ["Loaders", "Default, Dots, Bars"],
        ],
        col_widths=[3.8, 13.2],
    )
    d.h3("ลำดับการทำงาน")
    d.bullets(
        [
            "เปิด panel → onWillStart โหลดค่าจาก server เก็บเป็น saved และ draft",
            "ทุกการเปลี่ยนค่า → อัปเดต draft และเรียก applyThemeConfig(draft) ทันที (live preview)",
            "Apply (ปุ่มหลักสีน้ำเงิน) → บันทึกผ่าน /vpk/theme/config/save แล้วใช้ค่าที่ server ตอบกลับ (หลัง clamp)",
            "Discard (ปุ่มรองพื้นขาว) → คืนค่า saved แล้วปิด panel; ปิดด้วยปุ่ม × หรือคลิก overlay จะไม่คืนค่า (ดูหัวข้อ 10)",
            "Defaults → ตั้ง draft เป็นค่าเริ่มต้นทั้งหมด (ยังต้องกด Apply)",
        ],
        numbered=True,
    )
    d.note(
        "ถ้าต้องการกลับไปใช้สีเขียวของโรงพยาบาล ให้ System Administrator ตั้ง Primary Color = #00a884 "
        "และ Primary Hover Color = #047857 ที่แท็บ Colors แล้วกด Apply"
    )
    d.note(
        "ภาพหน้าจอ Theme Settings ต้องจับด้วยบัญชี System Administrator "
        "(ตั้ง ODOO_ADMIN_LOGIN / ODOO_ADMIN_PASSWORD แล้วรัน scripts/playwright/shot_theme_design.py) "
        "ฉบับนี้ยังไม่มีภาพของแผงในสไตล์ใหม่"
    )

    d.h2("ปุ่ม ลิงก์ และ focus")
    d.p("ไฟล์: scss/button_theme.scss")
    d.table(
        ["ประเภท", "สไตล์"],
        [
            ["ปุ่มหลัก (.btn-primary, statusbar, Send ใน chatter, modal footer)", "พื้นสีเรียบ --vpk-primary ตัวอักษร --vpk-on-primary หนา 500 มุม radius-md เงา shadow-sm; hover เป็น --vpk-primary-hover; focus-visible มีวงแหวน 2px; disabled โปร่ง 50%"],
            ["ปุ่มรอง (.btn-secondary, .btn-light, .btn-outline-secondary)", "พื้นขาว ขอบ slate-200 ตัวอักษร slate-600 เงา shadow-sm; hover พื้น slate-50 ขอบ slate-300 ตัวอักษร slate-900"],
            [".btn-outline-primary", "พื้นขาว ขอบและตัวอักษรสีหลัก; hover พื้น primary-soft"],
            ["ลิงก์ / .btn-link / .text-primary", "--vpk-primary hover --vpk-primary-hover"],
            ["focus ช่องกรอก / checkbox / select", "ขอบสีหลัก + วงแหวน 1px"],
            ["Statusbar (Draft / Approved / Done)", "ขั้นปกติ slate-500; ขั้นปัจจุบันพื้น primary-soft ตัวอักษรสีหลัก หนา 600"],
        ],
        col_widths=[6.0, 11.0],
    )

    d.h2("Form view")
    d.p("ไฟล์: scss/form_view_theme.scss, scss/form_fields.scss, scss/text_field_theme.scss, js/form_dropdown_patch.js, js/text_field_patch.js")
    d.table(
        ["องค์ประกอบ", "สไตล์"],
        [
            ["พื้นหลังฟอร์ม", "--vpk-app-bg (slate-50)"],
            ["Sheet", "การ์ดขาว ขอบ slate-200 มุม radius-lg (12px) เงา shadow-sm เต็มความกว้าง; จอ ≥ lg มี margin บนล่าง 12px"],
            ["Statusbar", "การ์ดขาว ขอบ slate-200 มุม radius-lg padding ซ้ายขวา 10px"],
            ["ชื่อเรกคอร์ด", "--vpk-font-size-xl หนา 600 slate-900"],
            ["Label ฟิลด์", "slate-600 หนา 500; ฟิลด์บังคับ slate-900 หนา 600 (ไม่ใช้สีหลักกับ label)"],
            ["ฟิลด์ input/select", "กรอบ 4 ด้าน slate-200 สูง --vpk-field-height มุม radius-md พื้นขาว; hover ขอบ slate-300; focus ขอบสีหลัก + วงแหวน 1px (เฉพาะฟอร์มโหมดแก้ไข ไม่ใช้กับ boolean, radio, image, tags, statusbar, text)"],
            ["Textarea", "สูงขั้นต่ำ 80px (ใน list 36px) ยืดแนวตั้งได้"],
            ["Separator", "หัวข้อส่วน ตัวเล็ก หนา 600 พิมพ์ใหญ่ เว้นระยะ 0.05em สี slate-500 เส้นใต้ slate-200 เต็มความกว้าง"],
            ["Stat buttons", "คั่นด้วยเส้นตั้ง slate-200 ไอคอน slate-400 ตัวเลข slate-900 หนา 600 tabular-nums; hover พื้น slate-50"],
            ["Dropdown Many2one", "ความกว้างเท่ากรอบฟิลด์ (form_dropdown_patch.js); รายการที่เลือกพื้น primary-soft"],
            ["ฟอร์มเต็มความกว้าง", "ฟอร์มการชำระเงิน หรือฟอร์มที่มี class o_vpk_fullwidth_form"],
        ],
        col_widths=[4.0, 13.0],
    )
    d.figure("04_form_view.png", "Form view ใบขอซื้อ: การ์ดขอบบาง หัวข้อส่วนตัวพิมพ์เล็ก ปุ่มหลักสีน้ำเงินและปุ่มรองพื้นขาว")

    d.h2("Notebook (แท็บในฟอร์ม)")
    d.p("ไฟล์: scss/form_notebook_theme.scss, scss/button_theme.scss, js/form_layout_patch.js, js/theme_utils.js")
    d.p("เป้าหมาย: ทุกแท็บมีกล่องขนาดเดียวกัน หน้าจอไม่กระตุกเมื่อสลับแท็บ", align="justify")
    d.bullets(
        [
            "Notebook เต็มความกว้าง sheet หัวแท็บ padding เท่ากับ sheet",
            "เนื้อหาแท็บสูงขั้นต่ำ --vpk-notebook-min-height และล็อกที่ความสูงมากสุดที่เคยแสดง",
            "กลุ่มที่มีคอลัมน์เดียว (Odoo ปกติให้ 50%) ขยายเป็น 100%",
            "x2many list ภายในแท็บไม่มี margin ติดลบ",
            "แท็บแบบเส้นใต้: แถบหัวมีเส้นล่าง slate-200; แท็บปกติ slate-500 หนา 500 ไม่มีกรอบ; active ตัวอักษรสีหลัก หนา 600 เส้นใต้ 2px",
            "จอ ≤ md แท็บเลื่อนแนวนอนได้ ไม่ตัดบรรทัด; แท็บนอกฟอร์ม (หน้า Settings ฯลฯ) ใช้แบบเส้นใต้เหมือนกัน",
        ]
    )

    d.h2("Chatter")
    d.p("ไฟล์: scss/form_chatter.scss, js/form_layout_patch.js (patch FormRenderer.mailLayout)")
    d.table(
        ["chatter_position", "ผลลัพธ์"],
        [
            ["bottom (ค่าเริ่มต้น)", "บังคับ chatter อยู่ใต้ฟอร์มทุกขนาดจอ"],
            ["right", "chatter อยู่ขวา กว้าง 34% เมื่อพื้นที่เนื้อหา ≥ 900px; ถ้าแคบกว่าจะย้ายลงล่างอัตโนมัติ"],
        ],
        col_widths=[4.5, 12.5],
    )
    d.p(
        "Chatter แสดงเป็นการ์ดขาว ขอบ slate-200 มุม radius-lg เงา shadow-sm บนพื้น slate-50 "
        "และใช้ฟอนต์ธีม (รองรับ emoji ด้วย text-emoji นำหน้า)",
        align="justify",
    )

    d.h2("Control panel")
    d.p("ไฟล์: scss/modern_ui.scss")
    d.table(
        ["องค์ประกอบ", "สไตล์"],
        [
            ["แถบ control panel", "พื้นขาว เส้นล่าง slate-200 ไม่มีเงา"],
            ["Breadcrumb", "ระดับก่อนหน้า slate-500 (hover slate-900) ระดับปัจจุบัน slate-900 หนา 600"],
            ["ช่องค้นหา", "พื้น slate-50 ขอบ slate-200 มุม radius-md; hover ขอบ slate-300; focus พื้นขาว ขอบสีหลัก + วงแหวน 1px; หัว facet พื้น primary-soft"],
            ["ปุ่มสลับมุมมอง", "ปกติ slate-500; มุมมองปัจจุบันพื้น primary-soft ตัวอักษรสีหลัก"],
            ["Pager", "slate-500 ตัวเลข tabular-nums"],
        ],
        col_widths=[4.0, 13.0],
    )

    d.h2("List view (ตารางข้อมูล)")
    d.p("ไฟล์: scss/list_view_theme.scss, scss/modern_ui.scss, scss/theme_config_panel.scss")
    d.table(
        ["องค์ประกอบ", "สไตล์"],
        [
            ["กรอบตาราง", "หน้า list หลัก: วางบนพื้น slate-50 ห่างขอบ 16px ตัวตารางเป็นการ์ดขาว ขอบ slate-200 มุม radius-lg เงา shadow-sm (one2many ในฟอร์มไม่มีกรอบการ์ด)"],
            ["หัวตาราง", "สูงคงที่ --vpk-list-header-height ตัวเล็ก หนา 500 slate-500 พิมพ์ใหญ่ เว้นระยะ 0.05em พื้น slate-50 เส้นล่าง slate-200"],
            ["แถว", "ไม่มีสีสลับแถว เส้นแบ่งแถว slate-100; hover พื้น slate-50; แถวที่เลือกพื้น primary-soft"],
            ["ตัวเลข", "ชิดขวา และทั้งตารางใช้ tabular-nums ตัวเลขจึงตรงหลักกัน"],
            ["แถวกลุ่ม / แถวรวม", "พื้น slate-50 หนา 600 เส้นบน slate-200"],
            ["ปุ่มรองในแถว", "ปุ่มลบแถว (ไอคอนถังขยะสี slate-400 hover rose-700) และปุ่มเปิดฟอร์ม แสดงเฉพาะเมื่อชี้แถวหรือแถวมี focus (เฉพาะอุปกรณ์ที่มีเมาส์; จอสัมผัสแสดงตลอด)"],
            ["vpk_list_compact", "padding แถวบนล่าง 2px"],
            ["vpk_list_sticky_header", "หัวตารางติดด้านบนเมื่อเลื่อน"],
        ],
        col_widths=[4.0, 13.0],
    )

    d.h2("Kanban")
    d.p(
        "ไฟล์: scss/modern_ui.scss — พื้นหลัง slate-50; การ์ดพื้นขาว ขอบ slate-200 มุม radius-lg ไม่มีเงา "
        "hover ขอบ slate-300 + shadow-sm; หัวคอลัมน์ slate-900 หนา 600",
        align="justify",
    )

    d.h2("Dialog / Wizard / Dropdown / Command Palette")
    d.p("ไฟล์: scss/dialog_theme.scss, scss/modern_ui.scss, xml/dialog_inherit.xml, js/layout_utils.js (bindVpkWizardResize)")
    d.bullets(
        [
            "Dialog: กรอบ slate-200 มุม radius-lg เงาใหญ่; หัวพื้นขาว เส้นล่าง slate-200 ตัวอักษร --vpk-font-size-lg หนา 600; "
            "footer พื้น slate-50 เส้นบน slate-200; backdrop slate-900 โปร่ง 30%",
            "ความสูงสูงสุด 90vh เนื้อหาเลื่อนในตัว ขนาดขั้นต่ำ 360×200px",
            "ลากมุมขวาล่างเพื่อปรับขนาดได้ (สัญลักษณ์มุมสี slate-400) ขยายได้ถึง 95vw",
            "Dialog \"Search More…\" (SelectCreateDialog) เปิดขนาด xl เสมอ",
            "Dropdown: ขอบ slate-200 มุม radius-md เงากลาง; item hover พื้น slate-100; item ที่เลือกพื้น primary-soft; หัวกลุ่มตัวเล็กพิมพ์ใหญ่",
            "Command Palette (⌘K): รายการปกติ slate-600 ส่วนที่ตรงคำค้นเป็นสีหลักตัวหนา รายการที่เลือกพื้น primary-soft",
        ]
    )

    d.h2("Layout และ Responsive")
    d.p("ไฟล์: scss/layout_responsive.scss, js/layout_utils.js")
    d.bullets(
        [
            "เนื้อหาหลักเว้นซ้ายเท่ากับ --vpk-main-offset ซึ่ง JS วัดจากความกว้าง sidebar จริงทุกครั้งที่ resize / พับ / เปลี่ยนขนาด",
            "ห้ามหน้าเลื่อนแนวนอนทั้งหน้า ตารางกว้างเลื่อนแนวนอนภายในตัวเอง",
            "ลด min-width ของฟอร์ม XXL (Odoo ตั้งไว้ 990px + chatter 530px) ให้หดได้",
            "Breakpoint: 767.98px (มือถือ), 992px (side chatter) และ mixin media-breakpoint-* ของ Bootstrap",
        ]
    )

    d.h2("ไอคอน")
    d.p("ไฟล์: scss/line_icons.scss, js/line_icons.js, scss/remixicon.scss, scss/font_icons.scss, static/lib/RemixIcon/remixicon.woff2")
    d.bullets(
        [
            "ไอคอนลายเส้น Lucide (ตามแนวทาง modern_erp_ai_guidelines.md) ใช้กับ sidebar ทั้งหมด: ไอคอนแอป ปุ่มค้นหา "
            "ลูกศรเมนู ปุ่มพับ และแถว systray เส้นหนา 1.75 สีตาม currentColor (เทา slate เมื่อปกติ สี primary เมื่อ active)",
            "scss/line_icons.scss สร้างจาก scripts/build_vpk_line_icons.py ฝัง SVG เป็น data URI (ไม่โหลดจากอินเทอร์เน็ต) "
            "ใช้ <span class=\"vpk-li vpk-li-NAME\"/> หรือ mask-image: var(--vpk-li-NAME) เพิ่มไอคอนใหม่ให้ใส่ชื่อในสคริปต์แล้วรันใหม่",
            "ไอคอนแอปกำหนดตาม xmlid ของเมนูหลักใน APP_LINE_ICONS (js/line_icons.js) แอปที่ไม่มีในรายการใช้ app-window แทนรูปไอคอนสีของ Odoo",
            "ไอคอน FontAwesome ใน systray ที่ Odoo วาดเอง (แชท, กิจกรรม, อนุมัติ, debug) ถูกแทนด้วย mask ของ Lucide ใน systray_spiffy.scss",
            "RemixIcon ยังโหลดจากไฟล์ในโมดูลสำหรับไอคอนส่วนอื่น (ประกาศเฉพาะคลาสที่ใช้จริง)",
            "Mixin vpk-fa-remix($name, $content) แทนไอคอน FontAwesome ที่ใช้บ่อย (bars, search, filter, plus, pencil, times, check, cog, print, paperclip ฯลฯ) ด้วยไอคอน Remix แบบเส้นบาง",
            "มี guard ป้องกันไม่ให้ฟอนต์ธีมไปทับฟอนต์ไอคอน .fa, .ri, .oi",
        ]
    )

    d.h2("Typography ข้ามส่วน")
    d.p("ไฟล์: scss/theme_fonts.scss, scss/portal_theme_font.scss, views/portal_theme_font_templates.xml")
    d.p(
        "บังคับฟอนต์ธีมกับส่วนที่ Odoo หรือโมดูลอื่นตั้งฟอนต์ไว้เอง ได้แก่ label ฟอร์ม แท็บ separator chatter "
        "date picker kanban card dashboard งบประมาณ (o_vpk_budget_*) และ dashboard รออนุมัติ (o_vpk_pending_review_*) "
        "ฝั่ง Portal ใช้ template ที่ inherit web.frontend_layout ฉีด <style> และ Google Fonts ตามค่าใน record กลาง "
        "และใส่คลาส vpk_font_* ที่ #wrapwrap (รองรับ vpk_font_inter)",
        align="justify",
    )

    d.h2("TinyMCE HTML Field")
    d.p("ไฟล์: js/tinymce_html_field.js, xml/tinymce_html_field.xml, static/lib/tinymce/")
    d.p(
        "ลงทะเบียน field widget ชื่อ tinymce_html โหลด TinyMCE แบบ lazy จากไฟล์ในโมดูล มี template เอกสารราชการเริ่มต้น "
        "ปัจจุบันยังไม่มี view ในโมดูลอื่นเรียกใช้ widget นี้",
        align="justify",
    )

    # ----- 7 Login -----
    d.page_break()
    d.h1("หน้าเข้าสู่ระบบ (vpk_login_page)")
    d.note("หน้า Login ยังไม่ได้ปรับเป็นสไตล์ Modern SaaS และใช้ชุดสี teal/green ของตัวเอง")
    d.figure("01_login.png", "หน้า Login แบบเต็มจอสองคอลัมน์")
    d.table(
        ["ส่วน", "รายละเอียด"],
        [
            ["Layout", "Grid 2 คอลัมน์ 1.1fr / 0.9fr เต็มจอ; จอ ≤ 991.98px เป็นคอลัมน์เดียว (ภาพสูง 42vh; ≤ 575.98px สูง 32vh)"],
            ["ซ้าย (Hero)", "ภาพ login_hero.jpg เต็มกรอบ ทับด้วย gradient เขียวเข้ม (โปร่ง 92% → 28% จากบนลงล่าง) หัวข้อ ชื่อหน่วยงาน คำโปรย และเส้นคั่นขาว 3px"],
            ["ขวา (ฟอร์ม)", "โลโก้บริษัท คำอธิบาย ช่อง Username / Password สูง 3rem มุมเหลี่ยม ปุ่มแสดง/ซ่อนรหัสผ่าน ลิงก์ลืมรหัสผ่าน ปุ่มเข้าสู่ระบบสีเขียว"],
            ["ฟอนต์", "Prompt (fallback Sarabun) โหลดเฉพาะหน้า login"],
            ["ข้อความ", "แก้ผ่าน System Parameter vpk_login_page.headline, .organisation, .tagline, .welcome_subtitle, .footnote"],
            ["ผู้ใช้ทดสอบ UAT", "ถ้า vpk_login_page.test_users_enabled = True จะมี dropdown เลือก 21 บทบาท เติม login/password ให้อัตโนมัติ"],
            ["Routing", "เข้า / แล้ว redirect ไป /web/login (ถ้า login แล้วไป /odoo)"],
            ["ใช้ร่วมกับ", "หน้า Signup และ Reset password ใช้ shell เดียวกัน เปลี่ยนเฉพาะคำอธิบาย"],
        ],
        col_widths=[3.5, 13.5],
    )
    d.h2("ชุดสีของหน้า Login")
    d.p("SCSS variables ใน login_page.scss แยกจากธีมหลังบ้าน", align="justify")
    d.table(
        ["ตัวแปร", "ค่า", "ใช้กับ"],
        [
            ["$vpk-teal-500/600/700", "#14696e / #115f60 / #0e5250", "พื้น hero, gradient ทับภาพ"],
            ["$vpk-green-500/600", "#2f8168 / #276b57", "ปุ่มเข้าสู่ระบบ / hover"],
            ["$vpk-ink", "#16232b", "ตัวอักษรหลัก"],
            ["$vpk-muted", "#5f7280", "ตัวอักษรรอง"],
            ["$vpk-border", "#cdd8dd", "ขอบช่องกรอก"],
        ],
        col_widths=[5.0, 6.0, 6.0],
    )

    # ----- 8 Assets -----
    d.page_break()
    d.h1("การโหลด Asset")
    d.h2("ผ่าน __manifest__.py (web.assets_backend)")
    d.p(
        "ลำดับ: remixicon.scss → font_icons.scss → sidebar_menu.scss → form_chatter.scss → theme_config_panel.scss "
        "→ list_view_theme.scss → dialog_theme.scss → JS ทั้งหมด → XML templates; "
        "web.assets_frontend: portal_theme_font.scss",
        align="justify",
    )
    d.h2("ผ่าน ir.asset แบบ append (โหลดท้าย bundle)")
    d.table(
        ["Sequence", "ไฟล์"],
        [
            ["100", "button_theme.scss"],
            ["101", "layout_responsive.scss"],
            ["102", "list_view_theme.scss (โหลดซ้ำจาก manifest)"],
            ["103", "form_view_theme.scss"],
            ["104", "form_fields.scss"],
            ["105", "theme_fonts.scss"],
            ["110", "form_notebook_theme.scss"],
            ["111", "text_field_theme.scss"],
            ["112", "dialog_theme.scss (โหลดซ้ำจาก manifest)"],
            ["113", "systray_spiffy.scss"],
            ["120", "modern_ui.scss (control panel ตาราง ป้ายสถานะ kanban dialog dropdown command palette)"],
        ],
        col_widths=[3.0, 14.0],
    )
    d.h2("<style> ที่ JS สร้างตอนรันไทม์")
    d.p(
        "theme_utils.js สร้าง <style> 2 ชุด: vpk-systray-theme-styles (grid ของ systray) และ vpk-notebook-theme-styles "
        "(ความสูง notebook ตามขนาดจอ) ชุด vpk-button-theme-styles (ปุ่ม gradient) ถูกลบออกตั้งแต่ v18.0.1.9.0 "
        "และ applyThemeConfig() จะลบ <style> เก่านั้นทิ้งถ้ายังค้างอยู่",
        align="justify",
    )
    d.h2("โมดูลอื่นที่ใช้ token ของธีม")
    d.p(
        "vpk_budget (dashboard, ฟอร์มคำของบ), vpk_tier_validation (dashboard/kanban รออนุมัติ) และ vpk_stock_warehouse "
        "(warehouse overview) อ้างอิง var(--vpk-sidebar-*) โดยตรง ตอนนี้ token เหล่านั้นชี้ไปที่สีหลักน้ำเงินแบบสีเรียบ "
        "ส่วนที่เคยเป็น gradient จึงเป็นสีเรียบ ถ้าไม่ได้ติดตั้ง vpk_sidebar_menu จะใช้ค่า fallback ที่ระบุใน var()",
        align="justify",
    )

    # ----- 9 Guidelines -----
    d.h1("แนวทางสำหรับนักพัฒนา")
    d.bullets(
        [
            "ใช้ token แทนการฮาร์ดโค้ดสี: สีหลัก var(--vpk-primary), hover var(--vpk-primary-hover), ตัวอักษรบนสีหลัก "
            "var(--vpk-on-primary), พื้นเน้นอ่อน var(--vpk-primary-soft); พื้น/ขอบ/ตัวอักษรใช้ --vpk-surface, --vpk-app-bg, "
            "--vpk-border, --vpk-text* และใส่ fallback เสมอ เช่น var(--vpk-primary, #2563eb) โค้ดใหม่ไม่ควรใช้ --vpk-sidebar-* อีก",
            "สีสถานะใช้ badge ของ Bootstrap (text-bg-success/warning/danger/info) แล้วธีมจะแปลงเป็นป้ายอ่อนให้เอง",
            "คอลัมน์ตัวเลขให้ชิดขวา ถ้าแสดงตัวเลขนอกตาราง ใส่คลาส o_vpk_tabular เพื่อให้ได้ tabular-nums",
            "เงาใช้ var(--vpk-shadow-sm) กับการ์ด var(--vpk-shadow-md) กับ popover/dropdown; มุมใช้ var(--vpk-border-radius-{lg|md|sm}) "
            "ห้ามใช้เงาหนาหรือ gradient",
            "ฟอนต์และขนาดใช้ var(--vpk-font-family, inherit) และ var(--vpk-font-size-md, inherit) "
            "ถ้าคอมโพเนนต์ตั้ง font-family เอง ต้องกันไม่ให้ไปทับ .fa, .ri, .oi",
            "ครอบ rule ด้วย body.o_web_client.o_vpk_sidebar_menu เพื่อไม่กระทบหน้า Portal และรายงาน",
            "ไฟล์ที่ต้อง override CSS ของโมดูลอื่น ให้เพิ่มเป็น ir.asset append ใน data/ir_asset_layout.xml ด้วย sequence ≥ 121",
            "เพิ่มตัวเลือกธีมใหม่ต้องแก้ 5 จุดให้ตรงกัน: ฟิลด์และ _to_dict() ในโมเดล, CONFIG_FIELDS ใน controller, "
            "DEFAULT_THEME_CONFIG และ applyThemeConfig() ใน theme_utils.js, UI ใน theme_config_panel.xml และ SCSS ที่อ่านค่า",
            "ฟอร์มที่ต้องการเต็มความกว้างให้ใส่ class o_vpk_fullwidth_form ที่ <form>",
            "ไอคอน Remix ใหม่ต้องประกาศคลาสและ codepoint ใน remixicon.scss ก่อนใช้",
        ],
        numbered=True,
    )

    # ----- 10 Known issues -----
    d.page_break()
    d.h1("ข้อจำกัดและประเด็นที่พบจากโค้ดปัจจุบัน")
    d.table(
        ["#", "ประเด็น", "รายละเอียด"],
        [
            ["1", "ตัวเลือกที่ยังไม่มีผล", "Loader style, Menu Position = Horizontal และ Tree Form Split View บันทึกค่าและใส่ body class ได้ แต่ไม่มี SCSS/JS อ่านคลาสเหล่านี้ ผู้ใช้เลือกแล้วหน้าจอไม่เปลี่ยน"],
            ["2", "สีหน้า Login ไม่ผูกกับธีม", "หน้า Login ใช้ชุดสี teal/green ของตัวเอง (อ่านแค่ฟอนต์จากธีม) จึงยังเป็นสีเขียวขณะที่หลังบ้านเป็นน้ำเงิน"],
            ["3", "ฟอนต์ขึ้นกับ Google Fonts", "Inter / Noto Sans Thai และฟอนต์อื่นโหลดจาก fonts.googleapis.com ถ้าเครือข่ายบล็อก จะใช้ฟอนต์ระบบแทน"],
            ["4", "ผู้ใช้ปรับธีมเองไม่ได้", "ตั้งแต่ v18.0.1.8.0 ธีมเป็นค่ากลาง ผู้ใช้ที่ต้องการตัวอักษรใหญ่ขึ้นต้องใช้การซูมของเบราว์เซอร์แทน"],
            ["5", "Preview ค้างเมื่อปิด panel", "ปิดด้วยปุ่ม × หรือคลิก overlay ไม่คืนค่าที่บันทึกไว้ จนกว่าจะรีเฟรช มีเฉพาะปุ่ม Discard ที่คืนค่า"],
            ["6", "CSS ซ้ำซ้อน", "grid ของ systray และ layout ของ notebook มีทั้งใน SCSS และ <style> ที่ JS สร้าง; list_view_theme.scss และ dialog_theme.scss โหลดสองครั้ง"],
            ["7", "ใช้ !important จำนวนมาก", "เพื่อชนะ CSS ของ Odoo และโมดูลอื่น ทำให้ override ต่อยาก ต้องใช้ selector ที่เฉพาะเจาะจงกว่า"],
            ["8", "สถานะพับ sidebar ไม่ถูกจำ", "รีเฟรชแล้ว sidebar กลับมากางเสมอ"],
            ["9", "ไม่ตรวจสอบค่าสี", "ช่องพิมพ์ HEX รับข้อความอะไรก็ได้ และบันทึกลงฐานข้อมูลโดยไม่ validate"],
            ["10", "ข้อความ UI ภาษาอังกฤษ", "Search…, Good Morning/Evening และป้ายในแผง Theme Settings ยังเป็นภาษาอังกฤษ ไม่มีไฟล์แปล"],
        ],
        col_widths=[1.0, 4.5, 11.5],
    )
    d.p(
        "ประเด็นที่แก้แล้วใน v18.0.1.9.0: สีเขียว rgba(0,168,132,…) ที่ฮาร์ดโค้ดใน focus ring/statusbar (เปลี่ยนเป็น token), "
        "resize listener ที่สะสมทุกครั้งที่เรียก applyThemeConfig() (ผูกครั้งเดียว), <style> ปุ่ม gradient ที่ซ้ำกับ SCSS (ลบแล้ว) "
        "และ systray ยังแสดงตอนพับ sidebar (แก้ specificity)",
        align="justify",
    )

    # ----- 11 Files -----
    d.h1("การอ้างอิงทางเทคนิค")
    d.h2("vpk_sidebar_menu")
    d.table(
        ["ไฟล์", "หน้าที่"],
        [
            ["controllers/main.py", "/vpk/theme/config, /vpk/theme/config/save"],
            ["models/vpk_theme_config.py", "โมเดลธีม, _get_global_config, ค่าฟอนต์ Portal"],
            ["security/ir.model.access.csv", "user อ่านอย่างเดียว, group_system แก้ไขได้"],
            ["data/vpk_theme_config_data.xml", "record ธีมกลาง vpk_theme_config_global"],
            ["data/ir_asset.xml, data/ir_asset_layout.xml", "SCSS ที่โหลดท้าย bundle (seq 100–120)"],
            ["views/portal_theme_font_templates.xml", "ฟอนต์ธีมบนหน้า Portal"],
            ["js/sidebar_menu.js", "patch NavBar + WebClient, ปุ่มค้นหา ⌘K"],
            ["js/theme_config_panel.js", "Theme Settings drawer"],
            ["js/theme_utils.js", "applyThemeConfig, tokens, notebook layout"],
            ["js/layout_utils.js", "วัด sidebar, main offset, ลากขยาย wizard"],
            ["js/form_layout_patch.js", "mailLayout (chatter), ความสูง notebook"],
            ["js/form_dropdown_patch.js", "ความกว้าง autocomplete dropdown"],
            ["js/text_field_patch.js", "textarea ยืดได้"],
            ["js/tinymce_html_field.js", "widget tinymce_html"],
            ["scss/sidebar_menu.scss", "design tokens (:root) + sidebar"],
            ["scss/button_theme.scss", "ปุ่ม ลิงก์ แท็บ focus"],
            ["scss/form_view_theme.scss, form_fields.scss", "การ์ดฟอร์ม label separator stat button กรอบช่องกรอก"],
            ["scss/systray_spiffy.scss", "systray grid ตัวนับแจ้งเตือน"],
            ["scss/modern_ui.scss", "control panel ตาราง ป้ายสถานะ kanban dialog dropdown command palette"],
            ["migrations/18.0.1.7.{54,69,70}", "ปรับค่า sidebar_width"],
            ["migrations/18.0.1.8.0", "รวมธีมรายผู้ใช้เป็นธีมกลาง"],
            ["migrations/18.0.1.9.0", "ตั้งค่าธีมกลางเป็นสไตล์ Modern SaaS"],
        ],
        col_widths=[7.0, 10.0],
    )
    d.h2("vpk_login_page")
    d.table(
        ["ไฟล์", "หน้าที่"],
        [
            ["controllers/main.py", "/ → /web/login"],
            ["models/res_users.py", "รายชื่อผู้ใช้ทดสอบ UAT"],
            ["views/login_templates.xml", "layout 2 คอลัมน์ ฟอร์ม และฟอนต์ Prompt"],
            ["static/src/js/login_page.js", "แสดง/ซ่อนรหัสผ่าน ย้ายลิงก์ลืมรหัส ตัวเลือกผู้ใช้ UAT"],
            ["static/src/scss/login_page.scss", "สไตล์หน้า Login"],
        ],
        col_widths=[7.0, 10.0],
    )
    d.h2("เอกสารที่เกี่ยวข้อง")
    d.bullets(
        [
            "ฉบับ Markdown: docs/Theme-Design-VPK.md",
            "แนวทางออกแบบ: modern_erp_ai_guidelines.md",
            "สคริปต์ภาพประกอบ: scripts/playwright/shot_theme_design.py",
            "เอกสารออกแบบระบบรวม: docs/เอกสารออกแบบระบบ-VPK-ERP-Odoo18.docx",
        ]
    )
    d.h2("ประวัติเอกสาร")
    d.table(
        ["เวอร์ชัน", "วันที่", "รายละเอียด"],
        [
            ["1.0", "17 พ.ย. 2569", "ร่างแรก — อ้างอิงจากซอร์สโค้ด vpk_sidebar_menu 18.0.1.7.70 และ vpk_login_page 18.0.1.3.4"],
            ["1.1", "17 พ.ย. 2569", "ธีมเป็นค่ากลางทั้งระบบ แก้ไขได้เฉพาะ System Administrator (vpk_sidebar_menu 18.0.1.8.0)"],
            ["1.2", "17 พ.ย. 2569", "ปรับสไตล์เป็น Modern SaaS ตาม modern_erp_ai_guidelines.md: โทน slate สีหลักน้ำเงิน ฟอนต์ Inter ตารางแบบใหม่ ป้ายสถานะอ่อน ปุ่มค้นหา ⌘K (vpk_sidebar_menu 18.0.1.9.0)"],
        ],
        col_widths=[3.0, 4.0, 10.0],
    )

    d.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
