/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class VpkTradePdfButton extends Component {
    static template = "vpk_vendor_api.TradePdfButton";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    get hasFile() {
        return Boolean(this.props.record.data.has_pdf && this.props.record.resId);
    }

    async open(ev) {
        ev?.stopPropagation?.();
        ev?.preventDefault?.();
        if (!this.hasFile) {
            return;
        }
        const action = await this.orm.call(
            "vpk.vendor.trade.document",
            "action_open_pdf_viewer",
            [[this.props.record.resId]]
        );
        if (!action) {
            this.notification.add("ยังไม่มีไฟล์ PDF", { type: "warning" });
            return;
        }
        await this.action.doAction(action);
    }
}

registry.category("fields").add("vpk_trade_pdf_button", {
    component: VpkTradePdfButton,
    supportedTypes: ["boolean"],
    listViewWidth: 48,
});
