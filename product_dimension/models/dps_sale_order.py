from odoo import _, Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_editable_dimension_quotations(self):
        """Keep dimensional quotations editable while they are quotations."""
        return self.filtered(lambda order: (
            order.state in ("draft", "sent")
            and any(
                not line.display_type and line.dimension_enabled
                for line in order.order_line
            )
        ))

    def _ensure_dimension_quotations_are_editable(self):
        """Compatibility with modules that automatically lock draft quotations.

        ``sale_restring`` adds ``blocked_order`` and sets it after every save.
        Standard Odoo keeps draft/sent quotations editable, which is required to
        reopen the product configurator and add more lines.  Do not depend on
        that optional module; only use its field when it is available.
        """
        if (
            self.env.context.get("skip_dimension_quotation_unlock")
            or "blocked_order" not in self._fields
        ):
            return
        blocked_quotations = self.sudo()._get_editable_dimension_quotations().filtered(
            "blocked_order"
        )
        if blocked_quotations:
            blocked_quotations.with_context(
                unlock=True,
                skip_dimension_quotation_unlock=True,
            ).write({"blocked_order": False})

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._ensure_dimension_quotations_are_editable()
        return orders

    def write(self, values):
        result = super().write(values)
        self._ensure_dimension_quotations_are_editable()
        return result

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
    dimension_bom_id = fields.Many2one(
        "mrp.bom",
        string="Lista de materiales dinámica",
        copy=False,
        readonly=True,
        ondelete="set null",
        help=(
            "Lista de materiales exacta generada para esta configuración. "
            "Solo contiene los componentes seleccionados en la cotización."
        ),
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
        return self._get_dimension_configuration_values().filtered(
            lambda value: not value._is_dimension_na_value()
        )

    def _get_dimension_configuration_values(self):
        self.ensure_one()
        return self._get_all_selected_dimension_values().filtered(
            lambda value: value.attribute_id.component_required
            or value.component_product_id
            or value._is_dimension_na_value()
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
        "linked_line_id",
        "linked_line_ids",
        "width_cm",
        "height_cm",
        "product_template_attribute_value_ids",
        "product_template_attribute_value_ids.product_attribute_value_id.name",
        "product_template_attribute_value_ids.skip_component",
        "product_no_variant_attribute_value_ids",
        "product_no_variant_attribute_value_ids.product_attribute_value_id.name",
        "product_no_variant_attribute_value_ids.skip_component",
    )
    def _compute_name(self):
        super()._compute_name()

    def _get_sale_order_line_multiline_description_sale(self):
        self.ensure_one()
        if not self.dimension_enabled:
            return super()._get_sale_order_line_multiline_description_sale()

        selected_values = self._get_all_selected_dimension_values().filtered(
            lambda value: not value._is_dimension_na_value()
        ).sorted()
        configuration_parts = []
        for attribute in selected_values.attribute_id.sorted("sequence"):
            attribute_values = selected_values.filtered(
                lambda value: value.attribute_id == attribute
            )
            configuration_parts.append(_(
                "%(attribute)s: %(values)s",
                attribute=attribute.name,
                values=", ".join(attribute_values.mapped("name")),
            ))

        description = self.product_template_id.name or self.product_id.name
        if configuration_parts:
            description = "%s (%s)" % (
                description,
                ", ".join(configuration_parts),
            )
        if self.width_cm > 0.0 and self.height_cm > 0.0:
            description += _(
                "\n(%(width).2f cm x %(height).2f cm)",
                width=self.width_cm,
                height=self.height_cm,
            )
        if self.product_id.description_sale:
            description += "\n" + self.product_id.description_sale
        return description

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
        "product_template_attribute_value_ids.attribute_line_id.attribute_id.dimension_type",
        "product_no_variant_attribute_value_ids",
        "product_no_variant_attribute_value_ids.pricing_mode",
        "product_no_variant_attribute_value_ids.dimension_price",
        "product_no_variant_attribute_value_ids.price_extra",
        "product_no_variant_attribute_value_ids.attribute_line_id.attribute_id.dimension_type",
    )
    def _compute_base_dimension_price(self):
        for line in self:
            if not line.product_id or not line.dimension_enabled:
                line.base_dimension_price = 0.0
                continue

            total_price = line.product_template_id.list_price
            for value in line._get_all_selected_dimension_values().filtered(
                lambda item: not item._is_dimension_na_value()
            ):
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
                line.name = line._get_sale_order_line_multiline_description_sale()

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

    def _get_dimension_bom(self):
        self.ensure_one()
        if not self.product_id:
            return self.env["mrp.bom"]
        boms = self.env["mrp.bom"].sudo().search([
            ("active", "=", True),
            ("type", "=", "normal"),
            ("is_dimension_dynamic", "=", False),
            ("company_id", "in", [False, self.order_id.company_id.id]),
            ("product_tmpl_id", "=", self.product_template_id.id),
            ("product_id", "in", [False, self.product_id.id]),
        ], order="sequence, product_id, id")
        configured_boms = boms.filtered(
            lambda bom: bom.bom_line_ids.filtered("dimension_attribute_id")
        )
        return configured_boms[:1] or boms[:1]

    def _link_dimension_components_from_bom(self, selected_values):
        self.ensure_one()
        bom = self._get_dimension_bom()
        bom_lines_by_attribute = {
            line.dimension_attribute_id.id: line
            for line in bom.bom_line_ids.filtered("dimension_attribute_id")
        }
        resolved_components = {}
        for value in selected_values:
            bom_line = bom_lines_by_attribute.get(value.attribute_id.id)
            component = value._get_or_create_bom_component(bom_line)
            component = component or value.component_product_id
            if component and value.component_product_id != component:
                value.product_attribute_value_id.sudo().write({
                    "component_product_id": component.id,
                })
            resolved_components[value.id] = component
        selected_values.invalidate_recordset(["component_product_id"])
        return resolved_components

    def _create_dimension_bom(self, selected_values, resolved_components=None):
        """Build the exact, archived BoM that standard MRP will use for this line."""
        self.ensure_one()
        resolved_components = resolved_components or {}

        def get_component(value):
            return resolved_components.get(value.id) or value.component_product_id

        source_bom = self._get_dimension_bom()
        previous_bom = self.dimension_bom_id.sudo()
        code = _(
            "DIN %(order)s / línea %(line)s",
            order=self.order_id.name or self.order_id.id,
            line=self.id,
        )
        if source_bom:
            dynamic_bom = source_bom.sudo().copy({
                "active": False,
                "code": code,
                "is_dimension_dynamic": True,
                "dimension_sale_line_id": self.id,
                "dimension_source_bom_id": source_bom.id,
            })
            mapped_lines = dynamic_bom.bom_line_ids.filtered(
                "dimension_attribute_id"
            )
            for bom_line in mapped_lines:
                attribute_values = selected_values.filtered(
                    lambda value: value.attribute_id == bom_line.dimension_attribute_id
                )
                if not attribute_values:
                    bom_line.unlink()
                    continue

                target_lines = [bom_line]
                target_lines.extend(
                    bom_line.copy() for _value in attribute_values[1:]
                )
                for target_line, value in zip(target_lines, attribute_values):
                    component = get_component(value)
                    quantity = value._get_component_quantity(
                        self.m2,
                        self.ml,
                        dynamic_bom.product_qty,
                    )
                    if (
                        not component
                        or float_is_zero(
                            quantity,
                            precision_rounding=component.uom_id.rounding,
                        )
                    ):
                        target_line.unlink()
                        continue
                    target_line.write({
                        "product_id": component.id,
                        "product_qty": quantity,
                        "product_uom_id": component.uom_id.id,
                        "dimension_value_id": value.id,
                        "bom_product_template_attribute_value_ids": [
                            Command.clear(),
                        ],
                    })
        else:
            bom_line_commands = []
            for value in selected_values:
                component = get_component(value)
                if not component:
                    continue
                bom_line_commands.append(Command.create({
                    "product_id": component.id,
                    "product_qty": value._get_component_quantity(
                        self.m2,
                        self.ml,
                        1.0,
                    ),
                    "product_uom_id": component.uom_id.id,
                    "dimension_attribute_id": value.attribute_id.id,
                    "dimension_value_id": value.id,
                }))
            dynamic_bom = self.env["mrp.bom"].sudo().create({
                "active": False,
                "code": code,
                "type": "normal",
                "product_tmpl_id": self.product_template_id.id,
                "product_id": self.product_id.id,
                "product_qty": 1.0,
                "product_uom_id": self.product_uom.id,
                "company_id": self.order_id.company_id.id,
                "is_dimension_dynamic": True,
                "dimension_sale_line_id": self.id,
                "bom_line_ids": bom_line_commands,
            })

        self.sudo().dimension_bom_id = dynamic_bom
        if previous_bom and previous_bom != dynamic_bom:
            used_bom = self.env["mrp.production"].sudo().search_count([
                ("bom_id", "=", previous_bom.id),
            ], limit=1)
            if not used_bom:
                previous_bom.unlink()
        return dynamic_bom

    def _get_dimension_manufacture_routes(self):
        self.ensure_one()
        candidate_routes = (
            self.product_id.route_ids
            | self.product_id.categ_id.total_route_ids
            | self.route_id
        )
        return candidate_routes.filtered(
            lambda route: "manufacture" in route.rule_ids.mapped("action")
        )

    def _validate_dimension_configuration(self):
        for line in self.filtered(lambda item: not item.display_type and item.dimension_enabled):
            if line.width_cm <= 0.0 or line.height_cm <= 0.0:
                raise ValidationError(_(
                    "Capture un ancho y un alto mayores que cero para %(product)s.",
                    product=line.product_id.display_name,
                ))
            configuration_values = line._get_dimension_configuration_values()
            selected_values = line._get_selected_dimension_values()
            required_attributes = line.product_template_id.attribute_line_ids.attribute_id.filtered(
                "component_required"
            )
            missing_attributes = required_attributes - configuration_values.attribute_id
            if missing_attributes:
                raise ValidationError(_(
                    "No se puede confirmar la cotización. Falta seleccionar un valor para: %(attributes)s",
                    attributes=", ".join(missing_attributes.mapped("display_name")),
                ))
            resolved_components = line._link_dimension_components_from_bom(
                selected_values
            )
            values_to_link = selected_values.filtered(
                lambda value: value.attribute_id.component_required
                and not resolved_components.get(value.id)
            )
            values_to_link.product_attribute_value_id._link_component_products_by_reference()
            values_to_link.invalidate_recordset(["component_product_id"])
            for value in values_to_link:
                resolved_components[value.id] = (
                    value.product_attribute_value_id.component_product_id
                )
            missing_values = selected_values.filtered(
                lambda value: value.attribute_id.component_required
                and not resolved_components.get(value.id)
            )
            if missing_values:
                raise ValidationError(_(
                    "No se puede confirmar la cotización. Los siguientes valores no tienen un "
                    "Producto componente asociado: %(values)s. Abra Configuración > Atributos, "
                    "use Configurar sobre cada valor y seleccione el producto real. En la pestaña "
                    "Compras de ese producto se configuran sus proveedores. Si su referencia "
                    "interna coincide con un único producto existente, el sistema lo vincula "
                    "automáticamente. También verifique que la línea (Base) de la lista de "
                    "materiales tenga informado el Atributo configurable y que dicho atributo "
                    "use creación de variantes instantánea o dinámica.",
                    values=", ".join(missing_values.mapped("display_name")),
                ))
            company = line.order_id.company_id
            missing_sellers = selected_values.filtered(lambda value: (
                resolved_components.get(value.id)
                and not resolved_components[value.id].sudo().with_company(
                    company
                )._prepare_sellers(False).filtered(
                    lambda seller: not seller.company_id or seller.company_id == company
                )
            ))
            if missing_sellers:
                raise ValidationError(_(
                    "No se puede generar la compra. Los siguientes componentes no tienen "
                    "proveedor: %(values)s. Configure el proveedor en la pestaña Compras del "
                    "producto (Base); sus variantes exactas usarán esa misma lista.",
                    values=", ".join(missing_sellers.mapped("display_name")),
                ))
            warehouse = line.order_id.warehouse_id
            manufacture_routes = line._get_dimension_manufacture_routes()
            if not manufacture_routes:
                raise ValidationError(_(
                    "Configure la ruta Fabricar en %(product)s. La ruta Comprar se utiliza "
                    "solamente para los componentes seleccionados.",
                    product=line.product_id.display_name,
                ))
            if (
                selected_values
                and (
                    not warehouse.buy_to_resupply
                    or not warehouse.buy_pull_id
                    or not warehouse.buy_pull_id.active
                )
            ):
                raise ValidationError(_(
                    "Active la ruta Comprar del almacén %(warehouse)s para generar las "
                    "solicitudes de cotización de los componentes.",
                    warehouse=warehouse.display_name,
                ))
            line._create_dimension_bom(selected_values, resolved_components)

    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        self.ensure_one()
        if self.dimension_enabled:
            manufacture_routes = self._get_dimension_manufacture_routes()
            values.update({
                "dimension_sale_line_id": self.id,
                "dimension_width_cm": self.width_cm,
                "dimension_height_cm": self.height_cm,
                "dimension_m2": self.m2,
                "dimension_ml": self.ml,
                "dimension_value_ids": self._get_selected_dimension_values().ids,
            })
            if self.dimension_bom_id:
                values["bom_id"] = self.dimension_bom_id.sudo()
                values["dimension_bom_id"] = self.dimension_bom_id.id
            if manufacture_routes:
                values["route_ids"] = manufacture_routes
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
