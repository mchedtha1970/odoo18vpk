/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

/** Community stand-in for Enterprise account_accountant move-line list. */
export class AccountMoveLineListRenderer extends ListRenderer {}

export const AccountMoveLineListView = {
    ...listView,
    Renderer: AccountMoveLineListRenderer,
};


export class JournalReportAccountMoveLineReconcileListRenderer extends AccountMoveLineListRenderer {
    setup() {
        super.setup();
        this.props.list.groups?.forEach(group => {
            group.list?.groups?.forEach(innerGroup => {
                this.toggleGroup(innerGroup);
            });
        });
    }
}

export const JournalReportAccountMoveLineReconcileLineListView = {
    ...AccountMoveLineListView,
    Renderer: JournalReportAccountMoveLineReconcileListRenderer,
};

registry.category("views").add("account_move_line_journal_report_list", JournalReportAccountMoveLineReconcileLineListView);
