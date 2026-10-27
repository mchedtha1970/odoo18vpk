/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { StaticList } from "@web/model/relational_model/static_list";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { MultiRecordViewButton } from "@web/views/view_button/multi_record_view_button";

patch(StaticList.prototype, {
    get selection() {
        return this.records.filter((record) => record.selected);
    },
    get isDomainSelected() {
        return false;
    },
    async getResIds(isSelected) {
        const records = isSelected ? this.selection : this.records;
        return records.map((record) => record.resId).filter((id) => typeof id === "number");
    },
    toggleSelection() {
        const selected = this.selection.length !== this.records.length;
        for (const record of this.records) {
            record._toggleSelection(selected);
        }
    },
});

export class SelectableX2ManyField extends X2ManyField {
    static template = "vpk_ebidding.SelectableX2ManyField";
    static components = {
        ...X2ManyField.components,
        MultiRecordViewButton,
    };

    get rendererProps() {
        const props = super.rendererProps;
        if (this.props.viewMode === "list") {
            props.allowSelectors = true;
        }
        return props;
    }
}

export const selectableX2ManyField = {
    ...x2ManyField,
    component: SelectableX2ManyField,
};

registry.category("fields").add("x2many_selectable", selectableX2ManyField);
