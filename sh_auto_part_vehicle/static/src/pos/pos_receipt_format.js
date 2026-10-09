/*
 * ICKAB Auto Parts & Vehicle Management
 * Formato del recibo POS (ancho de papel, tipografía y logo).
 */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    get ickabReceiptStyle() {
        const config = this.pos.config;
        const paperWidth = config.ickab_receipt_paper_width === "58" ? "58mm" : "80mm";
        const rasterWidth = config.ickab_receipt_paper_width === "58" ? "384px" : "512px";
        const lineHeight = config.ickab_receipt_line_height === "compact" ? 1.15 : 1.35;
        return [
            "--ickab-receipt-paper-width: " + paperWidth,
            "--ickab-receipt-raster-width: " + rasterWidth,
            "--ickab-receipt-font-size: " + config.ickab_receipt_font_size + "px",
            "--ickab-receipt-line-height: " + lineHeight,
            "--ickab-receipt-logo-height: " + config.ickab_receipt_logo_height + "px",
        ].join("; ");
    },
});
