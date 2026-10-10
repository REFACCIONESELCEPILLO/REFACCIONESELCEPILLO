/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

class CompatibilityProductStockDialog extends Component {
    static template = "sh_auto_part_vehicle_extends.CompatibilityProductStockDialog";
    static components = { Dialog };
    static props = { close: Function, productId: Number };

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

class CompatibilityDialog extends Component {
    static template = "sh_auto_part_vehicle_extends.CompatibilityDialog";
    static components = { Dialog };
    static props = { close: Function, templateId: Number, oemLineId: Number };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({ loading: true, error: false, data: null });
        onWillStart(async () => {
            try {
                const data = await this.orm.call(
                    "product.template",
                    "get_ick_kanban_compatibility",
                    [[this.props.templateId]],
                    { oem_line_id: this.props.oemLineId }
                );
                if (!Array.isArray(data.rows)) {
                    data.rows = await this.loadCompatibilityRows(data.code);
                    data.product_count = new Set(
                        data.rows.map((row) => row.product.id)
                    ).size;
                }
                this.state.data = data;
            } catch (error) {
                this.state.error = error?.message || "No fue posible consultar la compatibilidad.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    quantity(product) {
        const quantity = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 3,
        }).format(product.available_qty || 0);
        return product.uom ? `${quantity} ${product.uom}` : quantity;
    }

    openStock(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.dialog.add(CompatibilityProductStockDialog, {
            productId: parseInt(ev.currentTarget.dataset.productId, 10),
        });
    }

    async loadCompatibilityRows(code) {
        if (!code) {
            return [];
        }
        const products = await this.orm.searchRead(
            "product.product",
            [["default_code", "=", code.trim()]],
            ["display_name", "default_code", "brand"]
        );
        const rows = [];
        for (const product of products) {
            const vehicles = await this.orm.searchRead(
                "motorcycle.motorcycle",
                [["product_ids", "in", [product.id]]],
                ["make_id", "mmodel_id", "type_id", "year_id", "end_year_id"]
            );
            const productValues = {
                id: product.id,
                name: product.display_name || "",
                sku: product.default_code || "",
                brand: product.brand?.[1] || "",
                available_qty: 0,
                uom: "",
                image_url: `/web/image/product.product/${product.id}/image_128`,
            };
            if (vehicles.length) {
                for (const vehicle of vehicles) {
                    rows.push({
                        key: `${product.id}-${vehicle.id}`,
                        product: productValues,
                        vehicle: {
                            id: vehicle.id,
                            make: vehicle.make_id?.[1] || "",
                            model: vehicle.mmodel_id?.[1] || "",
                            type: vehicle.type_id?.[1] || "",
                            year_from: vehicle.year_id?.[1] || "",
                            year_to: vehicle.end_year_id?.[1] || "",
                        },
                    });
                }
            } else {
                rows.push({
                    key: `${product.id}-none`,
                    product: productValues,
                    vehicle: false,
                });
            }
        }
        return rows;
    }
}

class CompatibilityListDialog extends Component {
    static template = "sh_auto_part_vehicle_extends.CompatibilityListDialog";
    static components = { Dialog };
    static props = { close: Function, templateId: Number, codes: Array };

    setup() {
        this.dialog = useService("dialog");
    }

    openCompatibility(ev, code) {
        ev.preventDefault();
        ev.stopPropagation();
        this.props.close();
        this.dialog.add(CompatibilityDialog, {
            templateId: this.props.templateId,
            oemLineId: code.id,
        });
    }
}

export class KanbanCompatibility extends Component {
    static template = "sh_auto_part_vehicle_extends.KanbanCompatibility";
    static props = { ...standardFieldProps };

    setup() {
        this.dialog = useService("dialog");
    }

    get codes() {
        return this.props.record.data[this.props.name] || [];
    }

    get visibleCodes() {
        return this.codes.slice(0, 3);
    }

    get hiddenCodeCount() {
        return Math.max(this.codes.length - this.visibleCodes.length, 0);
    }

    stop(ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }

    openCompatibility(ev, code) {
        this.stop(ev);
        this.dialog.add(CompatibilityDialog, {
            templateId: this.props.record.resId,
            oemLineId: code.id,
        });
    }

    openCompatibilityList(ev) {
        this.stop(ev);
        this.dialog.add(CompatibilityListDialog, {
            templateId: this.props.record.resId,
            codes: this.codes,
        });
    }
}

registry.category("fields").add("ick_vehicle_kanban_compatibility", {
    component: KanbanCompatibility,
    supportedTypes: ["json"],
});
