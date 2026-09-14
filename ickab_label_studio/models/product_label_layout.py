# Copyright 2026 ICKAB. All rights reserved.
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    def _ickab_studio_check_user(self):
        if not (
            self.env.user.has_group("ickab_label_studio.group_label_studio_user")
            or self.env.user.has_group("base.group_system")
        ):
            raise UserError(_("No tiene permisos para utilizar ICKAB Label Studio."))

    print_format = fields.Selection(
        selection_add=[("ickab_label_studio", "ICKAB Label Studio")],
        ondelete={"ickab_label_studio": "set default"},
    )
    ickab_label_template_id = fields.Many2one(
        "ickab.label.template",
        string="Diseño de etiqueta",
        domain="[('model_id.model', 'in', ['product.product', 'product.template'])]",
    )

    def _ickab_studio_source_quantities(self):
        self.ensure_one()
        if self.custom_quantity <= 0:
            raise UserError(_("La cantidad de etiquetas debe ser mayor que cero."))
        if self.product_tmpl_ids:
            return "product.template", {record.id: self.custom_quantity for record in self.product_tmpl_ids}
        if self.product_ids:
            return "product.product", {record.id: self.custom_quantity for record in self.product_ids}
        raise UserError(_("No hay productos para generar etiquetas."))

    def _ickab_studio_prepare_data(self):
        self.ensure_one()
        self._ickab_studio_check_user()
        template = self.ickab_label_template_id
        if not template:
            raise UserError(_("Seleccione un diseño de ICKAB Label Studio."))
        target_model = template.model_id.model
        if target_model not in {"product.product", "product.template"}:
            raise UserError(_("El diseño seleccionado no está configurado para productos."))

        source_model, source_quantities = self._ickab_studio_source_quantities()
        target_quantities = defaultdict(int)
        if source_model == target_model:
            target_quantities.update(source_quantities)
        elif source_model == "product.product" and target_model == "product.template":
            for product_id, qty in source_quantities.items():
                product = self.env["product.product"].browse(product_id).exists()
                if product:
                    target_quantities[product.product_tmpl_id.id] += qty
        elif source_model == "product.template" and target_model == "product.product":
            for tmpl_id, qty in source_quantities.items():
                product_tmpl = self.env["product.template"].browse(tmpl_id).exists()
                variants = product_tmpl.product_variant_ids
                if len(variants) != 1:
                    raise UserError(_(
                        "El producto '%(product)s' tiene %(count)s variantes. "
                        "Seleccione variantes específicas o use un diseño basado en Plantilla de producto.",
                        product=product_tmpl.display_name,
                        count=len(variants),
                    ))
                target_quantities[variants.id] += qty
        else:
            raise UserError(_("Los productos seleccionados no corresponden al modelo del diseño."))

        quantities = {record_id: qty for record_id, qty in target_quantities.items() if qty > 0}
        if not quantities:
            raise UserError(_("No hay cantidades positivas para generar etiquetas."))
        return {
            "template_id": template.id,
            "active_model": target_model,
            "quantity_by_record": quantities,
            "label_dpi": int(template.dpi or 203),
        }

    def _prepare_report_data(self):
        if self.print_format != "ickab_label_studio":
            return super()._prepare_report_data()
        return "ickab_label_studio.action_report_label_zpl", self._ickab_studio_prepare_data()

    def process(self):
        self.ensure_one()
        if self.print_format != "ickab_label_studio":
            return super().process()
        data = self._ickab_studio_prepare_data()
        template = self.ickab_label_template_id

        # Optional embedded integration: when Direct Print is installed and the
        # current user has its print permission, hand the finished Studio design
        # to Direct Print. Studio never chooses ZPL/TSPL or a printer itself.
        if template._direct_print_runtime_available() and template._direct_print_user_allowed():
            report = self.env.ref("ickab_label_studio.action_report_label_zpl")
            template._direct_print_configure_report(report)
            data = template._direct_print_prepare_data(data)
            return report.report_action(None, data=data, config=False)

        # Standalone Label Studio behavior is intentionally preserved.
        return {
            "type": "ir.actions.act_url",
            "url": f"/ickab_label_studio/zpl/product_layout/{self.id}",
            "target": "self",
        }

    def action_ickab_label_preview(self):
        self.ensure_one()
        if self.print_format != "ickab_label_studio":
            raise UserError(_("Seleccione el formato ICKAB Label Studio."))
        return self.env.ref("ickab_label_studio.action_report_label_preview").report_action(
            None, data=self._ickab_studio_prepare_data(), config=False
        )
