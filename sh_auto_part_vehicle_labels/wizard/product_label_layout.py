# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(
        selection_add=[
            ("auto_part_zpl_50_30", "Etiqueta de autoparte - 50 x 30 mm"),
            ("auto_part_zpl_70_50", "Etiqueta de autoparte - 70 x 50 mm"),
        ],
        ondelete={
            "auto_part_zpl_50_30": "set default",
            "auto_part_zpl_70_50": "set default",
        },
    )
    label_dpi = fields.Selection(
        [
            ("203", "203 dpi"),
            ("300", "300 dpi"),
        ],
        string="Resolución de etiqueta",
        default="203",
        required=True,
    )
    label_preview_html = fields.Html(
        string="Vista previa de etiqueta",
        compute="_compute_label_preview_html",
        sanitize=False,
    )

    @api.depends("print_format", "label_dpi", "product_ids", "product_tmpl_ids")
    def _compute_label_preview_html(self):
        renderer = self.env["sh.auto.part.vehicle.label.renderer"]
        for wizard in self:
            if not wizard._is_auto_part_label_format():
                wizard.label_preview_html = False
                continue

            records = wizard._get_label_source_records()
            if not records:
                wizard.label_preview_html = False
                continue

            wizard.label_preview_html = renderer.build_preview_html(
                records[0],
                wizard.print_format,
                dpi=int(wizard.label_dpi or 203),
                company=wizard.env.company,
                selected_count=len(records),
            )

    def _is_auto_part_label_format(self):
        self.ensure_one()
        return self.print_format in {
            "auto_part_zpl_50_30",
            "auto_part_zpl_70_50",
        }

    def _get_label_source_records(self):
        self.ensure_one()
        return self.product_ids or self.product_tmpl_ids

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        if not self._is_auto_part_label_format():
            return xml_id, data

        # stock.product_label_layout may have split lot-tracked quantities into
        # custom_barcodes. For this product label we print the PRODUCT barcode,
        # so fold those quantities back into quantity_by_product.
        quantity_by_product = dict(data.get("quantity_by_product") or {})
        custom_barcodes = data.get("custom_barcodes") or {}
        for product_id, barcode_qtys in custom_barcodes.items():
            key = product_id
            string_key = str(product_id)
            existing_key = key if key in quantity_by_product else string_key
            current_qty = quantity_by_product.get(existing_key, 0)
            current_qty += sum(int(qty or 0) for _barcode, qty in barcode_qtys)
            quantity_by_product[existing_key] = current_qty

        data["quantity_by_product"] = quantity_by_product
        data.pop("custom_barcodes", None)
        data["label_dpi"] = int(self.label_dpi or 203)
        data["auto_part_label_format"] = self.print_format
        paper_codes = {
            "auto_part_zpl_50_30": "LABEL_50X30",
            "auto_part_zpl_70_50": "LABEL_70X50",
        }
        data["ickab_paper_code"] = paper_codes.get(self.print_format)
        xml_id = "sh_auto_part_vehicle_labels.action_report_auto_part_label_zpl"
        return xml_id, data
