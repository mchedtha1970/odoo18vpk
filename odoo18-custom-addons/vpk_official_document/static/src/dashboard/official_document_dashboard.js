/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class OfficialDocumentDashboard extends Component {
    static template = "vpk_official_document.OfficialDocumentDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            data: this.emptyData(),
        });
        onWillStart(() => this.loadData());
    }

    emptyData() {
        return {
            title: "หนังสือราชการ",
            subtitle: "",
            kpis: [],
            cards: [],
        };
    }

    async loadData() {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "vpk.official.document.type",
            "get_dashboard_data",
            []
        );
        this.state.ready = true;
    }

    async openAction(action) {
        if (action) {
            await this.actionService.doAction(action);
        }
    }

    openAll() {
        const kpi = this.state.data.kpis.find((item) => item.key === "total");
        return this.openAction(kpi && kpi.action);
    }
}

registry
    .category("actions")
    .add("vpk_official_document_dashboard", OfficialDocumentDashboard);
