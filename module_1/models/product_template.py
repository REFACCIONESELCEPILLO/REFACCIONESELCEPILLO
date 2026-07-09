# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warehouse_free_qty_kanban = fields.Text(
        string='Disponible por almacen',
        compute='_compute_warehouse_free_qty_kanban',
        compute_sudo=True,
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
            template.id: {warehouse.id: 0.0 for warehouse, __parent_path in warehouse_data}
            for template in self
        }
        if variant_to_template:
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
                        quantities[template.id][warehouse.id] += quant.quantity - quant.reserved_quantity
                        break

        for product in self:
            lines = []
            for warehouse, __parent_path in warehouse_data:
                free_qty = quantities[product.id][warehouse.id]
                if free_qty > 0:
                    lines.append('%s: %.3f %s' % (
                        warehouse.display_name,
                        free_qty,
                        product.uom_id.name,
                    ))
            product.warehouse_free_qty_kanban = '\n'.join(lines)

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
