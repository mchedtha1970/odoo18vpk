/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

const USAGE_QTY_FIELDS = {
    usage_qty_y3: "y3",
    usage_qty_y2: "y2",
    usage_qty_y1: "y1",
};

function toBeYear(fiscalYear) {
    const year = parseInt(fiscalYear, 10);
    if (!year) {
        return 0;
    }
    return year < 2400 ? year + 543 : year;
}

function getPlanYears(list) {
    const root = list?.model?.root;
    const data = root?.data || {};
    const current =
        data.plan_year_be ||
        (() => {
            const fiscalYear = list?.context?.vpk_usage_fiscal_year || data.fiscal_year;
            const currentBe = toBeYear(fiscalYear);
            return currentBe ? String(currentBe) : "";
        })();
    if (!current && !(data.usage_history_be_y1 || data.usage_history_be_y2 || data.usage_history_be_y3)) {
        const fiscalYear = list?.context?.vpk_usage_fiscal_year || data.fiscal_year;
        const currentBe = toBeYear(fiscalYear);
        if (!currentBe) {
            return null;
        }
        return {
            current: String(currentBe),
            y1: String(currentBe - 1),
            y2: String(currentBe - 2),
            y3: String(currentBe - 3),
        };
    }
    const currentBe = toBeYear(current || data.fiscal_year);
    return {
        current: current || (currentBe ? String(currentBe) : ""),
        y1: data.usage_history_be_y1 || (currentBe ? String(currentBe - 1) : ""),
        y2: data.usage_history_be_y2 || (currentBe ? String(currentBe - 2) : ""),
        y3: data.usage_history_be_y3 || (currentBe ? String(currentBe - 3) : ""),
    };
}

patch(ListRenderer.prototype, {
    getActiveColumns(list) {
        const columns = super.getActiveColumns(list);
        if (!list || list.resModel !== "departmental.budget.request.material.detail") {
            return columns;
        }
        const years = getPlanYears(list);
        if (!years) {
            return columns;
        }
        return columns.map((column) => {
            const yearKey = USAGE_QTY_FIELDS[column.name];
            if (yearKey && years[yearKey]) {
                return {
                    ...column,
                    label: `ปริมาณใช้ปี ${years[yearKey]}`,
                };
            }
            if (column.name === "plan_usage_qty" && years.current) {
                return {
                    ...column,
                    label: `ปริมาณใช้ในปี ${years.current}`,
                };
            }
            if (column.name === "quantity" && years.current) {
                return {
                    ...column,
                    label: `ปริมาณที่ของบในปี ${years.current}`,
                };
            }
            if (column.name === "unit_price") {
                return {
                    ...column,
                    label: "ราคา/หน่วยนับ",
                };
            }
            if (column.name === "total_amount") {
                return {
                    ...column,
                    label: "มูลค่าที่ของบ",
                };
            }
            return column;
        });
    },
});
