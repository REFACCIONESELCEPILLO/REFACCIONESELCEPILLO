from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    dimension_attribute_id = fields.Many2one(
        "product.attribute",
        string="Atributo configurable",
        compute="_compute_dimension_attribute_id",
        compute_sudo=True,
    )
    dimension_attribute_value_id = fields.Many2one(
        "product.attribute.value",
        string="Valor del atributo",
        domain="[('attribute_id', '=', dimension_attribute_id)]",
        help=(
            "Restringe esta tarifa de proveedor a la variante exacta que representa "
            "el valor seleccionado."
        ),
    )

    @api.depends(
        "product_tmpl_id",
        "product_tmpl_id.attribute_line_ids.attribute_id",
        "product_tmpl_id.attribute_line_ids.attribute_id.component_required",
    )
    def _compute_dimension_attribute_id(self):
        BomLine = self.env["mrp.bom.line"].sudo()
        for seller in self:
            attributes = seller.product_tmpl_id.attribute_line_ids.attribute_id.filtered(
                "component_required"
            )
            if len(attributes) != 1 and seller.product_tmpl_id:
                bom_lines = BomLine.search([
                    ("product_id.product_tmpl_id", "=", seller.product_tmpl_id.id),
                    ("dimension_attribute_id", "!=", False),
                ])
                attributes |= bom_lines.dimension_attribute_id
            seller.dimension_attribute_id = attributes if len(attributes) == 1 else False

    def _get_dimension_bom_line(self):
        self.ensure_one()
        if not self.product_tmpl_id or not self.dimension_attribute_value_id:
            return self.env["mrp.bom.line"]
        return self.env["mrp.bom.line"].sudo().search([
            ("product_id.product_tmpl_id", "=", self.product_tmpl_id.id),
            (
                "dimension_attribute_id",
                "=",
                self.dimension_attribute_value_id.attribute_id.id,
            ),
        ], order="id", limit=1)

    def _sync_dimension_product_variant(self):
        if self.env.context.get("skip_dimension_supplier_sync"):
            return
        for seller in self.filtered("dimension_attribute_value_id"):
            bom_line = seller._get_dimension_bom_line()
            if not bom_line:
                raise ValidationError(_(
                    "No se encontró una línea (Base) de lista de materiales vinculada "
                    "al atributo %(attribute)s para %(product)s.",
                    attribute=seller.dimension_attribute_value_id.attribute_id.display_name,
                    product=seller.product_tmpl_id.display_name,
                ))
            if seller.dimension_attribute_value_id.attribute_id.create_variant == "no_variant":
                raise ValidationError(_(
                    "El atributo %(attribute)s debe crear variantes de forma instantánea "
                    "o dinámica para asignar proveedores por valor.",
                    attribute=seller.dimension_attribute_value_id.attribute_id.display_name,
                ))
            component = seller.dimension_attribute_value_id._get_or_create_bom_component(
                bom_line
            )
            if not component:
                raise ValidationError(_(
                    "No fue posible generar la variante de compra para %(value)s en "
                    "%(product)s. Revise la configuración de atributos del producto Base.",
                    value=seller.dimension_attribute_value_id.display_name,
                    product=seller.product_tmpl_id.display_name,
                ))
            if seller.product_id != component:
                seller.with_context(skip_dimension_supplier_sync=True).sudo().write({
                    "product_id": component.id,
                })

    @api.model_create_multi
    def create(self, values_list):
        sellers = super().create(values_list)
        sellers._sync_dimension_product_variant()
        return sellers

    def write(self, values):
        sync_dimension_variant = bool({
            "product_tmpl_id",
            "dimension_attribute_value_id",
        }.intersection(values))
        sellers_to_generalize = self.env[self._name]
        if (
            "dimension_attribute_value_id" in values
            and not values["dimension_attribute_value_id"]
        ):
            sellers_to_generalize = self.filtered("dimension_attribute_value_id")
        # Odoo's supplierinfo sanitizer adds product_tmpl_id to the received dict
        # whenever product_id is written. Work with a copy and keep the original
        # trigger above, otherwise that internal addition starts a sync loop.
        result = super().write(dict(values))
        if sellers_to_generalize:
            sellers_to_generalize.with_context(
                skip_dimension_supplier_sync=True
            ).sudo().write({"product_id": False})
        if sync_dimension_variant:
            self._sync_dimension_product_variant()
        return result

    @api.constrains("dimension_attribute_value_id", "product_tmpl_id")
    def _check_dimension_attribute_value(self):
        for seller in self.filtered("dimension_attribute_value_id"):
            if (
                seller.dimension_attribute_id
                and seller.dimension_attribute_value_id.attribute_id
                != seller.dimension_attribute_id
            ):
                raise ValidationError(_(
                    "El valor %(value)s no pertenece al atributo configurable "
                    "%(attribute)s del producto Base.",
                    value=seller.dimension_attribute_value_id.display_name,
                    attribute=seller.dimension_attribute_id.display_name,
                ))
