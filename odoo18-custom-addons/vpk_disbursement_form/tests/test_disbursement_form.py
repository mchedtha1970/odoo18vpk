# Copyright 2026 VPK
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
import base64
from datetime import date

import xlrd

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.tests.common import TransactionCase

from ..models.disbursement_form import thai_baht_text
from ..tools.xls_template import read_sheet_protection


@tagged("post_install", "-at_install")
class TestDisbursementForm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = cls.env["vpk.disbursement.form"].create(
            {
                "budget_type": "2",
                "gfmis_po_number": "4102887681",
                "reference": "P690008971",
                "document_date": date(2026, 9, 12),
                "posting_date": date(2026, 9, 12),
                "description": "ค่ายา บริษัท แก้วมังกรเภสัช จำกัด เป็นเงิน  270,500 บาท",
                "amount_request": 270000.0,
                "tax_type": "corp",
                "agency_code": "2102",
                "agency_name": "สำนักงานปลัดกระทรวงสาธารณสุข",
                "province_code": "8300",
                "province_name": "ภูเก็ต",
                "unit_code": "2100200231",
                "unit_name": "โรงพยาบาลวชิระภูเก็ต",
            }
        )

    def test_baht_text(self):
        self.assertEqual(
            thai_baht_text(267476.64),
            "สองแสนหกหมื่นเจ็ดพันสี่ร้อยเจ็ดสิบหกบาทหกสิบสี่สตางค์",
        )
        self.assertEqual(thai_baht_text(18020), "หนึ่งหมื่นแปดพันยี่สิบบาทถ้วน")
        self.assertEqual(thai_baht_text(101), "หนึ่งร้อยเอ็ดบาทถ้วน")
        self.assertEqual(thai_baht_text(1000001), "หนึ่งล้านเอ็ดบาทถ้วน")

    def test_amounts_match_template_sample(self):
        # ตัวอย่างใน template: ฐาน 252,336.45 ภาษี 2,523.36 ยอดขอรับ 267,476.64
        self.assertAlmostEqual(self.form.wht_base, 252336.45, places=2)
        self.assertAlmostEqual(self.form.wht_amount, 2523.36, places=2)
        self.assertAlmostEqual(self.form.amount_net, 267476.64, places=2)
        self.assertEqual(
            self.form.amount_text,
            "สองแสนหกหมื่นเจ็ดพันสี่ร้อยเจ็ดสิบหกบาทหกสิบสี่สตางค์",
        )

    def test_generate_excel_attaches_file(self):
        self.form.action_generate_excel()
        files = self.form.file_ids.filtered(lambda f: f.kind == "generated")
        self.assertEqual(len(files), 1)
        self.assertEqual(files.version, 1)
        book = xlrd.open_workbook(file_contents=base64.b64decode(files.file))
        inp = book.sheet_by_name("Input")
        itf = book.sheet_by_name("Interface")
        self.assertEqual(inp.cell_value(7, 8), "4102887681")  # I8
        self.assertEqual(inp.cell_value(7, 12), 2.0)  # M8 ประเภทรายการขอเบิก
        self.assertEqual(inp.cell_value(13, 1), "P690008971")  # B14
        self.assertAlmostEqual(inp.cell_value(14, 10), 270000.0)  # K15
        self.assertAlmostEqual(inp.cell_value(17, 9), 252336.45)  # J18
        self.assertAlmostEqual(inp.cell_value(17, 10), 2523.36)  # K18
        self.assertAlmostEqual(inp.cell_value(20, 10), 267476.64)  # K21
        self.assertTrue(inp.cell_value(7, 1).startswith("○"))
        self.assertTrue(inp.cell_value(8, 1).startswith("●"))
        self.assertEqual(itf.cell_value(4, 3), "4102887681")  # D5
        self.assertEqual(itf.cell_value(4, 4), "KG")  # E5
        self.assertEqual(itf.cell_value(4, 5), "25690912")  # F5
        self.assertEqual(itf.cell_value(4, 7), "3")  # H5
        self.assertEqual(itf.cell_value(4, 10), "10")  # K5
        self.assertEqual(itf.cell_value(4, 11), "A1")  # L5
        self.assertAlmostEqual(itf.cell_value(4, 13), 2523.36)  # N5
        self.assertEqual(itf.cell_value(4, 18), "2100200231")  # S5
        self.assertEqual(itf.cell_value(1, 3), "IA04e25f01")  # HASH เดิมของ template
        self.assertEqual(book.sheet_by_name("Interface").visibility, 1)
        # ชีตต้องถูกล็อก (Protect Sheet + รหัสผ่านเดิม) เหมือน template
        template_prot = read_sheet_protection(
            file_open("vpk_disbursement_form/data/templates/kb01_template.xls", "rb").read()
        )
        generated_prot = read_sheet_protection(base64.b64decode(files.file))
        self.assertEqual(len(generated_prot), 2)
        self.assertEqual(generated_prot, template_prot)
        self.assertTrue(all(p["protect"] and p["password_hash"] for p in generated_prot))
        # สร้างซ้ำ = ไฟล์ครั้งที่ 2 (ไม่ทับของเดิม)
        self.form.action_generate_excel()
        self.assertEqual(
            sorted(self.form.file_ids.filtered(lambda f: f.kind == "generated").mapped("version")),
            [1, 2],
        )

    def test_validation_and_states(self):
        draft = self.form.copy({"reference": False})
        with self.assertRaises(UserError):
            draft.action_generate_excel()
        with self.assertRaises(UserError):
            draft.action_confirm()
        self.form.action_confirm()
        with self.assertRaises(UserError):
            self.form.action_mark_uploaded()  # ยังไม่มีไฟล์
        self.form.action_generate_excel()
        self.form.gfmis_doc_number = "3100000001"
        self.form.action_mark_uploaded()
        self.assertEqual(self.form.state, "uploaded")
        with self.assertRaises(UserError):
            self.form.unlink()
