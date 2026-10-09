/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";

class AutoProductPreviewDialog extends Component {
    static template = "ick_auto_part_vehicle_extends_pos.ProductPreviewDialog";
    static components = { Dialog };
    static props = { close: Function, product: Object, specifications: Boolean };

    setup() {
        this.pos = usePos();
        this.state = useState({ loading: false, error: "", lines: [] });
        onWillStart(async () => {
            if (!this.props.specifications) return;
            this.state.loading = true;
            try {
                const result = await this.pos.data.call("pos.session", "get_auto_product_specifications", [
                    this.pos.session.id, this.props.product.id,
                ]);
                this.state.lines = result.specifications || [];
            } catch (error) {
                this.state.error = error?.message || "No fue posible consultar las especificaciones.";
            } finally {
                this.state.loading = false;
            }
        });
    }

    get imageUrl() {
        return `/web/image/product.product/${this.props.product.id}/image_1024`;
    }

    get title() {
        const label = this.props.specifications ? "Especificaciones" : "Imagen ampliada";
        return `${label}: ${this.props.product.display_name || this.props.product.name}`;
    }
}

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.autoPreviewDialog = useService("dialog");
        this.autoPreview = useState({ visible: false, style: "" });
    },
    get autoPreviewImageUrl() {
        return `/web/image/product.product/${this.props.product.id}/image_1024`;
    },
    showAutoImagePreview(event) {
        if (event.pointerType === "touch" || !this.props.imageUrl) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const size = Math.min(340, window.innerWidth - 24, window.innerHeight - 24);
        const left = rect.right + size + 12 < window.innerWidth
            ? rect.right + 12 : Math.max(12, rect.left - size - 12);
        const top = Math.max(12, Math.min(rect.top, window.innerHeight - size - 12));
        this.autoPreview.style = `left:${left}px;top:${top}px;width:${size}px;height:${size}px`;
        this.autoPreview.visible = true;
    },
    hideAutoImagePreview() {
        this.autoPreview.visible = false;
    },
    openAutoProductPreview(specifications) {
        this.hideAutoImagePreview();
        this.autoPreviewDialog.add(AutoProductPreviewDialog, {
            product: this.props.product, specifications,
        });
    },
});
