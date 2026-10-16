/** @odoo-module **/

import { odooExceptionTitleMap } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

odooExceptionTitleMap.set(
    "odoo.addons.vpk_budget.models.purchase_request_budget.BudgetInsufficientError",
    _t("งบประมาณคงเหลือไม่เพียงพอ")
);
