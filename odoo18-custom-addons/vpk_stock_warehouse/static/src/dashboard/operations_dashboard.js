/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const PERIODS = [
    { id: "today", label: "วันนี้" },
    { id: "7d", label: "7 วัน" },
    { id: "30d", label: "30 วัน" },
];
const PREF_KEY = "vpk_warehouse_operations_dashboard";
const PROMPT_FONT_ID = "vpk-ops-prompt-font";
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

export class WarehouseOperationsDashboard extends Component {
    static template = "vpk_stock_warehouse.OperationsDashboard";
    static props = ["*"];

    setup() {
        ensurePromptFont();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.periods = PERIODS;
        const prefs = this.readPrefs();
        this.state = useState({
            ready: false,
            period: prefs.period,
            warehouseId: prefs.warehouseId,
            data: this.emptyData(),
        });
        onWillStart(() => this.loadData());
    }

    readPrefs() {
        try {
            const prefs = JSON.parse(window.sessionStorage.getItem(PREF_KEY) || "{}");
            const period = PERIODS.some((item) => item.id === prefs.period) ? prefs.period : "today";
            const warehouseId = Number(prefs.warehouseId) || false;
            return { period, warehouseId };
        } catch {
            return { period: "today", warehouseId: false };
        }
    }

    savePrefs() {
        window.sessionStorage.setItem(
            PREF_KEY,
            JSON.stringify({
                period: this.state.period,
                warehouseId: this.state.warehouseId || false,
            })
        );
    }

    emptyData() {
        return {
            date_label: "",
            updated_at: "",
            warehouse_id: false,
            warehouse_label: "",
            warehouses: [],
            kpis: [],
            columns: [],
            chart: { title: "", groups: [], series: [] },
            alerts: [],
            alert_count: 0,
        };
    }

    async loadData(period = this.state.period, warehouseId = this.state.warehouseId) {
        this.state.ready = false;
        const data = await this.orm.call(
            "stock.warehouse",
            "get_operations_dashboard",
            [],
            {
                period,
                warehouse_id: warehouseId || false,
            }
        );
        this.state.data = data;
        this.state.period = data.period || period;
        this.state.warehouseId = data.warehouse_id || false;
        this.savePrefs();
        this.state.ready = true;
    }

    async setPeriod(period) {
        if (period === this.state.period) {
            return;
        }
        await this.loadData(period, this.state.warehouseId);
    }

    async onWarehouseChange(ev) {
        await this.loadData(this.state.period, Number(ev.target.value));
    }

    async openAll(column) {
        if (column.action) {
            await this.actionService.doAction(column.action);
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

    barStyle(bar) {
        const series = (this.state.data.chart.series || []).find((item) => item.key === bar.key);
        const color = series ? series.color : "#94a3b8";
        const height = Math.max(bar.height || 0, bar.value ? 8 : 0);
        return `height:${height}%;background:${color};`;
    }
}

registry.category("actions").add("vpk_warehouse_operations_dashboard", WarehouseOperationsDashboard);
