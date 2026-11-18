/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


export class WorkAcceptanceDashboard extends Component {
    static template = "vpk_work_acceptance.WorkAcceptanceDashboard";
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
            updated_at: "",
            all_action: false,
            kpis: [],
            goods: { title: "", empty: "", rows: [] },
            services: { title: "", empty: "", rows: [] },
            drafts: { title: "", empty: "", rows: [] },
        };
    }

    async loadData() {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "work.acceptance",
            "get_work_acceptance_dashboard",
            []
        );
        this.state.ready = true;
    }

    async openAction(action) {
        if (action) {
            await this.actionService.doAction(action);
        }
    }

    async openItem(key) {
        if (!key) {
            return;
        }
        const action = await this.orm.call(
            "work.acceptance",
            "action_open_dashboard_item",
            [key]
        );
        if (action) {
            await this.actionService.doAction(action);
        }
    }
}

registry
    .category("actions")
    .add("vpk_work_acceptance_dashboard", WorkAcceptanceDashboard);
