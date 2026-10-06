import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

Orderline.props.line.shape.productBrandName = { type: String, optional: true };

patch(PosOrderline.prototype, {
    getDisplayData() {
        return {
            ...super.getDisplayData(...arguments),
            productBrandName: this.product_id.brand_name || "",
        };
    },
});
