import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getProductName(product) {
        const name = super.getProductName(...arguments);
        const reference = product.default_code;
        const mode =
            this.pos.config.ickab_pos_product_label_mode ||
            this.pos.config.product_label_mode ||
            "both";
        if (mode === "reference") {
            return reference || name;
        }
        if (mode === "both" && reference) {
            return name + " [" + reference + "]";
        }
        return name;
    },
});
