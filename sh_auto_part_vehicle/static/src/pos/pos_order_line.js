/*
 * ICKAB Auto Parts & Vehicle Management
 * Línea de pedido del POS: marca y datos de identificación del producto
 * (referencia interna y nombre) para pantalla y recibo.
 */
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

Orderline.props.line.shape.productBrandName = { type: String, optional: true };
Orderline.props.line.shape.internalReference = { type: String, optional: true };
Orderline.props.line.shape.receiptProductName = { type: String, optional: true };

patch(PosOrderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(...arguments),
            productBrandName: this.product_id.ickab_brand_name || "",
            internalReference: this.product_id.default_code || "",
            receiptProductName: this.product_id.name || "",
        };
    },
    get_full_product_name() {
        const name =
            super.get_full_product_name(...arguments) ||
            this.product_id?.display_name ||
            "";
        const reference = this.product_id?.default_code || "";
        const mode = this.config?.ickab_pos_product_label_mode || "both";
        if (mode === "reference") {
            return reference || name;
        }
        if (mode === "both" && reference) {
            return name + " [" + reference + "]";
        }
        return name;
    },
});
