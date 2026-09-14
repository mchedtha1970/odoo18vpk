# -*- coding: utf-8 -*-
"""Runtime override: Company → องค์กร for Thai code/web translations."""

from odoo.tools.translate import CodeTranslations, ReadonlyDict, code_translations

SOURCE_TERM = "Company"
THAI_TERM = "องค์กร"

_APPLIED = False
_ORIG_GET_PYTHON = CodeTranslations.get_python_translations
_ORIG_GET_WEB = CodeTranslations.get_web_translations


def _is_thai(lang):
    return bool(lang) and lang.startswith("th")


def _get_python_translations(self, module_name, lang):
    result = _ORIG_GET_PYTHON(self, module_name, lang)
    if not _is_thai(lang) or result.get(SOURCE_TERM) == THAI_TERM:
        return result
    merged = dict(result)
    merged[SOURCE_TERM] = THAI_TERM
    cached = ReadonlyDict(merged)
    self.python_translations[(module_name, lang)] = cached
    return cached


def _get_web_translations(self, module_name, lang):
    result = _ORIG_GET_WEB(self, module_name, lang)
    if not _is_thai(lang):
        return result
    messages = list(result.get("messages") or ())
    found = False
    new_messages = []
    changed = False
    for msg in messages:
        if msg.get("id") == SOURCE_TERM:
            found = True
            if msg.get("string") != THAI_TERM:
                new_messages.append(ReadonlyDict({"id": SOURCE_TERM, "string": THAI_TERM}))
                changed = True
            else:
                new_messages.append(msg)
        else:
            new_messages.append(msg)
    if not found:
        new_messages.append(ReadonlyDict({"id": SOURCE_TERM, "string": THAI_TERM}))
        changed = True
    if not changed:
        return result
    cached = ReadonlyDict({"messages": tuple(new_messages)})
    self.web_translations[(module_name, lang)] = cached
    return cached


def apply():
    global _APPLIED
    if _APPLIED:
        return
    CodeTranslations.get_python_translations = _get_python_translations
    CodeTranslations.get_web_translations = _get_web_translations
    code_translations.python_translations.clear()
    code_translations.web_translations.clear()
    _APPLIED = True
