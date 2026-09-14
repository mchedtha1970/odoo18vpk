#!/usr/bin/env python3
# Copyright 2026 VPK
"""Generate HIS stock requisition (main warehouse → front) specification as a Word document."""

import importlib.util
from pathlib import Path

_REV = Path(__file__).resolve().parent / "build_revenue_spec.py"
_spec = importlib.util.spec_from_file_location("build_revenue_spec", _REV)
_rev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rev)

SpecDoc = _rev.SpecDoc
NAVY = _rev.NAVY
TEAL = _rev.TEAL
set_run_font = _rev.set_run_font
WD_ALIGN_PARAGRAPH = _rev.WD_ALIGN_PARAGRAPH

OUT = Path(__file__).resolve().parent / "VPK-HIS-SPEC-STK-002-การเบิกเติมคลัง.docx"


class RequisitionSpecDoc(SpecDoc):
    def _setup_page(self):
        section = self.doc.sections[0]
        section.page_width = _rev.Cm(21.0)
        section.page_height = _rev.Cm(29.7)
        section.left_margin = _rev.Cm(2.0)
        section.right_margin = _rev.Cm(2.0)
        section.top_margin = _rev.Cm(2.0)
        section.bottom_margin = _rev.Cm(2.0)
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run(
            "โรงพยาบาลวชิระภูเก็ต  ·  HIS Stock Requisition Specification"
        )
        set_run_font(r, size=12, color=NAVY)
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("VPK-HIS-SPEC-STK-002  ·  ร่าง  ·  หน้า ")
        set_run_font(r, size=12, color=NAVY)
        _rev.add_page_number(fp)


def build():
    d = RequisitionSpecDoc()

    d.p("โรงพยาบาลวชิระภูเก็ต", size=20, bold=True, align="center", space_after=4, color=NAVY)
    d.p("ระบบคลังและบัญชี ERP (Odoo 18)", size=16, align="center", space_after=18, color=TEAL)
    d.p(
        "ข้อกำหนดการรับคำขอเบิกเติมสินค้าจากคลังหลักไปคลังบริการหน้า",
        size=26,
        bold=True,
        align="center",
        space_after=4,
        color=NAVY,
    )
    d.p(
        "HIS Stock Requisition (Replenishment) Specification",
        size=18,
        align="center",
        space_after=20,
        color=TEAL,
    )
    d.p(
        "เอกสารร่างสำหรับผู้พัฒนาระบบ HIS, ฝ่ายเภสัชกรรม/คลัง และฝ่ายเทคโนโลยีสารสนเทศ",
        size=16,
        align="center",
        space_after=24,
    )

    d.table(
        ["รายการ", "รายละเอียด"],
        [
            ["รหัสเอกสาร", "VPK-HIS-SPEC-STK-002"],
            ["เวอร์ชัน", "1.0  (ร่าง)"],
            ["วันที่", "26 สิงหาคม 2569"],
            ["สถานะ", "Draft — สำหรับทบทวนร่วมกับฝ่าย HIS / เภสัชกรรม"],
            ["ระบบต้นทาง", "Hospital Information System (Front HIS / ห้องยาหน้า / หน่วยบริการ)"],
            ["ระบบปลายทาง", "Odoo 18 ERP  โรงพยาบาลวชิระภูเก็ต"],
            ["โมดูล", "vpk_his_api"],
            ["ขอบเขตฉบับนี้", "การขอเบิกยา/เวชภัณฑ์จากคลังหลักไปเติมคลัง front (internal transfer)"],
            ["เอกสารที่เกี่ยวข้อง", "VPK-HIS-SPEC-STK-001 ตัดจ่ายจากการให้บริการ · VPK-HIS-SPEC-REV-001 รายได้"],
            ["ผู้ใช้เอกสาร", "ทีม HIS / เภสัชกรรมคลัง / IT"],
        ],
        col_widths=[5.5, 11.5],
    )

    d.h1("วัตถุประสงค์และขอบเขต")
    d.h2("วัตถุประสงค์")
    d.p(
        "เอกสารนี้กำหนดวิธีที่ระบบ HIS ส่งคำขอเบิกยาและเวชภัณฑ์จากคลังหลักของโรงพยาบาล "
        "(เช่น คลังยา PHAR หรือคลังกลาง WH) ไปยังคลังบริการหน้า (เช่น UNIT / ห้องยา OPD) "
        "เพื่อเติมสต็อกให้หน่วยบริการสามารถจ่ายยาให้คนไข้ได้ "
        "กระบวนการนี้ไม่เกี่ยวกับการจ่ายให้คนไข้โดยตรง — ไม่ต้องส่ง HN/VN",
        align="justify",
    )
    d.h2("อยู่ในขอบเขต")
    d.bullets(
        [
            "รับคำขอเบิกผ่าน REST API POST /vpk/api/v1/his/stock-requisitions",
            "ระบุคลังต้นทาง (source) และคลังปลายทาง (dest) เช่น PHAR → UNIT",
            "รองรับยา (drug) และเวชภัณฑ์ไม่ใช่ยา (medical_supply)",
            "ส่ง Lot ได้แต่ไม่บังคับตอนขอเบิก — ถ้าไม่ส่ง ERP เลือก Lot แบบ FEFO ตอน Post",
            "จัดคิวตรวจสอบใน HIS เบิกเติมคลัง แล้วให้เภสัชกร/เจ้าหน้าที่คลังกด Post",
            "เมื่อ Post สร้าง Internal Transfer (picking ประเภท HISINT)",
            "ยกเลิกชุดที่ Post แล้วด้วย reversal batch",
        ]
    )
    d.h2("อยู่นอกขอบเขตฉบับนี้")
    d.bullets(
        [
            "การตัดจ่ายยาให้คนไข้ — ใช้ VPK-HIS-SPEC-STK-001 / POST /stock-issues",
            "การรับสรุปรายได้ — ใช้ VPK-HIS-SPEC-REV-001 / POST /revenue",
            "การคืนยาจากคลัง front กลับคลังหลัก (reverse flow) — ยังไม่มี endpoint แยกในเอกสารนี้",
            "การสร้างรหัสสินค้าหรือ Lot ใหม่ใน ERP จาก HIS — ต้องมีรหัสอยู่ก่อน",
            "การส่ง HN, VN, ชื่อคนไข้ หรือข้อมูลส่วนบุคคล — ไม่เกี่ยวข้องกับการเบิกเติมคลัง",
        ]
    )
    d.h2("หลักการออกแบบ")
    d.bullets(
        [
            "เบิกเติมคลัง ≠ ตัดจ่ายคนไข้: เป็นการโอนสต็อกภายในองค์กร ไม่ใช่ consumption",
            "ทิศทางมาตรฐาน: คลังหลัก (PHAR/WH) → คลัง front (UNIT) หรือที่เก็บย่อยของหน่วยบริการ",
            "Staging ก่อนโอน: draft → ready|error แล้วเจ้าหน้าที่ Post",
            "Idempotency: คีย์ซ้ำคือ source_system + external_id",
            "Lot ตาม ERP: ส่ง lot_name/lots[] ได้ แต่ไม่บังคับ — ระบบเลือก FEFO จากคลังต้นทางถ้าไม่ระบุ",
            "ไม่สร้างสินค้า/Lot ใหม่อัตโนมัติ: รหัสไม่รู้จักทำให้ชุดข้อมูลเข้า error",
        ]
    )

    d.h1("ความแตกต่างจากการตัดจ่าย (stock-issues)")
    d.table(
        ["หัวข้อ", "stock-requisitions (เอกสารนี้)", "stock-issues (STK-001)"],
        [
            ["วัตถุประสงค์", "เติมสต็อกคลัง front จากคลังหลัก", "ตัดจ่ายให้คนไข้จากการบริการ"],
            ["Endpoint", "POST /stock-requisitions", "POST /stock-issues"],
            ["HN / VN", "ไม่ต้องส่ง", "จำเป็นเมื่อ reason = patient_use"],
            ["reason", "ไม่มีฟิลด์นี้", "patient_use, ward_use, expired, adjust"],
            ["เอกสารเมื่อ Post", "Internal Transfer (HISINT)", "HISOUT → Consumption หรือ Scrap"],
            ["ทิศทางสต็อก", "PHAR → UNIT (เพิ่มสต็อก front)", "UNIT → Consumption (ลดสต็อก front)"],
        ],
        col_widths=[4.5, 6.2, 6.3],
    )

    d.h1("สถาปัตยกรรมและขั้นตอนงาน")
    d.h2("ภาพรวมการไหลของข้อมูล")
    d.bullets(
        [
            "หน่วยบริการ (เช่น OPD / ห้องยาชั้น 1) ตรวจสอบสต็อกคงเหลือและจัดทำรายการขอเบิก",
            "HIS ส่ง POST JSON ไปที่ /vpk/api/v1/his/stock-requisitions พร้อมรหัสสินค้า จำนวน คลังต้นทาง/ปลายทาง",
            "ERP ตรวจรหัสสินค้า คลัง และ Lot (ถ้ามี) แล้วสร้างชุดข้อมูลในคิว HIS เบิกเติมคลัง",
            "ถ้าแมปครบ ชุดอยู่ในสถานะ Ready — เภสัชกร/คลังเปิดตรวจแล้วกด Post",
            "ระบบสร้างใบโอนภายใน (picking ประเภท HISINT) จากคลังต้นทางไปคลัง/ที่เก็บปลายทาง",
            "สต็อกคลังหลักลดลง สต็อกคลัง front เพิ่มขึ้นตามจำนวนที่เบิก",
        ],
        numbered=True,
    )
    d.h2("บทบาทระบบ")
    d.table(
        ["ระบบ", "หน้าที่"],
        [
            ["HIS / ห้องยาหน้า", "สร้างคำขอเบิก ส่งรหัสสินค้า จำนวน คลังต้นทาง/ปลายทาง หน่วยบริการ"],
            ["REST API (vpk_his_api)", "รับ JSON, จัดคิว, ตอบสถานะชุดข้อมูล"],
            ["เภสัชกร / เจ้าหน้าที่คลัง", "ตรวจคิว HIS เบิกเติมคลัง, กด Post, ติดตามสต็อก"],
            ["Odoo Inventory", "ใบโอน HISINT, Lot, คลัง PHAR/UNIT/WH และที่เก็บย่อย"],
        ],
        col_widths=[5, 12],
    )

    d.h1("การเชื่อมต่อและการยืนยันตัวตน")
    d.h2("โปรโตคอล")
    d.table(
        ["รายการ", "ค่า"],
        [
            ["โปรโตคอล", "HTTPS, JSON (application/json; charset=utf-8)"],
            ["เวอร์ชัน API", "v1"],
            ["Base path", "/vpk/api/v1/his"],
            ["Endpoint หลัก", "POST /vpk/api/v1/his/stock-requisitions"],
            ["วันที่", "YYYY-MM-DD (คริสต์ศักราช)"],
            ["จำนวน", "ตัวเลข ทศนิยมตามหน่วยนับสินค้า"],
        ],
        col_widths=[5, 12],
    )
    d.h2("การยืนยันตัวตน")
    d.p("ทุก endpoint ยกเว้น health ต้องส่ง API key อย่างใดอย่างหนึ่ง:")
    d.code("X-Api-Key: <HIS_API_KEY>\n\nหรือ\n\nAuthorization: Bearer <HIS_API_KEY>")
    d.table(
        ["HTTP", "ความหมาย"],
        [
            ["401", "ไม่มีคีย์ หรือคีย์ไม่ถูกต้อง"],
            ["503", "ปิด HIS API จากตั้งค่า หรือยังไม่กำหนดคีย์บนเซิร์ฟเวอร์"],
        ],
        col_widths=[3, 14],
    )
    d.note("คีย์ตั้งที่ การตั้งค่า → การออกใบแจ้งหนี้ → HIS API Key ห้ามฝังคีย์ในเอกสารนี้")

    d.h1("รายการ API ที่เกี่ยวข้อง")
    d.table(
        ["Method", "Path", "Auth", "หน้าที่"],
        [
            ["GET", "/vpk/api/v1/his/health", "ไม่ต้อง", "ตรวจว่าบริการทำงานและมีการตั้งคีย์"],
            ["POST", "/vpk/api/v1/his/stock-requisitions", "ต้อง", "ส่งคำขอเบิก / reversal เบิก"],
            ["GET", "/vpk/api/v1/his/batches/{external_id}", "ต้อง", "สอบถามสถานะชุด (query source_system)"],
            ["GET", "/vpk/api/v1/his/lookups/warehouses", "ต้อง", "รายการคลังและแมปหน่วยบริการ"],
            ["GET", "/vpk/api/v1/his/lookups/products", "ต้อง", "สอบถามรหัสสินค้าและว่าติดตาม Lot หรือไม่"],
        ],
        col_widths=[2.2, 7.5, 2.0, 5.3],
    )

    d.h1("สัญญาข้อมูล POST /stock-requisitions")
    d.h2("ฟิลด์ระดับชุดข้อมูล (batch)")
    d.table(
        ["ฟิลด์", "ชนิด", "จำเป็น", "คำอธิบาย"],
        [
            ["external_id", "string", "ใช่", "รหัสชุดข้อมูลฝั่ง HIS ต้องไม่ซ้ำใน source_system เดียวกัน"],
            ["source_system", "string", "ใช่", "รหัสระบบต้นทาง เช่น front_his"],
            ["business_date", "date", "ใช่", "วันที่ทางธุรกิจ YYYY-MM-DD"],
            ["shift", "string", "ไม่", "รหัสกะ เช่น 1, 2, night"],
            ["batch_type", "string", "ไม่", "stock_requisition (ค่าเริ่มต้น) หรือ reversal"],
            ["original_external_id", "string", "เมื่อยกเลิก", "external_id ของชุดที่ Post แล้ว"],
            ["source_warehouse_code", "string", "แนะนำ", "คลังต้นทาง เช่น PHAR, WH — ค่าเริ่มต้น PHAR"],
            ["dest_warehouse_code", "string", "แนะนำ*", "คลังปลายทาง เช่น UNIT (*หรือใช้ department_code แมป)"],
            ["dest_location_code", "string", "ไม่", "ที่เก็บปลายทาง เช่น shelf ห้องยาชั้น 1"],
            ["department_code", "string", "ไม่", "รหัสหน่วยบริการ HIS เช่น OPD — ใช้แมป dest ถ้าไม่ส่ง dest_warehouse_code"],
            ["lines", "array", "ใช่*", "บรรทัดขอเบิก (*หรือใช้ items / requisitions แทนได้)"],
            ["control_totals.qty_total", "number", "แนะนำ", "ยอดคุมจำนวนรวม ถ้าส่งมาต้องเท่าผลรวม qty"],
        ],
        col_widths=[5.2, 2.2, 2.2, 7.4],
    )
    d.h2("บรรทัดขอเบิก (lines[] / items[] / requisitions[])")
    d.table(
        ["ฟิลด์", "ชนิด", "จำเป็น", "คำอธิบาย"],
        [
            ["line_external_id", "string", "แนะนำ", "รหัสบรรทัดฝั่ง HIS"],
            ["product_code", "string", "ใช่", "รหัสสินค้า ERP (default_code) ยาตัวเลข pad เป็น 5 หลัก"],
            ["item_type", "string", "ไม่", "drug | medical_supply | other"],
            ["qty", "number", "ใช่", "จำนวนขอเบิก ห้ามเป็นศูนย์ (ถ้ามี lots[] ต้องเท่าผลรวม lot)"],
            ["uom", "string", "ไม่", "หน่วยนับ HIS ต้องเข้ากับหมวดหน่วยของสินค้า"],
            ["lot_name", "string", "ไม่", "Lot ที่ต้องการเบิก (ไม่บังคับ) — ห้ามส่งคู่กับ lots[]"],
            ["lots", "array", "ไม่", "หลาย Lot ในรายการเดียวกัน แต่ละองค์ประกอบมี lot_name และ qty"],
        ],
        col_widths=[4.5, 2.2, 2.2, 8.1],
    )
    d.h2("lots[]")
    d.table(
        ["ฟิลด์", "ชนิด", "จำเป็น", "คำอธิบาย"],
        [
            ["lot_name", "string", "ใช่", "ชื่อ Lot ใน ERP (หรือใช้ฟิลด์ lot / name)"],
            ["qty", "number", "ใช่", "จำนวนของ Lot นั้น"],
            ["line_external_id", "string", "ไม่", "ถ้าว่างระบบสร้างจากรหัสบรรทัดแม่ + ชื่อ Lot"],
        ],
        col_widths=[4.5, 2.2, 2.2, 8.1],
    )
    d.note(
        "การเบิกเติมคลังไม่เกี่ยวกับคนไข้ — ห้ามส่ง hn, vn หรือข้อมูลส่วนบุคคล "
        "(ถ้าส่งมาระบบจะตัดทิ้งตามนโยบาย PII ทั่วไป)"
    )

    d.h1("รหัสมาตรฐาน")
    d.h2("ประเภทสินค้า (item_type)")
    d.table(
        ["รหัส", "ความหมาย"],
        [
            ["drug", "ยา / เวชภัณฑ์ยา"],
            ["medical_supply", "เวชภัณฑ์ไม่ใช่ยา"],
            ["other", "อื่น ๆ"],
        ],
        col_widths=[5, 12],
    )
    d.h2("คลังที่เกี่ยวข้อง")
    d.table(
        ["รหัสคลัง", "ชื่อโดยสังเขป", "บทบาทในการเบิก"],
        [
            ["PHAR", "คลังยา", "คลังต้นทางหลัก (source) สำหรับยา"],
            ["WH", "คลังกลาง", "คลังต้นทางทางเลือก"],
            ["UNIT", "คลังยาหน่วยงาน", "คลังปลายทาง (dest) สำหรับ front / OPD"],
            ["SUPP", "คลังเวชภัณฑ์มิใช่ยา", "คลังต้นทาง/ปลายทางสำหรับเวชภัณฑ์"],
        ],
        col_widths=[3.2, 5.0, 8.8],
    )
    d.note(
        "ที่เก็บปลายทางระบุด้วย dest_location_code เป็นชื่อตำแหน่งใน ERP "
        "เช่น \"shelf ห้องยาชั้น 1 (1182,1183,1184,1185,1186)\" "
        "หรือใช้ department_code แมปจากเมนู HIS Service Units"
    )

    d.h1("กฎการโอนสต็อกเมื่อ Post")
    d.bullets(
        [
            "สร้าง picking ประเภท HISINT (Internal Transfer) จาก source_location ไป dest_location",
            "ใช้ picking type internal ของคลังต้นทาง หรือสร้าง HISINT อัตโนมัติถ้ายังไม่มี",
            "สินค้าที่ส่ง Lot จะโอนตาม Lot ที่ระบุ",
            "สินค้าติดตาม Lot แต่ไม่ส่ง Lot — ERP เลือก Lot จากคลังต้นทางแบบ FEFO (First Expired First Out)",
            "ห้ามสร้างรหัสสินค้าหรือ Lot ใหม่ขณะ Post — ต้องผ่าน Validate เป็น ready ก่อน",
            "หลัง Post สำเร็จ สต็อกคลังต้นทางลด สต็อกคลังปลายทางเพิ่มตามจำนวน",
        ]
    )
    d.h2("กฎ Lot")
    d.bullets(
        [
            "ตอนขอเบิก: ส่ง lot_name/lots[] ได้แต่ไม่บังคับ",
            "ตอน Post: ถ้าไม่ส่ง Lot และสินค้าติดตาม Lot ระบบเลือก FEFO จากคลังต้นทาง",
            "Lot ที่ส่งมาต้องมีอยู่แล้วใน ERP และผูกกับสินค้ารหัสนั้น",
            "สอบถาม tracking ได้ที่ GET /lookups/products?codes=00001",
        ]
    )

    d.h1("สถานะชุดข้อมูลและการทำงานของเจ้าหน้าที่")
    d.table(
        ["state", "ความหมาย", "HIS ทำอะไรได้", "คลัง/เภสัชทำอะไร"],
        [
            ["draft", "รับเข้าแล้วยังตรวจไม่จบ", "ส่งซ้ำได้", "รอ"],
            ["ready", "แมปครบ พร้อมโอนสต็อก", "ส่งซ้ำได้ (แทนที่บรรทัด)", "ตรวจแล้วกด Post"],
            ["error", "รหัสสินค้า/Lot/คลังผิด หรือ source=dest", "ส่งซ้ำหลังแก้ payload", "แก้แมป/ข้อมูลแล้วกด Validate"],
            ["posted", "โอนสต็อกแล้ว", "คีย์เดิมคืนชุดเดิม (HTTP 200)", "ดูใบโอน; ถ้าผิดใช้ reversal"],
            ["cancelled", "ยกเลิกก่อน Post", "ต้องใช้ external_id ใหม่", "ไม่ Post"],
        ],
        col_widths=[2.6, 5.0, 4.8, 4.6],
    )
    d.h2("เมนูในระบบ")
    d.bullets(
        [
            "สินค้าคงคลัง → HIS เบิกเติมคลัง — คิวชุดข้อมูลรอตรวจ/Post",
            "สินค้าคงคลัง → การตั้งค่า → HIS Service Units — แมป department_code → คลังปลายทาง",
            "สินค้าคงคลัง → HIS ตัดจ่ายสินค้า — คิวตัดจ่ายให้คนไข้ (คนละ endpoint)",
        ]
    )
    d.h2("Idempotency และ reversal")
    d.bullets(
        [
            "คีย์ = source_system + external_id ในบริษัทเดียวกัน",
            "ชุดยังไม่ posted: POST ซ้ำแทนที่บรรทัดแล้ว validate ใหม่ (action = updated)",
            "ชุด posted แล้ว: POST คีย์เดิมไม่สร้างซ้ำ (action = unchanged, HTTP 200)",
            "กลับรายการ: ส่งชุดใหม่ batch_type = reversal พร้อม original_external_id ผ่าน endpoint เดียวกัน",
        ]
    )
    d.code(
        '{\n'
        '  "external_id": "HIS-REQ-2026-08-26-OPD-1-REV",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-08-26",\n'
        '  "batch_type": "reversal",\n'
        '  "original_external_id": "HIS-REQ-2026-08-26-OPD-1"\n'
        "}"
    )

    d.h1("รหัสตอบกลับ HTTP")
    d.table(
        ["HTTP", "เมื่อไร", "ความหมายต่อ HIS"],
        [
            ["202", "สร้างหรืออัปเดตชุดที่ยังไม่ posted", "รับแล้ว อยู่คิว/รอ Post; อ่าน state และ errors"],
            ["200", "คีย์ซ้ำของชุดที่ posted แล้ว", "ไม่ทำซ้ำ คืนสถานะชุดเดิม"],
            ["400", "JSON ผิด ขาดฟิลด์ หรือค่าไม่อยู่ในโดเมน", "แก้ payload แล้วส่งใหม่"],
            ["401", "คีย์ผิดหรือไม่ส่ง", "ตรวจ header"],
            ["503", "API ถูกปิด หรือยังไม่ตั้งคีย์", "ติดต่อ IT"],
            ["500", "ข้อผิดพลาดภายใน", "แจ้ง IT หากซ้ำ"],
        ],
        col_widths=[2.2, 7.0, 7.8],
    )
    d.h2("ข้อผิดพลาดที่พบบ่อย")
    d.table(
        ["ข้อความโดยสังเขป", "สาเหตุและการแก้"],
        [
            ["source_warehouse_code is required", "ไม่พบคลังต้นทาง — ส่ง source_warehouse_code หรือตั้ง PHAR ใน ERP"],
            ["dest_warehouse_code or department_code is required", "ไม่พบคลังปลายทาง — ส่ง dest หรือแมปหน่วยบริการ"],
            ["Source and destination must differ", "คลังต้นทางและปลายทางต้องไม่เหมือนกัน"],
            ["Unknown product code", "รหัสสินค้าไม่มีใน ERP"],
            ["Unknown lot … for product …", "ชื่อ Lot ไม่ตรงหรือยังไม่มีใน ERP"],
            ["Stock requisition batch requires lines", "ต้องมีอย่างน้อยหนึ่งบรรทัดใน lines[]"],
            ["lines[].qty does not match sum of lots", "ยอดแม่ไม่เท่าผลรวม lots[]"],
            ["Qty total … does not match control", "control_totals.qty_total ไม่ตรง"],
            ["Send either lot_name or lots[], not both", "เลือกอย่างใดอย่างหนึ่ง"],
        ],
        col_widths=[8.0, 9.0],
    )

    d.h1("ข้อกำหนดตามสถานการณ์")
    d.h2("OPD ขอเบิกยาจากคลังยาหลักมาเติมห้องยาชั้น 1")
    d.bullets(
        [
            "source_warehouse_code = PHAR",
            "dest_warehouse_code = UNIT",
            "dest_location_code = ชื่อ shelf ห้องยาชั้น 1 ใน ERP",
            "department_code = OPD (ถ้ามีแมปใน HIS Service Units)",
            "ส่ง lines[] ตามรายการยาที่ต้องการเติม",
        ]
    )
    d.h2("เบิกหลายรายการยาในคำขอเดียว")
    d.p(
        "ส่งหลายบรรทัดใน lines[] โดยใช้ product_code และ qty ตามรายการที่ขอเบิก "
        "แนะนำส่ง control_totals.qty_total เพื่อกันยอดตกหล่น",
        align="justify",
    )
    d.h2("สินค้าติดตาม Lot — ไม่ระบุ Lot ตอนขอ")
    d.p(
        "หน่วยบริการอาจไม่ทราบ Lot ที่จะได้รับ — ส่งเฉพาะ product_code และ qty "
        "เมื่อเจ้าหน้าที่คลังกด Post ระบบเลือก Lot จากคลัง PHAR แบบ FEFO อัตโนมัติ",
        align="justify",
    )
    d.h2("สินค้าติดตาม Lot — ระบุ Lot ตอนขอ")
    d.p(
        "ถ้าหน่วยบริการต้องการ Lot เฉพาะ ส่ง lot_name หรือ lots[] "
        "Lot ต้องมีอยู่ใน ERP และมีสต็อกในคลังต้นทาง",
        align="justify",
    )

    d.h1("ตัวอย่าง Payload")
    d.h2("ตัวอย่าง A — OPD ขอเบิกยา 2 รายการจาก PHAR → UNIT")
    d.code(
        """
POST /vpk/api/v1/his/stock-requisitions

{
  "external_id": "HIS-REQ-2026-08-26-OPD-1",
  "source_system": "front_his",
  "business_date": "2026-08-26",
  "source_warehouse_code": "PHAR",
  "dest_warehouse_code": "UNIT",
  "dest_location_code": "shelf ห้องยาชั้น 1 (1182,1183,1184,1185,1186)",
  "department_code": "OPD",
  "lines": [
    {
      "line_external_id": "R1",
      "product_code": "00001",
      "item_type": "drug",
      "qty": 100
    },
    {
      "line_external_id": "R2",
      "product_code": "00012",
      "item_type": "drug",
      "qty": 50,
      "lot_name": "AMX-2508"
    }
  ],
  "control_totals": {
    "qty_total": 150
  }
}
""".strip()
    )
    d.p(
        "ผลหลัง Post: ใบโอน HISINT จาก PHAR/Stock ไป UNIT/ห้องยาชั้น 1 "
        "รายการ R1 ใช้ FEFO ถ้ายาติดตาม Lot รายการ R2 โอนตาม Lot AMX-2508"
    )

    d.h2("ตัวอย่าง B — ขอเบิกเวชภัณฑ์พร้อมหลาย Lot")
    d.code(
        """
{
  "external_id": "HIS-REQ-2026-08-26-SUP-1",
  "source_system": "front_his",
  "business_date": "2026-08-26",
  "source_warehouse_code": "SUPP",
  "dest_warehouse_code": "UNIT",
  "department_code": "OPD",
  "lines": [
    {
      "line_external_id": "R-GLOVE",
      "product_code": "201001",
      "item_type": "medical_supply",
      "qty": 200,
      "lots": [
        {"lot_name": "GLV-2508", "qty": 120},
        {"lot_name": "GLV-2507", "qty": 80}
      ]
    }
  ],
  "control_totals": {
    "qty_total": 200
  }
}
""".strip()
    )

    d.h2("ตัวอย่าง C — ใช้ department_code แทน dest_warehouse_code")
    d.code(
        """
{
  "external_id": "HIS-REQ-2026-08-26-DEPT-1",
  "source_system": "front_his",
  "business_date": "2026-08-26",
  "source_warehouse_code": "PHAR",
  "department_code": "OPD",
  "lines": [
    {
      "product_code": "00001",
      "item_type": "drug",
      "qty": 30
    }
  ]
}
""".strip()
    )
    d.p(
        "ถ้ามีแมป OPD → UNIT ใน HIS Service Units ระบบจะตั้ง dest_warehouse_code = UNIT อัตโนมัติ"
    )

    d.h1("การทดสอบร่วม (Test plan)")
    d.table(
        ["ลำดับ", "กรณี", "ผลที่คาด"],
        [
            ["1", "GET /health", "200, enabled และ api_key_configured"],
            ["2", "POST /stock-requisitions ไม่ส่งคีย์", "401"],
            ["3", "ส่ง lines ว่าง", "state=error"],
            ["4", "source = dest คลังเดียวกัน", "state=error"],
            ["5", "ส่งตัวอย่าง A สินค้า/คลังถูกต้อง", "202 ready จากนั้น Post ได้ใบโอน HISINT"],
            ["6", "สต็อกคลังต้นทางไม่พอ", "error ตอน Post"],
            ["7", "Lot ที่ส่งไม่มีใน ERP", "state=error"],
            ["8", "รหัสสินค้าไม่มี", "state=error ไม่สร้างสินค้าใหม่"],
            ["9", "POST คีย์เดิมหลัง Post", "200 unchanged ไม่โอนซ้ำ"],
            ["10", "control qty ไม่ตรง", "state=error"],
            ["11", "reversal ชุดที่ posted", "ชุดใหม่ ready เมื่อ Post กลับรายการต้นทาง"],
            ["12", "สินค้า tracked ไม่ส่ง Lot", "Post ได้ — ERP เลือก FEFO"],
        ],
        col_widths=[1.8, 7.0, 8.2],
    )

    d.h1("การเปิดบริการและจุดติดต่อ")
    d.bullets(
        [
            "ฝ่าย HIS ขอ API key และ URL จาก IT โรงพยาบาล",
            "ก่อนเปิดจริง ยืนยันรหัสคลัง PHAR/UNIT/WH และชื่อที่เก็บย่อยกับฝ่ายคลัง",
            "ตั้งแมปหน่วยบริการใน HIS Service Units สำหรับ department_code",
            "แยก workflow การเบิกเติม (เอกสารนี้) จากการตัดจ่ายคนไข้ (STK-001)",
            "ทบทวนร่วมกับเอกสารตัดจ่าย VPK-HIS-SPEC-STK-001 เพื่อไม่สับสน endpoint",
        ]
    )

    d.h1("ประวัติเอกสาร")
    d.table(
        ["เวอร์ชัน", "วันที่", "รายละเอียด"],
        [
            [
                "1.0 ร่าง",
                "26 ส.ค. 2569",
                "ร่างแรก: การเบิกเติมคลัง PHAR→UNIT, endpoint stock-requisitions, Lot/FEFO, idempotency และ reversal",
            ],
        ],
        col_widths=[3.5, 3.5, 10],
    )
    d.p(
        "เอกสารนี้เป็นร่างสำหรับทบทวน หากมีการเปลี่ยนแปลงรหัสคลัง กฎ Lot "
        "หรือ flow การคืนสินค้า ให้ปรับปรุงฉบับนี้ก่อนเปิดใช้งานจริง",
        align="justify",
    )

    d.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
