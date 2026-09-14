/** @odoo-module **/
/**
 * Community stand-in for Enterprise account_accountant move-line list.
 * account_reports imports these symbols; keep the same exports so journal
 * report js_class="account_move_line_journal_report_list" can load.
 */
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

export class AccountMoveLineListRenderer extends ListRenderer {}

export const AccountMoveLineListView = {
    ...listView,
    Renderer: AccountMoveLineListRenderer,
};
