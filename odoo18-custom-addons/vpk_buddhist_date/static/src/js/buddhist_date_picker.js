/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { BE_OFFSET } from "./buddhist_date";

function toBuddhistYears(text) {
    return String(text).replace(/(?<!\d)(1\d{3}|2[0-3]\d{2})(?!\d)/g, (year) =>
        String(Number(year) + BE_OFFSET)
    );
}

patch(DateTimePicker.prototype, {
    onWillRender() {
        super.onWillRender(...arguments);
        if (Array.isArray(this.title)) {
            this.title = this.title.map(toBuddhistYears);
        } else if (this.title) {
            this.title = toBuddhistYears(this.title);
        }
        if (Array.isArray(this.items)) {
            for (const item of this.items) {
                if (item && typeof item.label === "string" && /^\d{4}$/.test(item.label)) {
                    item.label = toBuddhistYears(item.label);
                }
            }
        }
    },
});
