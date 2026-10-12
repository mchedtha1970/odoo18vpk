/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const PERIODS = [
    { id: "today", label: "วันนี้" },
    { id: "7d", label: "7 วัน" },
    { id: "30d", label: "30 วัน" },
];
const PREF_KEY = "vpk_maintenance_dashboard";
const PROMPT_FONT_ID = "vpk-maint-prompt-font";
const PROMPT_FONT_URL =
    "https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap";

function ensurePromptFont() {
    if (document.getElementById(PROMPT_FONT_ID)) {
        return;
    }
    const link = document.createElement("link");
    link.id = PROMPT_FONT_ID;
    link.rel = "stylesheet";
    link.href = PROMPT_FONT_URL;
    document.head.appendChild(link);
}

export class MaintenanceDashboard extends Component {
    static template = "vpk_maintenance.MaintenanceDashboard";
    static props = ["*"];

    setup() {
        ensurePromptFont();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.periods = PERIODS;
        const period = this.readPeriod();
        this.state = useState({
            ready: false,
            period,
            data: this.emptyData(),
        });
        onWillStart(() => this.loadData());
    }

    readPeriod() {
        try {
            const prefs = JSON.parse(window.sessionStorage.getItem(PREF_KEY) || "{}");
            return PERIODS.some((item) => item.id === prefs.period) ? prefs.period : "7d";
        } catch {
            return "7d";
        }
    }

    emptyData() {
        return {
            date_label: "",
            updated_at: "",
            period_label: "",
            kpis: [],
            flow: [],
            teams: [],
            departments: [],
            movement: [],
            movement_count: 0,
            jobs: [],
            alerts: [],
        };
    }

    async loadData(period = this.state.period) {
        this.state.ready = false;
        const data = await this.orm.call(
            "maintenance.request",
            "get_maintenance_dashboard",
            [],
            { period }
        );
        this.state.data = data;
        this.state.period = data.period || period;
        window.sessionStorage.setItem(PREF_KEY, JSON.stringify({ period: this.state.period }));
        this.state.ready = true;
    }

    async setPeriod(period) {
        if (period === this.state.period) {
            return;
        }
        await this.loadData(period);
    }

    async refresh() {
        await this.loadData(this.state.period);
    }

    async openAction(item) {
        if (item && item.action) {
            await this.actionService.doAction(item.action);
        }
    }

    async openRecord(row) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: row.name,
            res_model: row.model,
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("vpk_maintenance_dashboard", MaintenanceDashboard);
