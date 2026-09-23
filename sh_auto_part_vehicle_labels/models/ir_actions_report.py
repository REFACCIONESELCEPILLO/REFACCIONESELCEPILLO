# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _ickab_prepare_print_source(self, res_ids=None, data=None):
        """Hand the fixed autopart layout to Direct Print without choosing a language."""
        if self.report_name != "sh_auto_part_vehicle_labels.report_auto_part_label_zpl":
            return super()._ickab_prepare_print_source(res_ids=res_ids, data=data)

        data = data or {}
        active_model = data.get("active_model")
        if active_model not in ("product.product", "product.template"):
            raise UserError(_("No se pudo determinar el modelo de producto para imprimir la etiqueta."))

        Product = self.env[active_model]
        records_with_qty = []
        for product_id, quantity in (data.get("quantity_by_product") or {}).items():
            try:
                product_id = int(product_id)
                quantity = int(quantity or 0)
            except (TypeError, ValueError):
                continue
            if quantity <= 0:
                continue
            record = Product.browse(product_id).exists()
            if record:
                record.check_access("read")
                records_with_qty.append((record, quantity))
        if not records_with_qty:
            raise UserError(_("No hay productos con cantidad positiva para imprimir."))

        wizard = self.env["product.label.layout"].browse(data.get("layout_wizard")).exists()
        print_format = data.get("auto_part_label_format") or (
            wizard.print_format if wizard else "auto_part_zpl_70_50"
        )
        return self.env["sh.auto.part.vehicle.label.renderer"].build_print_source(
            records_with_qty, print_format
        )
