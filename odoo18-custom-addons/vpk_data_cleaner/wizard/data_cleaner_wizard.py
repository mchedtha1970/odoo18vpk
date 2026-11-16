# -*- coding: utf-8 -*-
import logging
from collections import defaultdict, deque

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..models.classification_rules import is_excluded_model

_logger = logging.getLogger(__name__)


class VpkDataCleanerWizard(models.TransientModel):
    _name = "vpk.data.cleaner.wizard"
    _description = "หน้าต่างยืนยันการล้างข้อมูลโมเดล"

    line_ids = fields.One2many(
        "vpk.data.cleaner.wizard.line",
        "wizard_id",
        string="รายการโมเดลที่จะล้างข้อมูล",
    )
    selected_model_count = fields.Integer(
        string="จำนวนโมเดลที่เลือก",
        compute="_compute_summary",
    )
    selected_tx_count = fields.Integer(
        string="โมเดล Transaction",
        compute="_compute_summary",
    )
    selected_master_count = fields.Integer(
        string="โมเดล Master",
        compute="_compute_summary",
    )
    estimated_row_count = fields.Integer(
        string="จำนวนแถวที่จะถูกลบประมาณการ",
        compute="_compute_summary",
    )
    has_master_selected = fields.Boolean(
        string="มี Master ถูกเลือก",
        compute="_compute_summary",
    )

    clean_related_chatter = fields.Boolean(
        string="ลบประวัติแชท กิจกรรม สายอนุมัติ และไฟล์แนบของรายการที่ลบด้วย",
        default=True,
        help="ลบ mail.message, mail.activity, mail.followers, ir.attachment, tier.review และ vpk.approval.line ที่ผูกกับเรคคอร์ดที่ถูกลบ",
    )
    force_sql_delete = fields.Boolean(
        string="บังคับลบด้วย SQL หากสถานะเอกสารล็อกไม่ให้ลบผ่าน ORM (เช่น ยืนยันแล้ว / Posted / Done)",
        default=True,
    )
    reset_sequences = fields.Boolean(
        string="รีเซ็ตเลขรันเอกสารอัตโนมัติ (ir.sequence) ของโมดูลที่ล้างกลับเป็น 1",
        default=False,
    )
    confirm_master_delete = fields.Boolean(
        string="ข้าพเจ้ารับทราบว่ามีโมเดลประเภท Master Data รวมอยู่ด้วย และยืนยันที่จะลบ",
        default=False,
    )
    confirm_text = fields.Char(
        string="พิมพ์คำว่า CLEAR เพื่อยืนยัน",
    )

    @api.depends("line_ids.is_selected", "line_ids.data_type", "line_ids.record_count")
    def _compute_summary(self):
        for wiz in self:
            selected = wiz.line_ids.filtered("is_selected")
            tx = selected.filtered(lambda l: l.data_type == "transaction")
            ms = selected.filtered(lambda l: l.data_type == "master")
            wiz.selected_model_count = len(selected)
            wiz.selected_tx_count = len(tx)
            wiz.selected_master_count = len(ms)
            wiz.estimated_row_count = sum(selected.mapped("record_count"))
            wiz.has_master_selected = bool(ms)

    @api.model
    def create_from_models(self, cleaner_models):
        """สร้างรายการใน Wizard พร้อมดึงตารางลูก (Lines) ที่ผูกกับโมเดลที่เลือกมาให้อัตโนมัติ"""
        ModelCatalog = self.env["vpk.data.cleaner.model"].sudo()
        selected_names = set(cleaner_models.mapped("model_name"))

        # ดึงตารางลูกที่ parent_model_name อยู่ในรายการที่เลือก (เฉพาะประเภทเดียวกันหรือตารางลูกของเอกสาร)
        extra_children = ModelCatalog.search(
            [
                ("parent_model_name", "in", list(selected_names)),
                ("id", "not in", cleaner_models.ids),
            ]
        )
        extra_children._refresh_record_counts()

        all_models = cleaner_models | extra_children
        lines_vals = []
        for m in all_models.sorted(key=lambda r: (r.cleaner_module_id.technical_name, r.data_type != "transaction", r.model_name)):
            lines_vals.append(
                (
                    0,
                    0,
                    {
                        "is_selected": True,
                        "cleaner_model_id": m.id,
                        "cleaner_module_id": m.cleaner_module_id.id,
                        "model_name": m.model_name,
                        "name": m.name,
                        "table_name": m.table_name,
                        "data_type": m.data_type,
                        "record_count": m.record_count,
                        "is_auto_child": m.id in extra_children.ids,
                        "protect_note": m.protect_note,
                    },
                )
            )
        return self.create({"line_ids": lines_vals})

    def action_select_only_transactions(self):
        """ปุ่มลัด: ติ๊กเลือกเฉพาะ Transaction และเอา Master ออกทั้งหมด"""
        self.ensure_one()
        for line in self.line_ids:
            line.is_selected = line.data_type == "transaction"
        return {
            "type": "ir.actions.act_window",
            "name": _("ยืนยันการล้างข้อมูล (Clear Model Data)"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_protected_ids(self, model_name):
        """คืนชุด ID ที่ต้องห้ามลบเพื่อรักษาเสถียรภาพของระบบ Odoo"""
        cr = self.env.cr
        protected = set()
        if model_name == "res.partner":
            protected.update({1, 2, 3})
            cr.execute("SELECT partner_id FROM res_company WHERE partner_id IS NOT NULL")
            protected.update(r[0] for r in cr.fetchall())
            cr.execute("SELECT partner_id FROM res_users WHERE partner_id IS NOT NULL")
            protected.update(r[0] for r in cr.fetchall())
            if protected:
                cr.execute(
                    "SELECT commercial_partner_id FROM res_partner WHERE id = ANY(%s) AND commercial_partner_id IS NOT NULL",
                    (list(protected),),
                )
                protected.update(r[0] for r in cr.fetchall())
        elif model_name == "res.partner.bank":
            cr.execute(
                """
                SELECT b.id
                FROM res_partner_bank b
                JOIN res_company c ON c.partner_id = b.partner_id
                """
            )
            protected.update(r[0] for r in cr.fetchall())
        elif model_name == "stock.location":
            cr.execute(
                """
                SELECT l.id
                FROM stock_location l
                LEFT JOIN ir_model_data imd
                  ON imd.model = 'stock.location' AND imd.res_id = l.id AND imd.module = 'stock'
                WHERE l.usage != 'internal' OR imd.id IS NOT NULL
                """
            )
            protected.update(r[0] for r in cr.fetchall())
        elif model_name == "discuss.channel":
            cr.execute(
                """
                SELECT res_id
                FROM ir_model_data
                WHERE model = 'discuss.channel'
                """
            )
            protected.update(r[0] for r in cr.fetchall())
        elif model_name == "discuss.channel.member":
            cr.execute(
                """
                SELECT m.id
                FROM discuss_channel_member m
                JOIN ir_model_data imd
                  ON imd.model = 'discuss.channel' AND imd.res_id = m.channel_id
                """
            )
            protected.update(r[0] for r in cr.fetchall())
        return protected

    def _sort_lines_child_first(self, selected_lines):
        """เรียงลำดับตารางลูกให้ลบก่อนตารางแม่ตาม Foreign Key จริงใน PostgreSQL"""
        cr = self.env.cr
        table_to_line = {l.table_name: l for l in selected_lines if l.table_name}
        tables = list(table_to_line.keys())
        if len(tables) <= 1:
            return list(selected_lines)

        # หากตาราง A มี FK ชี้ไปหาตาราง B -> ต้องลบ A ก่อน B (edge: A -> B)
        cr.execute(
            """
            SELECT DISTINCT
                c_src.relname AS child_table,
                c_tgt.relname AS parent_table
            FROM pg_constraint con
            JOIN pg_class c_src ON c_src.oid = con.conrelid
            JOIN pg_class c_tgt ON c_tgt.oid = con.confrelid
            JOIN pg_namespace ns ON ns.oid = c_src.relnamespace
            WHERE con.contype = 'f'
              AND ns.nspname = 'public'
              AND c_src.relname = ANY(%s)
              AND c_tgt.relname = ANY(%s)
              AND c_src.relname <> c_tgt.relname
            """,
            (tables, tables),
        )
        adj = defaultdict(set)
        indegree = {t: 0 for t in tables}
        for child_t, parent_t in cr.fetchall():
            if parent_t not in adj[child_t]:
                adj[child_t].add(parent_t)
                indegree[parent_t] += 1

        queue = deque(sorted([t for t, deg in indegree.items() if deg == 0]))
        ordered_tables = []
        while queue:
            curr = queue.popleft()
            ordered_tables.append(curr)
            for nxt in sorted(adj[curr]):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

        # กรณีมี FK วงกลมระหว่างกัน (เช่น account_move <-> account_payment) ให้ต่อท้ายตารางที่เหลือ
        remaining = [t for t in tables if t not in ordered_tables]
        ordered_tables.extend(sorted(remaining))
        return [table_to_line[t] for t in ordered_tables]

    def _break_nullable_fks_to_target(self, tgt_table, tgt_ids, batch_tables):
        """ปลด FK ที่ยอมให้เป็น NULL จากตารางในชุดที่จะลบซึ่งชี้มายัง tgt_table ก่อนลบด้วย SQL"""
        if not tgt_ids or not batch_tables:
            return
        cr = self.env.cr
        cr.execute(
            """
            SELECT
                c_src.relname AS src_table,
                a_src.attname AS src_col
            FROM pg_constraint con
            JOIN pg_class c_src ON c_src.oid = con.conrelid
            JOIN pg_class c_tgt ON c_tgt.oid = con.confrelid
            JOIN pg_namespace ns ON ns.oid = c_src.relnamespace
            JOIN pg_attribute a_src ON a_src.attrelid = c_src.oid AND a_src.attnum = con.conkey[1]
            WHERE con.contype = 'f'
              AND array_length(con.conkey, 1) = 1
              AND ns.nspname = 'public'
              AND c_src.relname = ANY(%s)
              AND c_tgt.relname = %s
              AND NOT a_src.attnotnull
            """,
            (batch_tables, tgt_table),
        )
        for src_table, src_col in cr.fetchall():
            cr.execute(
                SQL(
                    "UPDATE %s SET %s = NULL WHERE %s = ANY(%s)",
                    SQL.identifier(src_table),
                    SQL.identifier(src_col),
                    SQL.identifier(src_col),
                    tgt_ids,
                )
            )

    def _check_external_blocking_fks(self, table_name, target_ids, batch_tables):
        """ตรวจว่ามีตารางโมเดลอื่นนอกรายการที่เลือกอ้างอิงอยู่แบบ RESTRICT/NO ACTION หรือไม่ และล้างตาราง M2M กลาง"""
        cr = self.env.cr
        if not target_ids:
            return []

        cr.execute(
            """
            SELECT
                c_src.relname AS ref_table,
                a_src.attname AS ref_col,
                con.confdeltype
            FROM pg_constraint con
            JOIN pg_class c_src ON c_src.oid = con.conrelid
            JOIN pg_class c_tgt ON c_tgt.oid = con.confrelid
            JOIN pg_namespace ns ON ns.oid = c_src.relnamespace
            JOIN pg_attribute a_src ON a_src.attrelid = c_src.oid AND a_src.attnum = con.conkey[1]
            WHERE con.contype = 'f'
              AND array_length(con.conkey, 1) = 1
              AND ns.nspname = 'public'
              AND c_tgt.relname = %s
            """,
            (table_name,),
        )
        refs = cr.fetchall()

        # รายชื่อตารางที่เป็นโมเดลจริงใน Odoo
        all_model_tables = {}
        for m in self.env["ir.model"].sudo().search([("transient", "=", False)]):
            if m.model in self.env:
                t = getattr(self.env[m.model], "_table", None)
                if t:
                    all_model_tables[t] = (m.model, m.with_context(lang="th_TH").name or m.name)

        blockers = []
        for ref_table, ref_col, confdeltype in refs:
            if ref_table in batch_tables:
                continue

            # หากเป็นตารางเชื่อม Many2many (ไม่ใช่ตารางโมเดลหลัก) ให้ลบแถวเชื่อมออกได้เลย
            if ref_table not in all_model_tables:
                cr.execute(
                    SQL(
                        "DELETE FROM %s WHERE %s = ANY(%s)",
                        SQL.identifier(ref_table),
                        SQL.identifier(ref_col),
                        target_ids,
                    )
                )
                continue

            # หากตั้งเป็น ON DELETE CASCADE ('c') หรือ SET NULL ('n') PostgreSQL จัดการให้อัตโนมัติ
            if confdeltype in ("c", "n", b"c", b"n"):
                continue

            cr.execute(
                SQL(
                    "SELECT COUNT(*) FROM %s WHERE %s = ANY(%s)",
                    SQL.identifier(ref_table),
                    SQL.identifier(ref_col),
                    target_ids,
                )
            )
            cnt = cr.fetchone()[0] or 0
            if cnt > 0:
                ref_model, ref_label = all_model_tables[ref_table]
                blockers.append(f"• {ref_label} ({ref_model}) — {cnt:,} รายการ")
        return blockers

    def _clean_polymorphic_links(self, model_name, target_ids):
        """ลบข้อความแชท ไฟล์แนบ กิจกรรม และสายอนุมัติที่ผูกกับเรคคอร์ดที่ถูกลบ"""
        if not target_ids:
            return
        cr = self.env.cr

        # ลบไฟล์แนบผ่าน ORM เพื่อให้ไฟล์ใน filestore สะอาดด้วย
        attachments = (
            self.env["ir.attachment"]
            .sudo()
            .search([("res_model", "=", model_name), ("res_id", "in", target_ids)])
        )
        if attachments:
            attachments.unlink()

        if model_name != "mail.message":
            cr.execute(
                "SELECT id FROM mail_message WHERE model = %s AND res_id = ANY(%s)",
                (model_name, target_ids),
            )
            msg_ids = [r[0] for r in cr.fetchall()]
            if msg_ids:
                cr.execute("DELETE FROM mail_tracking_value WHERE mail_message_id = ANY(%s)", (msg_ids,))
                cr.execute("DELETE FROM mail_notification WHERE mail_message_id = ANY(%s)", (msg_ids,))
                cr.execute("DELETE FROM mail_message_reaction WHERE message_id = ANY(%s)", (msg_ids,))
                cr.execute("DELETE FROM mail_message WHERE id = ANY(%s)", (msg_ids,))

        cr.execute("DELETE FROM mail_followers WHERE res_model = %s AND res_id = ANY(%s)", (model_name, target_ids))
        cr.execute("DELETE FROM mail_activity WHERE res_model = %s AND res_id = ANY(%s)", (model_name, target_ids))

        cr.execute("SELECT to_regclass('public.tier_review')")
        if cr.fetchone()[0]:
            cr.execute("DELETE FROM tier_review WHERE model = %s AND res_id = ANY(%s)", (model_name, target_ids))

        cr.execute("SELECT to_regclass('public.vpk_approval_line')")
        if cr.fetchone()[0]:
            cr.execute("DELETE FROM vpk_approval_line WHERE res_model = %s AND res_id = ANY(%s)", (model_name, target_ids))

    def _reset_module_sequences(self, module_names, model_names):
        """รีเซ็ตเลขรันเอกสาร (ir.sequence) ของโมดูล/โมเดลที่ล้างกลับเป็น 1"""
        cr = self.env.cr
        seq_ids = set()
        if module_names:
            cr.execute(
                """
                SELECT res_id
                FROM ir_model_data
                WHERE model = 'ir.sequence' AND module = ANY(%s)
                """,
                (list(module_names),),
            )
            seq_ids.update(r[0] for r in cr.fetchall())
        if model_names:
            seqs = self.env["ir.sequence"].sudo().search([("code", "in", list(model_names))])
            seq_ids.update(seqs.ids)

        if not seq_ids:
            return 0
        sequences = self.env["ir.sequence"].sudo().browse(list(seq_ids)).exists()
        sequences.write({"number_next": 1})
        date_ranges = self.env["ir.sequence.date_range"].sudo().search([("sequence_id", "in", sequences.ids)])
        if date_ranges:
            date_ranges.write({"number_next": 1})
        return len(sequences)

    def action_execute_clear(self):
        """ดำเนินการล้างข้อมูลตามรายการที่เลือกอย่างปลอดภัย"""
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("เฉพาะผู้ดูแลระบบสูงสุด (System Administrator) เท่านั้นที่สามารถล้างข้อมูลได้"))

        selected_lines = self.line_ids.filtered("is_selected")
        if not selected_lines:
            raise UserError(_("กรุณาเลือกอย่างน้อย 1 โมเดลที่ต้องการล้างข้อมูล"))

        if (self.confirm_text or "").strip().upper() != "CLEAR":
            raise UserError(_("กรุณาพิมพ์คำว่า CLEAR ในช่องยืนยันก่อนดำเนินการลบข้อมูล"))

        if self.has_master_selected and not self.confirm_master_delete:
            raise UserError(
                _("รายการที่เลือกมีโมเดลประเภท Master Data รวมอยู่ด้วย กรุณาติ๊กช่องยืนยันการลบ Master Data ก่อนดำเนินการ")
            )

        ordered_lines = self._sort_lines_child_first(selected_lines)
        batch_tables = [l.table_name for l in ordered_lines if l.table_name]

        env_clean = self.env(
            context=dict(
                self.env.context,
                active_test=False,
                tracking_disable=True,
                mail_notrack=True,
                force_delete=True,
                _force_unlink=True,
            )
        )
        cr = env_clean.cr

        # เตรียมชุด ID ที่ลบได้ของแต่ละตารางก่อน
        target_ids_by_table = {}
        for line in ordered_lines:
            m_name = line.model_name
            origin_mod = line.cleaner_module_id.technical_name
            if is_excluded_model(m_name, origin_mod) or m_name not in env_clean:
                continue
            cr.execute(SQL("SELECT id FROM %s", SQL.identifier(line.table_name)))
            all_ids = [r[0] for r in cr.fetchall()]
            protected_ids = self._get_protected_ids(m_name)
            safe_ids = [rid for rid in all_ids if rid not in protected_ids]
            target_ids_by_table[line.table_name] = safe_ids

        # ตรวจการอ้างอิงจากตารางภายนอกล่วงหน้า หากเปิดบังคับ SQL
        all_blockers = []
        for line in ordered_lines:
            t_ids = target_ids_by_table.get(line.table_name) or []
            if not t_ids:
                continue
            blockers = self._check_external_blocking_fks(line.table_name, t_ids, batch_tables)
            if blockers:
                all_blockers.append(
                    f"โมเดล {line.name} ({line.model_name}) ยังถูกอ้างอิงโดย:\n" + "\n".join(blockers)
                )
        if all_blockers:
            raise UserError(
                _(
                    "ไม่สามารถลบข้อมูลได้ เนื่องจากยังมีข้อมูลในโมเดลอื่นอ้างอิงอยู่:\n\n%s\n\n"
                    "คำแนะนำ: กรุณาเลือกล้างข้อมูลในโมเดลปลายทางที่อ้างอิงข้างต้นก่อน หรือเลือกพร้อมกันในรอบเดียว"
                )
                % ("\n\n".join(all_blockers))
            )

        now = fields.Datetime.now()
        total_deleted = 0
        cleared_model_names = set()
        cleared_module_names = set()
        log_entries = []

        for line in ordered_lines:
            m_name = line.model_name
            if m_name not in env_clean:
                continue
            # อ่าน ID ที่ยังเหลืออยู่จริง (เผื่อถูกลบไปพร้อม cascade ของตารางก่อนหน้าแล้ว)
            cr.execute(SQL("SELECT id FROM %s", SQL.identifier(line.table_name)))
            current_ids = [r[0] for r in cr.fetchall()]
            protected_ids = self._get_protected_ids(m_name)
            ids_to_delete = [rid for rid in current_ids if rid not in protected_ids]

            initial_target_count = len(target_ids_by_table.get(line.table_name) or [])
            if not ids_to_delete:
                if initial_target_count > 0:
                    log_entries.append(
                        f"[{line.cleaner_module_id.technical_name}] {m_name} ({line.data_type.upper()}): ลบอัตโนมัติผ่าน Cascade {initial_target_count:,} แถว"
                    )
                    total_deleted += initial_target_count
                else:
                    log_entries.append(
                        f"[{line.cleaner_module_id.technical_name}] {m_name} ({line.data_type.upper()}): ไม่มีข้อมูลให้ลบ (0 แถว)"
                    )
                line.cleaner_model_id.sudo().write(
                    {
                        "record_count": len(current_ids),
                        "last_cleared_at": now,
                        "last_cleared_by": self.env.user.id,
                    }
                )
                cleared_model_names.add(m_name)
                cleared_module_names.add(line.cleaner_module_id.technical_name)
                continue

            if self.clean_related_chatter:
                self._clean_polymorphic_links(m_name, ids_to_delete)

            recs = env_clean[m_name].sudo().browse(ids_to_delete).exists()
            deleted_count = len(ids_to_delete)
            method_used = "ORM"

            # ลองยกเลิกสถานะและลบผ่าน ORM ก่อน
            orm_ok = False
            try:
                with cr.savepoint():
                    for cancel_fn in ("button_cancel", "action_cancel", "button_draft", "action_draft"):
                        if hasattr(recs, cancel_fn):
                            try:
                                with cr.savepoint():
                                    getattr(recs, cancel_fn)()
                            except Exception:
                                pass
                    recs.unlink()
                    orm_ok = True
            except Exception as exc:
                if not self.force_sql_delete:
                    raise UserError(
                        _("ลบโมเดล %s ผ่าน ORM ไม่สำเร็จ: %s\n(หากต้องการบังคับลบ ให้เปิด 'บังคับลบด้วย SQL')")
                        % (m_name, str(exc))
                    ) from exc

            if not orm_ok:
                method_used = "SQL"
                env_clean.invalidate_all()
                self._break_nullable_fks_to_target(line.table_name, ids_to_delete, batch_tables)
                cr.execute(
                    SQL(
                        "DELETE FROM %s WHERE id = ANY(%s)",
                        SQL.identifier(line.table_name),
                        ids_to_delete,
                    )
                )

            cr.execute(SQL("SELECT COUNT(*) FROM %s", SQL.identifier(line.table_name)))
            remaining_count = cr.fetchone()[0] or 0

            line.cleaner_model_id.sudo().write(
                {
                    "record_count": remaining_count,
                    "last_cleared_at": now,
                    "last_cleared_by": self.env.user.id,
                }
            )
            total_deleted += deleted_count
            cleared_model_names.add(m_name)
            cleared_module_names.add(line.cleaner_module_id.technical_name)
            note_suffix = f" (คงข้อมูลระบบไว้ {remaining_count} แถว)" if remaining_count else ""
            log_entries.append(
                f"[{line.cleaner_module_id.technical_name}] {m_name} ({line.data_type.upper()}): ลบสำเร็จ {deleted_count:,} แถว [{method_used}]{note_suffix}"
            )

        # กรณีล้างใบเช็ค (vpk.bank.cheque.leaf) โดยไม่ได้ล้างสมุดเช็ค (vpk.bank.cheque.book) ให้สร้างใบเช็คเปล่ากลับมาใหม่
        if (
            "vpk.bank.cheque.leaf" in cleared_model_names
            and "vpk.bank.cheque.book" not in cleared_model_names
            and "vpk.bank.cheque.book" in env_clean
        ):
            books = env_clean["vpk.bank.cheque.book"].sudo().search([])
            if books and hasattr(books, "_generate_leaves"):
                books._generate_leaves()
                leaf_mod = self.env["vpk.data.cleaner.model"].sudo().search([("model_name", "=", "vpk.bank.cheque.leaf")], limit=1)
                if leaf_mod:
                    leaf_mod._refresh_record_counts()

        # หากมีการล้าง mail.message หรือ discuss.channel ให้รีเซ็ตตัวนับข้อความยังไม่อ่านในห้องแชทด้วย
        if {"mail.message", "discuss.channel", "mail.notification"} & cleared_model_names:
            cr.execute(
                """
                UPDATE discuss_channel_member
                SET seen_message_id = NULL,
                    fetched_message_id = NULL,
                    new_message_separator = 0
                """
            )
            cr.execute("DELETE FROM bus_bus")

        reset_seq_count = 0
        if self.reset_sequences:
            reset_seq_count = self._reset_module_sequences(cleared_module_names, cleared_model_names)
            if reset_seq_count:
                log_entries.append(f"รีเซ็ตเลขรันเอกสาร (ir.sequence) จำนวน {reset_seq_count} รายการกลับเป็น 1")

        env_clean.invalidate_all()

        # อัปเดตตัวเลขทุกโมเดลในโมดูลที่เกี่ยวข้อง
        affected_modules = selected_lines.mapped("cleaner_module_id")
        affected_modules.action_refresh_module_counts()

        log_rec = self.env["vpk.data.cleaner.log"].sudo().create(
            {
                "name": _("ล้างข้อมูล %d โมเดล (%s)") % (len(ordered_lines), ", ".join(sorted(cleared_module_names))),
                "executed_at": now,
                "user_id": self.env.user.id,
                "database_name": cr.dbname,
                "module_names": ", ".join(sorted(cleared_module_names)),
                "model_count": len(ordered_lines),
                "deleted_row_count": total_deleted,
                "included_master": self.has_master_selected,
                "reset_sequences": bool(reset_seq_count),
                "detail_log": "\n".join(log_entries),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("ผลการล้างข้อมูลสำเร็จ"),
            "res_model": "vpk.data.cleaner.log",
            "res_id": log_rec.id,
            "view_mode": "form",
            "target": "current",
        }


class VpkDataCleanerWizardLine(models.TransientModel):
    _name = "vpk.data.cleaner.wizard.line"
    _description = "รายการโมเดลในหน้าต่างยืนยันการล้างข้อมูล"
    _order = "cleaner_module_id asc, data_type desc, model_name asc"

    wizard_id = fields.Many2one(
        "vpk.data.cleaner.wizard",
        required=True,
        ondelete="cascade",
    )
    is_selected = fields.Boolean(string="เลือก", default=True)
    cleaner_module_id = fields.Many2one(
        "vpk.data.cleaner.module",
        string="โมดูล",
        readonly=True,
    )
    cleaner_model_id = fields.Many2one(
        "vpk.data.cleaner.model",
        string="โมเดลอ้างอิง",
        readonly=True,
    )
    name = fields.Char(string="ชื่อโมเดล", readonly=True)
    model_name = fields.Char(string="ชื่อเทคนิค (Model)", readonly=True)
    table_name = fields.Char(string="ตาราง (Table)", readonly=True)
    data_type = fields.Selection(
        [
            ("transaction", "Transaction"),
            ("master", "Master"),
        ],
        string="ประเภท",
        readonly=True,
    )
    record_count = fields.Integer(string="จำนวนแถวปัจจุบัน", readonly=True)
    is_auto_child = fields.Boolean(string="ตารางลูกอัตโนมัติ", readonly=True)
    protect_note = fields.Char(string="หมายเหตุความปลอดภัย", readonly=True)
