#!/usr/bin/env python3
"""สร้างตาราง Excel สรุป Function ของ 6 module หลัก (VPK Odoo 18)

ที่มาข้อมูล: __manifest__.py / เมนู (menuitem) ของ vpk_* และคู่มือการใช้งานใน docs/คู่มือการใช้งาน
รัน: python3 docs/build_module_function_summary_xlsx.py
"""
from pathlib import Path

import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).parent))
from budget_dataflow_data import FUNCTIONS as BUDGET_IO, PHASES as BUDGET_PHASES  # noqa: E402
from procurement_dataflow_data import (  # noqa: E402
    CONTRACT_COMPARE, CONTRACT_TYPES, FUNCTIONS as PROC_IO, INTEGRATION as PROC_INT, PHASES as PROC_PHASES,
    METHOD_LABEL,
)

OUT = Path(__file__).parent / "สรุป-Function-ตาม-Module.xlsx"
M_FILL = {"both": "EEF1F4", "specific": "E5F5EA", "ebidding": "FDF3E0"}

C = "Custom (VPK)"
S = "Odoo Standard"
O = "OCA / Community"

# (กลุ่มฟังก์ชัน, ฟังก์ชัน/เมนู, รายละเอียดการทำงาน, ผู้ใช้งานหลัก, Odoo module, ประเภท)
MODULES = {}

MODULES["1.งบประมาณ"] = {
    "title": "1. งบประมาณ",
    "desc": "บริหารงบประมาณประจำปี รับคำของบจากหน่วยงาน จัดสรร/อนุมัติ และตรวจสอบ-จองงบเมื่อมีการขอซื้อ/จ้าง",
    "rows": [
        ("ข้อมูลหลัก", "แหล่งเงิน", "กำหนดแหล่งเงิน เช่น งบประมาณ เงินบำรุง เงินบริจาค ใช้ผูกกับคำของบและงบประมาณประจำปี", "งานงบประมาณ", "vpk_budget", C),
        ("ข้อมูลหลัก", "ประเภทงบประมาณ", "กำหนดประเภทงบ (งบดำเนินงาน งบลงทุน ฯลฯ)", "งานงบประมาณ", "vpk_budget", C),
        ("ข้อมูลหลัก", "แบบฟอร์มคำของบ (4 ประเภท)", "กำหนดแบบฟอร์ม/บรรทัดของใบคำของบ: วัสดุ, ครุภัณฑ์, ก่อสร้าง, โครงการ", "งานงบประมาณ", "vpk_budget", C),
        ("ข้อมูลหลัก", "กลุ่มครุภัณฑ์ / ประเภทครุภัณฑ์", "จัดหมวดครุภัณฑ์สำหรับคำของบครุภัณฑ์", "งานงบประมาณ", "vpk_budget", C),
        ("ข้อมูลหลัก", "กลุ่มงบประมาณ-วัสดุ / ประเภทวัสดุย่อย", "จัดกลุ่มวัสดุเพื่อกำหนดวงเงินและรวมยอดตามกลุ่ม", "งานงบประมาณ", "vpk_budget", C),
        ("ข้อมูลหลัก", "หมวดงบประมาณ (Budgetary Position)", "ผูกบัญชีกับหมวดงบประมาณเพื่อเช็คยอดใช้จริงกับงบ", "งานงบประมาณ / บัญชี", "base_account_budget", O),
        ("ข้อมูลหลัก", "บัญชีวิเคราะห์ (หน่วยงาน/ศูนย์ต้นทุน)", "กำหนดหน่วยงานเป็น Analytic Account เพื่อแยกงบตามหน่วยงาน", "งานงบประมาณ", "analytic / vpk_budget", S),
        ("ข้อมูลหลัก", "งบประมาณประจำปี", "สร้างแผนงบประมาณรายปีงบประมาณ พร้อมรายการงบตามหมวด/หน่วยงาน", "งานงบประมาณ", "base_account_budget / vpk_budget", O),
        ("ข้อมูลหลัก", "Import Budget Master", "นำเข้าข้อมูลหลักงบประมาณ (แหล่งเงิน หมวด กลุ่ม แผน) จาก Excel เพื่อ data migration", "งานงบประมาณ / IT", "vpk_budget", C),
        ("คำของบประมาณ", "บันทึกคำของบ (ใบคำของบ)", "หน่วยงานสร้างใบคำของบ วัสดุ/ครุภัณฑ์/ก่อสร้าง/โครงการ กรอกรายการ จำนวน ราคา เหตุผล", "หน่วยงาน", "vpk_budget", C),
        ("คำของบประมาณ", "เลือกรายการจากแผนงบประมาณ / โหลดรายการตามหมวด", "ดึงรายการสินค้าจากแผนงบประมาณมาใส่ในใบคำของบอัตโนมัติ (Wizard)", "หน่วยงาน", "vpk_budget", C),
        ("คำของบประมาณ", "นำเข้ารายการวัสดุจาก Excel", "Import รายการวัสดุเข้าใบคำของบเป็นชุด", "หน่วยงาน", "vpk_budget", C),
        ("คำของบประมาณ", "ส่งคำขอ / ล็อกการแก้ไขหลังส่ง", "ส่งใบคำของบให้งานงบประมาณ หลังส่งหน่วยงานแก้ไขไม่ได้", "หน่วยงาน", "vpk_budget", C),
        ("คำของบประมาณ", "รวบรวมคำของบ (หน่วยงบประมาณ)", "งานงบประมาณรับเรื่อง ตรวจ รวมยอดคำของบจากทุกหน่วยงาน", "งานงบประมาณ", "vpk_budget", C),
        ("คำของบประมาณ", "จัดสรรงบ (Allocate Material Budget)", "ใส่ยอดจัดสรรรายรายการ/กลุ่มวัสดุ ก่อนอนุมัติ", "งานงบประมาณ", "vpk_budget", C),
        ("คำของบประมาณ", "ลำดับสถานะใบคำของบ", "Draft → ส่งใบคำขอ → รับเรื่อง → เริ่มพิจารณา → อนุมัติ (หรือตีกลับ / ตั้งเป็นร่าง) โดยงานงบประมาณ", "งานงบประมาณ", "vpk_budget", C),
        ("คำของบประมาณ", "ใบปะหน้าคำของบประมาณ", "พิมพ์ใบปะหน้าสรุปคำของบของหน่วยงาน", "งานงบประมาณ", "vpk_budget", C),
        ("คำของบประมาณ", "สรุปแผนการใช้เงินบำรุง", "รายงานสรุปแผนการใช้เงินบำรุงรายหน่วยงาน", "งานงบประมาณ / ผู้บริหาร", "vpk_budget", C),
        ("คำของบประมาณ", "สร้างคำของบตัวอย่าง (ครบทุกกลุ่ม)", "สร้างข้อมูลตัวอย่างสำหรับทดสอบ/ฝึกอบรม", "ผู้ดูแลระบบ", "vpk_budget", C),
        ("ควบคุมงบกับการจัดซื้อ", "รายการงบประมาณ (Budget Lines)", "ดูยอดงบ ยอดจอง ยอดใช้จริง ยอดคงเหลือ แยกตามหมวด/หน่วยงาน", "งานงบประมาณ / การเงิน", "base_account_budget / vpk_budget", O),
        ("ควบคุมงบกับการจัดซื้อ", "ตรวจสอบงบประมาณบนใบขอซื้อ (PR)", "เช็คงบคงเหลือก่อนส่ง/อนุมัติ PR พร้อมแท็บผลการเช็คงบ ถ้าไม่ผ่านจะบล็อก", "หน่วยงาน / พัสดุ", "vpk_budget", C),
        ("ควบคุมงบกับการจัดซื้อ", "จองงบ / ตัดงบเรียลไทม์", "จองงบเมื่อ PR/PO และตัดเมื่อเกิดรายการจริง ตามสูตรงบคงเหลือ", "ระบบอัตโนมัติ", "vpk_budget, vpk_purchase_contract", C),
        ("ควบคุมงบกับการจัดซื้อ", "ขอซื้อฉุกเฉิน/เร่งด่วน กับงบ", "PR ฉุกเฉินยังตรวจงบและใช้เส้นทางอนุมัติเร่งด่วน", "หน่วยงาน / พัสดุ", "vpk_purchase_request_urgent", C),
        ("Dashboard / รายงาน", "ติดตามงบประมาณประจำปี", "แถบสถานะงบภาพรวม ตารางสถานะการจองงบ กราฟเบิกจ่ายสะสมเทียบแผน แท่งเบิกจ่ายตามกลุ่มงาน โครงการลงทุน", "ผู้บริหาร / งานงบประมาณ", "vpk_budget", C),
        ("Dashboard / รายงาน", "ติดตามสถานะคำของบประมาณ", "กราฟคำขอเทียบยอดจัดสรร สัดส่วนประเภทงบ ตารางสถานะตามหน่วยงาน คำของบล่าสุด", "ผู้บริหาร / งานงบประมาณ", "vpk_budget", C),
        ("Dashboard / รายงาน", "กล่องอนุมัติเอกสาร", "ดูงานรออนุมัติ/อนุมัติแล้ว สถานะการอนุมัติหลายลำดับ", "ผู้อนุมัติ", "vpk_tier_validation", C),
    ],
}

MODULES["2.จัดซื้อจัดจ้าง"] = {
    "title": "2. จัดซื้อจัดจ้าง",
    "desc": "วงจรตั้งแต่แผนจัดซื้อ ใบขอซื้อ/จ้าง กระบวนการ e-GP ใบสั่งซื้อ สัญญา ตรวจรับ ไปจนถึงการประเมินผู้จำหน่าย",
    "rows": [
        ("แผนจัดซื้อจัดจ้าง", "แผนประจำปีงบประมาณ (ภายใน)", "จัดทำแผนจัดซื้อจัดจ้างประจำปี เป็นฐานสร้าง PR", "พัสดุ", "vpk_procurement_auto_pr", C),
        ("แผนจัดซื้อจัดจ้าง", "คำขอเพิ่มแผน", "ขอเพิ่ม/แก้ไขแผนนอกแผนเดิม พร้อมอนุมัติ", "หน่วยงาน / พัสดุ", "vpk_procurement_auto_pr", C),
        ("แผนจัดซื้อจัดจ้าง", "แผนปฏิบัติการจัดซื้อจัดจ้าง / รายเดือน", "ติดตามแผนอนุมัติ/ประกาศ ก่อหนี้ผูกพัน ส่งมอบ และเบิกเงิน รายเดือน", "พัสดุ", "vpk_procurement_action_plan", C),
        ("แผนจัดซื้อจัดจ้าง", "แผนรวมจัดซื้อจัดจ้าง (e-GP)", "บันทึกแผนที่จัดทำและประกาศแล้วในระบบ e-GP พร้อมรายการแผน", "พัสดุ", "vpk_ebidding", C),
        ("แผนจัดซื้อจัดจ้าง", "นำเข้าแผนจาก Excel / ประเภทเอกสาร e-GP ของแผน", "นำเข้าแผนเป็นชุด และกำหนดประเภทเอกสารแนบ", "พัสดุ", "vpk_ebidding", C),
        ("แผนจัดซื้อจัดจ้าง", "Auto Gen PR", "สร้าง PR อัตโนมัติจากจุดสั่งซื้อ (reorder) และสัญญาใกล้หมดอายุ", "ระบบอัตโนมัติ", "vpk_procurement_auto_pr", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "สร้างใบขอซื้อ/จ้าง/เช่า", "หน่วยงานเปิด PR กรอกหัวเอกสาร สินค้า คณะกรรมการ ตรวจงบ แนบเอกสารอนุมัติ", "หน่วยงาน", "purchase_request / l10n_th_gov_purchase_request", O),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "ขอซื้อฉุกเฉิน / เร่งด่วน", "PR ฉุกเฉิน-เร่งด่วน มีเหตุผลและเส้นทางอนุมัติเร่งด่วน", "หน่วยงาน", "vpk_purchase_request_urgent", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "ลำดับอนุมัติ PR หลายระดับ", "อนุมัติตามลำดับผ่านกล่องอนุมัติ และส่งจัดซื้อเมื่อผ่าน", "ผู้อนุมัติ", "vpk_tier_validation, purchase_request_tier_validation", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "แจ้งเตือนเมื่อ PR ไม่ผ่านอนุมัติ", "แจ้งผู้ขอและกลุ่มงานทางอีเมล/ระบบ", "ระบบอัตโนมัติ", "vpk_purchase_request_reject_notify", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "Dashboard พัสดุรับงาน / ใบขอซื้อจากหน่วยงาน", "พัสดุ monitor และรับงาน PR ที่ส่งมาจากหน่วยงาน", "พัสดุ", "vpk_procurement_inbox", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "ขอเลขสารบรรณจาก PR", "ออกเลขหนังสือสารบรรณและเชื่อมกับเอกสาร", "พัสดุ / สารบรรณ", "vpk_pr_saraban", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "ราคา/ปริมาณปีงบประมาณ (FY History)", "ตรวจราคา-ปริมาณที่เคยซื้อในปีงบประมาณบน PR/PO", "พัสดุ", "vpk_purchase_fy_history", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "สั่งซื้อขั้นต่ำ (MOQ)", "บันทึกและตรวจจำนวนสั่งซื้อขั้นต่ำตามผู้จำหน่าย", "พัสดุ", "vpk_purchase_moq", C),
        ("ใบขอซื้อ/จ้าง/เช่า (PR)", "รายละเอียดคุณลักษณะพัสดุ", "Auto gen คุณลักษณะจาก PR ที่มีสัญญา แนบเอกสาร/รูปแยกรายการ", "พัสดุ", "vpk_product_specification", C),
        ("กระบวนการ e-GP", "รายการโครงการ (Purchase Agreement)", "รวมงานจัดซื้อรายโครงการเป็นศูนย์กลาง e-GP: ส่ง PR เข้า e-GP บันทึกเอกสารตามขั้นตอน", "พัสดุ", "vpk_purchase_agreement_egp", C),
        ("กระบวนการ e-GP", "หัวข้อเอกสาร e-GP", "กำหนดหัวข้อ/รายการเอกสารที่ต้องแนบในแต่ละขั้น", "พัสดุ", "vpk_purchase_agreement_egp", C),
        ("กระบวนการ e-GP", "เปรียบเทียบราคา / รายงานผลและประกาศผู้ชนะ", "บันทึกผู้เสนอราคา เปรียบเทียบ จัดทำรายงานผลขออนุมัติ และประกาศผู้ชนะ", "พัสดุ", "vpk_purchase_agreement_egp, vpk_official_document", C),
        ("ใบสั่งซื้อ/จ้าง (PO)", "สร้าง/ยืนยัน PO", "สร้าง PO จากผู้ชนะ/ PR ผูกสัญญาและตรวจยอด", "พัสดุ", "purchase / purchase_request", S),
        ("ใบสั่งซื้อ/จ้าง (PO)", "แบบฟอร์มใบสั่งซื้อ/สั่งจ้าง", "พิมพ์ PO ตามแบบ VPK (QWeb/PDF)", "พัสดุ", "vpk_purchase_order_form", C),
        ("ใบสั่งซื้อ/จ้าง (PO)", "ส่ง PO เข้าแอป/พอร์ทัลผู้ขาย", "ผู้ขายล็อกอิน ดู PO เปิด PDF และยืนยัน/ลงนามออนไลน์", "พัสดุ / ผู้ขาย", "vpk_purchase_portal_egp, vpk_vendor_api", C),
        ("ใบสั่งซื้อ/จ้าง (PO)", "ประวัติ PO ที่ถูกยกเลิก / เหตุผลยกเลิก", "บันทึกเหตุผลและดูประวัติ PO ยกเลิก", "พัสดุ", "vpk_procurement_auto_pr, purchase_cancel_reason", C),
        ("สัญญาและหลักประกัน", "ทะเบียนสัญญา (รายการสัญญา)", "สัญญาหลัก ผูกบน PR/PO ตรวจยอดคงเหลือแบบ Hard Block ตัดลดเรียลไทม์ แบ่งงวดงาน", "พัสดุ", "vpk_purchase_contract", C),
        ("สัญญาและหลักประกัน", "หมวดสัญญา / ประเภทสัญญา", "ข้อมูลหลักสัญญา", "พัสดุ", "vpk_purchase_contract", C),
        ("สัญญาและหลักประกัน", "เอกสารสัญญา", "ดึงจาก Document Studio หรือแนบไฟล์ แล้วส่งลงนามตามลำดับ", "พัสดุ", "vpk_purchase_contract_document", C),
        ("สัญญาและหลักประกัน", "ทะเบียนหลักประกัน / รายการหลักประกัน", "บันทึกและติดตามหลักประกันสัญญา", "พัสดุ", "vpk_procurement_auto_pr", C),
        ("สัญญาและหลักประกัน", "ทะเบียนค่าปรับ", "บันทึกค่าปรับกรณีส่งมอบล่าช้า", "พัสดุ", "vpk_procurement_auto_pr", C),
        ("ตรวจรับ", "แต่งตั้งคณะกรรมการซื้อจ้าง", "ขออนุมัติแต่งตั้งกรรมการกำหนดคุณลักษณะ/ราคากลาง/จัดซื้อ/ตรวจรับ พร้อมแจ้งอีเมล", "พัสดุ", "vpk_committee_appointment", C),
        ("ตรวจรับ", "ตรวจรับมอบงาน", "ใบตรวจรับเชื่อมสัญญาและคณะกรรมการ บันทึกผลตรวจรับ", "คณะกรรมการ / พัสดุ", "vpk_work_acceptance, purchase_work_acceptance", C),
        ("หนังสือราชการ / เอกสาร", "หนังสือราชการจัดซื้อ", "ออกเอกสารตามแบบ: คำสั่งแต่งตั้ง, บันทึกขออนุมัติ, รายงานเฉพาะเจาะจง, ใบตรวจรับ, ประกาศผู้ชนะ, รายงานผลพิจารณา, แบบแสดงความบริสุทธิ์ใจ", "พัสดุ", "vpk_official_document", C),
        ("หนังสือราชการ / เอกสาร", "Document Studio / ลงนามเอกสาร", "ออกแบบฟอร์ม พิมพ์ Word/PDF ส่งลงนามบน PDF และขอเลขสารบรรณ", "พัสดุ / ผู้อนุมัติ", "vpk_document_studio*", C),
        ("ผู้จำหน่าย", "ข้อมูลผู้จำหน่าย + ตรวจข้อมูลซ้ำ + สิทธิ์", "จัดการผู้จำหน่าย ป้องกัน Tax ID/ชื่อ/เบอร์ซ้ำ กำหนดสิทธิ์เพิ่ม/แก้/ลบ", "พัสดุ", "vpk_partner_duplicate_check, vpk_vendor_security", C),
        ("ผู้จำหน่าย", "กลุ่มผู้จำหน่ายจัดซื้อ", "จัดกลุ่มผู้จำหน่ายเพื่อรายงานและควบคุม", "พัสดุ", "vpk_procurement_auto_pr", C),
        ("ผู้จำหน่าย", "ประเมินผู้จำหน่าย", "ใบประเมิน เกณฑ์ ให้คะแนน จัดเกรด และรายงาน", "พัสดุ", "vpk_vendor_evaluation", C),
        ("ผู้จำหน่าย", "ประวัติเจ้าหนี้ (ซื้อขาย / สินค้ามีปัญหา)", "ประวัติซื้อรายสินค้าและรายการสินค้ามีปัญหาต่อผู้จำหน่าย", "พัสดุ", "vpk_vendor_history", C),
        ("ผู้จำหน่าย", "ยืมของจากผู้ขาย", "รับของยืมด่วน เปิดขอซื้อตามหลัง และหักล้างเมื่อรับของจริง", "พัสดุ / คลัง", "vpk_vendor_loan", C),
        ("ติดตามและรายงาน", "ติดตามสถานะขอซื้อ/จ้าง/เช่า + Dashboard จัดซื้อ", "ติดตาม PR ที่ออก/ยังไม่ออก PO ภาพรวมการจัดซื้อ", "พัสดุ / ผู้บริหาร", "vpk_purchase_request_tracking", C),
        ("ติดตามและรายงาน", "Export รายงาน วัน/สัปดาห์/เดือน/ปี", "ส่งออกรายงาน PR/PO ตามช่วงเวลา", "พัสดุ", "vpk_purchase_request_tracking", C),
        ("ติดตามและรายงาน", "รายงานจัดซื้อ (ยอดซื้อ ทะเบียนคุม ค้างรับ ถึงกำหนดส่ง)", "ยอดซื้อแยกวัสดุ/ครุภัณฑ์/กลุ่มผู้จำหน่าย/ยา ED-NonED, ทะเบียนคุมสัญญา/e-GP/GFMIS, สินค้าค้างรับ, PO ถึงกำหนดส่ง, ราคาตามผู้จำหน่าย", "พัสดุ / ผู้บริหาร", "vpk_procurement_auto_pr", C),
    ],
}

MODULES["3.งานคลังและ Inventory"] = {
    "title": "3. งานคลังและ Inventory",
    "desc": "รับ-จ่าย-โอน-นับสต็อกสินค้า/ยา/เวชภัณฑ์ ควบคุมล็อต วันหมดอายุ QC และเชื่อมต่อ HIS",
    "rows": [
        ("Dashboard / ภาพรวม", "สถานะงานคลัง", "ภาพรวมใบรับ/จ่าย/โอนที่ค้างและเสร็จ", "คลัง", "vpk_stock_warehouse", C),
        ("Dashboard / ภาพรวม", "สถานะสินค้าคงคลัง", "ภาพรวมยอดคงคลัง ใกล้หมด ใกล้หมดอายุ", "คลัง / ผู้บริหาร", "vpk_stock_warehouse", C),
        ("Dashboard / ภาพรวม", "คลังและตำแหน่ง (Warehouse Overview)", "สำรวจคลัง/ชั้นวาง/Bin แบบ panel", "คลัง", "vpk_stock_warehouse", C),
        ("ข้อมูลหลัก", "สินค้า (ยา/เวชภัณฑ์)", "ข้อมูลสินค้า ยาตาม TOR ชื่อซื้อ e-GP แถบหมวดหมู่", "คลัง / พัสดุ", "vpk_product", C),
        ("ข้อมูลหลัก", "Import Product Master", "นำเข้า master สินค้าจาก Excel", "คลัง / IT", "vpk_product_import", C),
        ("ข้อมูลหลัก", "Change Product UoM", "เปลี่ยนหน่วยวัดสินค้า", "คลัง", "vpk_product", C),
        ("ข้อมูลหลัก", "หมวดสินค้า / หน่วยสินค้า (UoM)", "ตั้งหมวดย่อย หมวดยาจ่ายตามวันหมดอายุ (FEFO) และหน่วยบรรจุ", "คลัง", "stock / product", S),
        ("ข้อมูลหลัก", "คลังและตำแหน่งจัดเก็บ (Location)", "สร้างคลัง ชั้นวางแบบลำดับชั้น และควบคุมสิทธิ์เข้าถึงยาเสพติด", "คลัง", "vpk_stock_location, stock", C),
        ("ข้อมูลหลัก", "Template Master Data", "Template Excel ยกยอด คลัง สินค้า UoM", "คลัง / IT", "vpk_master_data_templates", C),
        ("รับสินค้า", "ตารางการส่งจากผู้ขาย", "ปฏิทิน/ตารางสินค้าที่ผู้ขายจะส่ง ก่อนวันรับ", "คลัง", "vpk_stock_warehouse", C),
        ("รับสินค้า", "ใบรับสินค้า (Receipt)", "รับเต็ม/บางส่วน ใส่ล็อตและวันหมดอายุ ตรวจสอบเข้าคลัง", "คลัง", "stock, purchase_stock", S),
        ("รับสินค้า", "ตรวจคุณภาพสินค้า (QC) / จุดควบคุมคุณภาพ", "ตรวจคุณภาพก่อนรับเข้าคลัง กำหนดจุด QC", "คลัง / QC", "vpk_stock_qc", C),
        ("รับสินค้า", "ยืมของจากผู้ขาย", "รับของยืม ตัดใช้ก่อนใบรับตามหลัง และหักล้าง", "คลัง / พัสดุ", "vpk_vendor_loan", C),
        ("โอน / เบิกจ่าย", "ขอโอนสินค้า", "หน่วยงานขอโอนสินค้าจากคลัง", "หน่วยงาน / คลัง", "vpk_stock_warehouse", C),
        ("โอน / เบิกจ่าย", "การโอนภายใน (Internal Transfer)", "เปิดใบโอน เลือกล็อต แพ็คลงกล่อง พิมพ์ฉลาก ส่งมอบ", "คลัง", "stock", S),
        ("โอน / เบิกจ่าย", "ใบขอเบิกภายในอัตโนมัติ (Replenishment)", "เติมสต็อกคลังหน่วยงานจากคลังใหญ่ก่อน ไม่พอค่อยเปิด PR", "ระบบ / คลัง", "vpk_stock_replenishment, vpk_stock_location", C),
        ("โอน / เบิกจ่าย", "จุดสั่งซื้อ (Reorder) และ Auto PR", "สร้าง PR อัตโนมัติเมื่อสต็อกต่ำกว่าเกณฑ์", "ระบบ / พัสดุ", "vpk_procurement_auto_pr", C),
        ("เชื่อมต่อ HIS", "HIS ตัดจ่ายสินค้า", "รับสรุปรายวันจาก HIS เข้าคิว staging แล้วตัดสต็อก", "คลัง / ระบบ", "vpk_his_api", C),
        ("เชื่อมต่อ HIS", "HIS เบิกเติมคลัง", "คิวเบิกเติมคลังจาก HIS", "คลัง / ระบบ", "vpk_his_api", C),
        ("เชื่อมต่อ HIS", "HIS Service Units / API Logs", "แมปหน่วยบริการ HIS กับ Location และบันทึก API", "IT", "vpk_his_api", C),
        ("นับ / ปรับสต็อก", "ใบนับสต็อก (Count Sheet)", "ใบนับที่เปิดอยู่ รายการนับ นำเข้า/ส่งออก Excel", "คลัง", "vpk_stock_location", C),
        ("นับ / ปรับสต็อก", "ปรับสินค้าคงคลัง (Inventory Adjustment)", "ใส่จำนวนที่นับได้ ระบุเหตุผล ปรับยอด", "คลัง", "stock", S),
        ("การผลิต", "การผลิตยา (BoM / สั่งผลิต)", "สูตรผลิต ใบสั่งผลิต บันทึกล็อตที่ผลิต", "คลัง / เภสัช", "mrp / stock", S),
        ("เครื่องมือ", "สแกนบาร์โค้ดมือถือ", "แอปสแกนบาร์โค้ดสำหรับรับ/โอน/นับ", "คลัง", "vpk_mobile_barcode", C),
        ("เครื่องมือ", "พิมพ์ฉลาก", "ฉลากกล่อง/ฉลากสินค้า และแสดงชื่อภาษาไทย", "คลัง", "vpk_th_discard_label / stock", C),
        ("รายงาน", "สินค้าค้างรับ / รับสินค้าประจำวัน", "ค้างรับแยกหมวด/ผู้ค้า และรายงานรับรายวัน", "คลัง / พัสดุ", "vpk_procurement_auto_pr", C),
        ("รายงาน", "รายงานคลังมาตรฐาน (Stock / Moves / Valuation)", "ยอดคงคลัง ความเคลื่อนไหว มูลค่าสต็อก", "คลัง / บัญชี", "stock, stock_account", S),
    ],
}

MODULES["4.งานบริหารทรัพย์สิน"] = {
    "title": "4. งานบริหารทรัพย์สิน",
    "desc": "ทะเบียนทรัพย์สิน ค่าเสื่อม โอน จำหน่าย ตรวจนับประจำปี และเชื่อมกับงานซ่อมบำรุง/จัดซื้อ/งบประมาณ",
    "rows": [
        ("ทะเบียนทรัพย์สิน", "บัตรสินทรัพย์ (Asset)", "ทะเบียนสินทรัพย์ถาวร วิธีคิดค่าเสื่อม มูลค่า สถานะ เลขสินทรัพย์", "ทรัพย์สิน / บัญชี", "account_asset_management, account_asset_number", O),
        ("ทะเบียนทรัพย์สิน", "ทะเบียนสินทรัพย์และแหล่งที่มา", "ติดตามแหล่งที่มาจาก PO, ใบแจ้งหนี้, GFMIS, งบประมาณ และสัญญา", "ทรัพย์สิน", "vpk_asset_registry", C),
        ("ทะเบียนทรัพย์สิน", "สินทรัพย์ประกอบเป็นชุด", "จัดกลุ่มสินทรัพย์ลูกเป็นชุด", "ทรัพย์สิน", "l10n_th_account_asset_management", O),
        ("ทะเบียนทรัพย์สิน", "ผู้ถือครอง / สถานะย่อยบนบัตร", "บันทึกผู้ถือครองและสถานะย่อย (เช่น รอจำหน่าย)", "ทรัพย์สิน / หน่วยงาน", "vpk_asset_registry, vpk_asset_disposal", C),
        ("ทะเบียนทรัพย์สิน", "พิมพ์ป้ายทรัพย์สิน (ภาษาไทย)", "พิมพ์ป้าย/QR ทรัพย์สิน", "ทรัพย์สิน", "vpk_asset_menu", C),
        ("โอน", "ใบโอนทรัพย์สินระหว่างหน่วยงาน", "ส่งขอโอน อนุมัติหลายลำดับ รับโอน เปลี่ยนหน่วยงานผู้ถือครอง", "หน่วยงาน / ทรัพย์สิน", "vpk_asset_transfer", C),
        ("จำหน่าย", "ใบขออนุมัติจำหน่าย", "ดึงรายการสถานะย่อยรอจำหน่าย ขออนุมัติ แล้วตัดออกจากทะเบียน", "หน่วยงาน / ทรัพย์สิน", "vpk_asset_disposal", C),
        ("ตรวจนับประจำปี", "รอบตรวจนับ", "เปิดรอบตรวจนับทรัพย์สินประจำปี และ gen sheet", "ทรัพย์สิน", "vpk_asset_inventory", C),
        ("ตรวจนับประจำปี", "Sheet ตามหน่วยงาน / Portal-QR", "หน่วยงานนับและบันทึกผลผ่าน Portal หรือสแกน QR", "หน่วยงาน", "vpk_asset_inventory", C),
        ("ตรวจนับประจำปี", "ผลการนับออนไลน์", "ดูผลนับ พบ/ไม่พบ ออนไลน์แบบเรียลไทม์", "ทรัพย์สิน / ผู้บริหาร", "vpk_asset_inventory", C),
        ("เชื่อมงานอื่น", "สร้าง Equipment จากบัตรสินทรัพย์", "สร้างรายการซ่อมบำรุงจากบัตรสินทรัพย์", "ทรัพย์สิน / ช่าง", "vpk_asset_equipment", C),
        ("เชื่อมงานอื่น", "ค่าเสื่อมราคาและรายการบัญชี", "คำนวณและลงรายการค่าเสื่อมเข้าบัญชี", "บัญชี", "account_asset_management", O),
        ("รายงาน / ตั้งค่า", "รายงานทรัพย์สิน", "รายงานตามเมนูรายงานของระบบสินทรัพย์", "ทรัพย์สิน / บัญชี", "account_asset_management, vpk_asset_menu", O),
        ("รายงาน / ตั้งค่า", "การตั้งค่า (หมวดสินทรัพย์ โปรไฟล์ค่าเสื่อม)", "กำหนดกลุ่ม/โปรไฟล์สินทรัพย์", "ทรัพย์สิน / บัญชี", "account_asset_management", O),
        ("รายงาน / ตั้งค่า", "Template ยกยอด Asset", "Template Excel ยกยอดสินทรัพย์", "ทรัพย์สิน / IT", "vpk_master_data_templates", C),
    ],
}

MODULES["5.งานซ่อมบำรุง"] = {
    "title": "5. งานซ่อมบำรุง",
    "desc": "แจ้งซ่อม ประเมิน เบิกอะไหล่ เปิด PR จ้างซ่อม แทงจำหน่าย ซ่อมป้องกันตามรอบ",
    "rows": [
        ("ข้อมูลหลัก", "อุปกรณ์ (Equipment)", "ทะเบียนอุปกรณ์/เครื่องมือ เชื่อมบัตรสินทรัพย์", "ช่างซ่อมบำรุง", "maintenance, vpk_asset_equipment", S),
        ("ข้อมูลหลัก", "หน่วยงานแจ้งซ่อม", "กำหนดหน่วยงานที่แจ้งซ่อม", "ผู้ดูแลระบบ", "vpk_maintenance", C),
        ("ข้อมูลหลัก", "ผลการประเมิน", "กำหนดผลประเมิน (ซ่อมได้/ไม่คุ้ม/ส่งซ่อมนอก ฯลฯ)", "ผู้ดูแลระบบ", "vpk_maintenance", C),
        ("คำขอซ่อม", "คำขอการซ่อมบำรุง", "เปิดคำขอซ่อม ระบุอุปกรณ์/อาการ/หน่วยงาน/ความเร่งด่วน", "หน่วยงาน / ช่าง", "maintenance", S),
        ("คำขอซ่อม", "สถานะย่อย (Sub State)", "สองแถบสถานะบนคำขอ: Stage หลัก และสถานะย่อยของการซ่อม", "ช่าง", "vpk_maintenance", C),
        ("คำขอซ่อม", "บันทึกผลการประเมิน", "ช่างประเมินความเสียหายและแนวทางซ่อม", "ช่าง", "vpk_maintenance", C),
        ("วัสดุ / จัดซื้อ", "เบิกอะไหล่", "เบิกอะไหล่จากคลังมาใช้ซ่อม บันทึกวัสดุที่ใช้", "ช่าง / คลัง", "vpk_maintenance, stock", C),
        ("วัสดุ / จัดซื้อ", "เปิดใบขอซื้อ/จ้างซ่อมจากคำขอ", "สร้าง PR จ้างซ่อมหรือซื้ออะไหล่จากคำขอซ่อม", "ช่าง / พัสดุ", "vpk_maintenance, purchase_request", C),
        ("วัสดุ / จัดซื้อ", "คำร้องส่งเครื่องซ่อมบริษัท", "ส่งเครื่องซ่อมภายนอกพร้อมติดตาม", "ช่าง / พัสดุ", "vpk_maintenance", C),
        ("จำหน่าย", "แทงจำหน่ายเมื่อซ่อมไม่คุ้ม", "ตั้งสถานะรอจำหน่ายเพื่อส่งต่อใบขออนุมัติจำหน่ายทรัพย์สิน", "ช่าง / ทรัพย์สิน", "vpk_maintenance, vpk_asset_disposal", C),
        ("ปิดงาน / PM", "ปิดงานซ่อม", "ปิดงานที่ซ่อมเสร็จ บันทึกค่าใช้จ่าย", "ช่าง", "maintenance", S),
        ("ปิดงาน / PM", "งานป้องกันตามรอบ (Preventive) / ปฏิทิน", "ตั้งรอบซ่อมบำรุงเชิงป้องกันและดูปฏิทินงาน", "ช่าง", "maintenance", S),
        ("Dashboard / รายงาน", "ติดตามงานซ่อม", "Dashboard สถานะงานซ่อมทั้งหมด", "ช่าง / ผู้บริหาร", "vpk_maintenance", C),
        ("Dashboard / รายงาน", "สรุปใบงานช่างซ่อมบำรุง", "รายงานสรุปใบงานช่าง", "ช่าง / ผู้บริหาร", "vpk_maintenance", C),
        ("Dashboard / รายงาน", "สรุปค่าใช้จ่ายการซ่อม", "สรุปค่าอะไหล่/ค่าจ้างต่อคำขอ/อุปกรณ์", "ผู้บริหาร / บัญชี", "vpk_maintenance", C),
        ("ตั้งค่า", "Template ยกยอด Equipment", "Template Excel ยกยอดอุปกรณ์", "IT", "vpk_master_data_templates", C),
    ],
}

MODULES["6.เจ้าหนี้ บัญชี การเงิน"] = {
    "title": "6. งานเจ้าหนี้ บัญชี การเงิน",
    "desc": "เจ้าหนี้ (ใบเรียกเก็บ/ภาษี/ลดหนี้) การเงิน (จ่ายเงิน GFMIS เช็ค ธนาคาร) และบัญชี (สมุดรายวัน งบการเงิน เชื่อม HIS/HR)",
    "rows": [
        ("เจ้าหนี้", "ใบเรียกเก็บเจ้าหนี้ (Vendor Bill)", "สร้างใบเรียกเก็บจากใบสั่งซื้อ/ใบรับของ ตรวจ 3-way match", "เจ้าหนี้", "account, purchase", S),
        ("เจ้าหนี้", "ภาษีซื้อและภาษีหัก ณ ที่จ่าย (WHT)", "บันทึกภาษีซื้อ ภาษีหัก ณ ที่จ่าย", "เจ้าหนี้ / บัญชี", "l10n-thailand, account", O),
        ("เจ้าหนี้", "ใบลดหนี้ (Credit Note)", "ลดหนี้/คืนสินค้า", "เจ้าหนี้", "account", S),
        ("เจ้าหนี้", "ส่งต่อการเงิน", "ส่งใบเรียกเก็บที่ตรวจแล้วเข้ากระบวนการจ่ายเงิน", "เจ้าหนี้ → การเงิน", "vpk_finance_flow, vpk_tier_validation", C),
        ("เจ้าหนี้", "ข้อมูลผู้จำหน่าย / ประวัติ", "ข้อมูลเจ้าหนี้ ประวัติซื้อขาย สินค้ามีปัญหา และสิทธิ์แก้ไข", "เจ้าหนี้ / พัสดุ", "vpk_vendor_history, vpk_vendor_security", C),
        ("เจ้าหนี้", "Template นำเข้าเจ้าหนี้", "Template ยกยอดเจ้าหนี้/ผู้จำหน่าย", "เจ้าหนี้ / IT", "vpk_master_data_templates", C),
        ("การเงิน", "ติดตามงานการเงิน", "Dashboard งานค้างและความเคลื่อนไหวของเจ้าหนี้/การเงิน/บัญชี", "การเงิน / ผู้บริหาร", "vpk_finance_flow", C),
        ("การเงิน", "จ่ายเงินจากใบเรียกเก็บ", "บันทึกการจ่ายชำระเจ้าหนี้ เลือกบัญชีธนาคาร/วิธีจ่าย", "การเงิน", "account, account-payment", S),
        ("การเงิน", "GFMIS - ขอเบิกเงิน", "สร้างเอกสารขอเบิกเงิน ผูกรายการใน ERP รวมภาษีหัก ณ ที่จ่าย/ค่าปรับ", "การเงิน", "vpk_gfmis", C),
        ("การเงิน", "GFMIS - ขอจ่ายโดยส่วนราชการ", "จ่ายผ่านส่วนราชการและบันทึกผล", "การเงิน", "vpk_gfmis", C),
        ("การเงิน", "GFMIS - เบิกเกินส่งคืน", "บันทึกเบิกเกินส่งคืน", "การเงิน", "vpk_gfmis", C),
        ("การเงิน", "GFMIS - รายงาน GF / รหัสหน่วยงาน / แบบฟอร์ม", "ทะเบียนเอกสาร GFMIS และข้อมูลหลัก", "การเงิน", "vpk_gfmis", C),
        ("การเงิน", "จัดการเช็ค (สมุดเช็ค/ใบเช็ค/แบบฟอร์ม)", "สมุดเช็ค พิมพ์เช็คจากใบเรียกเก็บหรือรายการจ่าย กำหนดตำแหน่งบนแบบฟอร์ม", "การเงิน", "vpk_cheque_management", C),
        ("การเงิน", "บัญชีธนาคารโรงพยาบาล", "ข้อมูลบัญชีธนาคารของโรงพยาบาล", "การเงิน", "vpk_th_account_menu", C),
        ("การเงิน", "บัญชีคุมเงินฝากธนาคาร (Subledger)", "ยอดรับ จ่าย คงเหลือแต่ละบัญชีธนาคาร + รายงานเงินฝาก", "การเงิน / บัญชี", "vpk_bank_subledger", C),
        ("การเงิน", "ใบนำส่งเงิน / ลูกหนี้ HIS", "ใบนำส่งเงิน ลูกหนี้คงค้างตามสิทธิ์ Aged Receivable", "การเงิน", "vpk_his_api", C),
        ("บัญชี", "ลงรายการบัญชี (Journal Entry)", "บันทึก ยืนยัน แก้ไขรายการที่ยืนยันแล้ว", "บัญชี", "account", S),
        ("บัญชี", "ผังบัญชี / สมุดรายวัน", "จัดการผังบัญชีและสมุดรายวัน", "บัญชี", "account", S),
        ("บัญชี", "ปีบัญชีและล็อกงวด", "กำหนดปีบัญชี ล็อกงวดบัญชี", "บัญชี", "account", S),
        ("บัญชี", "HIS Revenue / เงินมัดจำ", "รับสรุปรายได้/มัดจำรายวันจาก HIS แล้วลงบัญชี", "บัญชี / ระบบ", "vpk_his_api", C),
        ("บัญชี", "ชุดเงินเดือนจาก HR", "รับชุดเงินเดือนจาก HR แล้วสร้างสมุดรายวัน และแมปรหัสเงินเดือน", "บัญชี / ระบบ", "vpk_hr_payroll_api", C),
        ("บัญชี", "รายงานการเงิน รพ.", "งบแสดงฐานะการเงิน งบกระแสเงินสด งบผลการดำเนินงาน หมายเหตุ รายงานเงินฝาก", "บัญชี / ผู้บริหาร", "vpk_hospital_balance_sheet, account_reports", C),
        ("บัญชี", "รายงานบัญชีมาตรฐาน", "แยกประเภท งบทดลอง อายุเจ้าหนี้ ภาษี", "บัญชี", "account_reports, base_accounting_kit", S),
        ("บัญชี", "Template นำเข้าผังบัญชี/ยกยอด", "Template Excel ยกยอดผังบัญชี เจ้าหนี้ การเงิน บัญชี", "บัญชี / IT", "vpk_master_data_templates", C),
    ],
}

HEADERS = ["ลำดับ", "กลุ่มฟังก์ชัน", "ฟังก์ชัน / เมนู", "รายละเอียดการทำงาน", "ผู้ใช้งานหลัก", "Odoo module", "ประเภท"]
WIDTHS = [7, 24, 38, 70, 22, 34, 16]
NAVY = "1F3864"
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
HFILL = PatternFill("solid", fgColor=NAVY)
GFILL = PatternFill("solid", fgColor="DDEBF7")
TYPE_FILL = {C: "E2EFDA", S: "FFF2CC", O: "FCE4D6"}


def style_header(ws, row):
    for c in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(bold=True, color="FFFFFF", name="Prompt", size=11)
        cell.fill = HFILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def write_sheet(ws, title, desc, rows, with_module=False):
    ncol = len(HEADERS) + (1 if with_module else 0)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color=NAVY, name="Prompt")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)
    ws["A2"] = desc
    ws["A2"].font = Font(italic=True, size=10, color="595959", name="Prompt")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[2].height = 30

    headers = (["Module"] if with_module else []) + HEADERS
    widths = ([26] if with_module else []) + WIDTHS
    hr = 4
    for i, h in enumerate(headers, 1):
        ws.cell(row=hr, column=i, value=h)
    ws_cols = len(headers)
    for c in range(1, ws_cols + 1):
        cell = ws.cell(row=hr, column=c)
        cell.font = Font(bold=True, color="FFFFFF", name="Prompt", size=11)
        cell.fill = HFILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[hr].height = 24
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    r = hr + 1
    n = 0
    prev_group = None
    for row in rows:
        mod = None
        if with_module:
            mod, *row = row
        group, func, detail, user, mname, typ = row
        n += 1
        vals = ([mod] if with_module else []) + [n, group, func, detail, user, mname, typ]
        for i, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=i, value=v)
            cell.font = Font(name="Prompt", size=10)
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True,
                                       horizontal="center" if headers[i - 1] in ("ลำดับ", "ประเภท") else "left")
        off = 1 if with_module else 0
        if group != prev_group:
            ws.cell(row=r, column=2 + off).fill = GFILL
            ws.cell(row=r, column=2 + off).font = Font(name="Prompt", size=10, bold=True)
        prev_group = group
        ws.cell(row=r, column=7 + off).fill = PatternFill("solid", fgColor=TYPE_FILL[typ])
        r += 1
    ws.freeze_panes = ws.cell(row=hr + 1, column=1 + (1 if with_module else 0) + 3 - 1)
    ws.auto_filter.ref = f"A{hr}:{get_column_letter(ws_cols)}{r - 1}"
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{hr}:{hr}"


def write_io(wb, sheet_name, after, title, subtitle, funcs, phases):
    ws = wb.create_sheet(sheet_name, index=wb.sheetnames.index(after) + 1)
    has_m = any("method" in f for f in funcs)
    heads = ["รหัส", "ขั้นตอน (Phase)", "ฟังก์ชัน", "ผู้ใช้งาน", "เมนู / ปุ่ม", "Input (ข้อมูลเข้า)",
             "Process (การประมวลผล)", "Output (ผลลัพธ์)", "Model / Method"]
    widths = [7, 26, 30, 20, 28, 42, 38, 42, 40]
    if has_m:
        heads.insert(3, "วิธีจัดซื้อ")
        widths.insert(3, 14)
    off = 1 if has_m else 0
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(heads))
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color=NAVY, name="Prompt")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(heads))
    ws["A2"] = subtitle
    ws["A2"].font = Font(italic=True, size=10, color="595959", name="Prompt")
    for i, h in enumerate(heads, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", name="Prompt", size=11)
        c.fill = HFILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    pname = {c: f"{c}. {n}" for c, n, _ in phases}
    r = 5
    prev = None
    for f in funcs:
        vals = [f["code"], pname[f["phase"]], f["name"], f["actor"], f["menu"],
                "\n".join("• " + x for x in f["inputs"]),
                "\n".join("› " + x for x in f["process"]),
                "\n".join("• " + x for x in f["outputs"]), f["tech"]]
        if has_m:
            vals.insert(3, METHOD_LABEL[f["method"]])
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name="Prompt", size=10, bold=(i == 3))
            c.border = BORDER
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if i == 1 else "left")
        if f["phase"] != prev:
            ws.cell(row=r, column=2).fill = GFILL
            ws.cell(row=r, column=2).font = Font(name="Prompt", size=10, bold=True)
        ws.cell(row=r, column=6 + off).fill = PatternFill("solid", fgColor="E6EFFA")
        ws.cell(row=r, column=8 + off).fill = PatternFill("solid", fgColor="E5F5EA")
        if has_m:
            ws.cell(row=r, column=4).fill = PatternFill("solid", fgColor=M_FILL[f["method"]])
        prev = f["phase"]
        ws.row_dimensions[r].height = max(48, 15 * max(len(f["inputs"]), len(f["process"]), len(f["outputs"])) + 8)
        r += 1
    ws.freeze_panes = "D5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(heads))}{r - 1}"
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def write_integration(wb, sheet_name, after):
    ws = wb.create_sheet(sheet_name, index=wb.sheetnames.index(after) + 1)
    heads = ["รหัส", "จุดเชื่อม", "วิธีจัดซื้อ", "จากระบบ", "ไปยังระบบ", "Input (ข้อมูลที่ส่งไป)", "Output / ผลต่องบ",
             "ทริกเกอร์", "Field / Method"]
    widths = [7, 36, 14, 20, 20, 44, 50, 32, 52]
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(heads))
    ws["A1"] = "จัดซื้อจัดจ้าง: จุดรับ Input จากแผนงบที่อนุมัติ และผลกลับสู่งบ"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY, name="Prompt")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(heads))
    ws["A2"] = "ดูแผนภาพได้ที่ docs/Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx "
    ws["A2"].font = Font(italic=True, size=10, color="595959", name="Prompt")
    for i, h in enumerate(heads, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", name="Prompt", size=11)
        c.fill = HFILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    r = 5
    for t in PROC_INT:
        vals = [t["code"], t["name"], METHOD_LABEL[t["method"]], t["frm"], t["to"],
                "\n".join("• " + x for x in t["inputs"]),
                "\n".join("• " + x for x in t["outputs"]), t["trigger"], t["tech"]]
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name="Prompt", size=10, bold=(i in (1, 2)))
            c.border = BORDER
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if i == 1 else "left")
        ws.cell(row=r, column=3).fill = PatternFill("solid", fgColor=M_FILL[t["method"]])
        ws.cell(row=r, column=6).fill = PatternFill("solid", fgColor="E6EFFA")
        ws.cell(row=r, column=7).fill = PatternFill("solid", fgColor="E5F5EA")
        ws.row_dimensions[r].height = max(48, 16 * max(len(t["inputs"]), len(t["outputs"])) + 14)
        r += 1
    ws.freeze_panes = "C5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(heads))}{r - 1}"
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def write_contract_types(wb, sheet_name, after):
    ws = wb.create_sheet(sheet_name, index=wb.sheetnames.index(after) + 1)
    heads = ["ประเภทสัญญา", "รหัสขั้น", "ขั้นตอน", "ผู้ทำ", "Input", "Process", "Output", "Field / Method"]
    widths = [30, 9, 36, 22, 44, 46, 44, 44]
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(heads))
    ws["A1"] = "Workflow ตามประเภทสัญญา: สัญญาซื้อขาย / สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY, name="Prompt")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(heads))
    ws["A2"] = "ดูแผนภาพได้ที่ docs/Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx (สไลด์เปรียบเทียบประเภทสัญญาและ Workflow ประเภทสัญญา)"
    ws["A2"].font = Font(italic=True, size=10, color="595959", name="Prompt")
    r = 4
    ws.cell(row=r, column=1, value="เปรียบเทียบประเภทสัญญา").font = Font(bold=True, name="Prompt", size=11)
    r += 1
    for i, h in enumerate(["หัวข้อ", "", "สัญญาซื้อขาย", "", "สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน"], 1):
        pass
    for i, h in enumerate(["หัวข้อ", "สัญญาซื้อขาย", "สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน"], 1):
        c = ws.cell(row=r, column=[1, 3, 5][i - 1], value=h)
        c.font = Font(bold=True, color="FFFFFF", name="Prompt", size=11)
        c.fill = HFILL
        c.border = BORDER
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
    ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=8)
    r += 1
    for topic, a, b in CONTRACT_COMPARE:
        for col, v, fill in ((1, topic, "EEF1F4"), (3, a, "E5F5EA"), (5, b, "FDF3E0")):
            c = ws.cell(row=r, column=col, value=v)
            c.font = Font(name="Prompt", size=10, bold=(col == 1))
            c.fill = PatternFill("solid", fgColor=fill)
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border = BORDER
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=4)
        ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=8)
        ws.row_dimensions[r].height = 34
        r += 1
    r += 1
    hr = r
    for i, h in enumerate(heads, 1):
        c = ws.cell(row=r, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF", name="Prompt", size=11)
        c.fill = HFILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    r += 1
    for key, fill in (("sale", "E5F5EA"), ("framework", "FDF3E0")):
        info = CONTRACT_TYPES[key]
        for st in info["steps"]:
            vals = [info["name"], st["code"], st["name"], st["actor"],
                    "\n".join("• " + t for t in st["inputs"]),
                    "\n".join("› " + t for t in st["process"]),
                    "\n".join("• " + t for t in st["outputs"]), st["tech"]]
            for i, v in enumerate(vals, 1):
                c = ws.cell(row=r, column=i, value=v)
                c.font = Font(name="Prompt", size=10, bold=(i in (2, 3)))
                c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if i == 2 else "left")
                c.border = BORDER
            ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor=fill)
            ws.row_dimensions[r].height = max(48, 16 * max(len(st["inputs"]), len(st["process"]), len(st["outputs"])) + 14)
            r += 1
    ws.freeze_panes = ws.cell(row=hr + 1, column=3)
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def main():
    wb = Workbook()

    # Sheet สรุป
    ws = wb.active
    ws.title = "สรุปภาพรวม"
    ws.merge_cells("A1:F1")
    ws["A1"] = "สรุป Function ของระบบ ERP VPK (Odoo 18) แยกตาม Module"
    ws["A1"].font = Font(bold=True, size=15, color=NAVY, name="Prompt")
    hdr = ["ลำดับ", "Module", "ขอบเขตงาน", "จำนวนฟังก์ชัน", "Custom (VPK)", "Standard / OCA"]
    for i, h in enumerate(hdr, 1):
        ws.cell(row=3, column=i, value=h)
    for c in range(1, 7):
        cell = ws.cell(row=3, column=c)
        cell.font = Font(bold=True, color="FFFFFF", name="Prompt")
        cell.fill = HFILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    for i, w in enumerate([7, 30, 80, 16, 16, 16], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    r = 4
    tot = [0, 0, 0]
    for i, (key, m) in enumerate(MODULES.items(), 1):
        total = len(m["rows"])
        cust = sum(1 for x in m["rows"] if x[5] == C)
        vals = [i, m["title"], m["desc"], total, cust, total - cust]
        for j, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=j, value=v)
            cell.font = Font(name="Prompt", size=10, bold=(j == 2))
            cell.border = BORDER
            cell.alignment = Alignment(vertical="top", wrap_text=True, horizontal="center" if j in (1, 4, 5, 6) else "left")
        # hyperlink ไปยังชีต
        ws.cell(row=r, column=2).hyperlink = f"#'{key}'!A1"
        ws.cell(row=r, column=2).font = Font(name="Prompt", size=10, bold=True, color="0563C1", underline="single")
        tot[0] += total; tot[1] += cust; tot[2] += total - cust
        r += 1
    ws.cell(row=r, column=2, value="รวม")
    for j, v in enumerate(tot, 4):
        ws.cell(row=r, column=j, value=v)
    for c in range(1, 7):
        cell = ws.cell(row=r, column=c)
        cell.font = Font(bold=True, name="Prompt")
        cell.border = BORDER
        cell.fill = GFILL
        cell.alignment = Alignment(horizontal="center" if c != 2 else "left")
    r += 2
    ws.cell(row=r, column=2, value="คำอธิบายประเภท").font = Font(bold=True, name="Prompt")
    for k, txt in [(C, "พัฒนาเพิ่มเองสำหรับ รพ.วชิระภูเก็ต (vpk_*)"),
                   (S, "ฟังก์ชันมาตรฐานของ Odoo 18"),
                   (O, "โมดูลชุมชน OCA / l10n-thailand ที่นำมาใช้")]:
        r += 1
        c1 = ws.cell(row=r, column=2, value=k)
        c1.fill = PatternFill("solid", fgColor=TYPE_FILL[k])
        c1.font = Font(name="Prompt", size=10)
        c1.border = BORDER
        ws.cell(row=r, column=3, value=txt).font = Font(name="Prompt", size=10)
    r += 2
    ws.cell(row=r, column=2, value="หมายเหตุ").font = Font(bold=True, name="Prompt")
    ws.cell(row=r, column=3, value="สรุปจากเมนู/manifest ของ odoo18-custom-addons และคู่มือการใช้งานใน docs/คู่มือการใช้งาน "
                                   "ควรให้เจ้าของงานตรวจทานรายละเอียดอีกครั้ง").alignment = Alignment(wrap_text=True, vertical="top")
    ws.cell(row=r, column=3).font = Font(name="Prompt", size=10)
    ws.row_dimensions[r].height = 32

    # ชีตต่อ module
    for key, m in MODULES.items():
        s = wb.create_sheet(key[:31])
        write_sheet(s, m["title"], m["desc"], m["rows"])

    # ชีต Input / Process / Output ของงบประมาณ
    write_io(wb, "1.1 งบประมาณ Input-Output", "1.งบประมาณ",
             "งบประมาณ: Input / Process / Output ของแต่ละ function (สิ้นสุดที่แผนงบที่อนุมัติพร้อมใช้)",
             "ดูแผนภาพ Workflow/Dataflow ได้ที่ docs/Workflow-Dataflow-งบประมาณ.pptx",
             BUDGET_IO, BUDGET_PHASES)
    write_io(wb, "2.1 จัดซื้อ Input-Output", "2.จัดซื้อจัดจ้าง",
             "จัดซื้อจัดจ้าง: Input / Process / Output ของแต่ละ function (Input เริ่มจากแผนงบที่อนุมัติ → PR)",
             "ดูแผนภาพ Workflow/Dataflow ได้ที่ docs/Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx",
             PROC_IO, PROC_PHASES)
    write_integration(wb, "2.2 รับงบ-ผลกลับสู่งบ", "2.1 จัดซื้อ Input-Output")
    write_contract_types(wb, "2.3 Workflow ประเภทสัญญา", "2.2 รับงบ-ผลกลับสู่งบ")

    # ชีตรวม
    allrows = []
    for key, m in MODULES.items():
        for row in m["rows"]:
            allrows.append((m["title"], *row))
    s = wb.create_sheet("ตารางรวมทุก Module")
    write_sheet(s, "ตารางรวม Function ทุก Module", "กรอง/ค้นหาด้วย Filter ที่หัวคอลัมน์", allrows, with_module=True)

    wb.save(OUT)
    print("saved", OUT, tot)


if __name__ == "__main__":
    main()
