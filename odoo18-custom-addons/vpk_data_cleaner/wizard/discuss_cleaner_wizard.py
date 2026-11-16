# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VpkDiscussCleanerWizard(models.TransientModel):
    _name = "vpk.discuss.cleaner.wizard"
    _description = "ล้างข้อความและการแจ้งเตือนในแชท (Discuss)"

    clear_channel_messages = fields.Boolean(
        string="ล้างข้อความแชทในทุกห้องสนทนาและแชทส่วนตัว (Channel & Direct Messages)",
        default=True,
    )
    clear_inbox_notifications = fields.Boolean(
        string="ล้างกล่องจดหมาย (Inbox) รายการติดดาว (Starred) และประวัติแจ้งเตือน (History)",
        default=True,
    )
    clear_dm_channels = fields.Boolean(
        string="ลบห้องสนทนาส่วนตัวและกลุ่มแชทย่อย (คงห้องหลัก #general และ #Administrators ไว้)",
        default=True,
    )
    clear_activities = fields.Boolean(
        string="ล้างรายการกิจกรรมแจ้งเตือนค้าง (Pending Activities)",
        default=True,
    )
    clear_outgoing_mails = fields.Boolean(
        string="ล้างคิวและประวัติอีเมลขาออก (mail.mail)",
        default=True,
    )
    clear_all_document_chatter = fields.Boolean(
        string="ล้างประวัติข้อความท้ายเอกสารทั้งหมดในระบบด้วย (Document Chatter ทุกโมเดล)",
        default=False,
        help="หากเปิดไว้ ระบบจะลบประวัติบันทึกท้ายเอกสาร (เช่น สร้างเอกสาร/เปลี่ยนสถานะ) ของทุกโมเดลด้วย",
    )

    channel_message_count = fields.Integer(
        string="ข้อความในห้องแชท",
        compute="_compute_live_counts",
    )
    inbox_notification_count = fields.Integer(
        string="การแจ้งเตือนในกล่องจดหมาย/ประวัติ",
        compute="_compute_live_counts",
    )
    dm_channel_count = fields.Integer(
        string="ห้องแชทส่วนตัว/กลุ่มย่อย",
        compute="_compute_live_counts",
    )
    activity_count = fields.Integer(
        string="กิจกรรมแจ้งเตือนค้าง",
        compute="_compute_live_counts",
    )
    outgoing_mail_count = fields.Integer(
        string="อีเมลขาออก",
        compute="_compute_live_counts",
    )
    document_chatter_count = fields.Integer(
        string="ข้อความท้ายเอกสารทั้งหมด",
        compute="_compute_live_counts",
    )

    confirm_text = fields.Char(string="พิมพ์คำว่า CLEAR เพื่อยืนยัน")

    def _get_protected_channel_ids(self):
        self.env.cr.execute(
            "SELECT res_id FROM ir_model_data WHERE model = 'discuss.channel'"
        )
        return [r[0] for r in self.env.cr.fetchall()]

    @api.depends(
        "clear_channel_messages",
        "clear_inbox_notifications",
        "clear_dm_channels",
        "clear_activities",
        "clear_outgoing_mails",
        "clear_all_document_chatter",
    )
    def _compute_live_counts(self):
        cr = self.env.cr
        protected_ch = self._get_protected_channel_ids() or [0]

        cr.execute("SELECT COUNT(*) FROM mail_message WHERE model = 'discuss.channel'")
        ch_msg_cnt = cr.fetchone()[0] or 0

        cr.execute("SELECT COUNT(*) FROM mail_notification")
        notif_cnt = cr.fetchone()[0] or 0
        cr.execute("SELECT COUNT(*) FROM mail_message_res_partner_starred_rel")
        star_cnt = cr.fetchone()[0] or 0

        cr.execute(
            "SELECT COUNT(*) FROM discuss_channel WHERE id <> ALL(%s)",
            (protected_ch,),
        )
        dm_cnt = cr.fetchone()[0] or 0

        cr.execute("SELECT COUNT(*) FROM mail_activity")
        act_cnt = cr.fetchone()[0] or 0

        cr.execute("SELECT COUNT(*) FROM mail_mail")
        mail_cnt = cr.fetchone()[0] or 0

        cr.execute(
            "SELECT COUNT(*) FROM mail_message WHERE COALESCE(model, '') <> 'discuss.channel'"
        )
        doc_msg_cnt = cr.fetchone()[0] or 0

        for wiz in self:
            wiz.channel_message_count = ch_msg_cnt
            wiz.inbox_notification_count = notif_cnt + star_cnt
            wiz.dm_channel_count = dm_cnt
            wiz.activity_count = act_cnt
            wiz.outgoing_mail_count = mail_cnt
            wiz.document_chatter_count = doc_msg_cnt

    def _delete_messages_by_ids(self, msg_ids):
        """ลบรายการ mail_message ตามชุด ID พร้อมไฟล์แนบและตารางลูกที่เกี่ยวข้อง"""
        if not msg_ids:
            return 0
        cr = self.env.cr

        # หาไฟล์แนบที่ผูกกับข้อความชุดนี้ และไม่ได้ผูกกับเรคคอร์ดอื่น
        cr.execute(
            """
            SELECT DISTINCT mar.attachment_id
            FROM message_attachment_rel mar
            JOIN ir_attachment att ON att.id = mar.attachment_id
            WHERE mar.message_id = ANY(%s)
              AND COALESCE(att.res_model, 'mail.compose.message') IN ('discuss.channel', 'mail.compose.message', 'mail.message')
            """,
            (msg_ids,),
        )
        att_ids = [r[0] for r in cr.fetchall()]
        if att_ids:
            self.env["ir.attachment"].sudo().browse(att_ids).exists().unlink()

        cr.execute("DELETE FROM message_attachment_rel WHERE message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_tracking_value WHERE mail_message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_notification WHERE mail_message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_message_reaction WHERE message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_message_res_partner_starred_rel WHERE mail_message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_message_res_partner_rel WHERE mail_message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_link_preview WHERE message_id = ANY(%s)", (msg_ids,))
        cr.execute("DELETE FROM mail_mail WHERE mail_message_id = ANY(%s)", (msg_ids,))
        cr.execute("UPDATE mail_message SET parent_id = NULL WHERE parent_id = ANY(%s)", (msg_ids,))
        cr.execute("UPDATE discuss_channel SET from_message_id = NULL WHERE from_message_id = ANY(%s)", (msg_ids,))
        cr.execute(
            """
            UPDATE discuss_channel_member
            SET seen_message_id = NULL,
                fetched_message_id = NULL,
                new_message_separator = 0
            WHERE seen_message_id = ANY(%s) OR fetched_message_id = ANY(%s)
            """,
            (msg_ids, msg_ids),
        )
        cr.execute("DELETE FROM mail_message WHERE id = ANY(%s)", (msg_ids,))
        return len(msg_ids)

    def action_execute_clear_discuss(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("เฉพาะผู้ดูแลระบบสูงสุด (System Administrator) เท่านั้นที่สามารถล้างข้อความได้"))

        if not any(
            [
                self.clear_channel_messages,
                self.clear_inbox_notifications,
                self.clear_dm_channels,
                self.clear_activities,
                self.clear_outgoing_mails,
                self.clear_all_document_chatter,
            ]
        ):
            raise UserError(_("กรุณาเลือกอย่างน้อย 1 รายการที่ต้องการล้าง"))

        if (self.confirm_text or "").strip().upper() != "CLEAR":
            raise UserError(_("กรุณาพิมพ์คำว่า CLEAR ในช่องยืนยันก่อนดำเนินการลบข้อมูล"))

        cr = self.env.cr
        now = fields.Datetime.now()
        total_deleted = 0
        log_entries = []

        # 1) ล้างอีเมลขาออกก่อน (เพราะชี้ไปหา mail_message)
        if self.clear_outgoing_mails:
            cr.execute("SELECT COUNT(*) FROM mail_mail")
            cnt = cr.fetchone()[0] or 0
            if cnt:
                cr.execute("DELETE FROM mail_mail")
                total_deleted += cnt
            log_entries.append(f"[mail] mail.mail (อีเมลขาออก): ลบสำเร็จ {cnt:,} แถว")

        # 2) ล้างข้อความในห้องแชท Discuss (model = 'discuss.channel')
        if self.clear_channel_messages:
            cr.execute("SELECT id FROM mail_message WHERE model = 'discuss.channel'")
            ch_msg_ids = [r[0] for r in cr.fetchall()]
            ch_atts = self.env["ir.attachment"].sudo().search([("res_model", "=", "discuss.channel")])
            if ch_atts:
                ch_atts.unlink()
            deleted_ch_msgs = self._delete_messages_by_ids(ch_msg_ids)
            total_deleted += deleted_ch_msgs
            log_entries.append(
                f"[mail] ข้อความในห้องแชท Discuss (discuss.channel messages): ลบสำเร็จ {deleted_ch_msgs:,} ข้อความ"
            )

        # 3) ล้างกล่องจดหมาย Inbox / ติดดาว Starred / ประวัติ History ในหน้า Discuss
        if self.clear_inbox_notifications:
            cr.execute("SELECT COUNT(*) FROM mail_notification")
            notif_cnt = cr.fetchone()[0] or 0
            cr.execute("SELECT COUNT(*) FROM mail_message_res_partner_starred_rel")
            star_cnt = cr.fetchone()[0] or 0

            cr.execute("DELETE FROM mail_notification")
            cr.execute("DELETE FROM mail_message_res_partner_starred_rel")

            # ลบข้อความแจ้งเตือนเข้ากล่องจดหมายโดยตรง (user_notification / อีเมลลอยที่ไม่ได้ผูกเอกสาร)
            cr.execute(
                """
                SELECT id FROM mail_message
                WHERE message_type = 'user_notification'
                   OR (model IS NULL AND COALESCE(res_id, 0) = 0)
                """
            )
            direct_notif_msg_ids = [r[0] for r in cr.fetchall()]
            deleted_notif_msgs = self._delete_messages_by_ids(direct_notif_msg_ids)

            sub_total = notif_cnt + star_cnt + deleted_notif_msgs
            total_deleted += sub_total
            log_entries.append(
                f"[mail] กล่องจดหมาย Discuss (Inbox/History {notif_cnt:,} + ติดดาว {star_cnt:,} + แจ้งเตือนตรง {deleted_notif_msgs:,}): ลบสำเร็จรวม {sub_total:,} รายการ"
            )

        # 4) ลบห้องสนทนาส่วนตัวและกลุ่มแชทย่อย (คงห้องหลักของระบบไว้)
        if self.clear_dm_channels:
            protected_ch = self._get_protected_channel_ids() or [0]
            cr.execute("SELECT id FROM discuss_channel WHERE id <> ALL(%s)", (protected_ch,))
            dm_ids = [r[0] for r in cr.fetchall()]
            if dm_ids:
                cr.execute(
                    "SELECT id FROM mail_message WHERE model = 'discuss.channel' AND res_id = ANY(%s)",
                    (dm_ids,),
                )
                rem_msg_ids = [r[0] for r in cr.fetchall()]
                if rem_msg_ids:
                    self._delete_messages_by_ids(rem_msg_ids)
                cr.execute("DELETE FROM discuss_channel_member WHERE channel_id = ANY(%s)", (dm_ids,))
                cr.execute("DELETE FROM discuss_channel WHERE id = ANY(%s)", (dm_ids,))
                total_deleted += len(dm_ids)
            log_entries.append(
                f"[mail] ห้องแชทส่วนตัว/กลุ่มย่อย (discuss.channel): ลบสำเร็จ {len(dm_ids):,} ห้อง (คงห้องหลักไว้ {len(protected_ch)} ห้อง)"
            )

        # 5) ล้างกิจกรรมแจ้งเตือนค้าง (mail.activity)
        if self.clear_activities:
            cr.execute("SELECT COUNT(*) FROM mail_activity")
            act_cnt = cr.fetchone()[0] or 0
            if act_cnt:
                cr.execute("DELETE FROM mail_activity")
                total_deleted += act_cnt
            log_entries.append(f"[mail] กิจกรรมแจ้งเตือนค้าง (mail.activity): ลบสำเร็จ {act_cnt:,} รายการ")

        # 6) ตัวเลือกเสริม: ล้างประวัติบันทึกท้ายเอกสารทั้งหมด (Chatter)
        if self.clear_all_document_chatter:
            cr.execute("SELECT id FROM mail_message")
            all_rem_ids = [r[0] for r in cr.fetchall()]
            deleted_doc_msgs = self._delete_messages_by_ids(all_rem_ids)
            total_deleted += deleted_doc_msgs
            log_entries.append(
                f"[mail] ประวัติข้อความท้ายเอกสารทั้งหมด (Document Chatter): ลบสำเร็จ {deleted_doc_msgs:,} ข้อความ"
            )

        # รีเซ็ตสถานะการอ่านของสมาชิกห้องแชทที่คงเหลือ และล้างคิว bus
        cr.execute(
            """
            UPDATE discuss_channel_member
            SET seen_message_id = NULL,
                fetched_message_id = NULL,
                new_message_separator = 0
            """
        )
        cr.execute("DELETE FROM bus_bus")
        self.env.invalidate_all()

        # อัปเดตตัวเลขของโมดูล mail ในหน้า Data Cleaner
        mail_mod = self.env["vpk.data.cleaner.module"].sudo().search([("technical_name", "=", "mail")], limit=1)
        if mail_mod:
            mail_mod.action_refresh_module_counts()
            mail_mod.model_line_ids.filtered(lambda m: m.data_type == "transaction").sudo().write(
                {
                    "last_cleared_at": now,
                    "last_cleared_by": self.env.user.id,
                }
            )

        log_rec = self.env["vpk.data.cleaner.log"].sudo().create(
            {
                "name": _("ล้างข้อความและการแจ้งเตือนในแชท (Discuss)"),
                "executed_at": now,
                "user_id": self.env.user.id,
                "database_name": cr.dbname,
                "module_names": "mail (Discuss)",
                "model_count": len(log_entries),
                "deleted_row_count": total_deleted,
                "included_master": False,
                "reset_sequences": False,
                "detail_log": "\n".join(log_entries),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("ผลการล้างข้อความ Discuss สำเร็จ"),
            "res_model": "vpk.data.cleaner.log",
            "res_id": log_rec.id,
            "view_mode": "form",
            "target": "current",
        }
