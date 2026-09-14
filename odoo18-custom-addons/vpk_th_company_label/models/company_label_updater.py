# -*- coding: utf-8 -*-
from odoo import api, models

SOURCE_TERM = "Company"
THAI_TERM = "องค์กร"
THAI_LANGS = ("th_TH", "th")


class VpkThCompanyLabelUpdater(models.AbstractModel):
    _name = "vpk.th.company.label.updater"
    _description = "Update Thai translation: Company → องค์กร"

    @api.model
    def update_labels(self):
        installed = {
            code for code, _name in self.env["res.lang"].get_installed() if code.startswith("th")
        }
        langs = [lang for lang in THAI_LANGS if lang in installed] or list(installed)
        if not langs:
            return

        translations = {lang: THAI_TERM for lang in langs}
        self._update_model_field_labels(translations)
        self._update_translated_records(
            "ir.ui.menu",
            "name",
            translations,
        )
        self._update_translated_records(
            "ir.actions.act_window",
            "name",
            translations,
        )
        self._update_translated_records(
            "ir.module.module",
            "shortdesc",
            translations,
        )
        self.env.registry.clear_cache()

    def _update_model_field_labels(self, translations):
        # Prefer direct JSONB update so module .po reloads that still say
        # "บริษัท" are corrected on every upgrade of this module.
        for lang in translations:
            self.env.cr.execute(
                """
                UPDATE ir_model_fields
                   SET field_description = jsonb_set(
                        COALESCE(field_description, '{}'::jsonb),
                        %s,
                        to_jsonb(%s::text),
                        true
                   )
                 WHERE field_description->>'en_US' = %s
                   AND COALESCE(field_description->>%s, '') IS DISTINCT FROM %s
                """,
                [f"{{{lang}}}", translations[lang], SOURCE_TERM, lang, translations[lang]],
            )
        field_ids_query = """
            SELECT id
              FROM ir_model_fields
             WHERE field_description->>'en_US' = %s
        """
        self.env.cr.execute(field_ids_query, [SOURCE_TERM])
        field_ids = [row[0] for row in self.env.cr.fetchall()]
        if not field_ids:
            return
        fields = self.env["ir.model.fields"].browse(field_ids).sudo()
        for field in fields:
            field.update_field_translations("field_description", translations)

    def _update_translated_records(self, model_name, field_name, translations):
        Model = self.env[model_name].sudo()
        table = Model._table
        field = Model._fields.get(field_name)
        if not field or not field.translate or not field.store:
            return
        self.env.cr.execute(
            f"""
            SELECT id
              FROM "{table}"
             WHERE "{field_name}"->>'en_US' = %s
            """,
            [SOURCE_TERM],
        )
        record_ids = [row[0] for row in self.env.cr.fetchall()]
        if not record_ids:
            return
        for record in Model.browse(record_ids):
            record.update_field_translations(field_name, translations)
