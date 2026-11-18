/** @odoo-module **/

// Icon names must exist in static/src/scss/line_icons.scss (scripts/build_vpk_line_icons.py)
export const APP_LINE_ICONS = {
    "mail.menu_root_discuss": "message-circle",
    "contacts.menu_contacts": "users",
    "purchase_request.parent_menu_purchase_request": "clipboard-list",
    "vpk_tier_validation.menu_vpk_tier_validation_root": "file-check",
    "sale.sale_menu_root": "trending-up",
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root": "layout-dashboard",
    "vpk_budget.menu_vpk_budget_root": "wallet",
    "vpk_document.menu_vpk_document_root": "folder-open",
    "vpk_document_studio.menu_document_studio_root": "file-pen-line",
    "account.menu_finance": "calculator",
    "account_asset_management.menu_finance_assets": "boxes",
    "vpk_gfmis.menu_gfmis_root": "landmark",
    "website.menu_website_configuration": "globe",
    "purchase.menu_purchase_root": "shopping-cart",
    "stock.menu_stock_root": "warehouse",
    "mrp.menu_mrp_root": "factory",
    "maintenance.menu_maintenance_title": "wrench",
    "hr.menu_hr_root": "id-card",
    "hr_expense.menu_hr_expense_root": "receipt",
    "utm.menu_link_tracker_root": "link",
    "base.menu_management": "layout-grid",
    "base.menu_administration": "settings",
    "vpk_data_cleaner.menu_vpk_data_cleaner_root": "eraser",
    "base.menu_tests": "flask-conical",
};

export const DEFAULT_APP_LINE_ICON = "app-window";

export function getAppLineIcon(app) {
    return APP_LINE_ICONS[app.xmlid] || DEFAULT_APP_LINE_ICON;
}
