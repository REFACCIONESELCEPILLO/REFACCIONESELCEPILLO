import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    get ickabPrice() {
        return this.pos.getProductPriceFormatted(this.props.product);
    },
});

patch(ProductScreen.prototype, {
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
