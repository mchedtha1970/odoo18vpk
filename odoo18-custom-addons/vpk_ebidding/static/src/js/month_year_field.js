/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const MONTH_YEAR_FORMAT = "MM/yyyy";

export class MonthYearField extends Component {
    static template = "vpk_ebidding.MonthYearField";
    static components = { DateTimeInput };
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    get value() {
        return this.props.record.data[this.props.name] || false;
    }

    get formattedValue() {
        return this.value ? this.value.toFormat(MONTH_YEAR_FORMAT) : "";
    }

    get placeholder() {
        return this.props.placeholder || "06/2569";
    }

    onApply(value) {
        const next = value ? value.startOf("month") : false;
        this.props.record.update({ [this.props.name]: next });
    }
}

export const monthYearField = {
    component: MonthYearField,
    displayName: _t("Month/Year"),
    supportedTypes: ["date"],
    extractProps({ placeholder }) {
        return { placeholder };
    },
};

registry.category("fields").add("month_year", monthYearField);
