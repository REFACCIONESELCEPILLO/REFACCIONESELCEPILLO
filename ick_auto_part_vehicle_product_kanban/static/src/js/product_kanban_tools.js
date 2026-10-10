/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

class RelatedProductStockDialog extends Component {
    static template = "ick_auto_part_vehicle_product_kanban.RelatedProductStockDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productId: Number,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, error: false, data: null });
        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "product.template",
                    "get_ick_kanban_product_stock",
                    [],
                    { product_id: this.props.productId }
                );
            } catch (error) {
                this.state.error = error?.message || "No fue posible consultar las existencias.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    quantity(value, uom) {
        const quantity = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 3,
        }).format(value || 0);
        return uom ? `${quantity} ${uom}` : quantity;
    }
}

class RelatedProductsDialog extends Component {
    static template = "ick_auto_part_vehicle_product_kanban.RelatedProductsDialog";
    static components = { Dialog };
    static props = { close: Function, templateId: Number };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({ loading: true, error: false, data: null });
        onWillStart(async () => {
            try {
                this.state.data = await this.orm.call(
                    "product.template",
                    "get_ick_kanban_related_products",
                    [[this.props.templateId]]
                );
            } catch (error) {
                this.state.error = error?.message || "No fue posible consultar los productos relacionados.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    money(item) {
        try {
            return new Intl.NumberFormat(undefined, {
                style: "currency",
                currency: item.currency || "MXN",
            }).format(item.price || 0);
        } catch {
            return `${(item.price || 0).toFixed(2)} ${item.currency || ""}`;
        }
    }

    quantity(item) {
        const quantity = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 3,
        }).format(item.available_qty || 0);
        return item.uom ? `${quantity} ${item.uom}` : quantity;
    }

    openStock(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.dialog.add(RelatedProductStockDialog, {
            productId: parseInt(ev.currentTarget.dataset.productId, 10),
        });
    }
}

export class ProductKanbanRelated extends Component {
    static template = "ick_auto_part_vehicle_product_kanban.ProductKanbanRelated";
    static props = { ...standardFieldProps };

    setup() {
        this.dialog = useService("dialog");
    }

    openRelated(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.dialog.add(RelatedProductsDialog, {
            templateId: this.props.record.resId,
        });
    }
}

registry.category("fields").add("ick_product_kanban_related", {
    component: ProductKanbanRelated,
    supportedTypes: ["boolean"],
});
