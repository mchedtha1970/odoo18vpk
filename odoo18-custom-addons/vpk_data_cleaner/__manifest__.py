# -*- coding: utf-8 -*-
{
    "name": "VPK ล้างข้อมูลตามโมดูล (Data Cleaner)",
    "version": "18.0.1.1.0",
    "category": "Administration",
    "summary": "จัดการล้างข้อมูลแยกตาม Module พร้อมจำแนกชัดเจนว่า Model ไหนเป็น Master หรือ Transaction",
    "description": """
VPK Data Cleaner — ระบบล้างข้อมูลแยกตามโมดูล
=============================================
* แสดงรายการ Module ที่ติดตั้งในระบบ แยกกลุ่ม VPK / ภาษาไทย & OCA / มาตรฐาน Odoo
* จำแนกทุก Model ในแต่ละ Module อย่างชัดเจนว่าเป็น:
  - **Transaction (ข้อมูลรายการเคลื่อนไหว / เอกสาร)**
  - **Master (ข้อมูลหลัก / ค่าตั้งต้นระบบ)**
* แสดงจำนวนแถวปัจจุบัน (Record Count) แบบสดจากฐานข้อมูล พร้อมตารางแม่-ลูก
* เลือกล้างเฉพาะ Transaction ของแต่ละ Module หรือเลือกล้างราย Model ได้
* จัดลำดับการลบตารางลูกก่อนตารางแม่อัตโนมัติ (Topological Foreign Key Sort)
* รองรับการลบประวัติแชท กิจกรรม สายอนุมัติ ไฟล์แนบ และรีเซ็ตเลขรันเอกสาร (ir.sequence)
* ป้องกันข้อมูลระบบสำคัญ (Users, Companies, System Parameters) ไม่ให้ถูกลบจนระบบพัง
* บันทึกประวัติการล้างข้อมูลทุกครั้ง (Audit Log)
    """,
    "author": "VPK",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/data_cleaner_wizard_views.xml",
        "views/discuss_cleaner_wizard_views.xml",
        "views/data_cleaner_model_views.xml",
        "views/data_cleaner_module_views.xml",
        "views/data_cleaner_log_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}
