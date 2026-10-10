/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import {
    SaleOrderLineProductField,
    saleOrderLineProductField,
} from "@sale/js/sale_product_field";

import { CompatibilityDialog } from "./compatibility_dialog";
import { StockDialog } from "./stock_dialog";

/**
 * Automotive parts panel displayed on the side of the sale order form.
 *
 * It consumes the (non stored) ``x_auto_panel`` JSON field computed by
 * ``sale.order`` and renders grouped product suggestions. Each card can be
 * added to the current quotation or open the compatibility rules of the
 * product.
 */
export class AutoPartsPanel extends Component {
    static template = "ick_auto_part_vehicle_extends_sale.AutoPartsPanel";
    static props = {
        record: Object,
    };

    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({ addingProductId: false });
    }

    get panel() {
        return this.props.record.data.x_auto_panel || {};
    }

    get activeProduct() {
        return this.panel.active_product || null;
    }

    get isLocked() {
        return Boolean(
            this.props.record.data.blocked_order ||
            this.props.record.data.locked ||
            !["draft", "sent"].includes(this.props.record.data.state)
        );
    }

    get sections() {
        const panel = this.panel;
        return [
            {
                key: "compatible",
                label: "Piezas compatibles",
                icon: "fa-check-circle",
                empty: "Sin otras piezas para las aplicaciones de este producto.",
                items: panel.compatible || [],
            },
            {
                key: "equivalents",
                label: "Equivalencias OEM",
                icon: "fa-barcode",
                empty: "Sin equivalencias por código OEM.",
                items: panel.equivalents || [],
            },
            {
                key: "optional",
                label: "Opcionales",
                icon: "fa-plus-circle",
                empty: "Sin productos opcionales sugeridos.",
                items: panel.optional || [],
            },
            {
                key: "accessories",
                label: "Accesorios",
                icon: "fa-puzzle-piece",
                empty: "Sin accesorios sugeridos.",
                items: panel.accessories || [],
            },
            {
                key: "alternatives",
                label: "Alternativas",
                icon: "fa-exchange",
                empty: "Sin alternativas sugeridas.",
                items: panel.alternatives || [],
            },
        ];
    }

    get visibleSections() {
        return this.sections.filter((section) => section.items.length);
    }

    get hasRecommendations() {
        return this.visibleSections.length > 0;
    }

    money(value) {
        const currencyData = this.props.record.data.currency_id;
        const currency = (currencyData && currencyData.display_name) || "MXN";
        const amount = value || 0;
        try {
            return new Intl.NumberFormat(undefined, {
                style: "currency",
                currency,
            }).format(amount);
        } catch {
            return `${amount.toFixed(2)} ${currency}`;
        }
    }

    quantity(value, uom) {
        const quantity = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 3,
        }).format(value || 0);
        return uom ? `${quantity} ${uom}` : quantity;
    }

    /**
     * @param {MouseEvent} ev
     */
    async onAdd(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.isLocked) {
            this.notification.add(
                "La cotización está bloqueada. Solicite autorización para editarla.",
                { type: "warning" }
            );
            return;
        }
        const productId = parseInt(ev.currentTarget.dataset.productId, 10);
        const record = this.props.record;
        if (this.state.addingProductId) {
            return;
        }
        const addedProduct = this.sections
            .flatMap((section) => section.items)
            .find((product) => product.id === productId);
        if (!addedProduct) {
            this.notification.add("El producto sugerido ya no está disponible.", {
                type: "warning",
            });
            return;
        }
        this.state.addingProductId = productId;
        try {
            const orderLines = record.data.order_line;
            await orderLines.leaveEditMode();
            const existingLine = orderLines.records.find(
                (line) =>
                    !line.data.display_type &&
                    line.data.product_id?.[0] === productId
            );
            if (existingLine) {
                await existingLine.update({
                    product_uom_qty: (existingLine.data.product_uom_qty || 0) + 1,
                });
            } else {
                const line = await orderLines.addNewRecord({
                    position: "bottom",
                    mode: "readonly",
                });
                await line.update({
                    product_id: [productId, addedProduct.name || ""],
                    product_uom_qty: 1,
                });
            }
            this.notification.add("Producto agregado. La cotización continúa sin guardar.", {
                type: "success",
            });
        } catch (error) {
            this.notification.add(
                error?.message || "No fue posible agregar el producto.",
                { type: "danger" }
            );
        } finally {
            this.state.addingProductId = false;
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    async onCompatibility(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productId, 10);
        const item = this.sections
            .flatMap((section) => section.items)
            .find((product) => product.id === productId);
        this.dialog.add(CompatibilityDialog, {
            productId,
            productName: item?.name || "",
        });
    }

    onStock(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productId, 10);
        const item = this.sections
            .flatMap((section) => section.items)
            .find((product) => product.id === productId);
        this.dialog.add(StockDialog, {
            productId,
            productName: item?.name || "",
            companyId: this.props.record.data.company_id?.[0],
        });
    }
}

/**
 * Product selector dedicated to the automotive quotation workspace.
 *
 * Optional products are rendered by AutoPartsPanel. A single-variant part is
 * therefore selected directly instead of opening Odoo's optional-product
 * configurator. Configurable attributes, combos and explicit edits continue
 * through the native configurator.
 */
export class AutoSaleOrderLineProductField extends SaleOrderLineProductField {
    async _onProductUpdate() {
        await super._onProductUpdate(...arguments);
        const product = this.props.record.data.product_id;
        if (product) {
            await this.props.record.model.root.update({
                x_auto_context_product_id: product,
            });
        }
    }

    async _openProductConfigurator(edit = false) {
        if (!edit) {
            const productTemplate = this.props.record.data.product_template_id;
            if (productTemplate) {
                const result = await this.orm.call(
                    "product.template",
                    "get_single_product_variant",
                    [productTemplate[0]],
                    { context: this.context }
                );
                if (result?.product_id && !result.is_combo) {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    await this._onProductUpdate();
                    return;
                }
            }
        }
        return super._openProductConfigurator(...arguments);
    }
}

registry.category("fields").add("ick_auto_sale_product_many2one", {
    ...saleOrderLineProductField,
    component: AutoSaleOrderLineProductField,
});
