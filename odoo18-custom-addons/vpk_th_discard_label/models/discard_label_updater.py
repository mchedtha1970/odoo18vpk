# -*- coding: utf-8 -*-
import json
import re

from odoo import api, models

OLD_THAI = "ละทิ้ง"
THAI_TERM = "ยกเลิก"

# เปลี่ยนเฉพาะข้อความบนปุ่ม ไม่แตะประโยคที่แค่มีคำว่าละทิ้ง
_ATTR_REPLACEMENTS = (
    ('string="ละทิ้ง"', 'string="ยกเลิก"'),
    ("string='ละทิ้ง'", "string='ยกเลิก'"),
    ('cancel-label="ละทิ้ง"', 'cancel-label="ยกเลิก"'),
    ("cancel-label='ละทิ้ง'", "cancel-label='ยกเลิก'"),
)
_BTN_TEXT = re.compile(
    r"(<(?:a|button)\b[^>]*\bclass=\"[^\"]*\bbtn\b[^\"]*\"[^>]*>)(\s*)ละทิ้ง(\s*)(</(?:a|button)>)",
    re.IGNORECASE,
)


def rewrite_button_label(arch):
    if not arch or OLD_THAI not in arch:
        return arch
    updated = arch
    for old, new in _ATTR_REPLACEMENTS:
        updated = updated.replace(old, new)
    return _BTN_TEXT.sub(rf"\1\2{THAI_TERM}\3\4", updated)


class VpkThDiscardLabelUpdater(models.AbstractModel):
    _name = "vpk.th.discard.label.updater"
    _description = "เปลี่ยนปุ่มละทิ้งเป็นยกเลิก"

    @api.model
    def update_labels(self):
        self.env.cr.execute(
            """
            SELECT id, arch_db
              FROM ir_ui_view
             WHERE arch_db::text LIKE %s
            """,
            [f"%{OLD_THAI}%"],
        )
        for view_id, arch in self.env.cr.fetchall():
            if not isinstance(arch, dict):
                continue
            new_arch = {}
            changed = False
            for lang, value in arch.items():
                if isinstance(lang, str) and lang.startswith("th") and isinstance(value, str):
                    updated = rewrite_button_label(value)
                    if updated != value:
                        changed = True
                    new_arch[lang] = updated
                else:
                    new_arch[lang] = value
            if changed:
                self.env.cr.execute(
                    "UPDATE ir_ui_view SET arch_db = %s::jsonb WHERE id = %s",
                    [json.dumps(new_arch, ensure_ascii=False), view_id],
                )
        self.env.registry.clear_cache()
