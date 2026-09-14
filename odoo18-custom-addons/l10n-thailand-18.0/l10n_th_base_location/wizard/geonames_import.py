# Copyright 2020 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import csv
import logging
import os

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class CityZipGeonamesImport(models.TransientModel):
    _inherit = "city.zip.geonames.import"

    is_thailand = fields.Boolean(
        compute="_compute_is_thailand",
        help="For Thailand only, data is from TH_th.txt and TH_en.txt stored "
        "in the module's data folder. To get data from Geonames.org, "
        "please uninstall l10n_th_base_location.",
    )
    location_thailand_language = fields.Selection(
        [("th", "Thai"), ("en", "English")],
        string="Language of Thailand",
        default="th",
    )

    @api.depends("country_ids")
    def _compute_is_thailand(self):
        for wizard in self:
            wizard.is_thailand = "TH" in wizard.country_ids.mapped("code")

    @api.model
    def _normalize_th_state_code(self, code):
        if code and code.startswith("TH-"):
            return code[3:]
        return code

    @api.model
    def prepare_state(self, row, country):
        vals = super().prepare_state(row, country)
        if country.code == "TH":
            vals["code"] = self._normalize_th_state_code(vals.get("code"))
        return vals

    def _prepare_district_thailand(self, row):
        row_dict = dict(enumerate(row))
        return row_dict.get(5, ""), row_dict.get(6, "")

    @api.model
    def prepare_zip(self, row, city_id):
        vals = super().prepare_zip(row, city_id)
        if len(row) >= 7:
            district, sub_district = self._prepare_district_thailand(row)
            vals.update(
                {"district_code": district, "sub_district_code": sub_district}
            )
        return vals

    def _create_states(self, parsed_csv, search_states, max_import, country):
        """Thailand provinces already exist in Odoo. Update names to TH/EN."""
        if country.code != "TH":
            return super()._create_states(
                parsed_csv, search_states, max_import, country
            )

        states_map = {}
        if search_states:
            states_map = {
                state.code: state
                for state in self.env["res.country.state"].search(
                    [("country_id", "=", country.id)]
                )
            }

        state_vals_set = set()
        state_dict = {}
        for i, row in enumerate(parsed_csv):
            if max_import and i == max_import:
                break
            state = None
            if search_states:
                code = self._normalize_th_state_code(
                    row[country.geonames_state_code_column or 4]
                )
                state = states_map.get(code)
            state_vals = self.prepare_state(row, country)
            if not state:
                state_vals_set.add(
                    (
                        state_vals["name"],
                        state_vals["code"],
                        state_vals["country_id"],
                    )
                )
            else:
                state.write({"name": state_vals["name"]})
                state_dict[state.code] = state

        state_vals_list = [
            {"name": name, "code": code, "country_id": country_id}
            for name, code, country_id in state_vals_set
        ]
        logger.info("Importing %d states", len(state_vals_list))
        created_states = self.env["res.country.state"].create(state_vals_list)
        for i, vals in enumerate(state_vals_list):
            state_dict[vals["code"]] = created_states[i]
        return state_dict

    @api.model
    def get_and_parse_csv(self, country):
        if country.code == "TH":
            module_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            filename = (
                "data/TH_th.txt"
                if self.location_thailand_language == "th"
                else "data/TH_en.txt"
            )
            file_path = os.path.join(module_path, filename)
            with open(file_path, "r", encoding="utf-8") as data_file:
                reader = csv.reader(data_file, delimiter="\t")
                parsed_csv = [row for row in reader]
            for row in parsed_csv:
                if len(row) > 4:
                    row[4] = self._normalize_th_state_code(row[4])
            return parsed_csv
        return super().get_and_parse_csv(country)
