/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ApprovalStatusBoard extends Component {
    static template = "vpk_tier_validation.ApprovalStatusBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            filter: "all",
            progress: "all",
            data: { updated_at: "", total: 0, open_count: 0, done_count: 0, types: [] },
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.ready = false;
        this.state.data = await this.orm.call(
            "tier.review",
            "get_approval_status_board",
            [],
            {}
        );
        const keys = this.state.data.types.map((item) => item.key);
        if (this.state.filter !== "all" && !keys.includes(this.state.filter)) {
            this.state.filter = "all";
        }
        this.state.ready = true;
    }

    get visibleTypes() {
        return this.state.data.types
            .filter((item) => this.state.filter === "all" || item.key === this.state.filter)
            .map((item) => {
                const documents = item.documents.filter(
                    (card) => this.state.progress === "all" || card.progress === this.state.progress
                );
                return { ...item, documents, count: documents.length };
            })
            .filter((item) => item.documents.length);
    }

    setFilter(key) {
        this.state.filter = key;
    }

    setProgress(progress) {
        this.state.progress = progress;
    }

    async openDocument(card) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: card.name,
            res_model: card.model,
            res_id: card.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("vpk_approval_status_board", ApprovalStatusBoard);
