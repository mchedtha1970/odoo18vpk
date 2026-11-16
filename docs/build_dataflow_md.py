#!/usr/bin/env python3
"""สร้าง docs/dataflow.md (Workflow / Dataflow ชุดงบประมาณ และชุดจัดซื้อจัดจ้าง)

ข้อมูลตารางดึงจาก budget_dataflow_data.py และ procurement_dataflow_data.py
(ชุดเดียวกับที่ใช้สร้าง PPTX และ Excel) แผนภาพเป็น Mermaid

รัน: python3 docs/build_dataflow_md.py
ผลลัพธ์: docs/dataflow.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import budget_dataflow_data as B  # noqa: E402
import procurement_dataflow_data as P  # noqa: E402

OUT = Path(__file__).parent / "dataflow.md"


def cell(items, bullet="•"):
    if isinstance(items, str):
        items = [items]
    return "<br>".join(f"{bullet} {t}".replace("|", "\\|") for t in items)


def esc(t):
    return str(t).replace("|", "\\|")


def function_tables(funcs, phases, with_method=False):
    out = []
    for code, name, desc in phases:
        fs = [f for f in funcs if f["phase"] == code]
        if not fs:
            continue
        out.append(f"#### {code}. {name}\n")
        out.append(f"_{desc}_\n")
        head = "| รหัส | ฟังก์ชัน | ผู้ใช้ |"
        sep = "|---|---|---|"
        if with_method:
            head += " วิธีจัดซื้อ |"
            sep += "---|"
        head += " Input | Process | Output | เมนู | Model / Method |"
        sep += "---|---|---|---|---|"
        out += [head, sep]
        for f in fs:
            row = f"| {f['code']} | **{esc(f['name'])}** | {esc(f['actor'])} |"
            if with_method:
                row += f" {P.METHOD_LABEL[f['method']]} |"
            row += (f" {cell(f['inputs'])} | {cell(f['process'], '›')} | {cell(f['outputs'])} |"
                    f" {esc(f['menu'])} | `{esc(f['tech'])}` |")
            out.append(row)
        out.append("")
    return "\n".join(out)


def integration_table():
    out = ["| รหัส | วิธีจัดซื้อ | จุดเชื่อม | จาก → ไป | Input | Output / ผลต่องบ | ทริกเกอร์ | Field / Method |",
           "|---|---|---|---|---|---|---|---|"]
    for t in P.INTEGRATION:
        out.append(
            f"| {t['code']} | {P.METHOD_LABEL[t['method']]} | **{esc(t['name'])}** | {esc(t['frm'])} → {esc(t['to'])} |"
            f" {cell(t['inputs'])} | {cell(t['outputs'])} | {esc(t['trigger'])} | `{esc(t['tech'])}` |")
    return "\n".join(out)


def contract_steps(key):
    info = P.CONTRACT_TYPES[key]
    out = ["| ขั้น | ขั้นตอน | ผู้ทำ | Input | Process | Output | Field / Method |",
           "|---|---|---|---|---|---|---|"]
    for st in info["steps"]:
        out.append(f"| {st['code']} | **{esc(st['name'])}** | {esc(st['actor'])} | {cell(st['inputs'])} |"
                   f" {cell(st['process'], '›')} | {cell(st['outputs'])} | `{esc(st['tech'])}` |")
    return "\n".join(out)


def contract_compare():
    out = ["| หัวข้อ | สัญญาซื้อขาย | สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน |", "|---|---|---|"]
    for t, a, b in P.CONTRACT_COMPARE:
        out.append(f"| **{esc(t)}** | {esc(a)} | {esc(b)} |")
    return "\n".join(out)


HEAD = """# Workflow / Dataflow ระบบ VPK ERP (Odoo 18): งบประมาณ และจัดซื้อจัดจ้าง

เอกสารนี้สร้างอัตโนมัติด้วย `docs/build_dataflow_md.py` จากข้อมูลชุดเดียวกับ
`Workflow-Dataflow-งบประมาณ.pptx`, `Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx` และ `สรุป-Function-ตาม-Module.xlsx`
(แก้ข้อมูลที่ `budget_dataflow_data.py` / `procurement_dataflow_data.py` แล้วรันสคริปต์ใหม่)

แผนภาพเป็น Mermaid (ดูได้ใน Cursor / GitHub ที่เปิด Markdown preview)

## 1. ภาพรวม: แยกเป็น 2 ชุด

- **ชุดงบประมาณ** สิ้นสุดที่ "แผนงบที่อนุมัติ และพร้อมใช้งาน" (`budget.lines`)
- **ชุดจัดซื้อจัดจ้าง** มี INPUT คือแผนงบที่อนุมัติ นำไปทำใบขอซื้อ (PR) ตามวิธีจัดซื้อ

```mermaid
flowchart LR
    subgraph BUD["ชุดงบประมาณ (vpk_budget)"]
        direction LR
        A["ตั้งค่าข้อมูลหลัก"] --> Bq["หน่วยงานสร้างและส่งคำของบ"]
        Bq --> C["งานงบ รับเรื่อง / พิจารณา / จัดสรร"]
        C --> D["อนุมัติ สร้าง budget.lines"]
        D --> E["แผนงบที่อนุมัติ พร้อมใช้งาน"]
    end
    E -->|"INPUT"| F{"วิธีจัดซื้อ?"}
    subgraph PRO["ชุดจัดซื้อจัดจ้าง"]
        direction LR
        F -->|"เฉพาะเจาะจง: ไม่ต้องทำแผน"| S1["PR"]
        S1 --> S2["e-GP"] --> S3["สร้าง PO"] --> S4["ตรวจรับ / เจ้าหนี้"]
        F -->|"e-bidding: ทำแผนก่อน"| E1["แผนจัดซื้อ"]
        E1 --> E2["PR"] --> E3["e-GP"] --> E4["ทำสัญญา"] --> E5["ตรวจรับ / เจ้าหนี้"]
    end
    S4 -.->|"ผูกพัน / ใช้จริง กลับสู่งบ"| E
    E5 -.->|"ใช้จริง กลับสู่งบ"| E
```

"""

BUDGET_FLOW = """## 2. ชุดงบประมาณ

### 2.1 Workflow

```mermaid
flowchart TD
    subgraph L0["ข้อมูลหลัก"]
        s0["ขั้น 0 ตั้งค่าข้อมูลหลัก + แผนประจำปี"]
    end
    subgraph L1["หน่วยงาน"]
        s1["ขั้น 1 สร้างใบคำของบ"] --> s2["ขั้น 2 เพิ่มรายการ (โหลด / Import)"] --> s3["ขั้น 3 ส่งใบคำขอ"]
    end
    subgraph L2["งานงบประมาณ"]
        s4["ขั้น 4 รับเรื่อง / เริ่มพิจารณา"] --> s5["ขั้น 5 จัดสรรยอด"] --> s6["ขั้น 6 อนุมัติ"]
        s8["ขั้น 8 พิมพ์ / Export / Dashboard สถานะ"]
    end
    subgraph L3["ระบบ (อัตโนมัติ)"]
        sb["สร้าง budget.lines ในแผนประจำปี"] --> s7["ขั้น 7 แผนงบที่อนุมัติ พร้อมใช้งาน"]
    end
    s0 --> s1
    s3 --> s4
    s4 -.->|"ตีกลับ / ตั้งเป็นร่าง"| s1
    s5 -.->|"ตีกลับ"| s1
    s6 --> sb
    s7 -.->|"อ่านข้อมูล"| s8
    s7 ==>|"ส่งมอบ"| ENDN["ชุดจัดซื้อจัดจ้าง: ทำใบขอซื้อ (PR) โดยเลือกคำของบ + รายการงบ"]
```

### 2.2 สถานะใบคำของบ (`departmental.budget.request`)

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Submitted: ส่งใบคำขอ (หน่วยงาน)
    Submitted --> Received: รับเรื่อง (งานงบ)
    Received --> Review: เริ่มพิจารณา (งานงบ)
    Received --> Approved: อนุมัติทันที
    Review --> Approved: อนุมัติ
    Submitted --> Rejected: ตีกลับ
    Received --> Rejected: ตีกลับ
    Review --> Rejected: ตีกลับ
    Rejected --> Draft: ตั้งเป็นร่าง
    Approved --> Draft: ตั้งเป็นร่าง (ลบ budget.lines ที่เคยสร้าง)
    Approved --> [*]: budget.lines พร้อมให้ PR ใช้
```

เมื่ออนุมัติ: สร้าง `budget.lines` (planned = ยอดจัดสรร) และกำหนด `budget_record_id` = แผนประจำปี

### 2.3 Data Flow (ระดับ 1)

```mermaid
flowchart LR
    P1(["P1 ตั้งค่าข้อมูลหลัก<br>งานงบประมาณ"]) --> D1[("D1 ข้อมูลหลักงบ")]
    D1 --> P2(["P2 จัดทำและส่งคำของบ<br>หน่วยงาน"])
    P2 --> D2[("D2 ใบคำของบ<br>departmental.budget.request")]
    D2 <--> P3(["P3 พิจารณา จัดสรร อนุมัติ<br>งานงบประมาณ"])
    P3 -->|"สร้างรายการงบ planned"| D3[("D3 รายการงบประมาณ<br>budget.lines")]
    D3 ==>|"แผนงบที่อนุมัติ พร้อมใช้ (INPUT ของชุดจัดซื้อ)"| EXT["ระบบจัดซื้อจัดจ้าง"]
    D2 -.-> P4(["P4 รายงานและติดตามสถานะ"])
    D3 -.-> P4
    D1 -.-> P4
```

### 2.4 Input / Process / Output ของแต่ละ function

"""

PROC_FORK = """## 3. ชุดจัดซื้อจัดจ้าง

### 3.1 ภาพรวมกระบวนการจัดซื้อ จัดจ้าง (จุดแยกตามวิธีจัดซื้อ)

- **หน่วยงาน** เปิด PR → เลือกแผนงบประมาณ → เช็คงบประมาณ → เพิ่มกรรมการ → ขออนุมัติขอซื้อ → ส่งจัดซื้อ จากนั้น **จัดซื้อ** เป็นผู้ดำเนินการต่อตามเงื่อนไขว่าต้องทำแผนหรือไม่
- จัดซื้อรับงาน (admin ตรวจสอบ) แล้ว **ส่งเข้า e-GP ทันที** จุดตัดสินใจ (วิธีจัดซื้อ / ทำแผนหรือไม่) และ flow ทั้งหมดอยู่ใน e-GP — ขั้น e-GP คือการแนบไฟล์ต่างๆ จากระบบ e-GP ของรัฐ (ขออนุมัติ ลงนาม จนคัดเลือกได้ผู้ชนะ)
- **เฉพาะเจาะจง:** ไม่ต้องทำแผน → ได้ผู้ชนะ → สร้าง PO (ทำสัญญาก่อนสร้าง PO ได้ถ้าจำเป็น) (ถ้าโครงการมูลค่า **> 500,000 บาท** ต้องทำแผนในระบบ e-GP ด้วย)
- **e-bidding:** ต้องทำแผนก่อน → ได้ผู้ชนะ → ทำสัญญา → สร้าง PO
- **กล่อง "ทำแผน"** เป็นตัวเชื่อมภายใน e-GP: e-bidding ผ่านเสมอ · เฉพาะเจาะจงผ่านเมื่อมูลค่า > 500,000 บาท
- **e-GP จบที่ได้ผู้ชนะ และทำสัญญา** จากนั้นแยกเป็นกล่อง **PO ซื้อ** ให้สอดคล้องกับระบบงานรัฐที่ต้องทำใน GFMIS → ส่ง PO ให้ผู้ขายยืนยัน → ส่งกลับให้จัดซื้อยืนยันอีกครั้ง → สินค้า: เกิดใบรับส่งไประบบ Inventory · บริการ/ครุภัณฑ์: เข้าระบบตรวจรับงาน
- **หมายเหตุเทียบกับ ERP ปัจจุบัน:** ผู้ขายยืนยันบนพอร์ทัลแล้วระบบเรียกยืนยัน PO (`button_confirm`) อัตโนมัติ ยังไม่มีขั้นให้จัดซื้อกดยืนยันซ้ำ และ ERP ไม่เชื่อม GFMIS โดยตรง (ขั้นนี้ทำในระบบรัฐ)

```mermaid
flowchart TD
    subgraph U["หน่วยงาน"]
        IN["INPUT: แผนงบที่อนุมัติ<br>budget.lines"] --> u1["เปิด PR"] --> u2["เลือกแผนงบประมาณ"] --> u3["เช็คงบประมาณ<br>ตรวจ + จองงบ"] --> u4["เพิ่มกรรมการ"] --> u5["ขออนุมัติขอซื้อ"] --> u6["ส่งจัดซื้อ"]
    end
    u6 --> c1["จัดซื้อรับงาน<br>admin ตรวจสอบ + มอบหมาย"]
    c1 -->|"ส่งเข้า e-GP"| Q
    subgraph EG["ระบบ e-GP ของรัฐ: จุดตัดสินใจและ flow อยู่ในนี้ · จบที่ได้ผู้ชนะ และทำสัญญา"]
        Q{"วิธีจัดซื้อ?"}
        g{"เฉพาะเจาะจง<br>มูลค่า > 500,000 บาท?"}
        PLAN{{"ทำแผน (ตัวเชื่อม)<br>e-bidding: แผนจัดซื้อ A1<br>เฉพาะเจาะจง > 500,000: แผนใน e-GP A4"}}
        egp["แนบไฟล์จากระบบ e-GP<br>ขออนุมัติ ลงนาม เปรียบเทียบราคา"]
        win["ได้ผู้ชนะ"]
        con["ทำสัญญา<br>(e-bidding ทำเสมอ · เฉพาะเจาะจงทำได้ถ้าจำเป็น)"]
        Q -->|"เฉพาะเจาะจง<br>ไม่ต้องทำแผน"| g
        Q -->|"e-bidding<br>ทำแผนก่อน"| PLAN
        g -->|"ใช่ ต้องทำแผน"| PLAN
        g -->|"ไม่เกิน"| egp
        PLAN --> egp --> win
        win -->|"e-bidding ทำเสมอ<br>เฉพาะเจาะจง ถ้าต้องมีสัญญา"| con
    end
    subgraph PO["PO ซื้อ ตามระบบงานรัฐ (ทำใน GFMIS)"]
        po["สร้าง PO ซื้อ<br>บันทึกใน GFMIS"] --> snd["ส่ง PO ให้ผู้ขายยืนยัน"] --> cf["จัดซื้อยืนยัน PO อีกครั้ง<br>ตรวจงบ → ผูกพันงบ → ใบรอรับ"] --> ty{"ประเภท?"}
    end
    win -->|"เฉพาะเจาะจง ไม่ทำสัญญา"| po
    con --> po
    ty -->|"สินค้า"| rc["ใบรับสินค้า (Receipt)<br>ส่งเข้าระบบ Inventory"]
    ty -->|"บริการ / ครุภัณฑ์"| wa["ระบบตรวจรับงาน<br>คณะกรรมการตรวจรับ"]
    rc --> ap["เบิกจ่าย (ระบบบัญชี)<br>ตั้งเจ้าหนี้ → ตัดเป็นยอดใช้จริง"]
    wa --> ap
```

### 3.2 Workflow วิธีเฉพาะเจาะจง

```mermaid
flowchart TD
    subgraph U["หน่วยงาน"]
        pr["สร้าง PR<br>เลือกแผนงบที่อนุมัติ [T2]"] --> snd["ส่งจัดซื้อ<br>ต้องเช็คงบผ่าน [T6]"]
    end
    subgraph S["ระบบ: งบประมาณ"]
        inp["INPUT: แผนงบที่อนุมัติ"]
        chk["เช็คงบ + จอง<br>คงเหลือ ≥ ยอด PR [T3]"]
        exc["ข้อยกเว้น: PR ฉุกเฉิน ข้ามจอง [T5]"]
        cf["จัดซื้อยืนยัน PO อีกครั้ง<br>ตรวจงบ → ย้ายจอง → ผูกพัน [T8]"]
        used["ตัดผูกพัน → ยอดใช้จริง [T9]"]
    end
    subgraph PS["พัสดุ"]
        app["จัดซื้อรับงาน<br>admin ตรวจสอบ [C1]"] --> gate{"มูลค่า > 500,000 บาท?"}
        gate -->|"ใช่"| gp["ทำแผนในระบบ e-GP [A4]"] --> egp["e-GP: แนบไฟล์จากระบบรัฐ<br>ขออนุมัติ ลงนาม ได้ผู้ชนะ [T7]"]
        gate -->|"ไม่เกิน"| egp
        egp --> po["สร้าง PO ตามระบบ GFMIS"]
    end
    subgraph V["ผู้ขาย / ตรวจรับ"]
        vd["ผู้ขายยืนยัน → ใบรับสินค้า (Inventory) / ตรวจรับงาน (บริการ-ครุภัณฑ์)"]
    end
    subgraph F["เจ้าหนี้ / การเงิน"]
        bill["ตั้งเจ้าหนี้ Post Vendor Bill [T9]"] --> pay["จ่ายเงิน / GFMIS"]
    end
    inp -->|"ไม่ต้องทำแผน"| pr
    inp -.-> chk
    pr --> chk
    chk --> snd
    chk -.-> exc
    snd --> app
    po --> cf --> vd --> bill
    bill --> used
    used --> dash["Dashboard ติดตามงบ"]
```

### 3.3 Workflow วิธี e-bidding

```mermaid
flowchart TD
    subgraph U["หน่วยงาน"]
        pr["สร้าง PR<br>เลือกแผนงบที่อนุมัติ [T2]"] --> snd["ส่งจัดซื้อ<br>ต้องเช็คงบผ่าน [T6]"]
    end
    subgraph PS["พัสดุ"]
        plan["แผนจัดซื้อ (ต้องทำก่อน)<br>ผูกแผนงบ/รายการงบ [T1]"]
        app["จัดซื้อรับงาน<br>admin ตรวจสอบ [C1]"] --> egp["e-GP: แนบไฟล์จากระบบรัฐ<br>ขออนุมัติ ลงนาม ได้ผู้ชนะ [T7]"] --> con["ทำสัญญา<br>ทะเบียนสัญญา · งวดงาน [T4]"]
    end
    subgraph S["ระบบ: งบประมาณ"]
        inp["INPUT: แผนงบที่อนุมัติ"]
        chk["เช็คงบ + จอง [T3]"]
        exc["ข้อยกเว้น: PR ผูกสัญญา<br>ตรวจวงเงินสัญญาแทนการจองซ้ำ [T4]"]
        used["ตัดผูกพัน → ยอดใช้จริง [T9]"]
    end
    subgraph V["ผู้ขาย / ตรวจรับ"]
        rcv["ผู้ขายส่งมอบ → กรรมการตรวจรับ"]
    end
    subgraph F["เจ้าหนี้ / การเงิน"]
        bill["ตั้งเจ้าหนี้ Post Vendor Bill [T9]"] --> pay["จ่ายเงิน / GFMIS"]
    end
    inp --> plan --> pr
    inp -.-> chk
    pr --> chk --> snd
    chk -.-> exc
    snd --> app
    con --> rcv --> bill
    bill --> used --> dash["Dashboard ติดตามงบ"]
```

### 3.4 Data Flow ระหว่างงบประมาณ และจัดซื้อจัดจ้าง

วิธีเฉพาะเจาะจง:

```mermaid
flowchart LR
    subgraph BUD["INPUT จากชุดงบประมาณ"]
        d2["คำของบที่อนุมัติ"] --> d3[("budget.lines<br>planned / reserved / committed / actual")]
    end
    subgraph PRO["จัดซื้อจัดจ้าง: เฉพาะเจาะจง"]
        nop["ไม่ต้องทำแผนจัดซื้อ<br>(มูลค่า > 500,000 บาท ทำแผนใน e-GP)"]
        pr["ใบขอซื้อ (PR)"] --> egp["e-GP / เปรียบเทียบราคา"] --> po["ใบสั่งซื้อ (PO)"] --> bill["Vendor Bill"]
    end
    d2 -->|"T2 หน่วยงาน/แหล่งเงิน/กลุ่ม/หมวด"| pr
    d3 <-->|"T3 เลือกรายการงบ จอง / ตรวจงบคงเหลือ"| pr
    d3 <-->|"T8 ยืนยัน PO ย้ายจอง PR → ผูกพัน PO"| po
    bill -->|"T9 ผูกพันลด + ยอดใช้จริง"| d3
```

วิธี e-bidding:

```mermaid
flowchart LR
    subgraph BUD["INPUT จากชุดงบประมาณ"]
        d2["คำของบที่อนุมัติ"] --> d3[("budget.lines<br>planned / reserved / committed / actual")]
    end
    subgraph PRO["จัดซื้อจัดจ้าง: e-bidding"]
        plan["แผนจัดซื้อประจำปี (ต้องทำก่อน)"] --> pr["ใบขอซื้อ (PR)"] --> egp["e-GP / เปรียบเทียบราคา"] --> con["สัญญา"] --> bill["Vendor Bill"]
    end
    d3 <-->|"T1 ผูกแผนจัดซื้อกับแผนงบ"| plan
    d2 -->|"T2"| pr
    d3 <-->|"T3 เลือกรายการงบ จอง / ตรวจงบคงเหลือ"| pr
    d3 <-.->|"T4 PR/PO ผูกสัญญา ตรวจวงเงินสัญญาแทนการจองซ้ำ"| con
    bill -->|"T9 ผูกพันลด + ยอดใช้จริง"| d3
```

### 3.5 จุดเชื่อมกับงบประมาณ (T1–T10)

"""

CONTRACT_FLOWS = """## 4. Workflow ตามประเภทสัญญา (e-bidding ทำเสมอ · เฉพาะเจาะจงทำได้ถ้าจำเป็น)

ประเภทสัญญาเป็นข้อมูลหลักที่เพิ่มได้ในระบบ (ตารางประเภทสัญญา) ระบบตรวจวงเงินสัญญาเป็น **มูลค่า**
(Hard Block ที่ PR และตอนยืนยัน PO) ไม่ได้ตรวจจำนวนชิ้น ความต่างของสองประเภทเกิดจากการมี/ไม่มีงวดงาน
และความหมายของมูลค่ารวมสัญญา

### 4.1 เปรียบเทียบ

"""

SALE_FLOW = """
### 4.2 สัญญาซื้อขาย

```mermaid
flowchart LR
    S1["S1 เปิดทะเบียนสัญญา<br>จาก e-GP ผู้ชนะ"] --> S2["S2 บันทึกรายการ/เงื่อนไข"] --> S3["S3 แบ่งงวดงาน<br>ผลรวมงวด = มูลค่า"]
    S3 --> S4["S4 แนบเอกสาร + หลักประกัน"] --> S5["S5 ยืนยันสัญญา<br>(ผู้จัดการจัดซื้อ)"]
    S5 --> Y1(["มีผลบังคับใช้"])
    Y1 --> S6["S6 เปิด PR ต่องวด<br>ดึงงวดถัดไป ผูกสัญญา"]
    S6 --> Y2{"ตรวจวงเงินสัญญา<br>Hard Block"}
    Y2 --> S7["S7 สร้าง PO + ผู้ขายยืนยัน"]
    S7 --> Y3["ตัดวงเงินสัญญา"]
    Y3 --> S8["S8 ตรวจรับ → ตั้งเจ้าหนี้ ต่องวด"]
    S8 -->|"ยังมีงวดเหลือ"| S6
    S8 -->|"ครบทุกงวด / ครบอายุ"| S9["S9 ปิดสัญญา"]
```

"""

FW_FLOW = """
### 4.3 สัญญาจะซื้อจะจ้างไม่จำกัดจำนวน

```mermaid
flowchart LR
    N1["N1 เปิดทะเบียนสัญญา<br>จาก e-GP ผู้ชนะ"] --> N2["N2 วงเงินเพดาน<br>ราคาต่อหน่วย อายุสัญญา<br>(ไม่สร้างงวด)"]
    N2 --> N3["N3 แนบเอกสาร + หลักประกัน"] --> N4["N4 ยืนยันสัญญา"]
    N4 --> Y1(["มีผลบังคับใช้ พร้อมให้เรียกใช้"])
    Y1 --> N5["N5 เปิด PR เรียกใช้ (Call-off)<br>เพิ่มรายการเอง"]
    N5 --> Y2{"ตรวจวงเงินสัญญา<br>Hard Block"}
    Y2 --> N6["N6 สร้าง PO ต่อรอบ + ผู้ขายยืนยัน"]
    N6 --> Y3["ตัดวงเงินสัญญา"]
    Y3 --> N7["N7 ตรวจรับ → ตั้งเจ้าหนี้ ต่อรอบ"]
    N7 -->|"N8 วงเงินคงเหลือ > 0 และยังไม่หมดอายุ"| N5
    N7 -->|"วงเงินหมด / หมดอายุ"| N9["N9 ปิดสัญญา"]
```

"""


def main():
    parts = [HEAD, BUDGET_FLOW, function_tables(B.FUNCTIONS, B.PHASES), "\n", PROC_FORK, integration_table(), "\n",
             "\n### 3.6 Input / Process / Output ของแต่ละ function\n\n",
             function_tables(P.FUNCTIONS, P.PHASES, with_method=True), "\n",
             CONTRACT_FLOWS, contract_compare(), "\n", SALE_FLOW,
             "ขั้นตอนละเอียด:\n\n", contract_steps("sale"), "\n", FW_FLOW,
             "ขั้นตอนละเอียด:\n\n", contract_steps("framework"), "\n",
             """## 5. ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | หน้าที่ |
|---|---|
| `docs/budget_dataflow_data.py` | ข้อมูล Input/Process/Output ชุดงบประมาณ |
| `docs/procurement_dataflow_data.py` | ข้อมูลชุดจัดซื้อจัดจ้าง จุดเชื่อม T1–T10 และประเภทสัญญา |
| `docs/build_dataflow_md.py` | สร้างไฟล์นี้ |
| `docs/build_budget_dataflow_pptx.py` | สร้าง `Workflow-Dataflow-งบประมาณ.pptx` |
| `docs/build_procurement_dataflow_pptx.py` | สร้าง `Workflow-Dataflow-จัดซื้อจัดจ้าง.pptx` |
| `docs/build_module_function_summary_xlsx.py` | สร้าง `สรุป-Function-ตาม-Module.xlsx` |

> ข้อสังเกต: การติดป้ายวิธีจัดซื้อ (เฉพาะเจาะจง / e-bidding) และความหมายของประเภทสัญญา
> เป็นไปตามที่ผู้ใช้ระบุและพฤติกรรมของโค้ด ควรให้พัสดุยืนยันกับแนวปฏิบัติจริงของโรงพยาบาล
"""]
    OUT.write_text("".join(parts), encoding="utf-8")
    print("saved", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
