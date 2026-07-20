from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        for order in self:
            order.order_line._validate_dimension_configuration()
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    width_cm = fields.Float("Ancho (cm)", digits=(16, 2), copy=False)
    height_cm = fields.Float("Alto (cm)", digits=(16, 2), copy=False)
    m2 = fields.Float(
        "M²",
        compute="_compute_dimensions",
        store=True,
        precompute=True,
        digits=(16, 4),
    )
    ml = fields.Float(
        "ML",
        compute="_compute_dimensions",
        store=True,
        precompute=True,
        digits=(16, 4),
    )
    dimension_base_currency_id = fields.Many2one(
        "res.currency",
        related="product_template_id.currency_id",
        string="Moneda del precio dimensional base",
    )
    base_dimension_price = fields.Monetary(
        "Precio dimensional base",
        compute="_compute_base_dimension_price",
        store=True,
        precompute=True,
        currency_field="dimension_base_currency_id",
    )
    dimension_enabled = fields.Boolean(
        related="product_template_id.dimension_enabled",
        string="Configuración dimensional",
    )

    @api.depends("width_cm", "height_cm")
    def _compute_dimensions(self):
        for line in self:
            width = line.width_cm or 0.0
            height = line.height_cm or 0.0
            line.m2 = (width * height) / 10000.0
            line.ml = ((width * 2.0) + (height * 2.0)) / 100.0

    def _get_selected_dimension_values(self):
        self.ensure_one()
        return self._get_all_selected_dimension_values().filtered(
            lambda value: value.attribute_id.component_required
            or value.component_product_id
            or value.skip_component
        )

    def _get_all_selected_dimension_values(self):
        self.ensure_one()
        return (
            self.product_template_attribute_value_ids
            | self.product_no_variant_attribute_value_ids
        )

    @api.depends(
        "product_id",
        "product_template_id.dimension_enabled",
        "product_template_id.list_price",
        "m2",
        "ml",
        "product_template_attribute_value_ids",
        "product_template_attribute_value_ids.pricing_mode",
        "product_template_attribute_value_ids.dimension_price",
        "product_template_attribute_value_ids.price_extra",
        "product_template_attribute_value_ids.attribute_id.dimension_type",
        "product_no_variant_attribute_value_ids",
        "product_no_variant_attribute_value_ids.pricing_mode",
        "product_no_variant_attribute_value_ids.dimension_price",
        "product_no_variant_attribute_value_ids.price_extra",
        "product_no_variant_attribute_value_ids.attribute_id.dimension_type",
    )
    def _compute_base_dimension_price(self):
        for line in self:
            if not line.product_id or not line.dimension_enabled:
                line.base_dimension_price = 0.0
                continue

            total_price = line.product_template_id.list_price
            for value in line._get_all_selected_dimension_values():
                total_price += value._get_dimension_sale_amount(line.m2, line.ml)
            line.base_dimension_price = total_price

    def _apply_dimension_pricelist(self, base_price):
        """Apply the selected Odoo pricelist rule to a custom dimensional base."""
        self.ensure_one()
        return self.product_template_id._apply_dimension_pricelist_price(
            base_price,
            self.product_id,
            self.order_id.pricelist_id,
            self.product_uom_qty,
            self.product_uom,
            self.order_id.date_order or fields.Datetime.now(),
            self.order_id.company_id,
        )

    @api.depends(
        "base_dimension_price",
        "product_uom_qty",
        "order_id.pricelist_id",
        "order_id.date_order",
    )
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self.filtered(lambda item: item.product_id and item.dimension_enabled):
            price = line._apply_dimension_pricelist(line.base_dimension_price)
            line.update({
                "price_unit": price,
                "technical_price_unit": price,
            })

    def _compute_discount(self):
        super()._compute_discount()
        self.filtered(lambda line: line.product_id and line.dimension_enabled).discount = 0.0

    @api.onchange("width_cm", "height_cm")
    def _onchange_dimension_description(self):
        for line in self:
            if line.product_id and line.dimension_enabled:
                base_name = line.product_id.get_product_multiline_description_sale()
                line.name = _(
                    "%(product)s (%(width).2f cm x %(height).2f cm)",
                    product=base_name,
                    width=line.width_cm,
                    height=line.height_cm,
                )

    @api.onchange(
        "width_cm",
        "height_cm",
        "product_template_attribute_value_ids",
        "product_no_variant_attribute_value_ids",
    )
    def _onchange_recompute_dimension_price(self):
        self._compute_dimensions()
        self._compute_base_dimension_price()
        self._compute_price_unit()

    def _validate_dimension_configuration(self):
        for line in self.filtered(lambda item: not item.display_type and item.dimension_enabled):
            if line.width_cm <= 0.0 or line.height_cm <= 0.0:
                raise ValidationError(_(
                    "Capture un ancho y un alto mayores que cero para %(product)s.",
                    product=line.product_id.display_name,
                ))
            selected_values = line._get_selected_dimension_values()
            required_attributes = line.product_template_id.attribute_line_ids.attribute_id.filtered(
                "component_required"
            )
            missing_attributes = required_attributes - selected_values.attribute_id
            if missing_attributes:
                raise ValidationError(_(
                    "No se puede confirmar la cotización. Falta seleccionar un valor para: %(attributes)s",
                    attributes=", ".join(missing_attributes.mapped("display_name")),
                ))
            missing_values = selected_values.filtered(
                lambda value: value.attribute_id.component_required
                and not value.skip_component
                and not value.component_product_id
            )
            if missing_values:
                raise ValidationError(_(
                    "No se puede confirmar la cotización. Los siguientes valores no tienen un "
                    "producto componente asociado: %(values)s",
                    values=", ".join(missing_values.mapped("display_name")),
                ))

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        self.ensure_one()
        if self.dimension_enabled:
            values.update({
                "dimension_sale_line_id": self.id,
                "dimension_width_cm": self.width_cm,
                "dimension_height_cm": self.height_cm,
                "dimension_m2": self.m2,
                "dimension_ml": self.ml,
                "dimension_value_ids": self._get_all_selected_dimension_values().ids,
            })
        return values

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        values.update({
            "width_cm": self.width_cm,
            "height_cm": self.height_cm,
            "m2": self.m2,
            "ml": self.ml,
        })
        return values


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    width_cm = fields.Float("Ancho (cm)", digits=(16, 2))
    height_cm = fields.Float("Alto (cm)", digits=(16, 2))
    m2 = fields.Float("M²", digits=(16, 4))
    ml = fields.Float("ML", digits=(16, 4))
