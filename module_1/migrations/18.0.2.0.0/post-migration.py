# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


LEGACY_XMLIDS = (
    # Menú, acción y vista del antiguo informe de existencias.
    'module_1.menu_sale_report_dashboard_inherit_id',
    'module_1.sale_report_action_dashboard_pivot_inherit_id',
    'module_1.sale_report_action_dashboard',
    'module_1.sale_report_pivot_inherit_id',
    # Vistas antiguas de productos y ubicaciones.
    'module_1.product_template_kanban_inherit_id',
    'module_1.product_template_inherit_id',
    'module_1.stock_location_inherit_id',
    # Reporte de factura legado; module_1 queda dedicado al ticket de venta.
    'module_1.action_report_print_account_move_id',
    'module_1.report_print_account_move_id',
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    model_data = env['ir.model.data'].sudo()

    for xmlid in LEGACY_XMLIDS:
        module, name = xmlid.split('.', 1)
        metadata = model_data.search([
            ('module', '=', module),
            ('name', '=', name),
        ])
        if not metadata:
            continue

        record = env[metadata.model].browse(metadata.res_id).exists()
        if record:
            record.unlink()
        metadata.exists().unlink()
