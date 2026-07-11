# -*- coding: utf-8 -*-

from odoo import api, fields, models
from markupsafe import Markup, escape


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warehouse_free_qty_kanban = fields.Text(
        string='Disponible por almacen',
        compute='_compute_warehouse_free_qty_kanban',
        compute_sudo=True,
    )
    warehouse_availability_html = fields.Html(
        string='Resumen de existencias por almacen',
        compute='_compute_warehouse_availability_html',
        compute_sudo=True,
        sanitize=False,
    )
    warehouse_availability_ids = fields.One2many(
        comodel_name='product.warehouse.availability',
        inverse_name='product_tmpl_id',
        string='Existencias por almacen',
    )

    @api.depends(
        'product_variant_ids.stock_quant_ids.quantity',
        'product_variant_ids.stock_quant_ids.reserved_quantity',
        'product_variant_ids.stock_quant_ids.location_id',
    )
    def _compute_warehouse_free_qty_kanban(self):
        warehouse_data, quantities = self._get_warehouse_quantities()

        for product in self:
            lines = []
            for warehouse, __parent_path in warehouse_data:
                free_qty = quantities[product.id][warehouse.id]['free_quantity']
                if free_qty > 0:
                    lines.append('%s: %.3f %s' % (
                        warehouse.display_name,
                        free_qty,
                        product.uom_id.name,
                    ))
            product.warehouse_free_qty_kanban = '\n'.join(lines)

    @api.depends(
        'product_variant_ids.stock_quant_ids.quantity',
        'product_variant_ids.stock_quant_ids.reserved_quantity',
        'product_variant_ids.stock_quant_ids.location_id',
    )
    def _compute_warehouse_availability_html(self):
        warehouse_data, quantities = self._get_warehouse_quantities()

        for product in self:
            rows = []
            for warehouse, __parent_path in warehouse_data:
                values = quantities[product.id][warehouse.id]
                if not any(values.values()):
                    continue
                rows.append(
                    '<tr>'
                    '<td>%s</td>'
                    '<td class="text-end">%.3f</td>'
                    '<td class="text-end">%.3f</td>'
                    '<td class="text-end">%.3f</td>'
                    '<td>%s</td>'
                    '</tr>' % (
                        escape(warehouse.display_name),
                        values['quantity_on_hand'],
                        values['reserved_quantity'],
                        values['free_quantity'],
                        escape(product.uom_id.name or ''),
                    )
                )
            if not rows:
                product.warehouse_availability_html = Markup(
                    '<p class="text-muted">Sin existencias por almacen.</p>'
                )
                continue

            product.warehouse_availability_html = Markup(
                '<table class="table table-sm table-hover o_list_table">'
                '<thead><tr>'
                '<th>Almacen</th>'
                '<th class="text-end">Fisico</th>'
                '<th class="text-end">Reservado</th>'
                '<th class="text-end">Disponible</th>'
                '<th>UdM</th>'
                '</tr></thead>'
                '<tbody>%s</tbody>'
                '</table>' % ''.join(rows)
            )

    def _get_warehouse_quantities(self):
        warehouses = self.env['stock.warehouse'].search([
            ('company_id', 'in', self.env.companies.ids),
        ])
        warehouse_data = [
            (
                warehouse,
                warehouse.view_location_id.parent_path or '',
            )
            for warehouse in warehouses
            if warehouse.view_location_id.parent_path
        ]
        variant_to_template = {
            variant.id: template
            for template in self
            for variant in template.product_variant_ids
        }
        quantities = {
            template.id: {
                warehouse.id: {
                    'quantity_on_hand': 0.0,
                    'reserved_quantity': 0.0,
                    'free_quantity': 0.0,
                }
                for warehouse, __parent_path in warehouse_data
            }
            for template in self
        }
        if not variant_to_template:
            return warehouse_data, quantities

        quants = self.env['stock.quant'].sudo().search([
            ('product_id', 'in', list(variant_to_template)),
            ('location_id.usage', '=', 'internal'),
        ])
        for quant in quants:
            template = variant_to_template[quant.product_id.id]
            location_path = quant.location_id.parent_path or ''
            for warehouse, warehouse_path in warehouse_data:
                if quant.company_id and quant.company_id != warehouse.company_id:
                    continue
                if location_path.startswith(warehouse_path):
                    values = quantities[template.id][warehouse.id]
                    values['quantity_on_hand'] += quant.quantity
                    values['reserved_quantity'] += quant.reserved_quantity
                    values['free_quantity'] += quant.quantity - quant.reserved_quantity
                    break
        return warehouse_data, quantities

    def action_open_warehouse_availability(self):
        self.ensure_one()
        action = self.env.ref(
            'module_1.product_warehouse_availability_action'
        ).sudo().read()[0]
        action['domain'] = [('product_tmpl_id', '=', self.id)]
        action['context'] = {
            'search_default_group_by_warehouse': 1,
            'search_default_product_tmpl_id': self.id,
        }
        return action
