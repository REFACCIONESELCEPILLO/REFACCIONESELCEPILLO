/** @odoo-module **/

import { Component, onWillStart, useEffect, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

const EMPTY_PANEL = {
    active_product: null,
    compatible: [],
    equivalents: [],
    optional: [],
    accessories: [],
    alternatives: [],
};

class AutoPosInfoDialog extends Component {
    static template = "ick_auto_part_vehicle_extends_pos.AutoPosInfoDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        productId: Number,
        productName: String,
        mode: { type: String, validate: (value) => ["compatibility", "stock"].includes(value) },
    };

    setup() {
        this.pos = usePos();
        this.state = useState({ loading: true, data: null, error: "" });
        onWillStart(async () => {
            const method = this.props.mode === "stock"
                ? "get_auto_product_stock"
                : "get_auto_product_compatibility";
            try {
                this.state.data = await this.pos.data.call("pos.session", method, [
                    this.pos.session.id,
                    this.props.productId,
                ]);
            } catch (error) {
                this.state.error = error?.message || "No fue posible cargar la información.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    get title() {
        return this.props.mode === "stock"
            ? `Disponibilidad: ${this.props.productName}`
            : `Compatibilidad: ${this.props.productName}`;
    }

    quantity(value, uom) {
        const quantity = new Intl.NumberFormat(undefined, {
            maximumFractionDigits: 3,
        }).format(value || 0);
        return uom ? `${quantity} ${uom}` : quantity;
    }
}

export class AutoPartsPosPanel extends Component {
    static template = "ick_auto_part_vehicle_extends_pos.AutoPartsPosPanel";
    static props = { productId: Number };

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            loading: false,
            addingProductId: false,
            requestId: 0,
            panel: { ...EMPTY_PANEL },
            open: {
                compatible: true,
                equivalents: true,
                optional: true,
                accessories: false,
                alternatives: false,
            },
        });

        useEffect(
            (productId) => {
                this.loadPanel(productId);
            },
            () => [this.props.productId]
        );
    }

    get primarySections() {
        return [
            { key: "compatible", label: "Piezas compatibles", items: this.state.panel.compatible },
            { key: "equivalents", label: "Equivalencias OEM", items: this.state.panel.equivalents },
        ];
    }

    get suggestedSections() {
        return [
            { key: "optional", label: "Opcionales", items: this.state.panel.optional },
            { key: "accessories", label: "Accesorios", items: this.state.panel.accessories },
            { key: "alternatives", label: "Productos alternos", items: this.state.panel.alternatives },
        ];
    }

    get hasAnySuggestion() {
        return [...this.primarySections, ...this.suggestedSections].some(
            (section) => section.items.length
        );
    }

    async loadPanel(productId) {
        const requestId = ++this.state.requestId;
        if (!productId) {
            this.state.panel = { ...EMPTY_PANEL };
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        try {
            const panel = await this.pos.data.call(
                "pos.session",
                "get_auto_parts_panel",
                [this.pos.session.id, productId]
            );
            if (requestId === this.state.requestId) {
                this.state.panel = panel;
            }
        } catch (error) {
            if (requestId === this.state.requestId) {
                this.state.panel = { ...EMPTY_PANEL };
                this.notification.add(
                    error?.message || "No fue posible cargar las recomendaciones.",
                    { type: "danger" }
                );
            }
        } finally {
            if (requestId === this.state.requestId) {
                this.state.loading = false;
            }
        }
    }

    toggle(sectionKey) {
        this.state.open[sectionKey] = !this.state.open[sectionKey];
    }

    productRecord(item) {
        return this.pos.models["product.product"].get(item.id);
    }

    price(item) {
        const product = this.productRecord(item);
        return product ? this.pos.getProductPriceFormatted(product) : "";
    }

    quantity(item) {
        const value = new Intl.NumberFormat(undefined, {
            maximumFractionDigits: 3,
        }).format(item.available_qty || 0);
        return item.uom ? `${value} ${item.uom}` : value;
    }

    async add(item) {
        if (this.state.addingProductId) {
            return;
        }
        const product = this.productRecord(item);
        if (!product) {
            this.notification.add("El producto no está disponible en este punto de venta.", {
                type: "warning",
            });
            return;
        }
        this.state.addingProductId = item.id;
        try {
            await this.pos.addLineToCurrentOrder({ product_id: product }, {});
            this.notification.add("Producto agregado a la orden.", { type: "success" });
        } finally {
            this.state.addingProductId = false;
        }
    }

    showCompatibility(item) {
        this.dialog.add(AutoPosInfoDialog, {
            productId: item.id,
            productName: item.name,
            mode: "compatibility",
        });
    }

    showStock(item) {
        this.dialog.add(AutoPosInfoDialog, {
            productId: item.id,
            productName: item.name,
            mode: "stock",
        });
    }
}

patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        AutoPartsPosPanel,
    },
});

patch(ProductScreen.prototype, {
    get autoContextProductId() {
        const line = this.currentOrder?.get_selected_orderline();
        return line?.product_id?.id || 0;
    },
});
