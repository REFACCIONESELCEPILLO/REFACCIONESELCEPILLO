# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _ickab_render_payload(self, res_ids=None, data=None, printer=None):
        """Render autopart labels in the native language of the selected printer.

        Direct Print transports bytes but deliberately does not translate printer
        languages.  This module owns the label design, so it is also responsible
        for choosing the correct renderer (ZPL or TSPL) after the user selects a
        printer in the Direct Print wizard.
        """
        self.ensure_one()
        if self.report_name != "sh_auto_part_vehicle_labels.report_auto_part_label_zpl":
            return super()._ickab_render_payload(res_ids=res_ids, data=data, printer=printer)

        if not printer:
            raise UserError(_("Debe seleccionar una impresora para generar la etiqueta."))

        language = printer.language or "raw"
        if language not in ("zpl", "tspl"):
            raise UserError(_(
                "La impresora %(printer)s utiliza %(language)s. "
                "Las etiquetas de autopartes actualmente soportan ZPL/ZPL II y TSPL/TSPL2."
            ) % {
                "printer": printer.display_name,
                "language": language.upper(),
            })

        data = dict(data or {})
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
        if printer.dpi in ("203", "300", "600"):
            dpi = int(printer.dpi)
        else:
            dpi = int(data.get("label_dpi") or (wizard.label_dpi if wizard else 203) or 203)

        renderer = self.env["sh.auto.part.vehicle.label.renderer"]
        if language == "zpl":
            return "zpl", renderer.render_zpl_job(
                records_with_qty,
                print_format,
                dpi=dpi,
                company=self.env.company,
                printer=printer,
            )

        # TSPL uses native TEXT/BARCODE commands. Direct Print transports
        # the resulting RAW bytes without converting languages.
        paper = self.env["ickab.print.paper"]
        paper_code = data.get("ickab_paper_code")
        if paper_code:
            paper = self.env["ickab.print.paper"].search([
                ("code", "=", paper_code),
                "|", ("company_id", "=", False), ("company_id", "=", self.env.company.id),
            ], limit=1)
        return "tspl", renderer.render_tspl_job(
            records_with_qty,
            print_format,
            dpi=dpi,
            company=self.env.company,
            printer=printer,
            paper=paper,
        )
