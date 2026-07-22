from odoo import api, fields, models
from odoo.tools import float_compare, float_is_zero


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    is_dimension_dynamic = fields.Boolean(
        string="Lista dimensional dinámica",
        copy=False,
        index=True,
        help=(
            "Indica que la lista fue generada desde una línea de venta y contiene "
            "solo los componentes seleccionados."
        ),
    )
    dimension_sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Línea de venta dimensional",
        copy=False,
        index=True,
        ondelete="set null",
    )
    dimension_source_bom_id = fields.Many2one(
        "mrp.bom",
        string="Plantilla de lista de materiales",
        copy=False,
        index=True,
        ondelete="set null",
    )


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    dimension_attribute_id = fields.Many2one(
        "product.attribute",
        string="Atributo configurable",
        domain="[('component_required', '=', True)]",
        help=(
            "Identifica esta línea como el producto base que será sustituido por "
            "el componente exacto elegido en el configurador."
        ),
    )
    dimension_value_id = fields.Many2one(
        "product.template.attribute.value",
        string="Valor configurado",
        copy=True,
        index=True,
        ondelete="set null",
        help="Valor exacto de la cotización que originó este componente.",
    )


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    dimension_sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Línea de venta dimensional",
        copy=False,
        index=True,
    )
    dimension_width_cm = fields.Float("Ancho (cm)", digits=(16, 2), copy=False)
    dimension_height_cm = fields.Float("Alto (cm)", digits=(16, 2), copy=False)
    dimension_m2 = fields.Float("M² por pieza", digits=(16, 4), copy=False)
    dimension_ml = fields.Float("ML por pieza", digits=(16, 4), copy=False)
    dimension_value_ids = fields.Many2many(
        "product.template.attribute.value",
        "mrp_production_dimension_value_rel",
        "production_id",
        "value_id",
        string="Configuración seleccionada",
        copy=False,
    )

    @api.model_create_multi
    def create(self, values_list):
        productions = super().create(values_list)
        productions._sync_dimension_component_moves()
        return productions

    def write(self, values):
        result = super().write(values)
        sync_fields = {
            "product_qty",
            "dimension_m2",
            "dimension_ml",
            "dimension_value_ids",
        }
        if sync_fields.intersection(values) and not self.env.context.get("skip_dimension_component_sync"):
            self._sync_dimension_component_moves()
        return result

    def _sync_dimension_component_moves(self):
        StockMove = self.env["stock.move"]
        for production in self.filtered(
            lambda mo: (
                mo.dimension_sale_line_id
                and not mo.bom_id.is_dimension_dynamic
                and mo.state not in ("done", "cancel")
            )
        ):
            bom_lines_by_attribute = {
                line.dimension_attribute_id.id: line
                for line in production.bom_id.bom_line_ids.filtered("dimension_attribute_id")
            }
            configuration_values = production.dimension_value_ids.filtered(
                lambda value: (
                    value.attribute_id.component_required or value.component_product_id
                )
                and not value._is_dimension_na_value()
            )
            for value in configuration_values:
                bom_line = bom_lines_by_attribute.get(value.attribute_id.id)
                component = value._get_or_create_bom_component(bom_line)
                if component and value.component_product_id != component:
                    value.product_attribute_value_id.sudo().write({
                        "component_product_id": component.id,
                    })
            expected_values = configuration_values.filtered(
                "component_product_id"
            )
            selected_attributes = configuration_values.attribute_id
            placeholder_moves = production.move_raw_ids.filtered(
                lambda move: (
                    not move.dimension_value_id
                    and move.state not in ("done", "cancel")
                    and move.bom_line_id
                    and (
                        (
                            move.bom_line_id.dimension_attribute_id
                        )
                        or (
                            not move.bom_line_id.dimension_attribute_id
                            and len(move.bom_line_id.bom_product_template_attribute_value_ids.attribute_id) == 1
                            and move.bom_line_id.bom_product_template_attribute_value_ids.attribute_id
                            in selected_attributes
                        )
                    )
                )
            )
            production._remove_dimension_moves(placeholder_moves)

            existing_moves = production.move_raw_ids.filtered(
                lambda move: move.dimension_value_id and move.state != "cancel"
            )
            moves_by_value = {move.dimension_value_id.id: move for move in existing_moves}

            obsolete_moves = existing_moves.filtered(
                lambda move: move.dimension_value_id not in expected_values
            )
            production._remove_dimension_moves(obsolete_moves)

            new_moves = StockMove
            for value in expected_values:
                component = value.component_product_id
                bom_line = bom_lines_by_attribute.get(value.attribute_id.id)
                quantity = value._get_component_quantity(
                    production.dimension_m2,
                    production.dimension_ml,
                    production.product_qty,
                )
                move = moves_by_value.get(value.id)
                if move and move.product_id != component:
                    production._remove_dimension_moves(move)
                    move = False
                if float_is_zero(quantity, precision_rounding=component.uom_id.rounding):
                    if move:
                        production._remove_dimension_moves(move)
                    continue
                if move:
                    move_updates = {}
                    if bom_line and move.bom_line_id != bom_line:
                        move_updates["bom_line_id"] = bom_line.id
                    if float_compare(
                        move.product_uom_qty,
                        quantity,
                        precision_rounding=component.uom_id.rounding,
                    ):
                        move_updates.update({
                            "product_uom_qty": quantity,
                            "product_uom": component.uom_id.id,
                        })
                    if move_updates:
                        move.with_context(skip_dimension_component_sync=True).write(move_updates)
                    continue

                move_values = production._get_move_raw_values(
                    component,
                    quantity,
                    component.uom_id,
                    bom_line.operation_id.id if bom_line else False,
                    bom_line,
                )
                move_values["dimension_value_id"] = value.id
                buy_route = production.warehouse_id.buy_pull_id.route_id
                if buy_route:
                    move_values.update({
                        "procure_method": "make_to_order",
                        "route_ids": [(6, 0, buy_route.ids)],
                    })
                new_moves |= StockMove.create(move_values)

            if new_moves and production.state != "draft":
                new_moves._action_confirm(merge=False)

    def _get_move_raw_values(
        self,
        product,
        product_uom_qty,
        product_uom,
        operation_id=False,
        bom_line=False,
    ):
        values = super()._get_move_raw_values(
            product,
            product_uom_qty,
            product_uom,
            operation_id=operation_id,
            bom_line=bom_line,
        )
        if bom_line and bom_line.dimension_value_id:
            values["dimension_value_id"] = bom_line.dimension_value_id.id
            buy_route = self.warehouse_id.buy_pull_id.route_id
            if buy_route:
                values.update({
                    "procure_method": "make_to_order",
                    "route_ids": [(6, 0, buy_route.ids)],
                })
        return values

    def _remove_dimension_moves(self, moves):
        draft_moves = moves.filtered(lambda move: move.state == "draft")
        if draft_moves:
            draft_moves.unlink()
        active_moves = (moves - draft_moves).filtered(
            lambda move: move.state not in ("done", "cancel")
        )
        if active_moves:
            active_moves._action_cancel()


class StockMove(models.Model):
    _inherit = "stock.move"

    dimension_sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Línea de venta dimensional",
        copy=False,
        index=True,
        ondelete="set null",
    )
    dimension_bom_id = fields.Many2one(
        "mrp.bom",
        string="Lista de materiales dinámica",
        copy=False,
        index=True,
        ondelete="set null",
    )
    dimension_value_id = fields.Many2one(
        "product.template.attribute.value",
        string="Valor configurado",
        copy=False,
        index=True,
        ondelete="set null",
    )

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        self.ensure_one()
        sale_line = self.dimension_sale_line_id
        dimension_bom = self.dimension_bom_id or sale_line.dimension_bom_id
        if sale_line and dimension_bom:
            manufacture_routes = sale_line._get_dimension_manufacture_routes()
            values.update({
                "dimension_sale_line_id": sale_line.id,
                "dimension_bom_id": dimension_bom.id,
                "bom_id": dimension_bom.sudo(),
                "dimension_width_cm": sale_line.width_cm,
                "dimension_height_cm": sale_line.height_cm,
                "dimension_m2": sale_line.m2,
                "dimension_ml": sale_line.ml,
                "dimension_value_ids": (
                    sale_line._get_selected_dimension_values().ids
                ),
            })
            if manufacture_routes:
                values["route_ids"] = manufacture_routes
        if not self.dimension_value_id or not self.product_id:
            return values

        planned_date = fields.Date.to_date(values.get("date_planned"))
        variant_seller = self.product_id.with_company(
            self.company_id
        )._get_dimension_supplierinfo(
            self.dimension_value_id.product_attribute_value_id,
            quantity=self.product_uom_qty,
            date=planned_date,
            uom_id=self.product_uom,
        )
        if variant_seller:
            values["supplierinfo_id"] = variant_seller
        return values
