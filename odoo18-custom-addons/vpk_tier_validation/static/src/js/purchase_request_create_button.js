/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

const CREATE_LABEL = "สร้างเอกสารใหม่";

function relabelCreateButtons(root, selector) {
    if (!root) {
        return;
    }
    for (const button of root.querySelectorAll(selector)) {
        if (button.textContent.trim() !== CREATE_LABEL) {
            button.textContent = CREATE_LABEL;
        }
    }
}

function patchCreateLabel(Controller, selector) {
    patch(Controller.prototype, {
        setup() {
            super.setup(...arguments);
            if (this.props.resModel !== "purchase.request") {
                return;
            }
            const apply = () => relabelCreateButtons(this.rootRef.el, selector);
            onMounted(apply);
            onPatched(apply);
        },
    });
}

patchCreateLabel(ListController, ".o_list_button_add");
patchCreateLabel(FormController, ".o_form_button_create");
