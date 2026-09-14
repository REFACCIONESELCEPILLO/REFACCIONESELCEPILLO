# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import UserError


class ReportAutoPartVehicleLabelZpl(models.AbstractModel):
    _name = "report.sh_auto_part_vehicle_labels.report_auto_part_label_zpl"
    _description = "Auto Part Vehicle ZPL Label Report"

    def _get_report_values(self, docids, data=None):
        data = data or {}
        active_model = data.get("active_model")
        if active_model not in ("product.product", "product.template"):
            raise UserError(_("No se pudo determinar el modelo de producto para imprimir la etiqueta."))

        Product = self.env[active_model]
        records_with_qty = []
        for product_id, quantity in (data.get("quantity_by_product") or {}).items():
            quantity = int(quantity or 0)
            if quantity <= 0:
                continue
            record = Product.browse(int(product_id)).exists()
            if record:
                records_with_qty.append((record, quantity))

        if not records_with_qty:
            raise UserError(_("No hay productos con cantidad positiva para imprimir."))

        wizard = self.env["product.label.layout"].browse(data.get("layout_wizard")).exists()
        print_format = data.get("auto_part_label_format") or (
            wizard.print_format if wizard else "auto_part_zpl_70_50"
        )
        # En descarga normal se respeta la resolución elegida en el wizard.
        # Cuando ICKAB Direct Print interviene, éste informa la resolución REAL
        # de la impresora seleccionada mediante ickab_target_dpi. Así preview y
        # ZPL conservan las mismas medidas físicas (50x30 / 70x50 mm).
        dpi = int(
            data.get("ickab_target_dpi")
            or data.get("label_dpi")
            or (wizard.label_dpi if wizard else 203)
            or 203
        )

        renderer = self.env["sh.auto.part.vehicle.label.renderer"]
        zpl = renderer.render_zpl_job(
            records_with_qty,
            print_format,
            dpi=dpi,
            company=self.env.company,
        )
        return {
            # Markup prevents QWeb from converting characters such as '&' into
            # HTML entities in a qweb-text report.
            "zpl_content": Markup(zpl),
        }
