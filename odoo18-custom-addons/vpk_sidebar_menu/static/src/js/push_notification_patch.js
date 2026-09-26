/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import "@mail/webclient/web/webclient";

const PUSH_SERVICE_UNAVAILABLE = /push service not available/i;

patch(WebClient.prototype, {
    /**
     * Chromium raises this when notification permission is granted but the
     * browser has no push service. The failure is expected on this deployment,
     * so it must not leave a sticky danger toast on every page load.
     */
    async _subscribePush() {
        const notification = this.notification;
        const add = notification.add.bind(notification);
        notification.add = (message, options = {}) => {
            const text = typeof message === "string" ? message : "";
            if (PUSH_SERVICE_UNAVAILABLE.test(text)) {
                console.info("VPK: web push is unavailable in this browser.");
                return;
            }
            return add(message, options);
        };
        try {
            return await super._subscribePush(...arguments);
        } finally {
            notification.add = add;
        }
    },
});
