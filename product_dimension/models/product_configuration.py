from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ProductTemplate(models.Model):
    _inherit = "product.template"

    dimension_enabled = fields.Boolean(
        "Configuración dimensional Mocalli",
        help="Calcula el precio por dimensiones y genera los componentes configurados en fabricación.",
    )

    def _apply_dimension_pricelist_price(
        self,
        base_price,
        product,
        pricelist,
        quantity,
        uom,
        date,
        company,
    ):
        """Apply an Odoo pricelist rule directly to a dimensional unit price."""
        self.ensure_one()
        product_uom = product.uom_id
        if product_uom != uom:
            base_price = product_uom._compute_price(base_price, uom)
        if not pricelist:
            return base_price

        currency = pricelist.currency_id
        price = self.currency_id._convert(
            base_price,
            currency,
            company,
            date,
            round=False,
        )
        rule_id = pricelist._get_product_rule(
            product,
            quantity or 1.0,
            currency=currency,
            uom=uom,
            date=date,
        )
        rule = self.env["product.pricelist.item"].browse(rule_id)
        if not rule:
            return price

        convert_uom_price = (
            (lambda amount: product_uom._compute_price(amount, uom))
            if product_uom != uom
            else (lambda amount: amount)
        )
        if rule.compute_price == "fixed":
            return convert_uom_price(rule.fixed_price)
        if rule.compute_price == "percentage":
            return price * (1.0 - (rule.percent_price / 100.0))

        price_limit = price
        discount = rule.price_discount
        if rule.base == "standard_price":
            discount = -rule.price_markup
        price *= 1.0 - (discount / 100.0)
        if rule.price_round:
            price = float_round(price, precision_rounding=rule.price_round)
        if rule.price_surcharge:
            price += convert_uom_price(rule.price_surcharge)
        if rule.price_min_margin:
            price = max(price, price_limit + convert_uom_price(rule.price_min_margin))
        if rule.price_max_margin:
            price = min(price, price_limit + convert_uom_price(rule.price_max_margin))
        return price


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    dimension_type = fields.Selection([
        ("area", "Área (m²)"),
        ("perimeter", "Perímetro (ml)"),
        ("none", "Normal"),
    ], string="Tipo de cálculo", default="none", required=True)
    component_required = fields.Boolean(
        "Requiere componente",
        help="Exige que cada valor seleccionado apunte a un producto componente o esté marcado como N/A.",
    )


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    component_product_id = fields.Many2one(
        "product.product",
        string="Producto componente",
        domain="[('type', '=', 'consu')]",
        help="Producto o variante real que se consumirá y abastecerá al seleccionar este valor.",
    )
    component_internal_reference = fields.Char(
        string="Referencia interna",
        index=True,
        help="Referencia interna del valor configurable.",
    )
    component_cost_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_component_cost_currency_id",
        readonly=True,
    )
    component_cost = fields.Float(
        string="Costo",
        digits="Product Price",
        groups="base.group_user",
        help="Costo de referencia del valor configurable.",
    )
    component_calculation = fields.Selection([
        ("attribute", "Según atributo"),
        ("area", "Área (m²)"),
        ("perimeter", "Perímetro (ml)"),
        ("unit", "Unidad"),
    ], string="Cálculo del componente", default="attribute", required=True)
    component_qty_factor = fields.Float(
        "Factor de consumo",
        default=1.0,
        digits="Product Unit of Measure",
        help="Multiplicador aplicado al área, perímetro o número de piezas.",
    )
    skip_component = fields.Boolean(
        "No genera componente (N/A)",
        help="El valor puede seleccionarse, pero no agrega materia prima a la orden de fabricación.",
    )

    @api.depends("component_product_id.cost_currency_id")
    @api.depends_context("company")
    def _compute_component_cost_currency_id(self):
        company_currency = self.env.company.currency_id
        for value in self:
            value.component_cost_currency_id = (
                value.component_product_id.cost_currency_id or company_currency
            )

    @api.onchange("component_product_id")
    def _onchange_component_product_id(self):
        for value in self.filtered("component_product_id"):
            if not value.component_internal_reference:
                value.component_internal_reference = value.component_product_id.default_code
            if not value.component_cost:
                value.component_cost = value.component_product_id.standard_price

    @api.model
    def _add_component_defaults(self, vals, current_value=None):
        vals = dict(vals)
        if vals.get("component_product_id"):
            component = self.env["product.product"].browse(vals["component_product_id"])
            if (
                "component_internal_reference" not in vals
                and not (current_value and current_value.component_internal_reference)
            ):
                vals["component_internal_reference"] = component.default_code
            if (
                "component_cost" not in vals
                and not (current_value and current_value.component_cost)
            ):
                vals["component_cost"] = component.standard_price
        return vals

    def _sync_component_metadata(self, field_names):
        for value in self.filtered("component_product_id"):
            component_vals = {}
            if "component_internal_reference" in field_names:
                component_vals["default_code"] = value.component_internal_reference
            if "component_cost" in field_names:
                component_vals["standard_price"] = value.component_cost
            if component_vals:
                value.component_product_id.write(component_vals)

    @api.model_create_multi
    def create(self, vals_list):
        values = super().create([
            self._add_component_defaults(vals, self.env[self._name])
            for vals in vals_list
        ])
        for value, vals in zip(values, vals_list):
            synchronized_fields = {
                field_name
                for field_name in ("component_internal_reference", "component_cost")
                if field_name in vals
            }
            value._sync_component_metadata(synchronized_fields)
        return values

    def write(self, vals):
        if "component_product_id" in vals and len(self) > 1:
            return all(value.write(vals) for value in self)
        prepared_vals = self._add_component_defaults(vals, self[:1])
        result = super().write(prepared_vals)
        synchronized_fields = {
            field_name
            for field_name in ("component_internal_reference", "component_cost")
            if field_name in prepared_vals
        }
        if vals.get("component_product_id"):
            synchronized_fields.update(("component_internal_reference", "component_cost"))
        self._sync_component_metadata(synchronized_fields)
        return result

    def action_open_dimension_configuration(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Configurar valor de atributo"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [(
                self.env.ref(
                    "product_dimension.product_attribute_value_form_dimension_mocalli"
                ).id,
                "form",
            )],
            "target": "current",
        }

    @api.constrains("component_product_id", "component_qty_factor", "skip_component")
    def _check_component_configuration(self):
        for value in self:
            if value.component_product_id and value.skip_component:
                raise ValidationError(_(
                    "%(value)s no puede tener producto componente y estar marcado como N/A al mismo tiempo.",
                    value=value.display_name,
                ))
            if value.component_product_id and value.component_qty_factor <= 0.0:
                raise ValidationError(_(
                    "El factor de consumo de %(value)s debe ser mayor que cero.",
                    value=value.display_name,
                ))


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    dimension_price = fields.Float("Precio dimensional", digits="Product Price")
    pricing_mode = fields.Selection([
        ("attribute", "Según atributo (compatibilidad)"),
        ("included", "Incluido / sin cargo"),
        ("fixed", "Precio fijo"),
        ("area", "Precio por área"),
        ("perimeter", "Precio por perímetro"),
    ], string="Modo de precio", default="attribute", required=True)
    component_product_id = fields.Many2one(
        related="product_attribute_value_id.component_product_id",
        string="Producto componente",
        domain="[('type', '=', 'consu')]",
        readonly=False,
        help="Producto o variante real que se consumirá y abastecerá para este valor.",
    )
    component_sku = fields.Char(
        related="product_attribute_value_id.component_internal_reference",
        string="Referencia interna",
        readonly=False,
    )
    component_cost_currency_id = fields.Many2one(
        related="product_attribute_value_id.component_cost_currency_id",
        readonly=True,
    )
    component_cost = fields.Float(
        related="product_attribute_value_id.component_cost",
        string="Costo",
        digits="Product Price",
        readonly=False,
        groups="base.group_user",
        help="Costo de referencia del valor configurable.",
    )
    component_calculation = fields.Selection(
        related="product_attribute_value_id.component_calculation",
        readonly=False,
    )
    component_qty_factor = fields.Float(
        related="product_attribute_value_id.component_qty_factor",
        readonly=False,
    )
    skip_component = fields.Boolean(
        related="product_attribute_value_id.skip_component",
        readonly=False,
    )

    @api.depends("name", "component_sku")
    def _compute_display_name(self):
        super()._compute_display_name()
        for value in self:
            if value.component_sku:
                value.display_name = "[%s] %s" % (value.component_sku, value.display_name)

    def _get_effective_component_calculation(self):
        self.ensure_one()
        if self.component_calculation != "attribute":
            return self.component_calculation
        return {
            "area": "area",
            "perimeter": "perimeter",
            "none": "unit",
        }[self.attribute_id.dimension_type]

    def _get_component_quantity(self, area, perimeter, finished_qty):
        self.ensure_one()
        calculation = self._get_effective_component_calculation()
        measure = {
            "area": area,
            "perimeter": perimeter,
            "unit": 1.0,
        }[calculation]
        return measure * self.component_qty_factor * finished_qty

    def _get_dimension_sale_amount(self, area, perimeter):
        self.ensure_one()
        if self.pricing_mode == "included":
            return 0.0
        if self.pricing_mode == "fixed":
            return self.price_extra
        if self.pricing_mode == "area":
            return self.dimension_price * area
        if self.pricing_mode == "perimeter":
            return self.dimension_price * perimeter

        # Compatibility with the data already configured in Mocalli.
        rate = self.dimension_price or self.price_extra
        if self.attribute_id.dimension_type == "area":
            return rate * area
        if self.attribute_id.dimension_type == "perimeter":
            return rate * perimeter
        return self.price_extra
