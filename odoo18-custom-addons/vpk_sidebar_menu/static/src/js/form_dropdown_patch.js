/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { patch } from "@web/core/utils/patch";

/**
 * Visible bordered box for dropdown width/position anchor.
 * many2one: .o_field_many2one_selection (includes external link button)
 */
function resolveFieldBox(input) {
    if (!input) {
        return null;
    }
    const selection = input.closest(".o_field_many2one_selection");
    if (selection) {
        return selection;
    }
    const many2oneWidget = input.closest(".o_field_many2one, .o_field_many2one_avatar");
    if (many2oneWidget) {
        return many2oneWidget.querySelector(".o_field_many2one_selection") || many2oneWidget;
    }
    const bordered = input.closest(".o_input_dropdown, .o_datepicker");
    if (bordered?.closest(".o_form_editable")) {
        const widget = bordered.closest(".o_field_widget");
        return widget || bordered;
    }
    const widget = input.closest(".o_field_widget");
    if (widget?.closest(".o_form_editable")) {
        return widget;
    }
    return null;
}

function applyFieldBoxWidth(menu, fieldBox) {
    if (!menu || !fieldBox) {
        return;
    }
    const rect = fieldBox.getBoundingClientRect();
    const width = Math.round(rect.width);
    const left = Math.round(rect.left);
    const top = Math.round(rect.bottom + 1);
    if (width <= 0) {
        return;
    }
    menu.style.setProperty("width", `${width}px`, "important");
    menu.style.setProperty("min-width", `${width}px`, "important");
    menu.style.setProperty("max-width", `${width}px`, "important");
    menu.style.setProperty("left", `${left}px`, "important");
    menu.style.setProperty("top", `${top}px`, "important");
    menu.style.setProperty("right", "auto", "important");
}

function syncDropdownWidth(component) {
    const input = component.inputRef?.el;
    if (!input?.closest(".o_form_view")) {
        return;
    }
    const menu = input.closest(".o-autocomplete")?.querySelector(".o-autocomplete--dropdown-menu");
    if (!menu) {
        return;
    }
    applyFieldBoxWidth(menu, resolveFieldBox(input));
}

function scheduleDropdownWidthSync(component) {
    syncDropdownWidth(component);
    queueMicrotask(() => syncDropdownWidth(component));
    requestAnimationFrame(() => syncDropdownWidth(component));
}

patch(AutoComplete.prototype, {
    get dropdownOptions() {
        return {
            position: "bottom-fit",
            onPositioned: (popper) => {
                const input = this.inputRef?.el;
                if (!input?.closest(".o_form_view")) {
                    return;
                }
                applyFieldBoxWidth(popper, resolveFieldBox(input));
                requestAnimationFrame(() => applyFieldBoxWidth(popper, resolveFieldBox(input)));
            },
        };
    },

    get targetDropdown() {
        const input = this.inputRef?.el;
        if (input?.closest(".o_form_view")) {
            const fieldBox = resolveFieldBox(input);
            if (fieldBox) {
                return fieldBox;
            }
        }
        return super.targetDropdown;
    },

    open(useInput = false) {
        const result = super.open(...arguments);
        scheduleDropdownWidthSync(this);
        Promise.resolve(result).then(() => scheduleDropdownWidthSync(this));
        return result;
    },
});
