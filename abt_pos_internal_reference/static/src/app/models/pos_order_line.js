import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get_full_product_name() {
        const name =
            super.get_full_product_name(...arguments) ||
            this.product_id?.display_name ||
            "";
        const reference = this.product_id?.default_code || "";
        const mode = this.config?.product_label_mode || "both";
        if (mode === "reference") {
            return reference || name;
        }
        if (mode === "both" && reference) {
            return name + " [" + reference + "]";
        }
        return name;
    },
});
