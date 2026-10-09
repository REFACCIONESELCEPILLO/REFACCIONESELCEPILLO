/*
 * ICKAB Auto Parts & Vehicle Management
 * Etiqueta de producto (referencia/nombre) y catálogo del POS.
 */
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    getProductName(product) {
        const name = super.getProductName(...arguments);
        const reference = product.default_code;
        const mode = this.pos.config.ickab_pos_product_label_mode || "both";
        if (mode === "reference") {
            return reference || name;
        }
        if (mode === "both" && reference) {
            return name + " [" + reference + "]";
        }
        return name;
    },
    get ickabCatalogStyle() {
        const config = this.pos.config;
        return [
            "--ickab-card-width: " + config.ickab_catalog_card_width + "px",
            "--ickab-image-height: " + config.ickab_catalog_image_height + "px",
            "--ickab-image-fit: " + config.ickab_catalog_image_fit,
            "--ickab-name-size: " + config.ickab_catalog_font_size + "px",
            "--ickab-name-lines: " + config.ickab_catalog_name_lines,
        ].join("; ");
    },
});
