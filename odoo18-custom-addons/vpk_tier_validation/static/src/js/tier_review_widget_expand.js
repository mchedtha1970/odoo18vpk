/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {ReviewsTable} from "@base_tier_validation/components/tier_review_widget/tier_review_widget.esm";

patch(ReviewsTable.prototype, {
    setup() {
        super.setup(...arguments);
        // Match onToggleCollapse: collapse=true means currently expanded
        this.state.collapse = true;
    },
});
