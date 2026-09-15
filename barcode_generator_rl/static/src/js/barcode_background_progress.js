/** @odoo-module **/

import { onMounted, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import {
    ProgressBarField,
    progressBarField,
} from "@web/views/fields/progress_bar/progress_bar_field";

export class BarcodeBackgroundProgress extends ProgressBarField {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.stopped = false;
        this.refreshWarning = false;
        onMounted(() => this.scheduleRefresh());
        onWillDestroy(() => {
            this.stopped = true;
            clearTimeout(this.refreshTimer);
        });
    }

    scheduleRefresh() {
        if (!this.stopped) {
            this.refreshTimer = setTimeout(() => this.refreshProgress(), 3000);
        }
    }

    async refreshProgress() {
        try {
            const record = this.props.record;
            if (!this.stopped && record.resId && ["queued", "running"].includes(record.data.state)) {
                await record.load();
                this.refreshWarning = false;
            }
        } catch {
            if (!this.stopped && !this.refreshWarning) {
                this.notification.add(
                    _t("No se pudo actualizar el avance. Se reintentará automáticamente."),
                    { type: "warning" }
                );
                this.refreshWarning = true;
            }
        } finally {
            this.scheduleRefresh();
        }
    }
}

registry.category("fields").add("barcode_background_progress", {
    ...progressBarField,
    component: BarcodeBackgroundProgress,
});
