/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { View } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class WarehouseOverviewDashboard extends Component {
    static template = "vpk_stock_warehouse.WarehouseOverviewDashboard";
    static components = { Layout, View };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            ready: false,
            warehouses: [],
            selectedId: false,
            searchQuery: "",
            locationQuery: "",
            viewMode: "tree",
            treeRoot: null,
            treeTotal: 0,
            treeLoading: false,
            expandedIds: {},
        });
        this.viewProps = null;
        this._listActionData = null;

        onWillStart(async () => {
            const [warehouses, actionData] = await Promise.all([
                this.orm.call("stock.warehouse", "get_overview_panel_data", [], {}),
                this.actionService.loadAction(
                    "vpk_stock_warehouse.action_stock_location_overview_embedded"
                ),
            ]);
            this._listActionData = actionData;
            this.state.warehouses = warehouses;
            if (warehouses.length) {
                this.state.selectedId = warehouses[0].id;
                await this._loadTree(warehouses[0].id);
                this._buildViewProps(actionData);
            }
            this.state.ready = true;
        });
    }

    get display() {
        return { controlPanel: {} };
    }

    get filteredWarehouses() {
        const query = (this.state.searchQuery || "").trim().toLowerCase();
        if (!query) {
            return this.state.warehouses;
        }
        return this.state.warehouses.filter(
            (wh) =>
                (wh.name || "").toLowerCase().includes(query) ||
                (wh.code || "").toLowerCase().includes(query)
        );
    }

    get selectedWarehouse() {
        return this.state.warehouses.find((wh) => wh.id === this.state.selectedId) || null;
    }

    get filteredTreeRoot() {
        const root = this.state.treeRoot;
        if (!root) {
            return null;
        }
        const query = (this.state.locationQuery || "").trim().toLowerCase();
        if (!query) {
            return root;
        }
        return this._filterTree(root, query);
    }

    _filterTree(node, query) {
        const selfMatch =
            (node.name || "").toLowerCase().includes(query) ||
            (node.complete_name || "").toLowerCase().includes(query) ||
            (node.barcode || "").toLowerCase().includes(query);
        const children = [];
        for (const child of node.children || []) {
            const filtered = this._filterTree(child, query);
            if (filtered) {
                children.push(filtered);
            }
        }
        if (selfMatch || children.length) {
            return { ...node, children };
        }
        return null;
    }

    _locationDomain(warehouse) {
        if (!warehouse) {
            return [["id", "=", 0]];
        }
        if (warehouse.stock_location_id) {
            return [
                ["id", "child_of", warehouse.stock_location_id],
                ["usage", "=", "internal"],
                ["active", "=", true],
                ["id", "!=", warehouse.stock_location_id],
            ];
        }
        return [
            ["warehouse_id", "=", warehouse.id],
            ["usage", "=", "internal"],
            ["active", "=", true],
        ];
    }

    _buildViewProps(actionData) {
        const warehouse = this.selectedWarehouse;
        const listView = actionData.views.find((v) => v[1] === "list");
        const searchView = actionData.views.find((v) => v[1] === "search");
        this.viewProps = {
            resModel: actionData.res_model,
            type: "list",
            viewId: listView ? listView[0] : false,
            views: [
                [listView ? listView[0] : false, "list"],
                [searchView ? searchView[0] : false, "search"],
            ],
            domain: this._locationDomain(warehouse),
            context: { ...actionData.context, lang: user.context.lang },
            display: { controlPanel: true },
            className: "o_vpk_warehouse_overview_location_view",
        };
    }

    async _loadTree(warehouseId) {
        this.state.treeLoading = true;
        this.state.locationQuery = "";
        const data = await this.orm.call(
            "stock.warehouse",
            "get_overview_location_tree",
            [warehouseId],
            {}
        );
        this.state.treeRoot = data.root || null;
        this.state.treeTotal = data.total || 0;
        const expanded = {};
        if (data.root) {
            expanded[data.root.id] = true;
        }
        this.state.expandedIds = expanded;
        this.state.treeLoading = false;
    }

    async selectWarehouse(warehouseId) {
        if (this.state.selectedId === warehouseId) {
            return;
        }
        this.state.selectedId = warehouseId;
        await this._loadTree(warehouseId);
        if (this._listActionData) {
            this._buildViewProps(this._listActionData);
        }
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    isExpanded(nodeId) {
        if ((this.state.locationQuery || "").trim()) {
            return true;
        }
        return Boolean(this.state.expandedIds[nodeId]);
    }

    toggleExpand(nodeId) {
        this.state.expandedIds = {
            ...this.state.expandedIds,
            [nodeId]: !this.state.expandedIds[nodeId],
        };
    }

    expandAll() {
        const expanded = {};
        const walk = (node) => {
            if (!node) {
                return;
            }
            if ((node.children || []).length) {
                expanded[node.id] = true;
            }
            for (const child of node.children || []) {
                walk(child);
            }
        };
        walk(this.state.treeRoot);
        this.state.expandedIds = expanded;
    }

    collapseAll() {
        const expanded = {};
        if (this.state.treeRoot) {
            expanded[this.state.treeRoot.id] = true;
        }
        this.state.expandedIds = expanded;
    }

    openLocation(locationId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Location"),
            res_model: "stock.location",
            res_id: locationId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openWarehouseForm() {
        const warehouse = this.selectedWarehouse;
        if (!warehouse) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: warehouse.name,
            res_model: "stock.warehouse",
            res_id: warehouse.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllLocations() {
        const warehouse = this.selectedWarehouse;
        if (!warehouse) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Locations / Bins"),
            res_model: "stock.location",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: this._locationDomain(warehouse),
            context: { create: false },
            target: "current",
        });
    }
}

registry.category("actions").add("vpk_warehouse_overview", WarehouseOverviewDashboard);
