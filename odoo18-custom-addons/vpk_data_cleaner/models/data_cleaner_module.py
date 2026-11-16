# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import SQL

from .classification_rules import (
    MODEL_PROTECTION_NOTES,
    MODULE_THAI_LABELS,
    classify_model,
    get_module_group,
    is_excluded_model,
)

_logger = logging.getLogger(__name__)


class VpkDataCleanerModule(models.Model):
    _name = "vpk.data.cleaner.module"
    _description = "โมดูลสำหรับจัดการล้างข้อมูล"
    _order = "module_group_seq asc, technical_name asc"

    name = fields.Char(string="ชื่อโมดูล", required=True, index=True)
    technical_name = fields.Char(string="รหัสโมดูล (Technical Name)", required=True, index=True)
    ir_module_id = fields.Many2one(
        "ir.module.module",
        string="ข้อมูลโมดูลระบบ",
        ondelete="cascade",
        index=True,
    )
    module_group = fields.Selection(
        [
            ("vpk", "โมดูลเฉพาะ VPK (vpk_*)"),
            ("oca_th", "โมดูลภาครัฐไทย / OCA"),
            ("standard", "โมดูลมาตรฐาน Odoo"),
        ],
        string="กลุ่มโมดูล",
        required=True,
        default="standard",
        index=True,
    )
    module_group_seq = fields.Integer(string="ลำดับกลุ่ม", default=30, index=True)
    summary = fields.Char(string="คำอธิบายโมดูล")
    last_sync_at = fields.Datetime(string="อัปเดตข้อมูลล่าสุด", readonly=True)

    model_line_ids = fields.One2many(
        "vpk.data.cleaner.model",
        "cleaner_module_id",
        string="รายการโมเดลในโมดูลนี้",
    )
    transaction_model_ids = fields.One2many(
        "vpk.data.cleaner.model",
        "cleaner_module_id",
        domain=[("data_type", "=", "transaction")],
        string="โมเดลเก็บ Transaction",
    )
    master_model_ids = fields.One2many(
        "vpk.data.cleaner.model",
        "cleaner_module_id",
        domain=[("data_type", "=", "master")],
        string="โมเดลเก็บ Master Data",
    )

    total_model_count = fields.Integer(
        string="จำนวนโมเดลทั้งหมด",
        compute="_compute_stats",
        store=True,
    )
    transaction_model_count = fields.Integer(
        string="จำนวนโมเดล Transaction",
        compute="_compute_stats",
        store=True,
    )
    master_model_count = fields.Integer(
        string="จำนวนโมเดล Master",
        compute="_compute_stats",
        store=True,
    )
    transaction_record_count = fields.Integer(
        string="จำนวนแถว Transaction รวม",
        compute="_compute_stats",
        store=True,
    )
    master_record_count = fields.Integer(
        string="จำนวนแถว Master รวม",
        compute="_compute_stats",
        store=True,
    )
    total_record_count = fields.Integer(
        string="จำนวนแถวรวมทั้งหมด",
        compute="_compute_stats",
        store=True,
    )

    _sql_constraints = [
        (
            "technical_name_uniq",
            "unique(technical_name)",
            "รหัสโมดูลต้องไม่ซ้ำกัน",
        ),
    ]

    @api.depends(
        "model_line_ids.data_type",
        "model_line_ids.record_count",
    )
    def _compute_stats(self):
        for rec in self:
            tx_lines = rec.model_line_ids.filtered(lambda l: l.data_type == "transaction")
            ms_lines = rec.model_line_ids.filtered(lambda l: l.data_type == "master")
            tx_rows = sum(tx_lines.mapped("record_count"))
            ms_rows = sum(ms_lines.mapped("record_count"))
            rec.total_model_count = len(rec.model_line_ids)
            rec.transaction_model_count = len(tx_lines)
            rec.master_model_count = len(ms_lines)
            rec.transaction_record_count = tx_rows
            rec.master_record_count = ms_rows
            rec.total_record_count = tx_rows + ms_rows

    @api.model
    def _detect_parent_model(self, model_cls, model_name):
        """หาความสัมพันธ์ตารางแม่ (กรณีเป็นตารางลูก/บรรทัดรายการ)"""
        candidates = []
        for fname, field in model_cls._fields.items():
            if field.type != "many2one" or not getattr(field, "store", False):
                continue
            comodel = getattr(field, "comodel_name", None)
            if not comodel or comodel == model_name or comodel.startswith(("res.", "ir.", "uom.")):
                continue
            if getattr(field, "ondelete", "") == "cascade":
                if model_name.startswith(comodel + "."):
                    return comodel
                candidates.append(comodel)
            elif model_name.startswith(comodel + "."):
                candidates.append(comodel)
        return candidates[0] if candidates else False

    def action_sync_all(self):
        """สแกนโมดูลและโมเดลที่ติดตั้งจริงทั้งหมด จำแนก Master / Transaction และนับจำนวนแถวสด"""
        cr = self.env.cr
        now = fields.Datetime.now()

        # 1) ดึงรายชื่อตารางจริงใน PostgreSQL
        cr.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        existing_tables = {row[0] for row in cr.fetchall()}

        # 2) ดึงโมดูลต้นสังกัดของแต่ละ ir.model จาก ir_model_data
        cr.execute(
            """
            SELECT DISTINCT ON (imd.res_id)
                imd.res_id,
                imd.module
            FROM ir_model_data imd
            JOIN ir_module_module mm ON mm.name = imd.module AND mm.state = 'installed'
            WHERE imd.model = 'ir.model'
            ORDER BY imd.res_id, imd.id ASC
            """
        )
        origin_by_model_id = dict(cr.fetchall())

        installed_modules = {
            m.name: m
            for m in self.env["ir.module.module"].sudo().search([("state", "=", "installed")])
        }

        existing_mod_recs = {
            m.technical_name: m for m in self.sudo().search([])
        }
        existing_model_recs = {
            m.model_name: m for m in self.env["vpk.data.cleaner.model"].sudo().search([])
        }

        seen_modules = set()
        seen_models = set()

        ir_models = self.env["ir.model"].sudo().search([("transient", "=", False)], order="model asc")
        group_seq_map = {"vpk": 10, "oca_th": 20, "standard": 30}

        for ir_mod in ir_models:
            model_name = ir_mod.model
            if model_name not in self.env:
                continue
            model_cls = self.env[model_name]
            if (
                getattr(model_cls, "_abstract", False)
                or getattr(model_cls, "_transient", False)
                or not getattr(model_cls, "_auto", True)
            ):
                continue

            table_name = getattr(model_cls, "_table", None)
            if not table_name or table_name not in existing_tables:
                continue

            origin_module = origin_by_model_id.get(ir_mod.id)
            if not origin_module:
                # fallback จาก _original_module
                origin_module = getattr(model_cls, "_original_module", None) or "base"
            if origin_module not in installed_modules:
                continue
            if is_excluded_model(model_name, origin_module):
                continue

            mm = installed_modules[origin_module]
            mod_group = get_module_group(origin_module)
            mod_label = MODULE_THAI_LABELS.get(origin_module) or mm.shortdesc or origin_module
            display_mod_name = f"{mod_label} [{origin_module}]"

            mod_vals = {
                "name": display_mod_name,
                "technical_name": origin_module,
                "ir_module_id": mm.id,
                "module_group": mod_group,
                "module_group_seq": group_seq_map.get(mod_group, 30),
                "summary": mm.summary or mm.shortdesc or "",
                "last_sync_at": now,
            }
            if origin_module in existing_mod_recs:
                cleaner_mod = existing_mod_recs[origin_module]
                cleaner_mod.write(mod_vals)
            else:
                cleaner_mod = self.sudo().create(mod_vals)
                existing_mod_recs[origin_module] = cleaner_mod
            seen_modules.add(cleaner_mod.id)

            # นับจำนวนแถวจริงในตาราง
            cr.execute(SQL("SELECT COUNT(*) FROM %s", SQL.identifier(table_name)))
            row_count = cr.fetchone()[0] or 0

            default_type, reason = classify_model(model_name, model_cls._fields.keys())
            parent_model = self._detect_parent_model(model_cls, model_name)
            protect_note = MODEL_PROTECTION_NOTES.get(model_name, False)

            model_label = ir_mod.with_context(lang="th_TH").name or ir_mod.name or model_name
            model_vals = {
                "cleaner_module_id": cleaner_mod.id,
                "ir_model_id": ir_mod.id,
                "name": model_label,
                "model_name": model_name,
                "table_name": table_name,
                "parent_model_name": parent_model,
                "record_count": row_count,
                "protect_note": protect_note,
            }
            if model_name in existing_model_recs:
                rec_line = existing_model_recs[model_name]
                if not rec_line.is_type_overridden:
                    model_vals["data_type"] = default_type
                    model_vals["classification_reason"] = reason
                rec_line.with_context(syncing_cleaner=True).write(model_vals)
            else:
                model_vals["data_type"] = default_type
                model_vals["classification_reason"] = reason
                rec_line = (
                    self.env["vpk.data.cleaner.model"]
                    .sudo()
                    .with_context(syncing_cleaner=True)
                    .create(model_vals)
                )
                existing_model_recs[model_name] = rec_line
            seen_models.add(rec_line.id)

        # ลบรายการเก่าของโมดูล/โมเดลที่ถอนการติดตั้งแล้ว
        stale_models = self.env["vpk.data.cleaner.model"].sudo().search([("id", "not in", list(seen_models))])
        if stale_models:
            stale_models.unlink()
        stale_modules = self.sudo().search([("id", "not in", list(seen_modules))])
        if stale_modules:
            stale_modules.unlink()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("ซิงค์ข้อมูลสำเร็จ"),
                "message": _("อัปเดตข้อมูล %d โมดูล (%d โมเดล) เรียบร้อยแล้ว")
                % (len(seen_modules), len(seen_models)),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def action_refresh_module_counts(self):
        """อัปเดตจำนวนแถวเฉพาะโมดูลที่เปิดอยู่"""
        for rec in self:
            rec.model_line_ids._refresh_record_counts()
            rec.last_sync_at = fields.Datetime.now()
        return True

    def action_view_module_models(self):
        """เปิดหน้ารายการโมเดลทั้งหมดของโมดูลนี้"""
        self.ensure_one()
        self.action_refresh_module_counts()
        return {
            "type": "ir.actions.act_window",
            "name": _("โมเดลใน %s") % self.name,
            "res_model": "vpk.data.cleaner.model",
            "view_mode": "list,form",
            "domain": [("cleaner_module_id", "=", self.id)],
            "context": {
                "default_cleaner_module_id": self.id,
                "search_default_group_data_type": 1,
            },
        }

    def action_open_clear_transactions_wizard(self):
        """เปิดหน้าต่างยืนยันล้างเฉพาะโมเดลประเภท Transaction ของโมดูลที่เลือก"""
        self.action_refresh_module_counts()
        tx_models = self.mapped("model_line_ids").filtered(
            lambda m: m.data_type == "transaction"
        )
        if not tx_models:
            raise UserError(_("โมดูลที่เลือกไม่มีโมเดลประเภท Transaction"))
        return tx_models.action_open_clear_wizard()

    def action_open_clear_all_wizard(self):
        """เปิดหน้าต่างเลือกล้างข้อมูลทั้งหมด (ทั้ง Transaction และ Master) ในโมดูลนี้"""
        self.action_refresh_module_counts()
        models_to_clear = self.mapped("model_line_ids")
        if not models_to_clear:
            raise UserError(_("ไม่พบรายการโมเดลในโมดูลนี้"))
        return models_to_clear.action_open_clear_wizard()

    def action_open_discuss_cleaner(self):
        """เปิดหน้าต่างเฉพาะสำหรับล้างข้อความและการแจ้งเตือนในแชท (Discuss)"""
        return self.env.ref("vpk_data_cleaner.action_vpk_discuss_cleaner_wizard").read()[0]
