# -*- coding: utf-8 -*-
import re
from datetime import date, datetime

from odoo import api, fields, models

BE_OFFSET = 543


def to_buddhist_text(text, value):
    """Replace the Gregorian year of ``value`` inside ``text`` with the Buddhist year."""
    if not text or not value:
        return text
    if isinstance(value, str):
        try:
            value = fields.Datetime.from_string(value) if len(value) > 10 else fields.Date.from_string(value)
        except ValueError:
            return text
    if not isinstance(value, (date, datetime)):
        return text
    year = value.year
    if year >= 2400:
        return text
    text = str(text)
    full = re.sub(r"(?<!\d)%d(?!\d)" % year, str(year + BE_OFFSET), text)
    if full != text:
        return full
    short = "%02d" % (year % 100)
    return re.sub(r"(?<=/)%s(?!\d)" % short, "%02d" % ((year + BE_OFFSET) % 100), text)


class IrQwebFieldDate(models.AbstractModel):
    _inherit = "ir.qweb.field.date"

    @api.model
    def value_to_html(self, value, options):
        return to_buddhist_text(super().value_to_html(value, options), value)


class IrQwebFieldDatetime(models.AbstractModel):
    _inherit = "ir.qweb.field.datetime"

    @api.model
    def value_to_html(self, value, options):
        result = super().value_to_html(value, options)
        if isinstance(value, str):
            value = fields.Datetime.from_string(value)
        if isinstance(value, datetime):
            tz_value = fields.Datetime.context_timestamp(self, value)
            if tz_value.year != value.year:
                return to_buddhist_text(result, tz_value)
        return to_buddhist_text(result, value)
