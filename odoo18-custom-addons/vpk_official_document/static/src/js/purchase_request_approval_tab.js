/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

const TAB_NAME = "purchase_approval_memo";
const BASE_LABEL = "เอกสารอนุมัติขอซื้อ";

function plainDepartmentName(label) {
    const match = /^\[.*?\]\s*(.+)$/.exec(label || "");
    return (match ? match[1] : label || "").trim();
}

function many2oneName(value) {
    if (!value) {
        return "";
    }
    if (Array.isArray(value)) {
        return value[1] || "";
    }
    if (typeof value === "object") {
        return value.display_name || value.name || "";
    }
    return "";
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        const sync = () => this._vpkSyncApprovalMemoTab();
        onMounted(sync);
        onPatched(sync);
    },

    _vpkApprovalFormRoot() {
        const root = this.el;
        if (root?.querySelector) {
            const owned = root.querySelector(".o_form_view") || root.closest?.(".o_form_view");
            if (owned?.querySelector(`a.nav-link[name="${TAB_NAME}"]`)) {
                return owned;
            }
            if (root.querySelector(`a.nav-link[name="${TAB_NAME}"]`)) {
                return root;
            }
        }
        return document.querySelector(".o_form_view");
    },

    _vpkSyncApprovalMemoTab() {
        const record = this.props.record;
        if (!record || record.resModel !== "purchase.request") {
            return;
        }
        const form = this._vpkApprovalFormRoot();
        const tab = form?.querySelector(`a.nav-link[name="${TAB_NAME}"]`);
        if (!tab) {
            return;
        }
        const department = plainDepartmentName(
            many2oneName(record.data.department_id) ||
                many2oneName(record.data.budget_analytic_account_id)
        );
        const title = department ? `${BASE_LABEL} [${department}]` : BASE_LABEL;
        if (tab.textContent !== title) {
            tab.textContent = title;
        }
    },
});
