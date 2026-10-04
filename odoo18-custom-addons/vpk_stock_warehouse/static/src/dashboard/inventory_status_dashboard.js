/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const PREF_KEY = "vpk_inventory_status_dashboard";
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

export class InventoryStatusDashboard extends Component {
    static template = "vpk_stock_warehouse.InventoryStatusDashboard";
    static props = ["*"];

    setup() {
        ensurePromptFont();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        const prefs = this.readPrefs();
        this.state = useState({
            ready: false,
            warehouseId: prefs.warehouseId,
            categoryId: prefs.categoryId,
            data: this.emptyData(),
        });
        onWillStart(() => this.loadData());
    }

    emptyData() {
        return {
            date_label: "",
            warehouses: [],
            categories: [],
            parts: [],
            categories_table: [],
            ages: [],
            fast_rows: [],
            slow_rows: [],
            dead_rows: [],
            ids: { all: [], fast: [], slow: [], dead: [], dead_year: [] },
            total_sku: 0,
            total_qty: 0,
            total_value: 0,
            slow_cover: null,
            fast_low: 0,
            dead_year: 0,
        };
    }

    readPrefs() {
        try {
            const prefs = JSON.parse(window.sessionStorage.getItem(PREF_KEY) || "{}");
            return {
                warehouseId: Number(prefs.warehouseId) || 0,
                categoryId: Number(prefs.categoryId) || 0,
            };
        } catch {
            return { warehouseId: 0, categoryId: 0 };
        }
    }

    savePrefs() {
        window.sessionStorage.setItem(
            PREF_KEY,
            JSON.stringify({
                warehouseId: this.state.warehouseId || 0,
                categoryId: this.state.categoryId || 0,
            })
        );
    }

    async loadData(warehouseId = this.state.warehouseId, categoryId = this.state.categoryId) {
        this.state.ready = false;
        const data = await this.orm.call(
            "stock.warehouse",
            "get_inventory_status_dashboard",
            [],
            {
                warehouse_id: warehouseId || false,
                category_id: categoryId || false,
            }
        );
        this.state.data = data;
        this.state.warehouseId = data.warehouse_id || 0;
        this.state.categoryId = data.category_id || 0;
        this.savePrefs();
        this.state.ready = true;
    }

    async onWarehouseChange(ev) {
        await this.loadData(Number(ev.target.value), this.state.categoryId);
    }

    async onCategoryChange(ev) {
        await this.loadData(this.state.warehouseId, Number(ev.target.value));
    }

    part(key) {
        return (this.state.data.parts || []).find((item) => item.key === key) || {
            sku: 0,
            sku_pct: 0,
            value: 0,
            value_pct: 0,
        };
    }

    formatCount(value) {
        return new Intl.NumberFormat("th-TH", { maximumFractionDigits: 0 }).format(value || 0);
    }

    formatQty(value) {
        const number = Number(value || 0);
        const digits = Math.abs(number - Math.round(number)) < 0.001 ? 0 : 2;
        return new Intl.NumberFormat("th-TH", { maximumFractionDigits: digits }).format(number);
    }

    formatValue(value) {
        const number = Number(value || 0);
        if (Math.abs(number) >= 1000000) {
            return `฿${(number / 1000000).toFixed(2)} ล้าน`;
        }
        return `฿${this.formatCount(number)}`;
    }

    formatCompactValue(value) {
        const number = Number(value || 0);
        if (Math.abs(number) >= 1000000) {
            return `฿${(number / 1000000).toFixed(2)}M`;
        }
        return this.formatValue(number);
    }

    coverLabel(cover) {
        if (cover === null || cover === undefined || cover === false) {
            return "—";
        }
        if (cover > 9999) {
            return "9,999+ วัน";
        }
        return `${this.formatCount(cover)} วัน`;
    }

    barStyle(pct, color) {
        return `width:${Math.max(pct || 0, 0)}%;background:${color};`;
    }

    async openProducts(ids, name) {
        const productIds = ids || [];
        if (!productIds.length) {
            this.notification.add("ไม่มีสินค้าในกลุ่มนี้", { type: "warning" });
            return;
        }
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: "product.product",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["id", "in", productIds]],
            target: "current",
        });
    }

    async openProduct(productId) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "product.product",
            res_id: productId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async exportReport() {
        const rows = await this.orm.call(
            "stock.warehouse",
            "export_inventory_status_rows",
            [],
            {
                warehouse_id: this.state.warehouseId || false,
                category_id: this.state.categoryId || false,
            }
        );
        const header = [
            "รหัส",
            "สินค้า",
            "หมวด",
            "สถานะ",
            "คงเหลือ",
            "หน่วย",
            "มูลค่า",
            "จำนวนครั้งที่จ่าย 90 วัน",
            "จำนวนที่จ่าย 90 วัน",
            "พอใช้(วัน)",
            "เคลื่อนไหวล่าสุด",
        ];
        const body = rows.map((row) => [
            row.code,
            row.name,
            row.category,
            row.klass,
            row.qty,
            row.uom,
            row.value,
            row.out_90,
            row.qty_out_90,
            row.cover_days === null || row.cover_days === false ? "" : row.cover_days,
            row.last_move,
        ]);
        const csv = [header, ...body]
            .map((line) => line.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(","))
            .join("\n");
        const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "สถานะสินค้าคงคลัง.csv";
        link.click();
        URL.revokeObjectURL(link.href);
    }
}

registry.category("actions").add("vpk_inventory_status_dashboard", InventoryStatusDashboard);
