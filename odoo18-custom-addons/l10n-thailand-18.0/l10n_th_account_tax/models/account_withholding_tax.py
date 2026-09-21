# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .withholding_tax_cert import INCOME_TAX_FORM, WHT_CERT_INCOME_TYPE

_logger = logging.getLogger(__name__)

# หน่วยงานของรัฐ ตามมาตรา 3 เตรส และ ท.ป. 4/2528
GOV_WHT_SET = (
    {
        "xml_id": "l10n_th_account_tax.wht_gov_purchase_1",
        "code": "WHT-1-GOODS",
        "name": "WHT 1% ซื้อสินค้า/บริการทั่วไป (ส่วนราชการ)",
        "amount": 1.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "5",
        "is_pit": False,
        "min_base_amount": 10000.0,
        "note": (
            "จ่ายเงินตั้งแต่ 10,000 บาทขึ้นไป (นับรวมทั้งสัญญา) "
            "กฎพิเศษเฉพาะส่วนราชการตามข้อ 12/4 ท.ป.4/2528 "
            "หักแม้นิติบุคคล (ต่างจากเอกชนที่มักไม่หักกรณีซื้อสินค้า)"
        ),
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_hire_of_work_3",
        "code": "WHT-3-HIRE",
        "name": "WHT 3% จ้างทำของ/จ้างเหมา/รับเหมาก่อสร้าง",
        "amount": 3.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "5",
        "is_pit": False,
        "min_base_amount": 1000.0,
        "note": "จ่ายตั้งแต่ 1,000 บาทขึ้นไปต่อครั้ง/สัญญา ใช้กับนิติบุคคลและบุคคลธรรมดาที่ประกอบธุรกิจ",
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_rent_5",
        "code": "WHT-5-RENT",
        "name": "WHT 5% ค่าเช่าทรัพย์สิน",
        "amount": 5.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "5",
        "is_pit": False,
        "min_base_amount": 1000.0,
        "note": "ค่าเช่าอาคาร ที่ดิน เครื่องจักร ฯลฯ จ่ายตั้งแต่ 1,000 บาทขึ้นไปต่อครั้ง/สัญญา",
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_transport_1",
        "code": "WHT-1-TRANSPORT",
        "name": "WHT 1% ค่าขนส่ง",
        "amount": 1.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "5",
        "is_pit": False,
        "min_base_amount": 1000.0,
        "note": "ผู้ประกอบการขนส่งจดทะเบียน จ่ายตั้งแต่ 1,000 บาทขึ้นไปต่อครั้ง/สัญญา ยกเว้นไปรษณีย์ไทย",
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_advertising_2",
        "code": "WHT-2-ADS",
        "name": "WHT 2% ค่าโฆษณา",
        "amount": 2.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "5",
        "is_pit": False,
        "min_base_amount": 1000.0,
        "note": "จ่ายตั้งแต่ 1,000 บาทขึ้นไปต่อครั้ง/สัญญา",
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_professional_3",
        "code": "WHT-3-PROF",
        "name": "WHT 3% ค่าบริการวิชาชีพอิสระ (นิติบุคคล)",
        "amount": 3.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "5",
        "is_pit": False,
        "min_base_amount": 1000.0,
        "note": (
            "กฎหมาย บัญชี วิศวกรรม สถาปัตยกรรม ประกอบโรคศิลปะ "
            "กรณีนิติบุคคลหัก 3% ตั้งแต่ 1,000 บาทขึ้นไปต่อครั้ง/สัญญา "
            "กรณีบุคคลธรรมดาให้หักตามอัตราก้าวหน้า (มาตรา 40(6)) — ใช้รายการ PIT"
        ),
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_interest_1",
        "code": "WHT-1-INTEREST",
        "name": "WHT 1% ดอกเบี้ย",
        "amount": 1.0,
        "income_tax_form": "pnd53",
        "wht_cert_income_type": "4A",
        "is_pit": False,
        "min_base_amount": 0.0,
        "note": "ตามแต่ละกรณี ตามมาตรา 40(4)ก",
    },
    {
        "xml_id": "l10n_th_account_tax.wht_gov_pit_personal",
        "code": "PIT-40",
        "name": "PIT ค่าจ้าง/ค่าตอบแทนบุคคลธรรมดา ม.40(1)-(2)",
        "amount": 0.0,
        "income_tax_form": "pnd1",
        "wht_cert_income_type": "1",
        "is_pit": True,
        "min_base_amount": 0.0,
        "note": (
            "คำนวณแบบเดียวกับการหักภาษีเงินเดือน ตามอัตราก้าวหน้า "
            "ขึ้นกับฐานเงินได้สุทธิหลังหักค่าใช้จ่าย/ค่าลดหย่อน"
        ),
    },
)


class AccountWithholdingTax(models.Model):
    _name = "account.withholding.tax"
    _description = "Account Withholding Tax"
    _check_company_auto = True
    _rec_names_search = ["name", "code"]
    _order = "code, name"

    code = fields.Char(string="รหัส", required=True, index=True, copy=False)
    name = fields.Char(required=True)
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Withholding Tax Account",
        # domain="[('wht_account', '=', True), ('company_ids', 'in', company_id)]",
        domain="[('wht_account', '=', True)]",
        required=True,
        ondelete="restrict",
    )
    amount = fields.Float(
        string="Percent",
    )
    is_pit = fields.Boolean(
        string="Personal Income Tax",
        help="As PIT, the calculation of withholding amount is based on pit.rate",
    )
    pit_id = fields.Many2one(
        comodel_name="personal.income.tax",
        string="PIT Rate",
        compute="_compute_pit_id",
        help="Latest PIT Rates used to calcuate withholiding amount",
    )
    income_tax_form = fields.Selection(
        selection=INCOME_TAX_FORM,
        string="Default Income Tax Form",
    )
    wht_cert_income_type = fields.Selection(
        selection=WHT_CERT_INCOME_TYPE,
        string="Default Type of Income",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    min_base_amount = fields.Monetary(
        string="เกณฑ์ขั้นต่ำ (บาท)",
        currency_field="company_currency_id",
        help="ยอดจ่ายขั้นต่ำที่ต้องหักตาม ท.ป. 4/2528 เช่น 10,000 สำหรับซื้อสินค้าโดยส่วนราชการ",
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
    )
    note = fields.Text(
        string="เงื่อนไข / หมายเหตุ",
        help="เกณฑ์และข้อควรระวังตามสรุปภาษีหัก ณ ที่จ่ายหน่วยงานรัฐ",
    )

    _sql_constraints = [
        ("name_unique", "UNIQUE(name,company_id)", "Name must be unique!"),
        ("code_unique", "UNIQUE(code,company_id)", "Code must be unique!"),
    ]

    @api.constrains("is_pit")
    def _check_is_pit(self):
        pits = self.search_count([("is_pit", "=", True)])
        if pits > 1:
            raise ValidationError(self.env._("Only 1 personal income tax allowed!"))

    @api.constrains("account_id")
    def _check_account_id(self):
        for rec in self:
            if rec.account_id and not rec.account_id.wht_account:
                raise ValidationError(
                    self.env._("Selected account is not for withholding tax")
                )

    @api.depends("is_pit")
    def _compute_pit_id(self):
        pit_date = self.env.context.get("pit_date") or fields.Date.context_today(self)
        pit = self.env["personal.income.tax"].search(
            [("effective_date", "<=", pit_date)], order="effective_date desc", limit=1
        )
        self.update({"pit_id": pit.id})

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name

    @api.model
    def _get_wht_account(self, code=None):
        """Find the WHT payable account and mark it as a WHT account."""
        Account = self.env["account.account"]
        codes = []
        if code:
            codes.append(code)
        codes.extend(
            (
                "2102040106.101",  # ภาษีหัก ณ ที่จ่ายรอนำส่ง - นิติบุคคลจากบุคคลภายนอก
                "2102040104.101",  # ภงด 1
                "2102040103.101",  # บุคคลธรรมดา
            )
        )
        seen = set()
        for acc_code in codes:
            if acc_code in seen:
                continue
            seen.add(acc_code)
            acc = Account.search([("code", "=", acc_code)], limit=1)
            if not acc:
                self.env.cr.execute(
                    "SELECT id FROM account_account WHERE code_store->>'1' = %s LIMIT 1",
                    (acc_code,),
                )
                row = self.env.cr.fetchone()
                acc = Account.browse(row[0]) if row else Account.browse()
            if acc:
                if not acc.wht_account:
                    acc.wht_account = True
                return acc
        acc = Account.search([("wht_account", "=", True)], limit=1)
        return acc

    @api.model
    def _load_government_wht_set(self):
        """Create/update government WHT masters on module install/upgrade."""
        account = self._get_wht_account("2102040106.101")
        if not account:
            _logger.warning(
                "l10n_th_account_tax: ไม่พบบัญชีภาษีหัก ณ ที่จ่าย "
                "(เช่น 2102040106.101) — ยังไม่สร้างชุด WHT"
            )
            return
        pit_account = self._get_wht_account("2102040104.101") or account

        existing_pit = self.search([("is_pit", "=", True)], limit=1)
        records = []
        for item in GOV_WHT_SET:
            vals = {k: v for k, v in item.items() if k != "xml_id"}
            vals["account_id"] = (
                pit_account.id if vals.get("is_pit") else account.id
            )
            if vals.get("is_pit") and existing_pit:
                xmlid_rec = self.env.ref(item["xml_id"], raise_if_not_found=False)
                if not xmlid_rec or xmlid_rec != existing_pit:
                    _logger.info(
                        "l10n_th_account_tax: มี PIT อยู่แล้ว (%s) — ไม่สร้างซ้ำ",
                        existing_pit.display_name,
                    )
                    continue
            records.append(
                {
                    "xml_id": item["xml_id"],
                    "noupdate": False,
                    "values": vals,
                }
            )
        if records:
            self._load_records(records)
            _logger.info(
                "l10n_th_account_tax: โหลดชุด WHT หน่วยงานรัฐ %s รายการ", len(records)
            )
