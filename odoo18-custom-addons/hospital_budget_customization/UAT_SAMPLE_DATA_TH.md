# ชุดข้อมูลตัวอย่าง UAT (ภาษาไทย)

เอกสารนี้ใช้เตรียมข้อมูลทดสอบสำหรับโมดูล `hospital_budget_customization`  
เงื่อนไขตั้งต้น: มี `Budgetary Position` ที่ผูกบัญชีค่าใช้จ่ายครบแล้ว

## 1) ข้อมูลหลักที่ต้องมี (Master Data)

### 1.1 Analytic Account (แผนก/ศูนย์ต้นทุน)
- `MED-001` อายุรกรรม
- `SUR-001` ศัลยกรรม
- `ADM-001` บริหารทั่วไป

### 1.2 Budget Fund Source (แหล่งเงิน)
ใช้ค่าเริ่มต้นจากระบบ:
- `HOSP_MAINT` เงินบำรุง
- `STATE_BUDGET` เงินงบประมาณ
- `UC_FUND` เงินกองทุนหลักประกันสุขภาพ (UC)
- `DONATION` เงินบริจาค

### 1.3 สินค้าทดสอบสำหรับจัดซื้อ
- `P-001` ถุงมือแพทย์ (สินค้า stockable)
- `P-002` น้ำยาเวชภัณฑ์ (สินค้า consumable)
- `S-001` บริการสอบเทียบเครื่องมือแพทย์ (service)

## 2) ข้อมูลตั้งงบตัวอย่าง (Budget + Budget Lines)

## 2.1 สร้าง Budget Header
- Budget Name: `BUDGET-FY2026-UAT`
- Period: `2026-10-01` ถึง `2027-09-30`
- Company: บริษัท/หน่วยงานที่ใช้ทดสอบ

## 2.2 สร้าง Budget Lines (เลือก Budgetary Position ที่มีอยู่แล้ว)
ให้เลือก `Budgetary Position` ที่เกี่ยวกับค่าใช้จ่ายจริงของแผนกนั้น

### ชุดตัวอย่าง A (แนะนำ)
- Line 1
  - Analytic Account: `MED-001`
  - Fund Source: `STATE_BUDGET`
  - Requested Amount: `500000`
  - Planned Amount: `500000`
- Line 2
  - Analytic Account: `SUR-001`
  - Fund Source: `UC_FUND`
  - Requested Amount: `700000`
  - Planned Amount: `700000`
- Line 3
  - Analytic Account: `ADM-001`
  - Fund Source: `HOSP_MAINT`
  - Requested Amount: `300000`
  - Planned Amount: `300000`

รวมงบอนุมัติเบื้องต้น: `1,500,000`

## 3) ข้อมูลเอกสารทดสอบ PR/PO

## 3.1 เอกสาร PR สำหรับทดสอบผ่าน (งบพอ)
- PR Ref: `PR-UAT-001`
- Budget: `BUDGET-FY2026-UAT`
- Fund Source: `STATE_BUDGET`
- Department (Requester): `MED-001`
- รายการ:
  - P-001 จำนวน 100 กล่อง ราคา 1200 = `120000`
- Expected: กด `To be approved` แล้วผ่าน

## 3.2 เอกสาร PR สำหรับทดสอบไม่ผ่าน (งบไม่พอ)
- PR Ref: `PR-UAT-002`
- Budget: `BUDGET-FY2026-UAT`
- Fund Source: `STATE_BUDGET`
- Department (Requester): `MED-001`
- รายการ:
  - P-002 จำนวน 1000 หน่วย ราคา 1000 = `1000000`
- Expected: กด `To be approved` แล้วระบบ Block งบไม่พอ

## 3.3 เอกสาร PO สำหรับทดสอบผ่าน
- PO Ref: `PO-UAT-001`
- อ้างอิงจาก PR-UAT-001
- Amount Untaxed: `110000` ถึง `120000`
- Expected: `Confirm Order` ผ่าน

## 3.4 เอกสาร PO สำหรับทดสอบ Block
- PO Ref: `PO-UAT-002`
- Budget: `BUDGET-FY2026-UAT`
- Fund Source: `UC_FUND`
- Amount Untaxed: `900000` (หรือมากกว่า Available ของ line ที่เกี่ยวข้อง)
- Expected: `Confirm Order` ไม่ผ่าน พร้อมข้อความงบไม่พอ

## 4) ข้อมูลทดสอบ Audit Trail การปรับงบ

- เปิด Budget `BUDGET-FY2026-UAT`
- เลื่อนไปสถานะ review (Budget Office/Executive)
- เลือก Budget Line ของ `SUR-001`
- ใช้ปุ่ม `Adjust Budget Amount`
  - old amount: `700000`
  - new amount: `650000`
  - reason: `ปรับลดตามเพดานวงเงินที่ผู้บริหารอนุมัติ`
- Expected:
  - มี log บันทึก old/new/delta/reason/user/time

## 5) ข้อมูลทดสอบรายงานเปรียบเทียบ

รันปุ่ม `Budget Comparison Report` ด้วย filter ตามนี้:

- กรณี A:
  - Budget: `BUDGET-FY2026-UAT`
  - Fund Source: `STATE_BUDGET`
  - Department: เว้นว่าง
- กรณี B:
  - Budget: `BUDGET-FY2026-UAT`
  - Fund Source: เว้นว่าง
  - Department: `MED-001`

Expected:
- PDF แสดงคอลัมน์ Planned / Encumbrance / Actual ครบ
- ผลลัพธ์เปลี่ยนตาม filter

## 6) เช็กลิสต์ผลลัพธ์สำคัญ (Pass Criteria ย่อ)

- Historical 3 ปีแสดงได้ใน Budget Line
- เลือกแหล่งเงินได้ทั้ง Budget/PR/PO
- ระบบ Block PR/PO เมื่อ Available ไม่พอ
- มี Audit Trail ทุกครั้งที่ปรับ Planned Amount ในช่วง review
- รายงาน PDF พิมพ์ได้และกรองข้อมูลได้จริง
