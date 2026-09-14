# -*- coding: utf-8 -*-
from odoo import api, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def get_overview_panel_data(self):
        """Return warehouses for the overview left panel."""
        warehouses = self.with_context(active_test=False).search(
            [], order="sequence, name, id"
        )
        Location = self.env["stock.location"].sudo()
        result = []
        for wh in warehouses:
            stock_loc = wh.lot_stock_id
            bin_domain = self._overview_bin_domain(wh)
            result.append(
                {
                    "id": wh.id,
                    "name": wh.name,
                    "code": wh.code,
                    "active": wh.active,
                    "stock_location": stock_loc.complete_name if stock_loc else "",
                    "stock_location_id": stock_loc.id if stock_loc else False,
                    "location_count": Location.search_count(bin_domain),
                }
            )
        return result

    def _overview_bin_domain(self, warehouse):
        stock_loc = warehouse.lot_stock_id
        if stock_loc:
            return [
                ("id", "child_of", stock_loc.id),
                ("usage", "=", "internal"),
                ("active", "=", True),
                ("id", "!=", stock_loc.id),
            ]
        return [
            ("warehouse_id", "=", warehouse.id),
            ("usage", "=", "internal"),
            ("active", "=", True),
        ]

    @api.model
    def get_overview_location_tree(self, warehouse_id):
        """Return nested location/bin tree under the warehouse stock location."""
        warehouse = self.browse(warehouse_id).exists()
        if not warehouse:
            return {"root": False, "nodes": []}

        Location = self.env["stock.location"].sudo()
        stock_loc = warehouse.lot_stock_id
        if not stock_loc:
            return {"root": False, "nodes": []}

        locations = Location.search(
            [
                ("id", "child_of", stock_loc.id),
                ("active", "=", True),
            ],
            order="complete_name, id",
        )

        node_map = {}
        for loc in locations:
            node_map[loc.id] = {
                "id": loc.id,
                "name": loc.name,
                "complete_name": loc.complete_name,
                "barcode": loc.barcode or "",
                "usage": loc.usage,
                "is_empty": bool(loc.is_empty) if loc.usage in ("internal", "transit") else False,
                "parent_id": loc.location_id.id if loc.location_id else False,
                "children": [],
            }

        roots = []
        for loc in locations:
            node = node_map[loc.id]
            parent_id = node["parent_id"]
            if loc.id == stock_loc.id:
                roots.append(node)
            elif parent_id in node_map:
                node_map[parent_id]["children"].append(node)
            else:
                roots.append(node)

        def sort_tree(nodes):
            nodes.sort(key=lambda n: (n["name"] or "").lower())
            for child in nodes:
                sort_tree(child["children"])

        sort_tree(roots)

        root = next((n for n in roots if n["id"] == stock_loc.id), roots[0] if roots else False)
        return {
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "warehouse_code": warehouse.code,
            "root": root,
            "total": max(len(locations) - (1 if stock_loc in locations else 0), 0),
        }
