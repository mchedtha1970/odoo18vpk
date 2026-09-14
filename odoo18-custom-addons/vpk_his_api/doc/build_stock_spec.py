#!/usr/bin/env python3
# Copyright 2026 VPK
"""Generate HIS stock issue (dispense from service) specification as a Word document."""

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

OUT = Path(__file__).resolve().parent / "VPK-HIS-SPEC-STK-001-การตัดจ่ายยาจากการให้บริการ.docx"


class StockSpecDoc(SpecDoc):
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
            "โรงพยาบาลวชิระภูเก็ต  ·  HIS Stock Issue / Dispense Specification"
        )
        set_run_font(r, size=12, color=NAVY)
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("VPK-HIS-SPEC-STK-001  ·  ร่าง  ·  หน้า ")
        set_run_font(r, size=12, color=NAVY)
        _rev.add_page_number(fp)


def build():
    d = StockSpecDoc()

    d.p("โรงพยาบาลวชิระภูเก็ต", size=20, bold=True, align="center", space_after=4, color=NAVY)
    d.p("ระบบคลังและบัญชี ERP (Odoo 18)", size=16, align="center", space_after=18, color=TEAL)
    d.p(
        "ข้อกำหนดการรับข้อมูลตัดจ่ายยา/เวชภัณฑ์จากการให้บริการ",
        size=26,
        bold=True,
        align="center",
        space_after=4,
        color=NAVY,
    )
    d.p(
        "HIS Stock Issue (Service Dispense) Specification",
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
            ["รหัสเอกสาร", "VPK-HIS-SPEC-STK-001"],
            ["เวอร์ชัน", "1.0  (ร่าง)"],
            ["วันที่", "25 สิงหาคม 2569"],
            ["สถานะ", "Draft — สำหรับทบทวนร่วมกับฝ่าย HIS / เภสัชกรรม"],
            ["ระบบต้นทาง", "Hospital Information System (Front HIS / ห้องยาหน้า)"],
            ["ระบบปลายทาง", "Odoo 18 ERP  โรงพยาบาลวชิระภูเก็ต"],
            ["โมดูล", "vpk_his_api"],
            ["ขอบเขตฉบับนี้", "การตัดจ่ายยาและเวชภัณฑ์ที่เกิดจากการให้บริการ (patient dispense)"],
            ["เอกสารที่เกี่ยวข้อง", "VPK-HIS-SPEC-REV-001 การรับข้อมูลรายได้ (คนละ endpoint)"],
            ["ผู้ใช้เอกสาร", "ทีม HIS / เภสัชกรรมคลัง / IT"],
        ],
        col_widths=[5.5, 11.5],
    )

    d.h1("วัตถุประสงค์และขอบเขต")
    d.h2("วัตถุประสงค์")
    d.p(
        "เอกสารนี้กำหนดวิธีที่ระบบ HIS ส่งข้อมูลการตัดจ่ายยาและเวชภัณฑ์ที่เกิดจากการให้บริการ "
        "เข้าสู่ระบบคลังของโรงพยาบาล เพื่อให้ตัดสต็อกตามรหัสสินค้า Lot (ถ้ามี) และหน่วยบริการ/คลังที่จ่ายจริง "
        "โดยเก็บ HN และ VN เพื่อไล่รายการจ่ายยาตามคนไข้ในคิวตัดจ่าย "
        "แต่ไม่ส่งชื่อคนไข้หรือเลขประจำตัวประชาชนเข้า ERP",
        align="justify",
    )
    d.h2("อยู่ในขอบเขต")
    d.bullets(
        [
            "รับรายการตัดจ่ายจากการบริการผ่าน REST API POST /vpk/api/v1/his/stock-issues",
            "รองรับยา (drug) และเวชภัณฑ์ไม่ใช่ยา (medical_supply) ที่ตัดจากคลังบริการหน้า เช่น OPD / ห้องยาหน้า",
            "บังคับส่ง HN และ VN เมื่อเป็นการจ่ายให้คนไข้ (reason = patient_use)",
            "บังคับส่ง Lot เมื่อสินค้าใน ERP ติดตาม Lot หรือ Serial",
            "จัดคิวตรวจสอบใน HIS ตัดจ่ายสินค้า แล้วให้เภสัชกร/เจ้าหน้าที่คลังกด Post เพื่อตัดสต็อก",
            "ยกเลิกชุดที่ Post แล้วด้วย reversal batch",
        ]
    )
    d.h2("อยู่นอกขอบเขตฉบับนี้")
    d.bullets(
        [
            "การรับสรุปรายได้และสิทธิ์การรักษา — ใช้ VPK-HIS-SPEC-REV-001 / POST /revenue",
            "การโอนยาจากคลังกลางไปคลังหน่วยงาน (ทำในระบบคลัง ERP ตามกระบวนการเดิม)",
            "การสร้างรหัสสินค้าหรือ Lot ใหม่ใน ERP จาก HIS — ต้องมีรหัสอยู่ก่อน",
            "การส่งชื่อคนไข้ เลขประจำตัวประชาชน หรือข้อมูลส่วนบุคคลอื่นนอกจาก HN/VN",
            "การตัดจ่ายจากการเบิกหอผู้ป่วยแบบไม่ผูกคนไข้ (ward_use) — รองรับใน API แต่ไม่ใช่หัวข้อหลักของเอกสารนี้",
        ]
    )
    d.h2("หลักการออกแบบ")
    d.bullets(
        [
            "ตัดจ่ายตามการให้บริการ: แต่ละบรรทัดอ้างถึงคนไข้ด้วย HN + VN และรหัสสินค้าที่จ่ายจริง",
            "ส่งเป็นชุดรายวันหรือรายกะได้: หลายคนไข้ใน payload เดียว แต่ละบรรทัดต้องมี HN/VN ของตนเอง",
            "Staging ก่อนตัดสต็อก: draft → ready|error แล้วเจ้าหน้าที่ Post",
            "Idempotency: คีย์ซ้ำคือ source_system + external_id",
            "Lot ตาม ERP: สินค้าที่ tracking = lot/serial ต้องส่ง lot_name หรือ lots[]",
            "ไม่สร้างสินค้า/Lot ใหม่อัตโนมัติ: รหัสไม่รู้จักทำให้ชุดข้อมูลเข้า error",
        ]
    )

    d.h1("สถาปัตยกรรมและขั้นตอนงาน")
    d.h2("ภาพรวมการไหลของข้อมูล")
    d.bullets(
        [
            "HIS บันทึกการจ่ายยา/เวชภัณฑ์ที่หน้าบริการ (เช่น OPD) พร้อม HN VN รหัสยา Lot คลัง/ที่เก็บ",
            "ปิดกะหรือปิดวันแล้ว POST JSON ไปที่ /vpk/api/v1/his/stock-issues",
            "ERP ตรวจรหัสสินค้า คลัง Lot และ HN/VN แล้วสร้างชุดข้อมูลในคิว HIS ตัดจ่ายสินค้า",
            "ถ้าแมปครบ ชุดอยู่ในสถานะ Ready — เภสัชกร/คลังเปิดตรวจแล้วกด Post",
            "ระบบสร้างใบโอนตัดจ่าย (picking ประเภท HISOUT) จากคลังต้นทางไปยังตำแหน่ง HIS Consumption",
            "ถ้าเป็นยาหมดอายุ (reason = expired) จะสร้างเอกสาร Scrap แทนใบโอนปกติ",
        ],
        numbered=True,
    )
    d.h2("บทบาทระบบ")
    d.table(
        ["ระบบ", "หน้าที่"],
        [
            ["HIS / ห้องยาหน้า", "บันทึกการจ่ายตามคนไข้ ส่งรหัสสินค้า Lot คลัง HN VN ไม่ส่งชื่อ/CID"],
            ["REST API (vpk_his_api)", "รับ JSON, เก็บ HN/VN, ตัด PII อื่น, จัดคิว, ตอบสถานะชุดข้อมูล"],
            ["เภสัชกร / เจ้าหน้าที่คลัง", "ตรวจคิว HIS ตัดจ่ายสินค้า, กด Post, ติดตามสต็อกคงเหลือ"],
            ["Odoo Inventory", "ใบโอน HISOUT, Lot, คลัง UNIT/PHAR และที่เก็บย่อย (เช่น ห้องยาชั้น 1)"],
        ],
        col_widths=[5, 12],
    )
    d.h2("ความสัมพันธ์กับเอกสารรายได้")
    d.p(
        "การตัดสต็อกและการลงรายได้เป็นคนละชุดข้อมูล คนละ endpoint "
        "ยอดขายยาในรายได้อาจสรุปรวมตามสิทธิ์โดยไม่ระบุ HN "
        "ขณะที่การตัดสต็อกต้องระบุ HN/VN เพื่อยืนยันว่าตัดของจากการจ่ายให้คนไข้รายนั้น",
        align="justify",
    )

    d.h1("การเชื่อมต่อและการยืนยันตัวตน")
    d.h2("โปรโตคอล")
    d.table(
        ["รายการ", "ค่า"],
        [
            ["โปรโตคอล", "HTTPS, JSON (application/json; charset=utf-8)"],
            ["เวอร์ชัน API", "v1"],
            ["Base path", "/vpk/api/v1/his"],
            ["Endpoint หลัก", "POST /vpk/api/v1/his/stock-issues"],
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

    d.h1("รายการ API ที่เกี่ยวข้องกับการตัดจ่าย")
    d.table(
        ["Method", "Path", "Auth", "หน้าที่"],
        [
            ["GET", "/vpk/api/v1/his/health", "ไม่ต้อง", "ตรวจว่าบริการทำงานและมีการตั้งคีย์"],
            ["POST", "/vpk/api/v1/his/stock-issues", "ต้อง", "ส่งชุดตัดจ่าย / reversal ตัดจ่าย"],
            ["GET", "/vpk/api/v1/his/batches/{external_id}", "ต้อง", "สอบถามสถานะชุด (query source_system)"],
            ["GET", "/vpk/api/v1/his/lookups/warehouses", "ต้อง", "รายการคลังและแมปหน่วยบริการ"],
            ["GET", "/vpk/api/v1/his/lookups/products", "ต้อง", "สอบถามรหัสสินค้าและว่าต้องส่ง Lot หรือไม่"],
        ],
        col_widths=[2.2, 7.5, 2.0, 5.3],
    )

    d.h1("สัญญาข้อมูล POST /stock-issues")
    d.h2("ฟิลด์ระดับชุดข้อมูล (batch)")
    d.table(
        ["ฟิลด์", "ชนิด", "จำเป็น", "คำอธิบาย"],
        [
            ["external_id", "string", "ใช่", "รหัสชุดข้อมูลฝั่ง HIS ต้องไม่ซ้ำใน source_system เดียวกัน"],
            ["source_system", "string", "ใช่", "รหัสระบบต้นทาง เช่น front_his"],
            ["business_date", "date", "ใช่", "วันที่ทางธุรกิจ YYYY-MM-DD"],
            ["shift", "string", "ไม่", "รหัสกะ เช่น 1, 2, night"],
            ["batch_type", "string", "ไม่", "stock_issue (ค่าเริ่มต้นของ endpoint นี้) หรือ reversal"],
            ["original_external_id", "string", "เมื่อยกเลิก", "external_id ของชุดที่ Post แล้ว"],
            ["issues", "array", "ใช่*", "บรรทัดตัดจ่าย (*หรือใช้ชื่อฟิลด์ items แทนได้)"],
            ["control_totals.qty_total", "number", "แนะนำ", "ยอดคุมจำนวนรวม ถ้าส่งมาต้องเท่าผลรวม qty"],
        ],
        col_widths=[5.2, 2.2, 2.2, 7.4],
    )
    d.h2("บรรทัดตัดจ่าย (issues[] / items[])")
    d.table(
        ["ฟิลด์", "ชนิด", "จำเป็น", "คำอธิบาย"],
        [
            ["line_external_id", "string", "แนะนำ", "รหัสบรรทัดฝั่ง HIS"],
            ["hn", "string", "ใช่*", "HN คนไข้ (*จำเป็นเมื่อ reason = patient_use)"],
            ["vn", "string", "ใช่*", "VN การมารับบริการ (*จำเป็นเมื่อ reason = patient_use)"],
            ["product_code", "string", "ใช่", "รหัสสินค้า ERP (default_code) ยาตัวเลข pad เป็น 5 หลัก"],
            ["item_type", "string", "ไม่", "drug | medical_supply | other"],
            ["warehouse_code", "string", "ใช่*", "รหัสคลัง Odoo เช่น UNIT, PHAR (*หรือใช้แมป department_code)"],
            ["location_code", "string", "ไม่", "ชื่อหรือ barcode ที่เก็บย่อยภายใต้คลัง เช่น ห้องยาชั้น 1"],
            ["department_code", "string", "ไม่", "รหัสหน่วยบริการ HIS เช่น OPD หากมีแมปใน ERP"],
            ["qty", "number", "ใช่", "จำนวนที่จ่าย ห้ามเป็นศูนย์ (ถ้ามี lots[] ต้องเท่าผลรวม lot)"],
            ["uom", "string", "ไม่", "หน่วยนับ HIS ต้องเข้ากับหมวดหน่วยของสินค้า"],
            ["lot_name", "string", "ตามสินค้า", "Lot เดียว; ห้ามส่งคู่กับ lots[]"],
            ["lots", "array", "ตามสินค้า", "หลาย Lot ในรายการเดียวกัน แต่ละองค์ประกอบมี lot_name และ qty"],
            ["reason", "string", "ไม่", "ค่าเริ่มต้น patient_use"],
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
        "เมื่อขยาย lots[] ระบบคัดลอก hn, vn, product_code, warehouse_code และฟิลด์อื่นของบรรทัดแม่ไปทุก Lot"
    )
    d.h2("ข้อมูลส่วนบุคคลที่อนุญาตและที่ห้าม")
    d.table(
        ["ฟิลด์", "ตัดจ่ายสต็อก", "รายได้ (revenue)"],
        [
            ["hn, vn", "เก็บได้ และจำเป็นเมื่อจ่ายให้คนไข้", "ตัดทิ้ง ห้ามเก็บ"],
            ["patient_name, cid, national_id, firstname, lastname", "ตัดทิ้ง", "ตัดทิ้ง"],
            ["an, dob, birthdate", "ตัดทิ้ง", "ตัดทิ้ง"],
        ],
        col_widths=[7, 5, 5],
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
    d.h2("เหตุผลการตัด (reason)")
    d.table(
        ["รหัส", "ความหมาย", "HN/VN", "เอกสารเมื่อ Post"],
        [
            ["patient_use", "จ่ายจากการให้บริการ (ค่าเริ่มต้น)", "จำเป็น", "ใบโอน HISOUT → HIS Consumption"],
            ["ward_use", "ใช้ที่หอ/หน่วยงาน (ไม่ผูกคนไข้)", "ไม่บังคับ", "ใบโอน HISOUT"],
            ["expired", "ยาหมดอายุ / ของเสีย", "ไม่บังคับ", "Scrap"],
            ["adjust", "ปรับยอด", "ไม่บังคับ", "ใบโอน HISOUT"],
        ],
        col_widths=[3.2, 5.5, 3.0, 5.3],
    )
    d.h2("คลังที่เกี่ยวข้องกับการจ่ายหน้าบริการ")
    d.table(
        ["รหัสคลัง", "ชื่อโดยสังเขป", "การใช้กับเอกสารนี้"],
        [
            ["UNIT", "คลังยาหน่วยงาน", "คลังบริการหน้า เช่น OPD / ห้องยาชั้น 1 (แนะนำสำหรับ front)"],
            ["PHAR", "คลังยา", "คลังยาหลัก หากจ่ายตรงจากคลังยา"],
            ["SUPP", "คลังเวชภัณฑ์มิใช่ยา", "เมื่อตัดเวชภัณฑ์ไม่ใช่ยาจากคลังนี้"],
        ],
        col_widths=[3.2, 5.0, 8.8],
    )
    d.note(
        "ที่เก็บย่อยระบุด้วย location_code เป็นชื่อตำแหน่งใน ERP "
        "เช่น \"shelf ห้องยาชั้น 1 (1182,1183,1184,1185,1186)\" หรือ barcode ของตำแหน่งนั้น"
    )

    d.h1("กฎการตัดสต็อกเมื่อ Post")
    d.bullets(
        [
            "จัดกลุ่มใบโอนตามคลัง + ที่เก็บต้นทาง ในชุดข้อมูลเดียวกัน",
            "สร้าง picking ประเภท HISOUT จากที่เก็บต้นทางไปยังตำแหน่งเสมือน HIS Consumption",
            "สินค้าที่ส่ง Lot จะตัดตาม Lot ที่ระบุ สินค้าไม่ติดตาม Lot ตัดตามจำนวน",
            "ห้ามสร้างรหัสสินค้าหรือ Lot ใหม่ขณะ Post — ต้องผ่าน Validate เป็น ready ก่อน",
            "หลัง Post สำเร็จ สต็อกที่คลังต้นทางลดลงตามจำนวนที่ส่ง",
        ]
    )
    d.h2("กฎ Lot")
    d.bullets(
        [
            "สอบถามได้ที่ GET /lookups/products?codes=00001 — ฟิลด์ lot_required",
            "lot_required = true ต้องมี lot_name หรือ lots[]",
            "Lot ต้องมีอยู่แล้วใน ERP และผูกกับสินค้ารหัสนั้น",
            "สินค้า serial ต้องส่งทีละ 1 ต่อหมายเลข serial (qty = 1)",
        ]
    )

    d.h1("สถานะชุดข้อมูลและการทำงานของเจ้าหน้าที่")
    d.table(
        ["state", "ความหมาย", "HIS ทำอะไรได้", "คลัง/เภสัชทำอะไร"],
        [
            ["draft", "รับเข้าแล้วยังตรวจไม่จบ", "ส่งซ้ำได้", "รอ"],
            ["ready", "แมปครบ พร้อมตัดสต็อก", "ส่งซ้ำได้ (แทนที่บรรทัด)", "ตรวจแล้วกด Post"],
            ["error", "รหัสสินค้า/Lot/คลังผิด หรือขาด HN/VN", "ส่งซ้ำหลังแก้ payload", "แก้แมป/ข้อมูลแล้วกด Validate"],
            ["posted", "ตัดสต็อกแล้ว", "คีย์เดิมคืนชุดเดิม (HTTP 200)", "ดูใบโอน; ถ้าผิดใช้ reversal"],
            ["cancelled", "ยกเลิกก่อน Post", "ต้องใช้ external_id ใหม่", "ไม่ Post"],
        ],
        col_widths=[2.6, 5.0, 4.8, 4.6],
    )
    d.h2("เมนูในระบบ")
    d.bullets(
        [
            "สินค้าคงคลัง → HIS ตัดจ่ายสินค้า — คิวชุดข้อมูลรอตรวจ/Post",
            "สินค้าคงคลัง → การตั้งค่า → HIS Service Units — แมป department_code → คลัง",
            "ค้นหา HN/VN ได้จากช่องค้นหาของคิวตัดจ่าย",
        ]
    )
    d.h2("Idempotency และ reversal")
    d.bullets(
        [
            "คีย์ = source_system + external_id ในบริษัทเดียวกัน",
            "ชุดยังไม่ posted: POST ซ้ำแทนที่บรรทัดแล้ว validate ใหม่ (action = updated)",
            "ชุด posted แล้ว: POST คีย์เดิมไม่สร้างซ้ำ (action = unchanged, HTTP 200)",
            "กลับรายการ: ส่งชุดใหม่ batch_type = reversal พร้อม original_external_id",
        ]
    )
    d.code(
        '{\n'
        '  "external_id": "HIS-STK-2026-08-25-OPD-1-REV",\n'
        '  "source_system": "front_his",\n'
        '  "business_date": "2026-08-25",\n'
        '  "batch_type": "reversal",\n'
        '  "original_external_id": "HIS-STK-2026-08-25-OPD-1"\n'
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
            ["hn is required for patient dispensing", "จ่ายคนไข้ต้องส่ง hn"],
            ["vn is required for patient dispensing", "จ่ายคนไข้ต้องส่ง vn"],
            ["Unknown product code", "รหัสสินค้าไม่มีใน ERP"],
            ["Product … is lot-tracked; send lot_name or lots[]", "สินค้าติดตาม Lot ต้องส่ง Lot"],
            ["Unknown lot … for product …", "ชื่อ Lot ไม่ตรงหรือยังไม่มีใน ERP"],
            ["Unknown warehouse code", "รหัสคลังไม่ตรง เช่น ต้องเป็น UNIT ไม่ใช่ชื่อไทย"],
            ["warehouse_code or mapped department_code is required", "ต้องระบุคลังหรือแมปหน่วยบริการ"],
            ["issues[].qty does not match sum of lots", "ยอดแม่ไม่เท่าผลรวม lots[]"],
            ["Qty total … does not match control", "control_totals.qty_total ไม่ตรง"],
            ["Send either lot_name or lots[], not both", "เลือกอย่างใดอย่างหนึ่ง"],
        ],
        col_widths=[8.0, 9.0],
    )

    d.h1("ข้อกำหนดตามสถานการณ์")
    d.h2("จ่ายยาที่คลังบริการหน้า OPD ให้คนไข้หนึ่งราย")
    d.bullets(
        [
            "ระบุ hn, vn ของคนไข้รายนั้น",
            "warehouse_code = UNIT (หรือคลังที่จ่ายจริง) และ location_code ของห้องยา/ชั้นที่ตัด",
            "item_type = drug, reason = patient_use",
            "ถ้ายาติดตาม Lot ส่ง lot_name หรือ lots[] ตามที่จ่ายจริง",
        ]
    )
    d.h2("คนไข้หนึ่งรายได้หลายรายการยา/เวชภัณฑ์")
    d.p(
        "ส่งหลายบรรทัดใน issues[] โดยใช้ hn และ vn ชุดเดียวกัน แยก product_code และ Lot ตามรายการที่จ่าย",
        align="justify",
    )
    d.h2("สินค้าเดียวกันหลาย Lot ในครั้งเดียว")
    d.p(
        "ใส่ lots[] ในบรรทัดนั้น ผลรวม qty ของ lots ต้องเท่า qty ของบรรทัด "
        "ระบบจะแตกเป็นหลายบรรทัดในคิว ERP โดยยังคง HN/VN เดิม",
        align="justify",
    )
    d.h2("ปิดยอดรายวันหลายคนไข้")
    d.bullets(
        [
            "รวมหลายคนไข้ในชุดข้อมูลเดียวของวัน/กะนั้นได้",
            "แนะนำ external_id มีวันที่และกะ เช่น HIS-STK-2026-08-25-OPD-SHIFT1",
            "ส่ง control_totals.qty_total เสมอเพื่อกันยอดตกหล่น",
        ]
    )

    d.h1("ตัวอย่าง Payload")
    d.h2("ตัวอย่าง A — OPD จ่ายยาคนไข้หนึ่งราย สองรายการ")
    d.code(
        """
POST /vpk/api/v1/his/stock-issues

{
  "external_id": "HIS-STK-2026-08-25-OPD-1",
  "source_system": "front_his",
  "business_date": "2026-08-25",
  "shift": "1",
  "issues": [
    {
      "line_external_id": "OPD-6500123-ANT",
      "hn": "6500123",
      "vn": "6808250101",
      "product_code": "00001",
      "item_type": "drug",
      "warehouse_code": "UNIT",
      "location_code": "shelf ห้องยาชั้น 1 (1182,1183,1184,1185,1186)",
      "department_code": "OPD",
      "qty": 8,
      "reason": "patient_use",
      "lots": [
        {"lot_name": "OPD-ANT-2508", "qty": 5},
        {"lot_name": "OPD-ANT-2507", "qty": 3}
      ]
    },
    {
      "line_external_id": "OPD-6500123-OME",
      "hn": "6500123",
      "vn": "6808250101",
      "product_code": "00012",
      "item_type": "drug",
      "warehouse_code": "UNIT",
      "location_code": "shelf ห้องยาชั้น 1 (1182,1183,1184,1185,1186)",
      "department_code": "OPD",
      "qty": 14,
      "lot_name": "OPD-OME-2508",
      "reason": "patient_use"
    }
  ],
  "control_totals": {
    "qty_total": 22
  }
}
""".strip()
    )
    d.p(
        "ผลหลัง Post: ใบโอน HISOUT จาก UNIT/ห้องยาชั้น 1 ไป HIS Consumption "
        "ตัด Lot ตามที่ระบุ คิวเก็บ HN/VN สำหรับไล่รายการ"
    )

    d.h2("ตัวอย่าง B — ปิดกะ OPD สองคนไข้")
    d.code(
        """
{
  "external_id": "HIS-STK-2026-08-25-OPD-SHIFT1",
  "source_system": "front_his",
  "business_date": "2026-08-25",
  "shift": "1",
  "issues": [
    {
      "line_external_id": "P1-DRUG",
      "hn": "6500123",
      "vn": "6808250101",
      "product_code": "00001",
      "item_type": "drug",
      "warehouse_code": "UNIT",
      "qty": 4,
      "lot_name": "OPD-ANT-2508",
      "reason": "patient_use"
    },
    {
      "line_external_id": "P2-DRUG",
      "hn": "6700888",
      "vn": "6808250102",
      "product_code": "00001",
      "item_type": "drug",
      "warehouse_code": "UNIT",
      "qty": 4,
      "lot_name": "OPD-ANT-2508",
      "reason": "patient_use"
    },
    {
      "line_external_id": "P2-SUP",
      "hn": "6700888",
      "vn": "6808250102",
      "product_code": "20100001",
      "item_type": "medical_supply",
      "warehouse_code": "UNIT",
      "qty": 1,
      "lot_name": "SUP-2025-01",
      "reason": "patient_use"
    }
  ],
  "control_totals": {
    "qty_total": 9
  }
}
""".strip()
    )

    d.h2("ตัวอย่าง C — สอบถามสินค้าต้องส่ง Lot หรือไม่")
    d.code(
        "GET /vpk/api/v1/his/lookups/products?codes=00001,00012,20100001\n\n"
        "Response (ย่อ):\n"
        "{\n"
        '  "ok": true,\n'
        '  "products": [\n'
        '    {"code": "00001", "name": "…", "tracking": "lot", "lot_required": true},\n'
        '    {"code": "00012", "name": "…", "tracking": "lot", "lot_required": true}\n'
        "  ]\n"
        "}"
    )

    d.h1("การทดสอบร่วม (Test plan)")
    d.table(
        ["ลำดับ", "กรณี", "ผลที่คาด"],
        [
            ["1", "GET /health", "200, enabled และ api_key_configured"],
            ["2", "POST /stock-issues ไม่ส่งคีย์", "401"],
            ["3", "ขาด hn หรือ vn เมื่อ patient_use", "state=error"],
            ["4", "ส่งตัวอย่าง A สินค้า/Lot/คลังถูกต้อง", "202 ready จากนั้น Post ได้ใบโอน"],
            ["5", "สินค้าติดตาม Lot แต่ไม่ส่ง Lot", "state=error"],
            ["6", "Lot ไม่มีใน ERP", "state=error"],
            ["7", "รหัสสินค้าไม่มี", "state=error ไม่สร้างสินค้าใหม่"],
            ["8", "ส่งชื่อคนไข้ใน payload", "รับได้แต่ตัดชื่อทิ้ง เก็บเฉพาะ HN/VN"],
            ["9", "POST คีย์เดิมหลัง Post", "200 unchanged ไม่ตัดซ้ำ"],
            ["10", "control qty ไม่ตรง", "state=error"],
            ["11", "reversal ชุดที่ posted", "ชุดใหม่ ready เมื่อ Post กลับรายการต้นทาง"],
        ],
        col_widths=[1.8, 7.0, 8.2],
    )

    d.h1("การเปิดบริการและจุดติดต่อ")
    d.bullets(
        [
            "ฝ่าย HIS ขอ API key และ URL จาก IT โรงพยาบาล",
            "ก่อนเปิดจริง ยืนยันรหัสคลัง UNIT/PHAR และชื่อที่เก็บย่อยกับฝ่ายคลัง",
            "สอบถาม lot_required ผ่าน lookups/products ก่อนปิดยอดวันแรก",
            "เมื่อมีหน่วยบริการใหม่ ให้เภสัช/คลังเพิ่มแมปใน HIS Service Units",
            "ทบทวนร่วมกับเอกสารรายได้ VPK-HIS-SPEC-REV-001 เพื่อไม่สับสนเรื่อง PII",
        ]
    )

    d.h1("ประวัติเอกสาร")
    d.table(
        ["เวอร์ชัน", "วันที่", "รายละเอียด"],
        [
            [
                "1.0 ร่าง",
                "25 ส.ค. 2569",
                "ร่างแรก: ตัดจ่ายยา/เวชภัณฑ์จากการให้บริการ, HN/VN, Lot, คลังบริการหน้า OPD, idempotency และ reversal",
            ],
        ],
        col_widths=[3.5, 3.5, 10],
    )
    d.p(
        "เอกสารนี้เป็นร่างสำหรับทบทวน หากมีการเปลี่ยนแปลงรหัสคลัง กฎ Lot หรือข้อกำหนด HN/VN "
        "ให้ปรับปรุงฉบับนี้ก่อนเปิดใช้งานจริง",
        align="justify",
    )

    d.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
