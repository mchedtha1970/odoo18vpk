/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { getReportUrl } from "@web/webclient/actions/reports/utils";
import { PdfReportPreviewDialog } from "./pdf_report_preview_dialog";

/**
 * Intercept qweb-pdf report actions and open PDF.js print-preview viewer.
 */
async function vpkPdfPreviewHandler(action, options, env) {
    if (action.report_type !== "qweb-pdf") {
        return false;
    }

    downloadReportStatusProm.statusProm ||= rpc("/report/check_wkhtmltopdf");
    const status = await downloadReportStatusProm.statusProm;
    if (!["upgrade", "ok"].includes(status)) {
        return false;
    }

    const userContext = { ...user.context };
    if (action.context) {
        Object.assign(userContext, action.context);
    }

    const actionForUrl = {
        ...action,
        context: { ...(action.context || {}) },
    };
    if (!actionForUrl.context.active_ids && actionForUrl.context.active_id) {
        actionForUrl.context.active_ids = [actionForUrl.context.active_id];
    }

    const reportUrl = getReportUrl(actionForUrl, "pdf");
    const reportName =
        (typeof action.name === "string" && action.name) ||
        action.display_name ||
        _t("Report");
    const title = `${_t("Print Preview")}: ${reportName}`;

    env.services.dialog.add(PdfReportPreviewDialog, {
        title,
        reportUrl,
        action: actionForUrl,
        userContext,
    });
    return true;
}

const downloadReportStatusProm = {};

registry
    .category("ir.actions.report handlers")
    .add("vpk_pdf_preview_handler", vpkPdfPreviewHandler, { sequence: 10 });
