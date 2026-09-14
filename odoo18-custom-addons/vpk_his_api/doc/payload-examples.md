# HIS Interface — payload examples

Auth header (required except `/health`):

```
X-Api-Key: <key>
```

or `Authorization: Bearer <key>`

## Health

`GET /vpk/api/v1/his/health`

## Revenue (daily close)

`POST /vpk/api/v1/his/revenue`

```json
{
  "external_id": "HIS-REV-2026-08-22",
  "source_system": "front_his",
  "business_date": "2026-08-22",
  "shift": "1",
  "currency": "THB",
  "sales": [
    {
      "line_external_id": "S1",
      "entitlement_code": "SELF_PAY",
      "service_type": "op",
      "item_type": "service",
      "department_code": "OPD",
      "qty": 1,
      "amount_total": 150000.00
    },
    {
      "line_external_id": "S2",
      "entitlement_code": "UC",
      "service_type": "op",
      "item_type": "drug",
      "amount_total": 82000.00
    }
  ],
  "payments": [
    {
      "line_external_id": "P1",
      "payment_method_code": "cash",
      "entitlement_code": "SELF_PAY",
      "amount": 150000.00
    },
    {
      "line_external_id": "P2",
      "payment_method_code": "ar_claim",
      "entitlement_code": "UC",
      "amount": 82000.00
    }
  ],
  "control_totals": {
    "sales_total": 232000.00,
    "payments_total": 232000.00
  }
}
```

Entitlement codes: `SELF_PAY`, `UC`, `SSO`, `CSMBS`  
Service type: `op` | `ip`  
Item type: `service` | `drug` | `medical_supply` | `lab` | `other`  
Payment method (POS tenders):

- เงินจริงที่เคาน์เตอร์: `cash` | `transfer` | `credit_card` → ลงใบรับเงิน ใบแจ้งหนี้ปิด
- เงินล่วงหน้า: `advance_in` รับมัดจำ (เดบิตเงินสด / เครดิตหนี้สินรับล่วงหน้า, ไม่ลงรายได้) · `advance` (หรือ `prepaid`) ตัดมัดจำเมื่อมาใช้บริการ (ไม่นับเป็นเงินสดวันนี้) ถ้าไม่พอให้ส่ง `cash`/`transfer`/`credit_card` ส่วนต่าง
- ประเภทสิทธิ์ (พักลูกหนี้): `sso` | `uc` | `csmbs` | `ar_claim` → **ไม่ลงเงิน** ตั้งลูกหนี้สิทธิ์ แสดงใน aging จนกองทุนโอนมาเคลียร์

คนไข้ใช้ได้หลายสิทธิ์ในใบเดียว ให้ใส่ `ticket_external_id` ชุดเดียวกันทุกบรรทัดของใบนั้น (ไม่ต้องส่ง HN)

## POS-style visit (หลายสิทธิ์ในใบเดียว)

`POST /vpk/api/v1/his/revenue`

```json
{
  "external_id": "HIS-REV-2026-08-23-SHIFT1",
  "source_system": "front_his",
  "business_date": "2026-08-23",
  "shift": "1",
  "currency": "THB",
  "sales": [
    {
      "line_external_id": "T1-CASH",
      "ticket_external_id": "POS-OPD-0001",
      "entitlement_code": "SELF_PAY",
      "service_type": "op",
      "item_type": "service",
      "department_code": "OPD",
      "amount_total": 50.00
    },
    {
      "line_external_id": "T1-SSO",
      "ticket_external_id": "POS-OPD-0001",
      "entitlement_code": "SSO",
      "service_type": "op",
      "item_type": "drug",
      "department_code": "OPD",
      "amount_total": 200.00
    },
    {
      "line_external_id": "T1-UC",
      "ticket_external_id": "POS-OPD-0001",
      "entitlement_code": "UC",
      "service_type": "op",
      "item_type": "lab",
      "department_code": "OPD",
      "amount_total": 80.00
    }
  ],
  "payments": [
    {
      "line_external_id": "T1-PAY-CASH",
      "ticket_external_id": "POS-OPD-0001",
      "payment_method_code": "cash",
      "entitlement_code": "SELF_PAY",
      "amount": 50.00
    },
    {
      "line_external_id": "T1-PAY-SSO",
      "ticket_external_id": "POS-OPD-0001",
      "payment_method_code": "sso",
      "amount": 200.00
    },
    {
      "line_external_id": "T1-PAY-UC",
      "ticket_external_id": "POS-OPD-0001",
      "payment_method_code": "uc",
      "amount": 80.00
    }
  ],
  "control_totals": {
    "sales_total": 330.00,
    "payments_total": 330.00
  }
}
```

ผลลงบัญชีของใบนี้:

| ประเภทรับชำระ | เอกสาร | Aging |
|---|---|---|
| เงินสด 50 | ใบแจ้งหนี้ชำระเอง + ใบรับเงิน | ไม่ค้าง |
| สิทธิ์ SSO 200 | ใบแจ้งหนี้คู่ค้าประกันสังคม ค้างรับ | ขึ้นลูกหนี้สิทธิ์ / Aged Receivable |
| สิทธิ์ UC 80 | ใบแจ้งหนี้คู่ค้า UC ค้างรับ | ขึ้นลูกหนี้สิทธิ์ / Aged Receivable |

เมื่อกองทุนโอนเข้าบัญชี: เปิดใบแจ้งหนี้สิทธิ์นั้น → ลงทะเบียนการชำระเงินที่สมุด **Bank** → ลูกหนี้สิทธิ์เคลียร์ หลุดจาก aging

## IPD (ผู้ป่วยใน) — จ่ายตามสิทธิ์ + จ่ายบางส่วน

คนไข้ IPD ส่ง `service_type`: `"ip"` ทั้งบรรทัดขายและถ้ามีให้ใส่ที่รับเงินด้วย  
ยอดสิทธิ์พักลูกหนี้กองทุน ยอดคนไข้ที่จ่ายไม่ครบพักที่ **ชำระเงินเอง IP** และขึ้นในเมนู **ลูกหนี้คงค้าง** (กรองได้เป็น สิทธิ์ / คนไข้ IPD)

`POST /vpk/api/v1/his/revenue`

```json
{
  "external_id": "HIS-REV-2026-08-23-IPD-1",
  "source_system": "front_his",
  "business_date": "2026-08-23",
  "shift": "1",
  "currency": "THB",
  "sales": [
    {
      "line_external_id": "IPD-SELF",
      "ticket_external_id": "POS-IPD-0001",
      "entitlement_code": "SELF_PAY",
      "service_type": "ip",
      "item_type": "service",
      "department_code": "IPD",
      "amount_total": 15000.00
    },
    {
      "line_external_id": "IPD-SSO",
      "ticket_external_id": "POS-IPD-0001",
      "entitlement_code": "SSO",
      "service_type": "ip",
      "item_type": "drug",
      "department_code": "IPD",
      "amount_total": 80000.00
    }
  ],
  "payments": [
    {
      "line_external_id": "IPD-PAY-CASH",
      "ticket_external_id": "POS-IPD-0001",
      "payment_method_code": "cash",
      "amount": 5000.00
    },
    {
      "line_external_id": "IPD-PAY-SSO",
      "ticket_external_id": "POS-IPD-0001",
      "payment_method_code": "sso",
      "amount": 80000.00
    },
    {
      "line_external_id": "IPD-PAY-AR",
      "ticket_external_id": "POS-IPD-0001",
      "payment_method_code": "ar_claim",
      "entitlement_code": "SELF_PAY",
      "amount": 10000.00
    }
  ],
  "control_totals": {
    "sales_total": 95000.00,
    "payments_total": 95000.00
  }
}
```

ผลลงบัญชีของใบ IPD นี้:

| ประเภท | เอกสาร | ลูกหนี้คงค้าง |
|---|---|---|
| เงินสด 5,000 จากส่วนคนไข้ 15,000 | ใบแจ้งหนี้ชำระเอง IP + ใบรับเงิน | คงเหลือคนไข้ 10,000 |
| สิทธิ์ SSO 80,000 | ใบแจ้งหนี้คู่ค้าประกันสังคม IP | ค้างรับกองทุน 80,000 |
| `ar_claim` คนไข้ 10,000 | ไม่ลงเงิน | เป็นยอดค้างในใบชำระเอง IP |

`control_totals.payments_total` รวมเงินจริง + ยอดสิทธิ์ + ยอดค้างคนไข้ (`ar_claim`) ให้เท่ากับยอดขาย

## เงินล่วงหน้า — รับมัดจำแล้วตัดเมื่อมาใช้บริการ (จ่ายเพิ่มถ้าไม่พอ)

รับมัดจำก่อนวันมารักษา ส่งเฉพาะ `payments` ด้วย `advance_in` (ไม่ส่ง sales ไม่ลงรายได้)

เมื่อมาใช้บริการ ส่งยอดขายส่วนคนไข้ตามจริง แล้วตัดด้วย `advance` เท่าที่ใช้จากมัดจำ ถ้ามัดจำไม่พอให้ส่ง `cash` / `transfer` / `credit_card` ส่วนต่าง

`POST /vpk/api/v1/his/revenue` — วันรับมัดจำ

```json
{
  "external_id": "HIS-ADV-2026-08-20",
  "source_system": "front_his",
  "business_date": "2026-08-20",
  "shift": "1",
  "currency": "THB",
  "payments": [
    {
      "line_external_id": "DEP-1",
      "ticket_external_id": "DEP-0001",
      "payment_method_code": "advance_in",
      "amount": 10000.00
    }
  ],
  "control_totals": {
    "payments_total": 10000.00
  }
}
```

`POST /vpk/api/v1/his/revenue` — วันมารักษา ยอด 15,000 ตัดมัดจำ 10,000 จ่ายสดเพิ่ม 5,000

```json
{
  "external_id": "HIS-REV-2026-08-25-ADV-1",
  "source_system": "front_his",
  "business_date": "2026-08-25",
  "shift": "1",
  "currency": "THB",
  "sales": [
    {
      "line_external_id": "ADV-SELF",
      "ticket_external_id": "POS-OPD-ADV-1",
      "entitlement_code": "SELF_PAY",
      "service_type": "op",
      "item_type": "service",
      "department_code": "OPD",
      "amount_total": 15000.00
    }
  ],
  "payments": [
    {
      "line_external_id": "ADV-APPLY",
      "ticket_external_id": "POS-OPD-ADV-1",
      "payment_method_code": "advance",
      "amount": 10000.00
    },
    {
      "line_external_id": "ADV-CASH",
      "ticket_external_id": "POS-OPD-ADV-1",
      "payment_method_code": "cash",
      "amount": 5000.00
    }
  ],
  "control_totals": {
    "sales_total": 15000.00,
    "payments_total": 15000.00
  }
}
```

ผลลงบัญชี:

| ประเภท | เอกสาร | หมายเหตุ |
|---|---|---|
| `advance_in` 10,000 (วันรับมัดจำ) | เดบิตเงินสด / เครดิต 2103010103.101 | นับเป็นเงินสดในใบนำส่งเงินวันนั้น ไม่ลงรายได้ |
| `advance` 10,000 (วันมารักษา) | ใบแจ้งหนี้ชำระเอง + ใบรับเงินสมุด HADV | ไม่นับเงินสดวันนี้ ลดหนี้สินรับล่วงหน้า |
| เงินสดเพิ่ม 5,000 | ใบรับเงินสมุด HCSH | นับเงินสดวันนี้ |
| รวมใบแจ้งหนี้ 15,000 | ปิดครบ | ไม่ค้างลูกหนี้ |

ถ้ามัดจำพอทั้งใบ ส่งแค่ `advance` เท่ากับยอดขาย ไม่ต้องมี cash  
รหัสสำรองของ `advance`: `prepaid` / `deposit`

Idempotency key = `source_system` + `external_id`. Repeat while the batch is not posted replaces lines. After post, the same key returns the posted batch (HTTP 200).

To correct a posted batch, send a new `external_id` with `"batch_type": "reversal"` and `"original_external_id": "<posted id>"`.

## ตัดจ่ายสินค้า (จ่ายยา/เวชภัณฑ์ตาม VN/HN)

`POST /vpk/api/v1/his/stock-issues`

ส่งรายการตัดจ่ายที่เกิดจากบริการ **รายครั้งต่อคนไข้** โดยต้องมี `hn` และ `vn`  
ถ้าสินค้าติดตาม Lot ใน ERP ต้องส่ง Lot มาด้วย — แยกบรรทัดตาม Lot หรือใส่ `lots[]` ในรายการนั้น  
ยังส่งรวมเป็นชุดรายวัน (หลายคนไข้ใน payload เดียว) ได้ แต่ละบรรทัดต้องระบุคนไข้

```json
{
  "external_id": "HIS-STK-2026-08-25",
  "source_system": "front_his",
  "business_date": "2026-08-25",
  "shift": "1",
  "issues": [
    {
      "line_external_id": "DRUG-PARA-1",
      "hn": "6500123",
      "vn": "6808250001",
      "product_code": "00001",
      "item_type": "drug",
      "warehouse_code": "PHAR",
      "qty": 10,
      "reason": "patient_use",
      "lots": [
        {"lot_name": "LOT-A", "qty": 6},
        {"lot_name": "LOT-B", "qty": 4}
      ]
    },
    {
      "line_external_id": "SUP-GLOVE-1",
      "hn": "6500123",
      "vn": "6808250001",
      "product_code": "201001",
      "item_type": "medical_supply",
      "warehouse_code": "UNIT",
      "qty": 2,
      "reason": "patient_use"
    },
    {
      "line_external_id": "DRUG-AMOX-2",
      "hn": "6700888",
      "vn": "6808250042",
      "product_code": "00012",
      "item_type": "drug",
      "warehouse_code": "PHAR",
      "qty": 8,
      "lot_name": "AMX-2508",
      "reason": "patient_use"
    }
  ],
  "control_totals": {
    "qty_total": 20
  }
}
```

กฎสำคัญ:

| รายการ | ค่า |
|---|---|
| `hn` | รหัสโรงพยาบาลของคนไข้ **จำเป็น** เมื่อ `reason=patient_use` |
| `vn` | รหัสการมารับบริการ **จำเป็น** เมื่อ `reason=patient_use` |
| `product_code` | รหัสสินค้า ERP (`default_code`) ยาที่เป็นตัวเลขจะถูก pad เป็น 5 หลัก |
| `item_type` | `drug` ยา · `medical_supply` เวชภัณฑ์ไม่ใช่ยา · `other` (ไม่บังคับ) |
| `warehouse_code` | รหัสคลัง Odoo เช่น `PHAR`, `UNIT`, `OR` หรือใช้ `department_code` ถ้ามีแมปหน่วยบริการ |
| `qty` | จำนวนที่จ่ายในรายการนั้น (ถ้ามี `lots[]` ต้องเท่าผลรวม lot) |
| `lot_name` | ส่งเมื่อสินค้าติดตาม Lot และใช้ Lot เดียว |
| `lots[]` | ส่งเมื่อรายการเดียวกันใช้หลาย Lot — ห้ามส่งคู่กับ `lot_name` (HN/VN ของบรรทัดแม่ถูกคัดลอกไปทุก Lot) |
| `reason` | `patient_use` (ค่าเริ่มต้น, จ่ายจากการบริการ ต้องมี HN/VN) · `ward_use` · `expired` · `adjust` |
| `items` | ใช้แทน `issues` ได้ |

`hn` / `vn` เก็บใน ERP เฉพาะคิวตัดจ่ายสินค้า ใช้ไล่รายการจ่ายยาตามคนไข้ได้  
API รายได้ (`POST /revenue`) **ยังห้ามส่ง** HN/VN/ชื่อคนไข้ — ระบบตัดทิ้งตามเดิม

สินค้าที่ไม่ติดตาม Lot ไม่ต้องส่ง `lot_name`  
สินค้าที่ติดตาม Lot/Serial **ต้องส่ง Lot** — ไม่ทราบรหัสให้ถาม `GET /vpk/api/v1/his/lookups/products?codes=00001,201001` (`lot_required: true`)  
Lot ที่ไม่มีใน ERP ทำให้ชุดข้อมูลเข้า `error` จะไม่สร้าง Lot ใหม่อัตโนมัติ

รหัสสินค้าที่ไม่รู้จัก**ไม่สร้างสินค้าใหม่อัตโนมัติ** ชุดข้อมูลอยู่สถานะ `error` จนกว่าจะมีรหัสใน ERP

Idempotency เหมือนรายได้: `source_system` + `external_id`

## เบิกเติมคลัง (คลังหลัก → คลัง front)

`POST /vpk/api/v1/his/stock-requisitions`

ใช้เมื่อหน่วยบริการ (เช่น OPD / ห้องยาชั้น 1) **ขอเบิกยา/เวชภัณฑ์จากคลังหลัก** มาเติมคลัง front  
ไม่เกี่ยวกับการจ่ายให้คนไข้ — **ไม่ต้องส่ง HN/VN**

```json
{
  "external_id": "HIS-REQ-2026-08-26-OPD-1",
  "source_system": "front_his",
  "business_date": "2026-08-26",
  "source_warehouse_code": "PHAR",
  "dest_warehouse_code": "UNIT",
  "dest_location_code": "shelf ห้องยาชั้น 1",
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
      "product_code": "201001",
      "item_type": "medical_supply",
      "qty": 20,
      "lot_name": "GLV-2508"
    }
  ],
  "control_totals": {
    "qty_total": 120
  }
}
```

กฎสำคัญ:

| รายการ | ค่า |
|---|---|
| `source_warehouse_code` | คลังต้นทาง (คลังหลัก) เช่น `PHAR`, `WH` — ค่าเริ่มต้น `PHAR` |
| `dest_warehouse_code` | คลังปลายทาง (front) เช่น `UNIT` — ค่าเริ่มต้น `UNIT` |
| `department_code` | รหัสหน่วยบริการ HIS — ใช้แมปจาก `HIS Service Units` ถ้าไม่ส่ง `dest_warehouse_code` |
| `dest_location_code` | ชั้นวาง/location ปลายทาง (ไม่บังคับ) |
| `lines` / `items` / `requisitions` | รายการขอเบิก — โครงสร้างคล้าย `issues` แต่ไม่มี `hn`, `vn`, `reason` |
| `lot_name` / `lots[]` | ไม่บังคับตอนขอเบิก — ถ้าไม่ส่ง ERP เลือก Lot แบบ FEFO ตอน Post |

เมื่อ Post สำเร็จ ERP สร้าง Internal Transfer (`HISINT`) จากคลังต้นทางไปคลังปลายทาง  
Idempotency และ reversal เหมือน API อื่น — ใช้ endpoint เดียวกันพร้อม `original_external_id`

## Lookups

- `GET /vpk/api/v1/his/lookups/entitlements`
- `GET /vpk/api/v1/his/lookups/payment-methods`
- `GET /vpk/api/v1/his/lookups/warehouses`
- `GET /vpk/api/v1/his/lookups/products?codes=00001,201001` — ดูว่าสินค้าต้องส่ง Lot หรือไม่
- `GET /vpk/api/v1/his/batches/{external_id}?source_system=front_his`

Do not send patient identifiers on **revenue** (`hn`, `cid`, `patient_name`, …). That API drops them if present.  
Stock issues **must** send `hn` and `vn` for patient dispensing; other PII (name, CID) is still dropped.
